from __future__ import annotations
import json
import os
import logging
import asyncio
from functools import partial

import pandas as pd
from google import genai

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    _client = genai.Client(api_key=key)
    return _client


def _sample_dataframe(
    df: pd.DataFrame,
    schema_dict: dict | None = None,
    max_rows: int = 50,
    columns_only: list[str] | None = None,
) -> str:
    cols_to_drop = set()
    if schema_dict:
        for c in schema_dict.get("columns", []):
            if c.get("role") in ("identifier", "geo"):
                cols_to_drop.add(c["column_name"])

    subset = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")
    if columns_only:
        use = [c for c in columns_only if c in subset.columns]
        if use:
            subset = subset[use]
    clean = subset.dropna(thresh=int(len(subset.columns) * 0.5))
    sample = clean.head(max_rows)
    return sample.to_csv(index=False, lineterminator="\n")


def _build_schema_summary(schema_dict: dict) -> str:
    parts = []
    parts.append(f"Dataset type: {schema_dict.get('dataset_type', 'unknown')}")
    parts.append(f"Total rows: {schema_dict.get('row_count', '?')}")

    target = schema_dict.get("target_column")
    if target:
        parts.append(f"Detected target column: {target}")

    cols = schema_dict.get("columns", [])
    col_info = []
    for c in cols:
        col_info.append(f"  {c['column_name']} ({c['role']})")
    parts.append("Columns:\n" + "\n".join(col_info))

    return "\n".join(parts)


_token_log: list[dict] = []


def get_token_usage() -> dict:
    """Return cumulative token usage stats."""
    if not _token_log:
        return {"calls": 0, "total_input": 0, "total_output": 0, "total": 0, "breakdown": []}
    total_in = sum(e["input_tokens"] for e in _token_log)
    total_out = sum(e["output_tokens"] for e in _token_log)
    return {
        "calls": len(_token_log),
        "total_input": total_in,
        "total_output": total_out,
        "total": total_in + total_out,
        "breakdown": _token_log[-20:],
    }


def reset_token_usage():
    _token_log.clear()


def _call_gemini(prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        ),
    )

    usage = getattr(response, "usage_metadata", None)
    input_tok = getattr(usage, "prompt_token_count", 0) or 0
    output_tok = getattr(usage, "candidates_token_count", 0) or 0
    total_tok = input_tok + output_tok

    caller = "unknown"
    p_lower = prompt[:400].lower()
    if "data prep expert" in p_lower and "encoding" in p_lower:
        caller = "encoding_suggest"
    elif "clustering expert" in p_lower or "pca and k-means" in p_lower:
        caller = "clustering_features"
    elif "machine learning expert" in p_lower or "ml configuration" in p_lower:
        caller = "ml_config"
    elif "suggest" in prompt[:200].lower() or "chart types" in prompt[:300].lower():
        caller = "suggest_charts"
    elif "executive summary" in p_lower or "senior data analyst" in p_lower:
        if "just plotted" in p_lower:
            caller = "chart_insights"
        else:
            caller = "narrative_insights"

    _token_log.append({
        "call": caller,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "total_tokens": total_tok,
    })

    logger.info(
        f"Gemini [{caller}] tokens — input: {input_tok}, output: {output_tok}, total: {total_tok}"
    )

    return response.text.strip()


def _parse_json_response(text: str) -> dict | list:
    import re

    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object in the text
    for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    # Last resort: fix common issues (trailing commas, single quotes)
    cleaned = text.replace("'", '"')
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse Gemini response as JSON: {text[:200]}")


# ---------------------------------------------------------------------------
# Chart suggestions
# ---------------------------------------------------------------------------

_CHART_SUGGESTION_PROMPT = """You are a data visualization expert. Given the dataset schema and a sample of its data, suggest the best charts to visualize this dataset.

The available chart types are: histogram, bar, scatter, box, heatmap, pie (for tabular data) and line, ohlc, candlestick (for time-series data).

For each chart, specify:
- title: a short descriptive title
- chart_type: one of the types above
- x_col: column name for x axis (or the main column). Use the normalized column names shown in the schema.
- y_col: column name for y axis (if applicable, null otherwise)
- color_col: column to color/group by (if applicable, null otherwise)
- description: max 10 words on what this chart reveals
- priority: 1 (most important) to 10 (least important)

Return ONLY a valid JSON array. No markdown, no explanation, no extra text. Suggest exactly 8 charts ranked by analytical value. Keep all string values short and concise.

SCHEMA:
{schema}

SAMPLE DATA (first rows):
{sample}"""


