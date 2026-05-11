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


PAIRWISE_METRICS = ["auc_roc", "auc_pr"]
HEAD_TO_HEAD_METRICS = ["auc_roc", "auc_pr", "mcc"]
NO_REGRESSION_TOLERANCE = 0.005
SUBSTANTIAL_LOSS_THRESHOLD = -0.02


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


def _safe_percent(series: pd.Series) -> int:
    if series.empty:
        return 0
    return int(round(float(series.fillna(False).astype(bool).mean() * 100)))


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


def _claim_tier(
    score_percent: int,
    auc_roc_supported: int,
    cross_metric_supported: int,
    no_regression: int,
    auc_roc_aggregate_confidence: int,
    head_to_head_leadership: int,
    clinical_credibility: int,
) -> str:
    if (
        score_percent >= 85
        and (auc_roc_supported >= 75 or auc_roc_aggregate_confidence >= 98)
        and cross_metric_supported >= 60
        and no_regression >= 85
        and head_to_head_leadership >= 80
        and clinical_credibility >= 90
    ):
        return "strong"
    if (
        score_percent >= 70
        and (auc_roc_supported >= 50 or auc_roc_aggregate_confidence >= 95)
        and no_regression >= 80
    ):
        return "moderate"
    if score_percent >= 55 and (
        auc_roc_supported >= 25 or cross_metric_supported >= 25 or auc_roc_aggregate_confidence >= 90
    ):
        return "suggestive"
    return "insufficient"


def _claim_statement(tier: str, experiment: str | None, baseline: str | None) -> str:
    if tier == "strong":
        return (
            f"O experimento {experiment or '-'} sustenta uma alegacao forte de superioridade "
            f"contra {baseline or '-'} nas coortes externas auditadas."
        )
    if tier == "moderate":
        return (
            f"O experimento {experiment or '-'} sustenta uma alegacao moderada de ganho "
            f"contra {baseline or '-'}, mas ainda pede consolidacao final em dados reais."
        )
    if tier == "suggestive":
        return (
            f"O experimento {experiment or '-'} mostra sinal sugestivo frente a {baseline or '-'}, "
            "adequado para hipotese, nao para afirmacao forte."
        )
    return (
        f"A evidencia atual ainda nao sustenta uma alegacao robusta de ganho para {experiment or '-'} "
        f"contra {baseline or '-'}."
    )


def _prepare_pairwise_table(results: dict) -> pd.DataFrame:
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
                "positive_gain",
                "supported_gain",
                "no_regression",
                "substantial_loss",
            ]
        )

    if "metric" in pairwise_df.columns:
        pairwise_df = pairwise_df[pairwise_df["metric"].astype(str).isin(PAIRWISE_METRICS)].copy()
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
    pairwise_df["positive_gain"] = pairwise_df["delta_mean"].gt(0)
    pairwise_df["supported_gain"] = pairwise_df["ci_lower_95"].gt(0)
    pairwise_df["no_regression"] = pairwise_df["ci_upper_95"].ge(-NO_REGRESSION_TOLERANCE)
    pairwise_df["substantial_loss"] = pairwise_df["ci_upper_95"].lt(SUBSTANTIAL_LOSS_THRESHOLD)
    return pairwise_df.reset_index(drop=True)


def _build_metric_cohort_table(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    if pairwise_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for keys, subset in pairwise_df.groupby(
        ["experiment", "baseline_experiment", "feature_set", "is_prime_signal", "cohort", "cohort_role"],
        dropna=False,
    ):
        experiment, baseline_experiment, feature_set, is_prime_signal, cohort_name, cohort_role = keys
        row = {
            "experiment": experiment,
            "baseline_experiment": baseline_experiment,
            "feature_set": feature_set,
            "is_prime_signal": bool(is_prime_signal),
            "cohort": cohort_name,
            "cohort_role": cohort_role,
            "is_high_confidence_clinical_cohort": _is_high_confidence_clinical_cohort(cohort_name, cohort_role),
        }
        available_metrics = 0
        supported_all = True
        positive_all = True
        no_regression_all = True
        substantial_loss_any = False
        for metric_name in PAIRWISE_METRICS:
            metric_subset = subset[subset["metric"].astype(str) == metric_name]
            has_metric = not metric_subset.empty
            row[f"has_{metric_name}"] = has_metric
            if has_metric:
                metric_row = metric_subset.iloc[0]
                available_metrics += 1
                row[f"{metric_name}_delta_mean"] = _safe_float(metric_row.get("delta_mean"))
                row[f"{metric_name}_ci_lower_95"] = _safe_float(metric_row.get("ci_lower_95"))
                row[f"{metric_name}_ci_upper_95"] = _safe_float(metric_row.get("ci_upper_95"))
                row[f"{metric_name}_supported"] = bool(metric_row.get("supported_gain"))
                row[f"{metric_name}_positive"] = bool(metric_row.get("positive_gain"))
                row[f"{metric_name}_no_regression"] = bool(metric_row.get("no_regression"))
                row[f"{metric_name}_substantial_loss"] = bool(metric_row.get("substantial_loss"))
                supported_all = supported_all and bool(metric_row.get("supported_gain"))
                positive_all = positive_all and bool(metric_row.get("positive_gain"))
                no_regression_all = no_regression_all and bool(metric_row.get("no_regression"))
                substantial_loss_any = substantial_loss_any or bool(metric_row.get("substantial_loss"))
            else:
                row[f"{metric_name}_delta_mean"] = float("nan")
                row[f"{metric_name}_ci_lower_95"] = float("nan")
                row[f"{metric_name}_ci_upper_95"] = float("nan")
                row[f"{metric_name}_supported"] = False
                row[f"{metric_name}_positive"] = False
                row[f"{metric_name}_no_regression"] = False
                row[f"{metric_name}_substantial_loss"] = False
                supported_all = False
                positive_all = False
                no_regression_all = False
        row["available_pairwise_metrics"] = available_metrics
        row["cross_metric_supported"] = bool(available_metrics == len(PAIRWISE_METRICS) and supported_all)
        row["cross_metric_positive"] = bool(available_metrics == len(PAIRWISE_METRICS) and positive_all)
        row["cross_metric_no_regression"] = bool(available_metrics > 0 and no_regression_all)
        row["cross_metric_substantial_loss"] = bool(substantial_loss_any)
        rows.append(row)
    return pd.DataFrame(rows)


def _build_metric_aggregate_table(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    if pairwise_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for keys, subset in pairwise_df.groupby(
        ["experiment", "baseline_experiment", "feature_set", "is_prime_signal", "metric"],
        dropna=False,
    ):
        experiment, baseline_experiment, feature_set, is_prime_signal, metric_name = keys
        valid = subset.copy()
        valid["delta_se"] = valid.apply(
            lambda row: _estimate_standard_error(row.get("ci_lower_95"), row.get("ci_upper_95")),
            axis=1,
        )
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
            deltas = valid["delta_mean"].map(_safe_float).to_numpy(dtype=float)
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
                "baseline_experiment": baseline_experiment,
                "feature_set": feature_set,
                "is_prime_signal": bool(is_prime_signal),
                "metric": metric_name,
                "n_external_cohorts": int(subset["cohort"].astype(str).nunique()),
                "aggregate_delta_mean": aggregate_delta,
                "aggregate_ci_lower_95": aggregate_ci_lower,
                "aggregate_ci_upper_95": aggregate_ci_upper,
                "aggregate_supported": aggregate_supported,
                "aggregate_positive": aggregate_positive,
                "aggregate_directional_confidence_percent": aggregate_confidence,
            }
        )

    return pd.DataFrame(rows)


