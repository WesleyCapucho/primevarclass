# PrimeVarClass - Manual do usuário

Versão: 2026.05

Este manual foi escrito para orientar usuários com níveis diferentes de experiência: estudantes de graduação, pesquisadores, bioinformatas, equipes translacionais e gestores científicos. A linguagem é direta, mas preserva os limites científicos necessários para usar a plataforma com responsabilidade.

## Como usar este manual

Se este for seu primeiro contato com a plataforma, siga a sequência abaixo. Ela foi pensada para levar um usuário iniciante do acesso inicial até uma análise interpretável sem precisar conhecer todos os detalhes técnicos de bioinformática, aprendizado de máquina ou computação quântica.

- Leia as seções 1 a 6 para entender o objetivo da plataforma, os limites de uso e a organização da interface.
- Execute o roteiro da seção 26 para fazer uma primeira navegação guiada em aproximadamente 30 minutos.
- Use a seção 27 como mapa prático dos módulos da plataforma.
- Consulte a seção 29 quando tiver dúvida sobre o que preencher em cada campo.
- Consulte a seção 30 para entender o significado dos cartões, listas, manifestos e relatórios gerados.
- Use a seção 34 como checklist antes de apresentar resultados em relatório, banca, prêmio, artigo ou reunião com colaboradores.
- Use o glossário sempre que encontrar um termo técnico novo na interface.

## 1. O que é o PrimeVarClass

PrimeVarClass é uma plataforma de pesquisa translacional para priorização, interpretação e validação computacional de variantes missense. Ela combina dados clínicos, populacionais, funcionais, estruturais, proteômicos, quânticos e uma camada matemática baseada em números primos.

Em termos simples: a plataforma ajuda a transformar uma variante genética em uma hipótese científica organizada. Ela não entrega uma verdade clínica final sozinha. Ela reúne evidências, executa modelos, compara resultados, mostra lacunas e gera artefatos para pesquisa reprodutível.

O diferencial central é a integração entre:

- Dados reais independentes, como ClinVar, gnomAD, MaveDB, BRCA Exchange/ENIGMA, ClinGen ERepo, UniProt, AlphaFold DB, PDB, CIViC, cBioPortal, GDC, GWAS Catalog, Open Targets, PharmGKB e LOVD.
- Modelos de classificação de variantes missense.
- Codificações baseadas em números primos.
- Comparações contra baselines e controles não-prime.
- Camadas mecanísticas, incluindo estrutura 3D, proteômica, química computacional e VQE.
- Trilhas de auditoria, manifestos, relatórios e pacotes de publicação.

## 2. O que a plataforma faz hoje

A plataforma já permite:

- Classificar uma variante individual.
- Priorizar variantes em lote por CSV.
- Carregar registros de modelos treinados.
- Rodar pipelines com fontes públicas e locais.
- Preparar dados reais para estudo.
- Mapear bancos públicos independentes.
- Stagear fontes públicas abertas por APIs oficiais.
- Gerar inventário de dados com status pronto, parcial ou faltante.
- Construir estudos publicáveis.
- Executar preflight antes de um benchmark.
- Comparar estudos e acompanhar evolução longitudinal.
- Gerar relatórios de credibilidade científica.
- Criar filas de proteômica, estrutura 3D e análise quântica.
- Medir impacto social e translacional por sessões piloto e feedback.
- Trabalhar em português ou inglês.

## 3. O que a plataforma não deve fazer sozinha

PrimeVarClass não deve ser usada como:

- Laudo clínico autônomo.
- Substituta de curadoria ACMG/AMP formal.
- Substituta de revisão por geneticista, oncologista, bioinformata ou biólogo estrutural.
- Prova definitiva de mecanismo biológico.
- Prova de eficácia terapêutica.
- Ferramenta direta para indicar tratamento sem validação externa.

Sempre leia os resultados como evidência de pesquisa. Quanto mais importante for a decisão, maior deve ser a exigência de validação independente.

## 4. Estrutura geral da interface

A interface foi organizada em módulos para reduzir excesso de informação na tela. Use um módulo por vez.

Módulos principais:

- Início: orientação rápida, idioma, chave da API e visão geral.
- Modelos: carregamento e inspeção dos modelos disponíveis.
- Predição: classificação individual e triagem em lote.
- Equipe: perfis, instituições, times e colaboração.
- Dados públicos: catálogos, bootstrap, resolução e histórico de sincronização.
- Estudos: estudo publicável, preflight, inspeção, comparação e monitor longitudinal.
- Ciência: expansão gênica, descoberta biológica, proteômica, quantum, credibilidade e bancos independentes.
- Impacto: sessões piloto, métricas translacionais e feedback.
- Operação: prontidão, auditoria, jobs e checagens de lançamento.

## 5. Primeiro acesso passo a passo

1. Abra a plataforma em `/workbench`.
2. Escolha o idioma no seletor `Idioma / Language`.
3. Se a autenticação estiver ativa, cole a chave da API.
4. Clique em `Salvar chave`.
5. Vá para o módulo `Equipe`.
6. Crie ou selecione seu perfil institucional.
7. Crie ou selecione o time científico.
8. Vá para o módulo `Modelos`.
9. Clique em `Carregar modelos`.
10. Confirme se existe pelo menos um experimento disponível.
11. Vá para `Predição`.
12. Rode uma variante simples de teste.
13. Leia o resultado com atenção, principalmente probabilidade, classe e evidências.
14. Registre qualquer dúvida ou divergência no fluxo de feedback.

## 6. Conceitos essenciais para iniciantes

Antes de interpretar um resultado, entenda cinco ideias:

