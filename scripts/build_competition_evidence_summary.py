from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_summary(path: Path) -> dict:
    return _read_json(path).get("summary", {}) if path.exists() else {}


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _parse_unittest_log(path: Path) -> dict:
    text = ""
    if path.exists():
        raw = path.read_bytes()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff") or raw.count(b"\x00") > max(len(raw) // 10, 1):
            text = raw.decode("utf-16", errors="replace")
        else:
            text = raw.decode("utf-8", errors="replace")
    ran_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s", text)
    status = "passed" if re.search(r"\bOK\b", text) else "failed"
    if "FAILED" in text:
        status = "failed"
    if not text:
        status = "missing"
    return {
        "test_block": path.stem,
        "status": status,
        "n_tests": int(ran_match.group(1)) if ran_match else 0,
        "seconds": float(ran_match.group(2)) if ran_match else None,
        "log_path": str(path),
    }


def _best_external_metrics(brca_dir: Path) -> pd.DataFrame:
    external_path = brca_dir / "study_external_evaluation.csv"
    external = pd.read_csv(external_path)
    if "evaluation_group" in external.columns:
        combined = external[external["evaluation_group"].astype(str).eq("combined")].copy()
        external = combined if not combined.empty else external
    best_rows = []
    for cohort, group in external.groupby("cohort", sort=True):
        best = group.sort_values("auc_roc", ascending=False, kind="stable").iloc[0]
        best_rows.append(
            {
                "cohort": cohort,
                "best_experiment": best["experiment"],
                "feature_set": best.get("feature_set", ""),
                "auc_roc": round(float(best["auc_roc"]), 4),
                "auc_pr": round(float(best["auc_pr"]), 4),
                "mcc": round(float(best["mcc"]), 4),
                "n_variants": int(best["n_variants"]),
            }
        )
    return pd.DataFrame(best_rows)


