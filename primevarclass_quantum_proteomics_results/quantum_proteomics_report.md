# PrimeVarClass Quantum Proteomics Engine

- Generated at: `2026-04-23T22:42:20Z`
- Quantum targets: `12`
- High-priority QM targets: `12`
- Mean quantum priority: `89.3%`
- Mean prime score in QM targets: `74.0%`
- Mean prime-quantum coupling: `72.9%`
- Top vulnerability classes: `metal_redox_or_cysteine_network`

## Top quantum targets

- BRCA1 p.Leu82Lys: QM=91.8%, prime=82.2%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu82Glu: QM=91.7%, prime=82.2%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu22Glu: QM=91.3%, prime=82.2%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu100Asp: QM=91.1%, prime=82.2%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu4Asp: QM=91.1%, prime=82.2%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu30His: QM=89.4%, prime=70.0%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu22His: QM=89.2%, prime=70.0%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Val11Asp: QM=87.8%, prime=61.1%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Val41Asp: QM=87.8%, prime=61.1%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Val42Glu: QM=87.7%, prime=61.1%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Val11Glu: QM=87.7%, prime=61.1%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen
- BRCA1 p.Leu4Gln: QM=85.4%, prime=92.8%, class=metal_redox_or_cysteine_network, methods=xTB_GFN2_screen;DFT_fragment_single_point;QM_MM_boundary_refinement;docking_hotspot_screen

## Prime-quantum bridge

- BRCA1 p.Leu4Gln: prime-Q=86.7%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=1777;2741;4673
- BRCA1 p.Leu82Lys: prime-Q=77.8%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=2789;4327;7349
- BRCA1 p.Leu82Glu: prime-Q=77.8%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=2789;4327;7349
- BRCA1 p.Leu22Glu: prime-Q=77.8%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=2789;4327;7349
- BRCA1 p.Leu100Asp: prime-Q=77.8%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=2789;4327;7349
- BRCA1 p.Leu4Asp: prime-Q=77.8%, signature=strong_prime_displacement, seed=6e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=2789;4327;7349
- BRCA1 p.Leu30His: prime-Q=69.9%, signature=directional_prime_rewiring, seed=4e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=3299;5087;8677
- BRCA1 p.Leu22His: prime-Q=69.9%, signature=directional_prime_rewiring, seed=4e/6o prime-seeded start; expand only if xTB/DFT supports it, shots=3299;5087;8677

## VQE and quantum algorithm targets

- BRCA1 p.Leu4Gln: VQE readiness=97.0%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 1777;2741;4673
- BRCA1 p.Leu82Glu: VQE readiness=91.8%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2789;4327;7349
- BRCA1 p.Leu100Asp: VQE readiness=91.6%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2789;4327;7349
- BRCA1 p.Leu4Asp: VQE readiness=91.6%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2789;4327;7349
- BRCA1 p.Leu82Lys: VQE readiness=91.5%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2789;4327;7349
- BRCA1 p.Leu22Glu: VQE readiness=91.4%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2789;4327;7349
- BRCA1 p.Leu30His: VQE readiness=84.5%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 4e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 3299;5087;8677
- BRCA1 p.Leu22His: VQE readiness=84.3%, ansatz=UCCSD_then_ADAPT_VQE, mapping=Jordan-Wigner primary; parity/tapering optional after symmetry review, prime-guided=Use prime seed 4e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 3299;5087;8677

## Execution workflow

- 1_structure_acquisition (AlphaFold/PDB/local mutant model): Obtain reference and mutant protein coordinates around each prioritized residue.
- 2_local_relaxation (OpenMM): Relax the local mutant microenvironment and detect contact/solvation changes.
- 3_semiclassical_quantum_screen (xTB GFN2): Fast fragment-level charge, geometry, and interaction-energy screening.
- 4_dft_refinement (Psi4 or equivalent DFT backend): Refine top fragments with DFT single-point or constrained optimization.
- 5_druggability_probe (AutoDock Vina or ligand-screening backend): Probe ligandability of mutant-exposed pockets or interface rescue hypotheses.

## Scientific guardrails

- This engine prioritizes quantum/structural hypotheses; it does not claim therapeutic efficacy.
- Coordinates, protonation states, charge states, and experimental controls must be reviewed before running QM, MD, or docking.
- Drug-development hypotheses require orthogonal biochemical, cellular, and translational validation.