- Variante missense: troca de um aminoácido por outro na proteína.
- HGVS proteico: forma padronizada de escrever essa troca, como `p.Cys61Gly`.
- Probabilidade do modelo: estimativa computacional, não diagnóstico.
- Evidência externa: informação de bancos ou ensaios independentes.
- Lacuna: ausência de evidência; não significa benignidade.

Exemplo: se uma variante aparece com probabilidade alta, é um sinal para priorizar revisão. Isso não quer dizer que ela seja automaticamente patogênica.

## 7. Como classificar uma variante individual

Use este fluxo quando quiser analisar uma variante por vez.

1. Abra o módulo `Predição`.
2. Confirme o diretório do modelo.
3. Escolha o experimento.
4. Informe o gene, por exemplo `BRCA1`.
5. Informe o HGVS proteico, por exemplo `p.Cys61Gly`.
6. Preencha evidências opcionais, se disponíveis.
7. Clique em `Classificar variante`.
8. Leia a probabilidade.
9. Leia a classe retornada.
10. Revise os campos de explicabilidade.
11. Compare com bancos externos quando houver.
12. Registre divergências em notas ou feedback.

Campos opcionais úteis:

- PhyloP: conservação evolutiva.
- GERP: restrição evolutiva.
- SiPhy: conservação por modelo filogenético.
- REVEL: preditor externo de patogenicidade.
- gnomAD AF: frequência populacional.
- MAVE score: evidência funcional experimental.

## 8. Como interpretar a probabilidade

Use a probabilidade como triagem:

- Alta probabilidade: priorize revisão e busque evidências independentes.
- Probabilidade intermediária: trate como zona de incerteza.
- Baixa probabilidade: pode sugerir menor prioridade, mas não descarta risco.
- Resultado discordante: investigue manualmente.
- Resultado com dados ausentes: classifique como evidência fraca ou incompleta.

Não transforme automaticamente uma probabilidade em classificação clínica.

## 9. Como fazer triagem em lote

Use triagem em lote quando tiver muitas variantes.

Formato mínimo do CSV:

```csv
sample_id,gene,hgvs_p,phylop,gerp,siphy,revel,feature_gnomad_af,feature_mave_score
BRCA1_001,BRCA1,p.Cys61Gly,7.2,5.8,12.4,0.94,0.000002,-1.8
```

Boas práticas:

- Use uma linha por variante.
- Mantenha nomes de genes em maiúsculas.
- Use HGVS proteico padronizado.
- Não misture coordenadas GRCh37 e GRCh38 sem declarar.
- Revise linhas com erro antes de interpretar o ranking.
- Baixe o relatório Markdown para revisão científica.
- Guarde o CSV de saída com data e versão do modelo.

## 10. Dados reais e fontes públicas

O módulo `Dados públicos` ajuda a verificar, baixar, stagear e resolver fontes externas. Isso aumenta a credibilidade porque reduz dependência de exemplos internos.

Fontes importantes:

- ClinVar: rótulos clínicos e submissões.
- gnomAD: frequência populacional.
- MaveDB: ensaios funcionais MAVE/DMS.
- BRCA Exchange/ENIGMA: curadoria especializada em BRCA.
- ClinGen ERepo: classificações de grupos especialistas.
- UniProt: contexto proteico.
- AlphaFold DB: modelos estruturais preditos.
- RCSB PDB: estruturas experimentais.
- CIViC: evidência oncológica translacional.
- cBioPortal: coortes tumorais.
- GDC: dados genômicos de câncer.
- GWAS Catalog: associações genéticas.
- Open Targets: relação gene-doença.
- PharmGKB: contexto farmacogenômico.
- LOVD: bases locus-específicas.

## 11. Como saber se um dado está pronto

Um dado está mais próximo de pronto quando tem:

- Caminho local resolvido.
- Tamanho de arquivo não trivial.
- Schema reconhecido.
- Colunas de gene e variante.
- Release ou data de download.
- Fingerprint ou hash.
- Fonte oficial documentada.
- Status no inventário como `ready`.

Status comuns:

- `ready`: pode entrar em uma rodada de análise, após revisão.
- `partial`: existe arquivo, mas a cobertura ainda é incompleta.
- `missing`: a fonte ainda precisa ser baixada ou normalizada.

## 12. Fechamento de bancos independentes

O fluxo de fechamento de bancos independentes cria um retrato honesto do que já está stageado.

Ele gera:

- Inventário local.
- Plano de lacunas.
- Configuração TOML pronta para revisão.
- Script de staging.
- Manifesto JSON.
- Relatórios Markdown e HTML.

Como interpretar:

- `ready_source_count`: número de fontes prontas.
- `line_level_real_data_execution_percent`: quanto da execução real por linha está coberta.
- `independent_data_staging_closure_percent`: fechamento geral do staging.
- `ready_for_next_training_round`: indica se já existe base suficiente para uma nova rodada.
- `ready_for_full_independent_retraining`: exige cobertura mais ampla e crítica.

## 13. Estudos publicáveis

Um estudo publicável não é apenas um treino de modelo. Ele precisa de desenho experimental claro.

Antes de rodar:

- Defina a pergunta científica.
- Congele fontes.
- Separe treino, validação e teste.
- Defina coortes externas.
- Defina baselines.
- Defina métricas antes de olhar resultados.
- Registre thresholds.
- Rode preflight.

Depois de rodar:

- Leia métricas por coorte.
- Compare prime, não-prime e híbrido.
- Procure vazamento de dados.
- Verifique conflitos de rótulo.
- Gere pacote de publicação.
- Declare limitações.