def _build_pooled_metric_table(pooled_support_df: pd.DataFrame) -> pd.DataFrame:
    if pooled_support_df.empty:
        return pd.DataFrame()
    subset = pooled_support_df.copy()
    subset["metric"] = subset["metric"].astype(str)
    subset["pooled_cross_metric_supported"] = False
    subset["pooled_cross_metric_directional_confidence_percent"] = 0
    subset["pooled_cross_metric_delta_mean"] = float("nan")

    rows: List[dict] = []
    for keys, group in subset.groupby(["experiment", "baseline_experiment", "feature_set", "is_prime_signal"], dropna=False):
        experiment, baseline_experiment, feature_set, is_prime_signal = keys
        base_row = {
            "experiment": experiment,
            "baseline_experiment": baseline_experiment,
            "feature_set": feature_set,
            "is_prime_signal": bool(is_prime_signal),
            "n_external_cohorts": int(group["n_external_cohorts"].max()) if "n_external_cohorts" in group.columns else 0,
            "n_variants": int(group["n_variants"].max()) if "n_variants" in group.columns else 0,
        }
        metric_rows = {str(row["metric"]): row for _, row in group.iterrows()}
        roc_row = metric_rows.get("auc_roc", {})
        pr_row = metric_rows.get("auc_pr", {})
        roc_supported = bool(roc_row.get("pooled_supported_gain"))
        pr_supported = bool(pr_row.get("pooled_supported_gain"))
        roc_conf = _safe_int(roc_row.get("pooled_directional_confidence_percent"))
        pr_conf = _safe_int(pr_row.get("pooled_directional_confidence_percent"))
        roc_positive = bool(roc_row.get("pooled_positive_gain"))
        pr_positive = bool(pr_row.get("pooled_positive_gain"))
        rows.append(
            {
                **base_row,
                "pooled_auc_roc_supported": roc_supported,
                "pooled_auc_roc_positive": roc_positive,
                "pooled_auc_roc_confidence_percent": roc_conf,
                "pooled_auc_roc_delta_mean": _safe_float(roc_row.get("pooled_delta_mean")),
                "pooled_auc_roc_ci_lower_95": _safe_float(roc_row.get("pooled_ci_lower_95")),
                "pooled_auc_roc_ci_upper_95": _safe_float(roc_row.get("pooled_ci_upper_95")),
                "pooled_auc_pr_supported": pr_supported,
                "pooled_auc_pr_positive": pr_positive,
                "pooled_auc_pr_confidence_percent": pr_conf,
                "pooled_auc_pr_delta_mean": _safe_float(pr_row.get("pooled_delta_mean")),
                "pooled_auc_pr_ci_lower_95": _safe_float(pr_row.get("pooled_ci_lower_95")),
                "pooled_auc_pr_ci_upper_95": _safe_float(pr_row.get("pooled_ci_upper_95")),
                "pooled_cross_metric_supported": roc_supported and pr_supported,
                "pooled_cross_metric_positive": roc_positive and pr_positive,
                "pooled_cross_metric_confidence_percent": int(round((roc_conf + pr_conf) / 2)) if (roc_conf or pr_conf) else 0,
            }
        )
    return pd.DataFrame(rows)


