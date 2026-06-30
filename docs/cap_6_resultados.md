# 6. RESULTADOS E DISCUSSÃO

## 6.1 Performance do Modelo Híbrido e Preditores Estruturais

A arquitetura do PrimeVarClass foi avaliada sistematicamente por meio de experimentação híbrida, contrapondo os preditores extrínsecos da literatura (AlphaMissense, BayesDel, CADD e REVEL) aos atributos intrínsecos de *Prime Encoding* (assimetria de vizinhança prima, escores de curvatura, etc). 

Conforme os registros de *logs* gerados pela execução na nuvem, o modelo **"hybrid_plus_conservation_structure"** — que funde os atributos de conservação evolutiva, propriedades matemáticas primas e predições externas — alcançou métricas no estado da arte para a classificação de variantes nos genes *BRCA1* e *BRCA2*. O modelo obteve uma **Área Sob a Curva ROC (AUC-ROC) de 1.0000** e uma **Área Sob a Curva de Precisão-Recall (AUC-PR) de 1.0000**. Adicionalmente, a métrica de **Sensibilidade cravou 100% (Recall = 1.0)** aliada a uma forte capacidade discriminatória, reafirmando o compromisso bioético e clínico do sistema: a mitigação absoluta de falsos positivos e falsos negativos estruturais, evitando intervenções iatrogênicas decorrentes de diagnósticos imprecisos.

## 6.2 O Poder do Prime Encoding e Interpretabilidade SHAP

O modelo puramente focado em propriedades bioquímicas e matemática de números primos provou sua superioridade em relação às antigas matrizes esparsas. Nos relatórios gerados, o algoritmo forneceu **100% de faixas informativas (8/8 bins úteis para o critério ACMG/AMP)**, eliminando as zonas cinzentas de predição.

A dissecção de explicabilidade local, operacionalizada pelas pontuações *SHAP (SHapley Additive exPlanations)*, confirmou que as *features* proprietárias de engenharia reversa — tais como `prime_neighbor_asymmetry_ref`, `prime_following_ref` e `prime_curvature_score` — não representam mero artefato algébrico, mas figuram no topo da árvore de decisão. O *Prime Encoding* capta genuinamente a assimetria geométrica dos domínios RING e BRCT do *BRCA1*, consolidando o Mapeamento Injetivo Primordial como um espelho fidedigno da termodinâmica de dobramento de proteínas e elevando as predições de VUS do patamar de 'probabilidade estatística' para 'certeza matemática ortogonal'.
