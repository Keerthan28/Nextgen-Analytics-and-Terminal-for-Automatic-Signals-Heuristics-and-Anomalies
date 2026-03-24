"""Machine Learning service — classification + regression with user-configurable columns/models.

Supports: Logistic Regression, Random Forest, Gradient Boosting (classification)
          Linear Regression, Ridge, SVR, RF Regressor, GB Regressor (regression)
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from collections import Counter

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.svm import SVR
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    RandomForestRegressor, GradientBoostingRegressor,
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    mean_squared_error, mean_absolute_error, r2_score,
)

from app.models.schemas import DatasetSchema
from app.services.feature_encoding import (
    build_supervised_matrix,
    encoding_profile,
    merge_encoding_spec,
)

logger = logging.getLogger(__name__)

CLASSIFICATION_MODELS = {
    "logistic_regression": {
        "name": "Logistic Regression", "cls": LogisticRegression,
        "params": {"max_iter": 1000, "random_state": 42, "n_jobs": -1},
    },
    "random_forest": {
        "name": "Random Forest", "cls": RandomForestClassifier,
        "params": {"n_estimators": 100, "max_depth": 10, "random_state": 42, "n_jobs": -1},
    },
    "gradient_boosting": {
        "name": "Gradient Boosting", "cls": GradientBoostingClassifier,
        "params": {"n_estimators": 100, "max_depth": 5, "random_state": 42, "learning_rate": 0.1},
    },
}

REGRESSION_MODELS = {
    "linear_regression": {
        "name": "Linear Regression", "cls": LinearRegression,
        "params": {"n_jobs": -1},
    },
    "ridge_regression": {
        "name": "Ridge Regression", "cls": Ridge,
        "params": {"alpha": 1.0, "random_state": 42},
    },
    "random_forest_regressor": {
        "name": "Random Forest Regressor", "cls": RandomForestRegressor,
        "params": {"n_estimators": 100, "max_depth": 10, "random_state": 42, "n_jobs": -1},
    },
    "gradient_boosting_regressor": {
        "name": "Gradient Boosting Regressor", "cls": GradientBoostingRegressor,
        "params": {"n_estimators": 100, "max_depth": 5, "random_state": 42, "learning_rate": 0.1},
    },
}

ALL_MODELS = {**CLASSIFICATION_MODELS, **REGRESSION_MODELS}


def _detect_leakage(df: pd.DataFrame, target: str, num_cols: list[str], cat_cols: list[str]) -> list[str]:
    """Detect columns that are direct proxies of the target (data leakage)."""
    leaky = set()
    if not target or target not in df.columns:
        return []

    target_words = set(target.lower().replace("_", " ").replace("-", " ").split())
    leak_suffixes = {"value", "score", "label", "flag", "category", "reason", "status",
                     "indicator", "class", "type", "result", "outcome"}

    for col in num_cols + cat_cols:
        col_words = set(col.lower().replace("_", " ").replace("-", " ").split())
        overlap = target_words & col_words - leak_suffixes
        if overlap and len(overlap) >= 1:
            remaining = col_words - target_words
            if not remaining or remaining <= leak_suffixes:
                leaky.add(col)
                continue

    for col in cat_cols:
        if col in leaky:
            continue
        try:
            mapping = df.groupby(col)[target].nunique()
            if mapping.max() == 1 and df[col].nunique() <= df[target].nunique() * 5:
                leaky.add(col)
                continue
        except Exception:
            pass
        try:
            null_rates = df.groupby(target)[col].apply(lambda s: s.isna().mean())
            if null_rates.max() - null_rates.min() > 0.70:
                leaky.add(col)
        except Exception:
            pass

    for col in num_cols:
        if col in leaky:
            continue
        try:
            null_rates = df.groupby(target)[col].apply(lambda s: s.isna().mean())
            if null_rates.max() - null_rates.min() > 0.70:
                leaky.add(col)
        except Exception:
            pass

    le = LabelEncoder()
    try:
        y = le.fit_transform(df[target].dropna().astype(str))
    except Exception:
        return sorted(leaky)

    for col in num_cols:
        if col in leaky:
            continue
        try:
            valid = df[target].notna() & df[col].notna()
            x = df.loc[valid, col].values.astype(float)
            y_sub = le.transform(df.loc[valid, target].astype(str))
            corr = abs(np.corrcoef(x, y_sub)[0, 1])
            if corr > 0.90:
                leaky.add(col)
        except Exception:
            pass

    for col in cat_cols:
        if col in leaky:
            continue
        try:
            valid = df[target].notna() & df[col].notna()
            le_col = LabelEncoder()
            x = le_col.fit_transform(df.loc[valid, col].astype(str))
            y_sub = le.transform(df.loc[valid, target].astype(str))
            corr = abs(np.corrcoef(x, y_sub)[0, 1])
            if corr > 0.90:
                leaky.add(col)
        except Exception:
            pass

    return sorted(leaky)


def _detect_task_type(df: pd.DataFrame, target: str) -> str:
    """Heuristic: classification if target is categorical or low-cardinality, else regression."""
    if target not in df.columns:
        return "classification"
    col = df[target].dropna()
    if col.dtype == object or str(col.dtype) == "category":
        return "classification"
    nunique = col.nunique()
    if nunique <= 20:
        return "classification"
    return "regression"


def preliminary_analysis(
    df: pd.DataFrame,
    schema: DatasetSchema,
    target_override: str | None = None,
    task_type_override: str | None = None,
    exclude_cols: list[str] | None = None,
) -> dict:
    """Quick data quality + ML readiness check. Accepts user overrides."""
    target = target_override or schema.target_column
    num_cols = [c for c in schema.value_columns if c in df.columns and c != target]
    cat_cols = [c for c in schema.category_columns if c in df.columns and c != target]

    if exclude_cols:
        exclude_set = set(exclude_cols)
        num_cols = [c for c in num_cols if c not in exclude_set]
        cat_cols = [c for c in cat_cols if c not in exclude_set]

    task_type = task_type_override or _detect_task_type(df, target)

    all_columns = schema.value_columns + schema.category_columns
    all_columns = [c for c in all_columns if c != target]

    result = {
        "rows": len(df),
        "numeric_features": len(num_cols),
        "categorical_features": len(cat_cols),
        "total_features": len(num_cols) + len(cat_cols),
        "target_column": target,
        "target_detected": target is not None,
        "task_type": task_type,
        "all_columns": sorted(set(all_columns)),
        "excluded_by_user": exclude_cols or [],
        "issues": [],
        "recommendations": [],
    }

    if not target or target not in df.columns:
        result["issues"].append("No target column detected — cannot train supervised models")
        result["recommendations"].append("Select a target column")
        result["ready"] = False
        return result

    target_vals = df[target].dropna()

    if task_type == "classification":
        n_classes = target_vals.nunique()
        result["n_classes"] = n_classes
        result["class_distribution"] = dict(Counter(target_vals.astype(str).tolist()).most_common(10))

        if n_classes < 2:
            result["issues"].append(f"Target has only {n_classes} unique value(s) — need at least 2")
        elif n_classes > 50:
            result["issues"].append(f"Target has {n_classes} classes — consider regression or grouping")

        minority_pct = target_vals.value_counts(normalize=True).min() * 100
        result["minority_class_pct"] = round(minority_pct, 1)
        if minority_pct < 10:
            result["issues"].append(f"Class imbalance: minority at {minority_pct:.1f}%")
    else:
        result["target_stats"] = {
            "mean": round(float(target_vals.mean()), 4),
            "std": round(float(target_vals.std()), 4),
            "min": round(float(target_vals.min()), 4),
            "max": round(float(target_vals.max()), 4),
        }

    missing_pct = df[num_cols + cat_cols].isnull().mean() * 100
    high_missing = missing_pct[missing_pct > 30]
    result["missing_summary"] = {col: round(pct, 1) for col, pct in missing_pct.items() if pct > 0}
    if len(high_missing) > 0:
        result["issues"].append(f"{len(high_missing)} feature(s) have >30% missing data")

    leaky = _detect_leakage(df, target, num_cols, cat_cols)
    result["leakage_columns"] = leaky
    if leaky:
        result["issues"].append(f"Data leakage detected: {', '.join(leaky)}")
        result["total_features"] -= len(leaky)

    result["ready"] = len([i for i in result["issues"] if "cannot train" in i.lower() or "need at least" in i.lower()]) == 0

    if task_type == "classification":
        result["available_models"] = list(CLASSIFICATION_MODELS.keys())
    else:
        result["available_models"] = list(REGRESSION_MODELS.keys())

    return result


def _prepare_data(
    df: pd.DataFrame,
    schema: DatasetSchema,
    target: str,
    task_type: str,
    include_cols: list[str] | None = None,
    exclude_cols: list[str] | None = None,
) -> tuple:
    """Encode features, handle missing data, split train/test."""
    all_num = [c for c in schema.value_columns if c in df.columns and c != target]
    all_cat = [c for c in schema.category_columns if c in df.columns and c != target]

    if include_cols is not None:
        include_set = set(include_cols)
        all_num = [c for c in all_num if c in include_set]
        all_cat = [c for c in all_cat if c in include_set]

    exclude_set = set(exclude_cols or [])
    leaky = set(_detect_leakage(df, target, all_num, all_cat))
    drop = exclude_set | leaky

    num_cols = [c for c in all_num if c not in drop]
    cat_cols = [c for c in all_cat if c not in drop]

    if drop:
        logger.info(f"Excluded columns: {drop}")

    feature_names = []
    frames = []

    if num_cols:
        num_df = df[num_cols].copy()
        for col in num_cols:
            num_df[col] = num_df[col].fillna(num_df[col].median())
        frames.append(num_df)
        feature_names.extend(num_cols)

    if cat_cols:
        cat_df = df[cat_cols].copy()
        for col in cat_cols:
            mode_val = cat_df[col].mode()
            cat_df[col] = cat_df[col].fillna(mode_val.iloc[0] if len(mode_val) > 0 else "missing")
            le = LabelEncoder()
            cat_df[col] = le.fit_transform(cat_df[col].astype(str))
        frames.append(cat_df)
        feature_names.extend(cat_cols)

    if not frames:
        raise ValueError("No features available for modeling")

    X = pd.concat(frames, axis=1).values
    valid_mask = ~np.isnan(X).any(axis=1) & df[target].notna().values
    X = X[valid_mask]

    if task_type == "regression":
        y = df[target].values[valid_mask].astype(float)
        class_names = None
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
        )
    else:
        y_raw = df[target].values[valid_mask]
        le_target = LabelEncoder()
        y = le_target.fit_transform(y_raw.astype(str))
        class_names = le_target.classes_.tolist()
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

    return X_train, X_test, y_train, y_test, feature_names, class_names


def _prepare_data_encoded(
    df: pd.DataFrame,
    schema: DatasetSchema,
    target: str,
    task_type: str,
    num_cols: list[str],
    cat_cols: list[str],
    encoding_spec: dict[str, str],
) -> tuple:
    prof = encoding_profile(df, schema.model_dump(), target)
    sub_prof = [c for c in prof["columns"] if c["name"] in num_cols + cat_cols]
    spec = merge_encoding_spec(sub_prof, encoding_spec)
    return build_supervised_matrix(df, target, task_type, num_cols, cat_cols, spec)


def train_model(
    df: pd.DataFrame,
    schema: DatasetSchema,
    model_type: str = "random_forest",
    target: str | None = None,
    task_type: str | None = None,
    include_cols: list[str] | None = None,
    exclude_cols: list[str] | None = None,
    encoding_spec: dict[str, str] | None = None,
) -> dict:
    """Train a single model with user-configurable params."""
    target = target or schema.target_column
    if not target or target not in df.columns:
        raise ValueError(f"Target column '{target}' not found")

    task_type = task_type or _detect_task_type(df, target)
    model_pool = CLASSIFICATION_MODELS if task_type == "classification" else REGRESSION_MODELS

    if model_type not in model_pool:
        raise ValueError(f"Model '{model_type}' not valid for {task_type}. Choose: {list(model_pool.keys())}")

    if encoding_spec is not None:
        all_num = [c for c in schema.value_columns if c in df.columns and c != target]
        all_cat = [c for c in schema.category_columns if c in df.columns and c != target]
        if include_cols is not None:
            inc = set(include_cols)
            all_num = [c for c in all_num if c in inc]
            all_cat = [c for c in all_cat if c in inc]
        exclude_set = set(exclude_cols or [])
        leaky = set(_detect_leakage(df, target, all_num, all_cat))
        num_cols = [c for c in all_num if c not in exclude_set and c not in leaky]
        cat_cols = [c for c in all_cat if c not in exclude_set and c not in leaky]
        X_train, X_test, y_train, y_test, feature_names, class_names = _prepare_data_encoded(
            df, schema, target, task_type, num_cols, cat_cols, encoding_spec,
        )
    else:
        X_train, X_test, y_train, y_test, feature_names, class_names = _prepare_data(
            df, schema, target, task_type, include_cols, exclude_cols,
        )

    spec = model_pool[model_type]
    model = spec["cls"](**spec["params"])
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    importances = _get_feature_importance(model, feature_names)

    base = {
        "model_type": model_type,
        "model_name": spec["name"],
        "task_type": task_type,
        "target_column": target,
        "feature_importance": importances,
        "train_size": len(y_train),
        "test_size": len(y_test),
        "features_used": feature_names,
    }

    if task_type == "classification":
        base.update(_classification_metrics(model, spec, X_train, X_test, y_train, y_test, y_pred, class_names))
    else:
        base.update(_regression_metrics(model, spec, X_train, y_train, y_test, y_pred))

    return base


def _classification_metrics(model, spec, X_train, X_test, y_train, y_test, y_pred, class_names):
    is_binary = len(class_names) == 2
    avg = "binary" if is_binary else "weighted"

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, average=avg, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, average=avg, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, average=avg, zero_division=0)), 4),
    }

    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)
        try:
            if is_binary:
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_proba[:, 1])), 4)
            else:
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")), 4)
        except ValueError:
            metrics["roc_auc"] = None

    cv = cross_val_score(spec["cls"](**spec["params"]), X_train, y_train, cv=5, scoring="accuracy")
    metrics["cv_mean"] = round(float(cv.mean()), 4)
    metrics["cv_std"] = round(float(cv.std()), 4)

    cm = confusion_matrix(y_test, y_pred)

    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True, zero_division=0)
    per_class = {}
    for cls_name in class_names:
        if cls_name in report:
            per_class[cls_name] = {
                "precision": round(report[cls_name]["precision"], 4),
                "recall": round(report[cls_name]["recall"], 4),
                "f1": round(report[cls_name]["f1-score"], 4),
                "support": int(report[cls_name]["support"]),
            }

    return {
        "metrics": metrics,
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
        "per_class_metrics": per_class,
    }


def _regression_metrics(model, spec, X_train, y_train, y_test, y_pred):
    mse = mean_squared_error(y_test, y_pred)
    metrics = {
        "r2": round(float(r2_score(y_test, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
        "rmse": round(float(np.sqrt(mse)), 4),
        "mse": round(float(mse), 4),
    }

    scoring = "r2"
    cv = cross_val_score(spec["cls"](**spec["params"]), X_train, y_train, cv=5, scoring=scoring)
    metrics["cv_mean"] = round(float(cv.mean()), 4)
    metrics["cv_std"] = round(float(cv.std()), 4)

    residuals = (y_test - y_pred).tolist()
    return {
        "metrics": metrics,
        "residuals": residuals[:500],
        "y_test": y_test.tolist()[:500],
        "y_pred": y_pred.tolist()[:500],
    }


def train_selected_models(
    df: pd.DataFrame,
    schema: DatasetSchema,
    model_types: list[str],
    target: str | None = None,
    task_type: str | None = None,
    include_cols: list[str] | None = None,
    exclude_cols: list[str] | None = None,
    encoding_spec: dict[str, str] | None = None,
) -> dict:
    """Train user-selected models."""
    target = target or schema.target_column
    task_type = task_type or _detect_task_type(df, target)

    results = {}
    for mt in model_types:
        try:
            results[mt] = train_model(
                df, schema, mt, target, task_type, include_cols, exclude_cols, encoding_spec,
            )
        except Exception as e:
            logger.error(f"Failed to train {mt}: {e}")
            results[mt] = {"model_type": mt, "error": str(e)}

    best = None
    best_score = -999
    score_key = "f1" if task_type == "classification" else "r2"
    for name, r in results.items():
        s = r.get("metrics", {}).get(score_key, -999)
        if s > best_score:
            best_score = s
            best = name

    return {"models": results, "best_model": best, "task_type": task_type}


def _get_feature_importance(model, feature_names: list[str]) -> list[dict]:
    if hasattr(model, "feature_importances_"):
        raw = model.feature_importances_
    elif hasattr(model, "coef_"):
        raw = np.abs(model.coef_).mean(axis=0) if model.coef_.ndim > 1 else np.abs(model.coef_.flatten())
    else:
        return []

    if raw.sum() == 0:
        return []

    pairs = sorted(zip(feature_names, raw), key=lambda x: -x[1])
    return [{"feature": name, "importance": round(float(imp), 5)} for name, imp in pairs[:20]]
