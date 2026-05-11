from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, matthews_corrcoef


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    return default if np.isnan(numeric) else numeric


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _fmt(value: Any) -> str:
    numeric = _safe_float(value)
    return "-" if np.isnan(numeric) else f"{numeric:.4f}"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(values, dtype=float)))


def _ece(y_true: np.ndarray, y_score: np.ndarray, bins: int = 10) -> float:
    if len(y_true) == 0:
        return float("nan")
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.clip(np.asarray(y_score, dtype=float), 1e-6, 1 - 1e-6)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for idx in range(bins):
        if idx == bins - 1:
            mask = (y_score >= edges[idx]) & (y_score <= edges[idx + 1])
        else:
            mask = (y_score >= edges[idx]) & (y_score < edges[idx + 1])
        if not mask.any():
            continue
        total += abs(float(np.mean(y_true[mask])) - float(np.mean(y_score[mask]))) * (float(mask.sum()) / len(y_true))
    return float(total)


def _brier(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(y_true) == 0:
        return float("nan")
    y_score = np.clip(np.asarray(y_score, dtype=float), 1e-6, 1 - 1e-6)
    y_true = np.asarray(y_true, dtype=float)
    return float(np.mean(np.square(y_score - y_true)))


def _score_separation(y_true: np.ndarray, y_score: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    positives = y_score[y_true == 1]
    negatives = y_score[y_true == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    return float(np.mean(positives) - np.mean(negatives))


def _classification_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    pred = (y_score >= float(threshold)).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, pred)),
        "mcc": float(matthews_corrcoef(y_true, pred)) if len(np.unique(y_true)) == 2 else float("nan"),
        "sensitivity": tp / (tp + fn) if (tp + fn) else float("nan"),
        "specificity": tn / (tn + fp) if (tn + fp) else float("nan"),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


def _best_threshold(y_true: np.ndarray, y_score: np.ndarray) -> dict:
    rows = [_classification_metrics(y_true, y_score, threshold) for threshold in np.linspace(0.05, 0.95, 19)]
    ranked = sorted(
        rows,
        key=lambda item: (
            _safe_float(item.get("mcc"), -1.0),
            _safe_float(item.get("accuracy"), -1.0),
            -abs(float(item.get("threshold", 0.5)) - 0.5),
        ),
        reverse=True,
    )
    return ranked[0] if ranked else _classification_metrics(y_true, y_score, 0.5)


def _calibration_bins(cohort: str, score_type: str, y_true: np.ndarray, y_score: np.ndarray, bins: int = 10) -> list[dict]:
    rows: list[dict] = []
    edges = np.linspace(0.0, 1.0, bins + 1)
    for idx in range(bins):
        low = float(edges[idx])
        high = float(edges[idx + 1])
        if idx == bins - 1:
            mask = (y_score >= low) & (y_score <= high)
        else:
            mask = (y_score >= low) & (y_score < high)
        if not mask.any():
            rows.append(
                {
                    "cohort": cohort,
                    "score_type": score_type,
                    "bin_index": idx + 1,
                    "bin_low": low,
                    "bin_high": high,
                    "n": 0,
                    "mean_predicted": float("nan"),
                    "observed_rate": float("nan"),
                    "absolute_gap": float("nan"),
                }
            )
            continue
        predicted = float(np.mean(y_score[mask]))
        observed = float(np.mean(y_true[mask]))
        rows.append(
            {
                "cohort": cohort,
                "score_type": score_type,
                "bin_index": idx + 1,
                "bin_low": low,
                "bin_high": high,
                "n": int(mask.sum()),
                "mean_predicted": predicted,
                "observed_rate": observed,
                "absolute_gap": abs(predicted - observed),
            }
        )
    return rows


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _resolve_experiments(study_dir: Path, candidate_experiment: str | None, baseline_experiment: str | None) -> tuple[str, str]:
    claim_summary = (_read_json(study_dir / "claim_strength_manifest.json").get("summary") or {})
    robustness_summary = (_read_json(study_dir / "external_robustness_manifest.json").get("summary") or {})
    candidate = (
        candidate_experiment
        or claim_summary.get("selected_experiment")
        or robustness_summary.get("selected_experiment")
        or "hybrid_plus_external__logistic_regression"
    )
    baseline = (
        baseline_experiment
        or claim_summary.get("selected_baseline_experiment")
        or robustness_summary.get("baseline_experiment")
        or "external_predictors_only__logistic_regression"
    )
    return str(candidate), str(baseline)


def _score_paths(study_dir: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(study_dir.glob("study_scores_*.csv")):
        cohort = path.name.removeprefix("study_scores_").removesuffix(".csv")
        paths[cohort] = path
    return paths


def _processed_dataset_path(study_dir: Path, cohort: str) -> Path | None:
    direct = study_dir / "cohorts" / f"{cohort}_processed_dataset.csv"
    if direct.exists():
        return direct
    nested = study_dir / "cohorts" / f"{cohort}_ingestion" / "integrated_sources.csv"
    if nested.exists():
        return nested
    return None


def _metadata_for_cohort(study_dir: Path, cohort: str) -> pd.DataFrame:
    path = _processed_dataset_path(study_dir, cohort)
    if path is None:
        return pd.DataFrame()
    columns = [
        "variant",
        "feature_gnomad_af",
        "feature_mave_score",
        "prime_diff",
        "prime_ratio",
        "prime_local_density_delta",
        "biochemical_severity_score",
        "functional_domain",
        "protein_interface",
        "review_status",
        "source",
    ]
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    available = [column for column in columns if column in frame.columns]
    if "variant" not in available:
        return pd.DataFrame()
    return frame[available].drop_duplicates(subset=["variant"])


def build_calibration_rescue_package(
    study_dir: str,
    output_dir: str | None = None,
    candidate_experiment: str | None = None,
    baseline_experiment: str | None = None,
    focus_cohort: str = "bridges_like_external_validation_brca1",
) -> dict:
    study_root = Path(study_dir).resolve()
    if not study_root.exists():
        raise FileNotFoundError(f"Study directory not found: {study_root}")
    candidate, baseline = _resolve_experiments(study_root, candidate_experiment, baseline_experiment)
    candidate_column = f"score__{candidate}"
    baseline_column = f"score__{baseline}"

    score_paths = _score_paths(study_root)
    if not score_paths:
        raise ValueError(f"No study_scores_*.csv files found in {study_root}")

    summary_rows: list[dict] = []
    threshold_rows: list[dict] = []
    bin_rows: list[dict] = []
    queue_rows: list[dict] = []

    for cohort, score_path in score_paths.items():
        scores = pd.read_csv(score_path)
        if candidate_column not in scores.columns:
            raise ValueError(f"Candidate score column not found in {score_path}: {candidate_column}")
        if baseline_column not in scores.columns:
            raise ValueError(f"Baseline score column not found in {score_path}: {baseline_column}")
        work = scores[["variant", "gene", "label", candidate_column, baseline_column]].dropna(subset=["label"]).copy()
        work["label"] = work["label"].astype(int)
        y_true = work["label"].to_numpy(dtype=int)
        raw = np.clip(work[candidate_column].astype(float).to_numpy(dtype=float), 1e-6, 1 - 1e-6)
        baseline_scores = np.clip(work[baseline_column].astype(float).to_numpy(dtype=float), 1e-6, 1 - 1e-6)

        observed_prevalence = float(np.mean(y_true)) if len(y_true) else float("nan")
        mean_raw = float(np.mean(raw)) if len(raw) else float("nan")
        intercept_shift = float(_logit(np.array([observed_prevalence]))[0] - _logit(np.array([mean_raw]))[0])
        calibrated = np.clip(_sigmoid(_logit(raw) + intercept_shift), 1e-6, 1 - 1e-6)

        raw_brier = _brier(y_true, raw)
        calibrated_brier = _brier(y_true, calibrated)
        baseline_brier = _brier(y_true, baseline_scores)
        raw_ece = _ece(y_true, raw)
        calibrated_ece = _ece(y_true, calibrated)
        baseline_ece = _ece(y_true, baseline_scores)
        raw_threshold = _best_threshold(y_true, raw)
        calibrated_threshold = _best_threshold(y_true, calibrated)
        baseline_threshold = _best_threshold(y_true, baseline_scores)

        raw_safe_vs_baseline = bool(raw_brier <= baseline_brier + 0.005 and raw_ece <= baseline_ece + 0.02)
        calibrated_safe_vs_baseline = bool(
            calibrated_brier <= baseline_brier + 0.005 and calibrated_ece <= baseline_ece + 0.02
        )
        summary_rows.append(
            {
                "cohort": cohort,
                "n_variants": int(len(work)),
                "observed_prevalence": observed_prevalence,
                "raw_mean_score": mean_raw,
                "calibration_intercept_shift": intercept_shift,
                "raw_brier": raw_brier,
                "calibrated_brier": calibrated_brier,
                "baseline_brier": baseline_brier,
                "delta_brier_raw_to_calibrated": raw_brier - calibrated_brier,
                "delta_brier_vs_baseline_after": baseline_brier - calibrated_brier,
                "raw_ece": raw_ece,
                "calibrated_ece": calibrated_ece,
                "baseline_ece": baseline_ece,
                "delta_ece_raw_to_calibrated": raw_ece - calibrated_ece,
                "delta_ece_vs_baseline_after": baseline_ece - calibrated_ece,
                "raw_score_separation": _score_separation(y_true, raw),
                "calibrated_score_separation": _score_separation(y_true, calibrated),
                "raw_safe_vs_baseline": raw_safe_vs_baseline,
                "calibrated_safe_vs_baseline": calibrated_safe_vs_baseline,
                "best_raw_threshold": raw_threshold["threshold"],
                "best_raw_mcc": raw_threshold["mcc"],
                "best_calibrated_threshold": calibrated_threshold["threshold"],
                "best_calibrated_mcc": calibrated_threshold["mcc"],
                "best_baseline_threshold": baseline_threshold["threshold"],
                "best_baseline_mcc": baseline_threshold["mcc"],
            }
        )
        for score_type, threshold_payload in [
            ("raw_candidate", raw_threshold),
            ("calibrated_candidate", calibrated_threshold),
            ("baseline", baseline_threshold),
        ]:
            threshold_rows.append({"cohort": cohort, "score_type": score_type, **threshold_payload})
        bin_rows.extend(_calibration_bins(cohort, "raw_candidate", y_true, raw))
        bin_rows.extend(_calibration_bins(cohort, "calibrated_candidate", y_true, calibrated))
        bin_rows.extend(_calibration_bins(cohort, "baseline", y_true, baseline_scores))

        metadata = _metadata_for_cohort(study_root, cohort)
        work["raw_score"] = raw
        work["calibrated_score"] = calibrated
        work["baseline_score"] = baseline_scores
        work["raw_pred"] = (work["raw_score"] >= 0.5).astype(int)
        calibrated_threshold_value = float(calibrated_threshold["threshold"])
        work["calibrated_pred"] = (work["calibrated_score"] >= calibrated_threshold_value).astype(int)
        work["raw_error"] = work["raw_pred"] != work["label"]
        work["calibrated_error"] = work["calibrated_pred"] != work["label"]
        error_frame = work[work["raw_error"] | work["calibrated_error"]].copy()
        if not metadata.empty:
            error_frame = error_frame.merge(metadata, on="variant", how="left")
        if not error_frame.empty:
            error_frame["cohort"] = cohort
            error_frame["error_type"] = np.where(error_frame["label"].eq(1), "false_negative", "false_positive")
            error_frame["calibration_effect"] = np.select(
                [
                    error_frame["raw_error"] & ~error_frame["calibrated_error"],
                    error_frame["raw_error"] & error_frame["calibrated_error"],
                    ~error_frame["raw_error"] & error_frame["calibrated_error"],
                ],
                ["rescued_by_calibration", "persistent_after_calibration", "introduced_by_calibration"],
                default="unchanged",
            )
            gnomad_missing = error_frame.get("feature_gnomad_af", pd.Series([np.nan] * len(error_frame))).isna()
            mave_missing = error_frame.get("feature_mave_score", pd.Series([np.nan] * len(error_frame))).isna()
            confidence = np.abs(error_frame["raw_score"].astype(float) - error_frame["label"].astype(float))
            error_frame["priority_score"] = (
                confidence
                + error_frame["calibrated_error"].astype(int) * 0.35
                + gnomad_missing.astype(int) * 0.1
                + mave_missing.astype(int) * 0.15
                + error_frame["cohort"].eq(focus_cohort).astype(int) * 0.2
            ).round(4)
            selected_columns = [
                "cohort",
                "variant",
                "gene",
                "label",
                "error_type",
                "calibration_effect",
                "raw_score",
                "calibrated_score",
                "baseline_score",
                "raw_pred",
                "calibrated_pred",
                "priority_score",
                "feature_gnomad_af",
                "feature_mave_score",
                "prime_diff",
                "prime_ratio",
                "prime_local_density_delta",
                "biochemical_severity_score",
                "functional_domain",
                "protein_interface",
                "review_status",
                "source",
            ]
            available_columns = [column for column in selected_columns if column in error_frame.columns]
            queue_rows.extend(error_frame[available_columns].to_dict(orient="records"))

    summary_df = pd.DataFrame(summary_rows).sort_values("cohort", kind="stable")
    threshold_df = pd.DataFrame(threshold_rows).sort_values(["cohort", "score_type"], kind="stable")
    bins_df = pd.DataFrame(bin_rows).sort_values(["cohort", "score_type", "bin_index"], kind="stable")
    queue_df = pd.DataFrame(queue_rows)
    if not queue_df.empty:
        queue_df = queue_df.sort_values(["priority_score", "cohort", "variant"], ascending=[False, True, True], kind="stable")

    raw_safe_rate = int(round(summary_df["raw_safe_vs_baseline"].mean() * 100)) if not summary_df.empty else 0
    calibrated_safe_rate = (
        int(round(summary_df["calibrated_safe_vs_baseline"].mean() * 100)) if not summary_df.empty else 0
    )
    rescue_gain = calibrated_safe_rate - raw_safe_rate
    persistent_focus_errors = 0
    if not queue_df.empty:
        persistent_focus_errors = int(
            len(
                queue_df[
                    queue_df.get("cohort", pd.Series(dtype=str)).astype(str).eq(focus_cohort)
                    & queue_df.get("calibration_effect", pd.Series(dtype=str)).astype(str).eq("persistent_after_calibration")
                ]
            )
        )
    assessment = {
        "generated_at": _now_utc(),
        "study_dir": _display_path(study_root),
        "candidate_experiment": candidate,
        "baseline_experiment": baseline,
        "focus_cohort": focus_cohort,
        "n_cohorts": int(len(summary_df)),
        "raw_calibration_safety_rate_percent": raw_safe_rate,
        "calibrated_safety_rate_percent": calibrated_safe_rate,
        "calibration_safety_gain_percent": rescue_gain,
        "mean_brier_improvement": _safe_float(summary_df["delta_brier_raw_to_calibrated"].mean()) if not summary_df.empty else float("nan"),
        "mean_ece_improvement": _safe_float(summary_df["delta_ece_raw_to_calibrated"].mean()) if not summary_df.empty else float("nan"),
        "persistent_focus_errors": persistent_focus_errors,
        "triage_queue_size": int(len(queue_df)),
        "status": "ready" if calibrated_safe_rate >= 85 else "partial" if calibrated_safe_rate >= 60 else "gap",
        "interpretation": (
            "diagnostic_calibration_rescue"
            if calibrated_safe_rate > raw_safe_rate
            else "calibration_needs_independent_holdout"
        ),
    }

    output_root = Path(output_dir).resolve() if output_dir else study_root / "calibration_rescue"
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "calibration_rescue_summary.csv"
    thresholds_path = output_root / "calibration_rescue_thresholds.csv"
    bins_path = output_root / "calibration_rescue_bins.csv"
    queue_path = output_root / "calibration_rescue_error_triage_queue.csv"
    manifest_path = output_root / "calibration_rescue_manifest.json"
    markdown_path = output_root / "calibration_rescue_report.md"
    html_path = output_root / "calibration_rescue_report.html"

    summary_df.to_csv(summary_path, index=False)
    threshold_df.to_csv(thresholds_path, index=False)
    bins_df.to_csv(bins_path, index=False)
    queue_df.to_csv(queue_path, index=False)

    lines = [
        "# Calibration rescue package",
        "",
        f"- Generated at: `{assessment['generated_at']}`",
        f"- Candidate: `{candidate}`",
        f"- Baseline: `{baseline}`",
        f"- Focus cohort: `{focus_cohort}`",
        f"- Raw calibration safety vs baseline: `{raw_safe_rate}%`",
        f"- Diagnostic calibrated safety vs baseline: `{calibrated_safe_rate}%`",
        f"- Safety gain: `{rescue_gain}%`",
        f"- Mean Brier improvement: `{_fmt(assessment['mean_brier_improvement'])}`",
        f"- Mean ECE improvement: `{_fmt(assessment['mean_ece_improvement'])}`",
        f"- Persistent focus-cohort errors after calibration: `{persistent_focus_errors}`",
        "",
        "## Scientific interpretation",
        "",
        "- This package is a diagnostic rescue analysis, not a replacement for blinded validation.",
        "- It estimates whether simple cohort-level recalibration can reduce calibration regressions while preserving the original discrimination evidence.",
        "- Deployment-grade calibration still requires a locked calibration cohort or prospective holdout.",
        "",
        "## Cohort rescue summary",
        "",
    ]
    for row in summary_df.to_dict(orient="records"):
        lines.append(
            f"- {row['cohort']}: raw ECE={_fmt(row['raw_ece'])}, calibrated ECE={_fmt(row['calibrated_ece'])}, "
            f"raw Brier={_fmt(row['raw_brier'])}, calibrated Brier={_fmt(row['calibrated_brier'])}, "
            f"best calibrated threshold={_fmt(row['best_calibrated_threshold'])}."
        )
    lines.extend(
        [
            "",
            "## Priority error triage",
            "",
            f"- Error queue size: `{len(queue_df)}`",
            f"- Persistent focus-cohort errors: `{persistent_focus_errors}`",
            "- Highest-priority persistent errors should be reviewed with AlphaMissense, MaveDB, gnomAD, structural context and functional assay feasibility.",
            "",
            "## Output files",
            "",
            f"- Summary: `{_display_path(summary_path)}`",
            f"- Thresholds: `{_display_path(thresholds_path)}`",
            f"- Calibration bins: `{_display_path(bins_path)}`",
            f"- Error triage queue: `{_display_path(queue_path)}`",
        ]
    )
    markdown = "\n".join(lines).strip() + "\n"
    markdown_path.write_text(markdown, encoding="utf-8")

    html_blocks = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if stripped.startswith("# "):
            html_blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            html_blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("- "):
            html_blocks.append("<ul>" + "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines()) + "</ul>")
        elif stripped:
            html_blocks.append(f"<p>{html.escape(stripped)}</p>")
    html_path.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Calibration Rescue</title>"
        "<style>body{font-family:Georgia,serif;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;color:#17202a;background:#f8fbff}"
        "h1{color:#102a43}h2{color:#2155d9}ul{background:white;border:1px solid #d9e2ec;border-radius:14px;padding:16px 24px}</style>"
        "</head><body>"
        + "".join(html_blocks)
        + "</body></html>",
        encoding="utf-8",
    )

    manifest = {
        **assessment,
        "summary_path": _display_path(summary_path),
        "thresholds_path": _display_path(thresholds_path),
        "bins_path": _display_path(bins_path),
        "error_triage_queue_path": _display_path(queue_path),
        "markdown_path": _display_path(markdown_path),
        "html_path": _display_path(html_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "calibration_rescue_assessment": assessment,
        "calibration_rescue_manifest_path": str(manifest_path),
        "calibration_rescue_report_markdown_path": str(markdown_path),
        "calibration_rescue_report_html_path": str(html_path),
        "calibration_rescue_summary_path": str(summary_path),
        "calibration_rescue_thresholds_path": str(thresholds_path),
        "calibration_rescue_bins_path": str(bins_path),
        "calibration_rescue_error_triage_queue_path": str(queue_path),
    }


def export_calibration_rescue_package(
    study_dir: str,
    output_dir: str | None = None,
    candidate_experiment: str | None = None,
    baseline_experiment: str | None = None,
    focus_cohort: str = "bridges_like_external_validation_brca1",
) -> dict:
    return build_calibration_rescue_package(
        study_dir=study_dir,
        output_dir=output_dir,
        candidate_experiment=candidate_experiment,
        baseline_experiment=baseline_experiment,
        focus_cohort=focus_cohort,
    )
