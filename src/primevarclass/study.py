from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from .core import (
    run_experiment_suite,
    run_gene_stratified_experiments,
    run_repeated_holdout_experiment_suite,
    save_trained_models,
    train_model_with_feature_subset,
)
from .baseline_coverage import export_baseline_coverage_assessment
from .claim_strength import export_claim_strength_package
from .cohort_freeze import export_study_cohort_freeze
from .cohort_validation import export_cohort_independence_package
from .comparative_evidence import export_comparative_evidence_package
from .data_sources import build_dataset_from_source_config
from .external_robustness import export_external_robustness_package
from .manuscript_package import export_manuscript_package
from .methods_package import export_methods_package
from .prime_intelligence import export_prime_intelligence_package
from .publication_readiness import export_publication_readiness_package
from .reports import export_study_scientific_dossier
from .validation_lock import export_study_validation_lock
from .versioning import export_study_release_manifest


@dataclass
class StudyCohortSpec:
    name: str
    role: str
    source_config: str
    mode: str | None = None
    high_confidence_only: bool | None = None


@dataclass
class StudyDesign:
    name: str
    mode: str = "hybrid"
    keep_metadata: bool = True
    high_confidence_only: bool = False
    primary_metric: str = "auc_roc"
    baseline_experiment: str = "external_predictors_only"
    n_bootstrap: int = 200
    model_families: List[str] | None = None
    consensus_top_k: int = 3
    cohorts: List[StudyCohortSpec] | None = None


