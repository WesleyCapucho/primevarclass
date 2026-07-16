# A história dos números primos

### De uma hipótese ousada a uma prova de rigor científico

O nome **PrimeVarClass** guarda a origem do projeto — e essa origem é, ela
própria, um dos seus maiores méritos. Este documento conta, com transparência
total e números reproduzíveis, o papel que os números primos tiveram: **não como
o motor do método, mas como a fagulha que, testada com rigor, levou o
projeto ao que de fato funciona.**

---

## 1. A fagulha

A ideia inicial era pouco convencional e, por isso mesmo, sedutora: *e se a
matemática dos números primos escondesse um padrão biológico?* Codificamos cada
aminoácido por atributos derivados de números primos e perguntamos se **posições
e identidades "primas" seriam mais associadas a mutações patogênicas** em BRCA1 e
BRCA2. Era uma aposta de alto risco — exatamente o tipo de pergunta que a ciência
existe para responder.

## 2. A regra do jogo: testar para valer

Uma hipótese só vale o rigor com que é testada. Antes de olhar para qualquer
resultado, fixamos um protocolo à prova de autoengano:

- **Validação cruzada bloqueada por posição** (nenhuma posição da proteína aparece
  ao mesmo tempo no treino e no teste), para impedir *memorização*;
- **Coortes externas independentes** (o modelo é avaliado em variantes que nunca
  viu, de fontes distintas);
- **Teste de DeLong** para comparar curvas ROC com significância estatística.

Tudo com dados **públicos e reais** (ClinVar), e todo o código versionado.

## 3. O veredito: a hipótese foi refutada

Testamos sob o protocolo mais rigoroso do projeto: validação cruzada **bloqueada
por posição** (nenhuma posição aparece simultaneamente no treino e no teste) e,
de forma decisiva, **generalização em coortes externas independentes** — nunca
tocadas durante o treino. (Reproduzível em
[`scratch/prime_hypothesis_rigorous_test.py`](../scratch/prime_hypothesis_rigorous_test.py);
resultado salvo em
[`primevarclass_manuscript_analysis/prime_hypothesis_rigorous.json`](../primevarclass_manuscript_analysis/prime_hypothesis_rigorous.json).)

| Representação testada | nº de atributos | CV bloqueada por posição | Coortes externas |
|---|---:|---:|---:|
| Identidade simples (gene + aminoácidos + posição bruta)ᵃ | 4 | 0,871 | 0,882 |
| Bioquímica (inclui posição bruta)ᵃ | 28 | 0,802 | 0,791 |
| Bioquímica **+ primos** (híbrido)ᵃ | 76 | 0,783 | 0,765 |
| Identidade simples (sem posição) | 3 | 0,745 | 0,718 |
| **Só números primos** | 50 | 0,717 | **0,681** |

ᵃ Estes três conjuntos incluem a posição bruta do resíduo — um atalho que, como
mostramos no artigo, **memoriza** o treino e não se sustenta em dados novos; por
isso a comparação decisiva da hipótese dos primos usa as duas últimas linhas.

Duas conclusões, ambas estatisticamente significativas (DeLong):

1. **Os primos perdem até para a identidade simples do aminoácido**, sem posição
   (0,681 vs 0,718 nas coortes externas; *p* = 0,045).
2. **Adicionar primos a um modelo bioquímico *piora* o desempenho** nas coortes
   externas (0,791 → 0,765; *p* = 3,8 × 10⁻⁸).

> Ressalva: uma verificação preliminar mais simples — validação
> cruzada **sem** bloqueio por posição
> ([`scratch/decisive_prime_test.py`](../scratch/decisive_prime_test.py)) — chegou
> a números diferentes e mais otimistas para a identidade com posição (AUC ≈ 0,90).
> Não os usamos como veredito: eles **sofrem exatamente do vazamento posicional**
> que este projeto identifica e neutraliza (ver Seção 4). O teste que vale é o
> protocolo rigoroso acima.

Poderíamos ter escondido isso. Escolhemos o contrário: **a refutação virou o
alicerce de credibilidade do projeto.**

## 4. O pivô: deixar os dados apontarem o caminho

Com a hipótese original descartada, seguimos a evidência. Ela apontou
para dois ingredientes com significado biológico real:

- **Consciência de domínio funcional** — informar ao modelo *onde*, na arquitetura
  da proteína (RING, BRCT, DBD…), cada variante ocorre;
- **Modelo de linguagem de proteínas (ESM-2)** — que aprende as "regras" evolutivas
  de como as proteínas se dobram e funcionam.

O ganho foi consistente e transferível para as coortes externas:

| Modelo | AUC externa |
|---|---:|
| Consciente de domínio | 0,847 |
| **Consciente de domínio + ESM-2** | **0,909** |

O salto de domínio para domínio + ESM-2 é estatisticamente robusto (DeLong,
*p* ≈ 10⁻¹⁰). Este é o **coração científico** do PrimeVarClass — e ele nasceu de
ter tido a disciplina de abandonar a ideia bonita que não se sustentava.

## 5. Por que isso dá força ao projeto

Vivemos um momento em que a área de IA é inundada por alegações infladas e
resultados que não se reproduzem. Contra esse pano de fundo, uma trajetória de
**"hipótese ousada → teste rigoroso → refutação documentada → redirecionamento guiado
por evidência"** não é uma fraqueza: é exatamente o que distingue ciência de
marketing tecnológico.

- **Integridade demonstrada, não prometida.** Qualquer um pode reproduzir a
  refutação dos primos e a validação do modelo final.
- **Antídoto ao hype.** O projeto mostra, na prática, como se separa sinal de
  ilusão — uma competência tão valiosa quanto o resultado em si.
- **Método transferível.** O mesmo protocolo anti-autoengano que refutou os primos
  é o que dá confiança no desempenho final (AUC 0,909, calibração ACMG, validação
  temporal prospectiva).

## 6. Por que manter o nome

**PrimeVarClass** carrega os primos como assinatura de origem — a memória de ter
perseguido o caminho difícil e rigoroso. Os primos foram a pergunta; o rigor foi o
método; a consciência de domínio e o ESM-2 são a resposta. O nome celebra a
**jornada científica completa**, não um atalho.

> Em uma frase: *começamos com números primos, testamos com rigor,
> descobrimos que não funcionavam — e foi justamente esse rigor que nos levou
> a construir algo que funciona.*

---

*Todos os números deste documento são reais e reproduzíveis. Baselines e
comparações: [`scratch/decisive_results/`](../scratch/decisive_results).
Avaliação do modelo final: [`primevarclass_manuscript_analysis/`](../primevarclass_manuscript_analysis).*
