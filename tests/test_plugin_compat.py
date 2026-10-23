from pathlib import Path

import pytest

from runner import plugin_compat

REPO = Path(__file__).resolve().parent.parent


def _release(tmp_path, *, plugin: str, configs: dict[str, str]) -> Path:
    up = tmp_path / "upstream"
    (up / "conf").mkdir(parents=True)
    (up / "nextflow.config").write_text(
        f"plugins {{\n    id '{plugin}'\n}}\n" + configs.pop("nextflow.config", ""))
    for name, body in configs.items():
        (up / "conf" / name).write_text(body)
    return up


def test_flags_a_removed_nf_validation_param_under_nf_schema_2(tmp_path):
    up = _release(tmp_path, plugin="nf-schema@2.5.1",
                  configs={"test.config": "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"})
    issues = plugin_compat.check(up)
    assert len(issues) == 1
    assert "conf/test.config" in issues[0]
    assert "validationSchemaIgnoreParams" in issues[0]
    assert "validation.defaultIgnoreParams" in issues[0]      # names the replacement
    assert "inert" in issues[0]                               # says it does not affect results


def test_one_advisory_per_param_even_when_several_profiles_repeat_it(tmp_path):
    # scrnaseq sets the same dead option in three test profiles. Repeating the whole explanation
    # once per file would bury the run's own output.
    body = "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"
    up = _release(tmp_path, plugin="nf-schema@2.5.1",
                  configs={"test.config": body, "test_full.config": body})
    issues = plugin_compat.check(up)
    assert len(issues) == 1
    assert "conf/test.config" in issues[0] and "conf/test_full.config" in issues[0]


def test_silent_for_a_release_that_declares_nf_validation_1x(tmp_path):
    # The same param is CORRECT there — flagging it would be a false positive on most of the library.
    up = _release(tmp_path, plugin="nf-validation@1.1.3",
                  configs={"test.config": "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"})
    assert plugin_compat.check(up) == []


def test_silent_when_the_release_is_clean(tmp_path):
    up = _release(tmp_path, plugin="nf-schema@2.5.1",
                  configs={"test.config": "params {\n    fasta = 'x.fa'\n}\n"})
    assert plugin_compat.check(up) == []


def test_silent_when_no_plugin_is_declared(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "nextflow.config").write_text("params { fasta = 'x.fa' }\n")
    assert plugin_compat.check(up) == []


def test_advisory_states_nfclaw_neutralises_the_warning(tmp_path):
    # The advisory must say nf-claw suppresses the warning (via validation.ignoreParams), so the
    # behaviour is not mistaken for nf-claw silently hiding an upstream fault.
    up = _release(tmp_path, plugin="nf-schema@2.5.1",
                  configs={"test.config": "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"})
    issue = plugin_compat.check(up)[0]
    assert "validation.ignoreParams" in issue and "untouched" in issue


def test_removed_params_in_use_lists_the_names(tmp_path):
    up = _release(tmp_path, plugin="nf-schema@2.5.1",
                  configs={"test.config": "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"})
    assert plugin_compat.removed_params_in_use(up) == ["validationSchemaIgnoreParams"]


def test_removed_params_in_use_empty_for_a_clean_or_1x_release(tmp_path):
    # Same param, but declared under nf-validation 1.x where it is correct — nothing to neutralise.
    up = _release(tmp_path, plugin="nf-validation@1.1.3",
                  configs={"test.config": "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n"})
    assert plugin_compat.removed_params_in_use(up) == []


def test_write_ignore_params_config_adds_the_names_to_validation_ignoreparams(tmp_path):
    out = plugin_compat.write_ignore_params_config(
        ["validationSchemaIgnoreParams", "validationMonochromeLogs"], tmp_path / "compat.config")
    text = out.read_text()
    assert "validation { ignoreParams = ['validationSchemaIgnoreParams', 'validationMonochromeLogs'] }" in text
    assert text.lstrip().startswith("//")                      # explains itself for anyone who opens it


def test_known_plugin_bug_is_flagged(tmp_path):
    # nf-core-utils@0.4.0 logs a spurious "positional argument `nextflow`" on every run. A release
    # that declares it gets an advisory naming the exact version.
    up = _release(tmp_path, plugin="nf-core-utils@0.4.0", configs={})
    warnings = plugin_compat.known_plugin_warnings(up)
    assert len(warnings) == 1
    assert "nf-core-utils@0.4.0" in warnings[0]
    assert "positional argument" in warnings[0] and "inert" in warnings[0].lower()


def test_known_plugin_bug_silent_for_other_versions(tmp_path):
    # Self-clearing: a different (e.g. future, fixed) version of the same plugin is not flagged.
    up = _release(tmp_path, plugin="nf-core-utils@0.5.0", configs={})
    assert plugin_compat.known_plugin_warnings(up) == []


def test_known_plugin_bug_silent_when_no_such_plugin(tmp_path):
    up = _release(tmp_path, plugin="nf-schema@2.5.1", configs={})
    assert plugin_compat.known_plugin_warnings(up) == []


def test_the_pinned_scrnaseq_release_is_the_known_offender():
    # Anchored to the real library: scrnaseq is the one pinned release that declares nf-schema 2.x
    # while its test profiles still set the 1.x param — the warning seen on every `--demo` run.
    # If a future bump fixes it upstream, this test fails and the known-issues entry comes out.
    up = REPO / "pipelines" / "scrnaseq" / "upstream"
    if not (up / "nextflow.config").exists():
        pytest.skip("submodule not initialised")
    issues = plugin_compat.check(up)
    assert issues and any("conf/test.config" in i for i in issues)


def test_no_other_pinned_release_is_flagged():
    # The rest of the library declares nf-validation 1.x (where the param is correct) or is clean,
    # so this advisory must stay quiet for them — an advisory that cries wolf gets ignored.
    pipelines = REPO / "pipelines"
    flagged = sorted(
        d.name for d in pipelines.iterdir()
        if (d / "upstream" / "nextflow.config").exists() and plugin_compat.check(d / "upstream")
    )
    assert flagged in ([], ["scrnaseq"]), flagged


def test_the_pinned_sarek_release_declares_the_buggy_plugin():
    # Anchored to the real library: sarek 3.9.0 declares nf-core-utils@0.4.0, whose observer logs the
    # spurious "positional argument `nextflow`" on every run. If a future bump moves off 0.4.0, this
    # test fails and the known-issues entry (and the _KNOWN_PLUGIN_BUGS entry) can come out.
    up = REPO / "pipelines" / "sarek" / "upstream"
    if not (up / "nextflow.config").exists():
        pytest.skip("submodule not initialised")
    warnings = plugin_compat.known_plugin_warnings(up)
    assert warnings and any("nf-core-utils@0.4.0" in w for w in warnings)