## 14. Preflight

Preflight é a checagem antes do estudo principal.

Ele ajuda a detectar:

- Arquivo ausente.
- Caminho quebrado.
- Coluna faltante.
- Fonte sem release.
- Gene fora do escopo.
- Possível vazamento entre treino e teste.
- Falta de dados externos.
- Dados insuficientes para conclusão forte.

Sempre rode preflight antes de interpretar resultados de benchmark.

## 15. Números primos na plataforma

A camada de números primos é o diferencial metodológico do projeto.

Ela pode codificar:

- Identidade de aminoácidos.
- Trocas entre aminoácidos.
- Distâncias discretas.
- Assinaturas por posição.
- Relações modulares.
- Padrões de curvatura e lacunas prime.
- Sinais que podem ser comparados entre genes.

O ponto científico mais importante é testar se essas features melhoram generalização. Para isso, compare sempre:

- Modelo com features prime.
- Modelo sem features prime.
- Modelo híbrido.
- Baselines externos.
- Inicializações prime-guided contra não-prime no VQE.

Sem comparação controlada, a camada prime é uma ideia interessante. Com comparação controlada, ela pode virar evidência metodológica.

## 16. Proteômica e estrutura 3D

O módulo proteômico ajuda a transformar uma variante em hipótese mecanística.

Ele pode priorizar:

- Resíduos em domínios funcionais.
- Regiões de interface.
- Sítios catalíticos.
- Motivos conservados.
- Regiões desordenadas.
- Fragmentos para química computacional.
- Variantes candidatas para ensaio funcional.

Use essa camada para responder:

- A mutação está perto de uma região funcional?
- Ela pode alterar estabilidade?
- Ela pode alterar interação proteína-proteína?
- Ela pode afetar ligação a DNA, cofator ou ligante?
- Ela merece modelagem 3D mais cara?

## 17. Módulo quântico e VQE

O módulo quântico serve para investigação mecanística exploratória.

Ele pode organizar:

- Fragmentos moleculares.
- Active spaces.
- Seeds baseados em números primos.
- Comparação com seeds não-prime.
- Filas para xTB, DFT, Psi4, OpenMM, docking e VQE.

Interpretação correta:

- xTB é triagem rápida.
- DFT é mais forte, mas mais caro.
- Dinâmica molecular avalia estabilidade ao longo do tempo.
- Docking sugere hipóteses de ligação.
- VQE é uma exploração quântica simplificada.

Nenhuma dessas camadas prova tratamento. Elas ajudam a priorizar hipóteses para validação experimental.

## 18. Impacto translacional

O módulo de impacto mede se a plataforma ajuda pessoas reais em fluxos reais.

Registre:

- Caso revisado.
- Variante priorizada.
- Tempo economizado.
- Confiança do usuário.
- Acionabilidade percebida.
- Incidentes.
- Recomendação final.
- Comentários qualitativos.

Impacto translacional forte exige evidência de utilidade, segurança, clareza e reprodutibilidade.

## 19. Feedback

Use feedback para melhorar a plataforma.

Feedback útil deve dizer:

- O que o usuário tentou fazer.
- Onde ficou confuso.
- Qual resultado esperava.
- Qual resultado recebeu.
- Se houve risco de interpretação incorreta.
- Se a linguagem estava clara.
- Se o módulo ajudou ou atrapalhou.

Feedback negativo não é falha do projeto. É uma fonte de melhoria.

## 20. Como avaliar se a plataforma está pronta

A prontidão tem camadas diferentes.

Pronta para teste local:

- API roda.
- Interface carrega.
- Modelos carregam.
- Predição funciona.
- Documentação existe.

Pronta para staging web:

- API key configurada.
- CORS definido.
- Logs e auditoria ativos.
- Volume persistente configurado.
- PDFs e manuais disponíveis.
- Erros principais tratados.

Pronta para preprint computacional:

- Dados reais rastreados.
- Benchmarks congelados.
- Comparações contra baselines.
- Ablation prime versus não-prime.
- Limites declarados.
- Pacote reprodutível.

Pronta para afirmação científica forte:

- Validação independente.
- Confirmação funcional, estrutural ou biofísica.
- Generalização multigênica.
- Revisão externa.
- Linguagem conservadora e auditável.

## 21. Problemas comuns e soluções

`API indisponível`

Verifique se o servidor FastAPI está rodando e se a porta está correta.

`Chave inválida`

Confira se a `PRIMEVARCLASS_API_KEY` configurada no servidor é a mesma usada na interface.

`Nenhum modelo encontrado`

Confirme se o diretório contém `model_registry.csv` e artefatos de modelo.

`Resultado estranho`

Verifique gene, HGVS, dados opcionais e se a variante é realmente missense.

`gnomAD sem resultado`

Confirme build, cromossomo, posição, REF, ALT e versão do dataset.

`MaveDB ausente`

A variante pode não estar no score set disponível ou a cobertura pode ser parcial.

`Engine estrutural indisponível`

Confirme instalação de xTB, Psi4, OpenMM, Vina ou Qiskit no ambiente correto.

`Texto misturado em idiomas`

Use o seletor de idioma. Se persistir, registre feedback com o texto exato.

## 22. Boas práticas para artigo científico

Para escrever um artigo forte:

- Descreva o problema científico com precisão.
- Explique por que variantes missense são difíceis.
- Mostre a arquitetura da plataforma.
- Destaque a camada prime como hipótese metodológica.
- Demonstre comparação com controles.
- Use dados independentes.
- Mostre generalização entre genes.
- Inclua análise mecanística.
- Declare limitações.
- Evite claims clínicos não validados.
- Disponibilize manifestos, tabelas e parâmetros.

