# PrimeVarClass - publicação científica e lançamento web

Este runbook separa duas decisões que não devem ser misturadas:

- **Lançamento web controlado**: disponibilizar a plataforma para uso por equipe, revisores, colaboradores ou piloto institucional.
- **Afirmação científica forte**: sustentar conclusões sobre desempenho, mecanismo biológico e utilidade translacional com validação independente.

O produto pode ir para staging antes da validação experimental final, desde que a interface, o manuscrito e os relatórios deixem claro que a plataforma é uma ferramenta de pesquisa e não um dispositivo clínico.

## 1. Auditoria de prontidão

Gere o pacote de prontidão:

```bash
primevarclass --build-launch-readiness --output-dir primevarclass_launch_readiness_results
```

Arquivos gerados:

- `launch_readiness_manifest.json`: resumo auditável para API, equipe e publicação.
- `launch_readiness_report.md`: relatório legível com lacunas e próximos passos.
- `launch_readiness_report.html`: versão para revisão institucional.
- `launch_readiness_checklist.csv`: checklist linha a linha para acompanhamento.

Pela API:

```bash
curl -H "X-API-Key: $PRIMEVARCLASS_API_KEY" http://localhost:8000/launch/readiness
```

Para exportar via API:

```bash
curl -X POST http://localhost:8000/launch/readiness/export \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $PRIMEVARCLASS_API_KEY" \
  -d "{\"output_dir\":\"primevarclass_launch_readiness_results\"}"
```

## 2. Gates científicos mínimos

Antes de submeter um preprint computacional:

- Manifesto de dados reais versionado e rastreável.
- Benchmark final com coortes externas independentes.
- Pacote de `publication_readiness` gerado.
- Fechamento de validação e credibilidade gerado.
- Plano prospectivo/experimental exportado.
- Pacotes mecanísticos disponíveis para descoberta biológica, proteômica/3D e módulo quântico.
- Linguagem conservadora no manuscrito: sem alegar validade clínica, eficácia terapêutica ou descoberta causal experimental sem confirmação externa.

Antes de uma afirmação científica forte em periódico de maior impacto:

- Confirmação funcional independente dos alvos prioritários.
- Confirmação estrutural/experimental ou biophysical follow-up para variantes principais.
- Rodada prospectiva com dados não vistos.
- Revisão estatística independente.
- Disponibilização de código, manifests, seeds, versões de bases públicas e critérios de exclusão/inclusão.

## 3. Gates web mínimos

Antes de expor a plataforma fora da máquina local:

- Definir `PRIMEVARCLASS_API_KEY` com chave longa e privada.
- Usar HTTPS no domínio público.
- Definir `PRIMEVARCLASS_CORS_ORIGINS` se houver frontend hospedado fora da API.
- Usar volume persistente para `PRIMEVARCLASS_JOB_ROOT`.
- Testar `/health`, `/workbench`, `/knowledge`, `/launch/readiness` e fluxo de login por chave.
- Revisar logs de auditoria e política de retenção.
- Não montar dados sensíveis como volume público de leitura.

## 4. Execução local em container

Crie `.env` a partir de `.env.example` e ajuste a chave:

```bash
copy .env.example .env
```

Suba a plataforma:

```bash
docker compose up --build
```

Endereços:

- Workbench: `http://localhost:8000/workbench`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/launch/readiness`

## 5. Evidência para o artigo

Inclua no pacote suplementar:

- `launch_readiness_manifest.json`
- `publication_readiness_manifest.json`
- `validation_credibility_closure_manifest.json`
- `prospective_validation_closure_manifest.json`
- `real_data_preparation_manifest.json`
- manifests de release dos datasets e estudos
- relatórios de comparação, robustez externa, claim strength e validation lock

No manuscrito, descreva os números primos como camada metodológica testável:

- codificação prima de aminoácidos/códons;
- deslocamentos e assinaturas derivadas de números primos;
- contribuição de features primas em comparação com inicializações ou codificações não-primas;
- ponte prime-guided para seleção de alvos/active spaces no módulo quântico;
- ablação contra modelos sem features primas.

## 6. Frase de segurança científica

Use uma declaração como:

> PrimeVarClass é uma plataforma de pesquisa para priorização e geração de hipóteses sobre variantes missense. Os resultados não devem ser usados para decisão clínica sem validação independente, revisão especializada e confirmação funcional/estrutural quando aplicável.