def _build_head_to_head_table(results: dict, candidate_table: pd.DataFrame) -> pd.DataFrame:
    if candidate_table.empty:
        return pd.DataFrame()

    external_metrics = results.get("external_evaluation_metrics")
    external_df = external_metrics.copy() if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()
    if external_df.empty:
        return pd.DataFrame()

    combined_df = external_df[external_df["evaluation_group"].astype(str) == "combined"].copy() if "evaluation_group" in external_df.columns else external_df.copy()
    if combined_df.empty or "cohort" not in combined_df.columns or "experiment" not in combined_df.columns:
        return pd.DataFrame()

    rows: List[dict] = []
    for candidate in candidate_table.to_dict(orient="records"):
        candidate_experiment = str(candidate.get("experiment") or "")
        baseline_experiment = str(candidate.get("baseline_experiment") or "")
        if not candidate_experiment or not baseline_experiment:
            continue

        candidate_rows = combined_df[combined_df["experiment"].astype(str) == candidate_experiment].copy()
        baseline_rows = combined_df[combined_df["experiment"].astype(str) == baseline_experiment].copy()
        if candidate_rows.empty or baseline_rows.empty:
            continue

        shared_cohorts = sorted(set(candidate_rows["cohort"].astype(str)).intersection(set(baseline_rows["cohort"].astype(str))))
        for cohort_name in shared_cohorts:
            candidate_row = candidate_rows[candidate_rows["cohort"].astype(str) == cohort_name].head(1)
            baseline_row = baseline_rows[baseline_rows["cohort"].astype(str) == cohort_name].head(1)
            if candidate_row.empty or baseline_row.empty:
                continue
            candidate_item = candidate_row.iloc[0]
            baseline_item = baseline_row.iloc[0]
            for metric_name in HEAD_TO_HEAD_METRICS:
                if metric_name not in candidate_item.index or metric_name not in baseline_item.index:
                    continue
                candidate_value = _safe_float(candidate_item.get(metric_name))
                baseline_value = _safe_float(baseline_item.get(metric_name))
                if np.isnan(candidate_value) or np.isnan(baseline_value):
                    continue
                delta_value = candidate_value - baseline_value
                rows.append(
                    {
                        "experiment": candidate_experiment,
                        "baseline_experiment": baseline_experiment,
                        "feature_set": candidate.get("feature_set"),
                        "is_prime_signal": bool(candidate.get("is_prime_signal")),
                        "cohort": cohort_name,
                        "is_high_confidence_clinical_cohort": _is_high_confidence_clinical_cohort(cohort_name),
                        "metric": metric_name,
                        "candidate_value": candidate_value,
                        "baseline_value": baseline_value,
                        "delta_value": delta_value,
                        "win": bool(delta_value > 0),
                        "no_regression": bool(delta_value >= -NO_REGRESSION_TOLERANCE),
                        "substantial_loss": bool(delta_value < SUBSTANTIAL_LOSS_THRESHOLD),
                    }
                )
    return pd.DataFrame(rows)