## 23. Checklist rápido antes de usar resultados

Antes de confiar em qualquer resultado, pergunte:

- O gene está correto?
- O HGVS está correto?
- A variante é missense?
- O modelo certo foi carregado?
- O dado externo existe?
- Existe conflito entre fontes?
- O resultado foi comparado com baseline?
- A camada prime foi testada contra controle?
- Há evidência funcional ou estrutural?
- A conclusão respeita os limites da plataforma?

## 24. Frase de segurança científica

Use esta frase em relatórios quando necessário:

> Os resultados do PrimeVarClass representam priorização computacional e geração de hipóteses. Eles devem ser interpretados em conjunto com curadoria especializada, diretrizes aplicáveis, evidência independente e confirmação funcional ou estrutural antes de qualquer conclusão clínica ou terapêutica.

## 25. Caminhos úteis

- Interface principal: `/workbench`
- Documentação da API: `/docs`
- Índice de conhecimento: `/knowledge`
- Manual em Markdown: `/knowledge/manual.md`
- Manual em PDF: `/knowledge/manual.pdf`
- Glossário em Markdown: `/knowledge/glossary.md`
- Glossário em PDF: `/knowledge/glossary.pdf`

## 26. Roteiro guiado de primeiro uso em 30 minutos

Este roteiro é o caminho recomendado para um usuário novo conhecer a plataforma sem se perder. Ele não exige que todos os bancos externos estejam configurados. O objetivo é entender a lógica de uso, testar uma variante, conferir os módulos e aprender a interpretar as evidências.

### 26.1 Antes de começar

Confirme três pontos:

- A plataforma está aberta em `/workbench`.
- O idioma selecionado está correto: Português-BR ou English.
- Você sabe se está em perfil local, equipe local ou ambiente autenticado.

Se a autenticação estiver desativada, o campo "Chave da API" pode ficar vazio. Se a autenticação estiver ativa, informe a chave fornecida pelo administrador da plataforma.

### 26.2 Passo 1: reconhecer a tela principal

Na parte superior da tela você verá:

- Nome da plataforma.
- Botão para selecionar idioma.
- Botões de documentação, manual, glossário e feedback.
- Campo opcional de chave da API.
- Indicadores de autenticação, perfil e equipe.

Logo abaixo, a plataforma mostra a barra de módulos. Cada módulo organiza uma área de trabalho separada. Isso evita que a tela fique carregada e permite que o usuário trabalhe por etapas.

Resultado esperado: você deve conseguir alternar entre Início, Modelos, Predição, Equipe, Dados públicos, Estudos, Ciência, Impacto e Operação sem perder o contexto.

### 26.3 Passo 2: abrir o módulo Início

Use o módulo Início para entender o propósito da plataforma e acessar guias rápidos.

O que observar:

- A plataforma é voltada para pesquisa translacional, não para laudo clínico automático.
- Os resultados são hipóteses computacionais priorizadas.
- A interpretação deve considerar dados reais, auditoria, validação independente e confirmação funcional ou estrutural.

Resultado esperado: o usuário entende que PrimeVarClass é uma bancada científica para gerar evidências, não uma ferramenta isolada de diagnóstico.

### 26.4 Passo 3: verificar modelos carregados

Abra o módulo Modelos. Este módulo serve para consultar quais modelos estão disponíveis, qual diretório de modelos está ativo e se os artefatos necessários estão acessíveis.

Preencha ou confira:

- Diretório dos modelos.
- Endpoint de saúde do modelo, quando disponível.
- Versão ou identificador do modelo.
- Status da API.

Clique nos botões de consulta disponíveis. Se a plataforma retornar erro de modelo ausente, isso significa que o ambiente precisa apontar para o diretório correto dos artefatos treinados.

Resultado esperado: você deve saber se há um modelo operacional pronto para inferência ou se a plataforma está em modo de validação/documentação.

### 26.5 Passo 4: testar uma variante individual

Abra o módulo Predição. Este é o módulo mais direto para estudar uma variante missense específica.

Preencha:

- Gene, por exemplo `BRCA1`.
- Alteração proteica em formato HGVS, por exemplo `p.Arg1699Gln`.
- Identificador do experimento, se o campo estiver disponível.
- Modo de execução, quando houver opção entre simulação, inferência local ou inferência com dados reais.

Clique em executar predição ou inferência interpretável.

Resultado esperado: a plataforma deve retornar uma probabilidade, uma classe computacional, um conjunto de evidências e, quando disponível, explicações sobre as features usadas.

### 26.6 Passo 5: interpretar a predição sem exagerar a conclusão

Ao receber o resultado, leia nesta ordem:

- Probabilidade ou escore principal.
- Classe computacional sugerida.
- Evidências que sustentam o resultado.
- Evidências conflitantes.
- Fontes públicas consultadas.
- Alertas sobre dados ausentes.
- Recomendação de validação adicional.

Não conclua que uma variante é clinicamente patogênica apenas porque o modelo indicou alto risco. A conclusão forte exige triangulação com ClinVar, diretrizes aplicáveis, frequência populacional, dados funcionais, literatura e confirmação independente.

Resultado esperado: o usuário sai com uma hipótese priorizada e sabe quais evidências ainda faltam.

### 26.7 Passo 6: explorar Dados públicos

Abra Dados públicos para consultar ou sincronizar fontes externas. Este módulo organiza a conexão com bancos como ClinVar, gnomAD, MaveDB, UniProt, PDB, AlphaFold DB, Open Targets, PharmGKB e outros.

