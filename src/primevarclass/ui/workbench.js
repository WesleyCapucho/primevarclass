const state = {
  models: [],
  batchCsvReport: "",
  batchMarkdownReport: "",
  jobs: [],
  selectedJobId: null,
  authEnabled: false,
  profiles: [],
  teams: [],
  activeProfile: null,
  activeTeam: null,
  releaseManifest: null,
  roadmap: null,
  publicCatalog: null,
  language: "pt-BR",
  activeModule: "onboarding",
};

const LANGUAGE_STORAGE_KEY = "primevarclass_language";

const UI_TEXT = {
  "pt-BR": {
    "document.title": "PrimeVarClass | Bancada científica",
    "skip.main": "Ir para o conteúdo principal",
    "hero.eyebrow": "Bancada científica",
    "hero.copy": "Plataforma operacional para consultar modelos, classificar variantes missense, ampliar avaliações multigênicas e destacar a inteligência baseada em números primos.",
    "hero.manual": "Manual do usuário",
    "hero.glossary": "Glossário",
    "hero.feedback": "Guia de feedback",
    "hero.stack": "Inferência interpretável com dados reais",
    "language.label": "Idioma",
    "api.key": "Chave da API",
    "api.key.placeholder": "Opcional; necessária se a autenticação estiver ativa",
    "api.save_key": "Salvar chave",
    "guide.kicker": "Introdução",
    "guide.title": "Guia rápido para usuários",
    "guide.mode": "Produto multiusuário bilíngue",
    "guide.lede": "Escolha um módulo acima para trabalhar com uma frente da plataforma por vez. O fluxo foi desenhado para orientar pesquisadores experientes e estudantes em genômica translacional sem misturar operação, validação e administração na mesma tela.",
    "guide.card1.title": "Configure acesso e equipe",
    "guide.card1.copy": "Salve a chave da API, escolha o perfil, associe a equipe científica e mantenha cada execução auditável.",
    "guide.card2.title": "Carregue modelos e dados reais",
    "guide.card2.copy": "Inspecione o catálogo de modelos, resolva fontes públicas e acompanhe ClinVar, gnomAD, MaveDB e BRCA Exchange.",
    "guide.card3.title": "Classifique, explique e compare",
    "guide.card3.copy": "Rode predição individual, triagem em lote, estudo congelado e comparação longitudinal entre estudos.",
    "guide.card4.title": "Feche evidência translacional",
    "guide.card4.copy": "Use proteômica, estrutura 3D, módulo quântico, feedback de piloto e critérios de publicação antes de afirmações fortes.",
    "readiness.validation": "Validação científica",
    "readiness.validation.copy": "Forte para submissão computacional; ainda requer confirmação experimental independente.",
    "readiness.software": "Fechamento de software",
    "readiness.software.copy": "Pipelines, artefatos, manifestos, gnomAD local e motores estruturais estão integrados.",
    "readiness.publication": "Prontidão para publicação",
    "readiness.publication.score": "Quase pronta",
    "readiness.publication.copy": "Apta para preprint/manuscrito computacional; artigo de alto impacto exige validação externa final.",
    "audience.beginner": "Iniciante de graduação",
    "audience.senior": "Pesquisador sênior",
    "audience.clinical": "Equipe clínico-científica",
    "audience.ops": "Gestor translacional",
    "module.onboarding": "Início",
    "module.models": "Modelos",
    "module.inference": "Predição",
    "module.team": "Equipe",
    "module.data": "Dados públicos",
    "module.studies": "Estudos",
    "module.science": "Ciência",
    "module.translation": "Impacto",
    "module.operations": "Operação",
  },
  en: {
    "document.title": "PrimeVarClass Workbench",
    "skip.main": "Skip to main content",
    "hero.eyebrow": "Scientific Workbench",
    "hero.copy": "Operational workbench for loading models, classifying missense variants, expanding the multigene benchmark, and making the prime-number intelligence layer explicit.",
    "hero.manual": "User manual",
    "hero.glossary": "Glossary",
    "hero.feedback": "Feedback playbook",
    "hero.stack": "FastAPI + registry + interpretable inference",
    "language.label": "Language",
    "api.key": "API key",
    "api.key.placeholder": "Optional; required only when authentication is enabled",
    "api.save_key": "Save key",
    "guide.kicker": "Onboarding",
    "guide.title": "Quick start for users",
    "guide.mode": "Bilingual multi-user product",
    "guide.lede": "Start with the workflow below. It is designed to guide both experienced researchers and students entering translational genomics, while keeping the scientific limits visible.",
    "guide.card1.title": "Set access and team",
    "guide.card1.copy": "Save the API key, choose a profile, connect the scientific team, and keep every execution auditable.",
    "guide.card2.title": "Load models and real data",
    "guide.card2.copy": "Inspect the registry, resolve public catalogs, and track ClinVar, gnomAD, MaveDB, and BRCA Exchange.",
    "guide.card3.title": "Classify, explain, compare",
    "guide.card3.copy": "Run single-variant inference, batch screening, frozen benchmarks, and longitudinal study comparisons.",
    "guide.card4.title": "Close translational evidence",
    "guide.card4.copy": "Use proteomics, 3D structure, the quantum module, pilot feedback, and publication criteria before making strong claims.",
    "readiness.validation": "Scientific validation",
    "readiness.validation.copy": "Strong for computational submission; still needs independent experimental confirmation.",
    "readiness.software": "Software closure",
    "readiness.software.copy": "Pipelines, artifacts, manifests, local gnomAD, and structural engines are integrated.",
    "readiness.publication": "Publication readiness",
    "readiness.publication.score": "Near-ready",
    "readiness.publication.copy": "Ready for preprint/computational manuscript; top-tier publication still needs final external validation.",
    "audience.beginner": "Undergraduate beginner",
    "audience.senior": "Senior researcher",
    "audience.clinical": "Clinical-scientific team",
    "audience.ops": "Translational lead",
    "module.onboarding": "Start",
    "module.models": "Models",
    "module.inference": "Prediction",
    "module.team": "Team",
    "module.data": "Public data",
    "module.studies": "Studies",
    "module.science": "Science",
    "module.translation": "Impact",
    "module.operations": "Operations",
  },
};

const STATIC_TEXT_PT = {
  "Registry": "Modelos",
  "Inference": "Predição",
  "Profiles": "Perfis",
  "Teams": "Equipes",
  "Training": "Treinamento",
  "Public Data": "Dados públicos",
  "Batch Screening": "Triagem em lote",
  "Benchmark": "Estudo",
  "Diagnostics": "Diagnóstico",
  "Multigene": "Ciência multigênica",
  "Pilot Ops": "Impacto translacional",
  "Comparison": "Comparação",
  "Longitudinal": "Monitoramento",
  "Provenance": "Rastreabilidade",
  "Analytics": "Análises",
  "Operations": "Operação",
  "Catalogo de modelos": "Catálogo de modelos",
  "Predicao de variante": "Predição de variante",
  "Treino por catalogo": "Treino por catálogo",
  "Catalogo publico real": "Catálogo público real",
  "Estudo publicavel": "Estudo publicável",
  "Fila e historico": "Fila e histórico",
  "Gerar bootstrap": "Gerar pacote inicial",
  "Executar dry-run": "Executar simulação",
  "Executar candidate study": "Executar estudo candidato",
  "Gerar protein impact": "Gerar impacto proteico",
  "Gerar quantum proteomics": "Gerar proteômica quântica",
  "Planejar rollout": "Planejar expansão",
  "Gerar scaffolds": "Gerar estruturas de estudo",
  "Real-data manifest": "Manifesto de dados reais",
  "Prime intelligence manifest": "Manifesto de inteligência prima",
  "Gene expansion output": "Saída da expansão gênica",
  "Biological discovery output": "Saída de descoberta biológica",
  "Multigene rollout output": "Saída da expansão multigênica",
  "Study factory output": "Saída das estruturas de estudo",
  "Biological discovery manifest": "Manifesto de descoberta biológica",
  "Protein impact output": "Saída de impacto proteico",
  "Protein impact manifest": "Manifesto de impacto proteico",
  "Quantum proteomics output": "Saída de proteômica quântica",
  "Quantum proteomics manifest": "Manifesto de proteômica quântica",
  "Validation credibility output": "Saída de credibilidade científica",
  "Validation credibility manifest": "Manifesto de credibilidade científica",
  "Prospective validation output": "Saída de validação prospectiva",
  "Prospective validation manifest": "Manifesto de validação prospectiva",
  "Annotation enrichment manifest": "Manifesto de enriquecimento de anotações",
  "Public sync closure manifest": "Manifesto de sincronização pública",
  "BRCA1 engine execution manifest": "Manifesto de execução BRCA1",
  "BRCA1 paired mutant manifest": "Manifesto de mutantes pareados BRCA1",
  "BRCA1 mutant geometry QC manifest": "Manifesto de geometria mutante BRCA1",
  "Rollout manifest": "Manifesto de expansão",
  "Workspace root para os scaffolds": "Raiz do workspace para estruturas de estudo",
  "Atualizar dashboard": "Atualizar painel",
  "Notas de feedback": "Notas de retorno",
  "Salvar feedback": "Salvar retorno",
  "Inspetor de manifest": "Inspetor de manifesto",
  "Caminho do manifest": "Caminho do manifesto",
  "Atualizar jobs": "Atualizar trabalhos",
};

