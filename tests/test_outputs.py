from runner import outputs


def test_collect_finds_run_metadata_and_multiqc(tmp_path):
    (tmp_path / "pipeline_info").mkdir()
    (tmp_path / "pipeline_info" / "software_versions.yml").write_text("x")
    mqc = tmp_path / "multiqc"
    mqc.mkdir()
    (mqc / "multiqc_report.html").write_text("<html>")
    rep = outputs.collect(tmp_path)
    assert rep.multiqc_report == mqc / "multiqc_report.html"
    assert "pipeline_info/software_versions.yml" in rep.files


def test_collect_excludes_nextflow_internals(tmp_path):
    # When Nextflow launches from the outdir, .nextflow/ and .nextflow.log* land there — they are
    # engine internals, never pipeline results.
    (tmp_path / ".nextflow" / "cache").mkdir(parents=True)
    (tmp_path / ".nextflow" / "cache" / "db").write_text("x")
    (tmp_path / ".nextflow.log").write_text("log")
    (tmp_path / ".nextflow.log.1").write_text("log")
    (tmp_path / "result.txt").write_text("r")
    rep = outputs.collect(tmp_path)
    assert "result.txt" in rep.files
    assert not any(".nextflow" in f for f in rep.files)


def test_collect_excludes_the_provenance_bundle(tmp_path):
    # `nfclaw run` reported "outputs: N files" counting its own params file and logs as results —
    # inconsistent with outputs.sha256, which (rightly) excludes the provenance bundle.
    (tmp_path / "provenance" / "logs").mkdir(parents=True)
    (tmp_path / "provenance" / "params.json").write_text("{}")
    (tmp_path / "provenance" / "logs" / "stdout.txt").write_text("log")
    (tmp_path / "result.txt").write_text("r")
    assert outputs.collect(tmp_path).files == ("result.txt",)
