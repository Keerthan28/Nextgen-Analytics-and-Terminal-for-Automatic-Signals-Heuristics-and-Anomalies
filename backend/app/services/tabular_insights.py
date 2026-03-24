from __future__ import annotations
import numpy as np
import pandas as pd

from app.models.schemas import DatasetSchema, InsightItem, InsightReport


def generate_tabular_insights(
    df: pd.DataFrame, schema: DatasetSchema, dataset_id: str, max_findings: int = 8
) -> InsightReport:
    findings: list[InsightItem] = []

    findings.extend(_shape_insights(df, schema))
    findings.extend(_missing_data_insights(df, schema))
    findings.extend(_target_insights(df, schema))
    findings.extend(_distribution_insights(df, schema))
    findings.extend(_correlation_insights(df, schema))
    findings.extend(_category_insights(df, schema))
    findings.extend(_outlier_insights(df, schema))

    findings.sort(key=lambda f: _severity_rank(f.severity), reverse=True)
    top = findings[:max_findings]

    summary_parts = [f.title for f in top[:5]]
    summary = "Key findings: " + "; ".join(summary_parts) if summary_parts else "No significant findings."

    return InsightReport(dataset_id=dataset_id, top_findings=top, summary=summary)


def _severity_rank(sev: str) -> int:
    return {"critical": 4, "warning": 3, "info": 2, "neutral": 1}.get(sev, 0)


def _shape_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    n_cat = len(schema.category_columns)
    n_num = len(schema.value_columns)
    items.append(InsightItem(
        title=f"Dataset: {len(df):,} rows x {len(df.columns)} columns",
        description=f"{n_num} numeric and {n_cat} categorical features detected.",
        severity="info",
        rule="dataset_shape",
    ))
    return items


def _missing_data_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    total_cells = len(df) * len(df.columns)
    total_missing = int(df.isna().sum().sum())
    pct = total_missing / total_cells * 100 if total_cells else 0

    if pct > 5:
        worst = df.isna().sum().sort_values(ascending=False)
        worst = worst[worst > 0].head(3)
        detail = ", ".join(f"{c} ({int(v / len(df) * 100)}%)" for c, v in worst.items())
        items.append(InsightItem(
            title=f"Missing data: {pct:.1f}% of all values",
            description=f"Top missing columns: {detail}",
            severity="warning" if pct > 20 else "info",
            metric="missing_pct",
            value=round(pct, 2),
            rule="missing_data_pct",
        ))
    return items


def _target_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    tc = schema.target_column
    if not tc or tc not in df.columns:
        return items

    vc = df[tc].value_counts()
    if len(vc) == 2:
        minority_label = vc.index[-1]
        minority_pct = vc.iloc[-1] / len(df) * 100
        majority_label = vc.index[0]
        majority_pct = vc.iloc[0] / len(df) * 100
        imbalance = majority_pct / minority_pct if minority_pct > 0 else float("inf")

        items.append(InsightItem(
            title=f"{tc}: {minority_label} = {minority_pct:.1f}%, {majority_label} = {majority_pct:.1f}%",
            description=f"Class imbalance ratio: {imbalance:.1f}:1",
            severity="warning" if imbalance > 3 else "info",
            metric="class_imbalance",
            value=round(imbalance, 2),
            rule="binary_target_balance",
        ))
    else:
        items.append(InsightItem(
            title=f"{tc} has {len(vc)} distinct values",
            description=f"Top: {vc.index[0]} ({vc.iloc[0]:,}), {vc.index[1] if len(vc) > 1 else 'N/A'} ({vc.iloc[1]:,} )" if len(vc) > 1 else "Single class",
            severity="info",
            rule="target_distribution",
        ))
    return items


def _distribution_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    for col in schema.value_columns[:10]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if len(s) < 10:
            continue
        skew = float(s.skew())
        if abs(skew) > 2:
            direction = "right" if skew > 0 else "left"
            items.append(InsightItem(
                title=f"{col}: highly skewed ({direction}, skew={skew:.2f})",
                description=f"Consider log transform or binning for {col}.",
                severity="info",
                metric="skewness",
                value=round(skew, 4),
                rule="high_skewness_gt_2",
            ))
    return items


def _correlation_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    num_cols = [c for c in schema.value_columns if c in df.columns][:15]
    if len(num_cols) < 2:
        return items

    corr = df[num_cols].corr()
    pairs = []
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            r = corr.iloc[i, j]
            if not np.isnan(r):
                pairs.append((num_cols[i], num_cols[j], r))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    for a, b, r in pairs[:3]:
        if abs(r) > 0.7:
            strength = "very strong" if abs(r) > 0.9 else "strong"
            direction = "positive" if r > 0 else "negative"
            items.append(InsightItem(
                title=f"{strength.title()} {direction} correlation: {a} & {b} (r={r:.3f})",
                description=f"These columns move {'together' if r > 0 else 'inversely'}. Potential redundancy or causal link.",
                severity="warning" if abs(r) > 0.9 else "info",
                metric="correlation",
                value=round(r, 4),
                rule="high_correlation_gt_0.7",
            ))

    return items


def _category_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    tc = schema.target_column
    if not tc or tc not in df.columns or df[tc].nunique() > 10:
        return items

    for cat in schema.category_columns[:8]:
        if cat == tc or cat not in df.columns:
            continue
        if df[cat].nunique() > 20 or df[cat].nunique() < 2:
            continue

        ct = pd.crosstab(df[cat], df[tc], normalize="index")
        if ct.shape[1] != 2:
            continue

        target_col = ct.columns[-1]
        rates = ct[target_col]
        spread = float(rates.max() - rates.min())

        if spread > 0.15:
            best = rates.idxmax()
            worst = rates.idxmin()
            items.append(InsightItem(
                title=f"{cat} strongly affects {tc}",
                description=f"'{best}' has {rates[best]*100:.1f}% {target_col} rate vs '{worst}' at {rates[worst]*100:.1f}% — a {spread*100:.1f}pp spread.",
                severity="warning" if spread > 0.3 else "info",
                metric="segment_spread",
                value=round(spread * 100, 2),
                rule="category_target_spread_gt_15pp",
            ))

    return items


def _outlier_insights(df: pd.DataFrame, schema: DatasetSchema) -> list[InsightItem]:
    items = []
    for col in schema.value_columns[:10]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if len(s) < 20:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        outliers = ((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum()
        pct = outliers / len(s) * 100
        if pct > 1:
            items.append(InsightItem(
                title=f"{col}: {outliers} extreme outliers ({pct:.1f}%)",
                description=f"Values beyond 3x IQR from quartiles in {col}.",
                severity="info",
                metric="outlier_pct",
                value=round(pct, 2),
                rule="iqr_outlier_gt_1pct",
            ))
    return items