const STATIC_TEXT_EN = {
  "Roadmap": "Roadmap",
  "Progresso do projeto": "Project progress",
  "Atualizar progresso": "Refresh progress",
  "Registry": "Registry",
  "Registro": "Registry",
  "Modelos": "Models",
  "Catalogo de modelos": "Model catalog",
  "Catálogo de modelos": "Model catalog",
  "Diretorio dos modelos": "Model directory",
  "Diretório dos modelos": "Model directory",
  "Carregar modelos": "Load models",
  "Experimento": "Experiment",
  "Feature set": "Feature set",
  "Modelo": "Model",
  "AUC-ROC": "AUC-ROC",
  "MCC": "MCC",
  "Inference": "Inference",
  "Inferência": "Inference",
  "Predicao de variante": "Variant prediction",
  "Predição de variante": "Variant prediction",
  "Gene": "Gene",
  "HGVS proteico": "Protein HGVS",
  "Threshold": "Threshold",
  "Limiar": "Threshold",
  "Modo de encoding": "Encoding mode",
  "Modo de codificação": "Encoding mode",
  "Híbrido + externo": "Hybrid + external",
  "Híbrido": "Hybrid",
  "Códon": "Codon",
  "Massa prima": "Prime mass",
  "Classificar variante": "Classify variant",
  "Profiles": "Profiles",
  "Perfis": "Profiles",
  "Perfil institucional": "Institutional profile",
  "ID do perfil": "Profile ID",
  "Nome exibido": "Display name",
  "Papel": "Role",
  "Instituicao": "Institution",
  "Instituição": "Institution",
  "Salvar e ativar perfil": "Save and activate profile",
  "Teams": "Teams",
  "Equipes": "Teams",
  "Time cientifico": "Scientific team",
  "Time científico": "Scientific team",
  "Equipe científica": "Scientific team",
  "ID do time": "Team ID",
  "Nome do time": "Team name",
  "Descricao": "Description",
  "Descrição": "Description",
  "Salvar e ativar time": "Save and activate team",
  "Training": "Training",
  "Treinamento": "Training",
  "Treino por catalogo": "Catalog-based training",
  "Treino por catálogo": "Catalog-based training",
  "Arquivo TOML de fontes": "Sources TOML file",
  "Diretorio de saida": "Output directory",
  "Diretório de saída": "Output directory",
  "Familias de modelo": "Model families",
  "Famílias de modelo": "Model families",
  "Enfileirar treino": "Queue training",
  "Public Data": "Public data",
  "Dados públicos": "Public data",
  "Catalogo publico real": "Real public catalog",
  "Catálogo público real": "Real public catalog",
  "Inspecionar catalogo": "Inspect catalog",
  "Inspecionar catálogo": "Inspect catalog",
  "Gerar bootstrap": "Generate bootstrap",
  "Resolver catalogo": "Resolve catalog",
  "Resolver catálogo": "Resolve catalog",
  "Executar dry-run": "Run dry-run",
  "Ver historico": "View history",
  "Ver histórico": "View history",
  "Arquivo TOML de fontes publicas": "Public sources TOML file",
  "Diretorio opcional para exportar relatorio": "Optional report output directory",
  "Diretório opcional para exportar relatório": "Optional report output directory",
  "Batch Screening": "Batch screening",
  "Triagem em lote": "Batch screening",
  "Variantes em CSV": "Variants as CSV",
  "Titulo do relatorio": "Report title",
  "Título do relatório": "Report title",
  "Triar lote": "Screen batch",
  "Baixar CSV": "Download CSV",
  "Baixar relatorio": "Download report",
  "Baixar relatório": "Download report",
  "Sample": "Sample",
  "Variante": "Variant",
  "Status": "Status",
  "Probabilidade": "Probability",
  "Prioridade": "Priority",
  "Benchmark": "Benchmark",
  "Benchmark científico": "Scientific benchmark",
  "Validação comparativa": "Comparative validation",
  "Estudo publicavel": "Publishable study",
  "Estudo publicável": "Publishable study",
  "Arquivo TOML de estudo": "Study TOML file",
  "Titulo do dossie cientifico": "Scientific dossier title",
  "Título do dossiê científico": "Scientific dossier title",
  "Enfileirar benchmark": "Queue benchmark",
  "Enfileirar validação": "Queue validation",
  "Diagnostics": "Diagnostics",
  "Diagnóstico": "Diagnostics",
  "Preflight e inspecao": "Preflight and inspection",
  "Preflight e inspeção": "Preflight and inspection",
  "Pré-validação e inspeção": "Preflight and inspection",
  "Preflight e inspeção": "Preflight and inspection",
  "Arquivo TOML de estudo para preflight": "Study TOML file for preflight",
  "Arquivo TOML de estudo para pré-validação": "Study TOML file for preflight",
  "Diretorio de saida do preflight": "Preflight output directory",
  "Diretório de saída do preflight": "Preflight output directory",
  "Executar preflight": "Run preflight",
  "Executar pré-validação": "Run preflight",
  "Diretorio de estudo exportado": "Exported study directory",
  "Diretório de estudo exportado": "Exported study directory",
  "Inspecionar estudo": "Inspect study",
  "Diretorio da resolucao publica do estudo": "Study public resolution directory",
  "Diretório da resolução pública do estudo": "Study public resolution directory",
  "Diretorio de entrega de dados reais": "Real-data delivery directory",
  "Diretório de entrega de dados reais": "Real-data delivery directory",
  "Resolver estudo publico": "Resolve public study",
  "Autopreencher handoff": "Autofill handoff",
  "Autopreencher entrega": "Autofill handoff",
  "Executar estudo publico final": "Run final public study",
  "Executar estudo público final": "Run final public study",
  "Executar candidate study": "Run candidate study",
  "Executar estudo candidato": "Run candidate study",
  "Multigene": "Multigene",
  "Multigênico": "Multigene",
  "Expansao cientifica e numeros primos": "Scientific expansion and prime numbers",
  "Expansão científica e números primos": "Scientific expansion and prime numbers",
  "Gerar gene expansion": "Generate gene expansion",
  "Gerar expansão gênica": "Generate gene expansion",
  "Gerar biological discovery": "Generate biological discovery",
  "Gerar descoberta biológica": "Generate biological discovery",
  "Gerar protein impact": "Generate protein impact",
  "Gerar quantum proteomics": "Generate quantum proteomics",
  "Fechar validação prospectiva": "Close prospective validation",
  "Fechar credibilidade": "Close credibility",
  "Planejar rollout": "Plan rollout",
  "Planejar expansão": "Plan rollout",
  "Gerar scaffolds": "Generate scaffolds",
  "Gerar estruturas de estudo": "Generate study structures",
  "ClinVar variant summary": "ClinVar variant summary",
  "MaveDB dump": "MaveDB dump",
  "Real-data manifest": "Real-data manifest",
  "Prime intelligence manifest": "Prime intelligence manifest",
  "Gene expansion output": "Gene expansion output",
  "Biological discovery output": "Biological discovery output",
  "Multigene rollout output": "Multigene rollout output",
  "Study factory output": "Study factory output",
  "Biological discovery manifest": "Biological discovery manifest",
  "Protein impact output": "Protein impact output",
  "Protein impact manifest": "Protein impact manifest",
  "Quantum proteomics output": "Quantum proteomics output",
  "Quantum proteomics manifest": "Quantum proteomics manifest",
  "Validation credibility output": "Validation credibility output",
  "Validation credibility manifest": "Validation credibility manifest",
  "Prospective validation output": "Prospective validation output",
  "Prospective validation manifest": "Prospective validation manifest",
  "Annotation enrichment manifest": "Annotation enrichment manifest",
  "Public sync closure manifest": "Public sync closure manifest",
  "BRCA1 engine execution manifest": "BRCA1 engine execution manifest",
  "BRCA1 paired mutant manifest": "BRCA1 paired mutant manifest",
  "BRCA1 mutant geometry QC manifest": "BRCA1 mutant geometry QC manifest",
  "Rollout manifest": "Rollout manifest",
  "Workspace root para os scaffolds": "Workspace root for scaffolds",
  "Pilot Ops": "Pilot ops",
  "Piloto translacional": "Translational pilot",
  "Impacto social e translacional": "Social and translational impact",
  "Atualizar dashboard": "Refresh dashboard",
  "Estudo": "Study",
  "Site": "Site",
  "Session ID": "Session ID",
  "ID da sessão": "Session ID",
  "Modo do piloto": "Pilot mode",
  "Modo sombra": "Shadow mode",
  "Demonstração": "Demo mode",
  "Validação interna": "Internal validation",
  "Candidato em uso real": "Live candidate",
  "Planejada": "Planned",
  "Em execução": "Running",
  "Concluída": "Completed",
  "Cancelada": "Cancelled",
  "Casos revisados": "Cases reviewed",
  "Variantes sinalizadas": "Flagged variants",
  "Resumo da sessao": "Session summary",
  "Salvar sessao": "Save session",
  "Salvar sessão": "Save session",
  "Confianca (0-5)": "Confidence (0-5)",
  "Confiança (0-5)": "Confidence (0-5)",
  "Acionabilidade (0-5)": "Actionability (0-5)",
  "Tempo economizado (min)": "Time saved (min)",
  "Recomendacao": "Recommendation",
  "Recomendação": "Recommendation",
  "Recomendada": "Recommended",
  "Condicional": "Conditional",
  "Não recomendada": "Not recommended",
  "Nivel de incidente": "Incident level",
  "Nível de incidente": "Incident level",
  "Nenhum": "None",
  "Baixo": "Low",
  "Médio": "Medium",
  "Alto": "High",
  "Notas de feedback": "Feedback notes",
  "Salvar feedback": "Save feedback",
  "Comparison": "Comparison",
  "Comparação": "Comparison",
  "Comparar estudos": "Compare studies",
  "Estudo baseline": "Baseline study",
  "Estudo de referência": "Baseline study",
  "Estudo candidato": "Candidate study",
  "Titulo do comparativo": "Comparison title",
  "Título do comparativo": "Comparison title",
  "Longitudinal": "Longitudinal",
  "Acompanhamento": "Longitudinal",
  "Monitor longitudinal": "Longitudinal monitor",
  "Diretorios de estudo": "Study directories",
  "Diretórios de estudo": "Study directories",
  "Titulo do monitor": "Monitor title",
  "Título do monitor": "Monitor title",
  "Gerar monitor longitudinal": "Generate longitudinal monitor",
  "Provenance": "Provenance",
  "Proveniência": "Provenance",
  "Inspetor de manifest": "Manifest inspector",
  "Inspecionar": "Inspect",
  "Caminho do manifest": "Manifest path",
  "Analytics": "Analytics",
  "Indicadores": "Analytics",
  "Dashboard do time": "Team dashboard",
  "Painel da equipe": "Team dashboard",
  "Lançamento": "Launch",
  "Prontidão científica e web": "Scientific and web readiness",
  "Avaliar prontidão": "Assess readiness",
  "Operations": "Operations",
  "Operação": "Operations",
  "Fila e historico": "Queue and history",
  "Atualizar jobs": "Refresh jobs",
  "Job": "Job",
  "Tipo": "Type",
  "Criado em": "Created at",
  "Finalizado em": "Finished at",
  "Nenhum job disponivel.": "No jobs available.",
  "Nenhuma triagem executada ainda.": "No screening has been run yet.",
  "Carregue um `model_registry.csv` para inspecionar os modelos exportados.": "Load a `model_registry.csv` to inspect exported models.",
};

const PORTUGUESE_TEXT_FIXES = [
  ["Portugu\u00c3\u00aas-BR", "Português-BR"],
  ["Portugu\u00c3\u00a9s-BR", "Português-BR"],
  ["n\u00c3\u00bameros", "números"],
  ["n\u00c3\u0192\u00c2\u00bameros", "números"],
  ["Valida\u00c3\u00a7\u00c3\u00a3o", "Validação"],
  ["conteudo", "conteúdo"],
  ["laboratorio", "laboratório"],
  ["usuario", "usuário"],
  ["usuarios", "usuários"],
  ["Glossario", "Glossário"],
  ["Referencias", "Referências"],
  ["inferencia", "inferência"],
  ["interpretavel", "interpretável"],
  ["necessario", "necessário"],
  ["necessaria", "necessária"],
  ["autenticacao", "autenticação"],
  ["rapido", "rápido"],
  ["multiusuario", "multiusuário"],
  ["bilingue", "bilíngue"],
  ["estao", "estão"],
  ["genomica", "genômica"],
  ["cientificos", "científicos"],
  ["cientifica", "científica"],
  ["cientifico", "científico"],
  ["execucao", "execução"],
  ["catalogos publicos", "catálogos públicos"],
  ["publicas", "públicas"],
  ["publicos", "públicos"],
  ["multigenico", "multigênico"],
  ["inteligencia", "inteligência"],
  ["numeros primos", "números primos"],
  ["comparacao", "comparação"],
  ["evidencia", "evidência"],
  ["proteomica", "proteômica"],
  ["modulo quantico", "módulo quântico"],
  ["criterios de publicacao", "critérios de publicação"],
  ["confirmacao", "confirmação"],
  ["Prontidao", "Prontidão"],
  ["publicacao", "publicação"],
  ["graduacao", "graduação"],
  ["senior", "sênior"],
  ["clinico-cientifica", "clínico-científica"],
  ["disponivel", "disponível"],
  ["indisponivel", "indisponível"],
  ["relatorio", "relatório"],
  ["validacao", "validação"],
  ["publico", "público"],
  ["publica", "pública"],
  ["preparacao", "preparação"],
  ["ha fontes", "há fontes"],
  ["nao", "não"],
  ["Nao", "Não"],
  ["contem", "contém"],
  ["Proximo", "Próximo"],
  ["proximo", "próximo"],
  ["prontidao", "prontidão"],
  ["sincronizacao", "sincronização"],
  ["diagnostico", "diagnóstico"],
  ["estatistico", "estatístico"],
  ["biologica", "biológica"],
  ["biologico", "biológico"],
  ["aparecerao", "aparecerão"],
  ["aparecera", "aparecerá"],
  ["diretorios", "diretórios"],
  ["diretorio", "diretório"],
  ["Titulo", "Título"],
  ["titulo", "título"],
  ["Confianca", "Confiança"],
  ["confianca", "confiança"],
  ["Recomendacao", "Recomendação"],
  ["recomendacao", "recomendação"],
  ["Nivel", "Nível"],
  ["nivel", "nível"],
  ["evolucao", "evolução"],
  ["concluida", "concluída"],
  ["concluidas", "concluídas"],
  ["concluidos", "concluídos"],
  ["revisao", "revisão"],
  ["pendencias", "pendências"],
  ["reconciliacao", "reconciliação"],
  ["hipoteses", "hipóteses"],
  ["media QM", "média QM"],
  ["rerrodada", "nova rodada"],
  ["sessao", "sessão"],
  ["Resolucao", "Resolução"],
  ["resolucao", "resolução"],
  ["output_dir", "diretório de saída"],
  ["config_path", "caminho da configuração"],
  ["rollout", "expansão"],
  ["scaffolds", "estruturas de estudo"],
  ["dashboard", "painel"],
  ["Dashboard", "Painel"],
  ["jobs", "trabalhos"],
  ["job", "trabalho"],
  ["Job", "Trabalho"],
  ["manifest", "manifesto"],
  ["Manifest", "Manifesto"],
  ["templates", "modelos"],
  ["claims", "afirmações"],
  ["saida", "saída"],
  ["historico", "histórico"],
  ["Inspecao", "Inspeção"],
  ["inspecao", "inspeção"],
  ["Predicao", "Predição"],
  ["Catalogo", "Catálogo"],
  ["catalogo", "catálogo"],
  ["priorizacao", "priorização"],
  ["operacao", "operação"],
  ["Operacao", "Operação"],
  ["real-data readiness", "prontidão com dados reais"],
  ["claim strength", "força das afirmações"],
  ["validation lock", "trava de validação"],
  ["candidate study", "estudo candidato"],
  ["Candidate study", "Estudo candidato"],
  ["candidate config", "configuração candidata"],
  ["gene expansion", "expansão gênica"],
  ["Gene expansion", "Expansão gênica"],
  ["biological discovery", "descoberta biológica"],
  ["Biological discovery", "Descoberta biológica"],
  ["protein impact", "impacto proteico"],
  ["Protein impact", "Impacto proteico"],
  ["quantum proteomics", "proteômica quântica"],
  ["Quantum proteomics", "Proteômica quântica"],
  ["prime intelligence", "inteligência prima"],
  ["handoff", "entrega"],
  ["Release", "Versão"],
  ["release", "versão"],
  ["fingerprints", "assinaturas digitais"],
  ["fetch", "coleta"],
  ["Autofill", "Autopreenchimento"],
  ["Sync", "Sincronização"],
  ["sync", "sincronização"],
];

const PORTUGUESE_TEXT_SKIP_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "PRE", "CODE"]);
let isNormalizingPortugueseText = false;

function normalizePortugueseSourceText(value) {
  let next = String(value ?? "");
  PORTUGUESE_TEXT_FIXES.forEach(([from, to]) => {
    next = next.split(from).join(to);
  });
  return next;
}

function byId(id) {
  return document.getElementById(id);
}

function getStoredLanguage() {
  return window.localStorage.getItem(LANGUAGE_STORAGE_KEY) === "en" ? "en" : "pt-BR";
}

function setStoredLanguage(value) {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY, value === "en" ? "en" : "pt-BR");
}

function t(key) {
  return (UI_TEXT[state.language] || UI_TEXT["pt-BR"])[key] || UI_TEXT["pt-BR"][key] || key;
}

function l(ptText, enText) {
  return state.language === "en" ? enText : ptText;
}

function applyStaticTranslations() {
  const selector = [
    "h2",
    ".panel-kicker",
    "button",
    "a.action-chip",
    "label.field > span",
    "th",
    ".empty-cell",
    "option",
  ].join(", ");
  document.querySelectorAll(selector).forEach((element) => {
    if (element.dataset.i18n || element.id === "language-select") {
      return;
    }
    if (!element.dataset.i18nOriginal) {
      element.dataset.i18nOriginal = normalizePortugueseSourceText(element.textContent.trim());
    }
    const original = element.dataset.i18nOriginal;
    element.textContent = state.language === "en"
      ? (STATIC_TEXT_EN[original] || original)
      : (STATIC_TEXT_PT[original] || original);
  });
}

function updateKnowledgeLinks() {
  const suffix = state.language === "en" ? "_en" : "";
  byId("manual-link").href = `/knowledge/manual${suffix}.pdf`;
  byId("glossary-link").href = `/knowledge/glossary${suffix}.pdf`;
  byId("feedback-link").href = `/knowledge/feedback${suffix}`;
}

