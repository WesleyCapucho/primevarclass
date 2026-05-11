from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .pooled_external_support import get_or_build_pooled_external_support


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float("nan")
    if np.isnan(numeric):
        return float("nan")
    return numeric


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _fmt_metric(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.4f}"


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _criterion_row(
    criterion_id: str,
    title: str,
    weight: float,
    score_percent: int,
    evidence: str,
    next_step: str,
    critical: bool = False,
) -> dict:
    normalized = max(0, min(100, int(score_percent)))
    return {
        "criterion_id": criterion_id,
        "title": title,
        "weight": float(weight),
        "score_percent": normalized,
        "status": _status_from_percent(normalized),
        "critical": bool(critical),
        "evidence": evidence,
        "next_step": next_step,
    }


def _feature_set_from_experiment(experiment_name: str) -> str:
    token = str(experiment_name or "")
    if "__" in token:
        return token.split("__", 1)[0]
    return token


def _is_prime_signal(feature_set: str) -> bool:
    token = str(feature_set or "").strip().lower()
    return token.startswith("prime") or token.startswith("hybrid")


def _is_high_confidence_clinical_cohort(cohort_name: Any, cohort_role: Any = "") -> bool:
    token = f"{cohort_name or ''} {cohort_role or ''}".strip().lower()
    if not token:
        return False
    markers = (
        "expert",
        "expert_panel",
        "guideline",
        "practice_guideline",
        "clinvar_expert",
        "expert_external",
    )
    return any(marker in token for marker in markers)


def _safe_mean_percent(values: List[float]) -> int:
    valid = [float(item) for item in values if not np.isnan(float(item))]
    return int(round(float(np.mean(valid)))) if valid else 0


def _normal_cdf(value: float) -> float:
    if np.isnan(value):
        return float("nan")
    return 0.5 * (1.0 + math.erf(float(value) / math.sqrt(2.0)))


def _estimate_standard_error(ci_lower_95: Any, ci_upper_95: Any) -> float:
    lower = _safe_float(ci_lower_95)
    upper = _safe_float(ci_upper_95)
    if np.isnan(lower) or np.isnan(upper) or upper <= lower:
        return float("nan")
    return float((upper - lower) / (2 * 1.96))


def _build_pairwise_auc_table(results: dict) -> pd.DataFrame:
    pairwise = results.get("external_pairwise_comparisons")
    pairwise_df = pairwise.copy() if isinstance(pairwise, pd.DataFrame) else pd.DataFrame()
    if pairwise_df.empty:
        return pd.DataFrame(
            columns=[
                "cohort",
                "cohort_role",
                "experiment",
                "baseline_experiment",
                "metric",
                "delta_mean",
                "ci_lower_95",
                "ci_upper_95",
                "n_bootstrap_valid",
                "feature_set",
                "is_prime_signal",
            ]
        )

    if "metric" in pairwise_df.columns:
        pairwise_df = pairwise_df[pairwise_df["metric"].astype(str) == "auc_roc"].copy()
    if pairwise_df.empty:
        return pairwise_df

    pairwise_df["feature_set"] = pairwise_df["experiment"].astype(str).map(_feature_set_from_experiment)
    pairwise_df["is_prime_signal"] = pairwise_df["feature_set"].map(_is_prime_signal)
    pairwise_df["is_high_confidence_clinical_cohort"] = pairwise_df.apply(
        lambda row: _is_high_confidence_clinical_cohort(row.get("cohort"), row.get("cohort_role")),
        axis=1,
    )
    pairwise_df["delta_mean"] = pairwise_df["delta_mean"].map(_safe_float)
    pairwise_df["ci_lower_95"] = pairwise_df["ci_lower_95"].map(_safe_float)
    pairwise_df["ci_upper_95"] = pairwise_df["ci_upper_95"].map(_safe_float)
    pairwise_df["delta_se"] = pairwise_df.apply(
        lambda row: _estimate_standard_error(row.get("ci_lower_95"), row.get("ci_upper_95")),
        axis=1,
    )
    pairwise_df["supported_gain"] = pairwise_df["ci_lower_95"].gt(0)
    pairwise_df["positive_gain"] = pairwise_df["delta_mean"].gt(0)
    return pairwise_df.reset_index(drop=True)


