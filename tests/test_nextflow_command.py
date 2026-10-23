import subprocess

from runner import nextflow_command as nc
from runner.nextflow_command import may_set_params


def test_displayed_environment_names_cannot_become_shell_instructions():
    line = nc.shell_line("echo COMMAND_RAN", {"NXF_X; printf ENV_NAME_INJECTION;#": "value"})
    result = subprocess.run(["bash", "-c", line], capture_output=True, text=True)
    assert "ENV_NAME_INJECTION" not in result.stdout
    assert "COMMAND_RAN" not in result.stdout
    assert result.returncode != 0


def test_compose_profile_orders_test_first_modifiers_last():
    assert nc.compose_profile("docker", demo=True, modifiers=("arm64",)) == "test,docker,arm64"


def test_compose_profile_dedups():
    assert nc.compose_profile("docker,docker") == "docker"


def test_build_command_shape(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    pf = tmp_path / "params.json"
    pf.write_text("{}")
    cmd, s = nc.build(upstream=up, profile="docker", params_file=pf, resume=True)
    assert cmd[:2] == ["nextflow", "run"]
    assert "-profile" in cmd and "docker" in cmd
    assert "-params-file" in cmd and "-resume" in cmd
    assert cmd[2] == up.as_posix()


def test_command_never_carries_a_positional_argument(tmp_path):
    # nf-core pipelines reject positional arguments (anything not behind a flag), and sarek's
    # nf-core-utils plugin warns naming the offending token. nfclaw must never be the source of one:
    # the command is built as an argv list and handed to Popen without a shell, so nothing can be
    # word-split or glob-expanded into an extra token. This pins that as an invariant.
    cmd, _ = nc.build(
        upstream=tmp_path / "up", profile="test,docker",
        params_file=tmp_path / "params.json", resume=True,
        work_dir=tmp_path / "work", extra_configs=(tmp_path / "extra.config",))
    assert cmd[0:2] == ["nextflow", "run"]
    assert cmd[2] == (tmp_path / "up").as_posix()          # the pipeline — the only bare argument
    # Every remaining token is either an option or the value directly after one.
    rest = cmd[3:]
    i = 0
    while i < len(rest):
        assert rest[i].startswith("-"), f"positional argument in the command: {rest[i]!r}"
        i += 1 if rest[i] == "-resume" else 2              # flags take no value; options take one
    assert i == len(rest)


def test_only_engine_profiles_are_known_not_to_set_params():
    assert not may_set_params("docker")
    assert not may_set_params("singularity, arm64,debug")
    assert may_set_params("test,docker")
    assert may_set_params("docker,uppmax")                  # an institutional profile can set params


def test_stub_profiles_names_the_selected_profiles_whose_config_runs_stubs(tmp_path):
    (tmp_path / "conf").mkdir()
    (tmp_path / "nextflow.config").write_text(
        "profiles {\n    docker { docker.enabled = true }\n"
        "    test      { includeConfig 'conf/test.config'      }\n"
        "    test_full {\n        includeConfig 'conf/test_full.config'\n    }\n}\n")
    (tmp_path / "conf/test.config").write_text(
        "/*\n    stubRun = true only below, not in this comment\n*/\n\nstubRun = true\n"
        "params { input = 'x' }\n")
    (tmp_path / "conf/test_full.config").write_text(
        "// stubRun = true\n/*\nstubRun = true\n*/\nparams { input = 'y' }  // stubRun = true\n")
    assert nc.stub_profiles(tmp_path, "test,docker") == ["test"]
    assert nc.stub_profiles(tmp_path, "test_full,docker") == []
    assert nc.stub_profiles(tmp_path, "docker") == []
    assert nc.stub_profiles(tmp_path / "missing", "test") == []
    (tmp_path / "nextflow.config").write_text("profiles { test { includeConfig 'conf/test.config' } }\n")
    assert nc.stub_profiles(tmp_path, "test") == ["test"]
