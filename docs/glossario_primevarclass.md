# PrimeVarClass - Glossário

Versão: 2026.05

Este glossário explica os termos mais importantes da plataforma em linguagem acessível. A ideia é ajudar tanto usuários iniciantes quanto pesquisadores experientes a interpretar resultados com precisão.

## ACMG/AMP

Conjunto de diretrizes usado para interpretar variantes genéticas. A plataforma pode apoiar a organização de evidências, mas não substitui a curadoria ACMG/AMP formal.

Exemplo: uma variante pode ter alta probabilidade no modelo, mas ainda precisar de critérios ACMG/AMP antes de qualquer interpretação clínica.

## AlphaFold DB

Banco de modelos estruturais preditos de proteínas. No PrimeVarClass, ajuda a localizar a região da proteína onde uma variante ocorre.

Limite: AlphaFold é predição estrutural, não estrutura experimental.

## AlphaMissense

Preditor externo de efeitos de variantes missense. Pode ser usado como comparação independente contra o PrimeVarClass.

Uso correto: comparar concordâncias e discordâncias, não tratar como verdade final.

## API

Interface programável que permite que outros sistemas conversem com a plataforma. No PrimeVarClass, a API é baseada em FastAPI.

Exemplo: a interface web chama endpoints da API para classificar variantes, gerar relatórios e consultar prontidão.

## API key

Chave de acesso usada para proteger a plataforma quando ela é exposta em rede.

Boa prática: nunca publique a chave em artigo, print, repositório ou captura de tela.

## Área ativa

Módulo selecionado na interface. A plataforma foi dividida em módulos para evitar excesso de informação na tela.

## Baseline

Modelo ou método de comparação. Serve para saber se uma abordagem nova realmente melhora algo.

Exemplo: comparar o modelo prime contra logistic regression, random forest sem features prime ou preditores externos.

## Benchmark congelado

Estudo em que dados, splits, parâmetros, thresholds e métricas são definidos antes da avaliação.

Por que importa: reduz vazamento, overfitting e interpretação oportunista.

## BRCA Exchange

Base especializada em variantes BRCA1 e BRCA2. É útil para validação e comparação em câncer hereditário de mama e ovário.

## cBioPortal

Plataforma com dados de coortes tumorais. No PrimeVarClass, ajuda a conectar genes e variantes ao contexto oncológico.

Limite: dado somático tumoral não deve ser confundido automaticamente com evidência germinativa de patogenicidade.

## ClinGen ERepo

Repositório de evidências e classificações de grupos especialistas. É importante para validação externa e curadoria independente.

## ClinVar

Base pública de variantes genéticas e interpretações clínicas submetidas por laboratórios e grupos especialistas.

Limite: ClinVar pode conter conflitos, diferentes níveis de revisão e submissões antigas.

## Coorte

Conjunto de variantes, pacientes, amostras ou registros usados em uma análise.

Exemplo: coorte de treino, coorte externa, coorte BRCA, coorte TP53.

## Confirmação experimental

Evidência gerada por ensaio funcional, estrutural, biofísico, celular ou molecular.

Por que importa: transforma hipótese computacional em evidência biológica mais forte.

## Controle não-prime

Modelo, inicialização ou conjunto de features que não usa a camada de números primos.

Por que importa: permite saber se os números primos agregam valor real.

## Coordenada GRCh38

Posição genômica no genoma de referência GRCh38.

Uso: necessária para consultar corretamente gnomAD e outras fontes populacionais.

## Curadoria

Revisão especializada de evidências. Pode ser clínica, funcional, estrutural ou computacional.

## Dado real

Dado obtido de banco público, release oficial, experimento, coorte ou arquivo curado, em oposição a dados demonstrativos.

## Dado sintético

Dado criado artificialmente para teste, demonstração ou desenvolvimento.

Limite: útil para validar software, mas insuficiente para claims científicos fortes.

## DFT

Density Functional Theory. Método de química quântica usado para estimar propriedades energéticas e eletrônicas.

Uso no PrimeVarClass: etapa mais forte que xTB para investigar fragmentos priorizados.

## Docking

Simulação de encaixe entre molécula e proteína.

Uso: gerar hipóteses de interação ligante-proteína.

Limite: docking não prova eficácia farmacológica.

## Evidência funcional

Informação que mede ou sugere impacto da variante na função biológica.