function normalizePortugueseTextNode(node) {
  if (state.language !== "pt-BR" || !node || node.nodeType !== Node.TEXT_NODE) {
    return;
  }
  const parent = node.parentElement;
  if (!parent || PORTUGUESE_TEXT_SKIP_TAGS.has(parent.tagName)) {
    return;
  }
  const normalized = normalizePortugueseSourceText(node.nodeValue);
  if (normalized !== node.nodeValue) {
    node.nodeValue = normalized;
  }
}

function normalizePortugueseSubtree(root) {
  if (state.language !== "pt-BR" || !root) {
    return;
  }
  if (root.nodeType === Node.TEXT_NODE) {
    normalizePortugueseTextNode(root);
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE || PORTUGUESE_TEXT_SKIP_TAGS.has(root.tagName)) {
    return;
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    normalizePortugueseTextNode(walker.currentNode);
  }
}

function normalizeVisiblePortugueseText() {
  normalizePortugueseSubtree(document.body);
  document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((element) => {
    element.setAttribute("placeholder", normalizePortugueseSourceText(element.getAttribute("placeholder")));
  });
}

function setupPortugueseTextObserver() {
  if (!window.MutationObserver) {
    return;
  }
  const observer = new MutationObserver((mutations) => {
    if (isNormalizingPortugueseText || state.language !== "pt-BR") {
      return;
    }
    isNormalizingPortugueseText = true;
    try {
      mutations.forEach((mutation) => {
        if (mutation.type === "characterData") {
          normalizePortugueseTextNode(mutation.target);
          return;
        }
        mutation.addedNodes.forEach((node) => {
          normalizePortugueseSubtree(node);
        });
      });
    } finally {
      isNormalizingPortugueseText = false;
    }
  });
  observer.observe(document.body, { childList: true, characterData: true, subtree: true });
}

function normalizeDefaultPaths() {
  document.querySelectorAll("input").forEach((input) => {
    if (typeof input.value === "string" && /[\u00c3\u00c2]/.test(input.value)) {
      input.value = normalizePortugueseSourceText(input.value);
      return;
    }
    if (typeof input.value === "string" && (input.value.includes("Ã") || input.value.includes("Â"))) {
      input.value = normalizePortugueseSourceText(input.value);
    }
  });
}

function showModule(moduleName) {
  const selected = moduleName || "onboarding";
  state.activeModule = selected;
  document.querySelectorAll("[data-module-panel]").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.modulePanel === selected);
  });
  document.querySelectorAll("[data-module-target]").forEach((button) => {
    const isActive = button.dataset.moduleTarget === selected;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });
}

function setupModuleSwitcher() {
  document.querySelectorAll("[data-module-target]").forEach((button) => {
    button.addEventListener("click", () => {
      showModule(button.dataset.moduleTarget);
    });
  });
  showModule(state.activeModule);
}

function applyTranslations() {
  document.documentElement.lang = state.language;
  document.title = t("document.title");
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
  });
  applyStaticTranslations();
  updateKnowledgeLinks();
  normalizeVisiblePortugueseText();
  normalizeDefaultPaths();
}

function setLanguage(value) {
  state.language = value === "en" ? "en" : "pt-BR";
  setStoredLanguage(state.language);
  const selector = byId("language-select");
  if (selector) {
    selector.value = state.language;
  }
  applyTranslations();
}

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function getStoredApiKey() {
  return window.localStorage.getItem("primevarclass_api_key") || "";
}

function setStoredApiKey(value) {
  window.localStorage.setItem("primevarclass_api_key", value || "");
}

function getStoredProfileId() {
  return window.localStorage.getItem("primevarclass_profile_id") || "";
}

function setStoredProfileId(value) {
  if (value) {
    window.localStorage.setItem("primevarclass_profile_id", value);
    return;
  }
  window.localStorage.removeItem("primevarclass_profile_id");
}

function getStoredTeamId() {
  return window.localStorage.getItem("primevarclass_team_id") || "";
}

function setStoredTeamId(value) {
  if (value) {
    window.localStorage.setItem("primevarclass_team_id", value);
    return;
  }
  window.localStorage.removeItem("primevarclass_team_id");
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function setConsole(id, value) {
  const text = typeof value === "string"
    ? (state.language === "pt-BR" ? normalizePortugueseSourceText(value) : value)
    : prettyJson(value);
  byId(id).textContent = text;
}

function renderStudyValidationDetail(source) {
  const summary = (source && source.summary) || source || {};
  setConsole("study-validation-detail", {
    real_data_readiness_percent: summary.real_data_readiness_percent ?? null,
    ready_for_real_data_study: summary.ready_for_real_data_study ?? null,
    real_data_handoff_percent: summary.real_data_handoff_percent ?? null,
    real_data_handoff_autofill_percent: summary.real_data_handoff_autofill_percent ?? null,
    real_data_handoff_reconciliation_percent: summary.real_data_handoff_reconciliation_percent ?? null,
    real_data_handoff_application_percent: summary.real_data_handoff_application_percent ?? null,
    real_data_candidate_promotion_percent: summary.real_data_candidate_promotion_percent ?? null,
    ready_for_lab_handoff: summary.ready_for_lab_handoff ?? null,
    n_real_data_tasks: summary.n_real_data_tasks ?? null,
    n_critical_real_data_tasks: summary.n_critical_real_data_tasks ?? null,
    n_handoff_autofilled_tasks: summary.n_handoff_autofilled_tasks ?? null,
    n_handoff_preserved_completed_tasks: summary.n_handoff_preserved_completed_tasks ?? null,
    n_handoff_unmatched_tasks: summary.n_handoff_unmatched_tasks ?? null,
    n_handoff_validated_tasks: summary.n_handoff_validated_tasks ?? null,
    n_handoff_pending_tasks: summary.n_handoff_pending_tasks ?? null,
    n_handoff_invalid_tasks: summary.n_handoff_invalid_tasks ?? null,
    ready_for_reconciliation_rerun_from_autofill: summary.ready_for_reconciliation_rerun_from_autofill ?? null,
    n_handoff_applied_changes: summary.n_handoff_applied_changes ?? null,
    ready_to_rerun_resolution_from_handoff: summary.ready_to_rerun_resolution_from_handoff ?? null,
    ready_to_rerun_public_study_from_handoff: summary.ready_to_rerun_public_study_from_handoff ?? null,
    ready_for_candidate_resolution_from_handoff: summary.ready_for_candidate_resolution_from_handoff ?? null,
    ready_for_candidate_public_study_from_handoff: summary.ready_for_candidate_public_study_from_handoff ?? null,
    ready_to_promote_candidate_config: summary.ready_to_promote_candidate_config ?? null,
    ready_to_run_candidate_public_study: summary.ready_to_run_candidate_public_study ?? null,
    claim_strength_percent: summary.claim_strength_percent ?? null,
    claim_tier: summary.claim_tier ?? null,
    validation_lock_percent: summary.validation_lock_percent ?? null,
    validation_ready_for_submission_lock: summary.validation_ready_for_submission_lock ?? null,
    validation_ready_for_statistical_validation: summary.validation_ready_for_statistical_validation ?? null,
    validation_ready_for_translational_pilot: summary.validation_ready_for_translational_pilot ?? null,
    pilot_package_percent: summary.pilot_package_percent ?? null,
    pilot_mode: summary.pilot_mode ?? null,
    ready_for_demo_pilot: summary.ready_for_demo_pilot ?? null,
    ready_for_shadow_pilot: summary.ready_for_shadow_pilot ?? null,
    ready_for_live_pilot: summary.ready_for_live_pilot ?? null,
    translational_impact_percent: summary.translational_impact_percent ?? null,
    platform_completion_percent: summary.platform_completion_percent ?? null,
    development_complete: summary.development_complete ?? null,
    scientific_validation_pending: summary.scientific_validation_pending ?? null,
    evidence_execution_percent: summary.evidence_execution_percent ?? null,
    ready_for_assisted_pilot_ops: summary.ready_for_assisted_pilot_ops ?? null,
    ready_for_shadow_rollout: summary.ready_for_shadow_rollout ?? null,
    ready_for_institutional_rollout: summary.ready_for_institutional_rollout ?? null,
    final_mile_percent: summary.final_mile_percent ?? null,
    ready_for_real_data_execution: summary.ready_for_real_data_execution ?? null,
    ready_for_final_evidence_round: summary.ready_for_final_evidence_round ?? null,
    ready_for_submission_closeout: summary.ready_for_submission_closeout ?? null,
    ready_for_live_transition: summary.ready_for_live_transition ?? null,
    n_final_mile_blockers: summary.n_final_mile_blockers ?? null,
    n_final_mile_critical_blockers: summary.n_final_mile_critical_blockers ?? null,
    top_final_mile_blocker_phase: summary.top_final_mile_blocker_phase ?? null,
    top_final_mile_blocker_title: summary.top_final_mile_blocker_title ?? null,
  });
}

function fillProfileForm(profile) {
  if (!profile) {
    return;
  }
  byId("profile-id").value = profile.profile_id || "";
  byId("profile-name").value = profile.display_name || "";
  byId("profile-role").value = profile.role || "";
  byId("profile-institution").value = profile.institution || "";
}

function fillTeamForm(team) {
  if (!team || team.is_guest) {
    return;
  }
  byId("team-id").value = team.team_id || "";
  byId("team-name").value = team.display_name || "";
  byId("team-institution").value = team.institution || "";
  byId("team-description").value = team.description || "";
}

function updateExperimentSelect(models) {
  const select = byId("predict-experiment");
  const batchSelect = byId("batch-experiment");
  const currentValue = select.value;
  const currentBatchValue = batchSelect.value;
  select.innerHTML = "";
  batchSelect.innerHTML = "";
  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.experiment;
    option.textContent = model.experiment;
    select.appendChild(option);
    batchSelect.appendChild(option.cloneNode(true));
  });
  if (models.some((item) => item.experiment === currentValue)) {
    select.value = currentValue;
  }
  if (models.some((item) => item.experiment === currentBatchValue)) {
    batchSelect.value = currentBatchValue;
  }
}

function renderModelsTable(models) {
  const body = byId("models-table-body");
  body.innerHTML = "";
  if (!models.length) {
    body.innerHTML = '<div class="empty-cell">Nenhum modelo encontrado.</div>';
    return;
  }

  models.forEach((model) => {
    const row = document.createElement("article");
    row.className = "result-row";
    row.innerHTML = `
      <div class="result-row-main">
        <strong>${model.experiment ?? ""}</strong>
        <span>${model.feature_set ?? ""} | ${model.model_family ?? ""}</span>
      </div>
      <div class="result-row-metrics">
        <span>AUC-ROC <strong>${model.auc_roc ?? "-"}</strong></span>
        <span>MCC <strong>${model.mcc ?? "-"}</strong></span>
      </div>
    `;
    body.appendChild(row);
  });
}

