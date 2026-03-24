"""Per-column feature encoding for ML and clustering."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)

NUMERIC_ENCODING_OPTIONS = ("none", "drop")
CATEGORICAL_ENCODING_OPTIONS = ("binary", "one_hot", "label", "frequency", "target", "drop")

MAX_ONE_HOT_LEVELS = 28


def _col_stats(s: pd.Series) -> dict[str, Any]:
    s_clean = s.dropna()
    nu = int(s_clean.nunique()) if len(s_clean) else 0
    sample = s_clean.astype(str).head(5).tolist()
    null_pct = round(float(s.isna().mean() * 100), 2) if len(s) else 0.0
    return {"nunique": nu, "null_pct": null_pct, "sample_values": sample}


def encoding_profile(
    df: pd.DataFrame,
    schema_dict: dict,
    target: str | None = None,
) -> dict:
    value_cols = [c for c in schema_dict.get("value_columns", []) if c in df.columns]
    cat_cols = [c for c in schema_dict.get("category_columns", []) if c in df.columns]
    if target:
        value_cols = [c for c in value_cols if c != target]
        cat_cols = [c for c in cat_cols if c != target]

    columns = []
    for name in value_cols:
        st = _col_stats(df[name])
        columns.append({
            "name": name,
            "role": "numeric",
            "nunique": st["nunique"],
            "null_pct": st["null_pct"],
            "sample_values": st["sample_values"],
            "default_encoding": "none",
            "allowed_encodings": list(NUMERIC_ENCODING_OPTIONS),
        })
    for name in cat_cols:
        st = _col_stats(df[name])
        default = _default_cat_encoding(st["nunique"])
        columns.append({
            "name": name,
            "role": "categorical",
            "nunique": st["nunique"],
            "null_pct": st["null_pct"],
            "sample_values": st["sample_values"],
            "default_encoding": default,
            "allowed_encodings": list(CATEGORICAL_ENCODING_OPTIONS),
        })
    return {"columns": columns, "target_column": target}


def _default_cat_encoding(nunique: int) -> str:
    if nunique <= 2:
        return "binary"
    if nunique <= MAX_ONE_HOT_LEVELS:
        return "one_hot"
    return "frequency"


def merge_encoding_spec(
    profile_columns: list[dict],
    user_spec: dict[str, str] | None,
) -> dict[str, str]:
    out: dict[str, str] = {}
    allowed_map = {c["name"]: set(c["allowed_encodings"]) for c in profile_columns}
    for c in profile_columns:
        name = c["name"]
        enc = (user_spec or {}).get(name, c["default_encoding"])
        if enc not in allowed_map[name]:
            enc = c["default_encoding"]
        out[name] = enc
    return out


def _binary_encode_pair(s_train: pd.Series, s_test: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    yes = {"yes", "true", "1", "y", "t"}
    no = {"no", "false", "0", "n", "f"}

    def map_val(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v == 1:
                return 1.0
            if v == 0:
                return 0.0
        t = str(v).strip().lower()
        if t in yes:
            return 1.0
        if t in no:
            return 0.0
        return np.nan

    tr = s_train.map(map_val)
    te = s_test.map(map_val)
    fill = 0.0
    if tr.notna().any():
        fill = float(tr.mode().dropna().iloc[0]) if len(tr.mode().dropna()) else 0.0
    elif te.notna().any():
        fill = float(te.mode().dropna().iloc[0]) if len(te.mode().dropna()) else 0.0
    tr = tr.fillna(fill)
    te = te.fillna(fill)
    if tr.nunique() <= 1 and te.nunique() <= 1:
        return tr.values.reshape(-1, 1), te.values.reshape(-1, 1)
    u = sorted(set(tr.unique()) | set(te.unique()))
    if len(u) == 2 and all(x in (0.0, 1.0) for x in u):
        return tr.values.reshape(-1, 1), te.values.reshape(-1, 1)
    le = LabelEncoder()
    comb = pd.concat([s_train.fillna("_na_"), s_test.fillna("_na_")]).astype(str)
    le.fit(comb)
    tr_l = le.transform(s_train.fillna("_na_").astype(str)).astype(float)
    te_l = le.transform(s_test.fillna("_na_").astype(str)).astype(float)
    mx = max(tr_l.max(), te_l.max(), 1.0)
    return (tr_l / mx).reshape(-1, 1), (te_l / mx).reshape(-1, 1)


def _one_hot_pair(s_train: pd.Series, s_test: pd.Series) -> tuple[np.ndarray, np.ndarray, list[str]]:
    tr = s_train.fillna("_missing_").astype(str)
    te = s_test.fillna("_missing_").astype(str)
    vc = tr.value_counts()
    cats = vc.index.tolist()[:MAX_ONE_HOT_LEVELS]
    if len(vc) > MAX_ONE_HOT_LEVELS:
        other = "_other_"
        tr = tr.where(tr.isin(cats), other)
        te = te.where(te.isin(cats), other)
        if other not in cats:
            cats = list(cats[: MAX_ONE_HOT_LEVELS - 1]) + [other]
    n = len(cats)
    cat_to_i = {c: i for i, c in enumerate(cats)}
    colname = s_train.name

    def to_mat(s: pd.Series) -> np.ndarray:
        m = np.zeros((len(s), n), dtype=float)
        for i, v in enumerate(s):
            j = cat_to_i.get(v, -1)
            if j >= 0:
                m[i, j] = 1.0
        return m

    names = [f"{colname}={c}" for c in cats]
    return to_mat(tr), to_mat(te), names


def _label_pair(s_train: pd.Series, s_test: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    le = LabelEncoder()
    tr_f = s_train.fillna("_missing_").astype(str)
    le.fit(tr_f)
    tr = le.transform(tr_f).astype(float)
    te_f = s_test.fillna("_missing_").astype(str)
    te = np.array([le.transform([x])[0] if x in le.classes_ else 0 for x in te_f], dtype=float)
    mx = max(tr.max(), te.max(), 1.0)
    return (tr / mx).reshape(-1, 1), (te / mx).reshape(-1, 1)


def _frequency_pair(s_train: pd.Series, s_test: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    tr = s_train.fillna("_missing_").astype(str)
    te = s_test.fillna("_missing_").astype(str)
    freq = tr.value_counts(normalize=True)
    default = 1.0 / max(len(tr), 1)
    tr_v = tr.map(lambda x: float(freq.get(x, default))).values.reshape(-1, 1)
    te_v = te.map(lambda x: float(freq.get(x, default))).values.reshape(-1, 1)
    return tr_v, te_v


def _target_pair(
    s_train: pd.Series, s_test: pd.Series, y_train: np.ndarray, task_type: str,
) -> tuple[np.ndarray, np.ndarray]:
    tr = s_train.fillna("_missing_").astype(str)
    te = s_test.fillna("_missing_").astype(str)
    tmp = pd.DataFrame({"c": tr.values, "y": y_train})
    glob = float(np.mean(y_train))
    means = tmp.groupby("c", observed=False)["y"].mean()
    tr_v = tr.map(lambda x: float(means.get(x, glob))).values.reshape(-1, 1)
    te_v = te.map(lambda x: float(means.get(x, glob))).values.reshape(-1, 1)
    return tr_v, te_v


def _encode_cat_train_test(
    s_train: pd.Series,
    s_test: pd.Series,
    enc: str,
    y_train: np.ndarray | None,
    task_type: str,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Returns blocks and list of feature names (one or many for one_hot)."""
    if enc == "binary":
        a, b = _binary_encode_pair(s_train, s_test)
        return a, b, [str(s_train.name)]
    if enc == "one_hot":
        a, b, names = _one_hot_pair(s_train, s_test)
        return a, b, names
    if enc == "label":
        a, b = _label_pair(s_train, s_test)
        return a, b, [str(s_train.name)]
    if enc == "frequency":
        a, b = _frequency_pair(s_train, s_test)
        return a, b, [str(s_train.name)]
    if enc == "target" and y_train is not None:
        a, b = _target_pair(s_train, s_test, y_train, task_type)
        return a, b, [str(s_train.name)]
    a, b = _label_pair(s_train, s_test)
    return a, b, [str(s_train.name)]


