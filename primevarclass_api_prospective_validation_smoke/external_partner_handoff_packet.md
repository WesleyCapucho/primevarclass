# PrimeVarClass External Partner Handoff Packet

## Purpose

PrimeVarClass is ready for research-use-only shadow validation with blinded external functional and structural confirmation. This packet tells a partner lab what to run, what to return, and what must stay blinded.

## Current validation status

- Prospective readiness: `88%`
- Experimental completion: `0%`
- Final scientific proof cap: `88%`
- Partner handoff variants: `24`

## Partner rules

- Use only blinded IDs until raw assay/QC outputs are returned.
- Do not use the model score to choose assay thresholds after the run starts.
- Return raw readouts, normalized effects, replicate counts, QC status, failed variants and protocol deviations.
- Treat outputs as research evidence until clinical validation, regulatory review and disease-specific evidence standards are met.

## First targets

- PVC-BLIND-0001: BRCA1 p.Leu100Asp | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0002: BRCA1 p.Leu4Gln | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0003: BRCA1 p.Leu4Asp | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0004: BRCA1 p.Leu82Glu | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0005: BRCA1 p.Leu30Asn | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0006: BRCA1 p.Leu22Glu | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0007: BRCA1 p.Leu82Lys | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0008: BRCA1 p.Leu22Gln | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0009: BRCA1 p.Val64Asn | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0010: BRCA1 p.Val11Asp | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0011: BRCA1 p.Val41Asp | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`
- PVC-BLIND-0012: BRCA1 p.Leu30His | DNA repair and protein-domain integrity | SOP `SOP_BRCA1_HDR_SGE`

## Minimum data return

- `blinding_id`, `gene`, `hgvs_p`, `assay_version`, `raw_readout`, `normalized_effect`, `qc_status`, `replicate_count`, `control_pass`, `operator_blinded`, `notes`.