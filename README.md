# PrimeVarClass

**Classificação consciente de domínio de variantes *missense* em BRCA1/BRCA2, validada externamente.**

PrimeVarClass é um sistema aberto e reprodutível de inteligência artificial para priorizar **variantes de significado incerto (VUS)** em genes de predisposição ao câncer de mama e de ovário. Seu princípio central é o **rigor metodológico e a honestidade científica**.

> Este repositório acompanha o trabalho submetido ao **32º Prêmio Jovem Cientista** (categoria Estudante do Ensino Superior; tema *Inteligência Artificial para o Bem Comum* — subtema IA & Saúde). O artigo completo (Português, 24 páginas) está em **[`docs/manuscrito/PrimeVarClass_Artigo_Premio_Jovem_Cientista.pdf`](docs/manuscrito/PrimeVarClass_Artigo_Premio_Jovem_Cientista.pdf)**.

---

## A ciência, com honestidade

O projeto nasceu de uma hipótese original — **codificar aminoácidos como números primos** — que **testamos com rigor e refutamos de forma transparente**:

- sob validação cruzada bloqueada por posição e generalização em coortes externas, características derivadas de primos tiveram desempenho **inferior** ao de uma identidade trivial de aminoácidos sem posição (AUC externa 0,681 vs. 0,718; DeLong *p* = 0,045);
- adicioná-las a um modelo bioquímico **reduziu** o desempenho (AUC externa 0,791 → 0,765; DeLong *p* < 0,0001).

No processo, diagnosticamos uma **armadilha de vazamento posicional** (a posição bruta do resíduo memoriza o treino e colapsa em dados externos) e construímos a contribuição real do trabalho: um **classificador consciente de domínio funcional**.

### Resultado principal (dados reais, reexecutável)

| Modelo | CV bloqueada por posição | Coortes externas independentes |
| --- | ---: | ---: |
| Bioquímico (sem posição) | 0,743 | 0,717 |
| **Consciente de domínio (proposto)** | **0,818** | **0,847** |
| Posição bruta (referência de vazamento) | 0,802 | 0,791 |

O modelo consciente de domínio **generaliza** para coortes externas independentes (AUC **0,847**; DeLong *p* = 1,8 × 10⁻¹³ vs. linha de base), superando a memorização de posição — evidência de **biologia transferível, não memorização**. A robustez é confirmada por *bootstrap* (IC95% 0,810–0,881), teste de permutação (*p* = 5 × 10⁻⁴), validação cruzada multi-semente e meta-análise entre coortes.

---

## Integridade científica

- Todos os dados são **públicos e auditáveis**: ClinVar, painéis de especialistas ENIGMA/ClinGen, gnomAD.
- **Nenhum resultado, figura ou métrica foi fabricado ou simulado.** Todas as figuras e números do artigo são gerados por scripts reexecutáveis deste repositório.
- Anotação de domínio derivada do **UniProt** (BRCA1 P38398; BRCA2 P51587); estruturas 3D a partir de coordenadas experimentais reais do **RCSB PDB**.
- O uso de ferramentas de IA no desenvolvimento é declarado no artigo, sob responsabilidade humana integral.

---

## Núcleo do sistema

| Módulo | Papel |
| --- | --- |
| [`src/primevarclass/domain_annotation.py`](src/primevarclass/domain_annotation.py) | Mapa curado de domínios funcionais UniProt (BRCA1 RING/BRCT; BRCA2 DBD) |
| [`src/primevarclass/core.py`](src/primevarclass/core.py) | Engenharia de características, treino e validação (Random Forest) |
| [`src/primevarclass/esm_scores.py`](src/primevarclass/esm_scores.py) | Ingestão de escores ESM-2 (aprendizado profundo autêntico, *zero-shot*) |
| [`src/primevarclass/data_sources.py`](src/primevarclass/data_sources.py) | Ingestão de fontes públicas (ClinVar, gnomAD, ENIGMA/ClinGen) |
| [`tests/`](tests/) | Testes automatizados (anotação de domínio, ingestão ESM, núcleo) |

Os conjuntos de características de `get_feature_subsets` incluem, entre outros: `biochemical_only`, `domain_aware` (modelo proposto), `domain_aware_plus_esm` e `prime_only` (a hipótese testada e refutada).

---

## Reprodutibilidade

```bash
# instalar em modo editável
pip install -e .

# testes rápidos do núcleo honesto
pytest tests/test_domain_annotation.py tests/test_esm_scores.py -q

# reproduzir o resultado principal nas coortes reais
python scratch/validate_domain_integration.py

# robustez (Monte Carlo) e meta-análise entre coortes
python scratch/monte_carlo_robustness.py
python scratch/meta_analysis.py
```

Sementes aleatórias são fixadas para reprodutibilidade determinística. Os artefatos numéricos e as figuras em alta resolução são gravados em `primevarclass_manuscript_analysis/`.

---

## Aviso

Ferramenta de **apoio à pesquisa genética responsável**. **Não** é um dispositivo de diagnóstico clínico, **não** emite laudo e **não** substitui aconselhamento genético profissional nem validação experimental independente.

## Licença

Distribuído sob a licença **MIT** — ver [`LICENSE`](LICENSE).

## Autor

**Wesley Felipe Capucho** — graduando em Engenharia Bioquímica, Escola de Engenharia de Lorena, Universidade de São Paulo (EEL-USP).
