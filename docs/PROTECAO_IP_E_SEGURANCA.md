# Proteção intelectual e cibersegurança

Estratégia adotada: **repositório aberto + proveniência forte**. O trabalho
permanece público e auditável (o que reforça a credibilidade científica perante a
banca), enquanto a autoria fica cravada de forma imutável e datada, de modo que
qualquer plágio se torna **detectável, atribuível e legalmente acionável**.

> Nota: para um repositório público não existe "impedir a leitura/cópia";
> existe tornar a cópia sem crédito uma violação comprovável. As medidas abaixo
> garantem exatamente isso.

## ✅ Já implementado (lado do repositório)

| Medida | Arquivo | O que garante |
| --- | --- | --- |
| Licença com atribuição obrigatória | [`LICENSE`](../LICENSE) (MIT) | reuso legal exige creditar o autor |
| Aviso de copyright/autoria | [`NOTICE`](../NOTICE) | declara autoria de Wesley Felipe Capucho |
| Metadados de citação | [`CITATION.cff`](../CITATION.cff) | como citar o trabalho |
| Manifesto de proveniência | [`PROVENANCE.md`](../PROVENANCE.md), `provenance_manifest.sha256` | hash SHA-256 de todo o conteúdo, datado |
| Metadados de arquivamento | `.zenodo.json` | prepara o DOI do Zenodo |
| CI de segurança | `.github/workflows/ci.yml` | `pip-audit` (CVEs), lint, permissões mínimas |
| Higiene de segredos | `.gitignore`, `.env.example`, `SECURITY.md` | nenhuma credencial versionada |

O **histórico do git**, uma vez enviado ao GitHub, recebe um **carimbo de tempo do
servidor** (não forjável) para cada commit: a prova primária de anterioridade.

## 🔒 Ações que dependem da sua conta (faça você)

1. **DOI no Zenodo (mais importante).**
   - Acesse <https://zenodo.org>, faça *Log in with GitHub* e, em *Settings > GitHub*,
     ative o *toggle* para o repositório `primevarclass`.
   - No GitHub, crie um **Release** (ex.: tag `v1.0.0`). O Zenodo arquiva
     automaticamente aquele snapshot e **emite um DOI permanente e citável**,
     com sua autoria e data. Cole o DOI de volta no `README` e no `CITATION.cff`.

2. **Autenticação de dois fatores (2FA) no GitHub.** *Settings > Password and
   authentication > Two-factor authentication.* Sem isso, todo o resto é frágil.

3. **Commits assinados (GPG ou SSH).** Prova criptográfica de que os commits são
   seus. `git config --global commit.gpgsign true` após cadastrar sua chave em
   *Settings > SSH and GPG keys*. (Commits futuros aparecem como *Verified*.)

4. **Proteção de branch.** No GitHub: *Settings > Branches > Add rule* para
   `main`: exigir PR, **bloquear force-push** e **impedir reescrita de histórico**
   (isso protege sua autoria contra apagamento).

5. **Secret scanning + Dependabot.** *Settings > Code security*: ative *Secret
   scanning* e *Dependabot alerts*.

## Como verificar a proveniência (qualquer pessoa, no futuro)

```bash
python scratch/build_provenance_manifest.py   # regenera o manifesto
# compare o ROOT SHA-256 impresso com o registrado em PROVENANCE.md
```

Se o conteúdo tiver sido alterado, a raiz muda: a integridade é verificável.
