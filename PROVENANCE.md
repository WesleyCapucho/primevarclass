# Proveniência e autoria — PrimeVarClass

**Autor:** Wesley Felipe Capucho — Escola de Engenharia de Lorena, Universidade
de São Paulo (EEL-USP).
**Data deste registro:** 2026-07-09.

## Registro criptográfico de integridade

Este repositório inclui um manifesto (`provenance_manifest.sha256`) com o hash
**SHA-256** de cada arquivo versionado. A raiz abaixo é o SHA-256 do manifesto
completo — uma impressão digital única de todo o conteúdo nesta data:

```
ROOT SHA-256: 05e41c499b6e36cdd2904253f3c40fd664163205e218f6566b73238eba086d0e
arquivos: 149
```

Qualquer alteração de qualquer arquivo muda essa raiz. Para verificar:

```bash
python scratch/build_provenance_manifest.py
# a "ROOT SHA-256" impressa deve ser idêntica à registrada acima
```

## Prova de anterioridade

- O **histórico do git**, publicado no GitHub, associa cada commit ao autor e a
  um **carimbo de tempo do servidor** (não forjável), estabelecendo quando cada
  parte foi criada.
- Um **DOI do Zenodo** (a ser emitido a partir de um *release*) arquiva um
  snapshot imutável, datado e citável — a prova pública definitiva de autoria.
  Ver [`docs/PROTECAO_IP_E_SEGURANCA.md`](docs/PROTECAO_IP_E_SEGURANCA.md).

## Termos

Distribuído sob a licença **MIT** (ver `LICENSE`): o reuso é permitido, porém a
**atribuição ao autor é obrigatória**. Ver `NOTICE` e `CITATION.cff`.