def _build_internal_ranking(training_metrics: pd.DataFrame, primary_metric: str) -> pd.DataFrame:
    if training_metrics.empty:
        return pd.DataFrame(columns=["experiment", "feature_set", "internal_rank", "internal_primary_metric"])
    metric_name = primary_metric if primary_metric in training_metrics.columns else "auc_roc"
    ranked = training_metrics.sort_values(
        [metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    ranked = ranked.copy()
    ranked["internal_rank"] = np.arange(1, len(ranked) + 1)
    ranked["feature_set"] = ranked["experiment"].astype(str).map(_feature_set_from_experiment)
    ranked["internal_primary_metric"] = ranked[metric_name]
    columns = [col for col in ["experiment", "feature_set", "internal_rank", "internal_primary_metric", "auc_roc", "auc_pr", "mcc"] if col in ranked.columns]
    return ranked[columns].copy()


def _build_experiment_support_table(pairwise_auc_df: pd.DataFrame, internal_ranking: pd.DataFrame) -> pd.DataFrame:
    if pairwise_auc_df.empty:
        return pd.DataFrame()

    group = (
        pairwise_auc_df.groupby(["experiment", "feature_set", "is_prime_signal", "baseline_experiment"], as_index=False)
        .agg(
            n_external_cohorts=("cohort", "nunique"),
            n_positive_gains=("positive_gain", "sum"),
            n_supported_gains=("supported_gain", "sum"),
            mean_delta_auc_roc=("delta_mean", "mean"),
            median_delta_auc_roc=("delta_mean", "median"),
            mean_ci_lower_95=("ci_lower_95", "mean"),
            best_delta_auc_roc=("delta_mean", "max"),
        )
    )
    group["positive_gain_rate_percent"] = np.where(
        group["n_external_cohorts"].gt(0),
        np.round((group["n_positive_gains"] / group["n_external_cohorts"]) * 100),
        0,
    ).astype(int)
    group["supported_gain_rate_percent"] = np.where(
        group["n_external_cohorts"].gt(0),
        np.round((group["n_supported_gains"] / group["n_external_cohorts"]) * 100),
        0,
    ).astype(int)

    high_conf_rows: List[dict] = []
    for keys, subset in pairwise_auc_df.groupby(
        ["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
        as_index=False,
        dropna=False,
    ):
        experiment, feature_set, is_prime_signal, baseline_experiment = keys
        clinical_subset = subset[subset["is_high_confidence_clinical_cohort"]].copy()
        n_clinical = int(clinical_subset["cohort"].astype(str).nunique()) if not clinical_subset.empty else 0
        n_clinical_positive = (
            int(clinical_subset.groupby("cohort", dropna=False)["positive_gain"].any().sum()) if n_clinical else 0
        )
        n_clinical_supported = (
            int(clinical_subset.groupby("cohort", dropna=False)["supported_gain"].any().sum()) if n_clinical else 0
        )
        high_conf_rows.append(
            {
                "experiment": experiment,
                "feature_set": feature_set,
                "is_prime_signal": bool(is_prime_signal),
                "baseline_experiment": baseline_experiment,
                "n_high_confidence_clinical_cohorts": n_clinical,
                "high_confidence_clinical_positive_rate_percent": int(round((n_clinical_positive / n_clinical) * 100))
                if n_clinical
                else 0,
                "high_confidence_clinical_supported_rate_percent": int(round((n_clinical_supported / n_clinical) * 100))
                if n_clinical
                else 0,
            }
        )
    if high_conf_rows:
        group = group.merge(
            pd.DataFrame(high_conf_rows),
            on=["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
            how="left",
        )
    else:
        group["n_high_confidence_clinical_cohorts"] = 0
        group["high_confidence_clinical_positive_rate_percent"] = 0
        group["high_confidence_clinical_supported_rate_percent"] = 0

    if not internal_ranking.empty:
        group = group.merge(internal_ranking, on=["experiment", "feature_set"], how="left")
    else:
        group["internal_rank"] = np.nan
        group["internal_primary_metric"] = np.nan

    return group.sort_values(
        ["supported_gain_rate_percent", "positive_gain_rate_percent", "mean_delta_auc_roc", "experiment"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def _build_experiment_meta_analysis_table(pairwise_auc_df: pd.DataFrame) -> pd.DataFrame:
    if pairwise_auc_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for keys, subset in pairwise_auc_df.groupby(
        ["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
        as_index=False,
        dropna=False,
    ):
        experiment, feature_set, is_prime_signal, baseline_experiment = keys
        valid = subset.copy()
        valid["delta_se"] = valid["delta_se"].map(_safe_float)
        valid = valid[valid["delta_se"].gt(0)].copy()

        aggregate_delta = float("nan")
        aggregate_ci_lower = float("nan")
        aggregate_ci_upper = float("nan")
        aggregate_supported = False
        aggregate_positive = False
        aggregate_confidence = 0

        if not valid.empty:
            weights = 1.0 / np.square(valid["delta_se"].to_numpy(dtype=float))
            deltas = valid["delta_mean"].to_numpy(dtype=float)
            total_weight = float(np.sum(weights))
            if total_weight > 0:
                aggregate_delta = float(np.sum(weights * deltas) / total_weight)
                aggregate_se = float(math.sqrt(1.0 / total_weight))
                aggregate_ci_lower = float(aggregate_delta - (1.96 * aggregate_se))
                aggregate_ci_upper = float(aggregate_delta + (1.96 * aggregate_se))
                aggregate_supported = bool(aggregate_ci_lower > 0)
                aggregate_positive = bool(aggregate_delta > 0)
                if aggregate_se > 0:
                    aggregate_confidence = int(round(float(_normal_cdf(aggregate_delta / aggregate_se)) * 100))
                else:
                    aggregate_confidence = 100 if aggregate_positive else 0

        rows.append(
            {
                "experiment": experiment,
                "feature_set": feature_set,
                "is_prime_signal": bool(is_prime_signal),
                "baseline_experiment": baseline_experiment,
                "n_meta_cohorts": int(subset["cohort"].astype(str).nunique()),
                "n_meta_valid": int(len(valid)),
                "aggregate_delta_auc_roc": aggregate_delta,
                "aggregate_ci_lower_95": aggregate_ci_lower,
                "aggregate_ci_upper_95": aggregate_ci_upper,
                "aggregate_supported_gain": aggregate_supported,
                "aggregate_positive_gain": aggregate_positive,
                "aggregate_directional_confidence_percent": aggregate_confidence,
            }
        )

    return pd.DataFrame(rows).sort_values(
        [
            "aggregate_supported_gain",
            "aggregate_directional_confidence_percent",
            "aggregate_delta_auc_roc",
            "experiment",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def _build_pooled_metric_table(pooled_support_df: pd.DataFrame, metric_name: str) -> pd.DataFrame:
    if pooled_support_df.empty:
        return pd.DataFrame()
    subset = pooled_support_df[pooled_support_df["metric"].astype(str) == str(metric_name)].copy()
    if subset.empty:
        return pd.DataFrame()
    rename_map = {
        "pooled_candidate_value": f"pooled_{metric_name}_candidate_value",
        "pooled_baseline_value": f"pooled_{metric_name}_baseline_value",
        "pooled_delta_mean": f"pooled_{metric_name}_delta_mean",
        "pooled_observed_delta": f"pooled_{metric_name}_observed_delta",
        "pooled_ci_lower_95": f"pooled_{metric_name}_ci_lower_95",
        "pooled_ci_upper_95": f"pooled_{metric_name}_ci_upper_95",
        "pooled_supported_gain": f"pooled_{metric_name}_supported_gain",
        "pooled_positive_gain": f"pooled_{metric_name}_positive_gain",
        "pooled_directional_confidence_percent": f"pooled_{metric_name}_directional_confidence_percent",
        "n_bootstrap_valid": f"pooled_{metric_name}_bootstrap_valid",
    }
    base_columns = [
        "experiment",
        "baseline_experiment",
        "feature_set",
        "is_prime_signal",
        "n_external_cohorts",
        "n_variants",
        "n_high_confidence_clinical_cohorts",
        "n_high_confidence_clinical_variants",
    ]
    metric_columns = base_columns + list(rename_map.keys())
    subset = subset[metric_columns].rename(columns=rename_map)
    return subset.reset_index(drop=True)


def _build_feature_set_support_table(experiment_support_df: pd.DataFrame) -> pd.DataFrame:
    if experiment_support_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for feature_set, subset in experiment_support_df.groupby("feature_set"):
        best_row = subset.sort_values(
            ["supported_gain_rate_percent", "positive_gain_rate_percent", "mean_delta_auc_roc", "experiment"],
            ascending=[False, False, False, True],
        ).iloc[0]
        rows.append(
            {
                "feature_set": feature_set,
                "is_prime_signal": bool(best_row.get("is_prime_signal")),
                "best_experiment": best_row.get("experiment"),
                "n_experiments": int(len(subset)),
                "max_supported_gain_rate_percent": _safe_int(best_row.get("supported_gain_rate_percent")),
                "max_positive_gain_rate_percent": _safe_int(best_row.get("positive_gain_rate_percent")),
                "best_mean_delta_auc_roc": _safe_float(best_row.get("mean_delta_auc_roc")),
                "best_aggregate_supported_gain": bool(best_row.get("aggregate_supported_gain")),
                "best_aggregate_directional_confidence_percent": _safe_int(best_row.get("aggregate_directional_confidence_percent")),
                "best_aggregate_delta_auc_roc": _safe_float(best_row.get("aggregate_delta_auc_roc")),
                "best_internal_rank": _safe_float(best_row.get("internal_rank")),
            }
        )
    feature_df = pd.DataFrame(rows)
    return feature_df.sort_values(
        [
            "best_aggregate_supported_gain",
            "best_aggregate_directional_confidence_percent",
            "max_supported_gain_rate_percent",
            "max_positive_gain_rate_percent",
            "best_mean_delta_auc_roc",
            "feature_set",
        ],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)


def _build_cohort_support_table(pairwise_auc_df: pd.DataFrame) -> pd.DataFrame:
    if pairwise_auc_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for cohort_name, subset in pairwise_auc_df.groupby("cohort"):
        supported_subset = subset[subset["supported_gain"]].sort_values(
            ["delta_mean", "ci_lower_95", "experiment"],
            ascending=[False, False, True],
        )
        positive_subset = subset[subset["positive_gain"]].sort_values(
            ["delta_mean", "ci_lower_95", "experiment"],
            ascending=[False, False, True],
        )
        prime_supported = bool(((subset["is_prime_signal"]) & (subset["supported_gain"])).any())
        prime_positive = bool(((subset["is_prime_signal"]) & (subset["positive_gain"])).any())

        best_supported = supported_subset.iloc[0].to_dict() if not supported_subset.empty else {}
        best_positive = positive_subset.iloc[0].to_dict() if not positive_subset.empty else {}

        rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": subset["cohort_role"].astype(str).iloc[0] if "cohort_role" in subset.columns else "external_test",
                "is_high_confidence_clinical_cohort": bool(subset["is_high_confidence_clinical_cohort"].any()),
                "n_pairwise_experiments": int(len(subset)),
                "has_supported_gain": bool(not supported_subset.empty),
                "has_positive_gain": bool(not positive_subset.empty),
                "prime_supported_gain": prime_supported,
                "prime_positive_gain": prime_positive,
                "best_supported_experiment": best_supported.get("experiment"),
                "best_supported_feature_set": best_supported.get("feature_set"),
                "best_supported_delta_auc_roc": _safe_float(best_supported.get("delta_mean")),
                "best_supported_ci_lower_95": _safe_float(best_supported.get("ci_lower_95")),
                "best_positive_experiment": best_positive.get("experiment"),
                "best_positive_feature_set": best_positive.get("feature_set"),
                "best_positive_delta_auc_roc": _safe_float(best_positive.get("delta_mean")),
            }
        )
    cohort_df = pd.DataFrame(rows)
    return cohort_df.sort_values(["cohort"], ascending=[True]).reset_index(drop=True)


def build_comparative_evidence_assessment(results: dict) -> dict:
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Comparative Evidence")
    primary_metric = str(getattr(study_design, "primary_metric", "auc_roc") or "auc_roc")
    baseline_experiment = str(getattr(study_design, "baseline_experiment", "external_predictors_only") or "external_predictors_only")

    training_metrics = results.get("training_metrics")
    training_df = training_metrics.copy() if isinstance(training_metrics, pd.DataFrame) else pd.DataFrame()
    internal_ranking = _build_internal_ranking(training_df, primary_metric=primary_metric)
    pairwise_auc_df = _build_pairwise_auc_table(results)
    experiment_support_df = _build_experiment_support_table(pairwise_auc_df, internal_ranking)
    experiment_meta_df = _build_experiment_meta_analysis_table(pairwise_auc_df)
    pooled_support_df = get_or_build_pooled_external_support(results)
    pooled_auc_roc_df = _build_pooled_metric_table(pooled_support_df, "auc_roc")
    pooled_auc_pr_df = _build_pooled_metric_table(pooled_support_df, "auc_pr")
    if not experiment_support_df.empty and not experiment_meta_df.empty:
        experiment_support_df = experiment_support_df.merge(
            experiment_meta_df,
            on=["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
            how="left",
        )
    elif experiment_support_df.empty:
        experiment_support_df = experiment_meta_df.copy()
    if not experiment_support_df.empty and not pooled_auc_roc_df.empty:
        experiment_support_df = experiment_support_df.merge(
            pooled_auc_roc_df,
            on=["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
            how="left",
        )
    if not experiment_support_df.empty and not pooled_auc_pr_df.empty:
        experiment_support_df = experiment_support_df.merge(
            pooled_auc_pr_df,
            on=["experiment", "feature_set", "is_prime_signal", "baseline_experiment"],
            how="left",
        )
    if not experiment_support_df.empty:
        for column_name, default_value in [
            ("pooled_auc_roc_supported_gain", False),
            ("pooled_auc_pr_supported_gain", False),
            ("pooled_auc_roc_positive_gain", False),
            ("pooled_auc_pr_positive_gain", False),
            ("pooled_auc_roc_directional_confidence_percent", 0),
            ("pooled_auc_pr_directional_confidence_percent", 0),
            ("pooled_auc_roc_delta_mean", float("nan")),
            ("pooled_auc_pr_delta_mean", float("nan")),
            ("pooled_auc_roc_ci_lower_95", float("nan")),
            ("pooled_auc_pr_ci_lower_95", float("nan")),
            ("pooled_auc_roc_ci_upper_95", float("nan")),
            ("pooled_auc_pr_ci_upper_95", float("nan")),
        ]:
            if column_name not in experiment_support_df.columns:
                experiment_support_df[column_name] = default_value
        experiment_support_df["pooled_cross_metric_supported_gain"] = (
            experiment_support_df["pooled_auc_roc_supported_gain"].fillna(False).astype(bool)
            & experiment_support_df["pooled_auc_pr_supported_gain"].fillna(False).astype(bool)
        )
        experiment_support_df["pooled_cross_metric_positive_gain"] = (
            experiment_support_df["pooled_auc_roc_positive_gain"].fillna(False).astype(bool)
            & experiment_support_df["pooled_auc_pr_positive_gain"].fillna(False).astype(bool)
        )
        experiment_support_df["pooled_cross_metric_directional_confidence_percent"] = (
            (
                experiment_support_df["pooled_auc_roc_directional_confidence_percent"].map(_safe_int)
                + experiment_support_df["pooled_auc_pr_directional_confidence_percent"].map(_safe_int)
            )
            / 2.0
        ).round().astype(int)
    feature_support_df = _build_feature_set_support_table(experiment_support_df)
    cohort_support_df = _build_cohort_support_table(pairwise_auc_df)

    external_metrics = results.get("external_evaluation_metrics")
    external_df = external_metrics.copy() if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()
    if not external_df.empty and "cohort_role" in external_df.columns:
        n_external_cohorts = int(external_df[external_df["cohort_role"].astype(str) != "train"]["cohort"].astype(str).nunique())
    elif not external_df.empty and "cohort" in external_df.columns:
        n_external_cohorts = int(external_df["cohort"].astype(str).nunique())
    else:
        n_external_cohorts = int(cohort_support_df["cohort"].astype(str).nunique()) if not cohort_support_df.empty else 0

    n_pairwise_cohorts = int(cohort_support_df["cohort"].astype(str).nunique()) if not cohort_support_df.empty else 0
    pairwise_coverage_percent = int(round((n_pairwise_cohorts / n_external_cohorts) * 100)) if n_external_cohorts else 0
    supported_gain_rate_percent = int(round(cohort_support_df["has_supported_gain"].mean() * 100)) if not cohort_support_df.empty else 0
    positive_gain_rate_percent = int(round(cohort_support_df["has_positive_gain"].mean() * 100)) if not cohort_support_df.empty else 0
    prime_supported_gain_rate_percent = int(round(cohort_support_df["prime_supported_gain"].mean() * 100)) if not cohort_support_df.empty else 0
    prime_positive_gain_rate_percent = int(round(cohort_support_df["prime_positive_gain"].mean() * 100)) if not cohort_support_df.empty else 0
    high_conf_cohort_df = (
        cohort_support_df[cohort_support_df["is_high_confidence_clinical_cohort"]].copy()
        if not cohort_support_df.empty and "is_high_confidence_clinical_cohort" in cohort_support_df.columns
        else pd.DataFrame()
    )
    high_confidence_clinical_positive_rate_percent = (
        int(round(high_conf_cohort_df["has_positive_gain"].mean() * 100)) if not high_conf_cohort_df.empty else 0
    )
    high_confidence_clinical_supported_rate_percent = (
        int(round(high_conf_cohort_df["has_supported_gain"].mean() * 100)) if not high_conf_cohort_df.empty else 0
    )

    best_internal = internal_ranking.iloc[0].to_dict() if not internal_ranking.empty else {}
    best_internal_experiment = str(best_internal.get("experiment") or "")
    best_internal_feature_set = str(best_internal.get("feature_set") or "")
    matching_internal = experiment_support_df[experiment_support_df["experiment"].astype(str) == best_internal_experiment].copy()
    if matching_internal.empty and best_internal_feature_set:
        matching_internal = feature_support_df[feature_support_df["feature_set"].astype(str) == best_internal_feature_set].copy()
        internal_external_alignment_percent = (
            100 if not matching_internal.empty and _safe_float(matching_internal.iloc[0].get("best_mean_delta_auc_roc")) > 0
            else 35 if not matching_internal.empty
            else 0
        )
    else:
        internal_external_alignment_percent = (
            100 if not matching_internal.empty and _safe_float(matching_internal.iloc[0].get("mean_delta_auc_roc")) > 0
            else 35 if not matching_internal.empty
            else 0
        )

    dominant_feature_set = None
    winning_consistency_percent = 0
    if not cohort_support_df.empty:
        feature_tokens = cohort_support_df["best_supported_feature_set"].fillna("")
        feature_tokens = feature_tokens.where(feature_tokens.astype(bool), cohort_support_df["best_positive_feature_set"].fillna(""))
        feature_tokens = feature_tokens[feature_tokens.astype(str) != ""]
        if not feature_tokens.empty:
            dominant_feature_set = str(feature_tokens.value_counts().index[0])
            winning_consistency_percent = int(round((feature_tokens.value_counts().iloc[0] / len(cohort_support_df)) * 100))

    best_supported_experiment = None
    best_supported_feature_set = None
    best_supported_delta_auc_roc = float("nan")
    aggregate_supported_experiment = None
    aggregate_supported_feature_set = None
    aggregate_delta_auc_roc = float("nan")
    aggregate_ci_lower_95 = float("nan")
    aggregate_ci_upper_95 = float("nan")
    aggregate_directional_confidence_percent = 0
    aggregate_supported_gain = False
    pooled_supported_experiment = None
    pooled_supported_feature_set = None
    pooled_delta_auc_roc = float("nan")
    pooled_ci_lower_95 = float("nan")
    pooled_ci_upper_95 = float("nan")
    pooled_directional_confidence_percent = 0
    pooled_supported_gain = False
    pooled_cross_metric_supported_gain = False
    pooled_cross_metric_directional_confidence_percent = 0
    high_confidence_clinical_leadership_percent = 0
    high_confidence_clinical_supported_rate_best_percent = 0
    if not experiment_support_df.empty:
        ranked = experiment_support_df.sort_values(
            [
                "pooled_auc_roc_supported_gain",
                "pooled_cross_metric_supported_gain",
                "aggregate_supported_gain",
                "high_confidence_clinical_supported_rate_percent",
                "high_confidence_clinical_positive_rate_percent",
                "pooled_auc_roc_directional_confidence_percent",
                "pooled_cross_metric_directional_confidence_percent",
                "aggregate_directional_confidence_percent",
                "supported_gain_rate_percent",
                "positive_gain_rate_percent",
                "mean_delta_auc_roc",
                "experiment",
            ],
            ascending=[False, False, False, False, False, False, False, False, False, False, False, True],
        )
        top_row = ranked.iloc[0]
        best_supported_experiment = top_row.get("experiment")
        best_supported_feature_set = top_row.get("feature_set")
        best_supported_delta_auc_roc = _safe_float(top_row.get("mean_delta_auc_roc"))
        aggregate_supported_experiment = top_row.get("experiment")
        aggregate_supported_feature_set = top_row.get("feature_set")
        aggregate_delta_auc_roc = _safe_float(top_row.get("aggregate_delta_auc_roc"))
        aggregate_ci_lower_95 = _safe_float(top_row.get("aggregate_ci_lower_95"))
        aggregate_ci_upper_95 = _safe_float(top_row.get("aggregate_ci_upper_95"))
        aggregate_directional_confidence_percent = _safe_int(top_row.get("aggregate_directional_confidence_percent"))
        aggregate_supported_gain = bool(top_row.get("aggregate_supported_gain"))
        pooled_supported_experiment = top_row.get("experiment")
        pooled_supported_feature_set = top_row.get("feature_set")
        pooled_delta_auc_roc = _safe_float(top_row.get("pooled_auc_roc_delta_mean"))
        pooled_ci_lower_95 = _safe_float(top_row.get("pooled_auc_roc_ci_lower_95"))
        pooled_ci_upper_95 = _safe_float(top_row.get("pooled_auc_roc_ci_upper_95"))
        pooled_directional_confidence_percent = _safe_int(top_row.get("pooled_auc_roc_directional_confidence_percent"))
        pooled_supported_gain = bool(top_row.get("pooled_auc_roc_supported_gain"))
        pooled_cross_metric_supported_gain = bool(top_row.get("pooled_cross_metric_supported_gain"))
        pooled_cross_metric_directional_confidence_percent = _safe_int(
            top_row.get("pooled_cross_metric_directional_confidence_percent")
        )
        high_confidence_clinical_leadership_percent = _safe_int(
            top_row.get("high_confidence_clinical_positive_rate_percent")
        )
        high_confidence_clinical_supported_rate_best_percent = _safe_int(
            top_row.get("high_confidence_clinical_supported_rate_percent")
        )
    high_confidence_clinical_score_percent = int(
        round(
            (high_confidence_clinical_leadership_percent * 0.7)
            + (high_confidence_clinical_supported_rate_best_percent * 0.3)
        )
    )

    pooled_auc_roc_support_percent = (
        100
        if pooled_supported_gain
        else pooled_directional_confidence_percent if pooled_delta_auc_roc > 0 else 0
    )
    pooled_cross_metric_support_percent = (
        100
        if pooled_cross_metric_supported_gain
        else pooled_cross_metric_directional_confidence_percent if pooled_directional_confidence_percent > 0 else 0
    )
    supported_external_gain_score = max(supported_gain_rate_percent, pooled_auc_roc_support_percent)
    prime_signal_support_score = max(
        _safe_mean_percent([float(prime_supported_gain_rate_percent), float(prime_positive_gain_rate_percent)]),
        pooled_auc_roc_support_percent if bool(best_supported_feature_set and _is_prime_signal(best_supported_feature_set)) else 0,
    )
    aggregate_multicohort_score = max(
        aggregate_directional_confidence_percent if aggregate_delta_auc_roc > 0 else 0,
        pooled_auc_roc_support_percent,
    )

    criteria = [
        _criterion_row(
            "pairwise_external_coverage",
            "Pairwise external coverage",
            1.0,
            pairwise_coverage_percent,
            f"{n_pairwise_cohorts}/{n_external_cohorts} coortes externas possuem comparacao AUC-ROC vs baseline.",
            "Garantir comparacao pareada AUC-ROC para todas as coortes externas planejadas.",
            critical=True,
        ),
        _criterion_row(
            "supported_external_gain",
            "Supported external gain",
            1.35,
            supported_external_gain_score,
            (
                f"{supported_gain_rate_percent}% das coortes externas apresentam pelo menos um ganho suportado por coorte, "
                f"enquanto o pooled multicohorte para {pooled_supported_experiment or '-'} ficou em "
                f"{_fmt_metric(pooled_delta_auc_roc)} [{_fmt_metric(pooled_ci_lower_95)}, {_fmt_metric(pooled_ci_upper_95)}]."
            ),
            "Buscar ganhos suportados por coorte e manter o suporte pooled multicohorte na rodada final.",
            critical=True,
        ),
        _criterion_row(
            "high_confidence_clinical_leadership",
            "High-confidence clinical leadership",
            0.95,
            high_confidence_clinical_score_percent,
            (
                f"{aggregate_supported_experiment or '-'} lidera as coortes clinicas de alta confianca com "
                f"{high_confidence_clinical_leadership_percent}% de ganho positivo e "
                f"{high_confidence_clinical_supported_rate_best_percent}% de suporte estrito."
            ),
            "Aumentar o suporte estrito nas coortes clinicas de maior confianca para aproximar o estudo de uma alegacao mais forte.",
        ),
        _criterion_row(
            "aggregate_multicohort_direction",
            "Aggregate multicohort direction",
            1.0,
            aggregate_multicohort_score,
            (
                f"Meta-efeito: {aggregate_supported_experiment or '-'} = {_fmt_metric(aggregate_delta_auc_roc)} "
                f"[{_fmt_metric(aggregate_ci_lower_95)}, {_fmt_metric(aggregate_ci_upper_95)}], "
                f"pooled: {pooled_supported_experiment or '-'} = {_fmt_metric(pooled_delta_auc_roc)} "
                f"[{_fmt_metric(pooled_ci_lower_95)}, {_fmt_metric(pooled_ci_upper_95)}] "
                f"com confianca direcional de {pooled_directional_confidence_percent}%."
            ),
            "Consolidar o ganho agregado ate cruzar zero com margem mais confortavel e replicacao multicohorte.",
        ),
        _criterion_row(
            "pooled_cross_metric_support",
            "Pooled cross-metric support",
            1.05,
            pooled_cross_metric_support_percent,
            (
                f"O pooled multicohorte ficou em {pooled_cross_metric_directional_confidence_percent}% "
                "de confianca direcional simultanea para AUC-ROC e AUC-PR."
            ),
            "Sustentar ganho pooled simultaneo em AUC-ROC e AUC-PR para fortalecer a narrativa central do paper.",
            critical=True,
        ),
        _criterion_row(
            "prime_signal_support",
            "Prime-signal support rate",
            1.2,
            prime_signal_support_score,
            (
                f"Prime/hibrido teve {prime_supported_gain_rate_percent}% de suporte estrito e "
                f"{prime_positive_gain_rate_percent}% de ganho positivo entre as coortes externas, "
                f"com pooled de {pooled_auc_roc_support_percent}%."
            ),
            "Fortalecer a vantagem do bloco primo/hibrido contra o baseline em multiplas coortes.",
            critical=True,
        ),
        _criterion_row(
            "internal_external_alignment",
            "Internal-external alignment",
            0.95,
            internal_external_alignment_percent,
            (
                f"Melhor experimento interno: {best_internal_experiment or '-'} / "
                f"feature set {best_internal_feature_set or '-'}."
            ),
            "Alinhar o melhor experimento interno com ganhos positivos sustentados na validacao externa.",
        ),
        _criterion_row(
            "cross_cohort_consistency",
            "Cross-cohort consistency",
            0.85,
            winning_consistency_percent,
            f"Feature set dominante entre as coortes externas: {dominant_feature_set or '-'} com consistencia de {winning_consistency_percent}%.",
            "Buscar consistencia do mesmo bloco de sinal entre as coortes externas do estudo.",
        ),
    ]

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / total_weight)) if total_weight else 0

    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]

    markdown_lines = [
        "# Comparative Evidence Package",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Baseline experiment: {baseline_experiment}",
        f"- Overall comparative strength: {overall_percent}%",
        f"- Best supported experiment: {best_supported_experiment or '-'} ({best_supported_feature_set or '-'})",
        f"- Mean supported delta AUC-ROC: {_fmt_metric(best_supported_delta_auc_roc)}",
        (
            f"- Aggregate multicohort effect: {aggregate_supported_experiment or '-'} "
            f"=> delta={_fmt_metric(aggregate_delta_auc_roc)} "
            f"[{_fmt_metric(aggregate_ci_lower_95)}, {_fmt_metric(aggregate_ci_upper_95)}] "
            f"| confidence={aggregate_directional_confidence_percent}%"
        ),
        (
            f"- Pooled multicohort effect: {pooled_supported_experiment or '-'} "
            f"=> delta={_fmt_metric(pooled_delta_auc_roc)} "
            f"[{_fmt_metric(pooled_ci_lower_95)}, {_fmt_metric(pooled_ci_upper_95)}] "
            f"| confidence={pooled_directional_confidence_percent}%"
        ),
        "",
        "## Criteria",
        "",
    ]
    for item in criteria:
        markdown_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Score: {item['score_percent']}%",
                f"- Status: {item['status']}",
                f"- Critical: {'yes' if item['critical'] else 'no'}",
                f"- Evidence: {item['evidence']}",
                f"- Next step: {item['next_step']}",
                "",
            ]
        )

    markdown_lines.extend(["## Cohort Summary", ""])
    if cohort_support_df.empty:
        markdown_lines.append("- Nenhuma coorte externa com comparacao pareada AUC-ROC disponivel.")
    else:
        for _, row in cohort_support_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort']}: supported={row['best_supported_experiment'] or '-'} "
                f"(delta={_fmt_metric(row['best_supported_delta_auc_roc'])}) | "
                f"prime_supported={'yes' if row['prime_supported_gain'] else 'no'} | "
                f"prime_positive={'yes' if row['prime_positive_gain'] else 'no'}"
            )

    markdown_lines.extend(["", "## Experiment Support", ""])
    if experiment_support_df.empty:
        markdown_lines.append("- Sem suporte experimental agregado disponivel.")
    else:
        for _, row in experiment_support_df.head(8).iterrows():
            markdown_lines.append(
                f"- {row['experiment']}: supported={int(row['supported_gain_rate_percent'])}% | "
                f"positive={int(row['positive_gain_rate_percent'])}% | "
                f"mean delta={_fmt_metric(row['mean_delta_auc_roc'])} | "
                f"aggregate={_fmt_metric(row.get('aggregate_delta_auc_roc'))} "
                f"({int(_safe_int(row.get('aggregate_directional_confidence_percent')))}%) | "
                f"pooled={_fmt_metric(row.get('pooled_auc_roc_delta_mean'))} "
                f"({int(_safe_int(row.get('pooled_auc_roc_directional_confidence_percent')))}%) | "
                f"internal rank={_fmt_metric(row.get('internal_rank'))}"
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- A evidencia comparativa esta pronta para consolidacao final do paper.")

    return {
        "summary": {
            "generated_at": _now_utc(),
            "baseline_experiment": baseline_experiment,
            "overall_comparative_strength_percent": overall_percent,
            "overall_status": _status_from_percent(overall_percent),
            "n_external_cohorts": n_external_cohorts,
            "pairwise_coverage_percent": pairwise_coverage_percent,
            "supported_gain_rate_percent": supported_gain_rate_percent,
            "positive_gain_rate_percent": positive_gain_rate_percent,
            "prime_supported_gain_rate_percent": prime_supported_gain_rate_percent,
            "prime_positive_gain_rate_percent": prime_positive_gain_rate_percent,
            "high_confidence_clinical_positive_rate_percent": high_confidence_clinical_positive_rate_percent,
            "high_confidence_clinical_supported_rate_percent": high_confidence_clinical_supported_rate_percent,
            "internal_external_alignment_percent": internal_external_alignment_percent,
            "cross_cohort_consistency_percent": winning_consistency_percent,
            "best_internal_experiment": best_internal_experiment or None,
            "best_internal_feature_set": best_internal_feature_set or None,
            "best_supported_experiment": best_supported_experiment,
            "best_supported_feature_set": best_supported_feature_set,
            "best_supported_delta_auc_roc": best_supported_delta_auc_roc,
            "best_experiment_high_confidence_clinical_positive_rate_percent": high_confidence_clinical_leadership_percent,
            "best_experiment_high_confidence_clinical_supported_rate_percent": high_confidence_clinical_supported_rate_best_percent,
            "aggregate_supported_experiment": aggregate_supported_experiment,
            "aggregate_supported_feature_set": aggregate_supported_feature_set,
            "aggregate_delta_auc_roc": aggregate_delta_auc_roc,
            "aggregate_ci_lower_95": aggregate_ci_lower_95,
            "aggregate_ci_upper_95": aggregate_ci_upper_95,
            "aggregate_directional_confidence_percent": aggregate_directional_confidence_percent,
            "aggregate_supported_gain": aggregate_supported_gain,
            "pooled_supported_experiment": pooled_supported_experiment,
            "pooled_supported_feature_set": pooled_supported_feature_set,
            "pooled_delta_auc_roc": pooled_delta_auc_roc,
            "pooled_ci_lower_95": pooled_ci_lower_95,
            "pooled_ci_upper_95": pooled_ci_upper_95,
            "pooled_directional_confidence_percent": pooled_directional_confidence_percent,
            "pooled_supported_gain": pooled_supported_gain,
            "pooled_cross_metric_supported_gain": pooled_cross_metric_supported_gain,
            "pooled_cross_metric_directional_confidence_percent": pooled_cross_metric_directional_confidence_percent,
            "dominant_feature_set": dominant_feature_set,
            "n_critical_gaps": int(len(critical_gaps)),
        },
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "cohort_support": cohort_support_df.to_dict(orient="records"),
        "experiment_support": experiment_support_df.to_dict(orient="records"),
        "feature_support": feature_support_df.to_dict(orient="records"),
        "experiment_meta_analysis": experiment_meta_df.to_dict(orient="records"),
        "pairwise_auc_roc": pairwise_auc_df.to_dict(orient="records"),
        "pooled_external_support": pooled_support_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_comparative_evidence_html(assessment: dict) -> str:
    markdown = str(assessment.get("markdown_report") or "")
    blocks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            blocks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Comparative Evidence</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f8f1e8;color:#182631;max-width:1020px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}h3{margin-top:1.35rem;color:#245f67;}"
        "ul{background:#fff;border:1px solid #e8dcc8;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_comparative_evidence_package(results: dict, output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    assessment = build_comparative_evidence_assessment(results)
    html_report = build_comparative_evidence_html(assessment)

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    cohort_df = pd.DataFrame(assessment.get("cohort_support") or [])
    experiment_df = pd.DataFrame(assessment.get("experiment_support") or [])
    feature_df = pd.DataFrame(assessment.get("feature_support") or [])
    meta_df = pd.DataFrame(assessment.get("experiment_meta_analysis") or [])
    pairwise_df = pd.DataFrame(assessment.get("pairwise_auc_roc") or [])
    pooled_df = pd.DataFrame(assessment.get("pooled_external_support") or [])

    markdown_path = root / "comparative_evidence_report.md"
    html_path = root / "comparative_evidence_report.html"
    manifest_path = root / "comparative_evidence_manifest.json"
    criteria_path = root / "comparative_evidence_criteria.csv"
    cohort_path = root / "comparative_evidence_cohorts.csv"
    experiment_path = root / "comparative_evidence_experiments.csv"
    feature_path = root / "comparative_evidence_feature_sets.csv"
    meta_path = root / "comparative_evidence_meta_analysis.csv"
    pairwise_path = root / "comparative_evidence_pairwise_auc_roc.csv"
    pooled_path = root / "comparative_evidence_pooled_support.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    cohort_df.to_csv(cohort_path, index=False)
    experiment_df.to_csv(experiment_path, index=False)
    feature_df.to_csv(feature_path, index=False)
    meta_df.to_csv(meta_path, index=False)
    pairwise_df.to_csv(pairwise_path, index=False)
    pooled_df.to_csv(pooled_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "cohorts_path": str(cohort_path),
        "experiments_path": str(experiment_path),
        "feature_sets_path": str(feature_path),
        "meta_analysis_path": str(meta_path),
        "pairwise_auc_roc_path": str(pairwise_path),
        "pooled_support_path": str(pooled_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "comparative_evidence_assessment": assessment,
        "comparative_evidence_report_markdown_path": str(markdown_path),
        "comparative_evidence_report_html_path": str(html_path),
        "comparative_evidence_manifest_path": str(manifest_path),
        "comparative_evidence_criteria_path": str(criteria_path),
        "comparative_evidence_cohorts_path": str(cohort_path),
        "comparative_evidence_experiments_path": str(experiment_path),
        "comparative_evidence_feature_sets_path": str(feature_path),
        "comparative_evidence_meta_analysis_path": str(meta_path),
        "comparative_evidence_pairwise_auc_roc_path": str(pairwise_path),
        "comparative_evidence_pooled_support_path": str(pooled_path),
    }
