"""Command-line interface for PrimeVarClass.

Score a single BRCA1/BRCA2 missense variant with the flagship domain-aware +
ESM-2 model, and report its functional-domain context, zero-shot ESM-2 score and
the model's pathogenicity probability. Everything runs on the core and the
public data shipped in this repository; nothing is hard-coded.

Examples
--------
    primevarclass score BRCA1 p.Arg1699Trp
    primevarclass score BRCA2 p.Asp2723His
    primevarclass --version

The first ``score`` call trains the flagship model on the internal public cohort
(a few seconds) and caches it; later calls reuse the cache.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from . import __version__

_AA1TO3 = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln",
    "E": "Glu", "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys",
    "M": "Met", "F": "Phe", "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp",
    "Y": "Tyr", "V": "Val",
}
_AA3TO1 = {v.upper(): k for k, v in _AA1TO3.items()}


def _find_data_root(override: str | None) -> Path:
    """Locate the repository root that holds ``configs/`` and ``scratch/``."""
    if override:
        return Path(override).resolve()
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for base in candidates:
        if (base / "configs" / "public_brca_real.toml").exists():
            return base
    raise SystemExit(
        "Não foi possível localizar a raiz do projeto (configs/public_brca_real.toml). "
        "Rode a partir do repositório ou use --data-root."
    )


def _parse_change(change: str) -> tuple[str, int, str, str, str]:
    """Parse 'p.Arg1699Trp' / 'Arg1699Trp' / 'R1699W' -> (ref1, pos, alt1, ref3, alt3)."""
    import re

    s = change.strip()
    if s.lower().startswith("p."):
        s = s[2:]
    m = re.match(r"^([A-Za-z]{1,3})(\d+)([A-Za-z]{1,3})$", s)
    if not m:
        raise SystemExit(f"Formato de variante inválido: {change!r} (ex.: p.Arg1699Trp ou R1699W)")
    ref_raw, pos, alt_raw = m.group(1), int(m.group(2)), m.group(3)

    def to1(a: str) -> str:
        if len(a) == 1:
            return a.upper()
        return _AA3TO1.get(a.upper(), "")

    ref1, alt1 = to1(ref_raw), to1(alt_raw)
    if not ref1 or not alt1:
        raise SystemExit(f"Código de aminoácido não reconhecido em {change!r}.")
    return ref1, pos, alt1, _AA1TO3[ref1], _AA1TO3[alt1]


def _load_flagship(root: Path, random_state: int = 42):
    """Train (or load from cache) the flagship domain + ESM-2 pipeline."""
    import joblib
    import pandas as pd

    from .core import _build_pipeline, get_feature_subsets
    from .data_sources import build_dataset_from_source_config
    from .esm_scores import attach_esm_scores

    esm_path = root / "scratch" / "esm_input" / "esm2_scores.csv"
    cfg = root / "configs" / "public_brca_real.toml"
    cache_dir = root / ".primevarclass_cache"
    cache_dir.mkdir(exist_ok=True)
    key = hashlib.md5(
        f"{cfg.stat().st_mtime}:{esm_path.stat().st_mtime if esm_path.exists() else 0}".encode()
    ).hexdigest()[:12]
    cache = cache_dir / f"flagship_{key}.joblib"
    if cache.exists():
        return joblib.load(cache), esm_path

    esm_df = pd.read_csv(esm_path) if esm_path.exists() else None
    df, _, _ = build_dataset_from_source_config(str(cfg), mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    df = df.loc[keep].reset_index(drop=True)
    if esm_df is not None:
        df = attach_esm_scores(df, esm_df)
    cols = [c for c in get_feature_subsets(df)["domain_aware_plus_esm"]
            if c in df.columns and not df[c].isna().all()]
    pipe = _build_pipeline(df[cols], random_state=random_state)
    pipe.fit(df[cols], y.loc[keep].astype(int).to_numpy())
    bundle = {"pipeline": pipe, "columns": cols}
    joblib.dump(bundle, cache)
    return bundle, esm_path


def _cmd_score(args: argparse.Namespace) -> int:
    import pandas as pd

    from .core import build_dataset_from_dataframe
    from .domain_annotation import annotate_domain
    from .esm_scores import attach_esm_scores

    gene = str(args.gene).upper()
    if gene not in {"BRCA1", "BRCA2"}:
        raise SystemExit(f"Gene não suportado: {gene} (apenas BRCA1 e BRCA2).")
    ref1, pos, alt1, ref3, alt3 = _parse_change(args.change)
    hgvs_p = f"p.{ref3}{pos}{alt3}"

    root = _find_data_root(args.data_root)
    bundle, esm_path = _load_flagship(root)
    pipe, cols = bundle["pipeline"], bundle["columns"]

    # engineer the query variant's features exactly like the training data
    q = pd.DataFrame([{"gene": gene, "hgvs_p": hgvs_p, "label": 0,
                       "position": pos, "aa_ref": ref1, "aa_alt": alt1}])
    qb, _ = build_dataset_from_dataframe(q, mode="hybrid", keep_metadata=True)
    if esm_path.exists():
        qb = attach_esm_scores(qb, pd.read_csv(esm_path))
    for c in cols:
        if c not in qb.columns:
            qb[c] = pd.NA
    prob = float(pipe.predict_proba(qb[cols])[:, 1][0])

    domain, critical = annotate_domain(gene, pos)
    esm_llr = qb["esm2_llr"].iloc[0] if "esm2_llr" in qb.columns else None
    esm_txt = f"{float(esm_llr):+.2f}" if esm_llr is not None and pd.notna(esm_llr) else "indisponível"
    call = "PATOGÊNICA (provável)" if prob >= 0.5 else "BENIGNA (provável)"
    conf = "alta" if abs(prob - 0.5) > 0.35 else ("moderada" if abs(prob - 0.5) > 0.15 else "baixa")

    print(f"\nPrimeVarClass: variante {gene} {hgvs_p}")
    print("-" * 52)
    print(f"  Domínio funcional      : {domain}"
          f"{'  [REGIÃO CRÍTICA]' if critical else ''}")
    print(f"  ESM-2 LLR (zero-shot)  : {esm_txt}"
          f"{'   (sinal patogênico)' if (esm_llr is not None and pd.notna(esm_llr) and float(esm_llr) < -2) else ''}")
    print(f"  Probabilidade (modelo) : {prob:.3f}")
    print(f"  Classificação          : {call}  (confiança {conf})")
    print("-" * 52)
    print("  Ferramenta de apoio à pesquisa. NÃO substitui aconselhamento")
    print("  genético nem validação experimental independente.\n")
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    """Record a user/lab-confirmed classification so the model can learn from it."""
    from .continual import FeedbackStore

    gene = str(args.gene).upper()
    if gene not in {"BRCA1", "BRCA2"}:
        raise SystemExit(f"Gene não suportado: {gene} (apenas BRCA1 e BRCA2).")
    ref1, pos, alt1, _, _ = _parse_change(args.change)
    root = _find_data_root(args.data_root)
    store = FeedbackStore(root / "registro_prospectivo")
    rec = store.add(gene, pos, ref1, alt1, args.label, source=args.source,
                    submitter=args.submitter)
    if rec is None:
        print("Já registrado anteriormente; nada a fazer (armazenamento idempotente).")
        return 0
    lab = "PATOGÊNICA" if rec.label == 1 else "BENIGNA"
    print(f"\nFeedback registrado: {gene} p.{ref1}{pos}{alt1}  ->  {lab}")
    print(f"  fonte      : {rec.source}")
    print(f"  carimbo UTC: {rec.timestamp}")
    print(f"  SHA-256    : {rec.sha256[:16]}…")
    print("  Rode 'primevarclass update' para incorporar o feedback (com trava de segurança).\n")
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    """Refit with accumulated feedback; promote only if a locked hold-out doesn't degrade."""
    import pandas as pd

    from .continual import incremental_update
    from .data_sources import build_dataset_from_source_config

    root = _find_data_root(args.data_root)
    holdout_cfgs = ["configs/public_brca_external_real_clinvar_expert_brca1.toml",
                    "configs/public_brca_external_real_clinvar_expert_brca2.toml"]
    frames = []
    for c in holdout_cfgs:
        df, _, _ = build_dataset_from_source_config(str(root / c), mode="hybrid", keep_metadata=True)
        y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
        f = df.loc[keep, ["gene", "position", "aa_ref", "aa_alt"]].copy()
        f["label"] = y.loc[keep].astype(int).to_numpy()
        frames.append(f)
    holdout = pd.concat(frames, ignore_index=True)

    print("Reajustando com o feedback acumulado (trava de segurança ativa)…")
    entry = incremental_update(root, holdout_ids=holdout,
                               directory=root / "registro_prospectivo")
    print(f"\nAtualização contínua: versão candidata v{entry['version']}")
    print("-" * 52)
    print(f"  Rótulos de feedback     : {entry['n_feedback']}")
    print(f"  AUC (modelo atual)      : {entry['baseline_auc']:.3f}")
    print(f"  AUC (candidato+feedback): {entry['holdout_auc']:.3f}  [conjunto travado]")
    print(f"  Decisão                 : {'PROMOVIDO ✓' if entry['promoted'] else 'REJEITADO (trava de segurança)'}")
    print(f"  Hash do modelo          : {entry['model_sha256']}")
    print("-" * 52 + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="primevarclass",
        description="Classificação consciente de domínio de variantes missense em BRCA1/BRCA2.",
    )
    p.add_argument("--version", action="version", version=f"PrimeVarClass {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score", help="pontua uma variante missense (domínio + ESM-2 + modelo)")
    s.add_argument("gene", help="BRCA1 ou BRCA2")
    s.add_argument("change", help="mudança proteica, ex.: p.Arg1699Trp ou R1699W")
    s.add_argument("--data-root", default=None, help="raiz do repositório (auto-detectada por padrão)")
    s.set_defaults(func=_cmd_score)

    fb = sub.add_parser("feedback", help="registra uma classificação confirmada (aprendizado contínuo)")
    fb.add_argument("gene", help="BRCA1 ou BRCA2")
    fb.add_argument("change", help="mudança proteica, ex.: p.Arg1699Trp ou R1699W")
    fb.add_argument("--label", required=True, help="pathogenic|benign")
    fb.add_argument("--source", default="user", help="origem (clinvar, functional_assay, segregation…)")
    fb.add_argument("--submitter", default="anon", help="identificação de quem submeteu")
    fb.add_argument("--data-root", default=None, help="raiz do repositório (auto-detectada por padrão)")
    fb.set_defaults(func=_cmd_feedback)

    up = sub.add_parser("update", help="reajusta com o feedback acumulado (com trava de segurança)")
    up.add_argument("--data-root", default=None, help="raiz do repositório (auto-detectada por padrão)")
    up.set_defaults(func=_cmd_update)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