O que fazer:

- Consulte quais fontes estão disponíveis.
- Verifique se há manifesto de ingestão.
- Execute uma sincronização leve quando a interface disponibilizar essa opção.
- Leia os avisos sobre versão, data e origem dos dados.

Resultado esperado: o usuário entende de onde vieram as evidências e se elas são atuais, rastreáveis e independentes.

### 26.8 Passo 7: abrir Estudos

Use Estudos quando quiser organizar uma análise com potencial de relatório, publicação ou validação externa.

Preencha:

- Nome do estudo.
- Gene ou conjunto de genes.
- Versão do dataset.
- Critério de inclusão.
- Critério de exclusão.
- Diretório de saída.

Resultado esperado: a análise deixa de ser apenas uma consulta pontual e passa a ter estrutura reprodutível.

### 26.9 Passo 8: verificar Ciência

O módulo Ciência reúne os elementos que fortalecem a credibilidade científica:

- Benchmark contra baselines.
- Controles não-prime.
- Validação independente.
- Validação prospectiva.
- Evidência funcional.
- Evidência estrutural.
- Relatórios e manifestos.

Resultado esperado: o usuário consegue diferenciar uma demonstração exploratória de uma validação científica forte.

### 26.10 Passo 9: verificar Impacto

Use Impacto para organizar a relevância translacional:

- Quais variantes podem merecer priorização experimental.
- Quais genes ou doenças têm maior relevância.
- Quais resultados podem apoiar estudos funcionais.
- Quais hipóteses podem orientar investigação terapêutica.
- Quais limitações impedem uso clínico direto.

Resultado esperado: o usuário transforma resultado técnico em narrativa científica e social responsável.

### 26.11 Passo 10: abrir Operação

O módulo Operação é usado para verificar prontidão, jobs, incidentes, status de serviços, logs e trilhas de auditoria.

Antes de compartilhar resultados, confirme:

- O status da API está saudável.
- O modelo correto foi usado.
- O manifesto de dados existe.
- Os artefatos foram salvos.
- O relatório registra versão e data.
- Não há erro silencioso nos logs.

Resultado esperado: a análise está rastreável, reproduzível e pronta para revisão por outra pessoa.

## 27. Fluxo completo por módulo

Esta seção funciona como mapa rápido. Cada módulo tem uma função principal, um momento ideal de uso e um resultado esperado.

### 27.1 Início

Use quando quiser entender a plataforma, acessar documentos, escolher idioma e iniciar uma análise.

Campos e botões comuns:

- Documentação da API.
- Manual do usuário.
- Glossário.
- Guia de feedback.
- Idioma.
- Chave da API.

Resultado esperado: usuário orientado e com acesso aos materiais de suporte.

### 27.2 Modelos

Use quando precisar verificar se o algoritmo está pronto para inferência ou treinamento.

O que este módulo responde:

- Existe modelo treinado disponível?
- Qual diretório está sendo usado?
- A API consegue carregar o modelo?
- Há versão identificável?
- O ambiente está preparado para benchmark?

Resultado esperado: ambiente de modelagem verificado antes de executar predições importantes.

### 27.3 Predição

Use para analisar uma variante individual ou executar inferência interpretável.

O que este módulo responde:

- Qual é o escore computacional da variante?
- A variante foi priorizada como potencialmente relevante?
- Quais features influenciaram o resultado?
- Há evidências públicas disponíveis?
- O resultado precisa de confirmação adicional?

Resultado esperado: hipótese de classificação e priorização com evidências rastreáveis.

### 27.4 Equipe

Use para organizar perfis, equipe local, colaboração, responsabilidade e contexto de execução.

O que este módulo responde:

- Quem executou a análise?
- Qual perfil está ativo?
- Qual equipe está associada?
- O ambiente é local ou autenticado?

Resultado esperado: autoria e governança mínimas para uso multiusuário.

### 27.5 Dados públicos

Use para conectar, consultar, sincronizar ou registrar fontes independentes.

O que este módulo responde:

- Quais bancos públicos foram usados?
- Qual versão dos dados foi registrada?
- O dado é real, sintético ou demonstrativo?
- A fonte é populacional, clínica, funcional, estrutural ou terapêutica?

Resultado esperado: evidências externas rastreáveis e atualizáveis.

### 27.6 Estudos

Use para criar análises organizadas, reprodutíveis e publicáveis.

O que este módulo responde:

- Qual pergunta científica está sendo testada?
- Qual coorte ou conjunto de variantes foi usado?
- Qual split separa treino, validação e teste?
- O benchmark foi congelado?
- O relatório final pode ser auditado?

Resultado esperado: pacote de estudo com critérios, resultados e artefatos.

### 27.7 Ciência

Use para fortalecer validação, credibilidade e inovação metodológica.

O que este módulo responde:

- O modelo generaliza para dados independentes?
- A camada baseada em números primos melhora algo além do acaso?
- O VQE prime-guided supera inicializações não-prime?
- A interpretação estrutural é compatível com biologia conhecida?
- Há insight novo que justifique investigação experimental?

Resultado esperado: evidência científica mais robusta, com controles e comparações.

### 27.8 Impacto

Use para traduzir resultado técnico em relevância científica, social e translacional.

O que este módulo responde:

- Qual é a utilidade potencial do resultado?
- Que lacuna científica ele ajuda a fechar?
- Que experimento poderia confirmar a hipótese?
- Que público pode se beneficiar futuramente?
- Qual cuidado ético deve acompanhar a comunicação?

Resultado esperado: narrativa responsável de impacto e próximos passos translacionais.