Exemplo: MAVE/DMS, ensaio celular, transativação, estabilidade ou atividade enzimática.

## Evidência interpretável

Qualquer informação que ajude o usuário a entender por que uma variante foi priorizada.

Exemplos: raridade no gnomAD, conservação, score MAVE, região estrutural, domínio funcional, assinatura prime.

## Feature

Variável usada pelo modelo.

Exemplo: frequência gnomAD, score MAVE, conservação evolutiva, distância prime, curvatura prime.

## Fingerprint

Resumo técnico de um arquivo ou artefato, geralmente com hash, tamanho e data.

Uso: garantir rastreabilidade e reprodutibilidade.

## GDC

Genomic Data Commons do NCI. Fonte de dados genômicos ligados a câncer.

## Gene

Região do DNA que codifica ou regula um produto funcional. Na plataforma, o gene é a unidade principal para agrupar variantes e evidências.

## Generalização multigênica

Capacidade do método de funcionar além de um único gene.

Exemplo: sair de BRCA1/BRCA2 e avaliar TP53, PTEN, MSH2, KRAS, GCK e F9.

## gnomAD

Genome Aggregation Database. Banco de frequências populacionais.

Interpretação: frequência muito alta pode contradizer patogenicidade forte para doença rara, mas frequência baixa não prova patogenicidade.

## GWAS Catalog

Banco de associações genéticas entre variantes, regiões ou genes e fenótipos.

Uso: contexto de plausibilidade biológica e relação gene-doença.

## HGVS proteico

Nomenclatura padronizada para alteração em proteína.

Exemplo: `p.Cys61Gly` significa troca de cisteína por glicina na posição 61.

## Holdout externo

Conjunto de dados separado do treino e usado para avaliar generalização.

## Interface modular

Organização da tela em módulos selecionáveis. Evita excesso de informação e reduz erro de uso.

## Label

Rótulo usado para treinar ou avaliar o modelo.

Exemplos: benigno, patogênico, VUS, funcional, não funcional.

## LOVD

Leiden Open Variation Database. Conjunto de bases locus-específicas de variantes.

## Manifesto

Arquivo JSON que registra caminhos, parâmetros, fontes, versões, hashes e artefatos.

Por que importa: permite repetir, auditar e publicar o estudo com transparência.

## MAVE

Multiplexed Assay of Variant Effect. Ensaio de alto rendimento que mede efeitos de muitas variantes.

## MaveDB

Repositório público de estudos MAVE.

Uso no PrimeVarClass: adicionar evidência funcional independente.

## Missense

Tipo de variante que troca um aminoácido por outro.

Exemplo: `p.Arg175His`.

## Modelo híbrido

Modelo que combina features prime e features biológicas, clínicas ou funcionais.

## Módulo quântico

Camada da plataforma voltada a investigação física e química de fragmentos, active spaces, VQE e comparação prime-guided.

## Números primos

Números divisíveis apenas por 1 e por eles mesmos.

No PrimeVarClass, são usados como base matemática para codificar aminoácidos, trocas, distâncias e padrões discretos.

Importância científica: a camada prime só deve ser considerada diferencial validado quando superar controles não-prime em experimentos justos.

## Open Targets

Plataforma de evidências gene-doença. Ajuda a conectar genes, fenótipos e contexto translacional.

## Overfitting

Quando um modelo aprende detalhes específicos do treino, mas falha em dados novos.

Sinal de risco: desempenho excelente no treino e fraco em coorte externa.

## PDB

Protein Data Bank. Banco de estruturas experimentais de proteínas.

Uso: reforçar interpretação estrutural quando existe estrutura relevante.

## PharmGKB

Base de conhecimento farmacogenômico. Ajuda a contextualizar genes e variantes em relação a fármacos e resposta terapêutica.

## Preflight

Checagem antes da execução principal.

Detecta arquivos ausentes, schema incompleto, risco de vazamento, dados insuficientes e problemas de reprodutibilidade.

## Prime-guided VQE

Uso de assinaturas baseadas em números primos para orientar inicialização, escolha de fragmentos, active-space seed ou estratégia de execução em VQE.

Controle obrigatório: comparar contra VQE com inicialização não-prime.

## Probabilidade do modelo

Saída numérica que indica a tendência do modelo para uma classe.

Limite: probabilidade não é diagnóstico.

## Proteômica estrutural

