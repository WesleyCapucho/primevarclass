from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


POOLED_SUPPORT_METRICS = ("auc_roc", "auc_pr")


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


def _compute_metric(metric_name: str, y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return float("nan")
    if metric_name == "auc_roc":
        return float(roc_auc_score(y_true, y_score))
    if metric_name == "auc_pr":
        return float(average_precision_score(y_true, y_score))
    raise ValueError(f"Unsupported pooled metric: {metric_name}")


def _build_cohort_role_lookup(results: dict) -> Dict[str, str]:
    role_lookup: Dict[str, str] = {}
    cohort_manifest = results.get("cohort_manifest")
    if isinstance(cohort_manifest, pd.DataFrame) and not cohort_manifest.empty:
        for _, row in cohort_manifest.iterrows():
            role_lookup[str(row.get("cohort_name") or "")] = str(row.get("role") or "")
    external_metrics = results.get("external_evaluation_metrics")
    if isinstance(external_metrics, pd.DataFrame) and not external_metrics.empty:
        for _, row in external_metrics.iterrows():
            cohort_name = str(row.get("cohort") or "")
            if cohort_name and cohort_name not in role_lookup:
                role_lookup[cohort_name] = str(row.get("cohort_role") or "")
    return role_lookup


def _load_external_score_frame(results: dict) -> pd.DataFrame:
    external_score_paths = dict(results.get("external_score_paths") or {})
    if not external_score_paths:
        return pd.DataFrame()

    role_lookup = _build_cohort_role_lookup(results)
    frames: List[pd.DataFrame] = []
    for cohort_name, raw_path in external_score_paths.items():
        if not raw_path:
            continue
        path = Path(str(raw_path))
        if not path.exists():
            continue
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if frame.empty or "label" not in frame.columns:
            continue
        frame = frame.copy()
        frame["label"] = pd.to_numeric(frame["label"], errors="coerce")
        frame = frame[frame["label"].isin([0, 1])].copy()
        if frame.empty:
            continue
        frame["label"] = frame["label"].astype(int)
        frame["cohort"] = str(cohort_name)
        frame["cohort_role"] = role_lookup.get(str(cohort_name), "")
        frame["is_high_confidence_clinical_cohort"] = _is_high_confidence_clinical_cohort(
            cohort_name,
            role_lookup.get(str(cohort_name), ""),
        )
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _resolve_experiment_pairs(results: dict) -> pd.DataFrame:
    pairwise = results.get("external_pairwise_comparisons")
    pairwise_df = pairwise.copy() if isinstance(pairwise, pd.DataFrame) else pd.DataFrame()
    if not pairwise_df.empty:
        cols = ["experiment", "baseline_experiment"]
        out = pairwise_df[cols].dropna().drop_duplicates().copy()
    else:
        external_metrics = results.get("external_evaluation_metrics")
        external_df = external_metrics.copy() if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()
        if external_df.empty or "experiment" not in external_df.columns:
            return pd.DataFrame(columns=["experiment", "baseline_experiment"])
        study_design = results.get("study_design")
        baseline_experiment = str(getattr(study_design, "baseline_experiment", "") or "")
        if not baseline_experiment:
            return pd.DataFrame(columns=["experiment", "baseline_experiment"])
        out = external_df[["experiment"]].dropna().drop_duplicates().copy()
        out["baseline_experiment"] = baseline_experiment
        out = out[out["experiment"].astype(str) != baseline_experiment].copy()
    if out.empty:
        return pd.DataFrame(columns=["experiment", "baseline_experiment"])
    out["experiment"] = out["experiment"].astype(str)
    out["baseline_experiment"] = out["baseline_experiment"].astype(str)
    out = out[
        out["experiment"].astype(bool)
        & out["baseline_experiment"].astype(bool)
        & out["experiment"].ne(out["baseline_experiment"])
    ].copy()
    return out.reset_index(drop=True)


def _resample_within_cohort(cohort_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    sampled_groups: List[pd.DataFrame] = []
    for _, label_group in cohort_df.groupby("label", dropna=False):
        if label_group.empty:
            continue
        sample_size = len(label_group)
        indices = rng.integers(0, sample_size, size=sample_size)
        sampled_groups.append(label_group.iloc[indices].copy())
    if not sampled_groups:
        return cohort_df.head(0).copy()
    return pd.concat(sampled_groups, ignore_index=True)


def _bootstrap_pooled_metric_delta(
    pooled_df: pd.DataFrame,
    candidate_column: str,
    baseline_column: str,
    metric_name: str,
    n_bootstrap: int,
    random_state: int,
) -> Dict[str, Any]:
    observed = pooled_df.copy()
    y_true = observed["label"].astype(int).to_numpy()
    candidate_scores = pd.to_numeric(observed[candidate_column], errors="coerce").to_numpy(dtype=float)
    baseline_scores = pd.to_numeric(observed[baseline_column], errors="coerce").to_numpy(dtype=float)
    valid_mask = ~(np.isnan(candidate_scores) | np.isnan(baseline_scores))
    observed = observed.loc[valid_mask].copy()
    if observed.empty:
        return {
            "metric": metric_name,
            "pooled_candidate_value": float("nan"),
            "pooled_baseline_value": float("nan"),
            "pooled_delta_mean": float("nan"),
            "pooled_ci_lower_95": float("nan"),
            "pooled_ci_upper_95": float("nan"),
            "pooled_supported_gain": False,
            "pooled_positive_gain": False,
            "pooled_directional_confidence_percent": 0,
            "n_bootstrap_valid": 0,
        }

    observed_y = observed["label"].astype(int).to_numpy()
    observed_candidate = observed[candidate_column].astype(float).to_numpy(dtype=float)
    observed_baseline = observed[baseline_column].astype(float).to_numpy(dtype=float)
    observed_candidate_value = _compute_metric(metric_name, observed_y, observed_candidate)
    observed_baseline_value = _compute_metric(metric_name, observed_y, observed_baseline)
    observed_delta = observed_candidate_value - observed_baseline_value

    rng = np.random.default_rng(random_state)
    deltas: List[float] = []
    cohort_tables = list(observed.groupby("cohort", dropna=False))
    for _ in range(max(0, int(n_bootstrap))):
        boot_frames = [_resample_within_cohort(cohort_df, rng) for _, cohort_df in cohort_tables]
        boot_df = pd.concat(boot_frames, ignore_index=True) if boot_frames else observed.head(0).copy()
        if boot_df.empty or len(np.unique(boot_df["label"].astype(int).to_numpy())) < 2:
            continue
        boot_y = boot_df["label"].astype(int).to_numpy()
        boot_candidate = boot_df[candidate_column].astype(float).to_numpy(dtype=float)
        boot_baseline = boot_df[baseline_column].astype(float).to_numpy(dtype=float)
        boot_candidate_value = _compute_metric(metric_name, boot_y, boot_candidate)
        boot_baseline_value = _compute_metric(metric_name, boot_y, boot_baseline)
        if np.isnan(boot_candidate_value) or np.isnan(boot_baseline_value):
            continue
        deltas.append(float(boot_candidate_value - boot_baseline_value))

    if deltas:
        delta_array = np.asarray(deltas, dtype=float)
        ci_lower = float(np.percentile(delta_array, 2.5))
        ci_upper = float(np.percentile(delta_array, 97.5))
        directional_confidence = int(round(float(np.mean(delta_array > 0)) * 100))
        pooled_delta_mean = float(delta_array.mean())
    else:
        ci_lower = float("nan")
        ci_upper = float("nan")
        directional_confidence = 0
        pooled_delta_mean = observed_delta

    return {
        "metric": metric_name,
        "pooled_candidate_value": observed_candidate_value,
        "pooled_baseline_value": observed_baseline_value,
        "pooled_delta_mean": pooled_delta_mean,
        "pooled_observed_delta": observed_delta,
        "pooled_ci_lower_95": ci_lower,
        "pooled_ci_upper_95": ci_upper,
        "pooled_supported_gain": bool(not np.isnan(ci_lower) and ci_lower > 0),
        "pooled_positive_gain": bool(not np.isnan(observed_delta) and observed_delta > 0),
        "pooled_directional_confidence_percent": directional_confidence,
        "n_bootstrap_valid": int(len(deltas)),
    }


def build_pooled_external_support_table(
    results: dict,
    metrics: Iterable[str] = POOLED_SUPPORT_METRICS,
    n_bootstrap: int = 400,
    random_state: int = 42,
) -> pd.DataFrame:
    pooled_scores = _load_external_score_frame(results)
    experiment_pairs = _resolve_experiment_pairs(results)
    if pooled_scores.empty or experiment_pairs.empty:
        return pd.DataFrame()

    rows: List[dict] = []
    for _, pair in experiment_pairs.iterrows():
        experiment = str(pair.get("experiment") or "")
        baseline_experiment = str(pair.get("baseline_experiment") or "")
        candidate_column = f"score__{experiment}"
        baseline_column = f"score__{baseline_experiment}"
        if candidate_column not in pooled_scores.columns or baseline_column not in pooled_scores.columns:
            continue

        subset = pooled_scores[["cohort", "cohort_role", "is_high_confidence_clinical_cohort", "label", candidate_column, baseline_column]].copy()
        subset[candidate_column] = pd.to_numeric(subset[candidate_column], errors="coerce")
        subset[baseline_column] = pd.to_numeric(subset[baseline_column], errors="coerce")
        subset = subset.dropna(subset=[candidate_column, baseline_column, "label"]).copy()
        if subset.empty or subset["cohort"].astype(str).nunique() == 0:
            continue

        common_payload = {
            "experiment": experiment,
            "baseline_experiment": baseline_experiment,
            "feature_set": _feature_set_from_experiment(experiment),
            "is_prime_signal": _is_prime_signal(_feature_set_from_experiment(experiment)),
            "n_external_cohorts": int(subset["cohort"].astype(str).nunique()),
            "n_variants": int(len(subset)),
            "n_high_confidence_clinical_cohorts": int(
                subset.loc[subset["is_high_confidence_clinical_cohort"], "cohort"].astype(str).nunique()
            ),
            "n_high_confidence_clinical_variants": int(subset["is_high_confidence_clinical_cohort"].sum()),
        }
        for metric_name in metrics:
            payload = _bootstrap_pooled_metric_delta(
                pooled_df=subset,
                candidate_column=candidate_column,
                baseline_column=baseline_column,
                metric_name=str(metric_name),
                n_bootstrap=n_bootstrap,
                random_state=random_state,
            )
            rows.append({**common_payload, **payload})

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        [
            "metric",
            "pooled_supported_gain",
            "pooled_directional_confidence_percent",
            "pooled_delta_mean",
            "experiment",
        ],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)


def get_or_build_pooled_external_support(
    results: dict,
    metrics: Iterable[str] = POOLED_SUPPORT_METRICS,
    n_bootstrap: int = 400,
    random_state: int = 42,
) -> pd.DataFrame:
    cached = results.get("pooled_external_support")
    if isinstance(cached, pd.DataFrame):
        return cached.copy()
    table = build_pooled_external_support_table(
        results=results,
        metrics=metrics,
        n_bootstrap=n_bootstrap,
        random_state=random_state,
    )
    results["pooled_external_support"] = table.copy()
    return table
