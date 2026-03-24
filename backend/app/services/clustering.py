"""PCA + K-Means clustering — numeric and optional encoded categorical features."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.models.schemas import DatasetSchema
from app.services.feature_encoding import (
    build_unsupervised_matrix,
    encoding_profile,
    merge_encoding_spec,
)


def _numeric_matrix(
    df: pd.DataFrame,
    schema: DatasetSchema,
    feature_columns: list[str] | None = None,
) -> tuple[np.ndarray, list[str], pd.Index]:
    """Legacy path: numeric columns only, scaled."""
    base = [c for c in schema.value_columns if c in df.columns]
    if feature_columns is not None:
        if len(feature_columns) == 0:
            raise ValueError("feature_columns cannot be empty — select at least one column")
        allowed = set(base)
        num_cols = [c for c in feature_columns if c in allowed]
        if not num_cols:
            raise ValueError("No valid numeric columns in feature_columns (must be schema value columns)")
    else:
        num_cols = base
    if not num_cols:
        raise ValueError("No numeric columns available for PCA")

    sub = df[num_cols].copy()
    sub = sub.replace([np.inf, -np.inf], np.nan)

    row_mask = sub.dropna().index
    clean = sub.loc[row_mask]
    if len(clean) < 10:
        raise ValueError(f"Only {len(clean)} complete rows — need at least 10 for PCA")

    scaler = StandardScaler()
    X = scaler.fit_transform(clean.values)
    return X, num_cols, row_mask


def _clustering_matrix(
    df: pd.DataFrame,
    schema: DatasetSchema,
    feature_columns: list[str] | None,
    encoding_spec: dict[str, str] | None,
) -> tuple[np.ndarray, list[str], pd.Index, list[str]]:
    """Build scaled design matrix; notes describe encoding fallbacks."""
    schema_dict = schema.model_dump()
    if feature_columns is None:
        X, cols, idx = _numeric_matrix(df, schema, None)
        return X, cols, idx, []

    nums = [c for c in feature_columns if c in df.columns and c in schema.value_columns]
    cats = [c for c in feature_columns if c in df.columns and c in schema.category_columns]

    if not cats:
        X, cols, idx = _numeric_matrix(df, schema, nums if nums else None)
        return X, cols, idx, []

    prof = encoding_profile(df, schema_dict, None)
    sub_prof = [c for c in prof["columns"] if c["name"] in feature_columns]
    spec = merge_encoding_spec(sub_prof, encoding_spec)
    return build_unsupervised_matrix(df, nums, cats, spec)


def compute_pca(
    df: pd.DataFrame,
    schema: DatasetSchema,
    n_components: int | None = None,
    feature_columns: list[str] | None = None,
    encoding_spec: dict[str, str] | None = None,
) -> dict:
    X, col_names, row_idx, notes = _clustering_matrix(df, schema, feature_columns, encoding_spec)
    max_possible = min(X.shape[0], X.shape[1])

    if n_components is None or n_components < 1:
        n_components = max_possible
    n_components = min(n_components, max_possible)

    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(X)

    explained = pca.explained_variance_ratio_.tolist()
    cumulative = np.cumsum(explained).tolist()

    knee = _find_elbow(explained)

    loadings = {}
    for i in range(X.shape[1]):
        col = col_names[i] if i < len(col_names) else f"f{i}"
        loadings[col] = [round(float(pca.components_[j][i]), 4) for j in range(n_components)]

    return {
        "n_components": n_components,
        "max_components": max_possible,
        "explained_variance": [round(v, 5) for v in explained],
        "cumulative_variance": [round(v, 5) for v in cumulative],
        "suggested_components": knee,
        "loadings": loadings,
        "coordinates": coords[:, :min(n_components, 10)].tolist(),
        "row_indices": row_idx.tolist(),
        "feature_names": col_names,
        "encoding_notes": notes,
    }


def _find_elbow(variance_ratios: list[float]) -> int:
    cumul = 0.0
    for i, v in enumerate(variance_ratios):
        cumul += v
        if cumul >= 0.80:
            return max(i + 1, 2)
    return max(len(variance_ratios), 2)


def suggest_k(
    df: pd.DataFrame,
    schema: DatasetSchema,
    n_components: int = 5,
    k_min: int = 2,
    k_max: int = 10,
    feature_columns: list[str] | None = None,
    encoding_spec: dict[str, str] | None = None,
) -> dict:
    X, _, _, _ = _clustering_matrix(df, schema, feature_columns, encoding_spec)
    max_comp = min(X.shape[0], X.shape[1], n_components)
    pca = PCA(n_components=max_comp)
    coords = pca.fit_transform(X)

    k_max = min(k_max, len(coords) - 1)
    if k_max < k_min:
        return {"scores": [], "suggested_k": 2}

    scores = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42, max_iter=300)
        labels = km.fit_predict(coords)
        sil = silhouette_score(coords, labels)
        scores.append({"k": k, "silhouette": round(float(sil), 4), "inertia": round(float(km.inertia_), 2)})

    best = max(scores, key=lambda s: s["silhouette"])
    return {"scores": scores, "suggested_k": best["k"]}


def compute_kmeans(
    df: pd.DataFrame,
    schema: DatasetSchema,
    n_components: int = 5,
    n_clusters: int = 3,
    feature_columns: list[str] | None = None,
    encoding_spec: dict[str, str] | None = None,
) -> dict:
    X, col_names, row_idx, _notes = _clustering_matrix(df, schema, feature_columns, encoding_spec)
    max_comp = min(X.shape[0], X.shape[1], n_components)
    pca = PCA(n_components=max_comp)
    coords = pca.fit_transform(X)

    n_clusters = max(2, min(n_clusters, len(coords) - 1))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42, max_iter=300)
    labels = km.fit_predict(coords)

    sil = silhouette_score(coords, labels) if n_clusters < len(coords) else 0.0

    pc1 = coords[:, 0].tolist()
    pc2 = coords[:, 1].tolist() if coords.shape[1] > 1 else [0.0] * len(pc1)

    target_col = schema.target_column
    target_vals = None
    if target_col and target_col in df.columns:
        target_vals = df.loc[row_idx, target_col].astype(str).tolist()

    cluster_summary = []
    for c in range(n_clusters):
        mask = labels == c
        size = int(mask.sum())
        centroid = coords[mask].mean(axis=0)[:5].tolist()
        summary = {"cluster": c, "size": size, "centroid_pc": [round(v, 3) for v in centroid]}

        if target_vals:
            cluster_targets = [target_vals[i] for i in range(len(target_vals)) if mask[i]]
            from collections import Counter
            dist = Counter(cluster_targets)
            summary["target_distribution"] = dict(dist.most_common(5))

        cluster_summary.append(summary)

    explained = pca.explained_variance_ratio_[:2]
    pc1_label = f"PC1 ({explained[0]*100:.1f}%)"
    pc2_label = f"PC2 ({explained[1]*100:.1f}%)" if len(explained) > 1 else "PC2"

    return {
        "n_clusters": n_clusters,
        "n_components_used": max_comp,
        "silhouette_score": round(float(sil), 4),
        "labels": labels.tolist(),
        "pc1": pc1,
        "pc2": pc2,
        "pc1_label": pc1_label,
        "pc2_label": pc2_label,
        "target_values": target_vals,
        "cluster_summary": cluster_summary,
        "feature_names": col_names,
    }
