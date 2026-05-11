# PrimeVarClass - Playbook de feedback

## Para que serve

O feedback transforma uso real em evidencia de produto e impacto translacional. Cada sessao deve responder: a ferramenta ajudou, economizou tempo, gerou hipoteses acionaveis e manteve seguranca cientifica?

## Quando registrar

- Depois de uma triagem em lote.
- Depois da revisao de um caso dificil.
- Depois da comparacao com curadoria humana.
- Depois de reuniao de laboratorio ou comite translacional.
- Sempre que houver erro, confusao, atraso, resultado inesperado ou discordancia cientifica.

## Campos minimos

- `session_id`: identificador unico da sessao.
- `study_name`: estudo ou benchmark associado.
- `operator_name`: pessoa responsavel.
- `role`: papel do usuario.
- `confidence_score`: confianca de 0 a 5.
- `actionability_score`: utilidade pratica de 0 a 5.
- `time_saved_minutes`: tempo estimado economizado.
- `adoption_recommendation`: `recommended`, `conditional` ou `not_recommended`.
- `incident_level`: `none`, `low`, `medium` ou `high`.
- `notes`: comentarios livres.

## Escala recomendada

- 0: nao ajudou ou gerou risco.
- 1: ajudou pouco, com muita incerteza.
- 2: util em contexto limitado.
- 3: util, mas exige revisao cuidadosa.
- 4: muito util e compreensivel.
- 5: excelente, acionavel e com baixo atrito.

## Como interpretar

- Confianca alta e acionabilidade alta indicam maturidade de UX e ciencia.
- Confianca baixa com acionabilidade alta indica potencial, mas falta explicabilidade.
- Acionabilidade baixa com confianca alta pode indicar resultado correto, mas pouco util para decisao.
- Incidentes `medium` ou `high` devem bloquear rollout publico ate revisao.
- Tempo economizado sem qualidade cientifica nao basta para impacto real.

## Exemplo de nota util

```text
O ranking priorizou BRCA1 p.Cys61Gly de forma coerente com raridade e MAVE.
A explicacao foi clara para o time senior, mas o estudante pediu definicao de gnomAD AF.
Tempo economizado estimado: 25 minutos. Sem incidente.
```

## Como usar feedback negativo

Feedback negativo nao e fracasso. Ele deve virar backlog:

- Termo confuso: adicionar ao glossario.
- Botao dificil de encontrar: revisar hierarquia visual.
- Resultado sem evidencia: melhorar anotacao ou mensagem de lacuna.
- Erro recorrente: adicionar validacao ou preflight.
- Discordancia cientifica: criar caso de teste e registrar excecao.

## Regra de seguranca

Feedback positivo nao substitui validacao externa. Ele mede utilidade e experiencia; a validade cientifica continua dependendo de benchmark independente, auditoria, revisao humana e confirmacao experimental.