async def suggest_charts(df: pd.DataFrame, schema_dict: dict) -> list[dict]:
    sample_csv = _sample_dataframe(df, schema_dict)
    schema_text = _build_schema_summary(schema_dict)

    prompt = _CHART_SUGGESTION_PROMPT.format(schema=schema_text, sample=sample_csv)

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 4096, 0.3))
        suggestions = _parse_json_response(text)

        if isinstance(suggestions, list):
            suggestions.sort(key=lambda s: s.get("priority", 5))
            return suggestions[:10]
        return []

    except Exception as e:
        logger.error(f"Gemini chart suggestion failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Narrative insights
# ---------------------------------------------------------------------------

_INSIGHT_PROMPT = """You are a senior data analyst. Given the dataset schema, sample data, and computed statistics, provide a comprehensive analysis.

Write your response as a JSON object with these fields:
- "narrative": A 2-3 sentence executive summary. Be specific with numbers. Keep under 200 words.
- "findings": An array of exactly 5 objects, each with:
  - "title": max 8 words
  - "description": max 25 words with specific numbers
  - "severity": "critical", "warning", or "info"
  - "recommendation": max 15 words

Return ONLY valid JSON. No markdown, no code fences. Keep all text concise.

SCHEMA:
{schema}

COMPUTED STATISTICS:
{stats}

SAMPLE DATA (first rows):
{sample}"""


async def generate_narrative_insights(
    df: pd.DataFrame, schema_dict: dict, stats: dict
) -> dict:
    sample_csv = _sample_dataframe(df, schema_dict)
    schema_text = _build_schema_summary(schema_dict)

    stats_text = json.dumps(stats, indent=2, default=str)
    if len(stats_text) > 3000:
        stats_text = stats_text[:3000] + "\n... (truncated)"

    prompt = _INSIGHT_PROMPT.format(
        schema=schema_text,
        stats=stats_text,
        sample=sample_csv,
    )

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 4096, 0.4))
        return _parse_json_response(text)

    except Exception as e:
        logger.error(f"Gemini narrative insight failed: {e}")
        return {"narrative": f"AI analysis unavailable: {e}", "findings": []}


# ---------------------------------------------------------------------------
# Chart-specific insights
# ---------------------------------------------------------------------------

_CHART_INSIGHT_PROMPT = """You are a senior data analyst. The user just plotted a {chart_type} chart showing {description}.

Given the chart configuration and the underlying data, provide specific analytical insights about what this chart reveals.

Write your response as a JSON object with:
- "chart_narrative": 1-2 sentences, max 50 words, key takeaway from this chart
- "observations": Array of exactly 3 objects, each with:
  - "title": max 6 words
  - "detail": max 20 words
  - "severity": "critical", "warning", or "info"

Return ONLY valid JSON. No markdown. Be extremely concise.

CHART CONFIG:
- Type: {chart_type}
- X column: {x_col}
- Y column: {y_col}
- Color/Group: {color_col}

SCHEMA:
{schema}

SAMPLE DATA:
{sample}"""


# ---------------------------------------------------------------------------
# ML config detection
# ---------------------------------------------------------------------------

_ML_CONFIG_PROMPT = """ML expert: analyze dataset, return JSON.

Return ONLY this JSON (keep ALL string values under 10 words):
{{"target_column":"col","task_type":"classification","reason_target":"short","reason_task":"short","exclude_columns":["col"],"recommended_models":["id"],"confidence":0.9}}

task_type: "classification" or "regression"
Model IDs: logistic_regression, random_forest, gradient_boosting, linear_regression, ridge_regression, random_forest_regressor, gradient_boosting_regressor

SCHEMA:
{schema}

DATA:
{sample}"""


# ---------------------------------------------------------------------------
# PCA / clustering feature selection
# ---------------------------------------------------------------------------

_CLUSTERING_FEATURES_PROMPT = """Pick numeric columns for PCA+KMeans clustering.

Include: behavioral, financial, usage, scores, counts.
Exclude: IDs, zip/lat/long, near-constants, target proxies.

Return ONLY: {{"include":["col"],"exclude":["col"],"reason":"max 10 words","confidence":0.9}}

COLUMNS: {numeric_list}"""


async def suggest_clustering_columns(df: pd.DataFrame, schema_dict: dict) -> dict:
    """Gemini picks which numeric columns to use for PCA/K-Means."""
    numeric_cols = [c for c in schema_dict.get("value_columns", []) if c in df.columns]
    if not numeric_cols:
        return {"feature_columns": [], "exclude_columns": [], "reason": "No numeric columns", "confidence": 0.0}

    numeric_list = ", ".join(numeric_cols)
    prompt = _CLUSTERING_FEATURES_PROMPT.format(numeric_list=numeric_list)

    allowed = set(numeric_cols)
    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 2048, 0.2))
        result = _parse_json_response(text)
        if not isinstance(result, dict):
            return {"feature_columns": list(numeric_cols), "exclude_columns": [], "reason": "Could not parse AI response", "confidence": 0.0}

        raw_inc = result.get("include") or result.get("feature_columns") or []
        if isinstance(raw_inc, str):
            raw_inc = [raw_inc]
        picked = [c for c in raw_inc if c in allowed]

        raw_excl = result.get("exclude") or result.get("exclude_columns") or []
        if isinstance(raw_excl, str):
            raw_excl = [raw_excl]
        excluded = [c for c in raw_excl if c in allowed]

        if not picked:
            picked = [c for c in numeric_cols if c not in set(excluded)]
        if not picked:
            picked = list(numeric_cols)

        return {
            "feature_columns": picked,
            "exclude_columns": excluded,
            "reason": str(result.get("reason", ""))[:200],
            "confidence": float(result.get("confidence", 0.5)) if result.get("confidence") is not None else 0.5,
        }
    except Exception as e:
        logger.error(f"Gemini clustering features failed: {e}")
        return {"feature_columns": list(numeric_cols), "exclude_columns": [], "reason": f"AI unavailable — all columns selected", "confidence": 0.0}