Camada que conecta variante, proteína, estrutura, domínio, interface e função.

## Reprodutibilidade

Capacidade de repetir uma análise com os mesmos dados, versões e parâmetros.

Ferramentas da plataforma: manifestos, fingerprints, relatórios, configs e logs.

## Shadow pilot

Piloto em que a plataforma roda em paralelo ao processo humano, sem influenciar decisão final.

Uso: medir segurança, clareza e utilidade antes de adoção real.

## Split

Divisão dos dados em treino, validação, teste ou coorte externa.

## Staging

Processo de colocar dados em local padronizado, com formato e rastreabilidade prontos para uso.

## Threshold

Limiar usado para converter probabilidade em classe.

Boa prática: definir antes da avaliação externa.

## Trilhas de auditoria

Registros de ações, execuções, usuários, endpoints e resultados.

## UniProt

Base de conhecimento sobre proteínas. Fornece acessions, comprimento, domínios, função e anotações.

## Validação independente

Avaliação em dados não usados no desenvolvimento do modelo.

## Validação prospectiva

Avaliação em dados futuros ou separados temporalmente, idealmente definidos antes da análise.

## VQE

Variational Quantum Eigensolver. Algoritmo híbrido quântico-clássico para estimar energia de sistemas simplificados.

## VUS

Variant of Uncertain Significance. Variante de significado incerto.

Importante: VUS não deve ser tratada como benigna ou patogênica sem evidência adicional.

## xTB

Método semiempírico rápido para triagem química e estrutural.

Uso: etapa inicial antes de cálculos mais caros como DFT.

## Acionabilidade

Grau em que uma evidência pode orientar uma ação prática de pesquisa, validação experimental, priorização translacional ou investigação terapêutica.

Importante: acionabilidade na plataforma não significa recomendação clínica automática.

## Ambiente autenticado

Modo de uso em que a plataforma exige identificação por chave da API, usuário, equipe ou outro mecanismo de autenticação.

Uso: necessário quando a plataforma opera em contexto multiusuário, web ou colaborativo.

## Ambiente local

Modo de uso em que a plataforma roda na própria máquina ou em ambiente interno de desenvolvimento.

Uso: adequado para testes, demonstrações, validação inicial e trabalho privado.

## Aminoácido

Unidade básica que compõe proteínas. Cada aminoácido possui propriedades químicas, como carga, tamanho, polaridade e hidrofobicidade.

Relação com variantes: uma mutação missense troca um aminoácido por outro e pode alterar estabilidade, função, interação ou estrutura da proteína.

## Anotação

Informação adicionada a uma variante, gene ou proteína para facilitar interpretação.

Exemplos: frequência populacional, efeito funcional, domínio proteico, classificação clínica, escore computacional e evidência estrutural.

## Arquivo de entrada

Arquivo fornecido pelo usuário ou por uma rotina automática para iniciar uma análise.

Exemplos: lista de variantes, arquivo de configuração, manifesto, tabela de features ou dataset público processado.

## Artefato

Qualquer arquivo produzido ou usado pela plataforma durante uma análise.

Exemplos: modelo treinado, relatório, manifesto, log, gráfico, tabela de resultados, configuração e pacote de estudo.

## Autenticação desativada

Estado em que a plataforma permite uso local sem exigir chave da API.

Uso: comum em desenvolvimento, validação local e demonstração controlada.

## Autopreencher entrega

Ação que completa automaticamente campos de entrega, handoff ou empacotamento de resultados.

Uso: reduz erro manual ao preparar dados para revisão, validação ou transferência para outra etapa.

## Bases nitrogenadas

Componentes químicos do DNA e RNA. No DNA, as bases principais são adenina, timina, citosina e guanina.

Relação com a plataforma: variantes genéticas começam como mudanças em bases e podem resultar em alterações de aminoácidos nas proteínas.

## Bioengenharia

Área que integra biologia, engenharia, computação e tecnologia para estudar, projetar ou modificar sistemas biológicos.

Relação com a plataforma: o PrimeVarClass usa dados biológicos e computacionais para orientar hipóteses de validação e intervenção.

## Cache do navegador

Armazenamento local usado pelo navegador para acelerar carregamento de páginas, estilos e scripts.

Problema comum: após atualização da interface, o navegador pode mostrar versão antiga. A solução geralmente é atualizar com `Ctrl+F5`.