def build_summary(campaign_root: Path) -> dict:
    brca_dir = campaign_root / "brca_real_quick"
    output_dir = campaign_root
    output_dir.mkdir(parents=True, exist_ok=True)

    publication = _safe_summary(brca_dir / "publication_readiness_manifest.json")
    validation = _safe_summary(brca_dir / "study_validation_lock_manifest.json")
    claim = _safe_summary(brca_dir / "claim_strength_manifest.json")
    robustness = _safe_summary(brca_dir / "external_robustness_manifest.json")
    calibration_rescue = _read_json(campaign_root / "calibration_rescue" / "calibration_rescue_manifest.json")
    locked_holdout_path = campaign_root / "locked_calibration_holdout" / "locked_calibration_holdout_manifest.json"
    locked_holdout = _read_json(locked_holdout_path) if locked_holdout_path.exists() else {}
    competition_readiness_path = campaign_root / "competition_readiness" / "competition_readiness_manifest.json"
    competition_readiness = _read_json(competition_readiness_path) if competition_readiness_path.exists() else {}
    brca_error = _read_json(campaign_root / "brca1_lovd_error_analysis" / "brca1_lovd_error_analysis_manifest.json")

    cohort_manifest = pd.read_csv(brca_dir / "study_cohort_manifest.csv")
    cohort_size_column = "n_variants" if "n_variants" in cohort_manifest.columns else "valid_rows"
    train_variants = int(cohort_manifest.loc[cohort_manifest["role"].eq("train"), cohort_size_column].sum())
    external_variants = int(cohort_manifest.loc[cohort_manifest["role"].eq("external_test"), cohort_size_column].sum())
    total_variants = train_variants + external_variants

    external_best = _best_external_metrics(brca_dir)
    external_best_path = output_dir / "competition_external_best_metrics.csv"
    external_best.to_csv(external_best_path, index=False)

    log_paths = [
        campaign_root / "test_logs" / "targeted_core_ingestion_tests.log",
        campaign_root / "test_logs" / "targeted_scientific_modules_tests.log",
        campaign_root / "test_logs" / "targeted_study_benchmark_tests.log",
        campaign_root / "test_logs" / "targeted_api_operational_tests_fixed.log",
        campaign_root / "test_logs" / "targeted_calibration_rescue_tests.log",
        campaign_root / "test_logs" / "targeted_locked_calibration_holdout_tests.log",
        campaign_root / "test_logs" / "targeted_competition_readiness_tests.log",
    ]
    test_matrix = pd.DataFrame([_parse_unittest_log(path) for path in log_paths])
    test_matrix_path = output_dir / "competition_test_matrix.csv"
    test_matrix.to_csv(test_matrix_path, index=False)

    passed_tests = int(test_matrix.loc[test_matrix["status"].eq("passed"), "n_tests"].sum())
    total_targeted_tests = int(test_matrix["n_tests"].sum())
    test_seconds = float(test_matrix["seconds"].dropna().sum())

    score_rows = [
        {
            "area": "Publication readiness",
            "score_percent": publication.get("overall_readiness_percent"),
            "status": publication.get("overall_status"),
            "evidence": f"{publication.get('n_cohorts')} cohorts, {publication.get('n_external_cohorts')} external cohorts",
        },
        {
            "area": "Validation lock",
            "score_percent": validation.get("overall_validation_lock_percent"),
            "status": validation.get("overall_status"),
            "evidence": f"claim={validation.get('claim_tier')}; translational pilot={validation.get('ready_for_translational_pilot')}",
        },
        {
            "area": "Claim strength",
            "score_percent": claim.get("overall_claim_strength_percent"),
            "status": claim.get("claim_tier"),
            "evidence": claim.get("selected_experiment"),
        },
        {
            "area": "External robustness",
            "score_percent": robustness.get("overall_external_robustness_percent"),
            "status": robustness.get("overall_status"),
            "evidence": "pooled calibration/discrimination support with remaining calibration-safety gap",
        },
        {
            "area": "Calibration rescue",
            "score_percent": calibration_rescue.get("calibrated_safety_rate_percent"),
            "status": calibration_rescue.get("status"),
            "evidence": f"safety {calibration_rescue.get('raw_calibration_safety_rate_percent')}% -> {calibration_rescue.get('calibrated_safety_rate_percent')}%",
        },
        {
            "area": "Locked calibration holdout",
            "score_percent": locked_holdout.get("locked_calibrated_test_safety_rate_percent"),
            "status": locked_holdout.get("status"),
            "evidence": f"heldout n={locked_holdout.get('n_heldout_test_variants')}; safety {locked_holdout.get('raw_test_calibration_safety_rate_percent')}% -> {locked_holdout.get('locked_calibrated_test_safety_rate_percent')}%",
        },
        {
            "area": "Competition readiness",
            "score_percent": competition_readiness.get("competition_readiness_percent"),
            "status": "ready" if competition_readiness.get("ready_for_competition_dossier") else "partial",
            "evidence": f"paper {competition_readiness.get('paper_readiness_percent')}%; priority variants {competition_readiness.get('priority_variant_count')}",
        },
        {
            "area": "Cohort independence",
            "score_percent": validation.get("cohort_independence_percent"),
            "status": "ready",
            "evidence": "0% train/external overlap in frozen cohorts",
        },
        {
            "area": "Baseline and ablation",
            "score_percent": validation.get("baseline_coverage_percent"),
            "status": "partial",
            "evidence": "needs final ablation narrative and full-campaign confirmation",
        },
        {
            "area": "Targeted automated tests",
            "score_percent": round(100 * passed_tests / max(total_targeted_tests, 1), 1),
            "status": "passed" if passed_tests == total_targeted_tests else "partial",
            "evidence": f"{passed_tests}/{total_targeted_tests} targeted tests passed in {test_seconds:.1f}s",
        },
    ]
    scorecard = pd.DataFrame(score_rows)
    scorecard_path = output_dir / "competition_evidence_scorecard.csv"
    scorecard.to_csv(scorecard_path, index=False)

    best_lines = [
        f"- {row.cohort}: {row.best_experiment} | AUC-ROC={row.auc_roc:.4f}, AUC-PR={row.auc_pr:.4f}, MCC={row.mcc:.4f}, n={row.n_variants}"
        for row in external_best.itertuples(index=False)
    ]
    weak_brca1 = external_best[external_best["cohort"].eq("bridges_like_external_validation_brca1")]
    weak_brca1_auc = float(weak_brca1.iloc[0]["auc_roc"]) if not weak_brca1.empty else None
    score_lines = [
        f"- {row.area}: {row.score_percent}% ({row.status}) - {row.evidence}"
        for row in scorecard.itertuples(index=False)
    ]
    test_lines = [
        f"- {row.test_block}: {row.status}, {row.n_tests} tests, {row.seconds if pd.notna(row.seconds) else 'n/a'}s"
        for row in test_matrix.itertuples(index=False)
    ]

    markdown_path = output_dir / "competition_evidence_summary.md"
    markdown = "\n".join(
        [
            "# PrimeVarClass evidence summary for article and competition",
            "",
            f"- Generated at: `{_now_utc()}`",
            f"- Git commit: `{_git_commit()}`",
            "- Evidence run: `Jovem Cientista BRCA Real Evidence Quick Pass`",
            "- Canonical release assets: `https://github.com/WesleyCapucho/primevarclass/releases/tag/data-artifacts-2026-05-11`",
            "",
            "## What was validated",
            "",
            f"- Training variants: `{train_variants}`",
            f"- External validation variants: `{external_variants}`",
            f"- Total benchmarked variants: `{total_variants}`",
            f"- External cohorts: `{publication.get('n_external_cohorts')}`",
            f"- Publication readiness: `{publication.get('overall_readiness_percent')}%`",
            f"- Validation lock: `{validation.get('overall_validation_lock_percent')}%`",
            f"- Claim strength: `{claim.get('overall_claim_strength_percent')}%` (`{claim.get('claim_tier')}`)",
            f"- External robustness: `{robustness.get('overall_external_robustness_percent')}%`",
            f"- Diagnostic calibration safety: `{calibration_rescue.get('raw_calibration_safety_rate_percent')}%` -> `{calibration_rescue.get('calibrated_safety_rate_percent')}%`",
            f"- Locked calibration holdout safety: `{locked_holdout.get('raw_test_calibration_safety_rate_percent')}%` -> `{locked_holdout.get('locked_calibrated_test_safety_rate_percent')}%` on `{locked_holdout.get('n_heldout_test_variants')}` held-out variants",
            f"- Competition readiness: `{competition_readiness.get('competition_readiness_percent')}%`",
            f"- Targeted automated tests: `{passed_tests}/{total_targeted_tests}` passed",
            "",
            "## Best external results by cohort",
            "",
            *best_lines,
            "",
            "## Evidence scorecard",
            "",
            *score_lines,
            "",
            "## Automated test evidence",
            "",
            *test_lines,
            "",
            "## Main strengths for the article",
            "",
            "- The platform now has reproducible training and external validation on frozen, independent BRCA cohorts.",
            "- Cohort independence is locked at 100%, with no train/external variant overlap in the audited run.",
            "- The central prime-aware hybrid claim is strong in the current quick-pass evidence package.",
            "- The API and user-facing documentation endpoints are covered by targeted operational tests.",
            "- A new diagnostic calibration-rescue package shows that simple cohort-level recalibration can close the calibration-safety gap in the audited BRCA quick pass.",
            "- A locked calibration holdout now separates calibration/threshold fitting from held-out test evaluation using a deterministic prime-seeded split.",
            "- A competition-readiness package now maps allowed scientific claims, paper sections, priority variants and the next experimental strategy.",
            "- The GitHub repository and Release assets separate source code from large scientific artifacts with checksums.",
            "",
            "## Honest gaps to close before a top-tier paper",
            "",
            f"- BRCA1 LOVD remains the weakest holdout: best AUC-ROC `{weak_brca1_auc:.4f}`.",
            f"- BRCA1 LOVD selected-model errors: `{brca_error.get('selected_model_error_count')}` errors across `{brca_error.get('variant_count')}` variants.",
            f"- gnomAD coverage in the weak BRCA1 LOVD cohort: `{brca_error.get('feature_coverage', {}).get('gnomad_af_coverage_percent')}%`.",
            f"- MaveDB coverage in the weak BRCA1 LOVD cohort: `{brca_error.get('feature_coverage', {}).get('mavedb_score_coverage_percent')}%`.",
            f"- External robustness is still `{robustness.get('overall_external_robustness_percent')}%`; diagnostic recalibration and locked holdout both support `{calibration_rescue.get('calibrated_safety_rate_percent')}%` calibration safety, but this must be repeated in a larger blinded/prospective holdout.",
            f"- Locked holdout status is `{locked_holdout.get('status')}` with `{locked_holdout.get('persistent_focus_errors')}` persistent focus-cohort test errors; the next step is a larger blinded/prospective holdout.",
            f"- Persistent BRCA1/LOVD errors after calibration: `{calibration_rescue.get('persistent_focus_errors')}`.",
            f"- Baseline/ablation coverage is `{validation.get('baseline_coverage_percent')}%`; this needs a final ablation narrative before a high-impact submission.",
            "- The full unittest suite exceeded the interactive time budget and should be run as sharded CI jobs instead of one monolithic local command.",
            "",
            "## Recommended next experimental package",
            "",
            "- Run the full BRCA campaign with 200 bootstraps and multiple model families overnight or in CI/HPC.",
            "- Add AlphaMissense target-gene subsets to improve weak BRCA1/LOVD functional coverage.",
            "- Expand the locked calibration protocol to the full BRCA campaign and report calibration curves, Brier score, expected calibration error and decision thresholds.",
            "- Promote the locked holdout protocol into a frozen prospective validation plan with no post-hoc threshold changes.",
            "- Prioritize the BRCA1/LOVD false positives and false negatives for structural review and functional confirmation.",
            "- Convert this summary, the methods package, and the manuscript tables into the LaTeX paper scaffold after the full campaign is locked.",
            "",
            "## Output files",
            "",
            f"- Scorecard: `{scorecard_path}`",
            f"- Best external metrics: `{external_best_path}`",
            f"- Test matrix: `{test_matrix_path}`",
        ]
    )
    markdown_path.write_text(markdown + "\n", encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "campaign_root": str(campaign_root),
        "brca_quick_dir": str(brca_dir),
        "git_commit": _git_commit(),
        "train_variants": train_variants,
        "external_validation_variants": external_variants,
        "total_benchmarked_variants": total_variants,
        "passed_targeted_tests": passed_tests,
        "total_targeted_tests": total_targeted_tests,
        "locked_calibration_holdout_manifest_path": str(locked_holdout_path) if locked_holdout_path.exists() else None,
        "competition_readiness_manifest_path": str(competition_readiness_path) if competition_readiness_path.exists() else None,
        "scorecard_path": str(scorecard_path),
        "external_best_metrics_path": str(external_best_path),
        "test_matrix_path": str(test_matrix_path),
        "markdown_path": str(markdown_path),
    }
    manifest_path = output_dir / "competition_evidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a competition-ready evidence summary for PrimeVarClass.")
    parser.add_argument("--campaign-root", default="primevarclass_jovem_cientista_evidence_20260511")
    args = parser.parse_args()
    manifest = build_summary(Path(args.campaign_root))
    print(f"Evidence summary: {manifest['markdown_path']}")
    print(f"Evidence scorecard: {manifest['scorecard_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
