# PrimeVarClass BRCA1 Structural Campaign

- Generated at: `2026-04-24T04:33:52Z`
- BRCA1 campaign targets: `12`
- Template coverage: `75%`
- Campaign readiness: `59%`
- Mean structural signal: `85.1%`
- Mean drug-discovery readiness: `79.8%`
- xTB-ready targets: `0`
- DFT-ready targets: `0`

## Engine preflight

- xTB available: `no`
- Psi4 available: `no`
- OpenMM available: `no`
- AutoDock Vina available: `no`
- Missing blockers: `xtb, psi4, vina, openmm, qiskit_nature`

## Top BRCA1 targets

- BRCA1 p.Leu100Asp: signal=95.8%, delta=71.7%, alignment=83.0%, status=template_ready_engines_missing
- BRCA1 p.Leu4Gln: signal=98.1%, delta=73.2%, alignment=89.6%, status=template_ready_engines_missing
- BRCA1 p.Leu4Asp: signal=95.8%, delta=71.7%, alignment=83.0%, status=template_ready_engines_missing
- BRCA1 p.Leu82Glu: signal=95.9%, delta=71.7%, alignment=83.1%, status=template_ready_engines_missing
- BRCA1 p.Leu30Asn: signal=61.8%, delta=62.8%, alignment=48.6%, status=prioritized_requires_template_refresh
- BRCA1 p.Leu22Glu: signal=95.4%, delta=71.4%, alignment=82.9%, status=template_ready_engines_missing
- BRCA1 p.Leu82Lys: signal=95.4%, delta=71.4%, alignment=82.9%, status=template_ready_engines_missing
- BRCA1 p.Leu22Gln: signal=61.5%, delta=62.6%, alignment=48.5%, status=prioritized_requires_template_refresh
- BRCA1 p.Val64Asn: signal=57.6%, delta=56.0%, alignment=42.4%, status=prioritized_requires_template_refresh
- BRCA1 p.Val11Asp: signal=86.5%, delta=60.2%, alignment=67.8%, status=template_ready_engines_missing

## Guardrail

- This package organizes a BRCA1 execution campaign with honest preflight status.
- If xTB or Psi4 are missing, the current outputs remain surrogate prioritization plus ready-to-run templates.
- Do not claim executed QM/DFT evidence until the engine status is green and coordinates are reviewed.