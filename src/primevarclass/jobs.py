from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from .audit import PrimeVarClassAuditLogger


JOB_STATUS_TERMINAL = {"completed", "failed", "interrupted"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _result_highlights(result: Any) -> List[str]:
    if not isinstance(result, dict):
        return []
    highlights = []
    for key, label in [
        ("output_dir", "Output directory"),
        ("summary_report_path", "Summary report"),
        ("study_summary_report_path", "Study summary"),
        ("public_study_run_report_markdown_path", "Public study run report"),
        ("public_study_run_manifest_path", "Public study run manifest"),
        ("candidate_public_run_report_markdown_path", "Candidate public study run report"),
        ("candidate_public_run_manifest_path", "Candidate public study run manifest"),
        ("cohort_independence_report_markdown_path", "Cohort independence audit (Markdown)"),
        ("cohort_independence_report_html_path", "Cohort independence audit (HTML)"),
        ("cohort_independence_manifest_path", "Cohort independence audit manifest"),
        ("study_cohort_freeze_markdown_path", "Study cohort freeze (Markdown)"),
        ("study_cohort_freeze_html_path", "Study cohort freeze (HTML)"),
        ("study_cohort_freeze_manifest_path", "Study cohort freeze manifest"),
        ("study_real_data_handoff_markdown_path", "Real-data handoff (Markdown)"),
        ("study_real_data_handoff_html_path", "Real-data handoff (HTML)"),
        ("study_real_data_handoff_manifest_path", "Real-data handoff manifest"),
        ("study_real_data_handoff_autofill_markdown_path", "Real-data handoff autofill (Markdown)"),
        ("study_real_data_handoff_autofill_html_path", "Real-data handoff autofill (HTML)"),
        ("study_real_data_handoff_autofill_manifest_path", "Real-data handoff autofill manifest"),
        ("study_real_data_handoff_reconciliation_markdown_path", "Real-data handoff reconciliation (Markdown)"),
        ("study_real_data_handoff_reconciliation_html_path", "Real-data handoff reconciliation (HTML)"),
        ("study_real_data_handoff_reconciliation_manifest_path", "Real-data handoff reconciliation manifest"),
        ("study_real_data_handoff_application_markdown_path", "Real-data handoff application (Markdown)"),
        ("study_real_data_handoff_application_html_path", "Real-data handoff application (HTML)"),
        ("study_real_data_handoff_application_manifest_path", "Real-data handoff application manifest"),
        ("study_real_data_candidate_promotion_markdown_path", "Candidate promotion package (Markdown)"),
        ("study_real_data_candidate_promotion_html_path", "Candidate promotion package (HTML)"),
        ("study_real_data_candidate_promotion_manifest_path", "Candidate promotion package manifest"),
        ("scientific_dossier_markdown_path", "Scientific dossier (Markdown)"),
        ("scientific_dossier_html_path", "Scientific dossier (HTML)"),
        ("claim_strength_report_markdown_path", "Claim strength (Markdown)"),
        ("claim_strength_report_html_path", "Claim strength (HTML)"),
        ("claim_strength_manifest_path", "Claim strength manifest"),
        ("publication_readiness_report_markdown_path", "Publication readiness (Markdown)"),
        ("publication_readiness_report_html_path", "Publication readiness (HTML)"),
        ("publication_readiness_manifest_path", "Publication readiness manifest"),
        ("comparative_evidence_report_markdown_path", "Comparative evidence (Markdown)"),
        ("comparative_evidence_report_html_path", "Comparative evidence (HTML)"),
        ("comparative_evidence_manifest_path", "Comparative evidence manifest"),
        ("baseline_coverage_report_markdown_path", "Baseline coverage (Markdown)"),
        ("baseline_coverage_report_html_path", "Baseline coverage (HTML)"),
        ("baseline_coverage_manifest_path", "Baseline coverage manifest"),
        ("methods_package_markdown_path", "Methods package (Markdown)"),
        ("methods_package_html_path", "Methods package (HTML)"),
        ("methods_package_manifest_path", "Methods package manifest"),
        ("manuscript_package_markdown_path", "Manuscript package (Markdown)"),
        ("manuscript_package_html_path", "Manuscript package (HTML)"),
        ("manuscript_package_manifest_path", "Manuscript package manifest"),
        ("study_validation_lock_markdown_path", "Study validation lock (Markdown)"),
        ("study_validation_lock_html_path", "Study validation lock (HTML)"),
        ("study_validation_lock_manifest_path", "Study validation lock manifest"),
        ("study_execution_board_markdown_path", "Study execution board (Markdown)"),
        ("study_execution_board_html_path", "Study execution board (HTML)"),
        ("study_execution_board_manifest_path", "Study execution board manifest"),
        ("translational_pilot_package_markdown_path", "Translational pilot package (Markdown)"),
        ("translational_pilot_package_html_path", "Translational pilot package (HTML)"),
        ("translational_pilot_package_manifest_path", "Translational pilot package manifest"),
        ("translational_impact_package_markdown_path", "Translational impact package (Markdown)"),
        ("translational_impact_package_html_path", "Translational impact package (HTML)"),
        ("translational_impact_package_manifest_path", "Translational impact package manifest"),
        ("platform_completion_markdown_path", "Platform completion package (Markdown)"),
        ("platform_completion_html_path", "Platform completion package (HTML)"),
        ("platform_completion_manifest_path", "Platform completion package manifest"),
        ("final_mile_package_markdown_path", "Final mile package (Markdown)"),
        ("final_mile_package_html_path", "Final mile package (HTML)"),
        ("final_mile_package_manifest_path", "Final mile package manifest"),
        ("training_metrics_path", "Training metrics"),
        ("external_evaluation_path", "External evaluation"),
        ("model_registry_path", "Model registry"),
        ("metrics_path", "Metrics table"),
        ("source_ingestion_report_path", "Source ingestion report"),
        ("data_release_manifest_path", "Data release manifest"),
        ("study_release_manifest_path", "Study release manifest"),
        ("cohort_manifest_path", "Cohort manifest"),
        ("public_source_catalog_report_json", "Public source catalog report (JSON)"),
        ("public_source_catalog_report_markdown", "Public source catalog report (Markdown)"),
        ("public_source_sync_plan_json", "Public source sync plan (JSON)"),
        ("public_source_sync_plan_markdown", "Public source sync plan (Markdown)"),
        ("gene_expansion_manifest_path", "Gene expansion manifest"),
        ("gene_expansion_report_markdown_path", "Gene expansion report (Markdown)"),
        ("gene_expansion_report_html_path", "Gene expansion report (HTML)"),
        ("gene_expansion_candidates_path", "Gene expansion candidates"),
        ("gene_expansion_panel_template_path", "Gene expansion panel template"),
        ("biological_discovery_manifest_path", "Biological discovery manifest"),
        ("biological_discovery_report_markdown_path", "Biological discovery report (Markdown)"),
        ("biological_discovery_report_html_path", "Biological discovery report (HTML)"),
        ("biological_discovery_hotspots_path", "Biological discovery hotspots"),
        ("biological_discovery_hypothesis_variants_path", "Biological discovery hypotheses"),
        ("multigene_rollout_manifest_path", "Multigene rollout manifest"),
        ("multigene_rollout_markdown_path", "Multigene rollout report (Markdown)"),
        ("multigene_rollout_html_path", "Multigene rollout report (HTML)"),
        ("multigene_rollout_csv_path", "Multigene rollout table"),
        ("multigene_study_factory_manifest_path", "Multigene study factory manifest"),
        ("multigene_study_factory_markdown_path", "Multigene study factory report (Markdown)"),
        ("multigene_study_scaffold_index_path", "Multigene study scaffold index"),
        ("multigene_study_factory_tasks_path", "Multigene study factory tasks"),
    ]:
        value = result.get(key)
        if value:
            highlights.append(f"- {label}: {value}")
    return highlights


def default_job_root() -> Path:
    configured = os.environ.get("PRIMEVARCLASS_JOB_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / "primevarclass_job_history").resolve()


class PrimeVarClassJobManager:
    def __init__(self, root_dir: str | Path | None = None, audit_logger: PrimeVarClassAuditLogger | None = None):
        self.root_dir = Path(root_dir or default_job_root()).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._jobs: Dict[str, dict] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self.audit_logger = audit_logger
        self._load_existing_jobs()

    def _job_dir(self, job_id: str) -> Path:
        return self.root_dir / job_id

    def _job_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def _job_report_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job_report.md"

    def _write_job_report_unlocked(self, record: dict) -> None:
        lines = [
            f"# PrimeVarClass Job Report - {record['job_id']}",
            "",
            f"- Type: {record.get('job_type')}",
            f"- Status: {record.get('status')}",
            f"- Created at: {record.get('created_at')}",
            f"- Started at: {record.get('started_at')}",
            f"- Finished at: {record.get('finished_at')}",
        ]
        submitted_by = record.get("submitted_by") or {}
        submitted_for_team = record.get("submitted_for_team") or {}
        if submitted_by:
            lines.extend(
                [
                    "",
                    "## Submitted By",
                    "",
                    f"- Profile: {submitted_by.get('profile_id')}",
                    f"- Name: {submitted_by.get('display_name')}",
                    f"- Role: {submitted_by.get('role')}",
                    f"- Institution: {submitted_by.get('institution')}",
                ]
            )
        if submitted_for_team:
            lines.extend(
                [
                    "",
                    "## Team Context",
                    "",
                    f"- Team: {submitted_for_team.get('display_name')}",
                    f"- Team ID: {submitted_for_team.get('team_id')}",
                    f"- Institution: {submitted_for_team.get('institution')}",
                    f"- Member role: {submitted_for_team.get('member_role')}",
                ]
            )
        highlights = _result_highlights(record.get("result"))
        if highlights:
            lines.extend(["", "## Result Highlights", ""])
            lines.extend(highlights)
        if record.get("error"):
            lines.extend(["", "## Error", "", str(record.get("error"))])
        lines.extend(["", "## Payload", "", "```json", json.dumps(_to_jsonable(record.get("payload", {})), indent=2, ensure_ascii=False), "```"])
        if record.get("result") is not None:
            lines.extend(["", "## Result", "", "```json", json.dumps(_to_jsonable(record.get("result")), indent=2, ensure_ascii=False), "```"])
        self._job_report_file(str(record["job_id"])).write_text("\n".join(lines), encoding="utf-8")

    def _write_job_unlocked(self, record: dict) -> None:
        job_dir = self._job_dir(str(record["job_id"]))
        job_dir.mkdir(parents=True, exist_ok=True)
        record["job_dir"] = str(job_dir.resolve())
        record["job_file_path"] = str(self._job_file(str(record["job_id"])).resolve())
        record["report_path"] = str(self._job_report_file(str(record["job_id"])).resolve())
        self._job_file(str(record["job_id"])).write_text(
            json.dumps(_to_jsonable(record), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._write_job_report_unlocked(record)

    def _load_existing_jobs(self) -> None:
        for job_file in sorted(self.root_dir.glob("*/job.json")):
            try:
                record = json.loads(job_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            if record.get("status") in {"queued", "running"}:
                record["status"] = "interrupted"
                record["finished_at"] = _now_utc()
                record["error"] = "Processo anterior interrompido antes da conclusao."
                job_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
                if self.audit_logger is not None:
                    self.audit_logger.log_event(
                        event_type="job.interrupted_on_startup",
                        status="warning",
                        actor="system",
                        job_id=str(record.get("job_id")),
                        metadata={"job_type": record.get("job_type")},
                    )
            self._write_job_unlocked(record)
            self._jobs[str(record["job_id"])] = record

    def create_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        submitted_by: Dict[str, Any] | None = None,
        submitted_for_team: Dict[str, Any] | None = None,
    ) -> dict:
        job_id = f"{job_type}-{uuid.uuid4().hex[:12]}"
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "queued",
            "created_at": _now_utc(),
            "started_at": None,
            "finished_at": None,
            "payload": _to_jsonable(payload),
            "submitted_by": _to_jsonable(submitted_by or {}),
            "submitted_for_team": _to_jsonable(submitted_for_team or {}),
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = record
            self._write_job_unlocked(record)
        if self.audit_logger is not None:
            self.audit_logger.log_event(
                event_type="job.created",
                status="queued",
                actor="system",
                job_id=job_id,
                metadata={
                    "job_type": job_type,
                    "submitted_by_profile_id": record["submitted_by"].get("profile_id"),
                    "submitted_for_team_id": record["submitted_for_team"].get("team_id"),
                },
            )
        return dict(record)

    def _update_job(self, job_id: str, **fields: Any) -> dict:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job nao encontrado: {job_id}")
            self._jobs[job_id].update(_to_jsonable(fields))
            self._write_job_unlocked(self._jobs[job_id])
            updated = dict(self._jobs[job_id])
        if self.audit_logger is not None and "status" in fields:
            self.audit_logger.log_event(
                event_type="job.status_changed",
                status=str(updated.get("status")),
                actor="system",
                job_id=job_id,
                metadata={"job_type": updated.get("job_type")},
            )
        return updated

    def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        runner: Callable[[Dict[str, Any]], Dict[str, Any]],
        submitted_by: Dict[str, Any] | None = None,
        submitted_for_team: Dict[str, Any] | None = None,
    ) -> dict:
        record = self.create_job(
            job_type=job_type,
            payload=payload,
            submitted_by=submitted_by,
            submitted_for_team=submitted_for_team,
        )
        job_id = str(record["job_id"])

        def _target() -> None:
            self._update_job(job_id, status="running", started_at=_now_utc())
            try:
                result = runner(payload)
                self._update_job(job_id, status="completed", finished_at=_now_utc(), result=result)
            except Exception as exc:
                self._update_job(job_id, status="failed", finished_at=_now_utc(), error=str(exc))

        thread = threading.Thread(target=_target, name=f"primevarclass-{job_id}", daemon=True)
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return record

    def get_job(self, job_id: str) -> dict:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job nao encontrado: {job_id}")
            return dict(self._jobs[job_id])

    def list_jobs(self, limit: int = 50) -> List[dict]:
        with self._lock:
            records = [dict(record) for record in self._jobs.values()]
        records.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return records[:limit]
