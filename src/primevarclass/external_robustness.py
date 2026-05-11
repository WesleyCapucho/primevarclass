from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score


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


def _binomial_tail_probability(wins: int, trials: int, p: float = 0.5) -> float:
    if trials <= 0:
        return float("nan")
    probability = 0.0
    for k in range(int(wins), int(trials) + 1):
        probability += math.comb(int(trials), int(k)) * (p**k) * ((1.0 - p) ** (int(trials) - int(k)))
    return float(probability)


def _directional_confidence_percent(wins: int, losses: int) -> int:
    trials = int(wins) + int(losses)
    if trials <= 0:
        return 0
    effective_wins = max(int(wins), int(losses))
    tail = _binomial_tail_probability(effective_wins, trials)
    if np.isnan(tail):
        return 0
    return int(round((1.0 - tail) * 100))


def _compute_ece(y_true: np.ndarray, y_score: np.ndarray, bins: int = 10) -> float:
    if len(y_true) == 0:
        return float("nan")
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.clip(np.asarray(y_score, dtype=float), 1e-6, 1 - 1e-6)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for idx in range(bins):
        if idx == bins - 1:
            mask = (y_score >= edges[idx]) & (y_score <= edges[idx + 1])
        else:
            mask = (y_score >= edges[idx]) & (y_score < edges[idx + 1])
        if not mask.any():
            continue
        observed = float(np.mean(y_true[mask]))
        predicted = float(np.mean(y_score[mask]))
        ece += abs(observed - predicted) * (float(mask.sum()) / float(len(y_true)))
    return float(ece)


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else float("nan")


