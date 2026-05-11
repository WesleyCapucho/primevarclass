# PrimeVarClass - campanha de evidências reais para o Prêmio Jovem Cientista

Gerado em: 2026-05-10

## Objetivo

Construir um pacote de evidências reais, auditáveis e reutilizáveis para sustentar a candidatura da PrimeVarClass ao Prêmio Jovem Cientista e preparar material para artigo científico.

O foco desta campanha é demonstrar que a plataforma não é apenas uma interface ou uma hipótese conceitual. Ela já integra dados públicos reais, executa validação externa, registra independência de coortes, explora generalização multigênica e organiza evidências funcionais, estruturais, translacionais e metodológicas.

## Evidência 1: benchmark BRCA com dados reais

Pasta: `primevarclass_jovem_cientista_evidence_20260510/brca_real_quick`

Configuração usada: `configs/jovem_cientista_brca_evidence_quick.toml`

Fontes reais envolvidas:

- ClinVar `variant_summary`.
- BRCA Exchange / ENIGMA.
- gnomAD r4 via GraphQL preparado previamente.
- MaveDB dump público.

Coortes:

- Treino BRCA público: 869 variantes.
- Validação externa ClinVar expert BRCA1: 204 variantes.
- Validação externa ClinVar expert BRCA2: 175 variantes.
- Validação externa BRCA Exchange/LOVD BRCA1: 168 variantes.
- Validação externa BRCA Exchange/LOVD BRCA2: 289 variantes.

Resultados principais:

- Melhor experimento interno: `hybrid_plus_external__logistic_regression`.
- AUC-ROC interno: 0.8089.
- AUC-PR interno: 0.5676.
- MCC interno: 0.4039.
- Independência de coortes: 100%.
- Maior sobreposição treino/externo: 0%.
- Freeze de coortes reais: 100%.

Validação externa:

- ClinVar expert BRCA1: AUC-ROC 0.9223, AUC-PR 0.8640, MCC 0.6170.
- ClinVar expert BRCA2: AUC-ROC 0.7764, AUC-PR 0.5427, MCC 0.4173.
- BRCA Exchange/LOVD BRCA2: AUC-ROC 0.7509.
- BRCA Exchange/LOVD BRCA1: AUC-ROC 0.5904.

Comparação contra baseline externo:

- BRCA2 LOVD: ganho de AUC-ROC de 0.5175 sobre `external_predictors_only__logistic_regression`.
- ClinVar expert BRCA1: ganho de AUC-ROC de 0.1704.
- ClinVar expert BRCA2: ganho de AUC-ROC de 0.1376.
- BRCA1 LOVD: resultado ainda instável, com delta negativo pequeno e intervalo amplo.

Interpretação:

- A campanha produziu evidência real forte para BRCA em coortes independentes.
- O resultado é especialmente forte em ClinVar expert BRCA1 e BRCA2.
- O desempenho em BRCA1 LOVD precisa de análise de erro, revisão de distribuição de classes e possível enriquecimento funcional/estrutural.
- A camada prime aparece como componente relevante quando integrada ao modelo híbrido, mas deve continuar sendo testada por ablação em todos os estudos.

## Evidência 2: generalização multigênica real

Pasta de referência: `primevarclass_multigene_real_benchmark_results`

Genes avaliados:

- TP53.
- PTEN.
- MSH2.
- KRAS.
- GCK.
- F9.

Resumo do benchmark já existente:

- Linhas de treino: 580.
- Linhas externas combinadas: 978.
- Genes-alvo: 6.
- Genes com rodada externa concluída ou dados fortes: 5.
- Progresso médio por gene: 76%.
- AUC-ROC externa média: 72.9%.
- Balanced score externo médio: 58.7%.
- Força de alegação: 67%.
- Sinal prime multigênico: 55%.

Interpretação:

- A plataforma já ultrapassou BRCA e iniciou generalização real em genes clinicamente relevantes.
- O resultado ainda não é prova final para todos os genes, mas é uma excelente base para demonstrar escalabilidade científica.
- PTEN e KRAS permanecem como pontos prioritários por limitação de balanceamento de classes.

## Evidência 3: staging de fontes públicas independentes

Pasta: `primevarclass_jovem_cientista_evidence_20260510/independent_public_sources`

Resultado:

- Prontidão de autostaging: 100%.
- Fontes staged: 10 de 10.

Valor para a competição:

- Demonstra que a plataforma consegue se conectar a fontes abertas relevantes.
- Fortalece a narrativa de IA para o bem comum, porque usa ciência aberta, dados públicos e reprodutibilidade.
- Ajuda a transformar a plataforma em infraestrutura científica, não apenas em um classificador isolado.

## Evidência 4: fechamento de staging independente

Pasta: `primevarclass_jovem_cientista_evidence_20260510/independent_staging_closure`

Resultado:

- Fechamento de staging: 94%.
- Execução real em nível de linha: 91%.
- Fontes prontas: 14 de 16.
- Pronta para próxima rodada de treino: sim.
- Pronta para retreinamento independente completo: ainda não.

Fontes prontas:

- ClinVar.
- ClinGen Evidence Repository.
- BRCA Exchange / ENIGMA.
- gnomAD.
- UniProt.
- AlphaFold DB.
- RCSB PDB.
- CIViC.
- cBioPortal.
- NCI GDC.
- GWAS Catalog.
- Open Targets.
- PharmGKB / ClinPGx.
- LOVD.

Fontes pendentes:

- MaveDB está parcial.
- AlphaMissense ainda está ausente.

Interpretação:

- A plataforma está muito próxima de uma rodada independente ampliada.
- O gargalo principal agora não é arquitetura, mas completar fontes funcionais/preditivas em nível de linha para todos os genes.

## Evidência 5: prontidão técnica e documentação

