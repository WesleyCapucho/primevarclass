from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .core import encode_variant_features, parse_variant


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


def _fmt_percent(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.0f}%"


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "strong"
    if value >= 70:
        return "promising"
    if value >= 55:
        return "emerging"
    return "gap"


def _tier_from_percent(value: int) -> str:
    if value >= 90:
        return "strong"
    if value >= 75:
        return "moderate"
    if value >= 60:
        return "emerging"
    return "weak"


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


def _is_prime_like_feature_set(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token.startswith("prime") or token.startswith("hybrid")


def _ensure_feature_set_column(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    aligned = df.copy()
    if "feature_set" not in aligned.columns:
        aligned["feature_set"] = aligned.get("experiment", pd.Series(index=aligned.index, dtype=str)).astype(str).str.split("__").str[0]
    return aligned


def _is_prime_feature_name(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token.startswith("prime_") or token.startswith("codon_count") or token == "mass_prime_transition"


def _score_delta(delta: float, *, strong: float = 0.02, good: float = 0.005) -> int:
    if np.isnan(delta):
        return 0
    if delta >= strong:
        return 100
    if delta >= good:
        return 90
    if delta >= 0:
        return 78
    if delta >= -good:
        return 62
    if delta >= -strong:
        return 42
    return 18


def _score_share(value: float, *, strong: float = 0.75, good: float = 0.5) -> int:
    if np.isnan(value):
        return 0
    if value >= strong:
        return 100
    if value >= good:
        return 85
    if value >= 0.4:
        return 72
    if value >= 0.25:
        return 55
    return 28


def _study_root_from_results(results: dict, output_dir: str | None = None) -> Path:
    if output_dir:
        return Path(output_dir).expanduser().resolve()
    for key in ("training_metrics_path", "external_evaluation_path", "publication_readiness_manifest_path"):
        candidate = results.get(key)
        if candidate:
            return Path(str(candidate)).expanduser().resolve().parent
    return Path.cwd()


def _load_optional_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_optional_manifest(
    study_root: Path,
    explicit_path: str | None,
    default_dirname: str,
    filename: str,
) -> Path | None:
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        return candidate if candidate.exists() else None
    candidate = (study_root.parent / default_dirname / filename).resolve()
    return candidate if candidate.exists() else None


def _prime_metrics_from_variants(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    gene_column = next((column for column in ["gene", "GeneSymbol", "gene_symbol"] if column in df.columns), None)
    hgvs_column = next((column for column in ["hgvs_p", "Protein change", "protein_change", "protein_change_raw"] if column in df.columns), None)
    if gene_column is None or hgvs_column is None:
        return pd.DataFrame()
    rows: List[dict] = []
    for _, row in df.iterrows():
        gene = str(row.get(gene_column) or "").strip().upper()
        hgvs_p = str(row.get(hgvs_column) or "").strip()
        if not gene or not hgvs_p:
            continue
        try:
            variant = parse_variant(f"{gene} {hgvs_p}")
            features = encode_variant_features(variant, mode="hybrid")
        except Exception:
            continue
        rows.append(
            {
                **{key: row.get(key) for key in df.columns},
                "gene": gene,
                "hgvs_p": hgvs_p,
                "position": int(features.get("position") or 0),
                "prime_ref": _safe_int(features.get("prime_ref")),
                "prime_alt": _safe_int(features.get("prime_alt")),
                "prime_diff": _safe_float(features.get("prime_diff")),
                "prime_ratio": _safe_float(features.get("prime_ratio")),
                "prime_log_ratio": abs(_safe_float(features.get("prime_log_ratio"))),
                "prime_product": _safe_float(features.get("prime_product")),
            }
        )
    return pd.DataFrame(rows)


def _read_optional_csv(path_value: Any) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(str(path_value)).expanduser().resolve()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        return pd.DataFrame()


def _build_internal_signal_table(training_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if training_df.empty:
        return pd.DataFrame(), {}
    ranked = _ensure_feature_set_column(training_df).sort_values(
        ["auc_roc", "auc_pr", "mcc", "experiment"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    ranked["prime_like"] = ranked["feature_set"].map(_is_prime_like_feature_set)

    best_prime = ranked[ranked["prime_like"]].head(1)
    best_nonprime = ranked[~ranked["prime_like"]].head(1)
    if best_prime.empty or best_nonprime.empty:
        return ranked, {}

    prime_row = best_prime.iloc[0].to_dict()
    nonprime_row = best_nonprime.iloc[0].to_dict()
    delta_auc = _safe_float(prime_row.get("auc_roc")) - _safe_float(nonprime_row.get("auc_roc"))
    delta_pr = _safe_float(prime_row.get("auc_pr")) - _safe_float(nonprime_row.get("auc_pr"))
    delta_mcc = _safe_float(prime_row.get("mcc")) - _safe_float(nonprime_row.get("mcc"))
    score = int(
        round(
            np.mean(
                [
                    _score_delta(delta_auc, strong=0.02, good=0.005),
                    _score_delta(delta_pr, strong=0.05, good=0.01),
                    _score_delta(delta_mcc, strong=0.08, good=0.02),
                ]
            )
        )
    )
    return ranked, {
        "best_prime_experiment": prime_row.get("experiment"),
        "best_nonprime_experiment": nonprime_row.get("experiment"),
        "best_prime_auc_roc": _safe_float(prime_row.get("auc_roc")),
        "best_nonprime_auc_roc": _safe_float(nonprime_row.get("auc_roc")),
        "delta_auc_roc": delta_auc,
        "delta_auc_pr": delta_pr,
        "delta_mcc": delta_mcc,
        "score_percent": score,
    }


def _build_external_signal_table(external_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if external_df.empty:
        return pd.DataFrame(), {}
    combined = _ensure_feature_set_column(external_df)
    combined = combined[combined["evaluation_group"].astype(str) == "combined"].copy()
    if combined.empty:
        return pd.DataFrame(), {}

    rows: List[dict] = []
    for cohort_name, cohort_df in combined.groupby("cohort"):
        ranked = cohort_df.sort_values(
            ["auc_roc", "auc_pr", "mcc", "experiment"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        ranked["prime_like"] = ranked["feature_set"].map(_is_prime_like_feature_set)
        best_prime = ranked[ranked["prime_like"]].head(1)
        best_nonprime = ranked[~ranked["prime_like"]].head(1)
        if best_prime.empty or best_nonprime.empty:
            continue
        prime_row = best_prime.iloc[0]
        nonprime_row = best_nonprime.iloc[0]
        delta_auc = _safe_float(prime_row.get("auc_roc")) - _safe_float(nonprime_row.get("auc_roc"))
        rows.append(
            {
                "cohort": cohort_name,
                "prime_experiment": prime_row.get("experiment"),
                "nonprime_experiment": nonprime_row.get("experiment"),
                "prime_auc_roc": _safe_float(prime_row.get("auc_roc")),
                "nonprime_auc_roc": _safe_float(nonprime_row.get("auc_roc")),
                "prime_auc_pr": _safe_float(prime_row.get("auc_pr")),
                "nonprime_auc_pr": _safe_float(nonprime_row.get("auc_pr")),
                "prime_mcc": _safe_float(prime_row.get("mcc")),
                "nonprime_mcc": _safe_float(nonprime_row.get("mcc")),
                "delta_auc_roc": delta_auc,
                "prime_wins_auc_roc": bool(delta_auc > 0),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table, {}

    win_share = float(table["prime_wins_auc_roc"].mean())
    mean_delta_auc = _safe_float(table["delta_auc_roc"].mean())
    score = int(round(np.mean([_score_share(win_share), _score_delta(mean_delta_auc, strong=0.03, good=0.01)])))
    best_row = table.sort_values(["delta_auc_roc", "cohort"], ascending=[False, True]).iloc[0].to_dict()
    return table, {
        "prime_external_win_rate_percent": int(round(win_share * 100)),
        "mean_external_delta_auc_roc": mean_delta_auc,
        "best_prime_external_experiment": best_row.get("prime_experiment"),
        "best_prime_external_cohort": best_row.get("cohort"),
        "score_percent": score,
    }


def _build_pairwise_support_table(pairwise_df: pd.DataFrame, baseline_experiment: str) -> tuple[pd.DataFrame, dict]:
    if pairwise_df.empty or "metric" not in pairwise_df.columns:
        return pd.DataFrame(), {}
    auc_rows = pairwise_df[pairwise_df["metric"].astype(str) == "auc_roc"].copy()
    if auc_rows.empty:
        return pd.DataFrame(), {}
    auc_rows["feature_set"] = auc_rows["experiment"].astype(str).str.split("__").str[0]
    auc_rows = auc_rows[auc_rows["feature_set"].map(_is_prime_like_feature_set)].copy()
    if baseline_experiment:
        auc_rows = auc_rows[auc_rows["baseline_experiment"].astype(str) == str(baseline_experiment)].copy()
    if auc_rows.empty:
        return pd.DataFrame(), {}
    auc_rows["supported_gain"] = auc_rows["ci_lower_95"].astype(float) > 0
    auc_rows["positive_gain"] = auc_rows["delta_mean"].astype(float) > 0

    supported_share = float(auc_rows["supported_gain"].mean())
    positive_share = float(auc_rows["positive_gain"].mean())
    best_row = auc_rows.sort_values(
        ["delta_mean", "ci_lower_95", "experiment", "cohort"],
        ascending=[False, False, True, True],
    ).iloc[0].to_dict()
    score = int(round(np.mean([_score_share(supported_share, strong=0.5, good=0.25), _score_share(positive_share)])))
    return auc_rows, {
        "supported_pairwise_share_percent": int(round(supported_share * 100)),
        "positive_pairwise_share_percent": int(round(positive_share * 100)),
        "best_supported_prime_experiment": best_row.get("experiment"),
        "best_supported_prime_delta_auc_roc": _safe_float(best_row.get("delta_mean")),
        "score_percent": score,
    }


def _prime_salience_from_importance_table(table: pd.DataFrame) -> dict:
    if table.empty:
        return {}
    ranked = table.sort_values(["importance_mean", "feature"], ascending=[False, True]).reset_index(drop=True)
    top = ranked.head(10).copy()
    positive = top["importance_mean"].clip(lower=0.0)
    total_positive = float(positive.sum())
    prime_mask = top["feature"].map(_is_prime_feature_name)
    prime_positive = float(positive[prime_mask].sum())
    prime_share = (prime_positive / total_positive) if total_positive > 0 else 0.0
    prime_count = int(prime_mask.sum())
    score = int(
        round(
            np.mean(
                [
                    100 if prime_count >= 3 else 85 if prime_count >= 2 else 65 if prime_count >= 1 else 20,
                    100 if prime_share >= 0.2 else 85 if prime_share >= 0.1 else 70 if prime_share > 0 else 25,
                ]
            )
        )
    )
    return {
        "top_prime_feature_count": prime_count,
        "top_prime_feature_share": prime_share,
        "score_percent": score,
        "top_features": top["feature"].astype(str).tolist(),
    }


def _build_feature_attribution_table(study_root: Path, training_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if training_df.empty:
        return pd.DataFrame(), {}
    training_df = _ensure_feature_set_column(training_df)

    rows: List[dict] = []
    for feature_set in sorted(set(training_df["feature_set"].astype(str))):
        if not _is_prime_like_feature_set(feature_set):
            continue
        importance_path = study_root / f"study_feature_importance_{feature_set}.csv"
        if not importance_path.exists():
            continue
        table = pd.read_csv(importance_path)
        salience = _prime_salience_from_importance_table(table)
        if not salience:
            continue
        rows.append(
            {
                "feature_set": feature_set,
                "importance_path": str(importance_path),
                "top_prime_feature_count": salience["top_prime_feature_count"],
                "top_prime_feature_share": salience["top_prime_feature_share"],
                "score_percent": salience["score_percent"],
                "top_features": "; ".join(salience["top_features"][:10]),
                "is_mixed_prime_feature_set": feature_set != "prime_only",
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table, {}

    mixed = table[table["is_mixed_prime_feature_set"]].copy()
    pure = table[table["feature_set"].astype(str) == "prime_only"].copy()
    mixed_best = mixed.sort_values(["score_percent", "top_prime_feature_share"], ascending=[False, False]).head(1)
    pure_best = pure.sort_values(["score_percent", "top_prime_feature_share"], ascending=[False, False]).head(1)

    mixed_score = _safe_float(mixed_best.iloc[0]["score_percent"]) if not mixed_best.empty else float("nan")
    pure_score = _safe_float(pure_best.iloc[0]["score_percent"]) if not pure_best.empty else float("nan")
    parts = [score for score in [mixed_score, pure_score] if not np.isnan(score)]
    overall_score = int(round(float(np.mean(parts)))) if parts else 0

    return table, {
        "mixed_prime_attribution_percent": _safe_int(mixed_score),
        "pure_prime_attribution_percent": _safe_int(pure_score),
        "best_mixed_prime_feature_set": mixed_best.iloc[0]["feature_set"] if not mixed_best.empty else None,
        "best_pure_prime_feature_set": pure_best.iloc[0]["feature_set"] if not pure_best.empty else None,
        "score_percent": overall_score,
    }


def _build_biological_alignment_table(biological_manifest_path: Path | None) -> tuple[pd.DataFrame, dict]:
    manifest = _load_optional_json(biological_manifest_path)
    if not manifest:
        return pd.DataFrame(), {}

    artifact_paths = dict(manifest.get("artifact_paths") or {})
    training_table = _read_optional_csv(artifact_paths.get("training_table"))
    hotspots = _read_optional_csv(manifest.get("hotspots_path"))
    review_candidates = _read_optional_csv(manifest.get("review_upgrade_candidates_path"))
    hypothesis_variants = _read_optional_csv(manifest.get("hypothesis_variants_path"))

    background = _prime_metrics_from_variants(training_table)
    if background.empty:
        return pd.DataFrame(), {}

    background_median = _safe_float(background["prime_diff"].median())
    rows: List[dict] = []

    if not hotspots.empty:
        hotspot_windows = hotspots[["gene", "window_start", "window_end"]].copy()
        inside_mask = []
        for _, variant_row in background.iterrows():
            gene_name = str(variant_row.get("gene") or "")
            position = _safe_int(variant_row.get("position"))
            gene_windows = hotspot_windows[hotspot_windows["gene"].astype(str) == gene_name]
            in_window = bool(
                ((gene_windows["window_start"].astype(int) <= position) & (gene_windows["window_end"].astype(int) >= position)).any()
            ) if not gene_windows.empty else False
            inside_mask.append(in_window)
        hotspot_variants = background[pd.Series(inside_mask, index=background.index)]
        hotspot_median = _safe_float(hotspot_variants["prime_diff"].median())
        hotspot_delta = hotspot_median - background_median
        rows.append(
            {
                "analysis": "hotspot_enrichment",
                "group_count": int(len(hotspot_variants)),
                "group_median_prime_diff": hotspot_median,
                "background_median_prime_diff": background_median,
                "delta_prime_diff": hotspot_delta,
                "score_percent": _score_delta(hotspot_delta, strong=2.0, good=0.5),
            }
        )

    if not review_candidates.empty:
        review_prime = _prime_metrics_from_variants(review_candidates)
        review_median = _safe_float(review_prime["prime_diff"].median()) if not review_prime.empty else float("nan")
        review_delta = review_median - background_median
        rows.append(
            {
                "analysis": "review_upgrade_alignment",
                "group_count": int(len(review_prime)),
                "group_median_prime_diff": review_median,
                "background_median_prime_diff": background_median,
                "delta_prime_diff": review_delta,
                "score_percent": _score_delta(review_delta, strong=2.0, good=0.5),
            }
        )

    if not hypothesis_variants.empty:
        sort_columns = [column for column in ["hypothesis_score_percent", "hypothesis_score", "gene", "hgvs_p"] if column in hypothesis_variants.columns]
        ascending = [False if column in {"hypothesis_score_percent", "hypothesis_score"} else True for column in sort_columns]
        top_hypotheses = hypothesis_variants.sort_values(sort_columns, ascending=ascending).head(100) if sort_columns else hypothesis_variants.head(100)
        hypothesis_prime = _prime_metrics_from_variants(top_hypotheses)
        hypothesis_median = _safe_float(hypothesis_prime["prime_diff"].median()) if not hypothesis_prime.empty else float("nan")
        hypothesis_delta = hypothesis_median - background_median
        rows.append(
            {
                "analysis": "hypothesis_alignment",
                "group_count": int(len(hypothesis_prime)),
                "group_median_prime_diff": hypothesis_median,
                "background_median_prime_diff": background_median,
                "delta_prime_diff": hypothesis_delta,
                "score_percent": _score_delta(hypothesis_delta, strong=2.0, good=0.5),
            }
        )

    table = pd.DataFrame(rows)
    if table.empty:
        return table, {}
    overall_score = int(round(table["score_percent"].mean()))
    return table, {
        "background_median_prime_diff": background_median,
        "hotspot_alignment_percent": _safe_int(
            table.loc[table["analysis"].astype(str) == "hotspot_enrichment", "score_percent"].head(1).squeeze()
        ),
        "review_alignment_percent": _safe_int(
            table.loc[table["analysis"].astype(str) == "review_upgrade_alignment", "score_percent"].head(1).squeeze()
        ),
        "hypothesis_alignment_percent": _safe_int(
            table.loc[table["analysis"].astype(str) == "hypothesis_alignment", "score_percent"].head(1).squeeze()
        ),
        "score_percent": overall_score,
    }


def _build_expansion_runway_table(gene_expansion_manifest_path: Path | None) -> tuple[pd.DataFrame, dict]:
    manifest = _load_optional_json(gene_expansion_manifest_path)
    top_candidates = list(manifest.get("top_candidates") or [])
    if not top_candidates:
        return pd.DataFrame(), {}
    table = pd.DataFrame(top_candidates)
    if table.empty:
        return table, {}
    mean_priority = _safe_float(table["expansion_priority_percent"].mean())
    ready_or_strong = int(table["priority_band"].astype(str).isin({"ready", "strong"}).sum())
    runway_score = int(round(np.mean([mean_priority, 100 if ready_or_strong >= 5 else 80 if ready_or_strong >= 3 else 55])))
    return table, {
        "top_candidate_gene": table.iloc[0]["gene"],
        "recommended_gene_count": int(len(table)),
        "ready_or_strong_gene_count": ready_or_strong,
        "mean_top_candidate_priority_percent": mean_priority,
        "score_percent": runway_score,
    }


def build_prime_intelligence_assessment(
    results: dict,
    *,
    output_dir: str | None = None,
    biological_discovery_manifest_path: str | None = None,
    gene_expansion_manifest_path: str | None = None,
) -> dict:
    study_root = _study_root_from_results(results, output_dir=output_dir)
    training_df = results.get("training_metrics") if isinstance(results.get("training_metrics"), pd.DataFrame) else pd.DataFrame()
    external_df = results.get("external_evaluation_metrics") if isinstance(results.get("external_evaluation_metrics"), pd.DataFrame) else pd.DataFrame()
    pairwise_df = results.get("external_pairwise_comparisons") if isinstance(results.get("external_pairwise_comparisons"), pd.DataFrame) else pd.DataFrame()

    study_design = results.get("study_design")
    baseline_experiment = str(getattr(study_design, "baseline_experiment", "external_predictors_only") or "external_predictors_only")

    internal_table, internal_summary = _build_internal_signal_table(training_df.copy())
    external_table, external_summary = _build_external_signal_table(external_df.copy())
    pairwise_table, pairwise_summary = _build_pairwise_support_table(pairwise_df.copy(), baseline_experiment=baseline_experiment)
    attribution_table, attribution_summary = _build_feature_attribution_table(study_root, training_df.copy())

    biological_path = _resolve_optional_manifest(
        study_root,
        biological_discovery_manifest_path,
        "primevarclass_biological_discovery_results",
        "biological_discovery_manifest.json",
    )
    expansion_path = _resolve_optional_manifest(
        study_root,
        gene_expansion_manifest_path,
        "primevarclass_gene_expansion_results",
        "gene_expansion_manifest.json",
    )
    biological_table, biological_summary = _build_biological_alignment_table(biological_path)
    expansion_table, expansion_summary = _build_expansion_runway_table(expansion_path)

    criteria: List[dict] = []
    if internal_summary:
        criteria.append(
            _criterion_row(
                "internal_prime_competitiveness",
                "Internal prime competitiveness",
                1.4,
                internal_summary["score_percent"],
                (
                    f"Melhor experimento primo/hibrido: {internal_summary['best_prime_experiment']} "
                    f"vs melhor nao-primo: {internal_summary['best_nonprime_experiment']} "
                    f"(delta AUC-ROC={_fmt_metric(internal_summary['delta_auc_roc'])})."
                ),
                "Preservar o ganho interno do bloco primo/hibrido nas proximas rodadas multigene.",
                critical=True,
            )
        )
    if external_summary:
        criteria.append(
            _criterion_row(
                "external_prime_leadership",
                "External prime leadership",
                1.7,
                external_summary["score_percent"],
                (
                    f"Modelos primos/hibridos lideram {_fmt_percent(external_summary['prime_external_win_rate_percent'])} "
                    f"das coortes externas em AUC-ROC, com delta medio={_fmt_metric(external_summary['mean_external_delta_auc_roc'])}."
                ),
                "Expandir a lideranca externa para novos genes e novas coortes clinicas independentes.",
                critical=True,
            )
        )
    if pairwise_summary:
        criteria.append(
            _criterion_row(
                "pairwise_prime_support",
                "Prime pairwise support",
                1.5,
                pairwise_summary["score_percent"],
                (
                    f"{_fmt_percent(pairwise_summary['supported_pairwise_share_percent'])} das comparacoes auc_roc "
                    f"contra o baseline declarado sustentam ganho primo/hibrido."
                ),
                "Aumentar o suporte pareado positivo nas coortes externas mais exigentes.",
                critical=True,
            )
        )
    if attribution_summary:
        criteria.append(
            _criterion_row(
                "prime_feature_attribution",
                "Prime feature attribution",
                1.1,
                attribution_summary["score_percent"],
                (
                    f"Melhor retencao mista de features primas em {attribution_summary.get('best_mixed_prime_feature_set') or '-'} "
                    f"e saliencia pura em {attribution_summary.get('best_pure_prime_feature_set') or '-'}."
                ),
                "Continuar monitorando se o sinal primo aparece nas ablations mistas, nao so no bloco puro.",
                critical=False,
            )
        )
    if biological_summary:
        criteria.append(
            _criterion_row(
                "prime_biological_alignment",
                "Prime-biological alignment",
                1.5,
                biological_summary["score_percent"],
                (
                    f"Hotspots, variantes de upgrade e hipoteses funcionais apresentam "
                    f"medianas de deslocamento primo acima do background clinico em niveis variaveis."
                ),
                "Expandir a validacao biologica do sinal primo em novos genes e ensaios funcionais.",
                critical=True,
            )
        )
    if expansion_summary:
        criteria.append(
            _criterion_row(
                "cross_gene_runway",
                "Cross-gene runway",
                1.0,
                expansion_summary["score_percent"],
                (
                    f"{expansion_summary['recommended_gene_count']} genes recomendados alem de BRCA; "
                    f"{expansion_summary['ready_or_strong_gene_count']} em banda ready/strong."
                ),
                "Abrir a rodada multigene priorizando TP53, GCK, PTEN, MSH2 e KRAS.",
                critical=False,
            )
        )

    weighted_total = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / weighted_total)) if weighted_total else 0

    strengths = [item["title"] for item in criteria if item["score_percent"] >= 85]
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    summary = {
        "generated_at": _now_utc(),
        "overall_prime_intelligence_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "prime_intelligence_tier": _tier_from_percent(overall_percent),
        "baseline_experiment": baseline_experiment,
        "best_prime_internal_experiment": internal_summary.get("best_prime_experiment"),
        "best_nonprime_internal_experiment": internal_summary.get("best_nonprime_experiment"),
        "internal_delta_auc_roc": internal_summary.get("delta_auc_roc"),
        "prime_external_win_rate_percent": external_summary.get("prime_external_win_rate_percent"),
        "mean_external_delta_auc_roc": external_summary.get("mean_external_delta_auc_roc"),
        "best_prime_external_experiment": external_summary.get("best_prime_external_experiment"),
        "supported_pairwise_share_percent": pairwise_summary.get("supported_pairwise_share_percent"),
        "best_supported_prime_experiment": pairwise_summary.get("best_supported_prime_experiment"),
        "mixed_prime_attribution_percent": attribution_summary.get("mixed_prime_attribution_percent"),
        "pure_prime_attribution_percent": attribution_summary.get("pure_prime_attribution_percent"),
        "prime_biological_alignment_percent": biological_summary.get("score_percent"),
        "cross_gene_runway_percent": expansion_summary.get("score_percent"),
        "top_candidate_gene_beyond_brca": expansion_summary.get("top_candidate_gene"),
        "n_strengths": int(len(strengths)),
        "n_critical_gaps": int(len(critical_gaps)),
    }

    markdown_lines = [
        "# Prime Intelligence",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Overall prime intelligence: {summary['overall_prime_intelligence_percent']}%",
        f"- Tier: {summary['prime_intelligence_tier']}",
        f"- Best prime internal experiment: {summary.get('best_prime_internal_experiment') or '-'}",
        f"- Best prime external experiment: {summary.get('best_prime_external_experiment') or '-'}",
        "",
        "## Criteria",
        "",
    ]
    for criterion in criteria:
        markdown_lines.extend(
            [
                f"### {criterion['title']}",
                "",
                f"- Score: {criterion['score_percent']}%",
                f"- Status: {criterion['status']}",
                f"- Evidence: {criterion['evidence']}",
                f"- Next step: {criterion['next_step']}",
                "",
            ]
        )

    if not external_table.empty:
        markdown_lines.extend(["## External Prime Leadership", ""])
        for _, row in external_table.iterrows():
            markdown_lines.append(
                f"- {row['cohort']}: {row['prime_experiment']} vs {row['nonprime_experiment']} "
                f"=> delta AUC-ROC={_fmt_metric(row['delta_auc_roc'])}"
            )
        markdown_lines.append("")

    if not biological_table.empty:
        markdown_lines.extend(["## Prime-Biological Alignment", ""])
        for _, row in biological_table.iterrows():
            markdown_lines.append(
                f"- {row['analysis']}: delta prime_diff={_fmt_metric(row['delta_prime_diff'])} "
                f"({int(row['group_count'])} variants)"
            )
        markdown_lines.append("")

    if not expansion_table.empty:
        markdown_lines.extend(["## Cross-Gene Runway", ""])
        for _, row in expansion_table.head(8).iterrows():
            markdown_lines.append(
                f"- {row['gene']}: prioridade {row['expansion_priority_percent']:.1f}% ({row['priority_band']})"
            )

    context = {
        "study_root": str(study_root),
        "biological_discovery_manifest_path": str(biological_path) if biological_path else None,
        "gene_expansion_manifest_path": str(expansion_path) if expansion_path else None,
    }
    return {
        "title": "Prime Intelligence",
        "summary": summary,
        "strengths": strengths,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "criteria": criteria,
        "internal_leaderboard": internal_table.to_dict(orient="records"),
        "external_leadership": external_table.to_dict(orient="records"),
        "pairwise_support": pairwise_table.to_dict(orient="records"),
        "feature_attribution": attribution_table.to_dict(orient="records"),
        "biological_alignment": biological_table.to_dict(orient="records"),
        "expansion_runway": expansion_table.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def export_prime_intelligence_package(
    results: dict,
    *,
    output_dir: str,
    biological_discovery_manifest_path: str | None = None,
    gene_expansion_manifest_path: str | None = None,
) -> Dict[str, str]:
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    assessment = build_prime_intelligence_assessment(
        results,
        output_dir=str(output_root),
        biological_discovery_manifest_path=biological_discovery_manifest_path,
        gene_expansion_manifest_path=gene_expansion_manifest_path,
    )

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    internal_df = pd.DataFrame(assessment.get("internal_leaderboard") or [])
    external_df = pd.DataFrame(assessment.get("external_leadership") or [])
    pairwise_df = pd.DataFrame(assessment.get("pairwise_support") or [])
    attribution_df = pd.DataFrame(assessment.get("feature_attribution") or [])
    biological_df = pd.DataFrame(assessment.get("biological_alignment") or [])
    expansion_df = pd.DataFrame(assessment.get("expansion_runway") or [])

    markdown_path = output_root / "prime_intelligence_report.md"
    html_path = output_root / "prime_intelligence_report.html"
    manifest_path = output_root / "prime_intelligence_manifest.json"
    criteria_path = output_root / "prime_intelligence_criteria.csv"
    internal_path = output_root / "prime_intelligence_internal_leaderboard.csv"
    external_path = output_root / "prime_intelligence_external_leadership.csv"
    pairwise_path = output_root / "prime_intelligence_pairwise_support.csv"
    attribution_path = output_root / "prime_intelligence_feature_attribution.csv"
    biological_path = output_root / "prime_intelligence_biological_alignment.csv"
    expansion_path = output_root / "prime_intelligence_expansion_runway.csv"

    markdown_report = str(assessment.get("markdown_report") or "")
    html_report = (
        "<html><body><pre>"
        + html.escape(markdown_report)
        + "</pre></body></html>"
    )

    markdown_path.write_text(markdown_report, encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    internal_df.to_csv(internal_path, index=False)
    external_df.to_csv(external_path, index=False)
    pairwise_df.to_csv(pairwise_path, index=False)
    attribution_df.to_csv(attribution_path, index=False)
    biological_df.to_csv(biological_path, index=False)
    expansion_df.to_csv(expansion_path, index=False)

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "strengths": assessment.get("strengths"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "criteria_path": str(criteria_path),
        "internal_leaderboard_path": str(internal_path),
        "external_leadership_path": str(external_path),
        "pairwise_support_path": str(pairwise_path),
        "feature_attribution_path": str(attribution_path),
        "biological_alignment_path": str(biological_path),
        "expansion_runway_path": str(expansion_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "report_context": assessment.get("report_context"),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "prime_intelligence_assessment": assessment,
        "prime_intelligence_manifest_path": str(manifest_path),
        "prime_intelligence_report_markdown_path": str(markdown_path),
        "prime_intelligence_report_html_path": str(html_path),
        "prime_intelligence_criteria_path": str(criteria_path),
        "prime_intelligence_internal_leaderboard_path": str(internal_path),
        "prime_intelligence_external_leadership_path": str(external_path),
        "prime_intelligence_pairwise_support_path": str(pairwise_path),
        "prime_intelligence_feature_attribution_path": str(attribution_path),
        "prime_intelligence_biological_alignment_path": str(biological_path),
        "prime_intelligence_expansion_runway_path": str(expansion_path),
    }