function renderPredictionCard(payload) {
  const card = byId("prediction-card");
  card.classList.remove("result-card-empty");
  card.innerHTML = `
    <div class="metric-band">
      <div class="metric-tile">
        <div class="metric-label">${l("Probabilidade", "Probability")}</div>
        <div class="metric-value">${Number(payload.predicted_probability).toFixed(4)}</div>
      </div>
      <div class="metric-tile">
        <div class="metric-label">${l("Classe", "Class")}</div>
        <div class="metric-value">${payload.predicted_label === 1 ? l("Patogenica-like", "Pathogenic-like") : l("Benigna-like", "Benign-like")}</div>
      </div>
      <div class="metric-tile">
        <div class="metric-label">${l("Modelo", "Model")}</div>
        <div class="metric-value">${payload.model_family ?? "-"}</div>
      </div>
    </div>
    <div class="meta-block">
      <h3>${l("Contexto", "Context")}</h3>
      <ul class="meta-list">
        <li>${l("Experimento", "Experiment")}: ${payload.experiment}</li>
        <li>Feature set: ${payload.feature_set ?? "-"}</li>
        <li>${l("Variante", "Variant")}: ${payload.variant}</li>
        <li>Threshold: ${payload.threshold}</li>
      </ul>
    </div>
    <div class="meta-block">
      <h3>${l("Evidencias interpretaveis", "Interpretable evidence")}</h3>
      <ul class="evidence-list">
        ${payload.evidence_summary.map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderRoadmapStages(stages) {
  const container = byId("roadmap-stage-list");
  container.innerHTML = "";
  if (!stages || !stages.length) {
    container.innerHTML = `
      <div class="progress-stage-card">
        <div class="progress-stage-head">
          <strong>Nenhuma etapa disponível</strong>
          <span class="progress-stage-percent">0%</span>
        </div>
        <div class="progress-bar-track"><div class="progress-bar-fill" style="width: 0%"></div></div>
        <p class="progress-stage-copy">O roteiro ainda não foi carregado.</p>
      </div>
    `;
    return;
  }

  stages.forEach((stage) => {
    const card = document.createElement("div");
    card.className = "progress-stage-card";
    card.innerHTML = `
      <div class="progress-stage-head">
        <strong>${stage.title}</strong>
        <span class="progress-stage-percent">${stage.progress_percent}%</span>
      </div>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" style="width: ${stage.progress_percent}%"></div>
      </div>
      <div class="progress-stage-meta">${String(stage.status || "").replace("_", " ")}</div>
      <p class="progress-stage-copy">${stage.delivered}</p>
      <p class="progress-stage-copy"><strong>Próximo alvo:</strong> ${stage.next_target}</p>
    `;
    container.appendChild(card);
  });
}

function renderPublicCatalogSources(sources) {
  const container = byId("public-catalog-stage-list");
  container.innerHTML = "";
  if (!sources || !sources.length) {
    container.innerHTML = `
      <div class="progress-stage-card">
        <div class="progress-stage-head">
          <strong>Nenhuma fonte reconhecida</strong>
          <span class="progress-stage-percent">0%</span>
        </div>
        <div class="progress-bar-track"><div class="progress-bar-fill" style="width: 0%"></div></div>
        <p class="progress-stage-copy">O catálogo ainda não foi inspecionado ou não contém fontes públicas reconhecidas.</p>
      </div>
    `;
    return;
  }

  sources.forEach((source) => {
    const progressPercent = source.benchmark_readiness_percent ?? source.readiness_percent ?? source.coverage_percent ?? 0;
    const card = document.createElement("div");
    card.className = "progress-stage-card";
    card.innerHTML = `
      <div class="progress-stage-head">
        <strong>${source.display_name || source.source_name}</strong>
        <span class="progress-stage-percent">${progressPercent}%</span>
      </div>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" style="width: ${progressPercent}%"></div>
      </div>
      <div class="progress-stage-meta">${source.latest_execution_status || source.release_method || "unknown"}</div>
      <p class="progress-stage-copy">Fonte: ${source.source_name} | Release: ${source.release_value || "-"}</p>
      <p class="progress-stage-copy">Cobertura de esquema: ${source.schema_coverage_percent ?? 0}% | Pronta: ${source.ready_for_public_use ? "sim" : "ainda não"}</p>
      <p class="progress-stage-copy">Sincronização: ${source.latest_execution_status || "never_run"} | Prontidão de benchmark: ${source.benchmark_readiness_percent ?? 0}%</p>
      <p class="progress-stage-copy">Próximo passo: ${source.sync_next_action || source.next_action || "Definir sincronização."}</p>
      <p class="progress-stage-copy">${(source.warnings && source.warnings[0]) || (source.schema_warnings && source.schema_warnings[0]) || "Fonte pronta para rastreabilidade pública."}</p>
    `;
    container.appendChild(card);
  });
}

function buildPublicCatalogSources(payload) {
  const syncPlan = payload.sync_plan || {};
  const syncItems = syncPlan.sync_items || [];
  const syncHistory = payload.sync_history || {};
  const sourceStatuses = syncHistory.source_statuses || [];
  const benchmarkSources = ((payload.benchmark_readiness || {}).sources) || [];
  return (payload.sources || []).map((source) => {
    const syncItem = syncItems.find((item) => item.source_name === source.source_name) || {};
    const statusItem = sourceStatuses.find((item) => item.source_name === source.source_name) || {};
    const benchmarkItem = benchmarkSources.find((item) => item.source_name === source.source_name) || {};
    return {
      ...source,
      sync_next_action: syncItem.next_action || null,
      sync_strategy: syncItem.sync_strategy || null,
      latest_execution_status: statusItem.latest_execution_status || null,
      latest_run_started_at: statusItem.latest_run_started_at || null,
      sync_readiness_percent: statusItem.sync_readiness_percent ?? null,
      benchmark_readiness_percent: benchmarkItem.benchmark_readiness_percent ?? source.readiness_percent ?? 0,
      has_execution_ready_bundle: statusItem.has_execution_ready_bundle || false,
    };
  });
}

function updatePublicCatalogSummary(payload, overrideText = null) {
  if (overrideText) {
    byId("public-catalog-summary").textContent = overrideText;
    return;
  }
  const summary = payload.summary || payload.catalog_summary || {};
  const syncSummary = (payload.sync_history || {}).summary || {};
  const benchmarkSummary = ((payload.benchmark_readiness || {}).summary) || (((payload.sync_history || {}).benchmark_readiness || {}).summary) || {};
  byId("public-catalog-summary").textContent =
    `${summary.n_recognized_public_sources ?? 0} fontes públicas reconhecidas | ` +
    `release ${summary.release_coverage_percent ?? 0}% | ` +
    `esquema ${summary.schema_coverage_percent ?? 0}% | ` +
    `sincronização ${benchmarkSummary.sync_readiness_percent ?? syncSummary.sync_readiness_percent ?? 0}% | ` +
    `benchmark ${benchmarkSummary.benchmark_readiness_percent ?? 0}% | ` +
    `${benchmarkSummary.ready_for_live_public_benchmark ? "pronto para busca pública controlada" : "ainda em preparação operacional"}.`;
}

function renderJobsTable(jobs) {
  const body = byId("jobs-table-body");
  body.innerHTML = "";
  if (!jobs.length) {
    body.innerHTML = '<div class="empty-cell">Nenhum trabalho disponível.</div>';
    byId("jobs-summary").textContent = "Nenhum trabalho carregado ainda.";
    return;
  }

  const activeCount = jobs.filter((job) => ["queued", "running"].includes(job.status)).length;
  byId("jobs-summary").textContent = `${jobs.length} trabalhos carregados, ${activeCount} ativos no momento.`;

  jobs.forEach((job) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "result-row result-row-button";
    row.innerHTML = `
      <span class="result-row-main">
        <strong>${job.job_type}</strong>
        <span>${job.job_id}</span>
      </span>
      <span class="result-row-metrics">
        <span>Status <strong>${job.status}</strong></span>
        <span>Criado <strong>${job.created_at ?? "-"}</strong></span>
        <span>Finalizado <strong>${job.finished_at ?? "-"}</strong></span>
      </span>
    `;
    row.addEventListener("click", () => {
      state.selectedJobId = job.job_id;
      setConsole("job-detail", job);
      const manifestPath = job.result?.study_release_manifest_path || job.result?.data_release_manifest_path;
      if (manifestPath) {
        byId("release-manifest-path").value = manifestPath;
      }
    });
    body.appendChild(row);
  });

  const selected = jobs.find((job) => job.job_id === state.selectedJobId) || jobs[0];
  if (selected) {
    state.selectedJobId = selected.job_id;
    setConsole("job-detail", selected);
    const manifestPath = selected.result?.study_release_manifest_path || selected.result?.data_release_manifest_path;
    if (manifestPath) {
      byId("release-manifest-path").value = manifestPath;
    }
  }
}

function parseBatchCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) {
    throw new Error("Informe um CSV com cabecalho e pelo menos uma variante.");
  }
  const headers = lines[0].split(",").map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",").map((item) => item.trim());
    const row = Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
    const featurePayload = {};
    ["phylop", "gerp", "siphy", "revel", "feature_gnomad_af", "feature_mave_score"].forEach((key) => {
      const numericValue = numberOrNull(row[key]);
      if (numericValue !== null) {
        featurePayload[key] = numericValue;
      }
    });
    return {
      sample_id: row.sample_id || null,
      gene: row.gene,
      hgvs_p: row.hgvs_p,
      feature_payload: featurePayload,
    };
  });
}

function parseLineList(text) {
  return String(text || "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderBatchTable(rows) {
  const body = byId("batch-table-body");
  body.innerHTML = "";
  if (!rows.length) {
    body.innerHTML = '<div class="empty-cell">Nenhuma triagem executada ainda.</div>';
    return;
  }
  rows.forEach((row) => {
    const probability = row.predicted_probability === null || row.predicted_probability === undefined
      ? "-"
      : Number(row.predicted_probability).toFixed(4);
    const tableRow = document.createElement("article");
    tableRow.className = "result-row";
    tableRow.innerHTML = `
      <div class="result-row-main">
        <strong>${row.variant ?? `${row.gene ?? ""} ${row.hgvs_p ?? ""}`}</strong>
        <span>${row.sample_id ?? "Amostra sem identificador"} | ${row.status}</span>
      </div>
      <div class="result-row-metrics">
        <span>Probabilidade <strong>${probability}</strong></span>
        <span>Prioridade <strong>${row.priority_tier ?? "-"}</strong></span>
      </div>
    `;
    body.appendChild(tableRow);
  });
}

async function apiJson(url, options = {}) {
  const { omitTeamHeader = false, headers = {}, ...fetchOptions } = options;
  const authHeaders = {};
  const apiKey = getStoredApiKey();
  if (apiKey) {
    authHeaders["X-API-Key"] = apiKey;
  }
  const profileId = getStoredProfileId();
  if (profileId) {
    authHeaders["X-PrimeVarClass-Profile"] = profileId;
  }
  const teamId = getStoredTeamId();
  if (teamId && !omitTeamHeader) {
    authHeaders["X-PrimeVarClass-Team"] = teamId;
  }
  const response = await fetch(url, {
    ...fetchOptions,
    headers: { "Content-Type": "application/json", ...authHeaders, ...headers },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || prettyJson(payload));
  }
  return payload;
}

async function loadHealth() {
  const pill = byId("health-pill");
  try {
    const payload = await apiJson("/health", { method: "GET", headers: {} });
    pill.textContent = `${payload.service} online`;
  } catch (error) {
    pill.textContent = "API indisponível";
  }
}

async function loadAuthStatus() {
  const pill = byId("auth-pill");
  try {
    const payload = await apiJson("/auth/status", { method: "GET", headers: {} });
    state.authEnabled = Boolean(payload.auth_enabled);
    pill.textContent = payload.auth_enabled
      ? `Autenticação ativa ${payload.api_key_hint ? `(${payload.api_key_hint})` : ""}`
      : "Autenticação desativada";
  } catch (error) {
    pill.textContent = "Autenticação indisponível";
  }
}

async function loadUserContext() {
  const pill = byId("profile-pill");
  try {
    const payload = await apiJson("/users/context", { method: "GET", headers: {} });
    state.activeProfile = payload.active_profile || null;
    if (state.activeProfile && !state.activeProfile.is_guest) {
      fillProfileForm(state.activeProfile);
      pill.textContent = `${state.activeProfile.display_name} (${state.activeProfile.role || "user"})`;
    } else {
      pill.textContent = "Perfil local";
    }
    setConsole("profile-summary", payload);
  } catch (error) {
    pill.textContent = "Perfil indisponível";
    setConsole("profile-summary", `Falha ao carregar perfil: ${error.message}`);
  }
}

async function loadProfiles() {
  try {
    const payload = await apiJson("/users/profiles", { method: "GET", headers: {}, omitTeamHeader: true });
    state.profiles = payload.profiles || [];
    const selectedProfile = state.profiles.find((item) => item.profile_id === getStoredProfileId());
    if (selectedProfile) {
      fillProfileForm(selectedProfile);
    }
    if (!state.activeProfile || state.activeProfile.is_guest) {
      setConsole("profile-summary", payload);
    }
  } catch (error) {
    if (!byId("profile-summary").textContent) {
      setConsole("profile-summary", `Falha ao carregar perfis: ${error.message}`);
    }
  }
}

async function loadTeamContext() {
  const pill = byId("team-pill");
  try {
    const payload = await apiJson("/teams/context", { method: "GET", headers: {} });
    state.activeTeam = payload.active_team || null;
    if (state.activeTeam && !state.activeTeam.is_guest) {
      fillTeamForm(state.activeTeam);
      pill.textContent = `${state.activeTeam.display_name} (${state.activeTeam.member_role || "member"})`;
    } else {
      pill.textContent = "Equipe local";
    }
    setConsole("team-summary", payload);
  } catch (error) {
    pill.textContent = "Equipe indisponível";
    setConsole("team-summary", `Falha ao carregar equipe: ${error.message}`);
  }
}

async function loadTeams() {
  try {
    const payload = await apiJson("/teams", { method: "GET", headers: {}, omitTeamHeader: true });
    state.teams = payload.teams || [];
    const selectedTeam = state.teams.find((item) => item.team_id === getStoredTeamId());
    if (selectedTeam) {
      fillTeamForm(selectedTeam);
    }
    if (!state.activeTeam || state.activeTeam.is_guest) {
      setConsole("team-summary", payload);
    }
  } catch (error) {
    if (!byId("team-summary").textContent) {
      setConsole("team-summary", `Falha ao carregar times: ${error.message}`);
    }
  }
}

async function loadModels() {
  const modelDir = byId("models-dir").value.trim();
  const payload = await apiJson(`/models?model_dir=${encodeURIComponent(modelDir)}`, { method: "GET", headers: {} });
  state.models = payload.models || [];
  renderModelsTable(state.models);
  updateExperimentSelect(state.models);
  byId("predict-model-dir").value = modelDir;

  const best = state.models[0];
  byId("models-summary").textContent = best
    ? `${payload.n_models} modelos carregados. Melhor candidato atual: ${best.experiment} (${best.model_family || "model"}).`
    : "Registry vazio.";
}

async function loadJobs() {
  const payload = await apiJson("/jobs?limit=20", { method: "GET", headers: {} });
  state.jobs = payload.jobs || [];
  renderJobsTable(state.jobs);
}

async function loadAuditEvents() {
  try {
    const payload = await apiJson("/audit/events?limit=12", { method: "GET", headers: {} });
    setConsole("audit-detail", payload.events || []);
  } catch (error) {
    setConsole("audit-detail", `Auditoria indisponível: ${error.message}`);
  }
}

async function loadTeamDashboard() {
  try {
    const payload = await apiJson("/analytics/team-dashboard?recent_limit=8&audit_limit=300", { method: "GET", headers: {} });
    const summary = payload.summary || {};
    byId("team-dashboard-summary").textContent =
      `${summary.total_jobs ?? 0} jobs, ${summary.completed_jobs ?? 0} concluídos, ` +
      `${summary.failed_jobs ?? 0} falhos, ${summary.audit_events ?? 0} eventos auditados.`;
    setConsole("team-dashboard-detail", payload);
  } catch (error) {
    byId("team-dashboard-summary").textContent = `Falha ao carregar painel: ${error.message}`;
    setConsole("team-dashboard-detail", `Painel indisponível: ${error.message}`);
  }
}

function renderLaunchReadiness(payload) {
  const summary = payload.summary || {};
  const checks = payload.checks || [];
  byId("launch-readiness-summary").textContent =
    `Prontidão geral ${summary.overall_launch_readiness_percent ?? 0}% | ` +
    `ciência ${summary.scientific_publication_percent ?? 0}% | ` +
    `web ${summary.web_launch_percent ?? 0}% | ` +
    `operação ${summary.operational_hardening_percent ?? 0}% | ` +
    `${summary.ready_for_public_web ? "pronta para web pública controlada" : "ainda exige fechamento antes da exposição pública"}.`;

  const list = byId("launch-readiness-list");
  list.innerHTML = "";
  checks.slice(0, 10).forEach((check) => {
    const row = document.createElement("article");
    row.className = "result-row";
    row.innerHTML = `
      <div class="result-row-main">
        <strong>${check.title || check.gate_id || "-"}</strong>
        <span>${check.area || "-"} | ${check.status || "-"}</span>
      </div>
      <div class="result-row-metrics">
        <span>Score <strong>${check.score_percent ?? 0}%</strong></span>
        <span>${check.critical ? "Crítico" : "Apoio"}</span>
      </div>
    `;
    list.appendChild(row);
  });
  if (!checks.length) {
    list.innerHTML = '<div class="empty-cell">Nenhum critério de prontidão retornado.</div>';
  }
  setConsole("launch-readiness-detail", payload.markdown_report || payload);
}

async function loadLaunchReadiness() {
  const payload = await apiJson("/launch/readiness", { method: "GET", headers: {} });
  renderLaunchReadiness(payload);
}

async function loadRoadmap() {
  try {
    const payload = await apiJson("/roadmap/progress", { method: "GET", headers: {} });
    state.roadmap = payload;
    const summary = payload.summary || {};
    byId("roadmap-summary").textContent =
      `${summary.overall_progress_bar || ""} | ${summary.completed_stages ?? 0} etapas concluídas, ` +
      `${summary.in_progress_stages ?? 0} em andamento, ${summary.planned_stages ?? 0} planejadas | ` +
      `${summary.development_complete ? "desenvolvimento completo" : "desenvolvimento em andamento"} | ` +
      `${summary.scientific_validation_pending ? "validação científica segue separada" : "validação científica concluída"}.`;
    renderRoadmapStages(payload.stages || []);
    setConsole("roadmap-detail", payload);
  } catch (error) {
    byId("roadmap-summary").textContent = `Falha ao carregar roadmap: ${error.message}`;
    renderRoadmapStages([]);
    setConsole("roadmap-detail", `Roteiro indisponível: ${error.message}`);
  }
}

async function inspectPublicCatalog() {
  const configPath = byId("public-catalog-config").value.trim();
  const outputDir = byId("public-catalog-output").value.trim();
  if (!configPath) {
    byId("public-catalog-summary").textContent = "Informe o caminho do catálogo TOML.";
    setConsole("public-catalog-detail", "Catálogo não informado.");
    return;
  }
  try {
    const payload = await apiJson("/public-sources/catalog/inspect", {
      method: "POST",
      body: prettyJson({
        config_path: configPath,
        output_dir: outputDir || null,
      }),
    });
    state.publicCatalog = payload;
    updatePublicCatalogSummary(payload);
    renderPublicCatalogSources(buildPublicCatalogSources(payload));
    setConsole("public-catalog-detail", {
      ...payload,
      public_sync_summary: (payload.sync_plan || {}).summary || {},
    });
    setConsole("public-catalog-history-detail", payload.sync_history || "Nenhum histórico de sincronização encontrado ainda.");
  } catch (error) {
    byId("public-catalog-summary").textContent = `Falha ao inspecionar catálogo: ${error.message}`;
    renderPublicCatalogSources([]);
    setConsole("public-catalog-detail", `Catálogo indisponível: ${error.message}`);
  }
}

async function bootstrapPublicCatalog() {
  const configPath = byId("public-catalog-config").value.trim();
  const outputDir = byId("public-catalog-output").value.trim();
  if (!configPath || !outputDir) {
    setConsole("public-catalog-bootstrap-detail", "Informe config_path e output_dir para gerar o bootstrap.");
    return;
  }
  try {
    const payload = await apiJson("/public-sources/catalog/bootstrap", {
      method: "POST",
      body: prettyJson({
        config_path: configPath,
        output_dir: outputDir,
      }),
    });
    setConsole("public-catalog-bootstrap-detail", payload);
    setConsole("public-catalog-history-detail", payload.sync_history || "Nenhum histórico de sincronização encontrado ainda.");
    updatePublicCatalogSummary(payload);
  } catch (error) {
    setConsole("public-catalog-bootstrap-detail", `Falha ao gerar bootstrap: ${error.message}`);
  }
}

async function resolvePublicCatalog() {
  const configPath = byId("public-catalog-config").value.trim();
  const outputDir = byId("public-catalog-output").value.trim();
  if (!configPath || !outputDir) {
    setConsole("public-catalog-resolution-detail", "Informe config_path e output_dir para resolver o catálogo.");
    return;
  }
  try {
    const payload = await apiJson("/public-sources/catalog/resolve", {
      method: "POST",
      body: prettyJson({
        config_path: configPath,
        bootstrap_output_dir: outputDir,
        output_dir: outputDir,
      }),
    });
    const summary = payload.summary || {};
    byId("public-catalog-summary").textContent =
      `Resolução ${summary.overall_resolution_percent ?? 0}% | ` +
      `${summary.ready_for_resolved_config ? "catálogo pronto para coorte resolvida" : "ainda há fontes bloqueadas"} | ` +
      `${summary.n_resolved_from_stage ?? 0} fontes staged.`;
    setConsole("public-catalog-resolution-detail", payload);
  } catch (error) {
    setConsole("public-catalog-resolution-detail", `Falha ao resolver catálogo: ${error.message}`);
  }
}

async function executePublicCatalogBootstrapDryRun() {
  const configPath = byId("public-catalog-config").value.trim();
  const outputDir = byId("public-catalog-output").value.trim();
  if (!configPath || !outputDir) {
    setConsole("public-catalog-history-detail", "Informe config_path e output_dir para executar o bootstrap em dry-run.");
    return;
  }
  try {
    const payload = await apiJson("/public-sources/catalog/bootstrap/execute", {
      method: "POST",
      body: prettyJson({
        config_path: configPath,
        output_dir: outputDir,
        dry_run: true,
      }),
    });
    setConsole("public-catalog-history-detail", payload);
    const execution = payload.execution || {};
    if (state.publicCatalog) {
      const refreshedPayload = {
        ...state.publicCatalog,
        sync_history: execution.sync_history || {},
        benchmark_readiness: execution.benchmark_readiness || {},
      };
      renderPublicCatalogSources(buildPublicCatalogSources(refreshedPayload));
    }
    updatePublicCatalogSummary({
      summary: payload.catalog_summary || {},
      sync_history: execution.sync_history || {},
      benchmark_readiness: execution.benchmark_readiness || {},
    });
  } catch (error) {
    setConsole("public-catalog-history-detail", `Falha ao executar dry-run: ${error.message}`);
  }
}

async function loadPublicCatalogHistory() {
  const configPath = byId("public-catalog-config").value.trim();
  const outputDir = byId("public-catalog-output").value.trim();
  if (!outputDir) {
    setConsole("public-catalog-history-detail", "Informe output_dir para consultar o histórico de sincronização.");
    return;
  }
  try {
    const search = new URLSearchParams({ output_dir: outputDir });
    if (configPath) {
      search.set("config_path", configPath);
    }
    const payload = await apiJson(`/public-sources/catalog/bootstrap/history?${search.toString()}`, {
      method: "GET",
      headers: {},
    });
    setConsole("public-catalog-history-detail", payload);
    const history = payload.history || {};
    if (state.publicCatalog) {
      const refreshedPayload = {
        ...state.publicCatalog,
        sync_history: history,
        benchmark_readiness: history.benchmark_readiness || {},
      };
      renderPublicCatalogSources(buildPublicCatalogSources(refreshedPayload));
    }
    updatePublicCatalogSummary({
      summary: state.publicCatalog?.summary || {},
      sync_history: history,
      benchmark_readiness: history.benchmark_readiness || {},
    });
  } catch (error) {
    setConsole("public-catalog-history-detail", `Falha ao carregar histórico: ${error.message}`);
  }
}

async function loadReleaseManifest() {
  const manifestPath = byId("release-manifest-path").value.trim();
  if (!manifestPath) {
    byId("release-manifest-summary").textContent = "Informe o caminho de um manifesto para inspeção.";
    setConsole("release-manifest-detail", "Nenhum manifesto informado.");
    return;
  }
  try {
    const payload = await apiJson("/releases/manifest/load", {
      method: "POST",
      body: prettyJson({ manifest_path: manifestPath }),
    });
    state.releaseManifest = payload.manifest || null;
    const summary = payload.summary || {};
    byId("release-manifest-summary").textContent =
      `${summary.release_type || "release"} ${summary.release_id || ""} | ` +
      `${summary.n_sources ?? 0} fontes | ${summary.n_artifacts ?? 0} artefatos verificados.`;
    setConsole("release-manifest-detail", payload);
  } catch (error) {
    byId("release-manifest-summary").textContent = `Falha ao carregar manifesto: ${error.message}`;
    setConsole("release-manifest-detail", `Manifesto indisponível: ${error.message}`);
  }
}

async function submitPrediction(event) {
  event.preventDefault();
  const payload = {
    model_dir: byId("predict-model-dir").value.trim(),
    experiment: byId("predict-experiment").value,
    gene: byId("predict-gene").value,
    hgvs_p: byId("predict-hgvs").value.trim(),
    threshold: numberOrNull(byId("predict-threshold").value) ?? 0.5,
    mode: byId("predict-mode").value || null,
    feature_payload: {
      phylop: numberOrNull(byId("feat-phylop").value),
      gerp: numberOrNull(byId("feat-gerp").value),
      siphy: numberOrNull(byId("feat-siphy").value),
      revel: numberOrNull(byId("feat-revel").value),
      feature_gnomad_af: numberOrNull(byId("feat-gnomad").value),
      feature_mave_score: numberOrNull(byId("feat-mave").value),
    },
  };
  const response = await apiJson("/predict/variant", {
    method: "POST",
    body: prettyJson(payload),
  });
  renderPredictionCard(response);
}

async function submitTraining(event) {
  event.preventDefault();
  const familyText = byId("train-families").value.trim();
  const payload = {
    config_path: byId("train-config").value.trim(),
    output_dir: byId("train-output").value.trim(),
    model_families: familyText ? familyText.split(",").map((item) => item.trim()).filter(Boolean) : null,
  };
  setConsole("train-result", "Enfileirando treino...");
  const response = await apiJson("/jobs/train/source-config", {
    method: "POST",
    body: prettyJson(payload),
  });
  setConsole("train-result", response);
  await loadJobs();
}

function downloadFile(filename, content, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function submitBatch(event) {
  event.preventDefault();
  const variants = parseBatchCsv(byId("batch-input").value);
  const reportTitle = byId("batch-report-title").value.trim();
  const payload = {
    model_dir: byId("batch-model-dir").value.trim(),
    experiment: byId("batch-experiment").value,
    report_title: reportTitle || null,
    report_context: {
      batch_name: reportTitle || null,
      laboratory_name: byId("profile-institution").value.trim() || null,
      team_name: byId("team-name").value.trim() || null,
      team_id: byId("team-id").value.trim() || null,
    },
    variants,
  };
  byId("batch-summary").textContent = "Executando triagem em lote...";
  const response = await apiJson("/predict/batch", {
    method: "POST",
    body: prettyJson(payload),
  });
  state.batchCsvReport = response.csv_report || "";
  state.batchMarkdownReport = response.markdown_report || "";
  renderBatchTable(response.report || []);
  const summary = response.summary || {};
  byId("batch-summary").textContent =
    `${summary.total_variants} variantes, ${summary.n_success} concluídas, ${summary.n_error} com erro, ` +
    `${summary.n_tier_1} em tier 1, ${summary.n_tier_2} em tier 2.`;
}

async function submitStudy(event) {
  event.preventDefault();
  const payload = {
    config_path: byId("study-config").value.trim(),
    output_dir: byId("study-output").value.trim(),
    report_title: byId("study-report-title").value.trim() || null,
    report_context: {
      institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
      team_name: byId("team-name").value.trim() || null,
      operator_name: byId("profile-name").value.trim() || null,
      report_purpose: "benchmark_publicavel",
    },
  };
  setConsole("study-result", "Enfileirando benchmark...");
  const response = await apiJson("/jobs/study/run", {
    method: "POST",
    body: prettyJson(payload),
  });
  setConsole("study-result", response);
  await loadJobs();
}

async function runStudyPreflight() {
  const payload = {
    config_path: byId("preflight-config").value.trim(),
    output_dir: byId("preflight-output").value.trim(),
    report_context: {
      institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
      team_name: byId("team-name").value.trim() || null,
      operator_name: byId("profile-name").value.trim() || null,
      report_purpose: "study_preflight",
    },
  };
  byId("study-diagnostics-summary").textContent = "Executando preflight do estudo...";
  const response = await apiJson("/study/preflight", {
    method: "POST",
    body: prettyJson(payload),
  });
  const summary = response.summary || {};
  byId("study-diagnostics-summary").textContent =
    `Preflight ${summary.overall_preflight_percent ?? 0}% | ` +
    `independência ${summary.cohort_independence_percent ?? 0}% | ` +
    `${summary.ready_to_run ? "pronto para benchmark" : "ainda não pronto"} | ` +
    `${summary.n_critical_gaps ?? 0} gaps críticos.`;
  setConsole("study-preflight-detail", response);
  renderStudyValidationDetail({
    claim_strength_percent: null,
    claim_tier: null,
    validation_lock_percent: null,
    validation_ready_for_submission_lock: null,
    validation_ready_for_statistical_validation: summary.ready_to_run ?? null,
    validation_ready_for_translational_pilot: null,
  });
}

async function inspectStudyBundle() {
  const resultDir = byId("study-inspect-dir").value.trim();
  if (!resultDir) {
    byId("study-diagnostics-summary").textContent = "Informe um diretório de estudo exportado para inspeção.";
    return;
  }
  const response = await apiJson("/study/bundle/inspect", {
    method: "POST",
    body: prettyJson({ result_dir: resultDir }),
  });
  const summary = response.summary || {};
  byId("study-diagnostics-summary").textContent =
    `Pacote inspecionado | prontidão ${summary.publication_readiness_percent ?? 0}% | ` +
    `independence ${summary.cohort_independence_percent ?? 0}% | ` +
    `real-data ${summary.real_data_readiness_percent ?? 0}% | ` +
    `comparative ${summary.comparative_evidence_percent ?? 0}% | ` +
    `claim ${summary.claim_strength_percent ?? 0}% (${summary.claim_tier || "-"}) | ` +
    `lock ${summary.validation_lock_percent ?? 0}% | ` +
    `${summary.publication_ready_for_submission ? "pronto para submissão" : "ainda precisa de evidência final"}.`;
  setConsole("study-bundle-detail", response);
  renderStudyValidationDetail(summary);
  const manifestPath = response.study_release_manifest?.manifest_path || `${resultDir}\\study_release_manifest.json`;
  if (manifestPath) {
    byId("release-manifest-path").value = manifestPath;
  }
}

async function resolveStudyPublicConfig() {
  const configPath = byId("study-config").value.trim();
  const outputDir = byId("study-public-resolution-output").value.trim();
  const deliveryDir = byId("study-delivery-dir").value.trim();
  if (!configPath || !outputDir) {
    setConsole("study-public-resolution-detail", "Informe config_path e output_dir para resolver o estudo público.");
    return;
  }
  byId("study-diagnostics-summary").textContent = "Resolvendo estudo público para uma configuração congelada...";
  const payload = await apiJson("/study/public-config/resolve", {
    method: "POST",
    body: prettyJson({
      config_path: configPath,
      output_dir: outputDir,
      bootstrap_root_dir: outputDir,
      delivery_dir: deliveryDir || null,
    }),
  });
  const summary = payload.summary || {};
  byId("study-diagnostics-summary").textContent =
    `Resolução pública ${summary.overall_resolution_percent ?? 0}% | ` +
    `real-data ${summary.real_data_readiness_percent ?? 0}% | ` +
    `handoff-pack ${summary.real_data_handoff_percent ?? 0}% | ` +
    `autopreenchimento ${summary.real_data_handoff_autofill_percent ?? 0}% | ` +
    `handoff-check ${summary.real_data_handoff_reconciliation_percent ?? 0}% | ` +
    `handoff-apply ${summary.real_data_handoff_application_percent ?? 0}% | ` +
    `promoção ${summary.real_data_candidate_promotion_percent ?? 0}% | ` +
    `${summary.ready_for_resolved_study ? "estudo resolvido" : "ainda há coortes bloqueadas"} | ` +
    `${summary.n_ready_cohorts ?? 0}/${summary.n_cohorts ?? 0} coortes prontas.`;
  setConsole("study-public-resolution-detail", payload);
  renderStudyValidationDetail(summary);
  if (payload.resolved_study_config_path) {
    byId("preflight-config").value = payload.resolved_study_config_path;
  }
}

async function autofillRealDataHandoff() {
  const resolutionDir = byId("study-public-resolution-output").value.trim();
  const deliveryDir = byId("study-delivery-dir").value.trim();
  if (!resolutionDir || !deliveryDir) {
    setConsole("study-public-resolution-detail", "Informe o diretório de resolução pública e o diretório de entrega para autopreencher a entrega.");
    return;
  }
  byId("study-diagnostics-summary").textContent = "Varrendo a entrega do laboratório e propondo preenchimento do rastreador...";
  const payload = await apiJson("/study/real-data-handoff/autofill", {
    method: "POST",
    body: prettyJson({
      study_name: byId("study-report-title").value.trim() || "PrimeVarClass Public Study",
      handoff_tasks_path: `${resolutionDir}\\study_real_data_handoff_tasks.csv`,
      tracker_path: `${resolutionDir}\\study_real_data_handoff_tracker.csv`,
      delivery_dir: deliveryDir,
      output_dir: resolutionDir,
      report_context: {
        institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
        team_name: byId("team-name").value.trim() || null,
        operator_name: byId("profile-name").value.trim() || null,
        report_purpose: "real_data_handoff_autofill",
      },
    }),
  });
  const summary = payload.summary || {};
  byId("study-diagnostics-summary").textContent =
    `Autopreenchimento ${summary.overall_handoff_autofill_percent ?? 0}% | ` +
    `${summary.n_autofilled_tasks ?? 0} tarefas preenchidas | ` +
    `${summary.n_unmatched_tasks ?? 0} pendências | ` +
    `${summary.ready_for_reconciliation_rerun ? "pronto para reconciliação" : "ainda precisa de revisão manual"}.`;
  setConsole("study-public-resolution-detail", payload);
  renderStudyValidationDetail({
    real_data_handoff_autofill_percent: summary.overall_handoff_autofill_percent ?? null,
    n_handoff_autofilled_tasks: summary.n_autofilled_tasks ?? null,
    n_handoff_preserved_completed_tasks: summary.n_preserved_completed_tasks ?? null,
    n_handoff_unmatched_tasks: summary.n_unmatched_tasks ?? null,
    ready_for_reconciliation_rerun_from_autofill: summary.ready_for_reconciliation_rerun ?? null,
  });
}

async function runPublicStudy() {
  const configPath = byId("study-config").value.trim();
  const outputDir = byId("study-output").value.trim();
  const bootstrapRootDir = byId("study-public-resolution-output").value.trim();
  const deliveryDir = byId("study-delivery-dir").value.trim();
  if (!configPath || !outputDir) {
    setConsole("study-public-run-detail", "Informe config_path e output_dir para executar o estudo público final.");
    return;
  }
  byId("study-diagnostics-summary").textContent = "Enfileirando pipeline público final: resolução, pré-checagem, benchmark e painel de execução...";
  const response = await apiJson("/jobs/study/public-run", {
    method: "POST",
    body: prettyJson({
      config_path: configPath,
      output_dir: outputDir,
      bootstrap_root_dir: bootstrapRootDir || null,
      delivery_dir: deliveryDir || null,
      report_title: byId("study-report-title").value.trim() || null,
      report_context: {
        institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
        team_name: byId("team-name").value.trim() || null,
        operator_name: byId("profile-name").value.trim() || null,
        report_purpose: "public_benchmark_pipeline",
      },
    }),
  });
  byId("study-diagnostics-summary").textContent = `Pipeline público final enfileirado | job ${response.job_id || "-"} | acompanhe a fila abaixo.`;
  setConsole("study-public-run-detail", response);
  renderStudyValidationDetail({
    real_data_handoff_percent: null,
    real_data_handoff_reconciliation_percent: null,
    real_data_handoff_application_percent: null,
    ready_for_lab_handoff: null,
    n_real_data_tasks: null,
    n_critical_real_data_tasks: null,
    n_handoff_validated_tasks: null,
    n_handoff_pending_tasks: null,
    n_handoff_invalid_tasks: null,
    n_handoff_applied_changes: null,
    ready_to_rerun_resolution_from_handoff: null,
    ready_to_rerun_public_study_from_handoff: null,
    ready_for_candidate_resolution_from_handoff: null,
    ready_for_candidate_public_study_from_handoff: null,
    claim_strength_percent: null,
    claim_tier: null,
    validation_lock_percent: null,
    validation_ready_for_submission_lock: null,
    validation_ready_for_statistical_validation: null,
    validation_ready_for_translational_pilot: null,
    pilot_package_percent: null,
    pilot_mode: null,
    ready_for_demo_pilot: null,
    ready_for_shadow_pilot: null,
    ready_for_live_pilot: null,
    translational_impact_percent: null,
    ready_for_assisted_pilot_ops: null,
    ready_for_shadow_rollout: null,
    ready_for_institutional_rollout: null,
    final_mile_percent: null,
    ready_for_real_data_execution: null,
    ready_for_final_evidence_round: null,
    ready_for_submission_closeout: null,
    ready_for_live_transition: null,
    n_final_mile_blockers: null,
    n_final_mile_critical_blockers: null,
    top_final_mile_blocker_phase: null,
    top_final_mile_blocker_title: null,
  });
  byId("study-inspect-dir").value = `${outputDir}\\resolved_study_run`;
  await loadJobs();
}

async function runCandidatePublicStudy() {
  const resolutionDir = byId("study-public-resolution-output").value.trim();
  const outputDir = byId("study-output").value.trim();
  const candidateConfigPath = `${resolutionDir}\\study_real_data_candidate_config.toml`;
  const candidatePromotionManifestPath = `${resolutionDir}\\study_real_data_candidate_promotion_manifest.json`;
  if (!resolutionDir || !outputDir) {
    setConsole("study-public-run-detail", "Informe o diretório de resolução pública e o diretório de saída para executar o estudo candidato.");
    return;
  }
  byId("study-diagnostics-summary").textContent = "Enfileirando nova rodada controlada a partir da configuração candidata...";
  const response = await apiJson("/jobs/study/public-run/candidate", {
    method: "POST",
    body: prettyJson({
      candidate_config_path: candidateConfigPath,
      candidate_promotion_manifest_path: candidatePromotionManifestPath,
      output_dir: `${outputDir}\\candidate_public_study_run`,
      require_candidate_ready: true,
      report_context: {
        institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
        team_name: byId("team-name").value.trim() || null,
        operator_name: byId("profile-name").value.trim() || null,
        report_purpose: "candidate_public_benchmark_pipeline",
      },
    }),
  });
  byId("study-diagnostics-summary").textContent = `Estudo candidato enfileirado | job ${response.job_id || "-"} | acompanhe a fila abaixo.`;
  setConsole("study-public-run-detail", response);
  await loadJobs();
}

async function runGeneExpansion() {
  const clinvarPath = byId("multigene-clinvar-path").value.trim();
  const mavedbPath = byId("multigene-mavedb-path").value.trim();
  const outputDir = byId("multigene-gene-expansion-output").value.trim();
  if (!clinvarPath || !mavedbPath || !outputDir) {
    setConsole("multigene-gene-expansion-detail", "Informe ClinVar, MaveDB e output_dir para gerar a expansão gênica.");
    return;
  }
  byId("multigene-summary").textContent = "Gerando expansão gênica a partir de ClinVar + MaveDB...";
  const response = await apiJson("/science/gene-expansion", {
    method: "POST",
    body: prettyJson({
      clinvar_variant_summary_path: clinvarPath,
      mavedb_dump_path: mavedbPath,
      output_dir: outputDir,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Expansão gênica: ${summary.recommended_gene_count ?? 0} genes recomendados | ` +
    `sobreposição ${summary.overlap_gene_count ?? 0} | ` +
    `principal ${((summary.top_candidate_genes || [])[0]) || "-"}.`;
  setConsole("multigene-gene-expansion-detail", response);
}

