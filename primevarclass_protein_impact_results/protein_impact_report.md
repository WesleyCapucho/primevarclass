# PrimeVarClass Protein Impact Package

- Generated at: `2026-04-23T22:42:21Z`
- Candidate variants triaged: `883`
- 3D/proteomic modeling queue: `25`
- High-priority variants: `138` at `>= 85.0%`
- Modeling-queue prime alignment: `84%`
- Candidate-wide prime alignment: `26%`
- Mean queue prime score: `64.9%`

## Top modeling queue

- BRCA1 p.Leu100Asp: impact=92.7%, prime=75.5%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu4Gln: impact=92.6%, prime=84.1%, region=RING domain, tags=hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu4Asp: impact=92.6%, prime=75.5%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu82Glu: impact=92.5%, prime=75.5%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu30Asn: impact=92.0%, prime=84.1%, region=RING domain, tags=hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu22Glu: impact=91.4%, prime=75.5%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu82Lys: impact=91.2%, prime=75.5%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu22Gln: impact=91.1%, prime=84.1%, region=RING domain, tags=hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Val64Asn: impact=90.6%, prime=69.6%, region=RING domain, tags=hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_curvature_spike;twin_prime_context_shift
- BRCA1 p.Val11Asp: impact=90.3%, prime=52.3%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Val41Asp: impact=90.3%, prime=52.3%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;amino_acid_class_switch;large_prime_displacement;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift
- BRCA1 p.Leu30His: impact=90.2%, prime=67.0%, region=RING domain, tags=electrostatic_shift;hydrophobic_core_or_surface_shift;aromatic_packing_shift;amino_acid_class_switch;large_prime_displacement;prime_gap_rewiring;prime_curvature_spike;twin_prime_context_shift;sophie_germain_context_shift

## Region summary

- BRCA1 RING domain: variants=490, mean_impact=81.3%, mechanism=zinc_binding_or_E3_ligase_interface
- BRCA2 DNA-binding domain: variants=27, mean_impact=79.2%, mechanism=DNA_binding_or_fold_stability
- BRCA1 outside_curated_domain_prior: variants=366, mean_impact=70.9%, mechanism=context_dependent_or_unknown

## Modeling guidance

- Treat this package as a triage and hypothesis-generation layer, not as final structural proof.
- For top variants, run reference-vs-mutant structure modeling, local contact analysis, and assay follow-up.
- Use the prime-mechanistic score as an explanatory signal to prioritize biochemical shifts that are unusually large in the project's prime encoding space.