Pacotes já existentes:

- `primevarclass_launch_readiness_results`.
- `primevarclass_validation_credibility_closure_results`.
- `primevarclass_prospective_validation_closure_results`.
- `docs/pdf/manual_usuario.pdf`.
- `docs/pdf/glossario_primevarclass.pdf`.

Indicadores:

- Prontidão web: 100%.
- Prontidão geral de lançamento: 96%.
- Prontidão para preprint computacional: 95%.
- Prontidão para pacote de validação externa: sim.
- Pronto para afirmação terapêutica definitiva: não.

Interpretação:

- A plataforma pode ser apresentada como produto científico web em estágio piloto.
- Para artigo forte e competição, a narrativa deve afirmar priorização, geração de hipóteses e validação computacional, não validade clínica final.

## Próximas etapas críticas

1. Rodar a campanha BRCA completa em modo longo.

Objetivo: repetir o benchmark com `random_forest`, `extra_trees` e mais bootstrap para métricas finais do artigo.

Motivo: a rodada rápida já gerou evidência, mas a versão completa é melhor para publicação.

2. Completar MaveDB e AlphaMissense em nível de linha.

Objetivo: elevar staging independente de 94% para mais perto de 100%.

Motivo: fontes funcionais e preditivas reforçam a explicação biológica e o comparativo com métodos consolidados.

3. Atualizar o benchmark multigênico com gnomAD/MaveDB linha a linha.

Objetivo: aumentar a força de alegação multigênica além de 67%.

Motivo: vencer competição exige mostrar que a plataforma generaliza, não que funciona apenas em BRCA.

4. Fazer análise de erro do BRCA1 LOVD.

Objetivo: explicar por que esse holdout externo teve desempenho menor.

Motivo: reconhecer e investigar falhas aumenta credibilidade científica.

5. Priorizar top variantes para confirmação funcional/estrutural.

Objetivo: transformar resultados computacionais em hipóteses experimentais testáveis.

Motivo: isso é o salto de “boa IA” para “impacto científico real”.

## Tese competitiva

PrimeVarClass é uma plataforma brasileira de IA translacional que integra dados genéticos reais, evidência funcional, estrutura proteica, módulos quânticos e uma codificação matemática baseada em números primos para priorizar variantes missense de forma interpretável, auditável e expansível para múltiplos genes.

O diferencial competitivo não é apenas classificar variantes. O diferencial é organizar um ecossistema de evidência que conecta ciência aberta, IA responsável, validação externa, hipótese mecanística e potencial impacto social em saúde.

## Limite honesto da alegação

A plataforma já tem evidência computacional real e está pronta para piloto web e preprint computacional. Ainda não deve afirmar validade clínica, eficácia terapêutica ou descoberta causal definitiva sem confirmação funcional, estrutural e experimental independente.

## Atualização automática da campanha

Atualizado em: 2026-05-11T00:11:12Z

### Análise de erro BRCA1 LOVD

- Relatório: `primevarclass_jovem_cientista_evidence_20260510\brca1_lovd_error_analysis\brca1_lovd_error_analysis.md`
- Variantes analisadas: `168`
- Erros no modelo selecionado: `32`
- Falsos positivos: `15`
- Falsos negativos: `17`

### Plano AlphaMissense

- Plano: `primevarclass_jovem_cientista_evidence_20260510\alphamissense_subset_plan\alphamissense_subset_plan.md`
- Configuração pronta: `primevarclass_jovem_cientista_evidence_20260510\alphamissense_subset_plan\alphamissense_target_gene_source_config.toml`
- Extrator streaming pronto: `scripts\extract_alphamissense_subset.py`
- Status: preparado para subset seguro; download completo não foi iniciado para não travar a máquina.

### Enriquecimento multigênico atualizado

- Relatório: `primevarclass_jovem_cientista_evidence_20260510\multigene_annotation_enrichment_refresh\multigene_annotation_enrichment_report.md`
- Variantes multigênicas avaliadas: `1668`
- Cobertura de coordenadas GRCh38: `100%`
- Cobertura MaveDB linha a linha: `90%`
- Prontidão da matriz multigênica antes do sync cacheado: `62%`
- Interpretação: a evidência funcional já é forte para TP53, F9, MSH2 e GCK; KRAS e PTEN seguem como alvos de reforço.

### Sync público gnomAD/MaveDB atualizado

- Relatório: `primevarclass_jovem_cientista_evidence_20260510\public_sync_closure_refresh\public_sync_closure_report.md`
- Variantes multigênicas com gnomAD queryable: `100%`
- Tentativas gnomAD cacheadas: `100%`
- Variantes encontradas no gnomAD/cache local: `547`
- Cobertura MaveDB por HGVS proteico: `90%`
- Prontidão efetiva linha a linha: `98%`
- Public sync closure: `99%`
- Interpretação: a plataforma agora tem trilha retomável e auditável para gnomAD/MaveDB, reduzindo o risco de depender de consultas manuais.

### Credibilidade e validação prospectiva recalculadas

- Relatório de credibilidade: `primevarclass_jovem_cientista_evidence_20260510\validation_credibility_refresh\validation_credibility_closure_report.md`
- Fechamento de evidência de software: `93%`
- Credibilidade científica: `88%`
- Evidência pública linha a linha: `98%`
- Relatório prospectivo: `primevarclass_jovem_cientista_evidence_20260510\prospective_validation_refresh\prospective_validation_protocol.md`
- Fila funcional/estrutural: `primevarclass_jovem_cientista_evidence_20260510\prospective_validation_refresh\functional_structural_confirmation_queue.csv`
- Interpretação: a plataforma está pronta para validação externa mais forte, mas confirmação funcional/experimental ainda é o limite honesto para alegações definitivas.