def _build_candidate_table(
    metric_cohort_df: pd.DataFrame,
    head_to_head_df: pd.DataFrame,
    metric_aggregate_df: pd.DataFrame,
    pooled_metric_df: pd.DataFrame,
) -> pd.DataFrame:
    if metric_cohort_df.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for keys, subset in metric_cohort_df.groupby(["experiment", "baseline_experiment", "feature_set", "is_prime_signal"], dropna=False):
        experiment, baseline_experiment, feature_set, is_prime_signal = keys
        n_external_cohorts = int(subset["cohort"].astype(str).nunique())
        expected_pairwise_points = n_external_cohorts * len(PAIRWISE_METRICS)
        available_pairwise_points = int(subset["available_pairwise_metrics"].sum())
        pairwise_metric_coverage_percent = int(round((available_pairwise_points / expected_pairwise_points) * 100)) if expected_pairwise_points else 0
        auc_roc_supported_rate_percent = _safe_percent(subset["auc_roc_supported"])
        auc_pr_supported_rate_percent = _safe_percent(subset["auc_pr_supported"])
        auc_roc_positive_rate_percent = _safe_percent(subset["auc_roc_positive"])
        auc_pr_positive_rate_percent = _safe_percent(subset["auc_pr_positive"])
        cross_metric_supported_rate_percent = _safe_percent(subset["cross_metric_supported"])
        cross_metric_positive_rate_percent = _safe_percent(subset["cross_metric_positive"])
        cross_metric_no_regression_rate_percent = _safe_percent(subset["cross_metric_no_regression"])
        cross_metric_loss_rate_percent = _safe_percent(subset["cross_metric_substantial_loss"])
        high_conf_subset = subset[subset["is_high_confidence_clinical_cohort"]].copy()
        high_confidence_clinical_auc_roc_positive_rate_percent = (
            _safe_percent(high_conf_subset["auc_roc_positive"]) if not high_conf_subset.empty else 0
        )
        high_confidence_clinical_auc_roc_supported_rate_percent = (
            _safe_percent(high_conf_subset["auc_roc_supported"]) if not high_conf_subset.empty else 0
        )
        high_confidence_clinical_cross_metric_positive_rate_percent = (
            _safe_percent(high_conf_subset["cross_metric_positive"]) if not high_conf_subset.empty else 0
        )
        external_depth_percent = int(min(100, round((n_external_cohorts / 4) * 100))) if n_external_cohorts else 0

        aggregate_subset = metric_aggregate_df[
            (metric_aggregate_df["experiment"].astype(str) == str(experiment))
            & (metric_aggregate_df["baseline_experiment"].astype(str) == str(baseline_experiment))
        ].copy() if not metric_aggregate_df.empty else pd.DataFrame()
        aggregate_auc_roc_supported = False
        aggregate_auc_pr_supported = False
        aggregate_cross_metric_supported = False
        aggregate_auc_roc_confidence_percent = 0
        aggregate_auc_pr_confidence_percent = 0
        aggregate_cross_metric_confidence_percent = 0
        aggregate_mean_delta_auc_roc = float("nan")
        if not aggregate_subset.empty:
            roc_row = aggregate_subset[aggregate_subset["metric"].astype(str) == "auc_roc"].head(1)
            pr_row = aggregate_subset[aggregate_subset["metric"].astype(str) == "auc_pr"].head(1)
            if not roc_row.empty:
                aggregate_auc_roc_supported = bool(roc_row.iloc[0].get("aggregate_supported"))
                aggregate_auc_roc_confidence_percent = _safe_int(roc_row.iloc[0].get("aggregate_directional_confidence_percent"))
                aggregate_mean_delta_auc_roc = _safe_float(roc_row.iloc[0].get("aggregate_delta_mean"))
            if not pr_row.empty:
                aggregate_auc_pr_supported = bool(pr_row.iloc[0].get("aggregate_supported"))
                aggregate_auc_pr_confidence_percent = _safe_int(pr_row.iloc[0].get("aggregate_directional_confidence_percent"))
            if not roc_row.empty and not pr_row.empty:
                aggregate_cross_metric_supported = aggregate_auc_roc_supported and aggregate_auc_pr_supported
                aggregate_cross_metric_confidence_percent = int(
                    round((aggregate_auc_roc_confidence_percent + aggregate_auc_pr_confidence_percent) / 2)
                )

        pooled_subset = pooled_metric_df[
            (pooled_metric_df["experiment"].astype(str) == str(experiment))
            & (pooled_metric_df["baseline_experiment"].astype(str) == str(baseline_experiment))
        ].head(1).copy() if not pooled_metric_df.empty else pd.DataFrame()
        pooled_auc_roc_supported = False
        pooled_auc_pr_supported = False
        pooled_cross_metric_supported = False
        pooled_auc_roc_confidence_percent = 0
        pooled_auc_pr_confidence_percent = 0
        pooled_cross_metric_confidence_percent = 0
        pooled_mean_delta_auc_roc = float("nan")
        if not pooled_subset.empty:
            pooled_row = pooled_subset.iloc[0]
            pooled_auc_roc_supported = bool(pooled_row.get("pooled_auc_roc_supported"))
            pooled_auc_pr_supported = bool(pooled_row.get("pooled_auc_pr_supported"))
            pooled_cross_metric_supported = bool(pooled_row.get("pooled_cross_metric_supported"))
            pooled_auc_roc_confidence_percent = _safe_int(pooled_row.get("pooled_auc_roc_confidence_percent"))
            pooled_auc_pr_confidence_percent = _safe_int(pooled_row.get("pooled_auc_pr_confidence_percent"))
            pooled_cross_metric_confidence_percent = _safe_int(
                pooled_row.get("pooled_cross_metric_confidence_percent")
            )
            pooled_mean_delta_auc_roc = _safe_float(pooled_row.get("pooled_auc_roc_delta_mean"))

        head_subset = head_to_head_df[head_to_head_df["experiment"].astype(str) == str(experiment)].copy() if not head_to_head_df.empty else pd.DataFrame()
        head_to_head_coverage_percent = 0
        head_to_head_win_rate_percent = 0
        head_to_head_no_regression_rate_percent = 0
        head_to_head_substantial_loss_rate_percent = 0
        mean_head_to_head_delta = float("nan")
        if not head_subset.empty:
            expected_head_points = n_external_cohorts * len(HEAD_TO_HEAD_METRICS)
            head_to_head_coverage_percent = int(round((len(head_subset) / expected_head_points) * 100)) if expected_head_points else 0
            head_to_head_win_rate_percent = _safe_percent(head_subset["win"])
            head_to_head_no_regression_rate_percent = _safe_percent(head_subset["no_regression"])
            head_to_head_substantial_loss_rate_percent = _safe_percent(head_subset["substantial_loss"])
            mean_head_to_head_delta = _safe_float(head_subset["delta_value"].mean())
        high_conf_head_subset = (
            head_subset[head_subset["is_high_confidence_clinical_cohort"]].copy() if not head_subset.empty else pd.DataFrame()
        )
        high_confidence_clinical_head_to_head_win_rate_percent = (
            _safe_percent(high_conf_head_subset["win"]) if not high_conf_head_subset.empty else 0
        )
        high_confidence_clinical_head_to_head_no_regression_rate_percent = (
            _safe_percent(high_conf_head_subset["no_regression"]) if not high_conf_head_subset.empty else 0
        )

        prime_alignment_percent = 100 if bool(is_prime_signal) else 55
        high_confidence_clinical_score_percent = _safe_percent(
            pd.Series(
                [
                    high_confidence_clinical_auc_roc_positive_rate_percent >= 50,
                    high_confidence_clinical_head_to_head_win_rate_percent >= 50,
                    high_confidence_clinical_head_to_head_no_regression_rate_percent >= 80,
                ]
            )
        )
        pooled_auc_roc_support_percent = (
            100
            if pooled_auc_roc_supported
            else pooled_auc_roc_confidence_percent if pooled_mean_delta_auc_roc > 0 else 0
        )
        pooled_cross_metric_support_percent = (
            100
            if pooled_cross_metric_supported
            else pooled_cross_metric_confidence_percent if pooled_auc_roc_confidence_percent > 0 else 0
        )
        effective_auc_roc_support_percent = max(auc_roc_supported_rate_percent, pooled_auc_roc_support_percent)
        effective_auc_roc_confidence_percent = max(aggregate_auc_roc_confidence_percent, pooled_auc_roc_confidence_percent)
        effective_cross_metric_support_percent = max(cross_metric_supported_rate_percent, pooled_cross_metric_support_percent)
        effective_cross_metric_confidence_percent = max(
            aggregate_cross_metric_confidence_percent,
            pooled_cross_metric_confidence_percent,
        )
        effective_head_to_head_leadership_percent = int(
            round(
                np.mean(
                    [
                        float(head_to_head_win_rate_percent),
                        float(high_confidence_clinical_head_to_head_win_rate_percent),
                        float(pooled_cross_metric_support_percent),
                    ]
                )
            )
        )
        effective_no_regression_percent = int(
            round(
                np.mean(
                    [
                        float(head_to_head_no_regression_rate_percent),
                        float(cross_metric_no_regression_rate_percent),
                        float(high_confidence_clinical_head_to_head_no_regression_rate_percent),
                    ]
                )
            )
        )
        clinical_credibility_percent = int(
            round(
                np.mean(
                    [
                        float(high_confidence_clinical_score_percent),
                        float(high_confidence_clinical_auc_roc_positive_rate_percent),
                        float(high_confidence_clinical_head_to_head_win_rate_percent),
                        float(high_confidence_clinical_head_to_head_no_regression_rate_percent),
                    ]
                )
            )
        )
        claim_score_inputs = [
            (external_depth_percent, 0.85),
            (pairwise_metric_coverage_percent, 1.0),
            (effective_auc_roc_support_percent, 1.35),
            (effective_auc_roc_confidence_percent, 0.95),
            (effective_cross_metric_support_percent, 1.2),
            (effective_cross_metric_confidence_percent, 0.8),
            (clinical_credibility_percent, 0.9),
            (effective_head_to_head_leadership_percent, 1.0),
            (effective_no_regression_percent, 1.15),
            (prime_alignment_percent, 0.65),
        ]
        weighted_total = sum(weight for _, weight in claim_score_inputs)
        claim_strength_percent = int(round(sum(score * weight for score, weight in claim_score_inputs) / weighted_total)) if weighted_total else 0
        claim_tier = _claim_tier(
            score_percent=claim_strength_percent,
            auc_roc_supported=effective_auc_roc_support_percent,
            cross_metric_supported=effective_cross_metric_support_percent,
            no_regression=effective_no_regression_percent,
            auc_roc_aggregate_confidence=effective_auc_roc_confidence_percent,
            head_to_head_leadership=effective_head_to_head_leadership_percent,
            clinical_credibility=clinical_credibility_percent,
        )

        rows.append(
            {
                "experiment": experiment,
                "baseline_experiment": baseline_experiment,
                "feature_set": feature_set,
                "is_prime_signal": bool(is_prime_signal),
                "n_external_cohorts": n_external_cohorts,
                "external_depth_percent": external_depth_percent,
                "pairwise_metric_coverage_percent": pairwise_metric_coverage_percent,
                "auc_roc_supported_rate_percent": auc_roc_supported_rate_percent,
                "auc_pr_supported_rate_percent": auc_pr_supported_rate_percent,
                "auc_roc_positive_rate_percent": auc_roc_positive_rate_percent,
                "auc_pr_positive_rate_percent": auc_pr_positive_rate_percent,
                "cross_metric_supported_rate_percent": cross_metric_supported_rate_percent,
                "cross_metric_positive_rate_percent": cross_metric_positive_rate_percent,
                "cross_metric_no_regression_rate_percent": cross_metric_no_regression_rate_percent,
                "cross_metric_loss_rate_percent": cross_metric_loss_rate_percent,
                "high_confidence_clinical_auc_roc_positive_rate_percent": high_confidence_clinical_auc_roc_positive_rate_percent,
                "high_confidence_clinical_auc_roc_supported_rate_percent": high_confidence_clinical_auc_roc_supported_rate_percent,
                "high_confidence_clinical_cross_metric_positive_rate_percent": high_confidence_clinical_cross_metric_positive_rate_percent,
                "aggregate_auc_roc_supported": aggregate_auc_roc_supported,
                "aggregate_auc_pr_supported": aggregate_auc_pr_supported,
                "aggregate_cross_metric_supported": aggregate_cross_metric_supported,
                "aggregate_auc_roc_confidence_percent": aggregate_auc_roc_confidence_percent,
                "aggregate_auc_pr_confidence_percent": aggregate_auc_pr_confidence_percent,
                "aggregate_cross_metric_confidence_percent": aggregate_cross_metric_confidence_percent,
                "pooled_auc_roc_supported": pooled_auc_roc_supported,
                "pooled_auc_pr_supported": pooled_auc_pr_supported,
                "pooled_cross_metric_supported": pooled_cross_metric_supported,
                "pooled_auc_roc_confidence_percent": pooled_auc_roc_confidence_percent,
                "pooled_auc_pr_confidence_percent": pooled_auc_pr_confidence_percent,
                "pooled_cross_metric_confidence_percent": pooled_cross_metric_confidence_percent,
                "pooled_auc_roc_support_percent": pooled_auc_roc_support_percent,
                "pooled_cross_metric_support_percent": pooled_cross_metric_support_percent,
                "effective_auc_roc_support_percent": effective_auc_roc_support_percent,
                "effective_auc_roc_confidence_percent": effective_auc_roc_confidence_percent,
                "effective_cross_metric_support_percent": effective_cross_metric_support_percent,
                "effective_cross_metric_confidence_percent": effective_cross_metric_confidence_percent,
                "effective_head_to_head_leadership_percent": effective_head_to_head_leadership_percent,
                "effective_no_regression_percent": effective_no_regression_percent,
                "clinical_credibility_percent": clinical_credibility_percent,
                "head_to_head_coverage_percent": head_to_head_coverage_percent,
                "head_to_head_win_rate_percent": head_to_head_win_rate_percent,
                "head_to_head_no_regression_rate_percent": head_to_head_no_regression_rate_percent,
                "head_to_head_substantial_loss_rate_percent": head_to_head_substantial_loss_rate_percent,
                "high_confidence_clinical_head_to_head_win_rate_percent": high_confidence_clinical_head_to_head_win_rate_percent,
                "high_confidence_clinical_head_to_head_no_regression_rate_percent": high_confidence_clinical_head_to_head_no_regression_rate_percent,
                "high_confidence_clinical_score_percent": high_confidence_clinical_score_percent,
                "mean_delta_auc_roc": _safe_float(subset["auc_roc_delta_mean"].mean()),
                "aggregate_mean_delta_auc_roc": aggregate_mean_delta_auc_roc,
                "pooled_mean_delta_auc_roc": pooled_mean_delta_auc_roc,
                "mean_delta_auc_pr": _safe_float(subset["auc_pr_delta_mean"].mean()),
                "mean_head_to_head_delta": mean_head_to_head_delta,
                "claim_strength_percent": claim_strength_percent,
                "claim_tier": claim_tier,
            }
        )

    candidate_df = pd.DataFrame(rows)
    if candidate_df.empty:
        return candidate_df

    return candidate_df.sort_values(
        [
            "claim_strength_percent",
            "is_prime_signal",
            "effective_auc_roc_support_percent",
            "effective_auc_roc_confidence_percent",
            "effective_cross_metric_support_percent",
            "effective_head_to_head_leadership_percent",
            "mean_delta_auc_roc",
            "experiment",
        ],
        ascending=[False, False, False, False, False, False, False, True],
    ).reset_index(drop=True)