### 27.9 Operação

Use para status, auditoria, prontidão web, incidentes e rastreabilidade.

O que este módulo responde:

- A plataforma está saudável?
- Os jobs terminaram corretamente?
- Os artefatos foram salvos?
- Há incidentes ou falhas?
- O ambiente está pronto para demonstração, colaboração ou lançamento?

Resultado esperado: operação confiável e documentação técnica mínima.

## 28. Como escolher o fluxo certo

Nem todo usuário precisa começar pelo mesmo módulo. Escolha o fluxo conforme sua necessidade.

### 28.1 Quero analisar uma variante específica

Siga esta sequência:

- Início.
- Modelos.
- Predição.
- Dados públicos.
- Ciência.
- Impacto.
- Operação.

Use quando você tem uma variante como `BRCA1 p.Arg1699Gln` e quer gerar uma hipótese interpretável.

### 28.2 Quero validar o algoritmo com dados reais

Siga esta sequência:

- Dados públicos.
- Estudos.
- Modelos.
- Ciência.
- Operação.
- Impacto.

Use quando você quer treinar, testar ou comparar modelos usando bancos independentes.

### 28.3 Quero preparar material para artigo científico

Siga esta sequência:

- Estudos.
- Dados públicos.
- Ciência.
- Impacto.
- Operação.
- Manual e glossário.

Use quando o foco é reprodutibilidade, metodologia, controles, resultados e limitações.

### 28.4 Quero demonstrar a plataforma para avaliadores

Siga esta sequência:

- Início.
- Predição.
- Dados públicos.
- Ciência.
- Impacto.
- Operação.

Use quando o objetivo é mostrar clareza, inovação, responsabilidade científica e potencial translacional.

### 28.5 Quero preparar lançamento web

Siga esta sequência:

- Operação.
- Equipe.
- Dados públicos.
- Feedback.
- Manual.
- Glossário.
- Estudos.

Use quando o objetivo é disponibilizar a plataforma para múltiplos usuários com suporte e rastreabilidade.

## 29. Como preencher os principais campos

Esta seção explica os campos mais comuns. Os nomes podem variar um pouco conforme o módulo, mas a lógica é a mesma.

### 29.1 Chave da API

Use quando a plataforma estiver com autenticação ativa. A chave identifica o usuário ou serviço autorizado.

Como preencher:

- Cole a chave exatamente como fornecida.
- Não adicione espaços antes ou depois.
- Não compartilhe a chave em relatórios ou capturas de tela.

Se estiver em modo local sem autenticação, o campo pode permanecer vazio.

### 29.2 Gene

Informe o símbolo oficial do gene.

Exemplos:

- `BRCA1`.
- `TP53`.
- `PTEN`.
- `MSH2`.
- `KRAS`.
- `GCK`.
- `F9`.

Boa prática: confirme o símbolo no HGNC, ClinVar, UniProt ou Ensembl antes de uma análise publicável.

### 29.3 Variante proteica

Informe a alteração de aminoácido preferencialmente em formato HGVS proteico.

Exemplos:

- `p.Arg1699Gln`.
- `p.Val600Glu`.
- `p.Gly12Asp`.

Evite formatos ambíguos. Se houver diferentes transcritos, registre qual referência foi usada.

### 29.4 Experimento

Use um nome curto, rastreável e sem espaços problemáticos.

Exemplos:

- `brca1_pilot_2026_05`.
- `tp53_holdout_external`.
- `multigene_validation_v1`.

Boa prática: inclua gene, tipo de análise e data aproximada.

### 29.5 Diretório dos modelos

Indica onde estão os artefatos do algoritmo.

O que pode existir nesse diretório:

- Arquivo do modelo treinado.
- Configurações.
- Metadados.
- Versão do treinamento.
- Features esperadas.
- Manifesto do experimento.

Se o caminho estiver incorreto, a inferência pode falhar mesmo que a interface esteja funcionando.

### 29.6 Diretório de saída

Indica onde os resultados serão gravados.

Use para salvar:

- Relatórios.
- Manifestos.
- Predições.
- Benchmarks.
- Logs.
- Figuras.
- Pacotes de estudo.

Boa prática: não misture resultados exploratórios com resultados finais. Use pastas separadas.

### 29.7 Arquivo TOML

O TOML é um arquivo de configuração legível. Ele pode definir parâmetros de estudo, fontes de dados, diretórios e modos de execução.

Antes de executar:

- Verifique se os caminhos existem.
- Confirme se o gene está correto.
- Confirme se o split de dados está definido.
- Confirme se o benchmark não foi alterado sem registro.

### 29.8 Caminho do manifesto

O manifesto registra origem, versão, data e contexto dos dados ou resultados.

Use sempre que quiser reprodutibilidade. Um resultado sem manifesto pode ser útil para exploração, mas é fraco para publicação.

### 29.9 Limiar ou threshold

Define o ponto de corte usado para transformar probabilidade em classe.

Exemplo:

- Probabilidade acima do limiar pode ser marcada como alta prioridade.
- Probabilidade abaixo do limiar pode ser marcada como baixa prioridade.

Boa prática: defina o limiar antes da validação independente para evitar ajuste oportunista.

### 29.10 Modo de execução

Alguns módulos podem oferecer modos como simulação, execução local, execução com dados reais ou validação.

Interpretação:

- Simulação: útil para aprender e testar fluxo.
- Local: usa recursos disponíveis na máquina ou no ambiente configurado.
- Dados reais: consulta ou usa bancos externos reais.
- Validação: executa critérios mais rígidos para avaliação científica.

