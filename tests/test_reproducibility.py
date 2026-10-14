"""Run-time advisories for pinned tools whose results vary between executions of identical input."""
from runner import reproducibility


def _tree(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


TAXONOMY = {"modules/local/dada2_taxonomy/main.nf":
            'taxa <- assignTaxonomy(seq, "$database", multithread = $task.cpus)\n'}
RAREFY = {"modules/local/qiime2_diversity_core/main.nf":
          "qiime diversity core-metrics-phylogenetic \\\\\n    --p-sampling-depth $mindepth \\\\\n"}


def test_dada2_taxonomy_and_unseeded_rarefaction_are_announced(tmp_path):
    notes = reproducibility.advisories(_tree(tmp_path, {**TAXONOMY, **RAREFY}), {})
    assert len(notes) == 2
    assert any("assignTaxonomy" in n and "std::random_device" in n for n in notes)
    assert any("rarefy" in n and "without a seed" in n for n in notes)


def test_explicitly_skipped_steps_are_not_announced(tmp_path):
    tree = _tree(tmp_path, {**TAXONOMY, **RAREFY})
    assert reproducibility.advisories(tree, {"skip_taxonomy": True, "skip_qiime": True}) == []
    assert len(reproducibility.advisories(tree, {"skip_dada_taxonomy": True})) == 1
    assert len(reproducibility.advisories(tree, {"skip_diversity_indices": True})) == 1


def test_pipelines_without_these_steps_get_no_advisory(tmp_path):
    tree = _tree(tmp_path, {"modules/local/fastqc/main.nf": "fastqc $reads\n",
                            "main.nf": "// assignTaxonomy is mentioned only in a comment\n"})
    assert reproducibility.advisories(tree, {}) == []


def test_the_runner_announces_variability_before_launch(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path
    from runner import orchestration
    up = tmp_path / "pipelines" / "mini" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(Path(__file__).parent / "fixtures" / "mini" / "nextflow_schema.json", up)
    _tree(up, TAXONOMY)
    (tmp_path / "pipelines" / "mini" / "skill.md").write_text("---\nname: mini\n---\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    seen = []
    res = orchestration.run_pipeline(
        "mini", repo_root=tmp_path, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
        write_provenance=False, timeout_seconds=10, on_warning=seen.append)
    assert any("assignTaxonomy" in w for w in res.warnings)
    assert any("assignTaxonomy" in w for w in seen)            # said before launch, not after


SOURMASH = {
    "subworkflows/local/sourmash_create/main.nf":
        "def ch_sketch_input = ch_library.flatMap { meta, genomes ->\n"
        "    genomes\n        .sort()\n        .collate(batch_size)\n",
    "subworkflows/local/preprocessing/main.nf":
        "ch_prepped_dna_fastas = ch_x\n    .map { _meta, fasta -> [[id: params.dbname], fasta] }\n"
        "    .groupTuple()\n",
    "conf/test.config": "params {\n    build_sourmash_dna = true\n    build_sourmash_protein = true\n}\n",
}


def test_in_place_sort_of_shared_grouped_genomes_is_announced_when_sourmash_runs(tmp_path):
    tree = _tree(tmp_path, SOURMASH)
    for params, demo in (({"build_sourmash_dna": True}, False),
                         ({"build_sourmash_protein": True}, False),
                         ({}, True)):                      # the bundled test profile enables it
        notes = reproducibility.advisories(tree, params, demo=demo)
        assert len(notes) == 1
        assert "ConcurrentModificationException" in notes[0]
        assert "--build-sourmash-dna false" in notes[0]


def test_in_place_sort_advisory_needs_sourmash_enabled(tmp_path):
    tree = _tree(tmp_path, SOURMASH)
    assert reproducibility.advisories(tree, {}) == []          # off by default outside --demo
    assert reproducibility.advisories(
        tree, {"build_sourmash_dna": False, "build_sourmash_protein": False}, demo=True) == []


def test_in_place_sort_advisory_clears_when_grouping_no_longer_shares_lists(tmp_path):
    fixed = {**SOURMASH, "subworkflows/local/preprocessing/main.nf":
             "ch_prepped_dna_fastas = ch_x\n    .groupBy()\n"}
    assert reproducibility.advisories(_tree(tmp_path, fixed), {}, demo=True) == []