def build_encoded_dataframe(
    df: pd.DataFrame,
    schema_dict: dict,
    encoding_spec: dict[str, str],
    target: str | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply the encoding spec to the full dataset and return (encoded_df, summary).

    Unlike the train/test builders this does NOT scale — it returns raw encoded
    values so the user can inspect what each encoding does to their data.
    """
    value_cols = [c for c in schema_dict.get("value_columns", []) if c in df.columns]
    cat_cols = [c for c in schema_dict.get("category_columns", []) if c in df.columns]
    if target:
        value_cols = [c for c in value_cols if c != target]
        cat_cols = [c for c in cat_cols if c != target]

    spec = dict(encoding_spec)
    summary: list[dict] = []
    result_cols: dict[str, np.ndarray] = {}

    for col in value_cols:
        enc = spec.get(col, "none")
        if enc == "drop":
            summary.append({"column": col, "role": "numeric", "encoding": "drop", "output_columns": 0})
            continue
        s = df[col].copy()
        med = s.median()
        result_cols[col] = s.fillna(med).values.astype(float)
        summary.append({"column": col, "role": "numeric", "encoding": "none", "output_columns": 1})

    for col in cat_cols:
        enc = spec.get(col, "label")
        if enc == "drop":
            summary.append({"column": col, "role": "categorical", "encoding": "drop", "output_columns": 0})
            continue
        actual_enc = enc
        if enc == "target":
            actual_enc = "frequency"
        s = df[col].copy()
        arr, names = _encode_categorical_full_column(s, actual_enc)
        for i, n in enumerate(names):
            result_cols[n] = arr[:, i] if arr.ndim == 2 else arr.ravel()
        summary.append({
            "column": col, "role": "categorical", "encoding": enc,
            "output_columns": len(names),
            "new_columns": names if len(names) > 1 else None,
        })

    if target and target in df.columns:
        result_cols[f"_target_{target}"] = df[target].values

    encoded_df = pd.DataFrame(result_cols, index=df.index)
    return encoded_df, summary


def build_supervised_matrix(
    df: pd.DataFrame,
    target: str,
    task_type: str,
    num_cols: list[str],
    cat_cols: list[str],
    encoding_spec: dict[str, str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str] | None]:
    use_nums = [c for c in num_cols if encoding_spec.get(c, "none") != "drop"]
    use_cats = [c for c in cat_cols if encoding_spec.get(c, "label") != "drop"]
    use_cols = use_nums + use_cats
    if not use_cols:
        raise ValueError("No features after encoding drops")

    work = df[use_cols + [target]].copy()
    work = work[work[target].notna()]
    if len(work) < 10:
        raise ValueError("Too few rows with non-null target")

    idx = work.index.to_numpy()
    class_names: list[str] | None = None
    if task_type == "regression":
        y = work[target].values.astype(float)
        strat = None
    else:
        le_y = LabelEncoder()
        y = le_y.fit_transform(work[target].astype(str))
        class_names = le_y.classes_.tolist()
        strat = y

    idx_train, idx_test, y_train, y_test = train_test_split(
        idx, y, test_size=0.2, random_state=42, stratify=strat,
    )
    df_train = work.loc[idx_train]
    df_test = work.loc[idx_test]

    blocks_tr: list[np.ndarray] = []
    blocks_te: list[np.ndarray] = []
    names: list[str] = []

    for col in use_nums:
        enc = encoding_spec.get(col, "none")
        if enc == "drop":
            continue
        s_tr, s_te = df_train[col], df_test[col]
        med = s_tr.median()
        blocks_tr.append(s_tr.fillna(med).values.astype(float).reshape(-1, 1))
        blocks_te.append(s_te.fillna(med).values.astype(float).reshape(-1, 1))
        names.append(col)

    for col in use_cats:
        enc = encoding_spec.get(col, "label")
        if enc == "drop":
            continue
        s_tr, s_te = df_train[col], df_test[col]
        e = enc
        if e == "target" and y_train is None:
            e = "label"
        a, b, subnames = _encode_cat_train_test(s_tr, s_te, e, y_train, task_type)
        blocks_tr.append(a)
        blocks_te.append(b)
        names.extend(subnames)

    X_train = np.hstack(blocks_tr)
    X_test = np.hstack(blocks_te)
    X_train = np.nan_to_num(X_train, nan=0.0)
    X_test = np.nan_to_num(X_test, nan=0.0)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, names, class_names


def build_unsupervised_matrix(
    df: pd.DataFrame,
    num_cols: list[str],
    cat_cols: list[str],
    encoding_spec: dict[str, str],
) -> tuple[np.ndarray, list[str], pd.Index, list[str]]:
    notes: list[str] = []
    spec = dict(encoding_spec)
    for c in cat_cols:
        if spec.get(c) == "target":
            spec[c] = "frequency"
            notes.append(f"{c}: target encoding → frequency (unsupervised)")

    use_nums = [c for c in num_cols if spec.get(c, "none") != "drop"]
    use_cats = [c for c in cat_cols if spec.get(c, "label") != "drop"]
    use_cols = use_nums + use_cats
    if not use_cols:
        raise ValueError("No features for clustering after drops")

    work = df[use_cols].copy()
    blocks: list[np.ndarray] = []
    names: list[str] = []

    for col in use_nums:
        if spec.get(col, "none") == "drop":
            continue
        s = work[col]
        med = s.median()
        blocks.append(s.fillna(med).values.astype(float).reshape(-1, 1))
        names.append(col)

    for col in use_cats:
        enc = spec.get(col, "label")
        if enc == "drop":
            continue
        if enc == "target":
            enc = "frequency"
        s = work[col]
        # encode full column: train on first half, transform full via re-fit on all for frequency/label
        a, subn = _encode_categorical_full_column(s, enc)
        blocks.append(a)
        names.extend(subn)

    X = np.hstack(blocks)
    X = np.nan_to_num(X.astype(float), nan=0.0)
    row_idx = work.index
    if X.shape[0] < 10:
        raise ValueError(f"Only {X.shape[0]} rows — need at least 10 for PCA")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, names, row_idx, notes


def _binary_full_series(s: pd.Series) -> np.ndarray:
    yes = {"yes", "true", "1", "y", "t"}
    no = {"no", "false", "0", "n", "f"}

    def map_val(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v == 1:
                return 1.0
            if v == 0:
                return 0.0
        t = str(v).strip().lower()
        if t in yes:
            return 1.0
        if t in no:
            return 0.0
        return np.nan

    tr = s.map(map_val)
    fill = 0.0
    if tr.notna().any():
        fill = float(tr.mode().dropna().iloc[0]) if len(tr.mode().dropna()) else 0.0
    tr = tr.fillna(fill)
    if tr.nunique() <= 1:
        return tr.values.reshape(-1, 1)
    u = sorted(tr.unique())
    if len(u) == 2 and all(x in (0.0, 1.0) for x in u):
        return tr.values.reshape(-1, 1)
    le = LabelEncoder()
    v = le.fit_transform(s.fillna("_na_").astype(str)).astype(float)
    mx = max(v.max(), 1.0)
    return (v / mx).reshape(-1, 1)


def _encode_categorical_full_column(s: pd.Series, enc: str) -> tuple[np.ndarray, list[str]]:
    """Encode entire column (clustering — statistics from all rows)."""
    if enc == "binary":
        return _binary_full_series(s), [str(s.name)]

    if enc == "one_hot":
        tr = s.fillna("_missing_").astype(str)
        vc = tr.value_counts()
        cats = vc.index.tolist()[:MAX_ONE_HOT_LEVELS]
        if len(vc) > MAX_ONE_HOT_LEVELS:
            other = "_other_"
            tr = tr.where(tr.isin(cats), other)
            if other not in cats:
                cats = list(cats[: MAX_ONE_HOT_LEVELS - 1]) + [other]
        ncat = len(cats)
        cat_to_i = {c: i for i, c in enumerate(cats)}
        m = np.zeros((len(s), ncat), dtype=float)
        for i, v in enumerate(tr):
            j = cat_to_i.get(v, -1)
            if j >= 0:
                m[i, j] = 1.0
        names = [f"{s.name}={c}" for c in cats]
        return m, names

    if enc == "label":
        le = LabelEncoder()
        v = le.fit_transform(s.fillna("_missing_").astype(str)).astype(float)
        mx = max(v.max(), 1.0)
        return (v / mx).reshape(-1, 1), [str(s.name)]

    if enc == "frequency":
        tr = s.fillna("_missing_").astype(str)
        freq = tr.value_counts(normalize=True)
        default = 1.0 / max(len(tr), 1)
        v = tr.map(lambda x: float(freq.get(x, default))).values.reshape(-1, 1)
        return v, [str(s.name)]

    le = LabelEncoder()
    v = le.fit_transform(s.fillna("_missing_").astype(str)).astype(float)
    mx = max(v.max(), 1.0)
    return (v / mx).reshape(-1, 1), [str(s.name)]