def _slugify(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_").lower()
    return text or "study"


def _normalize_role(value: str | None) -> str:
    role = str(value or "external_test").strip().lower()
    aliases = {
        "train": "train",
        "training": "train",
        "dev": "validation",
        "validation": "validation",
        "external": "external_test",
        "external_validation": "external_test",
        "external_test": "external_test",
        "test": "external_test",
    }
    if role not in aliases:
        raise ValueError(f"Role de coorte nao suportado: {value}")
    return aliases[role]


def load_study_design(config_path: str) -> StudyDesign:
    with open(config_path, "rb") as handle:
        raw = tomllib.load(handle)

    study_payload = raw.get("study", {})
    cohort_payload = raw.get("cohorts", [])
    if not cohort_payload:
        raise ValueError("O arquivo de estudo precisa conter pelo menos uma entrada em [[cohorts]].")

    cohorts = [
        StudyCohortSpec(
            name=str(item["name"]),
            role=_normalize_role(item.get("role")),
            source_config=str(item["source_config"]),
            mode=item.get("mode"),
            high_confidence_only=item.get("high_confidence_only"),
        )
        for item in cohort_payload
    ]

    return StudyDesign(
        name=str(study_payload.get("name", Path(config_path).stem)),
        mode=str(study_payload.get("mode", "hybrid")),
        keep_metadata=bool(study_payload.get("keep_metadata", True)),
        high_confidence_only=bool(study_payload.get("high_confidence_only", False)),
        primary_metric=str(study_payload.get("primary_metric", "auc_roc")),
        baseline_experiment=str(study_payload.get("baseline_experiment", "external_predictors_only")),
        n_bootstrap=int(study_payload.get("n_bootstrap", 200)),
        model_families=list(study_payload.get("model_families", [])) or None,
        consensus_top_k=int(study_payload.get("consensus_top_k", 3)),
        cohorts=cohorts,
    )


def _resolve_cohort_mode(study: StudyDesign, cohort: StudyCohortSpec) -> str:
    return str(cohort.mode or study.mode)


def _resolve_cohort_high_confidence(study: StudyDesign, cohort: StudyCohortSpec) -> bool:
    return bool(study.high_confidence_only if cohort.high_confidence_only is None else cohort.high_confidence_only)


def _safe_auc_roc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else float("nan")


def _safe_auc_pr(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(average_precision_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else float("nan")


def _metric_from_name(metric_name: str, y_true: np.ndarray, y_score: np.ndarray) -> float:
    if metric_name == "auc_roc":
        return _safe_auc_roc(y_true, y_score)
    if metric_name == "auc_pr":
        return _safe_auc_pr(y_true, y_score)
    raise ValueError(f"Metrica de bootstrap nao suportada: {metric_name}")


def _classification_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5) -> dict:
    preds = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, preds, labels=[0, 1]).ravel()
    return {
        "auc_roc": _safe_auc_roc(y_true, y_score),
        "auc_pr": _safe_auc_pr(y_true, y_score),
        "accuracy": float(accuracy_score(y_true, preds)),
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else np.nan,
        "mcc": float(matthews_corrcoef(y_true, preds)) if len(np.unique(y_true)) == 2 else np.nan,
        "precision_at_0_5": tp / (tp + fp) if (tp + fp) > 0 else np.nan,
        "recall_at_0_5": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "n_variants": int(len(y_true)),
    }


def _align_features_for_prediction(df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    aligned = df.copy()
    for column in feature_columns:
        if column not in aligned.columns:
            aligned[column] = np.nan
    return aligned[feature_columns].copy()


def predict_scores_for_experiment(pipeline, df: pd.DataFrame, feature_columns: List[str]) -> np.ndarray:
    X = _align_features_for_prediction(df, feature_columns)
    return pipeline.predict_proba(X)[:, 1]


def _parse_experiment_metadata(experiment_name: str) -> tuple[str, str, int]:
    if "__" not in experiment_name:
        return experiment_name, "random_forest", 1
    feature_set, model_family = experiment_name.split("__", 1)
    return feature_set, model_family, 0


def _sort_experiment_metrics(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return table
    sort_columns = [col for col in ["cohort", "evaluation_group", "auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"] if col in table.columns]
    ascending_map = {
        "cohort": True,
        "evaluation_group": True,
        "auc_roc": False,
        "auc_pr": False,
        "mcc": False,
        "is_primary_experiment": False,
        "experiment": True,
    }
    ascending = [ascending_map[col] for col in sort_columns]
    return table.sort_values(sort_columns, ascending=ascending).reset_index(drop=True)


def _balanced_gene_score(row: pd.Series, primary_metric: str = "auc_roc") -> float:
    auc_roc = float(row.get("auc_roc", np.nan))
    auc_pr = float(row.get("auc_pr", np.nan))
    mcc = float(row.get("mcc", np.nan))
    safe_mcc = max(0.0, mcc) if not np.isnan(mcc) else 0.0
    primary_value = float(row.get(primary_metric, auc_roc)) if primary_metric in row.index else auc_roc
    values = [primary_value, auc_roc, auc_pr, safe_mcc]
    valid = [value for value in values if not np.isnan(value)]
    return float(np.mean(valid)) if valid else float("nan")


def _robust_blend_score(row: pd.Series | dict[str, Any], brier_loss: float) -> float:
    auc_roc = float(row.get("auc_roc", np.nan))
    auc_pr = float(row.get("auc_pr", np.nan))
    mcc = float(row.get("mcc", np.nan))
    safe_mcc = max(0.0, mcc) if not np.isnan(mcc) else 0.0
    calibration_score = 1.0 - min(max(float(brier_loss), 0.0), 1.0)
    values = [auc_roc, auc_pr, safe_mcc, calibration_score]
    valid = [value for value in values if not np.isnan(value)]
    return float(np.mean(valid)) if valid else float("nan")


def _is_prime_like_experiment(experiment_name: str) -> bool:
    feature_set = _parse_experiment_metadata(str(experiment_name))[0]
    token = str(feature_set).strip().lower()
    return token.startswith("prime") or token.startswith("hybrid")


def _resolve_stratified_folds(labels: pd.Series, maximum: int = 5) -> int:
    counts = labels.astype(int).value_counts()
    if len(counts) < 2:
        return 0
    return max(2, min(int(counts.min()), int(maximum)))


def _supports_local_gene_training(df: pd.DataFrame) -> bool:
    if df.empty or "label" not in df.columns:
        return False
    counts = df["label"].astype(int).value_counts()
    if len(counts) < 2:
        return False
    return int(counts.min()) >= 2


def _compute_oof_scores(
    df: pd.DataFrame,
    feature_columns: List[str],
    model_family: str,
    random_state: int = 42,
) -> np.ndarray:
    X = _align_features_for_prediction(df, feature_columns)
    y = df["label"].astype(int)
    n_splits = _resolve_stratified_folds(y)
    if n_splits < 2:
        model, _ = train_model_with_feature_subset(df, feature_columns, model_family=model_family)
        return predict_scores_for_experiment(model, df, feature_columns)
    estimator, _ = train_model_with_feature_subset(df, feature_columns, model_family=model_family)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    return cross_val_predict(
        clone(estimator),
        X,
        y,
        cv=cv,
        method="predict_proba",
    )[:, 1]


def _fit_score_calibrator(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float | str]:
    labels = np.asarray(y_true, dtype=int)
    scores = np.clip(np.asarray(y_score, dtype=float), 1e-6, 1 - 1e-6)
    if len(labels) == 0 or len(np.unique(labels)) < 2 or np.allclose(scores, scores[0]):
        return {"kind": "identity", "slope": 1.0, "intercept": 0.0}
    calibrator = LogisticRegression(
        class_weight="balanced",
        solver="liblinear",
        random_state=42,
    )
    calibrator.fit(scores.reshape(-1, 1), labels)
    return {
        "kind": "logistic",
        "slope": float(calibrator.coef_[0][0]),
        "intercept": float(calibrator.intercept_[0]),
    }


def _apply_score_calibrator(y_score: np.ndarray, calibrator: dict[str, float | str] | None) -> np.ndarray:
    scores = np.clip(np.asarray(y_score, dtype=float), 1e-6, 1 - 1e-6)
    payload = dict(calibrator or {})
    kind = str(payload.get("kind") or "identity").strip().lower()
    if kind != "logistic":
        return scores
    slope = float(payload.get("slope") or 1.0)
    intercept = float(payload.get("intercept") or 0.0)
    linear = intercept + (slope * scores)
    calibrated = 1.0 / (1.0 + np.exp(-linear))
    return np.clip(calibrated, 1e-6, 1 - 1e-6)


def build_gene_specialist_manifest(
    gene_training_metrics: Dict[str, pd.DataFrame],
    train_df: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_training_metrics: pd.DataFrame | None = None,
    primary_metric: str = "auc_roc",
    experiment_name: str = "gene_balanced_specialist",
) -> pd.DataFrame:
    rows: List[dict] = []
    global_metrics = global_training_metrics.copy() if isinstance(global_training_metrics, pd.DataFrame) else pd.DataFrame()
    gene_names = sorted({str(gene_name) for gene_name in train_df.get("gene", pd.Series(dtype=str)).dropna().astype(str)})
    for gene_name in gene_names:
        metrics_df = gene_training_metrics.get(gene_name)
        subset = train_df[train_df["gene"].astype(str) == str(gene_name)].copy() if "gene" in train_df.columns else pd.DataFrame()
        if subset.empty or subset["label"].nunique() < 2:
            continue

        use_local_training = _supports_local_gene_training(subset)
        ranked = metrics_df.copy() if isinstance(metrics_df, pd.DataFrame) and use_local_training else global_metrics.copy()
        if ranked.empty:
            continue
        ranked["balanced_internal_score"] = ranked.apply(
            lambda row: _balanced_gene_score(row, primary_metric=primary_metric),
            axis=1,
        )
        metric_name = primary_metric if primary_metric in ranked.columns else "auc_roc"
        ranked = ranked.sort_values(
            ["balanced_internal_score", metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, False, True],
        ).reset_index(drop=True)
        best_row = ranked.iloc[0]
        selected_experiment = str(best_row["experiment"])
        rows.append(
            {
                "gene": str(gene_name),
                "specialist_experiment": experiment_name,
                "selected_experiment": selected_experiment,
                "feature_set": str(best_row.get("feature_set") or _parse_experiment_metadata(selected_experiment)[0]),
                "model_family": str(best_row.get("model_family") or _parse_experiment_metadata(selected_experiment)[1]),
                "training_origin": "gene_local" if use_local_training else "global_fallback",
                "balanced_internal_score": float(best_row.get("balanced_internal_score", np.nan)),
                "auc_roc": float(best_row.get("auc_roc", np.nan)),
                "auc_pr": float(best_row.get("auc_pr", np.nan)),
                "mcc": float(best_row.get("mcc", np.nan)),
                "n_variants": int(len(subset)),
                "n_features": int(len(feature_sets.get(selected_experiment, []))),
            }
        )
    manifest = pd.DataFrame(rows)
    if not manifest.empty:
        manifest = manifest.sort_values(["gene"], ascending=[True]).reset_index(drop=True)
    return manifest


def train_gene_specialist_models(
    train_df: pd.DataFrame,
    specialist_manifest: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_trained_models: Dict[str, object] | None = None,
) -> Dict[str, dict]:
    trained: Dict[str, dict] = {}
    if specialist_manifest.empty:
        return trained
    global_models = dict(global_trained_models or {})

    for row in specialist_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        selected_experiment = str(row.get("selected_experiment") or "")
        if not gene_name or not selected_experiment:
            continue
        feature_columns = feature_sets.get(selected_experiment, [])
        if not feature_columns:
            continue
        gene_subset = train_df[train_df["gene"].astype(str) == gene_name].copy()
        if gene_subset.empty or gene_subset["label"].nunique() < 2:
            continue
        model_family = str(row.get("model_family") or _parse_experiment_metadata(selected_experiment)[1])
        if _supports_local_gene_training(gene_subset):
            pipeline, metrics = train_model_with_feature_subset(
                gene_subset,
                feature_columns,
                model_family=model_family,
            )
            training_origin = "gene_local"
        else:
            pipeline = global_models.get(selected_experiment)
            if pipeline is None:
                continue
            metrics = {
                "auc_roc": float(row.get("auc_roc", np.nan)),
                "auc_pr": float(row.get("auc_pr", np.nan)),
                "mcc": float(row.get("mcc", np.nan)),
                "cv_folds": 0,
                "model_family": model_family,
            }
            training_origin = "global_fallback"
        trained[gene_name] = {
            "pipeline": pipeline,
            "feature_columns": list(feature_columns),
            "selected_experiment": selected_experiment,
            "model_family": model_family,
            "training_origin": training_origin,
            "training_metrics": metrics,
        }
    return trained


def build_gene_adaptive_blend_manifest(
    gene_training_metrics: Dict[str, pd.DataFrame],
    train_df: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_training_metrics: pd.DataFrame | None = None,
    primary_metric: str = "auc_roc",
    baseline_experiment: str = "external_predictors_only",
    experiment_name: str = "hybrid_external_gene_adaptive_blend",
    optimization_mode: str = "balanced",
) -> pd.DataFrame:
    rows: List[dict] = []
    gene_names = (
        sorted(train_df["gene"].astype(str).dropna().unique().tolist())
        if "gene" in train_df.columns
        else []
    )
    for gene_name in gene_names:
        metrics_df = gene_training_metrics.get(str(gene_name))
        subset = train_df[train_df["gene"].astype(str) == str(gene_name)].copy() if "gene" in train_df.columns else pd.DataFrame()
        if subset.empty or subset["label"].nunique() < 2:
            continue

        ranked_source = metrics_df if isinstance(metrics_df, pd.DataFrame) and not metrics_df.empty else global_training_metrics
        selection_origin = "local_gene_metrics" if ranked_source is metrics_df else "global_fallback"
        if not isinstance(ranked_source, pd.DataFrame) or ranked_source.empty:
            continue

        ranked = ranked_source.copy()
        ranked["balanced_internal_score"] = ranked.apply(
            lambda row: _balanced_gene_score(row, primary_metric=primary_metric),
            axis=1,
        )
        baseline_rows = ranked[ranked["experiment"].astype(str) == str(baseline_experiment)].copy()
        prime_rows = ranked[ranked["experiment"].astype(str).map(_is_prime_like_experiment)].copy()
        if (baseline_rows.empty or prime_rows.empty) and selection_origin != "global_fallback" and isinstance(global_training_metrics, pd.DataFrame) and not global_training_metrics.empty:
            ranked = global_training_metrics.copy()
            ranked["balanced_internal_score"] = ranked.apply(
                lambda row: _balanced_gene_score(row, primary_metric=primary_metric),
                axis=1,
            )
            baseline_rows = ranked[ranked["experiment"].astype(str) == str(baseline_experiment)].copy()
            prime_rows = ranked[ranked["experiment"].astype(str).map(_is_prime_like_experiment)].copy()
            selection_origin = "global_fallback"
        if baseline_rows.empty or prime_rows.empty:
            continue

        metric_name = primary_metric if primary_metric in ranked.columns else "auc_roc"
        baseline_row = baseline_rows.sort_values(
            ["balanced_internal_score", metric_name, "auc_pr", "mcc", "experiment"],
            ascending=[False, False, False, False, True],
        ).iloc[0]
        prime_row = prime_rows.sort_values(
            ["balanced_internal_score", metric_name, "auc_pr", "mcc", "experiment"],
            ascending=[False, False, False, False, True],
        ).iloc[0]

        baseline_name = str(baseline_row["experiment"])
        prime_name = str(prime_row["experiment"])
        baseline_cols = feature_sets.get(baseline_name, [])
        prime_cols = feature_sets.get(prime_name, [])
        if not baseline_cols or not prime_cols:
            continue

        scoring_df = subset.copy()
        if not _supports_local_gene_training(subset):
            if selection_origin == "global_fallback" and _supports_local_gene_training(train_df):
                scoring_df = train_df.copy()
            else:
                continue

        baseline_scores = _compute_oof_scores(
            scoring_df,
            baseline_cols,
            model_family=str(baseline_row.get("model_family") or _parse_experiment_metadata(baseline_name)[1]),
        )
        prime_scores = _compute_oof_scores(
            scoring_df,
            prime_cols,
            model_family=str(prime_row.get("model_family") or _parse_experiment_metadata(prime_name)[1]),
        )
        y_true = scoring_df["label"].astype(int).to_numpy()

        best_candidate: dict[str, Any] | None = None
        for weight_prime in np.linspace(0.0, 1.0, 21):
            blended_scores = (weight_prime * prime_scores) + ((1.0 - weight_prime) * baseline_scores)
            metrics = _classification_metrics(y_true, blended_scores)
            brier_loss = float(np.mean(np.square(blended_scores - y_true)))
            candidate = {
                "blend_weight_prime": float(weight_prime),
                "blend_weight_baseline": float(1.0 - weight_prime),
                "balanced_internal_score": _balanced_gene_score(pd.Series(metrics), primary_metric=primary_metric),
                "robust_internal_score": _robust_blend_score(pd.Series(metrics), brier_loss=brier_loss),
                "brier_loss": brier_loss,
                **metrics,
            }
            if best_candidate is None:
                best_candidate = candidate
                continue
            if optimization_mode == "robust":
                candidate_key = (
                    float(candidate["robust_internal_score"]),
                    -float(candidate.get("brier_loss", np.nan)),
                    float(candidate.get(metric_name, np.nan)),
                    float(candidate.get("auc_pr", np.nan)),
                    float(candidate.get("mcc", np.nan)),
                    -abs(candidate["blend_weight_prime"] - 0.5),
                )
                best_key = (
                    float(best_candidate["robust_internal_score"]),
                    -float(best_candidate.get("brier_loss", np.nan)),
                    float(best_candidate.get(metric_name, np.nan)),
                    float(best_candidate.get("auc_pr", np.nan)),
                    float(best_candidate.get("mcc", np.nan)),
                    -abs(best_candidate["blend_weight_prime"] - 0.5),
                )
            else:
                candidate_key = (
                    float(candidate["balanced_internal_score"]),
                    float(candidate.get(metric_name, np.nan)),
                    float(candidate.get("auc_pr", np.nan)),
                    float(candidate.get("mcc", np.nan)),
                    -abs(candidate["blend_weight_prime"] - 0.5),
                )
                best_key = (
                    float(best_candidate["balanced_internal_score"]),
                    float(best_candidate.get(metric_name, np.nan)),
                    float(best_candidate.get("auc_pr", np.nan)),
                    float(best_candidate.get("mcc", np.nan)),
                    -abs(best_candidate["blend_weight_prime"] - 0.5),
                )
            if candidate_key > best_key:
                best_candidate = candidate

        if not best_candidate:
            continue

        rows.append(
            {
                "gene": str(gene_name),
                "blend_experiment": experiment_name,
                "prime_experiment": prime_name,
                "baseline_experiment": baseline_name,
                "prime_feature_set": str(prime_row.get("feature_set") or _parse_experiment_metadata(prime_name)[0]),
                "baseline_feature_set": str(baseline_row.get("feature_set") or _parse_experiment_metadata(baseline_name)[0]),
                "prime_model_family": str(prime_row.get("model_family") or _parse_experiment_metadata(prime_name)[1]),
                "baseline_model_family": str(baseline_row.get("model_family") or _parse_experiment_metadata(baseline_name)[1]),
                "blend_weight_prime": float(best_candidate["blend_weight_prime"]),
                "blend_weight_baseline": float(best_candidate["blend_weight_baseline"]),
                "selection_origin": selection_origin,
                "optimization_mode": optimization_mode,
                "balanced_internal_score": float(best_candidate["balanced_internal_score"]),
                "robust_internal_score": float(best_candidate["robust_internal_score"]),
                "brier_loss": float(best_candidate["brier_loss"]),
                "auc_roc": float(best_candidate.get("auc_roc", np.nan)),
                "auc_pr": float(best_candidate.get("auc_pr", np.nan)),
                "mcc": float(best_candidate.get("mcc", np.nan)),
                "n_variants": int(len(subset)),
                "n_features": int(len(sorted(set(prime_cols).union(baseline_cols)))),
            }
        )

    manifest = pd.DataFrame(rows)
    if not manifest.empty:
        manifest = manifest.sort_values(["gene"], ascending=[True]).reset_index(drop=True)
    return manifest


def build_gene_robust_blend_manifest(
    gene_training_metrics: Dict[str, pd.DataFrame],
    train_df: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_training_metrics: pd.DataFrame | None = None,
    baseline_experiment: str = "external_predictors_only",
    experiment_name: str = "hybrid_external_gene_robust_blend",
) -> pd.DataFrame:
    return build_gene_adaptive_blend_manifest(
        gene_training_metrics=gene_training_metrics,
        train_df=train_df,
        feature_sets=feature_sets,
        global_training_metrics=global_training_metrics,
        primary_metric="auc_roc",
        baseline_experiment=baseline_experiment,
        experiment_name=experiment_name,
        optimization_mode="robust",
    )


def train_gene_adaptive_blend_models(
    train_df: pd.DataFrame,
    blend_manifest: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_trained_models: Dict[str, object] | None = None,
) -> Dict[str, dict]:
    trained: Dict[str, dict] = {}
    if blend_manifest.empty:
        return trained

    for row in blend_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        if not gene_name:
            continue
        subset = train_df[train_df["gene"].astype(str) == gene_name].copy()
        if subset.empty or subset["label"].nunique() < 2:
            continue
        prime_name = str(row.get("prime_experiment") or "")
        baseline_name = str(row.get("baseline_experiment") or "")
        prime_cols = feature_sets.get(prime_name, [])
        baseline_cols = feature_sets.get(baseline_name, [])
        if not prime_cols or not baseline_cols:
            continue
        training_origin = str(row.get("selection_origin") or "local_gene_metrics")
        if training_origin == "global_fallback" or not _supports_local_gene_training(subset):
            global_models = global_trained_models or {}
            prime_model = global_models.get(prime_name)
            baseline_model = global_models.get(baseline_name)
            if prime_model is None or baseline_model is None:
                continue
            training_origin = "global_fallback"
        else:
            prime_model, _ = train_model_with_feature_subset(
                subset,
                prime_cols,
                model_family=str(row.get("prime_model_family") or _parse_experiment_metadata(prime_name)[1]),
            )
            baseline_model, _ = train_model_with_feature_subset(
                subset,
                baseline_cols,
                model_family=str(row.get("baseline_model_family") or _parse_experiment_metadata(baseline_name)[1]),
            )
            training_origin = "local_gene_metrics"
        trained[gene_name] = {
            "prime_model": prime_model,
            "baseline_model": baseline_model,
            "prime_feature_columns": list(prime_cols),
            "baseline_feature_columns": list(baseline_cols),
            "prime_experiment": prime_name,
            "baseline_experiment": baseline_name,
            "blend_weight_prime": float(row.get("blend_weight_prime") or 0.0),
            "blend_weight_baseline": float(row.get("blend_weight_baseline") or 1.0),
            "training_origin": training_origin,
        }
    return trained


def build_gene_calibrated_blend_manifest(
    train_df: pd.DataFrame,
    blend_manifest: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    experiment_name: str = "hybrid_external_gene_calibrated_blend",
) -> pd.DataFrame:
    rows: List[dict] = []
    if blend_manifest.empty:
        return pd.DataFrame()

    for row in blend_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        if not gene_name:
            continue
        subset = train_df[train_df["gene"].astype(str) == gene_name].copy()
        if subset.empty or subset["label"].nunique() < 2:
            continue

        prime_name = str(row.get("prime_experiment") or "")
        baseline_name = str(row.get("baseline_experiment") or "")
        prime_cols = feature_sets.get(prime_name, [])
        baseline_cols = feature_sets.get(baseline_name, [])
        if not prime_cols or not baseline_cols:
            continue

        scoring_df = subset.copy()
        selection_origin = str(row.get("selection_origin") or "local_gene_metrics")
        if not _supports_local_gene_training(subset):
            if selection_origin == "global_fallback" and _supports_local_gene_training(train_df):
                scoring_df = train_df.copy()
            else:
                continue

        prime_scores = _compute_oof_scores(
            scoring_df,
            prime_cols,
            model_family=str(row.get("prime_model_family") or _parse_experiment_metadata(prime_name)[1]),
        )
        baseline_scores = _compute_oof_scores(
            scoring_df,
            baseline_cols,
            model_family=str(row.get("baseline_model_family") or _parse_experiment_metadata(baseline_name)[1]),
        )
        raw_scores = (
            float(row.get("blend_weight_prime") or 0.0) * prime_scores
        ) + (
            float(row.get("blend_weight_baseline") or 1.0) * baseline_scores
        )
        y_true = scoring_df["label"].astype(int).to_numpy()
        calibrator = _fit_score_calibrator(y_true, raw_scores)
        calibrated_scores = _apply_score_calibrator(raw_scores, calibrator)
        metrics = _classification_metrics(y_true, calibrated_scores)

        rows.append(
            {
                "gene": gene_name,
                "blend_experiment": experiment_name,
                "source_blend_experiment": str(row.get("blend_experiment") or "hybrid_external_gene_adaptive_blend"),
                "prime_experiment": prime_name,
                "baseline_experiment": baseline_name,
                "prime_feature_set": str(row.get("prime_feature_set") or _parse_experiment_metadata(prime_name)[0]),
                "baseline_feature_set": str(row.get("baseline_feature_set") or _parse_experiment_metadata(baseline_name)[0]),
                "prime_model_family": str(row.get("prime_model_family") or _parse_experiment_metadata(prime_name)[1]),
                "baseline_model_family": str(row.get("baseline_model_family") or _parse_experiment_metadata(baseline_name)[1]),
                "blend_weight_prime": float(row.get("blend_weight_prime") or 0.0),
                "blend_weight_baseline": float(row.get("blend_weight_baseline") or 1.0),
                "selection_origin": selection_origin,
                "calibrator_kind": str(calibrator.get("kind") or "identity"),
                "calibrator_slope": float(calibrator.get("slope") or 1.0),
                "calibrator_intercept": float(calibrator.get("intercept") or 0.0),
                "balanced_internal_score": _balanced_gene_score(pd.Series(metrics), primary_metric="auc_roc"),
                "auc_roc": float(metrics.get("auc_roc", np.nan)),
                "auc_pr": float(metrics.get("auc_pr", np.nan)),
                "accuracy": float(metrics.get("accuracy", np.nan)),
                "sensitivity": float(metrics.get("sensitivity", np.nan)),
                "specificity": float(metrics.get("specificity", np.nan)),
                "mcc": float(metrics.get("mcc", np.nan)),
                "precision_at_0_5": float(metrics.get("precision_at_0_5", np.nan)),
                "recall_at_0_5": float(metrics.get("recall_at_0_5", np.nan)),
                "n_variants": int(len(subset)),
                "n_features": int(len(sorted(set(prime_cols).union(baseline_cols)))),
            }
        )

    manifest = pd.DataFrame(rows)
    if not manifest.empty:
        manifest = manifest.sort_values(["gene"], ascending=[True]).reset_index(drop=True)
    return manifest


def train_gene_calibrated_blend_models(
    train_df: pd.DataFrame,
    blend_manifest: pd.DataFrame,
    feature_sets: Dict[str, List[str]],
    global_trained_models: Dict[str, object] | None = None,
) -> Dict[str, dict]:
    trained: Dict[str, dict] = {}
    if blend_manifest.empty:
        return trained

    for row in blend_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        if not gene_name:
            continue
        subset = train_df[train_df["gene"].astype(str) == gene_name].copy()
        if subset.empty or subset["label"].nunique() < 2:
            continue
        prime_name = str(row.get("prime_experiment") or "")
        baseline_name = str(row.get("baseline_experiment") or "")
        prime_cols = feature_sets.get(prime_name, [])
        baseline_cols = feature_sets.get(baseline_name, [])
        if not prime_cols or not baseline_cols:
            continue
        training_origin = str(row.get("selection_origin") or "local_gene_metrics")
        if training_origin == "global_fallback" or not _supports_local_gene_training(subset):
            global_models = global_trained_models or {}
            prime_model = global_models.get(prime_name)
            baseline_model = global_models.get(baseline_name)
            if prime_model is None or baseline_model is None:
                continue
            training_origin = "global_fallback"
        else:
            prime_model, _ = train_model_with_feature_subset(
                subset,
                prime_cols,
                model_family=str(row.get("prime_model_family") or _parse_experiment_metadata(prime_name)[1]),
            )
            baseline_model, _ = train_model_with_feature_subset(
                subset,
                baseline_cols,
                model_family=str(row.get("baseline_model_family") or _parse_experiment_metadata(baseline_name)[1]),
            )
            training_origin = "local_gene_metrics"
        trained[gene_name] = {
            "prime_model": prime_model,
            "baseline_model": baseline_model,
            "prime_feature_columns": list(prime_cols),
            "baseline_feature_columns": list(baseline_cols),
            "prime_experiment": prime_name,
            "baseline_experiment": baseline_name,
            "blend_weight_prime": float(row.get("blend_weight_prime") or 0.0),
            "blend_weight_baseline": float(row.get("blend_weight_baseline") or 1.0),
            "calibrator": {
                "kind": str(row.get("calibrator_kind") or "identity"),
                "slope": float(row.get("calibrator_slope") or 1.0),
                "intercept": float(row.get("calibrator_intercept") or 0.0),
            },
            "training_origin": training_origin,
        }
    return trained


def _build_gene_adaptive_blend_training_row(
    blend_manifest: pd.DataFrame,
    trained_gene_blends: Dict[str, dict],
    experiment_name: str = "hybrid_external_gene_adaptive_blend",
    model_family: str = "gene_adaptive_blend",
) -> pd.DataFrame:
    if blend_manifest.empty or not trained_gene_blends:
        return pd.DataFrame()

    rows = []
    union_features = set()
    for row in blend_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        payload = trained_gene_blends.get(gene_name)
        if not payload:
            continue
        union_features.update(payload.get("prime_feature_columns") or [])
        union_features.update(payload.get("baseline_feature_columns") or [])
        rows.append(row)
    if not rows:
        return pd.DataFrame()

    weighted_df = pd.DataFrame(rows)
    weights = weighted_df["n_variants"].astype(float).to_numpy()
    weight_total = float(weights.sum()) if len(weights) else 0.0
    aggregate: dict[str, float | int | str] = {
        "experiment": experiment_name,
        "feature_set": experiment_name,
        "model_family": model_family,
        "is_primary_experiment": 0,
        "n_features": int(len(union_features)),
        "n_gene_specialists": int(len(rows)),
        "n_train": int(weight_total),
    }
    for column in ["auc_roc", "auc_pr", "accuracy", "sensitivity", "specificity", "mcc", "precision_at_0_5", "recall_at_0_5"]:
        values = weighted_df[column].astype(float).to_numpy() if column in weighted_df.columns else np.array([], dtype=float)
        if len(values) == 0:
            aggregate[column] = float("nan")
            continue
        valid = ~np.isnan(values)
        if not valid.any():
            aggregate[column] = float("nan")
            continue
        valid_weights = weights[valid]
        aggregate[column] = float(np.average(values[valid], weights=valid_weights)) if float(valid_weights.sum()) else float(np.mean(values[valid]))
    return pd.DataFrame([aggregate])


def evaluate_gene_adaptive_blend_on_cohort(
    trained_gene_blends: Dict[str, dict],
    df: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
    experiment_name: str = "hybrid_external_gene_adaptive_blend",
    model_family: str = "gene_adaptive_blend",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not trained_gene_blends or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if "label" not in df.columns:
        raise ValueError("A coorte de avaliacao precisa conter a coluna 'label'.")
    df = df.reset_index(drop=True).copy()

    score_values = np.full(len(df), np.nan, dtype=float)
    for gene_name, subset in df.groupby("gene", dropna=False):
        payload = trained_gene_blends.get(str(gene_name))
        if not payload:
            continue
        prime_scores = predict_scores_for_experiment(
            payload["prime_model"],
            subset,
            payload.get("prime_feature_columns") or [],
        )
        baseline_scores = predict_scores_for_experiment(
            payload["baseline_model"],
            subset,
            payload.get("baseline_feature_columns") or [],
        )
        blended_scores = (payload["blend_weight_prime"] * prime_scores) + (payload["blend_weight_baseline"] * baseline_scores)
        score_values[subset.index.to_numpy(dtype=int)] = blended_scores

    if np.isnan(score_values).all():
        return pd.DataFrame(), pd.DataFrame()

    score_frame = pd.DataFrame({
        "variant": df["variant"].astype(str) if "variant" in df.columns else [f"row_{i}" for i in range(len(df))],
        "gene": df["gene"].astype(str) if "gene" in df.columns else "unknown",
        "label": df["label"].astype(int),
        f"score__{experiment_name}": score_values,
    })

    rows: List[dict] = []
    grouped = [("combined", df.copy())]
    if "gene" in df.columns:
        grouped.extend([(str(gene_name), subset.copy()) for gene_name, subset in df.groupby("gene")])

    feature_union = sorted({
        column
        for payload in trained_gene_blends.values()
        for column in (payload.get("prime_feature_columns") or []) + (payload.get("baseline_feature_columns") or [])
    })
    for group_name, subset in grouped:
        group_scores = score_values[subset.index.to_numpy(dtype=int)]
        valid_mask = ~np.isnan(group_scores)
        if not valid_mask.any():
            continue
        y_true = subset["label"].astype(int).to_numpy()[valid_mask]
        metrics = _classification_metrics(y_true, group_scores[valid_mask])
        rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "evaluation_group": group_name,
                "experiment": experiment_name,
                "feature_set": experiment_name,
                "model_family": model_family,
                "is_primary_experiment": 0,
                "n_features": int(len(feature_union)),
                **metrics,
            }
        )

    metrics_df = pd.DataFrame(rows)
    if not metrics_df.empty:
        metrics_df = _sort_experiment_metrics(metrics_df)
    return metrics_df, score_frame


def _build_gene_calibrated_blend_training_row(
    blend_manifest: pd.DataFrame,
    trained_gene_blends: Dict[str, dict],
    experiment_name: str = "hybrid_external_gene_calibrated_blend",
) -> pd.DataFrame:
    if blend_manifest.empty or not trained_gene_blends:
        return pd.DataFrame()

    rows = []
    union_features = set()
    for row in blend_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        payload = trained_gene_blends.get(gene_name)
        if not payload:
            continue
        union_features.update(payload.get("prime_feature_columns") or [])
        union_features.update(payload.get("baseline_feature_columns") or [])
        rows.append(row)
    if not rows:
        return pd.DataFrame()

    weighted_df = pd.DataFrame(rows)
    weights = weighted_df["n_variants"].astype(float).to_numpy()
    weight_total = float(weights.sum()) if len(weights) else 0.0
    aggregate: dict[str, float | int | str] = {
        "experiment": experiment_name,
        "feature_set": experiment_name,
        "model_family": "gene_calibrated_blend",
        "is_primary_experiment": 0,
        "n_features": int(len(union_features)),
        "n_gene_specialists": int(len(rows)),
        "n_train": int(weight_total),
    }
    for column in ["auc_roc", "auc_pr", "accuracy", "sensitivity", "specificity", "mcc", "precision_at_0_5", "recall_at_0_5"]:
        values = weighted_df[column].astype(float).to_numpy() if column in weighted_df.columns else np.array([], dtype=float)
        if len(values) == 0:
            aggregate[column] = float("nan")
            continue
        valid = ~np.isnan(values)
        if not valid.any():
            aggregate[column] = float("nan")
            continue
        valid_weights = weights[valid]
        aggregate[column] = float(np.average(values[valid], weights=valid_weights)) if float(valid_weights.sum()) else float(np.mean(values[valid]))
    return pd.DataFrame([aggregate])


def evaluate_gene_calibrated_blend_on_cohort(
    trained_gene_blends: Dict[str, dict],
    df: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
    experiment_name: str = "hybrid_external_gene_calibrated_blend",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not trained_gene_blends or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if "label" not in df.columns:
        raise ValueError("A coorte de avaliacao precisa conter a coluna 'label'.")
    df = df.reset_index(drop=True).copy()

    score_values = np.full(len(df), np.nan, dtype=float)
    for gene_name, subset in df.groupby("gene", dropna=False):
        payload = trained_gene_blends.get(str(gene_name))
        if not payload:
            continue
        prime_scores = predict_scores_for_experiment(
            payload["prime_model"],
            subset,
            payload.get("prime_feature_columns") or [],
        )
        baseline_scores = predict_scores_for_experiment(
            payload["baseline_model"],
            subset,
            payload.get("baseline_feature_columns") or [],
        )
        blended_scores = (payload["blend_weight_prime"] * prime_scores) + (payload["blend_weight_baseline"] * baseline_scores)
        calibrated_scores = _apply_score_calibrator(blended_scores, payload.get("calibrator") or {})
        score_values[subset.index.to_numpy(dtype=int)] = calibrated_scores

    if np.isnan(score_values).all():
        return pd.DataFrame(), pd.DataFrame()

    score_frame = pd.DataFrame({
        "variant": df["variant"].astype(str) if "variant" in df.columns else [f"row_{i}" for i in range(len(df))],
        "gene": df["gene"].astype(str) if "gene" in df.columns else "unknown",
        "label": df["label"].astype(int),
        f"score__{experiment_name}": score_values,
    })

    rows: List[dict] = []
    grouped = [("combined", df.copy())]
    if "gene" in df.columns:
        grouped.extend([(str(gene_name), subset.copy()) for gene_name, subset in df.groupby("gene")])

    feature_union = sorted({
        column
        for payload in trained_gene_blends.values()
        for column in (payload.get("prime_feature_columns") or []) + (payload.get("baseline_feature_columns") or [])
    })
    for group_name, subset in grouped:
        group_scores = score_values[subset.index.to_numpy(dtype=int)]
        valid_mask = ~np.isnan(group_scores)
        if not valid_mask.any():
            continue
        y_true = subset["label"].astype(int).to_numpy()[valid_mask]
        metrics = _classification_metrics(y_true, group_scores[valid_mask])
        rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "evaluation_group": group_name,
                "experiment": experiment_name,
                "feature_set": experiment_name,
                "model_family": "gene_calibrated_blend",
                "is_primary_experiment": 0,
                "n_features": int(len(feature_union)),
                **metrics,
            }
        )

    metrics_df = pd.DataFrame(rows)
    if not metrics_df.empty:
        metrics_df = _sort_experiment_metrics(metrics_df)
    return metrics_df, score_frame


def _build_gene_specialist_training_row(
    specialist_manifest: pd.DataFrame,
    trained_gene_specialists: Dict[str, dict],
    primary_metric: str = "auc_roc",
    experiment_name: str = "gene_balanced_specialist",
) -> pd.DataFrame:
    if specialist_manifest.empty or not trained_gene_specialists:
        return pd.DataFrame()

    weighted_rows: List[dict] = []
    union_features = set()
    for row in specialist_manifest.to_dict(orient="records"):
        gene_name = str(row.get("gene") or "")
        payload = trained_gene_specialists.get(gene_name)
        if not payload:
            continue
        metrics = dict(payload.get("training_metrics") or {})
        weight = int(row.get("n_variants") or 0)
        union_features.update(payload.get("feature_columns") or [])
        weighted_rows.append({"weight": weight, **metrics})

    if not weighted_rows:
        return pd.DataFrame()

    weighted_df = pd.DataFrame(weighted_rows)
    weights = weighted_df["weight"].astype(float).to_numpy()
    weight_total = float(weights.sum()) if len(weights) else 0.0
    aggregate: dict[str, float | int | str] = {
        "experiment": experiment_name,
        "feature_set": experiment_name,
        "model_family": "gene_specialist",
        "is_primary_experiment": 0,
        "n_features": int(len(union_features)),
        "specialist_metric": primary_metric,
        "n_gene_specialists": int(len(weighted_rows)),
        "n_gene_local_models": int(sum(1 for payload in trained_gene_specialists.values() if payload.get("training_origin") == "gene_local")),
        "n_global_fallback_models": int(sum(1 for payload in trained_gene_specialists.values() if payload.get("training_origin") == "global_fallback")),
        "n_train": int(weight_total),
    }
    for column in ["auc_roc", "auc_pr", "accuracy", "sensitivity", "specificity", "mcc", "precision_at_0_5", "recall_at_0_5"]:
        if column not in weighted_df.columns:
            aggregate[column] = float("nan")
            continue
        values = weighted_df[column].astype(float).to_numpy()
        valid = ~np.isnan(values)
        if not valid.any():
            aggregate[column] = float("nan")
            continue
        valid_weights = weights[valid]
        if float(valid_weights.sum()) == 0:
            aggregate[column] = float(np.mean(values[valid]))
        else:
            aggregate[column] = float(np.average(values[valid], weights=valid_weights))
    return pd.DataFrame([aggregate])


def evaluate_gene_specialist_on_cohort(
    trained_gene_specialists: Dict[str, dict],
    df: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
    experiment_name: str = "gene_balanced_specialist",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not trained_gene_specialists or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if "label" not in df.columns:
        raise ValueError("A coorte de avaliacao precisa conter a coluna 'label'.")
    df = df.reset_index(drop=True).copy()

    score_values = np.full(len(df), np.nan, dtype=float)
    for gene_name, subset in df.groupby("gene", dropna=False):
        gene_key = str(gene_name)
        payload = trained_gene_specialists.get(gene_key)
        if not payload:
            continue
        feature_columns = payload.get("feature_columns") or []
        if not feature_columns:
            continue
        subset_scores = predict_scores_for_experiment(payload["pipeline"], subset, feature_columns)
        score_values[subset.index.to_numpy(dtype=int)] = subset_scores

    if np.isnan(score_values).all():
        return pd.DataFrame(), pd.DataFrame()

    score_frame = pd.DataFrame({
        "variant": df["variant"].astype(str) if "variant" in df.columns else [f"row_{i}" for i in range(len(df))],
        "gene": df["gene"].astype(str) if "gene" in df.columns else "unknown",
        "label": df["label"].astype(int),
        f"score__{experiment_name}": score_values,
    })

    rows: List[dict] = []
    grouped = [("combined", df.copy())]
    if "gene" in df.columns:
        grouped.extend([(str(gene_name), subset.copy()) for gene_name, subset in df.groupby("gene")])

    feature_union = sorted({
        column
        for payload in trained_gene_specialists.values()
        for column in (payload.get("feature_columns") or [])
    })
    for group_name, subset in grouped:
        group_scores = score_values[subset.index.to_numpy(dtype=int)]
        valid_mask = ~np.isnan(group_scores)
        if not valid_mask.any():
            continue
        y_true = subset["label"].astype(int).to_numpy()[valid_mask]
        metrics = _classification_metrics(y_true, group_scores[valid_mask])
        rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "evaluation_group": group_name,
                "experiment": experiment_name,
                "feature_set": experiment_name,
                "model_family": "gene_specialist",
                "is_primary_experiment": 0,
                "n_features": int(len(feature_union)),
                **metrics,
            }
        )

    metrics_df = pd.DataFrame(rows)
    if not metrics_df.empty:
        metrics_df = _sort_experiment_metrics(metrics_df)
    return metrics_df, score_frame