async function runBiologicalDiscovery() {
  const manifestPath = byId("multigene-real-data-manifest").value.trim();
  const outputDir = byId("multigene-biological-discovery-output").value.trim();
  if (!manifestPath || !outputDir) {
    setConsole("multigene-biological-discovery-detail", "Informe o manifesto de dados reais e o diretório de saída para gerar a descoberta biológica.");
    return;
  }
  byId("multigene-summary").textContent = "Gerando descoberta biológica a partir do pacote real...";
  const response = await apiJson("/science/biological-discovery", {
    method: "POST",
    body: prettyJson({
      real_data_manifest_path: manifestPath,
      output_dir: outputDir,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Descoberta biológica: ${summary.hotspot_count ?? 0} regiões críticas | ` +
    `revisões priorizadas ${summary.review_upgrade_candidate_count ?? 0} | ` +
    `hipóteses ${summary.hypothesis_variant_count ?? 0}.`;
  if (response.biological_discovery_manifest_path) {
    byId("multigene-biological-discovery-manifest").value = response.biological_discovery_manifest_path;
  }
  setConsole("multigene-biological-discovery-detail", response);
}

async function runProteinImpact() {
  const manifestPath = byId("multigene-biological-discovery-manifest").value.trim();
  const outputDir = byId("multigene-protein-impact-output").value.trim();
  if (!manifestPath || !outputDir) {
    setConsole("multigene-protein-impact-detail", "Informe o manifesto de descoberta biológica e o diretório de saída para gerar o impacto proteico.");
    return;
  }
  byId("multigene-summary").textContent = "Gerando fila proteômica/3D com mecanismo biológico e números primos...";
  const response = await apiJson("/science/protein-impact", {
    method: "POST",
    body: prettyJson({
      biological_discovery_manifest_path: manifestPath,
      output_dir: outputDir,
      max_modeling_variants: 25,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Impacto proteico: fila ${summary.modeling_queue_count ?? 0} | ` +
    `alta prioridade ${summary.high_priority_variant_count ?? 0} | ` +
    `alinhamento com números primos ${summary.prime_mechanistic_alignment_percent ?? 0}%.`;
  if (response.protein_impact_manifest_path) {
    byId("multigene-protein-impact-manifest").value = response.protein_impact_manifest_path;
  }
  setConsole("multigene-protein-impact-detail", response);
}

async function runQuantumProteomics() {
  const manifestPath = byId("multigene-protein-impact-manifest").value.trim();
  const outputDir = byId("multigene-quantum-proteomics-output").value.trim();
  if (!manifestPath || !outputDir) {
    setConsole("multigene-quantum-proteomics-detail", "Informe o manifesto de impacto proteico e o diretório de saída para gerar a proteômica quântica.");
    return;
  }
  byId("multigene-summary").textContent = "Gerando motor QM/QM-MM/MD/docking para investigar vulnerabilidades proteicas...";
  const response = await apiJson("/science/quantum-proteomics", {
    method: "POST",
    body: prettyJson({
      protein_impact_manifest_path: manifestPath,
      output_dir: outputDir,
      max_quantum_targets: 12,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Proteômica quântica: alvos ${summary.quantum_target_count ?? 0} | ` +
    `VQE ${summary.vqe_target_count ?? 0} | ` +
    `média QM ${summary.mean_quantum_priority_score_percent ?? 0}% | ` +
    `prime-Q ${summary.mean_prime_quantum_coupling_score_percent ?? 0}%.`;
  if (response.quantum_proteomics_manifest_path) {
    byId("multigene-quantum-proteomics-manifest").value = response.quantum_proteomics_manifest_path;
  }
  setConsole("multigene-quantum-proteomics-detail", response);
}

async function runProspectiveValidationClosure() {
  const outputDir = byId("multigene-prospective-validation-output").value.trim();
  const annotationManifestPath = byId("multigene-annotation-enrichment-manifest").value.trim();
  const brca1EngineManifestPath = byId("multigene-brca1-engine-execution-manifest").value.trim();
  if (!outputDir || !annotationManifestPath || !brca1EngineManifestPath) {
    setConsole(
      "multigene-prospective-validation-detail",
      "Informe o manifesto de enriquecimento de anotação, o manifesto do motor BRCA1 e o diretório de saída para fechar a validação prospectiva.",
    );
    return;
  }
  byId("multigene-summary").textContent =
    "Fechando pacote prospectivo/experimental com coortes cegas, SOPs, plano estatístico e entrega ao laboratório...";
  const response = await apiJson("/science/prospective-validation-closure", {
    method: "POST",
    body: prettyJson({
      multigene_annotation_enrichment_manifest_path: annotationManifestPath,
      brca1_engine_execution_manifest_path: brca1EngineManifestPath,
      output_dir: outputDir,
      validation_credibility_closure_manifest_path: byId("multigene-validation-credibility-manifest").value.trim() || null,
      public_sync_closure_manifest_path: byId("multigene-public-sync-closure-manifest").value.trim() || null,
      brca1_paired_mutant_execution_manifest_path: byId("multigene-brca1-paired-mutant-manifest").value.trim() || null,
      brca1_mutant_geometry_qc_manifest_path: byId("multigene-brca1-mutant-geometry-qc-manifest").value.trim() || null,
      max_queue_rows: 12,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Prospectiva ${summary.prospective_validation_readiness_percent ?? 0}% | ` +
    `pacote experimental ${summary.experimental_package_artifact_readiness_percent ?? 0}% | ` +
    `entrega ${summary.partner_handoff_variant_count ?? 0} alvos | ` +
    `teto da prova final ${summary.final_scientific_proof_cap_percent ?? 0}%.`;
  if (response.prospective_validation_closure_manifest_path) {
    byId("multigene-prospective-validation-manifest").value = response.prospective_validation_closure_manifest_path;
  }
  setConsole("multigene-prospective-validation-detail", response);
}

async function runValidationCredibilityClosure() {
  const outputDir = byId("multigene-validation-credibility-output").value.trim();
  if (!outputDir) {
    setConsole("multigene-validation-credibility-detail", "Informe o output_dir para gerar o fechamento de credibilidade.");
    return;
  }
  byId("multigene-summary").textContent = "Consolidando validação, credibilidade científica e lacunas restantes...";
  const response = await apiJson("/science/validation-credibility-closure", {
    method: "POST",
    body: prettyJson({
      output_dir: outputDir,
      prime_intelligence_manifest_path: byId("multigene-prime-intelligence-manifest").value.trim() || null,
      biological_discovery_manifest_path: byId("multigene-biological-discovery-manifest").value.trim() || null,
      protein_impact_manifest_path: byId("multigene-protein-impact-manifest").value.trim() || null,
      quantum_proteomics_manifest_path: byId("multigene-quantum-proteomics-manifest").value.trim() || null,
      multigene_rollout_manifest_path: byId("multigene-rollout-manifest").value.trim() || null,
      brca1_engine_execution_manifest_path: byId("multigene-brca1-engine-execution-manifest").value.trim() || null,
      multigene_annotation_enrichment_manifest_path: byId("multigene-annotation-enrichment-manifest").value.trim() || null,
      public_sync_closure_manifest_path: byId("multigene-public-sync-closure-manifest").value.trim() || null,
      prospective_validation_closure_manifest_path: byId("multigene-prospective-validation-manifest").value.trim() || null,
      brca1_paired_mutant_execution_manifest_path: byId("multigene-brca1-paired-mutant-manifest").value.trim() || null,
      brca1_mutant_geometry_qc_manifest_path: byId("multigene-brca1-mutant-geometry-qc-manifest").value.trim() || null,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Credibilidade ${summary.scientific_credibility_percent ?? 0}% | ` +
    `software ${summary.software_evidence_closure_percent ?? 0}% | ` +
    `teto da prova final ${summary.final_proof_cap_percent ?? 0}%.`;
  if (response.validation_credibility_closure_manifest_path) {
    byId("multigene-validation-credibility-manifest").value = response.validation_credibility_closure_manifest_path;
  }
  setConsole("multigene-validation-credibility-detail", response);
}

async function runIndependentDataExpansion() {
  const outputDir = byId("multigene-independent-data-output").value.trim();
  if (!outputDir) {
    setConsole("multigene-independent-data-detail", "Informe o diretório de saída para mapear bancos independentes.");
    return;
  }
  byId("multigene-summary").textContent = "Mapeando bancos públicos independentes para treino, validação e evidência funcional...";
  const response = await apiJson("/science/independent-data-expansion", {
    method: "POST",
    body: prettyJson({
      output_dir: outputDir,
      target_genes: ["BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9"],
      include_restricted_sources: false,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Bancos independentes ${summary.independent_data_expansion_percent ?? 0}% | ` +
    `${summary.database_count ?? 0} fontes | ` +
    `${summary.supported_preset_count ?? 0} presets prontos.`;
  if (response.independent_data_expansion_manifest_path) {
    byId("multigene-independent-data-manifest").value = response.independent_data_expansion_manifest_path;
  }
  setConsole("multigene-independent-data-detail", response);
}

async function runIndependentDataStagingClosure() {
  const outputDir = byId("multigene-independent-staging-output").value.trim();
  const expansionOutputDir = byId("multigene-independent-data-output").value.trim();
  const manifestPath =
    byId("multigene-independent-data-manifest").value.trim() ||
    `${expansionOutputDir}\\independent_data_expansion_manifest.json`;
  if (!outputDir) {
    setConsole("multigene-independent-data-detail", "Informe o diretório de saída para fechar a preparação independente.");
    return;
  }
  byId("multigene-summary").textContent = "Auditando arquivos locais, hashes, fontes prontas e lacunas de bancos independentes...";
  const response = await apiJson("/science/independent-data-staging-closure", {
    method: "POST",
    body: prettyJson({
      output_dir: outputDir,
      independent_data_expansion_manifest_path: manifestPath || null,
      target_genes: ["BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9"],
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Preparação independente ${summary.independent_data_staging_closure_percent ?? 0}% | ` +
    `execução linha a linha ${summary.line_level_real_data_execution_percent ?? 0}% | ` +
    `${summary.ready_source_count ?? 0}/${summary.database_count ?? 0} fontes prontas.`;
  setConsole("multigene-independent-data-detail", response);
}

async function runIndependentOpenSourceAutostage() {
  const outputDir = byId("multigene-independent-autostage-output").value.trim();
  if (!outputDir) {
    setConsole("multigene-independent-data-detail", "Informe o diretório de saída para a preparação aberta automática.");
    return;
  }
  byId("multigene-summary").textContent = "Baixando e preparando fontes públicas abertas por APIs oficiais...";
  const response = await apiJson("/science/independent-open-source-autostage", {
    method: "POST",
    body: prettyJson({
      output_dir: outputDir,
      target_genes: ["BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9"],
      refresh: false,
      max_gwas_per_gene: 8,
      max_pdb_per_gene: 8,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Preparação aberta automática ${summary.autostaging_readiness_percent ?? 0}% | ` +
    `${summary.staged_source_count ?? 0}/${summary.attempted_source_count ?? 0} fontes preparadas.`;
  setConsole("multigene-independent-data-detail", response);
}

async function runMultigeneRollout() {
  const geneExpansionManifestPath = `${byId("multigene-gene-expansion-output").value.trim()}\\gene_expansion_manifest.json`;
  const primeManifestPath = byId("multigene-prime-intelligence-manifest").value.trim() || null;
  const outputDir = byId("multigene-rollout-output").value.trim();
  if (!geneExpansionManifestPath || !outputDir) {
    setConsole("multigene-rollout-detail", "Informe os artefatos de expansão gênica e o diretório de saída do planejamento.");
    return;
  }
  byId("multigene-summary").textContent = "Planejando expansão multigênica com reforço da inteligência por números primos...";
  const response = await apiJson("/science/multigene-rollout", {
    method: "POST",
    body: prettyJson({
      gene_expansion_manifest_path: geneExpansionManifestPath,
      prime_intelligence_manifest_path: primeManifestPath,
      output_dir: outputDir,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Planejamento ${summary.overall_rollout_readiness_percent ?? 0}% | ` +
    `fase 1 ${((summary.phase_1_genes || []).join(", ")) || "nenhum"} | ` +
    `gene-prime ${summary.prime_top_candidate_gene || "-"}.`;
  if (response.multigene_rollout_manifest_path) {
    byId("multigene-rollout-manifest").value = response.multigene_rollout_manifest_path;
  }
  setConsole("multigene-rollout-detail", response);
}

async function runMultigeneStudyFactory() {
  const rolloutManifestPath = byId("multigene-rollout-manifest").value.trim();
  const outputDir = byId("multigene-study-factory-output").value.trim();
  const workspaceRoot = byId("multigene-workspace-root").value.trim() || null;
  if (!rolloutManifestPath || !outputDir) {
    setConsole("multigene-study-factory-detail", "Informe o manifesto de planejamento e o diretório de saída para gerar as estruturas de estudo.");
    return;
  }
  byId("multigene-summary").textContent = "Gerando estruturas de estudo multigênico para a próxima rodada real...";
  const response = await apiJson("/science/multigene-study-factory", {
    method: "POST",
    body: prettyJson({
      rollout_manifest_path: rolloutManifestPath,
      output_dir: outputDir,
      workspace_root: workspaceRoot,
    }),
  });
  const summary = response.summary || {};
  byId("multigene-summary").textContent =
    `Study factory ${summary.total_scaffolded_genes ?? 0} genes scaffoldados | ` +
    `phase 1 ${((summary.phase_1_genes || []).join(", ")) || "none"} | ` +
    `phase 2 ${((summary.phase_2_genes || []).join(", ")) || "none"}.`;
  setConsole("multigene-study-factory-detail", response);
}

async function submitStudyComparison(event) {
  event.preventDefault();
  const payload = {
    baseline_dir: byId("compare-baseline-dir").value.trim(),
    candidate_dir: byId("compare-candidate-dir").value.trim(),
    output_dir: byId("compare-output-dir").value.trim(),
    report_title: byId("compare-report-title").value.trim() || null,
    report_context: {
      institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
      team_name: byId("team-name").value.trim() || null,
      operator_name: byId("profile-name").value.trim() || null,
      comparison_purpose: "compare_studies",
    },
  };
  setConsole("study-compare-result", "Comparando estudos...");
  const response = await apiJson("/study/compare", {
    method: "POST",
    body: prettyJson(payload),
  });
  setConsole("study-compare-result", response);
}

async function submitStudyMonitor(event) {
  event.preventDefault();
  const payload = {
    study_dirs: parseLineList(byId("monitor-study-dirs").value),
    output_dir: byId("monitor-output-dir").value.trim(),
    report_title: byId("monitor-report-title").value.trim() || null,
    report_context: {
      institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
      team_name: byId("team-name").value.trim() || null,
      operator_name: byId("profile-name").value.trim() || null,
      monitoring_purpose: "track_study_versions",
    },
  };
  setConsole("study-monitor-result", "Gerando monitor longitudinal...");
  const response = await apiJson("/monitoring/studies/longitudinal", {
    method: "POST",
    body: prettyJson(payload),
  });
  setConsole("study-monitor-result", response);
}

async function saveProfile(event) {
  event.preventDefault();
  const payload = {
    profile_id: byId("profile-id").value.trim() || null,
    display_name: byId("profile-name").value.trim(),
    role: byId("profile-role").value.trim() || "researcher",
    institution: byId("profile-institution").value.trim() || null,
  };
  const response = await apiJson("/users/profiles", {
    method: "POST",
    body: prettyJson(payload),
    omitTeamHeader: true,
  });
  const profile = response.profile || null;
  if (profile && profile.profile_id) {
    setStoredProfileId(profile.profile_id);
    state.activeProfile = profile;
    fillProfileForm(profile);
  }
  setConsole("profile-summary", response);
  await loadUserContext();
  await loadProfiles();
}

async function saveTeam(event) {
  event.preventDefault();
  const payload = {
    team_id: byId("team-id").value.trim() || null,
    display_name: byId("team-name").value.trim(),
    institution: byId("team-institution").value.trim() || null,
    description: byId("team-description").value.trim() || null,
    owner_role: "owner",
  };
  const response = await apiJson("/teams", {
    method: "POST",
    body: prettyJson(payload),
    omitTeamHeader: true,
  });
  const team = response.team || null;
  if (team && team.team_id) {
    setStoredTeamId(team.team_id);
    state.activeTeam = team;
    fillTeamForm(team);
  }
  setConsole("team-summary", response);
  await loadTeamContext();
  await loadTeams();
}

async function loadTranslationalDashboard() {
  const studyName = byId("pilot-study-name").value.trim() || null;
  const response = await apiJson(`/impact/translational/dashboard${studyName ? `?study_name=${encodeURIComponent(studyName)}` : ""}`, {
    method: "GET",
    headers: {},
  });
  const summary = ((response.dashboard || {}).summary) || {};
  byId("translational-impact-summary").textContent =
    `Impacto translacional ${summary.rollout_signal_percent ?? 0}% | ` +
    `${summary.n_sessions ?? 0} sessões | ` +
    `${summary.n_completed_sessions ?? 0} concluídas | ` +
    `${summary.n_feedback_entries ?? 0} feedbacks | ` +
    `${summary.time_saved_minutes_total ?? 0} min economizados.`;
  setConsole("translational-impact-detail", response);
}

async function savePilotSession() {
  const payload = {
    session_id: byId("pilot-session-id").value.trim(),
    study_name: byId("pilot-study-name").value.trim() || null,
    pilot_mode: byId("pilot-mode").value,
    site_name: byId("pilot-site-name").value.trim() || null,
    institution: byId("team-institution").value.trim() || byId("profile-institution").value.trim() || null,
    team_name: byId("team-name").value.trim() || null,
    operator_name: byId("profile-name").value.trim() || null,
    status: byId("pilot-status").value,
    cases_reviewed: numberOrNull(byId("pilot-cases-reviewed").value) ?? 0,
    variants_flagged: numberOrNull(byId("pilot-variants-flagged").value) ?? 0,
    outcome_summary: byId("pilot-outcome-summary").value.trim() || null,
  };
  const response = await apiJson("/impact/pilot/sessions", {
    method: "POST",
    body: prettyJson(payload),
  });
  const session = response.session || {};
  byId("translational-impact-summary").textContent =
    `Sessão ${session.session_id || "-"} salva | ${session.status || "-"} | ${session.cases_reviewed ?? 0} casos revisados.`;
  setConsole("translational-impact-detail", response);
}

async function savePilotFeedback() {
  const payload = {
    session_id: byId("pilot-session-id").value.trim(),
    study_name: byId("pilot-study-name").value.trim() || null,
    operator_name: byId("profile-name").value.trim() || null,
    role: byId("profile-role").value.trim() || null,
    confidence_score: numberOrNull(byId("pilot-feedback-confidence").value) ?? 0,
    actionability_score: numberOrNull(byId("pilot-feedback-actionability").value) ?? 0,
    time_saved_minutes: numberOrNull(byId("pilot-feedback-time-saved").value) ?? 0,
    adoption_recommendation: byId("pilot-feedback-adoption").value,
    incident_level: byId("pilot-feedback-incident").value,
    notes: byId("pilot-feedback-notes").value.trim() || null,
  };
  const response = await apiJson("/impact/pilot/feedback", {
    method: "POST",
    body: prettyJson(payload),
  });
  const feedback = response.feedback || {};
  byId("translational-impact-summary").textContent =
    `Feedback salvo para ${feedback.session_id || "-"} | recomendação ${feedback.adoption_recommendation || "-"}.`;
  setConsole("translational-impact-detail", response);
}

function mountWorkbench() {
  state.language = getStoredLanguage();
  byId("language-select").value = state.language;
  byId("language-select").addEventListener("change", (event) => {
    setLanguage(event.target.value);
  });
  applyTranslations();
  setupModuleSwitcher();
  setupPortugueseTextObserver();

  byId("api-key-input").value = getStoredApiKey();
  if (getStoredProfileId()) {
    byId("profile-id").value = getStoredProfileId();
  }
  if (getStoredTeamId()) {
    byId("team-id").value = getStoredTeamId();
  }

  byId("save-api-key").addEventListener("click", async () => {
    setStoredApiKey(byId("api-key-input").value.trim());
    await loadAuthStatus();
    loadUserContext().catch(() => {});
    loadProfiles().catch(() => {});
    loadTeamContext().catch(() => {});
    loadTeams().catch(() => {});
    loadJobs().catch(() => {});
    loadAuditEvents().catch(() => {});
  });

  byId("profile-form").addEventListener("submit", async (event) => {
    try {
      await saveProfile(event);
    } catch (error) {
      setConsole("profile-summary", `Falha ao salvar perfil: ${error.message}`);
    }
  });

  byId("team-form").addEventListener("submit", async (event) => {
    try {
      await saveTeam(event);
    } catch (error) {
      setConsole("team-summary", `Falha ao salvar time: ${error.message}`);
    }
  });

  byId("load-models").addEventListener("click", async () => {
    try {
      await loadModels();
    } catch (error) {
      byId("models-summary").textContent = `Falha ao carregar modelos: ${error.message}`;
    }
  });

  byId("predict-form").addEventListener("submit", async (event) => {
    try {
      await submitPrediction(event);
    } catch (error) {
      byId("prediction-card").textContent = `Falha na predição: ${error.message}`;
      byId("prediction-card").classList.remove("result-card-empty");
    }
  });

  byId("train-form").addEventListener("submit", async (event) => {
    try {
      await submitTraining(event);
    } catch (error) {
      setConsole("train-result", `Falha no treino: ${error.message}`);
    }
  });

  byId("batch-form").addEventListener("submit", async (event) => {
    try {
      await submitBatch(event);
    } catch (error) {
      byId("batch-summary").textContent = `Falha na triagem: ${error.message}`;
    }
  });

  byId("download-batch-report").addEventListener("click", () => {
    if (!state.batchCsvReport) {
      byId("batch-summary").textContent = "Execute uma triagem antes de baixar o CSV.";
      return;
    }
    downloadFile("primevarclass_batch_report.csv", state.batchCsvReport, "text/csv;charset=utf-8");
  });

  byId("download-batch-markdown").addEventListener("click", () => {
    if (!state.batchMarkdownReport) {
      byId("batch-summary").textContent = "Execute uma triagem antes de baixar o relatório.";
      return;
    }
    downloadFile("primevarclass_batch_report.md", state.batchMarkdownReport, "text/markdown;charset=utf-8");
  });

  byId("refresh-jobs").addEventListener("click", async () => {
    try {
      await loadJobs();
      await loadAuditEvents();
    } catch (error) {
      byId("jobs-summary").textContent = `Falha ao carregar jobs: ${error.message}`;
    }
  });

  byId("study-form").addEventListener("submit", async (event) => {
    try {
      await submitStudy(event);
    } catch (error) {
      setConsole("study-result", `Falha no benchmark: ${error.message}`);
    }
  });

  byId("run-study-preflight").addEventListener("click", async () => {
    try {
      await runStudyPreflight();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha no preflight: ${error.message}`;
      setConsole("study-preflight-detail", `Preflight indisponível: ${error.message}`);
    }
  });

  byId("inspect-study-bundle").addEventListener("click", async () => {
    try {
      await inspectStudyBundle();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha na inspeção: ${error.message}`;
      setConsole("study-bundle-detail", `Inspeção indisponível: ${error.message}`);
    }
  });

  byId("resolve-study-public-config").addEventListener("click", async () => {
    try {
      await resolveStudyPublicConfig();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha na resolução pública: ${error.message}`;
      setConsole("study-public-resolution-detail", `Resolução indisponível: ${error.message}`);
    }
  });

  byId("autofill-real-data-handoff").addEventListener("click", async () => {
    try {
      await autofillRealDataHandoff();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha no autopreenchimento da entrega: ${error.message}`;
      setConsole("study-public-resolution-detail", `Autopreenchimento indisponível: ${error.message}`);
    }
  });

  byId("run-public-study").addEventListener("click", async () => {
    try {
      await runPublicStudy();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha no pipeline público: ${error.message}`;
      setConsole("study-public-run-detail", `Pipeline público indisponível: ${error.message}`);
    }
  });

  byId("run-candidate-public-study").addEventListener("click", async () => {
    try {
      await runCandidatePublicStudy();
    } catch (error) {
      byId("study-diagnostics-summary").textContent = `Falha no estudo candidato: ${error.message}`;
      setConsole("study-public-run-detail", `Estudo candidato indisponível: ${error.message}`);
    }
  });

  byId("run-gene-expansion").addEventListener("click", async () => {
    try {
      await runGeneExpansion();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no gene expansion: ${error.message}`;
      setConsole("multigene-gene-expansion-detail", `Expansão gênica indisponível: ${error.message}`);
    }
  });

  byId("run-biological-discovery").addEventListener("click", async () => {
    try {
      await runBiologicalDiscovery();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha na descoberta biológica: ${error.message}`;
      setConsole("multigene-biological-discovery-detail", `Descoberta biológica indisponível: ${error.message}`);
    }
  });

  byId("run-protein-impact").addEventListener("click", async () => {
    try {
      await runProteinImpact();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no protein impact: ${error.message}`;
      setConsole("multigene-protein-impact-detail", `Impacto proteico indisponível: ${error.message}`);
    }
  });
  byId("run-quantum-proteomics").addEventListener("click", async () => {
    try {
      await runQuantumProteomics();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no quantum proteomics: ${error.message}`;
      setConsole("multigene-quantum-proteomics-detail", `Proteômica quântica indisponível: ${error.message}`);
    }
  });
  byId("run-prospective-validation-closure").addEventListener("click", async () => {
    try {
      await runProspectiveValidationClosure();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no fechamento prospectivo: ${error.message}`;
      setConsole("multigene-prospective-validation-detail", `Fechamento prospectivo indisponível: ${error.message}`);
    }
  });
  byId("run-validation-credibility-closure").addEventListener("click", async () => {
    try {
      await runValidationCredibilityClosure();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no fechamento de credibilidade: ${error.message}`;
      setConsole("multigene-validation-credibility-detail", `Fechamento indisponível: ${error.message}`);
    }
  });

  byId("run-independent-data-expansion").addEventListener("click", async () => {
    try {
      await runIndependentDataExpansion();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no mapeamento de bancos independentes: ${error.message}`;
      setConsole("multigene-independent-data-detail", `Mapeamento indisponível: ${error.message}`);
    }
  });

  byId("run-independent-data-staging-closure").addEventListener("click", async () => {
    try {
      await runIndependentDataStagingClosure();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no staging de bancos independentes: ${error.message}`;
      setConsole("multigene-independent-data-detail", `Staging independente indisponível: ${error.message}`);
    }
  });

  byId("run-independent-open-source-autostage").addEventListener("click", async () => {
    try {
      await runIndependentOpenSourceAutostage();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha no auto-stage de fontes abertas: ${error.message}`;
      setConsole("multigene-independent-data-detail", `Auto-stage aberto indisponível: ${error.message}`);
    }
  });

  byId("run-multigene-rollout").addEventListener("click", async () => {
    try {
      await runMultigeneRollout();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha na expansão multigênica: ${error.message}`;
      setConsole("multigene-rollout-detail", `Expansão multigênica indisponível: ${error.message}`);
    }
  });

  byId("run-multigene-study-factory").addEventListener("click", async () => {
    try {
      await runMultigeneStudyFactory();
    } catch (error) {
      byId("multigene-summary").textContent = `Falha nas estruturas de estudo multigênico: ${error.message}`;
      setConsole("multigene-study-factory-detail", `Fábrica de estudos multigênicos indisponível: ${error.message}`);
    }
  });

  byId("load-translational-dashboard").addEventListener("click", async () => {
    try {
      await loadTranslationalDashboard();
    } catch (error) {
      byId("translational-impact-summary").textContent = `Falha ao carregar painel translacional: ${error.message}`;
      setConsole("translational-impact-detail", `Painel translacional indisponível: ${error.message}`);
    }
  });

  byId("save-pilot-session").addEventListener("click", async () => {
    try {
      await savePilotSession();
    } catch (error) {
      byId("translational-impact-summary").textContent = `Falha ao salvar sessão: ${error.message}`;
      setConsole("translational-impact-detail", `Sessão de piloto indisponível: ${error.message}`);
    }
  });

  byId("save-pilot-feedback").addEventListener("click", async () => {
    try {
      await savePilotFeedback();
    } catch (error) {
      byId("translational-impact-summary").textContent = `Falha ao salvar feedback: ${error.message}`;
      setConsole("translational-impact-detail", `Feedback translacional indisponível: ${error.message}`);
    }
  });

  byId("study-compare-form").addEventListener("submit", async (event) => {
    try {
      await submitStudyComparison(event);
    } catch (error) {
      setConsole("study-compare-result", `Falha na comparação: ${error.message}`);
    }
  });

  byId("study-monitor-form").addEventListener("submit", async (event) => {
    try {
      await submitStudyMonitor(event);
    } catch (error) {
      setConsole("study-monitor-result", `Falha no monitoramento: ${error.message}`);
    }
  });

  byId("refresh-dashboard").addEventListener("click", async () => {
    await loadTeamDashboard();
  });

  byId("load-launch-readiness").addEventListener("click", async () => {
    try {
      await loadLaunchReadiness();
    } catch (error) {
      byId("launch-readiness-summary").textContent = `Falha ao avaliar prontidão: ${error.message}`;
      setConsole("launch-readiness-detail", `Prontidão de lançamento indisponível: ${error.message}`);
    }
  });

  byId("inspect-public-catalog").addEventListener("click", async () => {
    await inspectPublicCatalog();
  });

  byId("bootstrap-public-catalog").addEventListener("click", async () => {
    await bootstrapPublicCatalog();
  });

  byId("resolve-public-catalog").addEventListener("click", async () => {
    await resolvePublicCatalog();
  });

  byId("execute-public-catalog-dry-run").addEventListener("click", async () => {
    await executePublicCatalogBootstrapDryRun();
  });

  byId("load-public-catalog-history").addEventListener("click", async () => {
    await loadPublicCatalogHistory();
  });

  byId("load-release-manifest").addEventListener("click", async () => {
    await loadReleaseManifest();
  });

  inspectPublicCatalog().catch(() => {});
  loadHealth();
  loadAuthStatus();
  loadUserContext().catch((error) => {
    setConsole("profile-summary", `Falha ao carregar perfil: ${error.message}`);
  });
  loadProfiles().catch(() => {});
  loadTeamContext().catch((error) => {
    setConsole("team-summary", `Falha ao carregar time: ${error.message}`);
  });
  loadTeams().catch(() => {});
  loadModels().catch((error) => {
    byId("models-summary").textContent = `Falha ao carregar modelos: ${error.message}`;
  });
  loadJobs().catch((error) => {
    byId("jobs-summary").textContent = `Falha ao carregar jobs: ${error.message}`;
  });
  loadReleaseManifest().catch(() => {});
  loadTeamDashboard().catch(() => {});
  loadLaunchReadiness().catch(() => {});
  loadTranslationalDashboard().catch(() => {});
  loadAuditEvents().catch(() => {});
  inspectStudyBundle().catch(() => {});
  window.setInterval(() => {
    loadJobs().catch(() => {});
    loadAuditEvents().catch(() => {});
    loadTeamDashboard().catch(() => {});
    loadTranslationalDashboard().catch(() => {});
  }, 5000);
}

document.addEventListener("DOMContentLoaded", mountWorkbench);
