"""Build a PRE-REGISTERED, timestamped prospective prediction registry.

For every BRCA1/2 variant that is currently a VUS or has conflicting
classifications in ClinVar, we record — dated and hashed — PrimeVarClass's
calibrated ACMG prediction. As ClinVar resolves these variants over the coming
years, anyone can check our hit rate against this immutable record. This is the
honest, falsifiable version of "prospective validation".

Writes registro_prospectivo/brca_vus_predictions_<date>.csv and MANIFEST.md
(with a SHA-256 of the predictions so the record cannot be altered afterwards).

Run: python scratch/build_prospective_registry.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os

import pandas as pd

OUTDIR = "registro_prospectivo"
os.makedirs(OUTDIR, exist_ok=True)
DATE = "2026-07-09"
key = ["gene", "position", "aa_ref", "aa_alt"]

clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
res = pd.read_csv("primevarclass_manuscript_analysis/brca_missense_evidence_resource.csv")


def status(s):
    s = str(s)
    if "onflicting" in s:
        return "conflitante"
    if "ncertain" in s:
        return "VUS"
    return "outro"


clin["registration_status"] = clin.clinsig.map(status)
unres = clin[clin.registration_status.isin(["VUS", "conflitante"])]
reg = unres.merge(res[key + ["pathogenicity_prob", "acmg_evidence"]], on=key, how="inner")

pred = {"PP3_Strong": "Patogênica/Provavelmente patogênica",
        "BP4_Moderate": "Benigna/Provavelmente benigna",
        "uninformative": "Indeterminada (permanece VUS)"}
reg["predicted_reclassification"] = reg.acmg_evidence.map(pred)
reg["registration_date"] = DATE
reg = reg[["gene", "hgvs_p", "position", "aa_ref", "aa_alt", "registration_status",
           "pathogenicity_prob", "acmg_evidence", "predicted_reclassification",
           "registration_date"]].sort_values(["gene", "position", "aa_alt"]).reset_index(drop=True)

csv_path = os.path.join(OUTDIR, f"brca_vus_predictions_{DATE}.csv")
reg.to_csv(csv_path, index=False)
sha = hashlib.sha256(open(csv_path, "rb").read()).hexdigest()

n_path = int((reg.acmg_evidence == "PP3_Strong").sum())
n_ben = int((reg.acmg_evidence == "BP4_Moderate").sum())
n_ind = int((reg.acmg_evidence == "uninformative").sum())

manifest = f"""# Registro prospectivo de predições — PrimeVarClass

**Data de registro:** {DATE}
**Arquivo de predições:** `brca_vus_predictions_{DATE}.csv`
**SHA-256:** `{sha}`

## O que é isto

Um **compromisso público, datado e imutável**. Registramos aqui a predição
calibrada do PrimeVarClass para **todas as variantes** *missense* de BRCA1/BRCA2
que, nesta data, são **VUS** (significado incerto) ou têm **classificações
conflitantes** no ClinVar. À medida que painéis de especialistas resolverem essas
variantes nos próximos anos, qualquer pessoa poderá conferir nossa taxa de acerto
contra este registro — que não pode ser alterado retroativamente (verifique o
SHA-256 acima).

Esta é a versão **honesta e falsificável** de "validação prospectiva": não
afirmamos ter validação prospectiva hoje; nós a *tornamos possível* para o futuro.

## Conteúdo ({len(reg)} variantes não resolvidas)

| Predição | n | Interpretação |
| --- | ---: | --- |
| **PP3_Forte → patogênica** | {n_path} | predizemos reclassificação como (provavelmente) patogênica |
| **BP4_Moderado → benigna** | {n_ben} | predizemos reclassificação como (provavelmente) benigna |
| Indeterminada (mantém VUS) | {n_ind} | abstenção responsável — não arriscamos um palpite |

As predições PP3_Forte e BP4_Moderado usam apenas os dois níveis de evidência
externamente validados (Material Suplementar S3): na coorte externa, PP3_Forte
correspondeu a 94% de patogênicas e BP4_Moderado a 3%.

## Como validar no futuro

1. Confirme a integridade: `sha256sum brca_vus_predictions_{DATE}.csv` deve
   bater com o valor acima.
2. Baixe o ClinVar atual e verifique, entre as variantes aqui listadas como VUS
   em {DATE}, quantas foram reclassificadas — e em que direção.
3. Compare a direção real com a coluna `predicted_reclassification`.

Metodologia de pontuação: `scratch/generate_evidence_resource.py` e
`scratch/acmg_calibration.py` (limiares PP3_Forte ≥ 0,675 e BP4_Moderado ≤ 0,255).
"""
open(os.path.join(OUTDIR, "MANIFEST.md"), "w", encoding="utf-8").write(manifest)

print(f">> registro escrito em {OUTDIR}/")
print(f"   {len(reg)} variantes não resolvidas | PP3_Forte={n_path}  BP4_Moderado={n_ben}  indet.={n_ind}")
print(f"   SHA-256: {sha}")