# ---------------------------------------------------------------------------
# Encoding suggestions
# ---------------------------------------------------------------------------

_ENCODING_PROMPT = """Data prep expert: choose per-column encodings for ML.

Return ONLY JSON: {{"encodings":{{"col":"one_hot"}},"reasons":{{"col":"max 6 words"}}}}

Allowed values:
- numeric role: "none" or "drop"
- categorical role: "binary", "one_hot", "label", "frequency", "target", "drop"

Use ONLY keys from COLUMN_NAMES. Prefer one_hot for low-cardinality nominals; frequency or label for high cardinality; binary for yes/no; target only if TARGET is set and column is predictive; drop for IDs.

COLUMNS:
{cols_json}

TARGET: {target}
"""


async def suggest_encoding_config(
    df: pd.DataFrame,
    schema_dict: dict,
    target: str | None,
) -> dict:
    from app.services.feature_encoding import (
        CATEGORICAL_ENCODING_OPTIONS,
        NUMERIC_ENCODING_OPTIONS,
        encoding_profile,
        merge_encoding_spec,
    )

    prof = encoding_profile(df, schema_dict, target)
    if not prof["columns"]:
        return {"encodings": {}, "reasons": {}}

    cols_json = json.dumps(
        [{"name": c["name"], "role": c["role"], "nunique": c["nunique"], "null_pct": c["null_pct"]} for c in prof["columns"]],
        separators=(",", ":"),
    )
    prompt = _ENCODING_PROMPT.format(
        cols_json=cols_json,
        target=target or "null",
    )
    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 2048, 0.15))
        raw = _parse_json_response(text)
        if not isinstance(raw, dict):
            return {"encodings": {}, "reasons": {}}
        enc_in = raw.get("encodings") or {}
        reasons = raw.get("reasons") or {}
        if not isinstance(enc_in, dict):
            enc_in = {}
        # validate: only known columns and allowed values per role
        name_to_role = {c["name"]: c["role"] for c in prof["columns"]}
        cleaned = {}
        for k, v in enc_in.items():
            if k not in name_to_role:
                continue
            role = name_to_role[k]
            opts = NUMERIC_ENCODING_OPTIONS if role == "numeric" else CATEGORICAL_ENCODING_OPTIONS
            if v in opts:
                cleaned[k] = v
        merged = merge_encoding_spec(prof["columns"], cleaned)
        return {"encodings": merged, "reasons": reasons if isinstance(reasons, dict) else {}}
    except Exception as e:
        logger.error(f"Gemini encoding suggest failed: {e}")
        merged = merge_encoding_spec(prof["columns"], None)
        return {"encodings": merged, "reasons": {}, "error": str(e)}


async def suggest_ml_config(df: pd.DataFrame, schema_dict: dict) -> dict:
    sample_csv = _sample_dataframe(df, schema_dict, max_rows=30)
    schema_text = _build_schema_summary(schema_dict)

    prompt = _ML_CONFIG_PROMPT.format(schema=schema_text, sample=sample_csv)

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 2048, 0.2))
        result = _parse_json_response(text)
        if isinstance(result, dict):
            return result
        return {}
    except Exception as e:
        logger.error(f"Gemini ML config failed: {e}")
        return {}


async def generate_chart_insights(
    df: pd.DataFrame,
    schema_dict: dict,
    chart_type: str,
    x_col: str | None,
    y_col: str | None,
    color_col: str | None,
) -> dict:
    sample_csv = _sample_dataframe(df, schema_dict)
    schema_text = _build_schema_summary(schema_dict)

    desc_parts = []
    if x_col:
        desc_parts.append(x_col)
    if y_col:
        desc_parts.append(f"vs {y_col}")
    if color_col:
        desc_parts.append(f"colored by {color_col}")
    description = " ".join(desc_parts) or "the dataset"

    prompt = _CHART_INSIGHT_PROMPT.format(
        chart_type=chart_type,
        description=description,
        x_col=x_col or "N/A",
        y_col=y_col or "N/A",
        color_col=color_col or "None",
        schema=schema_text,
        sample=sample_csv,
    )

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(_call_gemini, prompt, 2048, 0.4))
        return _parse_json_response(text)

    except Exception as e:
        logger.error(f"Gemini chart insight failed: {e}")
        return {"chart_narrative": f"AI analysis unavailable: {e}", "observations": []}
