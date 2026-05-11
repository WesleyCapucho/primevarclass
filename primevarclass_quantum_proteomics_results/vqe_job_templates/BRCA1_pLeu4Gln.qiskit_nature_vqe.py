# PrimeVarClass VQE template for BRCA1 p.Leu4Gln
# VQE rank: 1
# Active space: metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT; prime seed: 6e/6o prime-seeded start; expand only if xTB/DFT supports it
# Ansatz: UCCSD_then_ADAPT_VQE
# Prime coupling: 86.7% (strong_prime_displacement)
# Prime shot schedule: 1777;2741;4673
# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import Estimator
from qiskit_nature.second_q.mappers import JordanWignerMapper
# TODO: build ElectronicStructureProblem from a reviewed molecular driver.
# Prime-guided initialization: Use prime seed 6e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 1777;2741;4673
mapper = JordanWignerMapper()
optimizer = COBYLA(maxiter=500)
# ansatz = ...  # UCCSD or hardware-efficient circuit after active-space review
# vqe = VQE(Estimator(), ansatz, optimizer)