## Caminho do arquivo

Endereço local ou relativo que indica onde um arquivo está salvo.

Exemplos: diretório dos modelos, diretório de saída, caminho do manifesto e caminho do dataset.

## Catálogo público real

Fonte pública de dados científicos usada para consulta, treino, validação ou enriquecimento de evidências.

Exemplos: ClinVar, gnomAD, MaveDB, UniProt, PDB, AlphaFold DB, Open Targets, PharmGKB e GWAS Catalog.

## Chave da API

Código usado para autenticar uma requisição ou identificar um usuário autorizado.

Cuidados: não compartilhe em imagens, relatórios públicos, repositórios ou mensagens abertas.

## Codificação por primos

Representação matemática que utiliza propriedades dos números primos para transformar informações biológicas em sinais computacionais.

Objetivo: criar uma camada de representação diferente das codificações tradicionais e testá-la contra controles não-prime.

## Códon

Sequência de três bases no DNA ou RNA que codifica um aminoácido ou sinal de parada.

Relação com missense: uma troca de base pode alterar um códon e trocar o aminoácido resultante.

## Console

Área ou retorno textual que mostra mensagens de execução, status, erro, aviso ou saída técnica.

Uso: ajuda a diagnosticar se uma tarefa rodou corretamente.

## Controle experimental

Comparação usada para verificar se um resultado é específico do método testado ou poderia aparecer por acaso.

Na plataforma: controles não-prime, baselines tradicionais e comparações entre referência e mutante são exemplos de controle.

## Dados públicos

Dados disponibilizados por instituições, consórcios, repositórios ou bases científicas.

Importante: público não significa perfeito. Cada fonte tem versão, escopo, viés, critérios e limitações.

## Diretório de saída

Pasta em que a plataforma grava resultados.

Exemplos de conteúdo: relatórios, manifestos, logs, métricas, gráficos e pacotes de análise.

## Diretório dos modelos

Pasta em que ficam os modelos treinados e seus arquivos auxiliares.

Se o caminho estiver incorreto, a plataforma pode abrir normalmente, mas falhar ao executar inferência.

## Dry-run

Execução de teste que verifica o fluxo sem executar toda a análise pesada ou definitiva.

Uso: útil para checar configuração, caminhos, credenciais e formato dos dados.

## Enfileirar

Adicionar uma tarefa à fila de execução.

Exemplos: enfileirar treino, validação, sincronização de dados públicos ou geração de relatório.

## Engine

Motor computacional que executa uma tarefa específica.

Exemplos: engine de inferência, engine estrutural, engine quântica, engine de sincronização pública e engine de benchmark.

## Escore

Valor numérico produzido por modelo, banco de dados ou método computacional.

Exemplos: probabilidade do modelo, escore funcional MAVE, frequência alélica, conservação evolutiva e energia estimada.

## Estudo publicável

Análise organizada com pergunta científica, dados rastreáveis, método documentado, controles, métricas, limitações e resultados reproduzíveis.

Uso: etapa mais forte que uma demonstração exploratória.

## Feedback

Registro enviado por usuário para comunicar erro, dúvida, sugestão ou avaliação de experiência.

Bom feedback inclui módulo, entrada usada, resultado esperado, resultado observado e mensagem de erro.

## Fila de jobs

Lista de tarefas aguardando execução ou processamento.

Uso: importante para plataformas multiusuário, análises longas e rotinas automáticas.

## Guia de feedback

Material que explica como relatar problemas e sugestões de forma útil para a equipe de desenvolvimento.

Objetivo: facilitar melhoria contínua e reduzir retrabalho.

## Handoff

Entrega organizada de dados, resultados ou artefatos de uma etapa para outra pessoa, módulo ou processo.

Exemplo: pacote com manifesto, resultados e logs entregue para validação independente.

## ID do perfil

Identificador associado ao perfil de uso ativo.

Uso: ajuda a separar análises locais, usuários, equipes ou contextos de execução.

## ID do time

Identificador associado à equipe ativa.

Uso: relevante para colaboração, auditoria, governança e plataforma multiusuário.

## Inferência interpretável

Predição acompanhada de explicações, evidências ou sinais que ajudam o usuário a entender por que o modelo produziu determinado resultado.

Importante: interpretável não significa infalível. A explicação também precisa ser conferida.

## Inferência interpretável com dados reais

