# Public data blueprint

## Objetivo

Este blueprint organiza um estudo BRCA de nivel publicavel em tres camadas:

- coorte rotulada para treinamento
- anotacoes populacionais e funcionais para enriquecimento
- catalogos versionados em TOML para reproducibilidade

## Fontes prioritarias

### ClinVar

- papel: coorte principal rotulada
- preset: `clinvar_variant_summary`
- saida esperada: `gene`, `hgvs_p`, `label`, `review_status`

### gnomAD

- papel: anotacao populacional
- preset: `gnomad_variant_table`
- features esperadas:
  - `feature_gnomad_af`
  - `feature_gnomad_ac`
  - `feature_gnomad_an`
  - `feature_gnomad_nhomalt`
  - `feature_gnomad_popmax_af`

### MaveDB

- papel: anotacao funcional independente
- preset: `mavedb_score_table`
- features esperadas:
  - `feature_mave_score`
  - `feature_mave_se`
  - `feature_mave_qvalue`
  - `feature_mave_pvalue`
  - `feature_mave_annotation`

## Catalogos prontos

- `configs/public_brca_example.toml`: exemplo executavel com arquivos locais real-like
- `configs/public_brca_study_template.toml`: template para um estudo publico real

## Versionamento de release por fonte

- Cada `[[sources]]` agora pode declarar `release_version` e/ou `release_date`.
- Quando esses campos nao sao preenchidos, o PrimeVarClass tenta inferir release automaticamente a partir do nome do arquivo, URL, ETag, Last-Modified e outros sinais de proveniencia.
- A ingestao exporta `public_source_catalog_report.json` e `public_source_catalog_report.md` com a cobertura de release e de esquema por fonte publica reconhecida.
- A ingestao tambem exporta `public_source_sync_plan.json` e `public_source_sync_plan.md`, com a receita recomendada de sincronizacao para cada fonte publica reconhecida.
- O endpoint `POST /public-sources/catalog/bootstrap` gera `public_source_bootstrap_manifest.json`, `public_source_bootstrap_guide.md` e `bootstrap_public_sources.ps1` para preparar a coleta local.
- Quando a fonte gnomAD aponta para uma tabela local ja exportada, o bootstrap consegue gerar um recorte BRCA controlado em `gnomad_brca_subset.tsv`, com manifest proprio de staging.
- Quando a fonte MaveDB declara `release_version = "urn:mavedb:..."`, o bootstrap consegue preparar o staging oficial via API para metadados do score set e `mapped_variants.json`.
- Quando a fonte ENIGMA aponta para um arquivo curado local, o bootstrap consegue preparar um staging auditavel da importacao em `enigma_curated_import.*`, com manifest proprio.
- O endpoint `POST /public-sources/catalog/inspect` e o painel "Catalogo publico real" na workbench ajudam a validar se o catalogo esta pronto para benchmark publicavel.
- O endpoint `POST /public-sources/catalog/resolve` gera um `resolved_source_config.toml`, preferindo artefatos staged quando eles existem e preservando arquivos locais versionados quando isso for mais confiavel.
- O endpoint `POST /study/public-config/resolve` gera um `resolved_study_config.toml` que aponta cada coorte para TOMLs congelados, reduzindo edicao manual de caminhos antes do benchmark final.
- Os endpoints `POST /study/public-run` e `POST /jobs/study/public-run` fecham o fluxo publico fim a fim: resolucao, preflight, benchmark e execution board em um unico pacote operacional.
- O benchmark final agora tambem exporta auditoria de independencia entre coortes, ajudando a detectar vazamento entre treino e validacao externa antes da interpretacao cientifica.
- O benchmark final agora tambem exporta `claim strength` e `validation lock`, o que deixa explicito se a rodada publica sustenta apenas hipotese, uma alegacao moderada ou uma narrativa forte de superioridade.
- O benchmark final agora tambem exporta `cohort freeze`, deixando claro se a rodada ainda depende de arquivos demo/example ou se ja esta congelada em coortes reais versionadas.
- A resolucao publica do estudo agora tambem exporta `real-data handoff`, que transforma os bloqueios restantes em tarefas acionaveis por coorte, fonte, prioridade e responsavel sugerido.

## Estrategia recomendada para artigo

1. Treino principal em ClinVar curado e filtrado.
2. Enriquecimento com frequencias populacionais do gnomAD.
3. Validacao biologica adicional com scores funcionais do MaveDB.
4. Benchmark externo com coortes independentes quando disponiveis.
5. Ablation study separando:
   - prime only
   - prime + bioquimica
   - prime + anotacoes externas
   - baselines sem codificacao prima

## Comando sugerido

```bash
primevarclass --source-config configs/public_brca_example.toml --output-dir primevarclass_results_public_brca
```

## Observacoes

- Nem toda base publica usa o mesmo formato de `hgvs_p`; os presets ajudam a normalizar isso.
- Variantes funcionais e populacionais entram como `feature_*`, ficando disponiveis automaticamente para os experimentos.
- Metadados de origem entram como `meta_*` e ficam fora dos subconjuntos de features para reduzir leakage.