def _safe_auc_pr(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(average_precision_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else float("nan")


def _safe_mcc(y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    preds = (np.asarray(y_score, dtype=float) >= threshold).astype(int)
    return float(matthews_corrcoef(y_true, preds))


def _score_separation(y_true: np.ndarray, y_score: np.ndarray) -> float:
    positives = np.asarray(y_score, dtype=float)[np.asarray(y_true, dtype=int) == 1]
    negatives = np.asarray(y_score, dtype=float)[np.asarray(y_true, dtype=int) == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    return float(np.mean(positives) - np.mean(negatives))


def _score_bundle_metrics(frame: pd.DataFrame, score_column: str) -> dict:
    work = frame[["label", score_column]].dropna().copy()
    if work.empty:
        return {
            "n_variants": 0,
            "brier": float("nan"),
            "ece": float("nan"),
            "mean_positive_score": float("nan"),
            "mean_negative_score": float("nan"),
            "score_separation": float("nan"),
        }
    y_true = work["label"].astype(int).to_numpy(dtype=int)
    y_score = np.clip(work[score_column].astype(float).to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    positives = y_score[y_true == 1]
    negatives = y_score[y_true == 0]
    return {
        "n_variants": int(len(work)),
        "brier": float(np.mean(np.square(y_score - y_true))),
        "ece": _compute_ece(y_true, y_score),
        "mean_positive_score": float(np.mean(positives)) if len(positives) else float("nan"),
        "mean_negative_score": float(np.mean(negatives)) if len(negatives) else float("nan"),
        "score_separation": float(np.mean(positives) - np.mean(negatives))
        if len(positives) and len(negatives)
        else float("nan"),
    }


def _resolve_selected_experiment(results: dict) -> tuple[str, str, str]:
    claim_summary = dict((results.get("claim_strength_assessment") or {}).get("summary") or {})
    selected_experiment = str(results.get("robustness_target_experiment") or "")
    baseline_experiment = str(
        claim_summary.get("selected_baseline_experiment")
        or getattr(results.get("study_design"), "baseline_experiment", "external_predictors_only")
        or "external_predictors_only"
    )
    raw_metrics = results.get("external_evaluation_metrics")
    metrics_df = raw_metrics.copy() if isinstance(raw_metrics, pd.DataFrame) else pd.DataFrame()
    available_metrics = metrics_df.copy()
    if not available_metrics.empty:
        available_experiments = set(available_metrics.get("experiment", pd.Series(dtype=str)).astype(str))
        if selected_experiment and selected_experiment in available_experiments:
            return selected_experiment, baseline_experiment, "robustness_target"

    selected_experiment = str(claim_summary.get("selected_experiment") or "")
    if selected_experiment:
        return selected_experiment, baseline_experiment, "claim_strength"

    if metrics_df.empty:
        return "", baseline_experiment, "unresolved"
    combined = metrics_df.copy()
    if "evaluation_group" in combined.columns:
        combined = combined[combined["evaluation_group"].astype(str) == "combined"].copy()
    if baseline_experiment:
        combined = combined[combined["experiment"].astype(str) != baseline_experiment].copy()
    if combined.empty:
        return "", baseline_experiment, "unresolved"
    ranked = (
        combined.groupby("experiment", as_index=False)["auc_roc"]
        .mean()
        .sort_values(["auc_roc", "experiment"], ascending=[False, True])
    )
    return str(ranked.iloc[0]["experiment"]), baseline_experiment, "auc_roc_fallback"


def _load_score_tables(results: dict) -> pd.DataFrame:
    score_paths = dict(results.get("external_score_paths") or {})
    rows: list[pd.DataFrame] = []
    for cohort_name, path in score_paths.items():
        score_path = Path(str(path))
        if not score_path.exists():
            continue
        frame = pd.read_csv(score_path)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["cohort"] = str(cohort_name)
        rows.append(frame)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _build_calibration_table(results: dict, selected_experiment: str, baseline_experiment: str) -> pd.DataFrame:
    score_df = _load_score_tables(results)
    if score_df.empty or not selected_experiment or not baseline_experiment:
        return pd.DataFrame()

    selected_col = f"score__{selected_experiment}"
    baseline_col = f"score__{baseline_experiment}"
    if selected_col not in score_df.columns or baseline_col not in score_df.columns:
        return pd.DataFrame()

    rows: list[dict] = []
    for cohort_name, subset in score_df.groupby("cohort", dropna=False):
        selected_metrics = _score_bundle_metrics(subset, selected_col)
        baseline_metrics = _score_bundle_metrics(subset, baseline_col)
        delta_brier = _safe_float(baseline_metrics.get("brier")) - _safe_float(selected_metrics.get("brier"))
        delta_ece = _safe_float(baseline_metrics.get("ece")) - _safe_float(selected_metrics.get("ece"))
        delta_separation = _safe_float(selected_metrics.get("score_separation")) - _safe_float(
            baseline_metrics.get("score_separation")
        )
        rows.append(
            {
                "cohort": str(cohort_name),
                "is_high_confidence_clinical_cohort": _is_high_confidence_clinical_cohort(cohort_name),
                "n_variants": _safe_int(selected_metrics.get("n_variants")),
                "candidate_brier": _safe_float(selected_metrics.get("brier")),
                "baseline_brier": _safe_float(baseline_metrics.get("brier")),
                "delta_brier_improvement": delta_brier,
                "candidate_ece": _safe_float(selected_metrics.get("ece")),
                "baseline_ece": _safe_float(baseline_metrics.get("ece")),
                "delta_ece_improvement": delta_ece,
                "candidate_score_separation": _safe_float(selected_metrics.get("score_separation")),
                "baseline_score_separation": _safe_float(baseline_metrics.get("score_separation")),
                "delta_score_separation": delta_separation,
                "brier_win": bool(delta_brier > 0),
                "ece_win": bool(delta_ece > 0),
                "separation_win": bool(delta_separation > 0),
                "calibration_no_regression": bool(delta_brier >= -0.01 and delta_ece >= -0.02),
            }
        )
    return pd.DataFrame(rows).sort_values(["cohort"], ascending=[True]).reset_index(drop=True)


def _build_discrimination_table(results: dict, selected_experiment: str, baseline_experiment: str) -> pd.DataFrame:
    external_df = results.get("external_evaluation_metrics")
    metrics_df = external_df.copy() if isinstance(external_df, pd.DataFrame) else pd.DataFrame()
    if metrics_df.empty or not selected_experiment or not baseline_experiment:
        return pd.DataFrame()
    if "evaluation_group" in metrics_df.columns:
        metrics_df = metrics_df[metrics_df["evaluation_group"].astype(str) == "combined"].copy()
    if metrics_df.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for cohort_name, subset in metrics_df.groupby("cohort", dropna=False):
        candidate_row = subset[subset["experiment"].astype(str) == selected_experiment].head(1)
        baseline_row = subset[subset["experiment"].astype(str) == baseline_experiment].head(1)
        if candidate_row.empty or baseline_row.empty:
            continue
        candidate = candidate_row.iloc[0]
        baseline = baseline_row.iloc[0]
        auc_roc_delta = _safe_float(candidate.get("auc_roc")) - _safe_float(baseline.get("auc_roc"))
        auc_pr_delta = _safe_float(candidate.get("auc_pr")) - _safe_float(baseline.get("auc_pr"))
        mcc_delta = _safe_float(candidate.get("mcc")) - _safe_float(baseline.get("mcc"))
        rows.append(
            {
                "cohort": str(cohort_name),
                "is_high_confidence_clinical_cohort": _is_high_confidence_clinical_cohort(cohort_name),
                "candidate_auc_roc": _safe_float(candidate.get("auc_roc")),
                "baseline_auc_roc": _safe_float(baseline.get("auc_roc")),
                "delta_auc_roc": auc_roc_delta,
                "candidate_auc_pr": _safe_float(candidate.get("auc_pr")),
                "baseline_auc_pr": _safe_float(baseline.get("auc_pr")),
                "delta_auc_pr": auc_pr_delta,
                "candidate_mcc": _safe_float(candidate.get("mcc")),
                "baseline_mcc": _safe_float(baseline.get("mcc")),
                "delta_mcc": mcc_delta,
                "auc_roc_win": bool(auc_roc_delta > 0),
                "auc_pr_win": bool(auc_pr_delta > 0),
                "mcc_win": bool(mcc_delta > 0),
                "discrimination_no_regression": bool(auc_roc_delta >= -0.01 and auc_pr_delta >= -0.02 and mcc_delta >= -0.03),
            }
        )
    return pd.DataFrame(rows).sort_values(["cohort"], ascending=[True]).reset_index(drop=True)


def _score_delta_from_frame(
    frame: pd.DataFrame,
    candidate_col: str,
    baseline_col: str,
    metric_id: str,
) -> float:
    work = frame[["label", candidate_col, baseline_col]].dropna().copy()
    if work.empty:
        return float("nan")

    y_true = work["label"].astype(int).to_numpy(dtype=int)
    candidate_score = np.clip(work[candidate_col].astype(float).to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    baseline_score = np.clip(work[baseline_col].astype(float).to_numpy(dtype=float), 1e-6, 1 - 1e-6)

    if metric_id == "brier_improvement":
        return float(np.mean(np.square(baseline_score - y_true)) - np.mean(np.square(candidate_score - y_true)))
    if metric_id == "ece_improvement":
        return float(_compute_ece(y_true, baseline_score) - _compute_ece(y_true, candidate_score))
    if metric_id == "score_separation":
        return float(_score_separation(y_true, candidate_score) - _score_separation(y_true, baseline_score))
    if metric_id == "auc_roc":
        return float(_safe_auc(y_true, candidate_score) - _safe_auc(y_true, baseline_score))
    if metric_id == "auc_pr":
        return float(_safe_auc_pr(y_true, candidate_score) - _safe_auc_pr(y_true, baseline_score))
    if metric_id == "mcc":
        return float(_safe_mcc(y_true, candidate_score) - _safe_mcc(y_true, baseline_score))
    raise ValueError(f"Metrica pooled de robustez nao suportada: {metric_id}")


def _bootstrap_pooled_metric_support(
    frame: pd.DataFrame,
    candidate_col: str,
    baseline_col: str,
    metric_id: str,
    cohort_scope: str,
    metric_category: str,
    n_bootstrap: int = 400,
    random_state: int = 42,
) -> dict[str, Any]:
    work = frame[["cohort", "label", candidate_col, baseline_col]].dropna().copy()
    if work.empty:
        return {
            "cohort_scope": cohort_scope,
            "metric_id": metric_id,
            "metric_category": metric_category,
            "n_cohorts": 0,
            "n_variants": 0,
            "delta_mean": float("nan"),
            "ci_lower_95": float("nan"),
            "ci_upper_95": float("nan"),
            "positive_direction_confidence_percent": 0,
            "direction_confidence_percent": 0,
            "supported_gain": False,
            "support_percent": 0,
        }

    observed_delta = _score_delta_from_frame(work, candidate_col, baseline_col, metric_id)
    rng = np.random.default_rng(random_state)
    bootstrapped: list[float] = []
    grouped = list(work.groupby("cohort", sort=True))
    for _ in range(int(n_bootstrap)):
        sampled_cohorts: list[pd.DataFrame] = []
        for _, cohort_df in grouped:
            sampled_labels: list[pd.DataFrame] = []
            for _, label_df in cohort_df.groupby("label", sort=True):
                if label_df.empty:
                    continue
                sampled_labels.append(
                    label_df.sample(
                        n=len(label_df),
                        replace=True,
                        random_state=int(rng.integers(0, 2**31 - 1)),
                    )
                )
            if sampled_labels:
                sampled_cohorts.append(pd.concat(sampled_labels, ignore_index=True))
        if not sampled_cohorts:
            continue
        sampled_frame = pd.concat(sampled_cohorts, ignore_index=True)
        delta = _score_delta_from_frame(sampled_frame, candidate_col, baseline_col, metric_id)
        if not np.isnan(delta):
            bootstrapped.append(float(delta))

    if bootstrapped:
        boot = np.asarray(bootstrapped, dtype=float)
        ci_lower = float(np.nanpercentile(boot, 2.5))
        ci_upper = float(np.nanpercentile(boot, 97.5))
        positive_direction_confidence = int(round(float(np.mean(boot > 0)) * 100))
        negative_direction_confidence = int(round(float(np.mean(boot < 0)) * 100))
        direction_confidence = max(positive_direction_confidence, negative_direction_confidence)
    else:
        ci_lower = float("nan")
        ci_upper = float("nan")
        positive_direction_confidence = 0
        direction_confidence = 0

    supported_gain = bool(not np.isnan(ci_lower) and ci_lower > 0)
    support_percent = 100 if supported_gain else (
        positive_direction_confidence if not np.isnan(observed_delta) and observed_delta > 0 else 0
    )
    return {
        "cohort_scope": cohort_scope,
        "metric_id": metric_id,
        "metric_category": metric_category,
        "n_cohorts": int(work["cohort"].astype(str).nunique()),
        "n_variants": int(len(work)),
        "delta_mean": float(observed_delta),
        "ci_lower_95": ci_lower,
        "ci_upper_95": ci_upper,
        "positive_direction_confidence_percent": int(positive_direction_confidence),
        "direction_confidence_percent": int(direction_confidence),
        "supported_gain": supported_gain,
        "support_percent": int(max(0, min(100, round(support_percent)))),
    }


def _build_pooled_support_table(results: dict, selected_experiment: str, baseline_experiment: str) -> pd.DataFrame:
    score_df = _load_score_tables(results)
    if score_df.empty or not selected_experiment or not baseline_experiment:
        return pd.DataFrame()

    candidate_col = f"score__{selected_experiment}"
    baseline_col = f"score__{baseline_experiment}"
    if candidate_col not in score_df.columns or baseline_col not in score_df.columns:
        return pd.DataFrame()

    metric_specs = [
        ("brier_improvement", "calibration"),
        ("ece_improvement", "calibration"),
        ("score_separation", "calibration"),
        ("auc_roc", "discrimination"),
        ("auc_pr", "discrimination"),
        ("mcc", "discrimination"),
    ]
    scope_specs = [
        ("all_external", score_df.copy()),
        (
            "high_confidence_clinical",
            score_df[score_df["cohort"].astype(str).map(_is_high_confidence_clinical_cohort)].copy(),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for cohort_scope, subset in scope_specs:
        if subset.empty:
            continue
        for metric_id, metric_category in metric_specs:
            rows.append(
                _bootstrap_pooled_metric_support(
                    frame=subset,
                    candidate_col=candidate_col,
                    baseline_col=baseline_col,
                    metric_id=metric_id,
                    cohort_scope=cohort_scope,
                    metric_category=metric_category,
                )
            )

    pooled_df = pd.DataFrame(rows)
    if pooled_df.empty:
        return pooled_df
    return pooled_df.sort_values(["cohort_scope", "metric_category", "metric_id"], ascending=[True, True, True]).reset_index(drop=True)


def build_external_robustness_assessment(results: dict) -> dict:
    selected_experiment, baseline_experiment, selection_basis = _resolve_selected_experiment(results)
    calibration_df = _build_calibration_table(results, selected_experiment, baseline_experiment)
    discrimination_df = _build_discrimination_table(results, selected_experiment, baseline_experiment)
    pooled_support_df = _build_pooled_support_table(results, selected_experiment, baseline_experiment)

    def _pooled_scope_score(scope: str, metric_ids: list[str]) -> int:
        if pooled_support_df.empty:
            return 0
        subset = pooled_support_df[
            (pooled_support_df["cohort_scope"].astype(str) == scope)
            & (pooled_support_df["metric_id"].astype(str).isin(metric_ids))
        ].copy()
        if subset.empty:
            return 0
        return int(round(subset["support_percent"].astype(float).mean()))

    calibration_coverage_percent = 100 if not calibration_df.empty else 0
    discrimination_coverage_percent = 100 if not discrimination_df.empty else 0
    brier_win_rate_percent = int(round(calibration_df["brier_win"].mean() * 100)) if not calibration_df.empty else 0
    ece_win_rate_percent = int(round(calibration_df["ece_win"].mean() * 100)) if not calibration_df.empty else 0
    calibration_no_regression_rate_percent = (
        int(round(calibration_df["calibration_no_regression"].mean() * 100)) if not calibration_df.empty else 0
    )
    separation_win_rate_percent = (
        int(round(calibration_df["separation_win"].mean() * 100)) if not calibration_df.empty else 0
    )
    auc_roc_win_rate_percent = (
        int(round(discrimination_df["auc_roc_win"].mean() * 100)) if not discrimination_df.empty else 0
    )
    auc_pr_win_rate_percent = (
        int(round(discrimination_df["auc_pr_win"].mean() * 100)) if not discrimination_df.empty else 0
    )
    mcc_win_rate_percent = int(round(discrimination_df["mcc_win"].mean() * 100)) if not discrimination_df.empty else 0
    discrimination_no_regression_rate_percent = (
        int(round(discrimination_df["discrimination_no_regression"].mean() * 100)) if not discrimination_df.empty else 0
    )
    pooled_calibration_support_percent = _pooled_scope_score(
        "all_external",
        ["brier_improvement", "ece_improvement", "score_separation"],
    )
    pooled_discrimination_support_percent = _pooled_scope_score(
        "all_external",
        ["auc_roc", "auc_pr", "mcc"],
    )

    calibration_losses = (
        int((~calibration_df["brier_win"]).sum())
        + int((~calibration_df["ece_win"]).sum())
        + int((~calibration_df["separation_win"]).sum())
    ) if not calibration_df.empty else 0
    discrimination_losses = (
        int((~discrimination_df["auc_roc_win"]).sum())
        + int((~discrimination_df["auc_pr_win"]).sum())
        + int((~discrimination_df["mcc_win"]).sum())
    ) if not discrimination_df.empty else 0
    sign_wins = (
        int(calibration_df["brier_win"].sum())
        + int(calibration_df["ece_win"].sum())
        + int(calibration_df["separation_win"].sum())
        + int(discrimination_df["auc_roc_win"].sum())
        + int(discrimination_df["auc_pr_win"].sum())
        + int(discrimination_df["mcc_win"].sum())
    )
    sign_losses = calibration_losses + discrimination_losses
    exact_sign_confidence_percent = _directional_confidence_percent(sign_wins, sign_losses)

    high_conf_calibration = (
        calibration_df[calibration_df["is_high_confidence_clinical_cohort"]].copy()
        if not calibration_df.empty
        else pd.DataFrame()
    )
    high_conf_discrimination = (
        discrimination_df[discrimination_df["is_high_confidence_clinical_cohort"]].copy()
        if not discrimination_df.empty
        else pd.DataFrame()
    )
    high_conf_brier_win_rate_percent = (
        int(round(high_conf_calibration["brier_win"].mean() * 100)) if not high_conf_calibration.empty else 0
    )
    high_conf_ece_win_rate_percent = (
        int(round(high_conf_calibration["ece_win"].mean() * 100)) if not high_conf_calibration.empty else 0
    )
    high_conf_separation_win_rate_percent = (
        int(round(high_conf_calibration["separation_win"].mean() * 100)) if not high_conf_calibration.empty else 0
    )
    high_conf_auc_roc_win_rate_percent = (
        int(round(high_conf_discrimination["auc_roc_win"].mean() * 100)) if not high_conf_discrimination.empty else 0
    )
    high_conf_auc_pr_win_rate_percent = (
        int(round(high_conf_discrimination["auc_pr_win"].mean() * 100)) if not high_conf_discrimination.empty else 0
    )
    high_conf_mcc_win_rate_percent = (
        int(round(high_conf_discrimination["mcc_win"].mean() * 100)) if not high_conf_discrimination.empty else 0
    )
    high_conf_discrimination_no_regression_rate_percent = (
        int(round(high_conf_discrimination["discrimination_no_regression"].mean() * 100))
        if not high_conf_discrimination.empty
        else 0
    )
    pooled_high_confidence_clinical_support_percent = _pooled_scope_score(
        "high_confidence_clinical",
        ["brier_improvement", "ece_improvement", "auc_roc", "auc_pr", "mcc"],
    )
    calibration_leadership_percent = int(
        round(
            np.mean(
                [
                    float(brier_win_rate_percent),
                    float(ece_win_rate_percent),
                    float(separation_win_rate_percent),
                    float(pooled_calibration_support_percent),
                ]
            )
        )
    )
    discrimination_robustness_percent = int(
        round(
            np.mean(
                [
                    float(auc_roc_win_rate_percent),
                    float(auc_pr_win_rate_percent),
                    float(mcc_win_rate_percent),
                    float(pooled_discrimination_support_percent),
                ]
            )
        )
    )
    high_confidence_clinical_robustness_percent = int(
        round(
            np.mean(
                [
                    float(high_conf_brier_win_rate_percent),
                    float(high_conf_ece_win_rate_percent),
                    float(high_conf_auc_roc_win_rate_percent),
                    float(high_conf_auc_pr_win_rate_percent),
                    float(high_conf_mcc_win_rate_percent),
                    float(high_conf_discrimination_no_regression_rate_percent),
                    float(pooled_high_confidence_clinical_support_percent),
                ]
            )
        )
    )
    effective_high_confidence_clinical_robustness_percent = int(
        round(
            np.mean(
                [
                    float(high_confidence_clinical_robustness_percent),
                    float(pooled_high_confidence_clinical_support_percent),
                    float(high_conf_auc_roc_win_rate_percent),
                    float(high_conf_discrimination_no_regression_rate_percent),
                ]
            )
        )
    )

    heterogeneity_stability_percent = 0
    if not discrimination_df.empty:
        delta_std = float(discrimination_df["delta_auc_roc"].astype(float).std(ddof=0))
        heterogeneity_stability_percent = int(round(max(0.0, 1.0 - min(delta_std / 0.15, 1.0)) * 100))

    criteria = [
        _criterion_row(
            "coverage",
            "External robustness coverage",
            0.9,
            int(round((calibration_coverage_percent + discrimination_coverage_percent) / 2)),
            f"Calibration in {calibration_coverage_percent}% and discrimination in {discrimination_coverage_percent}% of external cohorts.",
            "Guarantee paired score files and external metrics for every frozen cohort.",
            critical=True,
        ),
        _criterion_row(
            "calibration_wins",
            "Calibration leadership",
            1.05,
            calibration_leadership_percent,
            (
                f"Brier win={brier_win_rate_percent}%, ECE win={ece_win_rate_percent}% "
                f"and separation win={separation_win_rate_percent}% with pooled support={pooled_calibration_support_percent}%."
            ),
            "Improve external calibration and score separation against the declared baseline.",
            critical=True,
        ),
        _criterion_row(
            "calibration_safety",
            "Calibration safety",
            1.0,
            calibration_no_regression_rate_percent,
            f"{calibration_no_regression_rate_percent}% of external cohorts show no relevant calibration regression.",
            "Reduce calibration regressions before claiming stronger translational use.",
            critical=True,
        ),
        _criterion_row(
            "discrimination_wins",
            "Discrimination robustness",
            1.1,
            discrimination_robustness_percent,
            (
                f"AUC-ROC win={auc_roc_win_rate_percent}%, AUC-PR win={auc_pr_win_rate_percent}% "
                f"and MCC win={mcc_win_rate_percent}% with pooled support={pooled_discrimination_support_percent}%."
            ),
            "Consolidate external wins across the core benchmark metrics.",
            critical=True,
        ),
        _criterion_row(
            "sign_confidence",
            "Exact sign confidence",
            1.0,
            exact_sign_confidence_percent,
            f"{exact_sign_confidence_percent}% directional confidence across external calibration and discrimination wins or losses.",
            "Increase directional confidence with more independent cohorts or stronger signal.",
            critical=True,
        ),
        _criterion_row(
            "clinical_holdout_robustness",
            "High-confidence clinical robustness",
            1.1,
            effective_high_confidence_clinical_robustness_percent,
            (
                f"Robustness in high-confidence clinical cohorts = {high_confidence_clinical_robustness_percent}% "
                f"(effective={effective_high_confidence_clinical_robustness_percent}%) "
                f"with pooled support={pooled_high_confidence_clinical_support_percent}%."
            ),
            "Strengthen calibration and discrimination specifically in expert-grade clinical cohorts.",
            critical=True,
        ),
        _criterion_row(
            "heterogeneity_stability",
            "Cross-cohort stability",
            0.9,
            heterogeneity_stability_percent,
            f"Cross-cohort stability based on the spread of AUC-ROC deltas = {heterogeneity_stability_percent}%.",
            "Reduce heterogeneity across external cohorts and genes before framing the result as stable.",
        ),
    ]

    weighted_total = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / weighted_total)) if weighted_total else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    markdown_lines = [
        "# External Robustness Package",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Selected candidate: {selected_experiment or '-'}",
        f"- Selection basis: {selection_basis}",
        f"- Baseline comparator: {baseline_experiment or '-'}",
        f"- Overall external robustness: {overall_percent}%",
        f"- Exact sign confidence: {exact_sign_confidence_percent}%",
        f"- Pooled calibration support: {pooled_calibration_support_percent}%",
        f"- Pooled high-confidence clinical support: {pooled_high_confidence_clinical_support_percent}%",
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

    markdown_lines.extend(["## Cohort Calibration", ""])
    if calibration_df.empty:
        markdown_lines.append("- Calibration evidence unavailable.")
    else:
        for _, row in calibration_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort']}: dBrier={_fmt_metric(row['delta_brier_improvement'])}, "
                f"dECE={_fmt_metric(row['delta_ece_improvement'])}, "
                f"dSeparation={_fmt_metric(row['delta_score_separation'])}."
            )

    markdown_lines.extend(["", "## Cohort Discrimination", ""])
    if discrimination_df.empty:
        markdown_lines.append("- Discrimination evidence unavailable.")
    else:
        for _, row in discrimination_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort']}: dAUC-ROC={_fmt_metric(row['delta_auc_roc'])}, "
                f"dAUC-PR={_fmt_metric(row['delta_auc_pr'])}, dMCC={_fmt_metric(row['delta_mcc'])}."
            )

    markdown_lines.extend(["", "## Pooled Support", ""])
    if pooled_support_df.empty:
        markdown_lines.append("- Pooled support unavailable.")
    else:
        for _, row in pooled_support_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort_scope']} / {row['metric_id']}: delta={_fmt_metric(row['delta_mean'])}, "
                f"CI95=[{_fmt_metric(row['ci_lower_95'])}, {_fmt_metric(row['ci_upper_95'])}], "
                f"support={_safe_int(row['support_percent'])}%."
            )

    return {
        "summary": {
            "generated_at": _now_utc(),
            "selected_experiment": selected_experiment or None,
            "selection_basis": selection_basis,
            "baseline_experiment": baseline_experiment or None,
            "overall_external_robustness_percent": overall_percent,
            "overall_status": _status_from_percent(overall_percent),
            "calibration_coverage_percent": calibration_coverage_percent,
            "discrimination_coverage_percent": discrimination_coverage_percent,
            "brier_win_rate_percent": brier_win_rate_percent,
            "ece_win_rate_percent": ece_win_rate_percent,
            "separation_win_rate_percent": separation_win_rate_percent,
            "pooled_calibration_support_percent": pooled_calibration_support_percent,
            "calibration_no_regression_rate_percent": calibration_no_regression_rate_percent,
            "auc_roc_win_rate_percent": auc_roc_win_rate_percent,
            "auc_pr_win_rate_percent": auc_pr_win_rate_percent,
            "mcc_win_rate_percent": mcc_win_rate_percent,
            "pooled_discrimination_support_percent": pooled_discrimination_support_percent,
            "discrimination_no_regression_rate_percent": discrimination_no_regression_rate_percent,
            "exact_sign_confidence_percent": exact_sign_confidence_percent,
            "high_conf_brier_win_rate_percent": high_conf_brier_win_rate_percent,
            "high_conf_ece_win_rate_percent": high_conf_ece_win_rate_percent,
            "high_conf_separation_win_rate_percent": high_conf_separation_win_rate_percent,
            "high_conf_auc_roc_win_rate_percent": high_conf_auc_roc_win_rate_percent,
            "high_conf_auc_pr_win_rate_percent": high_conf_auc_pr_win_rate_percent,
            "high_conf_mcc_win_rate_percent": high_conf_mcc_win_rate_percent,
            "high_conf_discrimination_no_regression_rate_percent": high_conf_discrimination_no_regression_rate_percent,
            "pooled_high_confidence_clinical_support_percent": pooled_high_confidence_clinical_support_percent,
            "high_confidence_clinical_robustness_percent": high_confidence_clinical_robustness_percent,
            "effective_high_confidence_clinical_robustness_percent": effective_high_confidence_clinical_robustness_percent,
            "heterogeneity_stability_percent": heterogeneity_stability_percent,
            "n_critical_gaps": int(len(critical_gaps)),
        },
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "calibration": calibration_df.to_dict(orient="records"),
        "discrimination": discrimination_df.to_dict(orient="records"),
        "pooled_support": pooled_support_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_external_robustness_html(assessment: dict) -> str:
    markdown = str(assessment.get("markdown_report") or "")
    blocks: list[str] = []
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
        "<title>PrimeVarClass External Robustness</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f2ec;color:#1e2732;max-width:1020px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#7b3f24;}h3{margin-top:1.35rem;color:#305d66;}"
        "ul{background:#fff;border:1px solid #e8dcc8;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_external_robustness_package(results: dict, output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    assessment = build_external_robustness_assessment(results)
    html_report = build_external_robustness_html(assessment)

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    calibration_df = pd.DataFrame(assessment.get("calibration") or [])
    discrimination_df = pd.DataFrame(assessment.get("discrimination") or [])
    pooled_support_df = pd.DataFrame(assessment.get("pooled_support") or [])

    markdown_path = root / "external_robustness_report.md"
    html_path = root / "external_robustness_report.html"
    manifest_path = root / "external_robustness_manifest.json"
    criteria_path = root / "external_robustness_criteria.csv"
    calibration_path = root / "external_robustness_calibration.csv"
    discrimination_path = root / "external_robustness_discrimination.csv"
    pooled_support_path = root / "external_robustness_pooled_support.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    calibration_df.to_csv(calibration_path, index=False)
    discrimination_df.to_csv(discrimination_path, index=False)
    pooled_support_df.to_csv(pooled_support_path, index=False)

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "criteria_path": str(criteria_path),
        "calibration_path": str(calibration_path),
        "discrimination_path": str(discrimination_path),
        "pooled_support_path": str(pooled_support_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "external_robustness_assessment": assessment,
        "external_robustness_report_markdown_path": str(markdown_path),
        "external_robustness_report_html_path": str(html_path),
        "external_robustness_manifest_path": str(manifest_path),
        "external_robustness_criteria_path": str(criteria_path),
        "external_robustness_calibration_path": str(calibration_path),
        "external_robustness_discrimination_path": str(discrimination_path),
        "external_robustness_pooled_support_path": str(pooled_support_path),
    }