## 30. Como interpretar os principais resultados

A plataforma pode exibir cartões, listas, tabelas internas, manifestos, logs e relatórios. A regra geral é: nenhum resultado deve ser lido isoladamente.

### 30.1 Probabilidade

Probabilidade é o escore computacional do modelo. Ela não é diagnóstico clínico.

Como interpretar:

- Valor alto sugere maior prioridade computacional.
- Valor baixo sugere menor prioridade computacional.
- Valores intermediários exigem cautela.
- A calibração do modelo importa tanto quanto o valor bruto.

### 30.2 Classe computacional

Classe é a categoria sugerida pelo algoritmo com base no limiar definido.

Exemplos:

- Alta prioridade.
- Baixa prioridade.
- Incerta.
- Necessita revisão.

A classe deve ser conferida contra evidência independente.

### 30.3 Evidências favoráveis

São dados que apoiam a hipótese gerada.

Exemplos:

- Variante rara em gnomAD.
- Evidência funcional em MaveDB.
- Registro clínico consistente em ClinVar.
- Região estrutural sensível.
- Alteração em domínio proteico importante.

### 30.4 Evidências conflitantes

São dados que reduzem a confiança ou indicam divergência.

Exemplos:

- ClinVar com classificações discordantes.
- Frequência populacional incompatível com alta penetrância.
- Modelo computacional alto, mas ensaio funcional neutro.
- Evidência estrutural fraca ou ausente.

Quando houver conflito, o relatório deve declarar a incerteza.

### 30.5 Fontes consultadas

Sempre confira quais bancos foram usados.

Exemplos de fontes:

- ClinVar.
- gnomAD.
- MaveDB.
- BRCA Exchange/ENIGMA.
- UniProt.
- AlphaFold DB.
- PDB.
- CIViC.
- Open Targets.
- PharmGKB.

Resultado forte precisa de fontes rastreáveis, não apenas de escore interno.

### 30.6 Manifesto

Manifesto é o comprovante técnico da análise.

Ele deve responder:

- Qual dado foi usado?
- Qual versão foi usada?
- Quando a análise foi feita?
- Qual configuração foi usada?
- Onde os resultados foram salvos?

Sem manifesto, a análise fica difícil de reproduzir.

### 30.7 Logs e status

Logs registram o que aconteceu durante a execução.

Procure:

- Erros.
- Avisos.
- Tempo de execução.
- Fonte indisponível.
- Campo ausente.
- Job incompleto.

Nunca ignore erro apenas porque algum cartão visual apareceu na interface.

### 30.8 Relatório final

Um relatório confiável deve conter:

- Pergunta científica.
- Dados usados.
- Modelo usado.
- Resultado principal.
- Evidências externas.
- Controles.
- Limitações.
- Próximos passos experimentais.

## 31. Roteiros prontos para tarefas comuns

### 31.1 Roteiro para variante individual

Use quando quiser estudar uma variante específica.

Passos:

- Abra Predição.
- Informe gene e HGVS proteico.
- Execute inferência.
- Leia probabilidade e classe.
- Confira evidências externas.
- Abra Ciência para ver necessidade de validação.
- Abra Impacto para traduzir a hipótese.
- Salve ou registre o resultado com manifesto.

Conclusão segura: "A variante foi priorizada computacionalmente e merece avaliação adicional."

Conclusão insegura: "A variante é clinicamente patogênica porque o algoritmo indicou alto risco."

### 31.2 Roteiro para lote de variantes

Use quando quiser processar muitas variantes.

Passos:

- Prepare arquivo de entrada com gene e variante.
- Confira se todos os nomes seguem padrão consistente.
- Abra Estudos ou Predição em lote, se disponível.
- Informe diretório de saída.
- Execute a triagem.
- Revise erros de formato.
- Ordene variantes por prioridade.
- Separe variantes com evidência forte, conflitante e ausente.

Boa prática: mantenha o arquivo original intacto e salve uma cópia processada.

### 31.3 Roteiro para validação com dados públicos

Use quando quiser fortalecer a credibilidade do algoritmo.

Passos:

- Abra Dados públicos.
- Confirme fontes reais disponíveis.
- Registre versões em manifesto.
- Abra Estudos.
- Defina conjunto de treino, validação e teste.
- Abra Ciência.
- Execute benchmark contra baseline.
- Compare camada prime contra controle não-prime.
- Registre métricas, intervalos e limitações.

Boa prática: congele o benchmark antes de olhar o resultado final.

### 31.4 Roteiro para estudo multigênico

Use quando quiser testar generalização.

Passos:

- Escolha genes independentes.
- Confirme se há dados suficientes por gene.
- Separe BRCA1 de genes usados para validação externa.
- Execute análise por gene.
- Compare desempenho global e desempenho específico.
- Investigue genes em que o modelo falha.
- Documente limites de generalização.

Genes úteis para expansão incluem `TP53`, `PTEN`, `MSH2`, `KRAS`, `GCK` e `F9`, desde que haja dados suficientes e critérios bem definidos.

### 31.5 Roteiro para hipótese proteômica e estrutural

Use quando quiser investigar mecanismo biológico.

Passos:

- Identifique a proteína e a variante.
- Consulte UniProt para domínios e função.
- Consulte AlphaFold DB ou PDB para estrutura.
- Verifique se a variante está em domínio funcional.
- Analise proximidade com sítio ativo, interface ou região de ligação.
- Use xTB, DFT ou VQE apenas quando houver pergunta química clara.
- Compare mutante contra referência.
- Registre incertezas estruturais.