Modo de análise que combina predição do modelo com evidências vindas de fontes públicas ou datasets reais.

Valor científico: fortalece a análise porque reduz dependência de dados sintéticos ou demonstrações isoladas.

## Job

Tarefa computacional executada pela plataforma.

Exemplos: predizer variante, sincronizar dados, treinar modelo, rodar benchmark, gerar PDF ou criar manifesto.

## Módulo

Área funcional da interface dedicada a uma parte da plataforma.

Exemplos: Início, Modelos, Predição, Equipe, Dados públicos, Estudos, Ciência, Impacto e Operação.

## Módulo Ciência

Área da plataforma voltada à validação, benchmark, controles, metodologia, reprodutibilidade e credibilidade científica.

Uso: essencial antes de afirmar que um resultado é robusto.

## Módulo Dados públicos

Área usada para consultar, sincronizar e registrar bases externas reais.

Uso: conecta a plataforma com evidências independentes.

## Módulo Estudos

Área usada para organizar análises reprodutíveis com pergunta, dataset, critérios, resultados e artefatos.

Uso: indicada para validação, artigo, relatório técnico e colaboração.

## Módulo Impacto

Área usada para traduzir resultados científicos em relevância social, translacional e experimental.

Uso: ajuda a conectar computação, biologia, saúde e benefício potencial.

## Módulo Modelos

Área usada para verificar modelos treinados, diretórios, versões e disponibilidade de inferência.

Uso: deve ser conferida antes de rodar predições importantes.

## Módulo Operação

Área usada para acompanhar status, jobs, incidentes, logs, auditoria e prontidão da plataforma.

Uso: essencial para ambiente multiusuário e lançamento web.

## Módulo Predição

Área usada para executar análise de variantes individuais ou em lote.

Uso: ponto central para gerar hipóteses computacionais.

## Multiusuário

Capacidade de uma plataforma ser usada por múltiplas pessoas com perfis, permissões, registros e contexto separados.

Importante: exige autenticação, auditoria, feedback, documentação e governança.

## Nucleotídeo

Unidade básica do DNA ou RNA, formada por base nitrogenada, açúcar e grupo fosfato.

Relação com variantes: alterações em nucleotídeos podem alterar códons e proteínas.

## Pacote de estudo

Conjunto organizado de arquivos necessários para revisar ou reproduzir uma análise.

Exemplos: configuração, manifesto, resultados, logs, métricas, figuras e relatório.

## Painel

Bloco visual da interface que agrupa informações ou ações relacionadas.

Exemplos: painel de status, painel de resultados, painel de equipe e painel de dados públicos.

## Perfil local

Perfil usado em ambiente local quando não há autenticação completa.

Uso: útil para desenvolvimento e validação inicial, mas menos robusto que identificação multiusuário completa.

## Prontidão web

Grau em que a plataforma está preparada para ser usada por usuários externos pela internet.

Inclui: autenticação, estabilidade, documentação, segurança, feedback, logs, acessibilidade e infraestrutura.

## Requisição

Pedido enviado pela interface ou por outro sistema para a API executar uma ação.

Exemplos: consultar modelo, predizer variante, baixar documento ou iniciar sincronização.

## Resultado observado

O que realmente aconteceu durante uma execução.

Uso: deve ser comparado ao resultado esperado ao enviar feedback ou diagnosticar erro.

## Resultado esperado

O que o usuário esperava que acontecesse durante uma execução.

Uso: ajuda a equipe a entender se houve erro, comportamento confuso ou problema de documentação.

## Sincronização pública

Processo de buscar, atualizar ou registrar dados de fontes públicas relevantes.

Uso: mantém a plataforma alinhada com bases científicas atualizadas.

## Status

Indicação do estado atual de uma tarefa, serviço ou módulo.

Exemplos: saudável, em execução, concluído, falhou, pendente, indisponível ou parcialmente configurado.

## Variante individual

Uma única alteração genética analisada isoladamente.

Uso: indicada para investigação pontual, ensino, triagem inicial ou estudo de caso.

## Variante sinalizada

Variante destacada pela plataforma por apresentar escore, evidência ou conflito que merece atenção.

Importante: sinalização é priorização, não conclusão definitiva.

## Workbench

Área principal de trabalho da plataforma, acessada em `/workbench`.

Uso: reúne os módulos operacionais e científicos em uma interface única.
