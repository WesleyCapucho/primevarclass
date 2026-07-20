# Scripts de análise e reprodução

Esta pasta contém os scripts que produzem **todos os números e figuras** do artigo
e do material suplementar. Cada script é independente, roda a partir da raiz do
repositório e grava seus resultados em `primevarclass_manuscript_analysis/`
(dados) e em `docs/*/figuras/` (imagens).

```bash
pip install -e ".[explain,dev]"
python scratch/<script>.py          # sempre a partir da raiz do repositorio
```

> O núcleo do método está em [`src/primevarclass/`](../src/primevarclass), com
> testes em [`tests/`](../tests). Esta pasta é a camada de **experimentos**: cada
> arquivo responde a uma pergunta do artigo e não é importado pelo pacote.

## Comece por aqui

| Ordem | Script | Responde a |
| --- | --- | --- |
| 1 | `validate_domain_integration.py` | **o resultado principal**: consciência de domínio vs. posição bruta (Tabelas 2 e 3) |
| 2 | `prime_hypothesis_rigorous_test.py` | a hipótese dos primos foi refutada? (Tabela 1) |
| 3 | `benchmark_sota.py` | como o modelo se compara ao estado da arte (Tabela 5) |
| 4 | `acmg_calibration.py` | o escore vira evidência clínica ACMG/AMP? |
| 5 | `prospective_analysis.py` | o modelo prevê reclassificações futuras? (Figura 7) |

---

## 1. Dados (executar antes de qualquer análise)

| Script | O que faz |
| --- | --- |
| `fetch_clinvar.py` | baixa os registros reais de BRCA1/BRCA2 do ClinVar (E-utilities) |
| `fetch_clinvar_expanded_panel.py` | idem para VHL, MLH1, MSH2, MSH6 e RET (painel expandido) |
| `fetch_gnomad_populations.py` | frequências alélicas por ancestralidade (gnomAD v4) |
| `fetch_alphamissense_annotations.py` | predições completas do AlphaMissense por substituição |
| `fetch_alphamissense_vep.py` | AlphaMissense via Ensembl VEP para as variantes vivas do ClinVar |
| `esm2_score.py` | escores ESM-2 (masked-marginal LLR) de BRCA1/BRCA2, em CPU |
| `esm2_score_tp53.py`, `esm2_score_hboc.py` | idem para TP53 e o painel HBOC |
| `colab_esm2_650M_panel.py`, `colab_esm2_650M_expanded.py` | mesma pontuação em GPU (Colab); usados para os painéis multigênicos |
| `colab_esm2_panel.py` | primeira versão do pontuador de painel em Colab, anterior à padronização no modelo de 650M |
| `colab_esm2_3b_panel.py` | verificação de robustez com o ESM-2 de 3B parâmetros |
| `colab_proteinmpnn_structure.py` | escore estrutural por variante (ProteinMPNN), exploratório |
| `make_notebook.py` | gera o notebook Colab pronto para a pontuação em GPU |
| `prep_brca2_structural.py` | prepara as entradas estruturais de BRCA2 para o PyMOL |

## 2. Resultado principal e robustez

| Script | Produz |
| --- | --- |
| `validate_domain_integration.py` | AUC do carro-chefe sob CV bloqueada e coortes externas |
| `prime_hypothesis_rigorous_test.py` | a refutação documentada da hipótese dos primos |
| `per_cohort_flagship.py` | desempenho coorte a coorte (Tabela 4) |
| `monte_carlo_flagship.py` | 500 divisões bloqueadas por posição (Figura S15) |
| `monte_carlo_robustness.py` | bootstrap, permutação, CV repetida e calibração |
| `meta_analysis.py` | meta-análise de efeitos aleatórios entre as coortes externas |
| `structural_features_test.py` | características estruturais contínuas vs. fronteira rígida de domínio |
| `evaluate_esm.py` | o ESM-2 agrega ao modelo consciente de domínio? |

## 3. Comparação com o estado da arte

| Script | Produz |
| --- | --- |
| `benchmark_sota.py` | AUC e DeLong contra AlphaMissense, REVEL e CADD (Tabela 5, Figura S1) |
| `benchmark_leakage_controlled.py` | a comparação criteriosa, com o vazamento a favor de terceiros explicitado (Figura 4) |
| `leakagefree_benchmark.py` | head-to-head em variantes que nenhuma ferramenta pôde ter visto |
| `eve_metrics_benchmark.py` | AUPRC/MCC e o comparador não circular (EVE) |
| `meta_classifier.py` | integração calibrada dos quatro sinais (Tabela S2) |
| `benchmark_figure.py` | figura das curvas ROC sobrepostas |

## 4. Tradução clínica

