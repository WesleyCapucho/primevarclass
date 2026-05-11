# PrimeVarClass VQE template for BRCA1 p.Val41Asp
# VQE rank: 10
# Active space: metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT; prime seed: 4e/6o prime-seeded start; expand only if xTB/DFT supports it
# Ansatz: UCCSD_then_ADAPT_VQE
# Prime coupling: 64.7% (directional_prime_rewiring)
# Prime shot schedule: 2309;3557;6067
# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import Estimator
from qiskit_nature.second_q.mappers import JordanWignerMapper
# TODO: build ElectronicStructureProblem from a reviewed molecular driver.
# Prime-guided initialization: Use prime seed 4e/6o prime-seeded start; expand only if xTB/DFT supports it with shot ladder 2309;3557;6067
mapper = JordanWignerMapper()
optimizer = COBYLA(maxiter=500)
# ansatz = ...  # UCCSD or hardware-efficient circuit after active-space review
# vqe = VQE(Estimator(), ansatz, optimizer)
