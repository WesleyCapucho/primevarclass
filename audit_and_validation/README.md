# PrimeVarClass - Auditoria e Validação

Este diretório contém os scripts e os conjuntos de dados utilizados para a validação empírica e auditoria preditiva do **PrimeVarClass**, um Sistema de Suporte a Decisão Clínica baseado no *Prime Encoding*.

## Estrutura

- **`data/`**: Contém os logs e datasets de auditoria gerados durante o processo. Aqui estão os arquivos `.csv` (como `alphafold_integrated_audit.csv`, `massive_integrated_audit.csv`, e `true_empirical_audit.csv`) que comprovam as métricas do modelo e as correlações preditivas (e.g., Prime Gap vs. Distância de Grantham).
- **`scripts/`**: Contém os algoritmos de validação.
  - `massive_validation.py` / `mavedb_massive_validation.py`: Scripts usados para rodar validação externa nas bases DMS.
  - `empirical_grounding.py`: Script responsável pelo cálculo da distância de Grantham vs Prime Gap.
  - `alphafold_structural_grounding.py`: Script para cruzar coordenadas estruturais (pLDDT, RSA) com o impacto de variações.

## Reprodutibilidade e Auditoria
Todos os dados e métodos usados para atingir as métricas citadas no artigo final (AUC de 0,822 OOF e AUC > 0.93 para os painéis de especialistas ClinVar) estão codificados e estruturados nos scripts desta pasta. 
Para auditar a matriz preditiva, consulte os arquivos dentro de `data/`.

## Manuscrito Final
A versão compilada oficial do artigo em formato DOCX (25 páginas, Normas ABNT, com as respectivas análises SHAP e mapas tridimensionais) encontra-se no caminho:
`docs/manuscripts/PrimeVarClass_Artigo_Final_ABNT_v3.docx`
