# Política de segurança: PrimeVarClass

## Escopo e postura

PrimeVarClass é uma **ferramenta de apoio à pesquisa** que classifica variantes
*missense* de BRCA1/BRCA2 a partir de **dados públicos e agregados** (ClinVar,
gnomAD, painéis de especialistas ENIGMA/ClinGen, UniProt, RCSB PDB). O projeto:

- **não coleta, armazena ou processa dados pessoais de pacientes**: apenas
  identificadores de variantes e rótulos de significância clínica de bases
  públicas. Não há informação identificável (em conformidade com a LGPD, a
  ferramenta opera fora do regime de dados pessoais sensíveis);
- **não é dispositivo médico** e não emite laudo; as saídas exigem confirmação
  por aconselhamento genético e validação experimental independente;
- não expõe serviço de rede na configuração de referência: a execução é local,
  sobre dados versionados neste repositório.

## Boas práticas de segurança adotadas

- **Sem segredos no versionamento.** Arquivos `.env` e credenciais estão no
  `.gitignore`; o repositório traz apenas `.env.example`. O histórico é
  verificado para ausência de chaves. Nunca comite segredos.
- **Cadeia de suprimento.** Dependências de runtime mínimas e maduras
  (`numpy`, `pandas`, `scikit-learn`, `matplotlib`, `joblib`). A CI executa
  `pip-audit` para sinalizar CVEs conhecidas em dependências.
- **CI com privilégio mínimo.** O workflow declara `permissions: contents: read`
  e fixa as *actions* em versões maiores confiáveis.
- **Entrada de dados.** A ingestão faz *parsing* de arquivos tabulares/TOML
  públicos; não há `eval`, `pickle` de fontes não confiáveis nem execução
  dinâmica de conteúdo externo.

## Como reportar uma vulnerabilidade

Se você encontrar uma vulnerabilidade de segurança ou um problema de
integridade de dados, **não abra uma *issue* pública**. Envie um e-mail para
**wesleycapucho@usp.br** com a descrição, o impacto e, se possível, uma prova de
conceito. O objetivo é responder em até **15 dias úteis** e corrigir problemas
confirmados de forma responsável antes de divulgação pública.
