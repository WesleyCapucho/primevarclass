# Projeto cientifico

## Visao

PrimeVarClass busca investigar se uma representacao numerica baseada em numeros primos pode melhorar a classificacao de variantes missense em `BRCA1` e `BRCA2`, especialmente no contexto de VUS e da evidencia computacional PP3/BP4.

## Problema central

- Variantes missense em BRCA1/2 continuam dificeis de interpretar.
- Preditores in silico existentes nem sempre concordam entre si.
- Muitas variantes permanecem em faixa nao informativa para uso clinico.

## Hipotese de trabalho

Uma codificacao prima que combine propriedades de codons, massa prima e sinais bioquimicos pode capturar informacao funcional complementar aos preditores tradicionais.

## Objetivos do software

1. Curar datasets BRCA1/2 com classes confiaveis.
2. Gerar features baseadas em numeros primos e propriedades bioquimicas.
3. Treinar modelos tabulares interpretaveis para classificacao binaria.
4. Calibrar scores em faixas compatveis com PP3/BP4.
5. Exportar resultados reprodutiveis para analise, relatorio e futura publicacao.

## Fases previstas

### Fase 1. Codificacao prima

- Comparar os modos `codon`, `prime_mass` e `hybrid`.
- Revisar o racional biologico de cada encoding.
- Medir estabilidade das features derivadas.

### Fase 2. Curadoria de dados

- Consolidar ClinVar com filtros de confianca.
- Excluir VUS, conflitos e variantes nao missense.
- Preparar campos opcionais de conservacao, estrutura e preditores externos.

### Fase 3. Modelagem

- Rodar experimentos com subconjuntos de features.
- Comparar desempenho entre abordagens prime-only, hybrid e hybrid-plus-external.
- Expandir depois para gradient boosting e modelos gene-especificos.

### Fase 4. Calibracao

- Gerar tabelas de likelihood ratio por bins de score.
- Mapear bins informativos para niveis PP3/BP4.
- Medir cobertura de regioes informativas e nao informativas.

### Fase 5. Validacao comparativa

- Benchmark com REVEL, BayesDel, AlphaMissense e CADD.
- Validacao com dados funcionais e coortes independentes.
- Analise por gene, dominio funcional e tipo de substituicao.

## Entregaveis

- Pacote Python instalavel
- CLI para processamento e treino
- Camada de conectores para arquivos, bancos locais e endpoints remotos
- Tabelas exportadas para metricas, importancia de features e calibracao
- Relatorio interpretavel em texto
- Base pronta para evoluir para API web e pacote R

## Proximos passos recomendados

1. Criar uma camada de ingestao para ClinVar e arquivos externos.
2. Versionar datasets curados e metadados de origem.
3. Adicionar benchmark automatizado contra preditores externos.
4. Incluir notebooks ou scripts de analise estatistica para figuras do artigo.
5. Preparar uma interface web simples para uso exploratorio do laboratorio.

## Arquitetura de dados recomendada

- Fontes de coorte: ClinVar, ENIGMA, BRIDGES ou tabelas internas com rotulo.
- Fontes de anotacao: gnomAD, MAVE, scores estruturais, bancos locais de features.
- Chaves canonicas: `gene` e `hgvs_p`.
- Estrategia: concatenar coortes, deduplicar variantes e depois enriquecer com anotacoes por merge controlado.
- Reprodutibilidade: toda combinacao de fontes deve ser descrita em arquivo TOML versionado no repositorio.
