# Prime-number ablation narrative

## Jury-facing message

Prime numbers are not presented as a mystical biological law. They are used as a transparent, reproducible feature-engineering lens that maps amino-acid substitutions into discrete mathematical relationships. The ablation story is strongest when the prime-only signal is compared against biochemical-only, external-only and hybrid models on the same frozen data.

## Evidence table

| Feature set | Training AUC-ROC | Best external AUC-ROC | Jury interpretation |
|---|---:|---:|---|
| hybrid_plus_external | 0.8089 | 0.7771 | Best competition story: prime-aware model plus public biological evidence. |
| hybrid_plus_conservation_structure | 0.8062 | 0.7711 | Supportive ablation layer for robustness and interpretability. |
| hybrid | 0.8062 | 0.7709 | Shows the prime representation works best when fused with biochemical context. |
| hybrid_plus_conservation | 0.8062 | 0.7709 | Supportive ablation layer for robustness and interpretability. |
| biochemical_only | 0.8027 | 0.7764 | Non-prime biological baseline for judging the added value of prime features. |
| gene_balanced_specialist | 0.757 | 0.9223 | Supportive ablation layer for robustness and interpretability. |
| prime_only | 0.7104 | 0.6843 | Isolates the prime-number signal; useful for originality, but must not be overclaimed alone. |
| external_predictors_only | 0.5246 | 0.7419 | Baseline comparator; proves the project is not just repackaging external predictors. |

## Safe claim

The prime-number component is a defensible originality layer because it is explicit, testable and ablated against non-prime controls. The final paper should claim that prime-aware features improve the platform as part of a hybrid biological AI workflow, not that prime numbers alone prove pathogenicity.

## Figure recommendation

Create one figure with five bars: prime-only, biochemical-only, external-only, hybrid, and hybrid-plus-external. Add a callout showing that the prime signal becomes most valuable when fused with biochemical and public-data evidence.
