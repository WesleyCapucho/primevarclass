from __future__ import annotations

import argparse

from .api import run_api
from .biological_discovery import export_biological_discovery_package
from .candidate_public_runner import run_candidate_public_benchmark_pipeline
from .continuous_learning import export_continuous_learning_package
from .core import demo_full_pipeline_run, print_usage_guide, run_full_training_pipeline
from .data_sources import ingest_sources_from_config, train_from_source_config
from .development_progress import export_development_progress_dashboard
from .frozen_study_refresh import refresh_frozen_study_assessment
from .gene_expansion import export_gene_expansion_assessment
from .gnomad_gene_subset import DEFAULT_TARGET_GENES, export_gnomad_gene_subset
from .independent_data_expansion import DEFAULT_EXPANSION_GENES, export_independent_data_expansion_package
from .independent_data_staging_closure import export_independent_data_staging_closure_package
from .independent_public_autostager import export_independent_open_source_autostage_package
from .launch_readiness import export_launch_readiness_package
from .monitoring import build_longitudinal_study_monitor, export_longitudinal_study_monitor
from .brca1_engine_execution import export_brca1_engine_execution_package
from .brca1_fragment_preparation import export_brca1_fragment_preparation_package
from .brca1_paired_mutant_execution import export_brca1_paired_mutant_execution_package
from .brca1_mutant_geometry_qc import export_brca1_mutant_geometry_qc_package
from .multigene_annotation_enrichment import export_multigene_annotation_enrichment_package
from .multigene_rollout import export_multigene_rollout_plan
from .multigene_study_factory import export_multigene_study_factory
from .protein_impact import export_protein_impact_package
from .prospective_validation_closure import export_prospective_validation_closure_package
from .public_sync_closure import export_public_sync_closure_package
from .quantum_proteomics import export_quantum_proteomics_package
from .real_data_preparation import export_real_data_preparation_bundle
from .public_study_runner import run_public_benchmark_pipeline
from .study_compare import build_study_comparison, export_study_comparison
from .study import run_publication_study
from .validation_credibility_closure import export_validation_credibility_closure


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PrimeVarClass - pipeline para classificacao de variantes missense com validacao BRCA-first e expansao multigenica"
    )
    parser.add_argument("--input-csv", type=str, default=None, help="Caminho para o CSV canonico de entrada")
    parser.add_argument("--source-config", type=str, default=None, help="Arquivo TOML com multiplas fontes de dados")
    parser.add_argument("--study-config", type=str, default=None, help="Arquivo TOML descrevendo um estudo com treino e validacao externa")
    parser.add_argument("--refresh-frozen-study-assessment", action="store_true", help="Regerar comparative, claim e external-robustness packages a partir de um estudo ja congelado em --output-dir")
    parser.add_argument("--prepare-real-data", action="store_true", help="Gerar os artefatos canonicos e os TOMLs reais a partir dos downloads brutos")
    parser.add_argument("--build-gene-expansion", action="store_true", help="Avaliar genes candidatos para expansao multicohorte/multigene a partir de ClinVar + MaveDB")
    parser.add_argument("--build-multigene-rollout", action="store_true", help="Gerar um plano priorizado de rollout multigenico a partir do gene-expansion e do prime-intelligence")
    parser.add_argument("--build-multigene-study-factory", action="store_true", help="Gerar scaffolds de estudos reais por gene a partir do rollout multigenico")
    parser.add_argument("--build-biological-discovery", action="store_true", help="Gerar um pacote de hotspots, variantes prioritarias e hipoteses funcionais a partir do manifesto de dados reais")
    parser.add_argument("--build-protein-impact", action="store_true", help="Gerar uma fila mecanistica para proteomica/modelagem 3D a partir do biological-discovery")
    parser.add_argument("--build-quantum-proteomics", action="store_true", help="Gerar alvos QM/QM-MM/MD/docking a partir do protein-impact")
    parser.add_argument("--build-multigene-annotation-enrichment", action="store_true", help="Gerar matriz multigenica linha a linha com coordenadas, gnomAD e MaveDB")
    parser.add_argument("--build-gnomad-gene-subset", action="store_true", help="Baixar subset local amplo do gnomAD por genes-alvo via API publica")
    parser.add_argument("--build-public-sync-closure", action="store_true", help="Gerar cache/fila retomavel para sync publico gnomAD/MaveDB")
    parser.add_argument("--build-brca1-engine-execution", action="store_true", help="Gerar pacote executavel BRCA1 com AlphaFold, engines, instalador e runner")
    parser.add_argument("--build-brca1-fragment-preparation", action="store_true", help="Preparar fragmentos BRCA1 reais derivados de AlphaFold e executar baseline xTB opcional")
    parser.add_argument("--build-brca1-paired-mutant-execution", action="store_true", help="Gerar pares BRCA1 referencia-vs-mutante e executar xTB de triagem")
    parser.add_argument("--build-brca1-mutant-geometry-qc", action="store_true", help="Revisar geometria dos mutantes BRCA1 e executar otimizacao xTB opcional")
    parser.add_argument("--build-prospective-validation-closure", action="store_true", help="Gerar protocolo prospectivo e fila de confirmacao funcional/estrutural")
    parser.add_argument("--build-development-progress", action="store_true", help="Recalcular tabela global de progresso da plataforma")
    parser.add_argument("--build-validation-credibility-closure", action="store_true", help="Consolidar evidencias de validacao, credibilidade e lacunas restantes")
    parser.add_argument("--build-continuous-learning", action="store_true", help="Gerar o pacote de aprendizado continuo com sync publico, resolucao e retraining automatizavel")
    parser.add_argument("--build-independent-data-expansion", action="store_true", help="Gerar plano e templates para ampliar treino/validacao com bancos reais independentes")
    parser.add_argument("--autostage-open-independent-sources", action="store_true", help="Baixar/stagear fontes publicas abertas independentes via APIs oficiais")
    parser.add_argument("--build-independent-data-staging-closure", action="store_true", help="Auditar bancos independentes baixados localmente e gerar config pronta para nova rodada de treino")
    parser.add_argument("--build-launch-readiness", action="store_true", help="Auditar prontidao para publicacao cientifica, staging web e lancamento publico")
    parser.add_argument("--clinvar-variant-summary-path", type=str, default=None, help="Arquivo bruto do ClinVar variant_summary (.txt/.txt.gz)")
    parser.add_argument("--brca-exchange-release-path", type=str, default=None, help="Release bruto do BRCA Exchange (.tar/.tar.gz)")
    parser.add_argument("--mavedb-dump-path", type=str, default=None, help="Dump bruto publico do MaveDB (.zip)")
    parser.add_argument("--gnomad-annotations-path", type=str, default=None, help="Arquivo opcional direto do gnomAD com anotacoes BRCA; se omitido, a API oficial do gnomAD sera consultada")
    parser.add_argument("--real-data-manifest-path", type=str, default=None, help="Manifesto JSON do preparo real para reutilizar os artefatos canonicos")
    parser.add_argument("--biological-discovery-manifest-path", type=str, default=None, help="Manifesto opcional do pacote biologico para enriquecer o prime-intelligence")
    parser.add_argument("--gene-expansion-manifest-path", type=str, default=None, help="Manifesto opcional do pacote de expansao para enriquecer o prime-intelligence")
    parser.add_argument("--prime-intelligence-manifest-path", type=str, default=None, help="Manifesto opcional do prime-intelligence para priorizar o rollout multigenico")
    parser.add_argument("--multigene-rollout-manifest-path", type=str, default=None, help="Manifesto do rollout multigenico para gerar scaffolds de estudo por gene")
    parser.add_argument("--multigene-real-benchmark-manifest-path", type=str, default=None, help="Manifesto do benchmark multigenico real")
    parser.add_argument("--multigene-annotation-enrichment-manifest-path", type=str, default=None, help="Manifesto do enriquecimento multigenico linha a linha")
    parser.add_argument("--public-sync-closure-manifest-path", type=str, default=None, help="Manifesto do fechamento de sync publico")
    parser.add_argument("--protein-impact-manifest-path", type=str, default=None, help="Manifesto do protein-impact para gerar alvos quantum proteomics")
    parser.add_argument("--brca1-structural-campaign-manifest-path", type=str, default=None, help="Manifesto da campanha estrutural BRCA1")
    parser.add_argument("--brca1-engine-execution-manifest-path", type=str, default=None, help="Manifesto da execucao/preflight BRCA1 com engines")
    parser.add_argument("--brca1-fragment-preparation-manifest-path", type=str, default=None, help="Manifesto do preparo de fragmentos BRCA1 AlphaFold/xTB")
    parser.add_argument("--brca1-paired-mutant-execution-manifest-path", type=str, default=None, help="Manifesto da execucao pareada BRCA1 referencia-vs-mutante")
    parser.add_argument("--brca1-mutant-geometry-qc-manifest-path", type=str, default=None, help="Manifesto da revisao geometrica dos mutantes BRCA1")
    parser.add_argument("--prospective-validation-closure-manifest-path", type=str, default=None, help="Manifesto do fechamento prospectivo/experimental")
    parser.add_argument("--validation-credibility-closure-manifest-path", type=str, default=None, help="Manifesto do fechamento de validacao e credibilidade")
    parser.add_argument("--independent-data-expansion-manifest-path", type=str, default=None, help="Manifesto do plano de bancos independentes para fechar staging local")
    parser.add_argument("--quantum-proteomics-manifest-path", type=str, default=None, help="Manifesto do quantum-proteomics para fechamento de credibilidade")
    parser.add_argument("--claim-strength-manifest-path", type=str, default=None, help="Manifesto opcional do claim-strength para fechamento de credibilidade")
    parser.add_argument("--max-modeling-variants", type=int, default=25, help="Numero maximo de variantes na fila de modelagem proteica/3D")
    parser.add_argument("--max-quantum-targets", type=int, default=12, help="Numero maximo de alvos QM/QM-MM/MD/docking no pacote quantum proteomics")
    parser.add_argument("--max-live-gnomad-queries", type=int, default=48, help="Numero maximo de consultas live gnomAD para enriquecimento multigenico")
    parser.add_argument("--skip-live-gnomad", action="store_true", help="Nao consultar gnomAD ao vivo no enriquecimento multigenico")
    parser.add_argument("--gnomad-batch-size", type=int, default=25, help="Tamanho do lote para o runner retomavel de sync gnomAD")
    parser.add_argument("--gnomad-sleep-seconds", type=int, default=6, help="Pausa entre consultas gnomAD no runner retomavel")
    parser.add_argument("--existing-gnomad-cache-path", type=str, default=None, help="Cache gnomAD existente para merge incremental")
    parser.add_argument("--gnomad-release-table-path", type=str, default=None, help="Tabela/VCF local do gnomAD ou subset oficial para fechar evidencias linha a linha sem rate limit")
    parser.add_argument("--gnomad-dataset", type=str, default="gnomad_r4", help="Dataset gnomAD usado em consultas GraphQL, ex.: gnomad_r4")
    parser.add_argument("--target-gene", action="append", default=None, help="Gene-alvo para subset gnomAD; pode ser repetido")
    parser.add_argument("--include-restricted-sources", action="store_true", help="Incluir fontes controladas/restritas no plano de expansao de dados independentes")
    parser.add_argument("--refresh-open-source-staging", action="store_true", help="Refazer downloads do autostager de fontes publicas abertas mesmo se os arquivos ja existirem")
    parser.add_argument("--max-gwas-per-gene", type=int, default=8, help="Numero maximo de associacoes GWAS por gene no autostager")
    parser.add_argument("--max-pdb-per-gene", type=int, default=8, help="Numero maximo de estruturas RCSB PDB por gene no autostager")
    parser.add_argument("--execute-engines-if-available", action="store_true", help="Executar comandos BRCA1 se engines reais estiverem disponiveis")
    parser.add_argument("--execute-xtb-baseline", action="store_true", help="Executar xTB single-point nos fragmentos BRCA1 preparados")
    parser.add_argument("--fragment-radius-angstrom", type=float, default=5.0, help="Raio em Angstrom para selecionar o microambiente local do residuo mutado")
    parser.add_argument("--fragment-max-atoms", type=int, default=90, help="Numero maximo de atomos por fragmento estrutural BRCA1")
    parser.add_argument("--max-xtb-runs", type=int, default=2, help="Numero maximo de fragmentos BRCA1 para executar xTB nesta rodada")
    parser.add_argument("--max-mutant-pairs", type=int, default=3, help="Numero maximo de pares referencia-vs-mutante BRCA1 para executar xTB")
    parser.add_argument("--execute-xtb-opt", action="store_true", help="Executar otimizacao xTB loose nos mutantes BRCA1 selecionados")
    parser.add_argument("--max-xtb-opt-pairs", type=int, default=2, help="Numero maximo de mutantes BRCA1 para otimizar com xTB")
    parser.add_argument("--xtb-timeout-sec", type=int, default=240, help="Timeout por execucao xTB em segundos")
    parser.add_argument("--exclude-gene", action="append", default=None, help="Gene a excluir do ranking de expansao; pode ser repetido")
    parser.add_argument("--top-k-genes", type=int, default=12, help="Numero de genes recomendados no pacote de expansao")
    parser.add_argument("--workspace-root", type=str, default=None, help="Raiz do workspace onde os artefatos canonicos e configs reais serao escritos")
    parser.add_argument("--launch-workspace-root", type=str, default=None, help="Raiz do workspace a auditar no pacote de launch readiness")
    parser.add_argument("--public-study-run", action="store_true", help="Executar o fluxo integrado de estudo publico: resolucao + preflight + benchmark + execution board")
    parser.add_argument("--candidate-public-study-run", action="store_true", help="Executar a rerrodada controlada a partir de um candidate study config")
    parser.add_argument("--candidate-promotion-manifest", type=str, default=None, help="Manifesto opcional do candidate-promotion package")
    parser.add_argument("--bootstrap-root-dir", type=str, default=None, help="Diretorio raiz de bootstrap/resolucao publica a reutilizar no estudo publico")
    parser.add_argument("--delivery-dir", type=str, default=None, help="Diretorio opcional com a entrega local dos datasets reais para autofill do handoff")
    parser.add_argument("--require-live-public-ready", action="store_true", help="Falhar se o estudo publico ainda nao estiver pronto para uma rodada live com fontes publicas resolvidas")
    parser.add_argument("--require-candidate-ready", action="store_true", help="Falhar se o candidate config ainda nao estiver pronto segundo o pacote de promocao")
    parser.add_argument("--compare-study-baseline", type=str, default=None, help="Diretorio de um estudo baseline exportado")
    parser.add_argument("--compare-study-candidate", type=str, default=None, help="Diretorio de um estudo candidato exportado")
    parser.add_argument("--monitor-study-dir", action="append", default=None, help="Diretorio de estudo a incluir no monitor longitudinal; pode ser repetido")
    parser.add_argument("--output-dir", type=str, default="primevarclass_results_cli", help="Diretorio de saida")
    parser.add_argument("--mode", type=str, default="hybrid", choices=["codon", "prime_mass", "hybrid"], help="Modo de codificacao prima")
    parser.add_argument("--model-family", action="append", default=None, help="Familia de modelo a incluir; pode ser repetido")
    parser.add_argument("--high-confidence-only", action="store_true", help="Filtrar variantes de maior confianca")
    parser.add_argument("--demo", action="store_true", help="Executar a demo completa com CSV realista")
    parser.add_argument("--ingest-only", action="store_true", help="Somente integrar e normalizar as fontes, sem treinar")
    parser.add_argument("--serve-api", action="store_true", help="Iniciar a API web do PrimeVarClass")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host da API")
    parser.add_argument("--port", type=int, default=8000, help="Porta da API")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.serve_api:
        run_api(host=args.host, port=args.port)
        return 0
    if args.build_gene_expansion:
        if not args.clinvar_variant_summary_path:
            parser.error("--build-gene-expansion exige --clinvar-variant-summary-path.")
        if not args.mavedb_dump_path:
            parser.error("--build-gene-expansion exige --mavedb-dump-path.")
        results = export_gene_expansion_assessment(
            clinvar_variant_summary_path=args.clinvar_variant_summary_path,
            mavedb_dump_path=args.mavedb_dump_path,
            output_dir=args.output_dir,
            exclude_genes=args.exclude_gene,
            top_k=args.top_k_genes,
        )
        print("PrimeVarClass gene-expansion assessment finished.")
        print(f"Gene expansion manifest: {results['gene_expansion_manifest_path']}")
        print(f"Gene expansion report: {results['gene_expansion_report_markdown_path']}")
        print(f"Gene expansion candidates: {results['gene_expansion_candidates_path']}")
        print(f"Gene expansion panel template: {results['gene_expansion_panel_template_path']}")
        return 0
    if args.build_multigene_rollout:
        if not args.gene_expansion_manifest_path:
            parser.error("--build-multigene-rollout exige --gene-expansion-manifest-path.")
        results = export_multigene_rollout_plan(
            gene_expansion_manifest_path=args.gene_expansion_manifest_path,
            prime_intelligence_manifest_path=args.prime_intelligence_manifest_path,
            output_dir=args.output_dir,
            max_total_genes=max(args.top_k_genes, 1),
        )
        print("PrimeVarClass multigene rollout finished.")
        print(f"Multigene rollout manifest: {results['manifest_path']}")
        print(f"Multigene rollout report: {results['markdown_path']}")
        print(f"Multigene rollout table: {results['rollout_csv_path']}")
        return 0
    if args.build_multigene_study_factory:
        if not args.multigene_rollout_manifest_path:
            parser.error("--build-multigene-study-factory exige --multigene-rollout-manifest-path.")
        results = export_multigene_study_factory(
            rollout_manifest_path=args.multigene_rollout_manifest_path,
            output_dir=args.output_dir,
            workspace_root=args.workspace_root,
        )
        print("PrimeVarClass multigene study factory finished.")
        print(f"Multigene study factory manifest: {results['manifest_path']}")
        print(f"Multigene study scaffold index: {results['scaffold_index_path']}")
        print(f"Multigene study tasks: {results['tasks_path']}")
        return 0
    if args.build_gnomad_gene_subset:
        results = export_gnomad_gene_subset(
            output_dir=args.output_dir,
            target_genes=args.target_gene or DEFAULT_TARGET_GENES,
            dataset=args.gnomad_dataset,
        )
        print("PrimeVarClass gnomAD gene subset finished.")
        print(f"gnomAD subset manifest: {results['gnomad_gene_subset_manifest_path']}")
        print(f"gnomAD subset variants: {results['gnomad_gene_subset_variants_path']}")
        return 0
    if args.build_multigene_annotation_enrichment:
        if not args.multigene_real_benchmark_manifest_path:
            parser.error("--build-multigene-annotation-enrichment exige --multigene-real-benchmark-manifest-path.")
        results = export_multigene_annotation_enrichment_package(
            multigene_real_benchmark_manifest_path=args.multigene_real_benchmark_manifest_path,
            output_dir=args.output_dir,
            variant_summary_path=args.clinvar_variant_summary_path,
            run_live_gnomad=not args.skip_live_gnomad,
            max_live_gnomad_queries=args.max_live_gnomad_queries,
        )
        print("PrimeVarClass multigene annotation enrichment finished.")
        print(f"Annotation manifest: {results['multigene_annotation_enrichment_manifest_path']}")
        print(f"Annotation matrix: {results['multigene_variant_annotation_matrix_path']}")
        print(f"Coverage by gene: {results['multigene_annotation_coverage_by_gene_path']}")
        return 0
    if args.build_public_sync_closure:
        if not args.multigene_annotation_enrichment_manifest_path:
            parser.error("--build-public-sync-closure exige --multigene-annotation-enrichment-manifest-path.")
        results = export_public_sync_closure_package(
            multigene_annotation_enrichment_manifest_path=args.multigene_annotation_enrichment_manifest_path,
            output_dir=args.output_dir,
            existing_gnomad_cache_path=args.existing_gnomad_cache_path,
            gnomad_release_table_path=args.gnomad_release_table_path,
            gnomad_batch_size=args.gnomad_batch_size,
            gnomad_sleep_seconds=args.gnomad_sleep_seconds,
        )
        print("PrimeVarClass public sync closure finished.")
        print(f"Public sync manifest: {results['public_sync_closure_manifest_path']}")
        print(f"gnomAD queue: {results['gnomad_sync_queue_path']}")
        print(f"Resume script: {results['resume_gnomad_sync_script_path']}")
        return 0
    if args.build_biological_discovery:
        if not args.real_data_manifest_path:
            parser.error("--build-biological-discovery exige --real-data-manifest-path.")
        results = export_biological_discovery_package(
            real_data_manifest_path=args.real_data_manifest_path,
            output_dir=args.output_dir,
        )
        print("PrimeVarClass biological-discovery package finished.")
        print(f"Biological discovery manifest: {results['biological_discovery_manifest_path']}")
        print(f"Biological discovery report: {results['biological_discovery_report_markdown_path']}")
        print(f"Biological discovery hotspots: {results['biological_discovery_hotspots_path']}")
        print(f"Biological discovery hypotheses: {results['biological_discovery_hypothesis_variants_path']}")
        return 0
    if args.build_protein_impact:
        if not args.biological_discovery_manifest_path:
            parser.error("--build-protein-impact exige --biological-discovery-manifest-path.")
        results = export_protein_impact_package(
            biological_discovery_manifest_path=args.biological_discovery_manifest_path,
            output_dir=args.output_dir,
            max_modeling_variants=args.max_modeling_variants,
        )
        print("PrimeVarClass protein-impact package finished.")
        print(f"Protein impact manifest: {results['protein_impact_manifest_path']}")
        print(f"Protein impact report: {results['protein_impact_report_markdown_path']}")
        print(f"Protein modeling queue: {results['protein_modeling_queue_path']}")
        return 0
    if args.build_quantum_proteomics:
        if not args.protein_impact_manifest_path:
            parser.error("--build-quantum-proteomics exige --protein-impact-manifest-path.")
        results = export_quantum_proteomics_package(
            protein_impact_manifest_path=args.protein_impact_manifest_path,
            output_dir=args.output_dir,
            max_quantum_targets=args.max_quantum_targets,
        )
        print("PrimeVarClass quantum-proteomics package finished.")
        print(f"Quantum proteomics manifest: {results['quantum_proteomics_manifest_path']}")
        print(f"Quantum targets: {results['quantum_targets_path']}")
        print(f"Quantum job templates: {results['quantum_job_templates_dir']}")
        return 0
    if args.build_brca1_engine_execution:
        if not args.brca1_structural_campaign_manifest_path:
            parser.error("--build-brca1-engine-execution exige --brca1-structural-campaign-manifest-path.")
        results = export_brca1_engine_execution_package(
            brca1_structural_campaign_manifest_path=args.brca1_structural_campaign_manifest_path,
            output_dir=args.output_dir,
            execute_if_available=args.execute_engines_if_available,
        )
        print("PrimeVarClass BRCA1 engine execution package finished.")
        print(f"BRCA1 engine manifest: {results['brca1_engine_execution_manifest_path']}")
        print(f"BRCA1 execution queue: {results['brca1_engine_execution_queue_path']}")
        print(f"Engine install script: {results['structural_engine_install_script_path']}")
        return 0
    if args.build_brca1_fragment_preparation:
        if not args.brca1_engine_execution_manifest_path:
            parser.error("--build-brca1-fragment-preparation exige --brca1-engine-execution-manifest-path.")
        results = export_brca1_fragment_preparation_package(
            brca1_engine_execution_manifest_path=args.brca1_engine_execution_manifest_path,
            output_dir=args.output_dir,
            radius_angstrom=args.fragment_radius_angstrom,
            max_atoms=args.fragment_max_atoms,
            execute_xtb=args.execute_xtb_baseline,
            max_xtb_runs=args.max_xtb_runs,
            xtb_timeout_sec=args.xtb_timeout_sec,
        )
        print("PrimeVarClass BRCA1 fragment preparation package finished.")
        print(f"BRCA1 fragment manifest: {results['brca1_fragment_preparation_manifest_path']}")
        print(f"BRCA1 prepared fragment table: {results['brca1_prepared_fragment_table_path']}")
        print(f"BRCA1 xTB baseline log: {results['brca1_xtb_baseline_execution_log_path']}")
        return 0
    if args.build_brca1_paired_mutant_execution:
        if not args.brca1_fragment_preparation_manifest_path:
            parser.error("--build-brca1-paired-mutant-execution exige --brca1-fragment-preparation-manifest-path.")
        results = export_brca1_paired_mutant_execution_package(
            brca1_fragment_preparation_manifest_path=args.brca1_fragment_preparation_manifest_path,
            output_dir=args.output_dir,
            execute_xtb=args.execute_xtb_baseline,
            max_pairs=args.max_mutant_pairs,
            xtb_timeout_sec=args.xtb_timeout_sec,
        )
        print("PrimeVarClass BRCA1 paired mutant execution package finished.")
        print(f"BRCA1 paired mutant manifest: {results['brca1_paired_mutant_execution_manifest_path']}")
        print(f"BRCA1 paired mutant table: {results['brca1_paired_mutant_table_path']}")
        print(f"BRCA1 paired mutant xTB log: {results['brca1_paired_mutant_xtb_execution_log_path']}")
        return 0
    if args.build_brca1_mutant_geometry_qc:
        if not args.brca1_paired_mutant_execution_manifest_path:
            parser.error("--build-brca1-mutant-geometry-qc exige --brca1-paired-mutant-execution-manifest-path.")
        results = export_brca1_mutant_geometry_qc_package(
            brca1_paired_mutant_execution_manifest_path=args.brca1_paired_mutant_execution_manifest_path,
            output_dir=args.output_dir,
            execute_xtb_opt=args.execute_xtb_opt,
            max_opt_pairs=args.max_xtb_opt_pairs,
            xtb_timeout_sec=args.xtb_timeout_sec,
        )
        print("PrimeVarClass BRCA1 mutant geometry QC package finished.")
        print(f"BRCA1 mutant geometry QC manifest: {results['brca1_mutant_geometry_qc_manifest_path']}")
        print(f"BRCA1 mutant geometry QC table: {results['brca1_mutant_geometry_qc_table_path']}")
        print(f"BRCA1 xTB optimization log: {results['brca1_xtb_optimization_log_path']}")
        return 0
    if args.build_prospective_validation_closure:
        if not args.multigene_annotation_enrichment_manifest_path:
            parser.error("--build-prospective-validation-closure exige --multigene-annotation-enrichment-manifest-path.")
        if not args.brca1_engine_execution_manifest_path:
            parser.error("--build-prospective-validation-closure exige --brca1-engine-execution-manifest-path.")
        results = export_prospective_validation_closure_package(
            multigene_annotation_enrichment_manifest_path=args.multigene_annotation_enrichment_manifest_path,
            brca1_engine_execution_manifest_path=args.brca1_engine_execution_manifest_path,
            validation_credibility_closure_manifest_path=args.validation_credibility_closure_manifest_path,
            public_sync_closure_manifest_path=args.public_sync_closure_manifest_path,
            brca1_paired_mutant_execution_manifest_path=args.brca1_paired_mutant_execution_manifest_path,
            brca1_mutant_geometry_qc_manifest_path=args.brca1_mutant_geometry_qc_manifest_path,
            output_dir=args.output_dir,
        )
        print("PrimeVarClass prospective validation closure finished.")
        print(f"Prospective validation manifest: {results['prospective_validation_closure_manifest_path']}")
        print(f"Confirmation queue: {results['functional_structural_confirmation_queue_path']}")
        print(f"Cohort lock plan: {results['prospective_validation_cohort_plan_path']}")
        print(f"Partner lab handoff: {results['partner_lab_handoff_sheet_path']}")
        print(f"Statistical analysis plan: {results['statistical_analysis_plan_path']}")
        print(f"SOP template manifest: {results['sop_template_manifest_path']}")
        return 0
    if args.build_validation_credibility_closure:
        results = export_validation_credibility_closure(
            output_dir=args.output_dir,
            prime_intelligence_manifest_path=args.prime_intelligence_manifest_path,
            biological_discovery_manifest_path=args.biological_discovery_manifest_path,
            protein_impact_manifest_path=args.protein_impact_manifest_path,
            quantum_proteomics_manifest_path=args.quantum_proteomics_manifest_path,
            multigene_rollout_manifest_path=args.multigene_rollout_manifest_path,
            brca1_engine_execution_manifest_path=args.brca1_engine_execution_manifest_path,
            multigene_real_benchmark_manifest_path=args.multigene_real_benchmark_manifest_path,
            multigene_annotation_enrichment_manifest_path=args.multigene_annotation_enrichment_manifest_path,
            public_sync_closure_manifest_path=args.public_sync_closure_manifest_path,
            prospective_validation_closure_manifest_path=args.prospective_validation_closure_manifest_path,
            brca1_fragment_preparation_manifest_path=args.brca1_fragment_preparation_manifest_path,
            brca1_paired_mutant_execution_manifest_path=args.brca1_paired_mutant_execution_manifest_path,
            brca1_mutant_geometry_qc_manifest_path=args.brca1_mutant_geometry_qc_manifest_path,
            claim_strength_manifest_path=args.claim_strength_manifest_path,
        )
        print("PrimeVarClass validation-credibility closure finished.")
        print(f"Validation closure manifest: {results['validation_credibility_closure_manifest_path']}")
        print(f"Validation closure report: {results['validation_credibility_report_markdown_path']}")
        return 0
    if args.build_development_progress:
        results = export_development_progress_dashboard(
            output_dir=args.output_dir,
            prime_intelligence_manifest_path=args.prime_intelligence_manifest_path,
            biological_discovery_manifest_path=args.biological_discovery_manifest_path,
            protein_impact_manifest_path=args.protein_impact_manifest_path,
            quantum_proteomics_manifest_path=args.quantum_proteomics_manifest_path,
            brca1_engine_execution_manifest_path=args.brca1_engine_execution_manifest_path,
            brca1_fragment_preparation_manifest_path=args.brca1_fragment_preparation_manifest_path,
            brca1_paired_mutant_execution_manifest_path=args.brca1_paired_mutant_execution_manifest_path,
            brca1_mutant_geometry_qc_manifest_path=args.brca1_mutant_geometry_qc_manifest_path,
            multigene_real_benchmark_manifest_path=args.multigene_real_benchmark_manifest_path,
            multigene_annotation_enrichment_manifest_path=args.multigene_annotation_enrichment_manifest_path,
            public_sync_closure_manifest_path=args.public_sync_closure_manifest_path,
            continuous_learning_manifest_path=None,
            validation_credibility_closure_manifest_path=args.validation_credibility_closure_manifest_path,
            prospective_validation_closure_manifest_path=args.prospective_validation_closure_manifest_path,
        )
        print("PrimeVarClass development progress dashboard finished.")
        print(f"Development progress manifest: {results['development_progress_manifest_path']}")
        print(f"Development progress table: {results['development_progress_table_path']}")
        return 0
    if args.build_continuous_learning:
        if not args.source_config:
            parser.error("--build-continuous-learning exige --source-config.")
        results = export_continuous_learning_package(
            config_path=args.source_config,
            output_dir=args.output_dir,
            mode=args.mode,
            high_confidence_only=args.high_confidence_only,
            model_families=args.model_family,
        )
        print("PrimeVarClass continuous-learning package finished.")
        print(f"Continuous-learning manifest: {results['continuous_learning_manifest_path']}")
        print(f"Continuous-learning report: {results['continuous_learning_report_markdown_path']}")
        print(f"Continuous-learning runner: {results['continuous_learning_runner_path']}")
        return 0
    if args.build_independent_data_expansion:
        results = export_independent_data_expansion_package(
            output_dir=args.output_dir,
            target_genes=args.target_gene or DEFAULT_EXPANSION_GENES,
            include_restricted_sources=args.include_restricted_sources,
            report_context={
                "report_purpose": "cli_independent_data_expansion",
            },
        )
        summary = results.get("summary") or {}
        print("PrimeVarClass independent data expansion package finished.")
        print(f"Independent data expansion readiness: {summary.get('independent_data_expansion_percent')}%")
        print(f"Public/independent databases: {summary.get('database_count')}")
        print(f"Supported presets: {summary.get('supported_preset_count')}")
        print(f"Expansion manifest: {results['independent_data_expansion_manifest_path']}")
        print(f"Source templates: {results['independent_source_templates_path']}")
        return 0
    if args.autostage_open_independent_sources:
        results = export_independent_open_source_autostage_package(
            output_dir=args.output_dir,
            workspace_root=args.workspace_root,
            target_genes=args.target_gene or DEFAULT_EXPANSION_GENES,
            refresh=args.refresh_open_source_staging,
            max_gwas_per_gene=args.max_gwas_per_gene,
            max_pdb_per_gene=args.max_pdb_per_gene,
            report_context={
                "report_purpose": "cli_independent_open_source_autostage",
            },
        )
        summary = results.get("summary") or {}
        print("PrimeVarClass independent open-source autostage finished.")
        print(f"Autostaging readiness: {summary.get('autostaging_readiness_percent')}%")
        print(f"Staged sources: {summary.get('staged_source_count')}/{summary.get('attempted_source_count')}")
        print(f"Autostage manifest: {results['independent_open_source_autostage_manifest_path']}")
        print(f"Autostage status: {results['independent_open_source_autostage_status_path']}")
        return 0
    if args.build_independent_data_staging_closure:
        results = export_independent_data_staging_closure_package(
            output_dir=args.output_dir,
            independent_data_expansion_manifest_path=args.independent_data_expansion_manifest_path,
            workspace_root=args.workspace_root,
            target_genes=args.target_gene or DEFAULT_EXPANSION_GENES,
            report_context={
                "report_purpose": "cli_independent_data_staging_closure",
            },
        )
        summary = results.get("summary") or {}
        print("PrimeVarClass independent data staging closure finished.")
        print(f"Staging closure: {summary.get('independent_data_staging_closure_percent')}%")
        print(f"Line-level real-data execution: {summary.get('line_level_real_data_execution_percent')}%")
        print(f"Ready sources: {summary.get('ready_source_count')}/{summary.get('database_count')}")
        print(f"Staging closure manifest: {results['independent_data_staging_closure_manifest_path']}")
        print(f"Ready source config: {results['independent_ready_source_config_path']}")
        print(f"Gap plan: {results['independent_data_staging_gap_plan_path']}")
        return 0
    if args.build_launch_readiness:
        results = export_launch_readiness_package(
            output_dir=args.output_dir,
            workspace_root=args.launch_workspace_root or args.workspace_root,
            include_absolute_paths=True,
            report_context={
                "report_purpose": "cli_launch_readiness",
            },
        )
        summary = results.get("launch_readiness_summary") or {}
        print("PrimeVarClass launch-readiness package finished.")
        print(f"Overall launch readiness: {summary.get('overall_launch_readiness_percent')}%")
        print(f"Scientific publication readiness: {summary.get('scientific_publication_percent')}%")
        print(f"Web launch readiness: {summary.get('web_launch_percent')}%")
        print(f"Launch readiness manifest: {results['launch_readiness_manifest_path']}")
        print(f"Launch readiness report: {results['launch_readiness_report_markdown_path']}")
        return 0
    if args.prepare_real_data:
        if not args.clinvar_variant_summary_path:
            parser.error("--prepare-real-data exige --clinvar-variant-summary-path.")
        if not args.brca_exchange_release_path:
            parser.error("--prepare-real-data exige --brca-exchange-release-path.")
        if not args.mavedb_dump_path:
            parser.error("--prepare-real-data exige --mavedb-dump-path.")
        results = export_real_data_preparation_bundle(
            clinvar_variant_summary_path=args.clinvar_variant_summary_path,
            brca_exchange_release_path=args.brca_exchange_release_path,
            mavedb_dump_path=args.mavedb_dump_path,
            gnomad_annotations_path=args.gnomad_annotations_path,
            output_dir=args.output_dir,
            workspace_root=args.workspace_root,
        )
        print("PrimeVarClass real-data preparation finished.")
        print(f"Preparation manifest: {results['real_data_preparation_manifest_path']}")
        print(f"Preparation report: {results['real_data_preparation_report_markdown_path']}")
        for key, value in results.get("artifact_paths", {}).items():
            print(f"{key}: {value}")
        for key, value in results.get("config_paths", {}).items():
            print(f"{key}: {value}")
        return 0
    if args.refresh_frozen_study_assessment:
        if not args.study_config:
            parser.error("--refresh-frozen-study-assessment exige --study-config.")
        results = refresh_frozen_study_assessment(
            study_output_dir=args.output_dir,
            study_config_path=args.study_config,
            biological_discovery_manifest_path=args.biological_discovery_manifest_path,
            gene_expansion_manifest_path=args.gene_expansion_manifest_path,
        )
        print("PrimeVarClass frozen-study assessment refresh finished.")
        print(f"Comparative evidence manifest: {results['comparative_evidence_manifest_path']}")
        print(f"Claim strength manifest: {results['claim_strength_manifest_path']}")
        print(f"External robustness manifest: {results['external_robustness_manifest_path']}")
        print(f"Prime intelligence manifest: {results['prime_intelligence_manifest_path']}")
        return 0
    if args.compare_study_baseline or args.compare_study_candidate:
        if not args.compare_study_baseline or not args.compare_study_candidate:
            parser.error("--compare-study-baseline exige tambem --compare-study-candidate, e vice-versa.")
        comparison = build_study_comparison(
            baseline_dir=args.compare_study_baseline,
            candidate_dir=args.compare_study_candidate,
        )
        results = export_study_comparison(comparison, output_dir=args.output_dir)
        print("PrimeVarClass study comparison finished.")
        for key, value in results.items():
            print(f"{key}: {value}")
        return 0
    if args.monitor_study_dir:
        monitor = build_longitudinal_study_monitor(study_dirs=args.monitor_study_dir)
        results = export_longitudinal_study_monitor(monitor, output_dir=args.output_dir)
        print("PrimeVarClass longitudinal monitoring finished.")
        for key, value in results.items():
            print(f"{key}: {value}")
        return 0
    if args.demo:
        results = demo_full_pipeline_run(output_dir=args.output_dir)
    elif args.study_config:
        if args.candidate_public_study_run:
            results = run_candidate_public_benchmark_pipeline(
                candidate_config_path=args.study_config,
                output_dir=args.output_dir,
                candidate_promotion_manifest_path=args.candidate_promotion_manifest,
                require_candidate_ready=args.require_candidate_ready,
            )
        elif args.public_study_run:
            results = run_public_benchmark_pipeline(
                config_path=args.study_config,
                output_dir=args.output_dir,
                bootstrap_root_dir=args.bootstrap_root_dir,
                delivery_dir=args.delivery_dir,
                require_live_public_ready=args.require_live_public_ready,
            )
        else:
            results = run_publication_study(config_path=args.study_config, output_dir=args.output_dir)
    elif args.ingest_only:
        if not args.source_config:
            parser.error("--ingest-only exige --source-config.")
        results = ingest_sources_from_config(config_path=args.source_config, output_dir=args.output_dir)
        print("PrimeVarClass data ingestion finished.")
        for key, value in results.get("output_paths", {}).items():
            print(f"{key}: {value}")
        return 0
    elif args.source_config:
        results = train_from_source_config(
            config_path=args.source_config,
            output_dir=args.output_dir,
            mode=args.mode,
            keep_metadata=True,
            high_confidence_only=args.high_confidence_only,
            model_families=args.model_family,
        )
    elif args.input_csv:
        results = run_full_training_pipeline(
            input_csv_path=args.input_csv,
            mode=args.mode,
            output_dir=args.output_dir,
            keep_metadata=True,
            high_confidence_only=args.high_confidence_only,
            model_families=args.model_family,
        )
    else:
        results = demo_full_pipeline_run(output_dir=args.output_dir)

    print("PrimeVarClass execution finished.")

    summary_path = results.get("summary_report_path")
    if summary_path:
        print(f"Summary report: {summary_path}")

    metrics_path = results.get("export_paths", {}).get("metrics")
    if metrics_path:
        print(f"Metrics table: {metrics_path}")

    study_metrics_path = results.get("training_metrics_path")
    if study_metrics_path:
        print(f"Study training metrics: {study_metrics_path}")

    study_summary_path = results.get("study_summary_report_path")
    if study_summary_path:
        print(f"Study summary: {study_summary_path}")

    public_study_run_report_path = results.get("public_study_run_report_markdown_path")
    if public_study_run_report_path:
        print(f"Public study run report: {public_study_run_report_path}")

    cohort_independence_path = results.get("cohort_independence_report_markdown_path")
    if cohort_independence_path:
        print(f"Cohort independence audit: {cohort_independence_path}")

    cohort_freeze_path = results.get("study_cohort_freeze_markdown_path")
    if cohort_freeze_path:
        print(f"Study cohort freeze: {cohort_freeze_path}")

    real_data_handoff_path = results.get("study_real_data_handoff_markdown_path")
    if real_data_handoff_path:
        print(f"Real-data handoff: {real_data_handoff_path}")

    handoff_autofill_path = results.get("study_real_data_handoff_autofill_markdown_path")
    if handoff_autofill_path:
        print(f"Real-data handoff autofill: {handoff_autofill_path}")

    handoff_reconciliation_path = results.get("study_real_data_handoff_reconciliation_markdown_path")
    if handoff_reconciliation_path:
        print(f"Real-data handoff reconciliation: {handoff_reconciliation_path}")

    handoff_application_path = results.get("study_real_data_handoff_application_markdown_path")
    if handoff_application_path:
        print(f"Real-data handoff application: {handoff_application_path}")

    candidate_config_path = results.get("study_real_data_candidate_config_path")
    if candidate_config_path:
        print(f"Real-data candidate config: {candidate_config_path}")

    candidate_promotion_path = results.get("study_real_data_candidate_promotion_markdown_path")
    if candidate_promotion_path:
        print(f"Candidate promotion package: {candidate_promotion_path}")

    candidate_public_run_path = results.get("candidate_public_run_report_markdown_path")
    if candidate_public_run_path:
        print(f"Candidate public study run: {candidate_public_run_path}")

    claim_strength_path = results.get("claim_strength_report_markdown_path")
    if claim_strength_path:
        print(f"Claim strength package: {claim_strength_path}")

    validation_lock_path = results.get("study_validation_lock_markdown_path")
    if validation_lock_path:
        print(f"Study validation lock: {validation_lock_path}")

    execution_board_path = results.get("study_execution_board_markdown_path")
    if execution_board_path:
        print(f"Study execution board: {execution_board_path}")

    pilot_package_path = results.get("translational_pilot_package_markdown_path")
    if pilot_package_path:
        print(f"Translational pilot package: {pilot_package_path}")

    translational_impact_path = results.get("translational_impact_package_markdown_path")
    if translational_impact_path:
        print(f"Translational impact package: {translational_impact_path}")

    platform_completion_path = results.get("platform_completion_markdown_path")
    if platform_completion_path:
        print(f"Platform completion package: {platform_completion_path}")

    final_mile_package_path = results.get("final_mile_package_markdown_path")
    if final_mile_package_path:
        print(f"Final mile package: {final_mile_package_path}")

    source_outputs = results.get("source_ingestion_output_paths", {})
    if source_outputs:
        for key, value in source_outputs.items():
            print(f"{key}: {value}")

    additional_outputs = results.get("additional_export_paths", {})
    if additional_outputs:
        print(f"Additional result files: {len(additional_outputs)}")

    print_usage_guide()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