| Script | Produz |
| --- | --- |
| `acmg_calibration.py` | limiares PP3/BP4 por razão de verossimilhança (Figura S3) |
| `grey_zone_analysis.py` | complemento ao AlphaMissense onde ele se abstém (Figura 5) |
| `clinical_utility.py` | eficiência de triagem e curva de decisão (Figura S16) |
| `conformal_prediction.py` | incerteza por variante e abstenção segura (Figura S13) |
| `vus_worklist.py` | o backlog de VUS convertido em worklist acionável (Figura S14) |
| `generate_evidence_resource.py` | evidência pré-computada para todas as ~100 mil missense possíveis |

## 5. Validação prospectiva e temporal

| Script | Produz |
| --- | --- |
| `prospective_analysis.py` | **análise canônica**: prevê as reclassificações de 2023 a 2026 (Figura 7) |
| `reclassification_prospective.py` | versão anterior do mesmo teste, mantida por rastreabilidade |
| `temporal_validation.py` | validação por corte temporal ano a ano (Tabela 7) |
| `continual_learning_demo.py` | aprendizado contínuo com trava de segurança (Figura 6) |
| `build_prospective_registry.py` | registro datado e imutável de predições, falsificável no futuro |

## 6. Mecanismo, função e explicabilidade

| Script | Produz |
| --- | --- |
| `functional_validation.py` | validação contra ensaios funcionais do MaveDB (Figura S4) |
| `mechanism_vs_function.py` | o mecanismo previsto acompanha a função medida? (Figura S9) |
| `mechanism_domains.py` | decomposição de mecanismo nos domínios críticos (Figura S7) |
| `mechanism_analysis.py` | versão inicial, restrita ao BRCA1 |
| `detected_mutations_analysis.py` | quais mutações reais o algoritmo detecta |
| `shap_explain.py` | explicabilidade por valores de Shapley (Figura S10) |

## 7. Generalização e equidade

| Script | Produz |
| --- | --- |
| `multigene_panel.py` | generalização para TP53, ATM, PALB2 e CHEK2 (Figura S12) |
| `multigene_panel_expanded.py` | Lynch, VHL e MEN2 com rótulos reais (Figura S12b) |
| `equity_analysis.py` | lacuna de resolução entre ancestralidades (Figura S8) |

## 8. Figuras e renders 3D

Os renders exigem **PyMOL open-source**; os scripts `compose_*` apenas montam as
imagens já renderizadas, e rodam com Python comum.

| Script | Produz |
| --- | --- |
| `figures_disease.py` | mecanismo da doença (Figura 1) |
| `figures_domains.py` | arquitetura de domínios (Figura 2) |
| `figures_structures.py` | estruturas experimentais dos alvos |
| `pymol_detected_panel.py`, `compose_detected_panel.py` | seis variantes patogênicas reais (Figura 3) |
| `pymol_brca2_panel.py`, `compose_brca2_panel.py` | o mesmo para BRCA2 |
| `pymol_detection_maps.py`, `compose_detection_figures.py` | mapas de detecção por resíduo em BRCA1 |
| `pymol_domain_surface.py`, `compose_domain_surface.py` | superfície molecular dos domínios |
| `pymol_vhl_detection.py`, `pymol_panel_detection.py`, `compose_detection_maps.py` | mapas de VHL, MSH2 e RET (Figuras S12c a S12e) |
| `render_vhl_detection.py` | trilha de detecção por resíduo do VHL, consumida pelo PyMOL |
| `pymol_variants_found.py`, `compose_variants_figure.py` | as duas variantes emblemáticas em 3D |
| `pymol_render.py`, `pymol_hero_render.py`, `compose_hero_cover.py` | renders de destaque visual |

## 9. Proveniência e auditoria

| Script | Produz |
| --- | --- |
| `build_provenance_manifest.py` | manifesto SHA-256 de todo o conteúdo versionado |
| `rigor_audit.py` | auditoria adversarial das alegações do artigo |
| `build_final_manuscript.py` | monta a **versão base** do manuscrito. Não reproduz o artigo submetido: leia o aviso no cabeçalho do arquivo antes de executar |

---

## Convenções

- Sementes aleatórias fixas: as execuções são determinísticas.
- Nenhum script fabrica dados. Todo número vem de fonte pública (ClinVar, gnomAD,
  UniProt, RCSB PDB, Ensembl VEP, MaveDB) ou de cálculo sobre elas.
- Rótulos clínicos passam por `primevarclass.core.clinvar_binary_label`, ponto
  único de interpretação das classificações do ClinVar.
- Dados brutos ficam em `data/raw/` e não são versionados; os scripts de `fetch_*`
  os recriam.