def build_claim_strength_assessment(results: dict) -> dict:
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Claim Strength")
    pairwise_df = _prepare_pairwise_table(results)
    metric_cohort_df = _build_metric_cohort_table(pairwise_df)
    metric_aggregate_df = _build_metric_aggregate_table(pairwise_df)
    pooled_metric_df = _build_pooled_metric_table(get_or_build_pooled_external_support(results))
    candidate_seed_df = _build_candidate_table(metric_cohort_df, pd.DataFrame(), metric_aggregate_df, pooled_metric_df)
    head_to_head_df = _build_head_to_head_table(results, candidate_seed_df)
    candidate_df = _build_candidate_table(metric_cohort_df, head_to_head_df, metric_aggregate_df, pooled_metric_df)

    top_candidate = candidate_df.iloc[0].to_dict() if not candidate_df.empty else {}
    overall_percent = _safe_int(top_candidate.get("claim_strength_percent"))
    claim_tier = str(top_candidate.get("claim_tier") or "insufficient")
    selected_experiment = top_candidate.get("experiment")
    selected_baseline = top_candidate.get("baseline_experiment")
    selected_feature_set = top_candidate.get("feature_set")
    critical_gaps: List[str] = []

    criteria = [
        _criterion_row(
            "external_depth",
            "External cohort depth",
            0.85,
            _safe_int(top_candidate.get("external_depth_percent")),
            f"{_safe_int(top_candidate.get('n_external_cohorts'))} coorte(s) externas sustentam o experimento candidato.",
            "Aumentar o numero de coortes externas independentes para sustentar uma alegacao mais forte.",
        ),
        _criterion_row(
            "pairwise_metric_coverage",
            "Pairwise multi-metric coverage",
            1.0,
            _safe_int(top_candidate.get("pairwise_metric_coverage_percent")),
            f"{_safe_int(top_candidate.get('pairwise_metric_coverage_percent'))}% das combinacoes coorte-metrica foram materializadas para o candidato.",
            "Garantir AUC-ROC e AUC-PR pareados contra baseline em todas as coortes externas.",
            critical=True,
        ),
        _criterion_row(
            "supported_auc_roc",
            "Supported AUC-ROC gain",
            1.35,
            _safe_int(top_candidate.get("effective_auc_roc_support_percent")),
            (
                f"{_safe_int(top_candidate.get('auc_roc_supported_rate_percent'))}% das coortes externas mostram ganho AUC-ROC com IC inferior > 0, "
                f"enquanto o pooled multicohorte ficou em {_safe_int(top_candidate.get('pooled_auc_roc_support_percent'))}% "
                f"com delta {_fmt_metric(top_candidate.get('pooled_mean_delta_auc_roc'))}."
            ),
            "Buscar suporte estatistico do ganho AUC-ROC em mais coortes externas reais e preservar o suporte pooled multicohorte.",
            critical=True,
        ),
        _criterion_row(
            "high_confidence_clinical_holdout",
            "High-confidence clinical holdout",
            0.9,
            _safe_int(top_candidate.get("clinical_credibility_percent") or top_candidate.get("high_confidence_clinical_score_percent")),
            (
                f"Nas coortes clinicas de alta confianca, o candidato teve "
                f"{_safe_int(top_candidate.get('high_confidence_clinical_auc_roc_positive_rate_percent'))}% de ganho positivo em AUC-ROC, "
                f"{_safe_int(top_candidate.get('high_confidence_clinical_head_to_head_win_rate_percent'))}% de vitorias diretas "
                f"e {_safe_int(top_candidate.get('high_confidence_clinical_head_to_head_no_regression_rate_percent'))}% sem regressao relevante, "
                f"com credibilidade clinica agregada em {_safe_int(top_candidate.get('clinical_credibility_percent'))}%."
            ),
            "Transformar a lideranca nas coortes clinicas de alta confianca em suporte estatistico mais estrito.",
        ),
        _criterion_row(
            "aggregate_auc_roc_direction",
            "Aggregate AUC-ROC direction",
            0.95,
            _safe_int(top_candidate.get("effective_auc_roc_confidence_percent")),
            (
                f"{_safe_int(top_candidate.get('aggregate_auc_roc_confidence_percent'))}% de confianca direcional "
                f"no meta-agregado em AUC-ROC e {_safe_int(top_candidate.get('pooled_auc_roc_confidence_percent'))}% "
                f"no pooled multicohorte, com delta pooled {_fmt_metric(top_candidate.get('pooled_mean_delta_auc_roc'))}."
            ),
            "Fortalecer o efeito agregado ate convergir para suporte estrito e nao apenas direcional.",
        ),
        _criterion_row(
            "cross_metric_support",
            "Cross-metric support",
            1.2,
            _safe_int(top_candidate.get("effective_cross_metric_support_percent")),
            (
                f"{_safe_int(top_candidate.get('cross_metric_supported_rate_percent'))}% das coortes externas "
                f"sustentam ganho simultaneo em AUC-ROC e AUC-PR, com pooled em "
                f"{_safe_int(top_candidate.get('pooled_cross_metric_support_percent'))}%."
            ),
            "Fortalecer o sinal em mais de uma metrica para sustentar a alegacao central do paper.",
            critical=True,
        ),
        _criterion_row(
            "head_to_head_win_rate",
            "Head-to-head external win rate",
            1.0,
            _safe_int(top_candidate.get("effective_head_to_head_leadership_percent") or top_candidate.get("head_to_head_win_rate_percent")),
            (
                f"{_safe_int(top_candidate.get('head_to_head_win_rate_percent'))}% das comparacoes externas "
                f"diretas superam o baseline em AUC-ROC, AUC-PR ou MCC, com lideranca efetiva em "
                f"{_safe_int(top_candidate.get('effective_head_to_head_leadership_percent'))}%."
            ),
            "Aumentar a taxa de vitoria direta do candidato nas metricas externas centrais.",
            critical=True,
        ),
        _criterion_row(
            "no_regression_safety",
            "No-regression safety",
            1.15,
            _safe_int(
                top_candidate.get("effective_no_regression_percent")
                or top_candidate.get("head_to_head_no_regression_rate_percent")
                or top_candidate.get("cross_metric_no_regression_rate_percent")
            ),
            (
                f"{_safe_int(top_candidate.get('head_to_head_no_regression_rate_percent'))}% das comparacoes externas "
                f"nao mostram regressao relevante frente ao baseline, com seguranca efetiva em "
                f"{_safe_int(top_candidate.get('effective_no_regression_percent'))}%."
            ),
            "Reduzir sinais de regressao antes de sustentar uma alegacao forte de superioridade.",
            critical=True,
        ),
    ]

    for item in criteria:
        if item["critical"] and item["score_percent"] < 70:
            critical_gaps.append(item["title"])
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    claim_statement = _claim_statement(claim_tier, selected_experiment, selected_baseline)

    markdown_lines = [
        "# Claim Strength Package",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Study: {study_name}",
        f"- Selected candidate: {selected_experiment or '-'}",
        f"- Baseline comparator: {selected_baseline or '-'}",
        f"- Claim strength: {overall_percent}%",
        f"- Claim tier: {claim_tier}",
        f"- Statement: {claim_statement}",
        (
            f"- Pooled support: AUC-ROC={_safe_int(top_candidate.get('pooled_auc_roc_support_percent'))}% | "
            f"cross-metric={_safe_int(top_candidate.get('pooled_cross_metric_support_percent'))}%"
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

    markdown_lines.extend(["## Candidate Ranking", ""])
    if candidate_df.empty:
        markdown_lines.append("- Nenhum candidato comparativo foi identificado.")
    else:
        for _, row in candidate_df.head(8).iterrows():
            markdown_lines.append(
                f"- {row['experiment']}: claim={int(row['claim_strength_percent'])}% ({row['claim_tier']}), "
                f"AUC-ROC support={int(row['effective_auc_roc_support_percent'])}%, "
                f"aggregate AUC-ROC={int(row['effective_auc_roc_confidence_percent'])}%, "
                f"cross-metric={int(row['effective_cross_metric_support_percent'])}%, "
                f"leadership={int(row['effective_head_to_head_leadership_percent'])}%."
            )

    markdown_lines.extend(["", "## Head-to-Head Evidence", ""])
    if head_to_head_df.empty:
        markdown_lines.append("- Nenhuma comparacao head-to-head externa disponivel.")
    else:
        for _, row in head_to_head_df.head(18).iterrows():
            markdown_lines.append(
                f"- {row['cohort']} | {row['metric']}: {row['experiment']} vs {row['baseline_experiment']} "
                f"=> delta={_fmt_metric(row['delta_value'])} "
                f"({'win' if row['win'] else 'no win'}, {'safe' if row['no_regression'] else 'regression risk'})."
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- A alegacao comparativa parece pronta para consolidacao final.")

    return {
        "summary": {
            "generated_at": _now_utc(),
            "study_name": study_name,
            "overall_claim_strength_percent": overall_percent,
            "overall_status": _status_from_percent(overall_percent),
            "claim_tier": claim_tier,
            "claim_statement": claim_statement,
            "selected_experiment": selected_experiment,
            "selected_feature_set": selected_feature_set,
            "selected_baseline_experiment": selected_baseline,
            "selected_is_prime_signal": bool(top_candidate.get("is_prime_signal")),
            "selected_external_depth_percent": _safe_int(top_candidate.get("external_depth_percent")),
            "selected_pairwise_metric_coverage_percent": _safe_int(top_candidate.get("pairwise_metric_coverage_percent")),
            "selected_auc_roc_supported_rate_percent": _safe_int(top_candidate.get("auc_roc_supported_rate_percent")),
            "selected_effective_auc_roc_support_percent": _safe_int(top_candidate.get("effective_auc_roc_support_percent")),
            "selected_aggregate_auc_roc_confidence_percent": _safe_int(top_candidate.get("aggregate_auc_roc_confidence_percent")),
            "selected_effective_auc_roc_confidence_percent": _safe_int(top_candidate.get("effective_auc_roc_confidence_percent")),
            "selected_pooled_auc_roc_support_percent": _safe_int(top_candidate.get("pooled_auc_roc_support_percent")),
            "selected_pooled_auc_roc_confidence_percent": _safe_int(top_candidate.get("pooled_auc_roc_confidence_percent")),
            "selected_cross_metric_supported_rate_percent": _safe_int(top_candidate.get("cross_metric_supported_rate_percent")),
            "selected_effective_cross_metric_support_percent": _safe_int(top_candidate.get("effective_cross_metric_support_percent")),
            "selected_pooled_cross_metric_support_percent": _safe_int(top_candidate.get("pooled_cross_metric_support_percent")),
            "selected_effective_head_to_head_leadership_percent": _safe_int(top_candidate.get("effective_head_to_head_leadership_percent")),
            "selected_effective_no_regression_percent": _safe_int(top_candidate.get("effective_no_regression_percent")),
            "selected_clinical_credibility_percent": _safe_int(top_candidate.get("clinical_credibility_percent")),
            "selected_high_confidence_clinical_score_percent": _safe_int(top_candidate.get("high_confidence_clinical_score_percent")),
            "selected_high_confidence_clinical_auc_roc_positive_rate_percent": _safe_int(
                top_candidate.get("high_confidence_clinical_auc_roc_positive_rate_percent")
            ),
            "selected_high_confidence_clinical_head_to_head_win_rate_percent": _safe_int(
                top_candidate.get("high_confidence_clinical_head_to_head_win_rate_percent")
            ),
            "selected_head_to_head_win_rate_percent": _safe_int(top_candidate.get("head_to_head_win_rate_percent")),
            "selected_head_to_head_no_regression_rate_percent": _safe_int(top_candidate.get("head_to_head_no_regression_rate_percent")),
            "selected_head_to_head_substantial_loss_rate_percent": _safe_int(top_candidate.get("head_to_head_substantial_loss_rate_percent")),
            "selected_mean_delta_auc_roc": _safe_float(top_candidate.get("mean_delta_auc_roc")),
            "selected_aggregate_mean_delta_auc_roc": _safe_float(top_candidate.get("aggregate_mean_delta_auc_roc")),
            "selected_pooled_mean_delta_auc_roc": _safe_float(top_candidate.get("pooled_mean_delta_auc_roc")),
            "selected_mean_delta_auc_pr": _safe_float(top_candidate.get("mean_delta_auc_pr")),
            "n_candidate_experiments": int(len(candidate_df)),
            "n_critical_gaps": int(len(critical_gaps)),
        },
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "candidates": candidate_df.to_dict(orient="records"),
        "metric_cohort": metric_cohort_df.to_dict(orient="records"),
        "metric_aggregate": metric_aggregate_df.to_dict(orient="records"),
        "pooled_metric": pooled_metric_df.to_dict(orient="records"),
        "head_to_head": head_to_head_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_claim_strength_html(assessment: dict) -> str:
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
        "<title>PrimeVarClass Claim Strength</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f8f4ec;color:#16252f;max-width:1020px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8a4f2d;}h3{margin-top:1.35rem;color:#245f67;}"
        "ul{background:#fff;border:1px solid #e8dcc8;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_claim_strength_package(results: dict, output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    assessment = build_claim_strength_assessment(results)
    html_report = build_claim_strength_html(assessment)

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    candidates_df = pd.DataFrame(assessment.get("candidates") or [])
    metric_cohort_df = pd.DataFrame(assessment.get("metric_cohort") or [])
    metric_aggregate_df = pd.DataFrame(assessment.get("metric_aggregate") or [])
    pooled_metric_df = pd.DataFrame(assessment.get("pooled_metric") or [])
    head_to_head_df = pd.DataFrame(assessment.get("head_to_head") or [])

    markdown_path = root / "claim_strength_report.md"
    html_path = root / "claim_strength_report.html"
    manifest_path = root / "claim_strength_manifest.json"
    criteria_path = root / "claim_strength_criteria.csv"
    candidates_path = root / "claim_strength_candidates.csv"
    metric_cohort_path = root / "claim_strength_metric_cohort.csv"
    metric_aggregate_path = root / "claim_strength_metric_aggregate.csv"
    pooled_metric_path = root / "claim_strength_pooled_metric.csv"
    head_to_head_path = root / "claim_strength_head_to_head.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    candidates_df.to_csv(candidates_path, index=False)
    metric_cohort_df.to_csv(metric_cohort_path, index=False)
    metric_aggregate_df.to_csv(metric_aggregate_path, index=False)
    pooled_metric_df.to_csv(pooled_metric_path, index=False)
    head_to_head_df.to_csv(head_to_head_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "candidates_path": str(candidates_path),
        "metric_cohort_path": str(metric_cohort_path),
        "metric_aggregate_path": str(metric_aggregate_path),
        "pooled_metric_path": str(pooled_metric_path),
        "head_to_head_path": str(head_to_head_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "claim_strength_assessment": assessment,
        "claim_strength_report_markdown_path": str(markdown_path),
        "claim_strength_report_html_path": str(html_path),
        "claim_strength_manifest_path": str(manifest_path),
        "claim_strength_criteria_path": str(criteria_path),
        "claim_strength_candidates_path": str(candidates_path),
        "claim_strength_metric_cohort_path": str(metric_cohort_path),
        "claim_strength_metric_aggregate_path": str(metric_aggregate_path),
        "claim_strength_pooled_metric_path": str(pooled_metric_path),
        "claim_strength_head_to_head_path": str(head_to_head_path),
    }