def evaluate_experiment_suite_on_cohort(
    trained_models: Dict[str, object],
    feature_sets: Dict[str, List[str]],
    df: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "label" not in df.columns:
        raise ValueError("A coorte de avaliacao precisa conter a coluna 'label'.")

    score_frame = pd.DataFrame({
        "variant": df["variant"].astype(str) if "variant" in df.columns else [f"row_{i}" for i in range(len(df))],
        "gene": df["gene"].astype(str) if "gene" in df.columns else "unknown",
        "label": df["label"].astype(int),
    })

    rows = []
    grouped = [("combined", df.copy())]
    if "gene" in df.columns:
        grouped.extend([(str(gene_name), subset.copy()) for gene_name, subset in df.groupby("gene")])

    for experiment_name, model in trained_models.items():
        cols = feature_sets.get(experiment_name, [])
        if not cols:
            continue

        feature_set_name, model_family, is_primary_experiment = _parse_experiment_metadata(experiment_name)
        combined_scores = predict_scores_for_experiment(model, df, cols)
        score_frame[f"score__{experiment_name}"] = combined_scores

        for group_name, subset in grouped:
            subset_scores = predict_scores_for_experiment(model, subset, cols)
            y_true = subset["label"].astype(int).to_numpy()
            metrics = _classification_metrics(y_true, subset_scores)
            rows.append({
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "evaluation_group": group_name,
                "experiment": experiment_name,
                "feature_set": feature_set_name,
                "model_family": model_family,
                "is_primary_experiment": is_primary_experiment,
                "n_features": len(cols),
                **metrics,
            })

    metrics_df = pd.DataFrame(rows)
    if not metrics_df.empty:
        metrics_df = _sort_experiment_metrics(metrics_df)
    return metrics_df, score_frame


def bootstrap_metric_delta(
    y_true: np.ndarray,
    y_score_a: np.ndarray,
    y_score_b: np.ndarray,
    metric_name: str = "auc_roc",
    n_bootstrap: int = 200,
    random_state: int = 42,
) -> dict:
    rng = np.random.default_rng(random_state)
    deltas = []
    n = len(y_true)
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        y_b = y_true[idx]
        if len(np.unique(y_b)) < 2:
            continue
        metric_a = _metric_from_name(metric_name, y_b, y_score_a[idx])
        metric_b = _metric_from_name(metric_name, y_b, y_score_b[idx])
        deltas.append(metric_a - metric_b)

    if not deltas:
        return {
            "metric": metric_name,
            "delta_mean": np.nan,
            "ci_lower_95": np.nan,
            "ci_upper_95": np.nan,
            "n_bootstrap_valid": 0,
        }

    arr = np.asarray(deltas, dtype=float)
    return {
        "metric": metric_name,
        "delta_mean": float(arr.mean()),
        "ci_lower_95": float(np.percentile(arr, 2.5)),
        "ci_upper_95": float(np.percentile(arr, 97.5)),
        "n_bootstrap_valid": int(len(arr)),
    }


def _resolve_score_column(score_frame: pd.DataFrame, experiment_reference: str) -> tuple[str | None, str | None]:
    score_columns = [col for col in score_frame.columns if col.startswith("score__")]
    exact_column = f"score__{experiment_reference}"
    if exact_column in score_columns:
        return exact_column, experiment_reference

    random_forest_column = f"score__{experiment_reference}__random_forest"
    if random_forest_column in score_columns:
        return random_forest_column, random_forest_column.replace("score__", "", 1)

    prefix = f"score__{experiment_reference}__"
    matching = sorted(col for col in score_columns if col.startswith(prefix))
    if matching:
        return matching[0], matching[0].replace("score__", "", 1)
    return None, None


def build_pairwise_comparison_table(
    score_frame: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
    baseline_experiment: str = "external_predictors_only",
    n_bootstrap: int = 200,
) -> pd.DataFrame:
    baseline_column, resolved_baseline_experiment = _resolve_score_column(score_frame, baseline_experiment)
    score_columns = [col for col in score_frame.columns if col.startswith("score__")]
    if baseline_column is None or resolved_baseline_experiment is None:
        return pd.DataFrame(columns=[
            "cohort", "cohort_role", "experiment", "baseline_experiment", "metric",
            "delta_mean", "ci_lower_95", "ci_upper_95", "n_bootstrap_valid",
        ])

    y_true = score_frame["label"].astype(int).to_numpy()
    rows = []
    for score_column in score_columns:
        experiment_name = score_column.replace("score__", "", 1)
        if experiment_name == resolved_baseline_experiment:
            continue
        for metric_name in ["auc_roc", "auc_pr"]:
            delta = bootstrap_metric_delta(
                y_true=y_true,
                y_score_a=score_frame[score_column].to_numpy(dtype=float),
                y_score_b=score_frame[baseline_column].to_numpy(dtype=float),
                metric_name=metric_name,
                n_bootstrap=n_bootstrap,
                random_state=42,
            )
            rows.append({
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "experiment": experiment_name,
                "baseline_experiment": resolved_baseline_experiment,
                **delta,
            })

    return pd.DataFrame(rows)


def select_consensus_members(
    training_metrics: pd.DataFrame,
    primary_metric: str = "auc_roc",
    top_k: int = 3,
) -> List[str]:
    if training_metrics.empty or top_k < 2:
        return []
    metric_name = primary_metric if primary_metric in training_metrics.columns else "auc_roc"
    ranking = training_metrics.sort_values(
        [metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)

    selected: List[str] = []
    used_feature_sets = set()
    if "feature_set" in ranking.columns:
        for _, row in ranking.iterrows():
            feature_set = str(row.get("feature_set", row["experiment"]))
            experiment_name = str(row["experiment"])
            if feature_set in used_feature_sets:
                continue
            selected.append(experiment_name)
            used_feature_sets.add(feature_set)
            if len(selected) >= top_k:
                return selected

    for experiment_name in ranking["experiment"].astype(str).tolist():
        if experiment_name not in selected:
            selected.append(experiment_name)
        if len(selected) >= top_k:
            break
    return selected


def add_consensus_to_evaluation(
    metrics_df: pd.DataFrame,
    score_frame: pd.DataFrame,
    cohort_name: str,
    cohort_role: str,
    consensus_members: List[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    resolved_members = [
        experiment_name
        for experiment_name in consensus_members
        if f"score__{experiment_name}" in score_frame.columns
    ]
    if len(resolved_members) < 2:
        return metrics_df, score_frame, pd.DataFrame(columns=["consensus_experiment", "member_rank", "member_experiment"])

    consensus_name = f"consensus_top{len(resolved_members)}"
    updated_score_frame = score_frame.copy()
    member_columns = [f"score__{experiment_name}" for experiment_name in resolved_members]
    updated_score_frame[f"score__{consensus_name}"] = updated_score_frame[member_columns].mean(axis=1)

    grouped = [("combined", updated_score_frame.copy())]
    if "gene" in updated_score_frame.columns:
        grouped.extend(
            [(str(gene_name), subset.copy()) for gene_name, subset in updated_score_frame.groupby("gene")]
        )

    new_rows = []
    for group_name, subset in grouped:
        y_true = subset["label"].astype(int).to_numpy()
        y_score = subset[f"score__{consensus_name}"].to_numpy(dtype=float)
        new_rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": cohort_role,
                "evaluation_group": group_name,
                "experiment": consensus_name,
                "feature_set": "consensus",
                "model_family": "ensemble_mean",
                "is_primary_experiment": 0,
                "n_features": len(resolved_members),
                **_classification_metrics(y_true, y_score),
            }
        )

    updated_metrics = pd.concat([metrics_df, pd.DataFrame(new_rows)], ignore_index=True)
    updated_metrics = _sort_experiment_metrics(updated_metrics)
    manifest = pd.DataFrame(
        [
            {
                "consensus_experiment": consensus_name,
                "member_rank": index + 1,
                "member_experiment": experiment_name,
            }
            for index, experiment_name in enumerate(resolved_members)
        ]
    )
    return updated_metrics, updated_score_frame, manifest


def add_gene_specialist_to_evaluation(
    metrics_df: pd.DataFrame,
    score_frame: pd.DataFrame,
    specialist_metrics: pd.DataFrame,
    specialist_score_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if specialist_metrics.empty or specialist_score_frame.empty:
        return metrics_df, score_frame

    updated_score_frame = score_frame.copy()
    for column in specialist_score_frame.columns:
        if column.startswith("score__"):
            updated_score_frame[column] = specialist_score_frame[column].to_numpy(dtype=float)

    updated_metrics = pd.concat([metrics_df, specialist_metrics], ignore_index=True)
    updated_metrics = _sort_experiment_metrics(updated_metrics)
    return updated_metrics, updated_score_frame


def build_feature_set_leaderboard(training_metrics: pd.DataFrame) -> pd.DataFrame:
    if training_metrics.empty or "feature_set" not in training_metrics.columns:
        return pd.DataFrame()
    ranked = training_metrics.sort_values(
        ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
        ascending=[False, False, False, False, True],
    )
    return ranked.groupby("feature_set", as_index=False).head(1).reset_index(drop=True)


def build_model_family_summary(training_metrics: pd.DataFrame) -> pd.DataFrame:
    if training_metrics.empty or "model_family" not in training_metrics.columns:
        return pd.DataFrame()
    summary = (
        training_metrics.groupby("model_family", as_index=False)
        .agg(
            n_experiments=("experiment", "count"),
            auc_roc_mean=("auc_roc", "mean"),
            auc_pr_mean=("auc_pr", "mean"),
            mcc_mean=("mcc", "mean"),
            best_auc_roc=("auc_roc", "max"),
            best_auc_pr=("auc_pr", "max"),
            best_mcc=("mcc", "max"),
        )
        .sort_values(["best_auc_roc", "best_auc_pr", "best_mcc"], ascending=False)
        .reset_index(drop=True)
    )
    return summary


def _export_named_tables(table_map: Dict[str, pd.DataFrame], output_dir: str, prefix: str) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for name, table in table_map.items():
        safe_name = _slugify(name)
        path = os.path.join(output_dir, f"{prefix}_{safe_name}.csv")
        table.to_csv(path, index=False)
        paths[name] = path
    return paths


def build_study_summary_report(results: dict) -> str:
    lines: List[str] = []
    design = results.get("study_design")
    if design is not None:
        lines.append(f"PrimeVarClass Study Report - {design.name}")
        lines.append("=" * (31 + len(design.name)))

    cohort_manifest = results.get("cohort_manifest")
    if isinstance(cohort_manifest, pd.DataFrame) and not cohort_manifest.empty:
        lines.append("\n1. Cohort manifest")
        for _, row in cohort_manifest.iterrows():
            lines.append(
                f"- {row['cohort_name']} ({row['role']}): n={int(row['valid_rows'])}, "
                f"labels={int(row['n_classes'])}, source_tables={int(row['n_source_tables'])}"
            )

    training_metrics = results.get("training_metrics")
    if isinstance(training_metrics, pd.DataFrame) and not training_metrics.empty:
        best_row = training_metrics.iloc[0]
        lines.append("\n2. Best internal experiment")
        lines.append(
            f"- {best_row['experiment']}: AUC-ROC={float(best_row.get('auc_roc', np.nan)):.4f}, "
            f"AUC-PR={float(best_row.get('auc_pr', np.nan)):.4f}, MCC={float(best_row.get('mcc', np.nan)):.4f}"
        )

    consensus_members = results.get("consensus_members")
    if isinstance(consensus_members, list) and consensus_members:
        lines.append("\n3. Consensus ensemble")
        lines.append(f"- Consensus members: {', '.join(consensus_members)}")

    external_metrics = results.get("external_evaluation_metrics")
    if isinstance(external_metrics, pd.DataFrame) and not external_metrics.empty:
        lines.append("\n4. External evaluation")
        combined_rows = external_metrics[external_metrics["evaluation_group"] == "combined"]
        for cohort_name, subset in combined_rows.groupby("cohort"):
            top_row = subset.sort_values(["auc_roc", "auc_pr", "mcc"], ascending=False).iloc[0]
            lines.append(
                f"- {cohort_name}: best={top_row['experiment']} "
                f"(AUC-ROC={float(top_row.get('auc_roc', np.nan)):.4f}, "
                f"AUC-PR={float(top_row.get('auc_pr', np.nan)):.4f}, MCC={float(top_row.get('mcc', np.nan)):.4f})"
            )

    pairwise = results.get("external_pairwise_comparisons")
    if isinstance(pairwise, pd.DataFrame) and not pairwise.empty:
        lines.append("\n5. Pairwise deltas vs baseline")
        for cohort_name, subset in pairwise.groupby("cohort"):
            auc_rows = subset[subset["metric"] == "auc_roc"].sort_values("delta_mean", ascending=False)
            if not auc_rows.empty:
                row = auc_rows.iloc[0]
                lines.append(
                    f"- {cohort_name}: {row['experiment']} vs {row['baseline_experiment']} "
                    f"delta AUC-ROC={float(row.get('delta_mean', np.nan)):.4f} "
                    f"[{float(row.get('ci_lower_95', np.nan)):.4f}, {float(row.get('ci_upper_95', np.nan)):.4f}]"
                )

    independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    if independence_summary:
        lines.append("\n6. Cohort independence")
        lines.append(
            f"- independence={int(independence_summary.get('overall_independence_percent', 0))}% | "
            f"max train/external overlap={int(independence_summary.get('max_variant_overlap_percent', 0))}% | "
            f"ready={'yes' if independence_summary.get('ready_for_external_validation') else 'not yet'}"
        )

    cohort_freeze_summary = dict(results.get("study_cohort_freeze_summary") or {})
    if cohort_freeze_summary:
        lines.append("\n7. Real-data cohort freeze")
        lines.append(
            f"- readiness={int(cohort_freeze_summary.get('overall_real_data_readiness_percent', 0))}% | "
            f"ready={'yes' if cohort_freeze_summary.get('ready_for_real_data_study') else 'not yet'} | "
            f"example-blocked={int(cohort_freeze_summary.get('n_example_blocked_cohorts', 0))} | "
            f"placeholder-release-blocked={int(cohort_freeze_summary.get('n_placeholder_release_blocked_cohorts', 0))}"
        )

    return "\n".join(lines)


def run_publication_study(
    config_path: str,
    output_dir: str = "primevarclass_study_results",
    report_context: Dict[str, Any] | None = None,
) -> dict:
    study = load_study_design(config_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    train_cohorts = [cohort for cohort in study.cohorts or [] if cohort.role == "train"]
    if len(train_cohorts) != 1:
        raise ValueError("O estudo precisa definir exatamente uma coorte com role='train'.")

    cohort_results = {}
    manifest_rows = []
    cohort_output_dir = output_root / "cohorts"
    cohort_output_dir.mkdir(parents=True, exist_ok=True)

    for cohort in study.cohorts or []:
        cohort_slug = _slugify(cohort.name)
        ingestion_output_dir = cohort_output_dir / f"{cohort_slug}_ingestion"
        built_df, build_report, source_report = build_dataset_from_source_config(
            config_path=cohort.source_config,
            mode=_resolve_cohort_mode(study, cohort),
            keep_metadata=study.keep_metadata,
            high_confidence_only=_resolve_cohort_high_confidence(study, cohort),
            source_output_dir=str(ingestion_output_dir),
        )

        built_path = cohort_output_dir / f"{cohort_slug}_processed_dataset.csv"
        report_path = cohort_output_dir / f"{cohort_slug}_source_report.csv"
        built_df.to_csv(built_path, index=False)
        source_report.to_csv(report_path, index=False)

        cohort_results[cohort.name] = {
            "spec": cohort,
            "built_df": built_df,
            "build_report": build_report,
            "source_report": source_report,
            "processed_dataset_path": str(built_path),
            "source_report_path": str(report_path),
            "ingestion_output_dir": str(ingestion_output_dir),
        }
        manifest_rows.append({
            "cohort_name": cohort.name,
            "role": cohort.role,
            "source_config": cohort.source_config,
            "valid_rows": build_report.valid_rows,
            "n_classes": int(built_df["label"].nunique()) if "label" in built_df.columns and not built_df.empty else 0,
            "n_source_tables": int(len(source_report)),
            **asdict(build_report),
        })

    train_cohort = train_cohorts[0]
    train_df = cohort_results[train_cohort.name]["built_df"]

    base_training_metrics, importance_tables, trained_models, feature_sets = run_experiment_suite(
        train_df,
        model_families=study.model_families,
    )
    training_metrics = base_training_metrics.copy()
    repeated_holdout = run_repeated_holdout_experiment_suite(
        train_df,
        model_families=study.model_families,
    )
    gene_training_metrics = {
        name: table
        for name, table in run_gene_stratified_experiments(
            train_df,
            model_families=study.model_families,
        ).items()
    }
    gene_specialist_manifest = build_gene_specialist_manifest(
        gene_training_metrics=gene_training_metrics,
        train_df=train_df,
        feature_sets=feature_sets,
        global_training_metrics=base_training_metrics,
        primary_metric=study.primary_metric,
    )
    trained_gene_specialists = train_gene_specialist_models(
        train_df=train_df,
        specialist_manifest=gene_specialist_manifest,
        feature_sets=feature_sets,
        global_trained_models=trained_models,
    )
    gene_specialist_training = _build_gene_specialist_training_row(
        specialist_manifest=gene_specialist_manifest,
        trained_gene_specialists=trained_gene_specialists,
        primary_metric=study.primary_metric,
    )
    if not gene_specialist_training.empty:
        training_metrics = pd.concat([training_metrics, gene_specialist_training], ignore_index=True)
        training_metrics = training_metrics.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    gene_adaptive_blend_manifest = build_gene_adaptive_blend_manifest(
        gene_training_metrics=gene_training_metrics,
        train_df=train_df,
        feature_sets=feature_sets,
        global_training_metrics=base_training_metrics,
        primary_metric=study.primary_metric,
        baseline_experiment=study.baseline_experiment,
    )
    trained_gene_adaptive_blends = train_gene_adaptive_blend_models(
        train_df=train_df,
        blend_manifest=gene_adaptive_blend_manifest,
        feature_sets=feature_sets,
        global_trained_models=trained_models,
    )
    gene_adaptive_blend_training = _build_gene_adaptive_blend_training_row(
        blend_manifest=gene_adaptive_blend_manifest,
        trained_gene_blends=trained_gene_adaptive_blends,
    )
    if not gene_adaptive_blend_training.empty:
        training_metrics = pd.concat([training_metrics, gene_adaptive_blend_training], ignore_index=True)
        training_metrics = training_metrics.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    gene_robust_blend_manifest = build_gene_robust_blend_manifest(
        gene_training_metrics=gene_training_metrics,
        train_df=train_df,
        feature_sets=feature_sets,
        global_training_metrics=base_training_metrics,
        baseline_experiment=study.baseline_experiment,
    )
    trained_gene_robust_blends = train_gene_adaptive_blend_models(
        train_df=train_df,
        blend_manifest=gene_robust_blend_manifest,
        feature_sets=feature_sets,
        global_trained_models=trained_models,
    )
    gene_robust_blend_training = _build_gene_adaptive_blend_training_row(
        blend_manifest=gene_robust_blend_manifest,
        trained_gene_blends=trained_gene_robust_blends,
        experiment_name="hybrid_external_gene_robust_blend",
        model_family="gene_robust_blend",
    )
    if not gene_robust_blend_training.empty:
        training_metrics = pd.concat([training_metrics, gene_robust_blend_training], ignore_index=True)
        training_metrics = training_metrics.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    gene_calibrated_blend_manifest = build_gene_calibrated_blend_manifest(
        train_df=train_df,
        blend_manifest=gene_adaptive_blend_manifest,
        feature_sets=feature_sets,
    )
    trained_gene_calibrated_blends = train_gene_calibrated_blend_models(
        train_df=train_df,
        blend_manifest=gene_calibrated_blend_manifest,
        feature_sets=feature_sets,
        global_trained_models=trained_models,
    )
    gene_calibrated_blend_training = _build_gene_calibrated_blend_training_row(
        blend_manifest=gene_calibrated_blend_manifest,
        trained_gene_blends=trained_gene_calibrated_blends,
    )
    if not gene_calibrated_blend_training.empty:
        training_metrics = pd.concat([training_metrics, gene_calibrated_blend_training], ignore_index=True)
        training_metrics = training_metrics.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    training_mode = str(train_df["prime_mode"].dropna().iloc[0]) if "prime_mode" in train_df.columns and not train_df["prime_mode"].dropna().empty else None
    model_paths = save_trained_models(
        trained_models,
        output_dir=str(output_root / "models"),
        feature_sets=feature_sets,
        metrics_df=base_training_metrics,
        training_mode=training_mode,
    )
    feature_set_leaderboard = build_feature_set_leaderboard(training_metrics)
    model_family_summary = build_model_family_summary(training_metrics)
    consensus_members = select_consensus_members(
        training_metrics=base_training_metrics,
        primary_metric=study.primary_metric,
        top_k=study.consensus_top_k,
    )

    training_metrics_path = output_root / "study_training_metrics.csv"
    training_metrics.to_csv(training_metrics_path, index=False)

    repeated_holdout_path = output_root / "study_repeated_holdout.csv"
    repeated_holdout.to_csv(repeated_holdout_path, index=False)

    feature_set_leaderboard_path = output_root / "study_best_by_feature_set.csv"
    feature_set_leaderboard.to_csv(feature_set_leaderboard_path, index=False)

    model_family_summary_path = output_root / "study_model_family_summary.csv"
    model_family_summary.to_csv(model_family_summary_path, index=False)

    consensus_members_path = output_root / "study_consensus_members.csv"
    pd.DataFrame(
        [
            {"consensus_experiment": f"consensus_top{len(consensus_members)}", "member_rank": index + 1, "member_experiment": experiment_name}
            for index, experiment_name in enumerate(consensus_members)
        ]
    ).to_csv(consensus_members_path, index=False)

    importance_paths = _export_named_tables(importance_tables, str(output_root), "study_feature_importance")
    gene_training_paths = _export_named_tables(gene_training_metrics, str(output_root), "study_gene_training_metrics")
    gene_specialist_manifest_path = output_root / "study_gene_specialist_manifest.csv"
    gene_specialist_manifest.to_csv(gene_specialist_manifest_path, index=False)
    gene_adaptive_blend_manifest_path = output_root / "study_gene_adaptive_blend_manifest.csv"
    gene_adaptive_blend_manifest.to_csv(gene_adaptive_blend_manifest_path, index=False)
    gene_robust_blend_manifest_path = output_root / "study_gene_robust_blend_manifest.csv"
    gene_robust_blend_manifest.to_csv(gene_robust_blend_manifest_path, index=False)
    gene_calibrated_blend_manifest_path = output_root / "study_gene_calibrated_blend_manifest.csv"
    gene_calibrated_blend_manifest.to_csv(gene_calibrated_blend_manifest_path, index=False)

    external_metric_tables = []
    external_score_paths = {}
    pairwise_tables = []
    consensus_tables = []
    for cohort in study.cohorts or []:
        if cohort.role == "train":
            continue
        built_df = cohort_results[cohort.name]["built_df"]
        metrics_df, score_frame = evaluate_experiment_suite_on_cohort(
            trained_models=trained_models,
            feature_sets=feature_sets,
            df=built_df,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
        )
        metrics_df, score_frame, consensus_manifest = add_consensus_to_evaluation(
            metrics_df=metrics_df,
            score_frame=score_frame,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
            consensus_members=consensus_members,
        )
        specialist_metrics, specialist_score_frame = evaluate_gene_specialist_on_cohort(
            trained_gene_specialists=trained_gene_specialists,
            df=built_df,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
        )
        metrics_df, score_frame = add_gene_specialist_to_evaluation(
            metrics_df=metrics_df,
            score_frame=score_frame,
            specialist_metrics=specialist_metrics,
            specialist_score_frame=specialist_score_frame,
        )
        blend_metrics, blend_score_frame = evaluate_gene_adaptive_blend_on_cohort(
            trained_gene_blends=trained_gene_adaptive_blends,
            df=built_df,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
        )
        metrics_df, score_frame = add_gene_specialist_to_evaluation(
            metrics_df=metrics_df,
            score_frame=score_frame,
            specialist_metrics=blend_metrics,
            specialist_score_frame=blend_score_frame,
        )
        robust_blend_metrics, robust_blend_score_frame = evaluate_gene_adaptive_blend_on_cohort(
            trained_gene_blends=trained_gene_robust_blends,
            df=built_df,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
            experiment_name="hybrid_external_gene_robust_blend",
            model_family="gene_robust_blend",
        )
        metrics_df, score_frame = add_gene_specialist_to_evaluation(
            metrics_df=metrics_df,
            score_frame=score_frame,
            specialist_metrics=robust_blend_metrics,
            specialist_score_frame=robust_blend_score_frame,
        )
        calibrated_blend_metrics, calibrated_blend_score_frame = evaluate_gene_calibrated_blend_on_cohort(
            trained_gene_blends=trained_gene_calibrated_blends,
            df=built_df,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
        )
        metrics_df, score_frame = add_gene_specialist_to_evaluation(
            metrics_df=metrics_df,
            score_frame=score_frame,
            specialist_metrics=calibrated_blend_metrics,
            specialist_score_frame=calibrated_blend_score_frame,
        )
        pairwise_df = build_pairwise_comparison_table(
            score_frame=score_frame,
            cohort_name=cohort.name,
            cohort_role=cohort.role,
            baseline_experiment=study.baseline_experiment,
            n_bootstrap=study.n_bootstrap,
        )

        cohort_slug = _slugify(cohort.name)
        score_path = output_root / f"study_scores_{cohort_slug}.csv"
        metrics_path = output_root / f"study_external_metrics_{cohort_slug}.csv"
        pairwise_path = output_root / f"study_pairwise_{cohort_slug}.csv"
        consensus_path = output_root / f"study_consensus_{cohort_slug}.csv"
        score_frame.to_csv(score_path, index=False)
        metrics_df.to_csv(metrics_path, index=False)
        pairwise_df.to_csv(pairwise_path, index=False)
        consensus_manifest.to_csv(consensus_path, index=False)

        external_metric_tables.append(metrics_df)
        pairwise_tables.append(pairwise_df)
        if not consensus_manifest.empty:
            consensus_tables.append(consensus_manifest.assign(cohort=cohort.name, cohort_role=cohort.role))
        external_score_paths[cohort.name] = str(score_path)
        cohort_results[cohort.name]["external_metrics_path"] = str(metrics_path)
        cohort_results[cohort.name]["pairwise_path"] = str(pairwise_path)
        cohort_results[cohort.name]["consensus_path"] = str(consensus_path)

    external_evaluation_metrics = pd.concat(external_metric_tables, ignore_index=True) if external_metric_tables else pd.DataFrame()
    external_pairwise = pd.concat(pairwise_tables, ignore_index=True) if pairwise_tables else pd.DataFrame()
    external_consensus_manifest = pd.concat(consensus_tables, ignore_index=True) if consensus_tables else pd.DataFrame()

    external_metrics_path = output_root / "study_external_evaluation.csv"
    external_pairwise_path = output_root / "study_external_pairwise.csv"
    external_consensus_path = output_root / "study_external_consensus.csv"
    external_evaluation_metrics.to_csv(external_metrics_path, index=False)
    external_pairwise.to_csv(external_pairwise_path, index=False)
    external_consensus_manifest.to_csv(external_consensus_path, index=False)

    cohort_manifest = pd.DataFrame(manifest_rows)
    cohort_manifest_path = output_root / "study_cohort_manifest.csv"
    cohort_manifest.to_csv(cohort_manifest_path, index=False)

    results = {
        "study_design": study,
        "cohort_manifest": cohort_manifest,
        "cohort_manifest_path": str(cohort_manifest_path),
        "cohort_results": cohort_results,
        "training_metrics": training_metrics,
        "training_metrics_path": str(training_metrics_path),
        "training_repeated_holdout": repeated_holdout,
        "training_repeated_holdout_path": str(repeated_holdout_path),
        "feature_set_leaderboard": feature_set_leaderboard,
        "feature_set_leaderboard_path": str(feature_set_leaderboard_path),
        "model_family_summary": model_family_summary,
        "model_family_summary_path": str(model_family_summary_path),
        "consensus_members": consensus_members,
        "consensus_members_path": str(consensus_members_path),
        "gene_training_metrics": gene_training_metrics,
        "gene_training_paths": gene_training_paths,
        "gene_specialist_manifest": gene_specialist_manifest,
        "gene_specialist_manifest_path": str(gene_specialist_manifest_path),
        "gene_adaptive_blend_manifest": gene_adaptive_blend_manifest,
        "gene_adaptive_blend_manifest_path": str(gene_adaptive_blend_manifest_path),
        "gene_robust_blend_manifest": gene_robust_blend_manifest,
        "gene_robust_blend_manifest_path": str(gene_robust_blend_manifest_path),
        "gene_calibrated_blend_manifest": gene_calibrated_blend_manifest,
        "gene_calibrated_blend_manifest_path": str(gene_calibrated_blend_manifest_path),
        "importance_tables": importance_tables,
        "importance_paths": importance_paths,
        "feature_sets": feature_sets,
        "model_paths": model_paths,
        "trained_gene_specialists": trained_gene_specialists,
        "trained_gene_adaptive_blends": trained_gene_adaptive_blends,
        "trained_gene_robust_blends": trained_gene_robust_blends,
        "trained_gene_calibrated_blends": trained_gene_calibrated_blends,
        "external_evaluation_metrics": external_evaluation_metrics,
        "external_evaluation_path": str(external_metrics_path),
        "external_pairwise_comparisons": external_pairwise,
        "external_pairwise_path": str(external_pairwise_path),
        "external_consensus_manifest": external_consensus_manifest,
        "external_consensus_path": str(external_consensus_path),
        "external_score_paths": external_score_paths,
        "robustness_target_experiment": "hybrid_external_gene_robust_blend" if trained_gene_robust_blends else "",
    }

    cohort_independence_paths = export_cohort_independence_package(
        [
            {
                "cohort_name": cohort_name,
                "role": payload["spec"].role,
                "dataframe": payload["built_df"],
            }
            for cohort_name, payload in cohort_results.items()
        ],
        output_dir=str(output_root),
    )
    results.update(cohort_independence_paths)
    cohort_freeze_paths = export_study_cohort_freeze(
        config_path=config_path,
        output_dir=str(output_root),
    )
    results.update(cohort_freeze_paths)

    summary_text = build_study_summary_report(results)
    summary_path = output_root / "study_summary_report.txt"
    summary_path.write_text(summary_text, encoding="utf-8")
    results["study_summary_report_path"] = str(summary_path)
    dossier_paths = export_study_scientific_dossier(
        results,
        output_dir=str(output_root),
        report_context=report_context,
    )
    results.update(dossier_paths)
    comparative_paths = export_comparative_evidence_package(
        results,
        output_dir=str(output_root),
    )
    results.update(comparative_paths)
    claim_strength_paths = export_claim_strength_package(
        results,
        output_dir=str(output_root),
    )
    results.update(claim_strength_paths)
    external_robustness_paths = export_external_robustness_package(
        results,
        output_dir=str(output_root),
    )
    results.update(external_robustness_paths)
    prime_intelligence_paths = export_prime_intelligence_package(
        results,
        output_dir=str(output_root),
    )
    results.update(prime_intelligence_paths)
    readiness_paths = export_publication_readiness_package(
        results,
        output_dir=str(output_root),
        report_context=report_context,
    )
    results.update(readiness_paths)
    baseline_paths = export_baseline_coverage_assessment(
        results,
        output_dir=str(output_root),
    )
    results.update(baseline_paths)
    methods_paths = export_methods_package(
        results,
        output_dir=str(output_root),
        report_context=report_context,
    )
    results.update(methods_paths)
    manuscript_paths = export_manuscript_package(
        results,
        output_dir=str(output_root),
        report_context=report_context,
    )
    results.update(manuscript_paths)
    validation_lock_paths = export_study_validation_lock(
        results,
        output_dir=str(output_root),
        report_context=report_context,
    )
    results.update(validation_lock_paths)
    results.update(
        export_study_release_manifest(
            config_path=config_path,
            results=results,
            output_dir=str(output_root),
            report_context=report_context,
        )
    )
    return results