Boa prática: estrutura computacional sugere mecanismo, mas não substitui ensaio experimental.

### 31.6 Roteiro para impacto translacional

Use quando quiser transformar resultado em plano de pesquisa aplicada.

Passos:

- Liste variantes priorizadas.
- Classifique nível de evidência.
- Identifique mecanismo provável.
- Consulte relação com doença.
- Verifique se há fármacos, vias ou alvos conhecidos.
- Defina experimento confirmatório.
- Indique benefício potencial e risco de interpretação.

Resultado esperado: hipótese translacional pronta para discussão com equipe experimental ou clínica.

## 32. Como registrar evidência para publicação, prêmio ou colaboração

Para que a plataforma seja avaliada com seriedade, cada conclusão precisa ser acompanhada de evidência rastreável.

### 32.1 Evidência mínima por análise

Inclua:

- Data da execução.
- Versão da plataforma.
- Versão do modelo.
- Gene e variante.
- Fonte dos dados.
- Manifesto.
- Resultado principal.
- Limitações.

### 32.2 Evidência forte por estudo

Inclua:

- Dataset independente.
- Split congelado.
- Baseline comparativo.
- Controle não-prime.
- Métricas de desempenho.
- Análise de erro.
- Relatório interpretável.
- Confirmação funcional ou estrutural quando disponível.

### 32.3 Evidência ideal para alto impacto científico

Inclua:

- Validação externa prospectiva.
- Generalização multigênica.
- Comparação com métodos consolidados.
- Interpretação mecanística nova.
- Hipótese experimental testável.
- Reprodutibilidade completa.
- Discussão clara de limites.

## 33. Erros comuns e como resolver

### 33.1 A plataforma abriu, mas a aparência parece antiga

Possível causa: cache do navegador.

Como resolver:

- Pressione `Ctrl+F5`.
- Reabra `/workbench`.
- Confirme se a URL não está apontando para uma versão antiga.

### 33.2 O botão executa, mas não aparece resultado

Possíveis causas:

- API não respondeu.
- Chave da API ausente.
- Modelo não carregado.
- Campo obrigatório vazio.
- Job ainda em execução.

Como resolver:

- Confira o módulo Operação.
- Leia logs ou status.
- Verifique se gene e variante foram preenchidos.
- Teste primeiro com uma análise simples.

### 33.3 O resultado aparece, mas faltam evidências externas

Possíveis causas:

- Fonte pública não configurada.
- Banco externo indisponível.
- Variante não existe naquela fonte.
- Gene ou HGVS foram informados em formato diferente.

Como resolver:

- Abra Dados públicos.
- Confira fontes disponíveis.
- Registre a ausência como limitação.
- Não invente evidência ausente.

### 33.4 A predição parece contradizer ClinVar

Possível causa: o modelo mede prioridade computacional, enquanto ClinVar agrega interpretação clínica.

Como resolver:

- Declare conflito.
- Verifique data e versão do ClinVar.
- Consulte evidência funcional.
- Consulte frequência populacional.
- Não force concordância artificial.

### 33.5 O benchmark parece bom demais

Possíveis causas:

- Vazamento entre treino e teste.
- Duplicatas.
- Variante presente em fontes usadas durante desenvolvimento.
- Limiar ajustado depois de ver resultado.

Como resolver:

- Refaça split.
- Use holdout externo.
- Congele benchmark.
- Compare com baseline.
- Documente o risco.

### 33.6 O módulo quântico retorna resultado difícil de interpretar

Possível causa: VQE e química computacional exigem pergunta molecular bem delimitada.

Como resolver:

- Defina o fragmento.
- Compare referência e mutante.
- Use controle não-prime.
- Evite concluir mecanismo biológico apenas por diferença de energia.
- Registre como hipótese, não como confirmação.

## 34. Checklist antes de compartilhar um resultado

Use este checklist sempre que for enviar uma análise para orientador, banca, colaborador, avaliador de prêmio ou artigo.

### 34.1 Checklist técnico

- A plataforma usada é a versão correta.
- O gene foi conferido.
- O HGVS foi conferido.
- O modelo foi carregado corretamente.
- O diretório de saída foi definido.
- O manifesto foi gerado.
- Os logs não mostram erro crítico.

### 34.2 Checklist científico

- A fonte dos dados está registrada.
- O resultado foi comparado com baseline.
- A camada prime foi comparada com controle não-prime quando relevante.
- A validação independente foi separada do treino.
- As limitações foram escritas.
- Evidências conflitantes foram preservadas.
- Não houve conclusão clínica indevida.

### 34.3 Checklist translacional

- A hipótese biológica está clara.
- O possível mecanismo foi descrito com cautela.
- O experimento confirmatório foi sugerido.
- O benefício potencial foi explicado sem exagero.
- O risco de uso indevido foi declarado.

## 35. Como pedir ajuda ou enviar feedback útil

Quando encontrar problema, envie feedback com contexto suficiente para reprodução.

Inclua:

- Módulo usado.
- Gene.
- Variante.
- Horário aproximado.
- Mensagem de erro.
- Resultado esperado.
- Resultado observado.
- Se a análise usou dados reais ou simulação.

Evite enviar apenas "não funcionou". Um bom feedback acelera correção e melhora a plataforma para todos.

## 36. Regra de ouro da plataforma

O PrimeVarClass é mais forte quando combina três coisas:

- Predição computacional rastreável.
- Evidência independente real.
- Interpretação biológica testável.

Quando esses três elementos concordam, a hipótese fica muito mais forte. Quando eles discordam, a discordância não é falha: é uma oportunidade científica para descobrir o que ainda não entendemos.
