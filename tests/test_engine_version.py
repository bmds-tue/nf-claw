from runner import engine_version as ev


def test_required_spec_reads_manifest(tmp_path):
    cfg = tmp_path / "nextflow.config"
    cfg.write_text("manifest {\n    nextflowVersion = '!>=25.04.3'\n}\n")
    assert ev.required_spec(cfg) == "!>=25.04.3"


def test_required_spec_none_when_absent(tmp_path):
    cfg = tmp_path / "nextflow.config"
    cfg.write_text("manifest { name = 'x' }\n")
    assert ev.required_spec(cfg) is None


def test_minimum_version_extracts_the_pin_for_nxf_ver():
    # skill.md tells the agent which engine to pin; the version must come from the manifest, never
    # be invented. A newer Nextflow major changes the config parser and adds warnings the release
    # never saw (scrnaseq 4.2.0 on 26.04.6 vs 25.10.4 — see docs/known-issues.md).
    assert ev.minimum_version("!>=25.10.4") == "25.10.4"
    assert ev.minimum_version(">=22.10.1") == "22.10.1"


def test_minimum_version_is_silent_on_a_spec_it_cannot_model():
    for spec in (None, "", ">=23.04.0 && <24", "!>=22.10.1, <23"):
        assert ev.minimum_version(spec) is None


def test_java_major_reads_modern_and_legacy_version_strings():
    assert ev.java_major('openjdk version "17.0.20.1" 2026-08-18\nOpenJDK Runtime') == 17
    assert ev.java_major('java version "1.8.0_402"\nJava(TM) SE Runtime') == 8
    assert ev.java_major('openjdk version "21" 2023-09-19\n') == 21
    assert ev.java_major("no version here") is None


def test_engines_before_21_10_cannot_run_on_java_17():
    # Nextflow 21.04.0 cannot compile a config on Java 17 ("Unsupported class file major version
    # 61"); 21.10.3 can — both verified on OpenJDK 17.0.20.
    assert not ev.runs_on_java("21.04.0", 17)
    assert not ev.runs_on_java("20.10.0", 21)
    assert ev.runs_on_java("21.04.0", 11)
    assert ev.runs_on_java("21.10.3", 17)
    assert ev.runs_on_java("24.10.5", 21)


def test_the_java_nextflow_runs_on_follows_its_launcher():
    assert ev.java_command({"NXF_JAVA_HOME": "/a", "JAVA_HOME": "/b"}) == "/a/bin/java"
    assert ev.java_command({"JAVA_HOME": "/b"}) == "/b/bin/java"
    assert ev.java_command({}) == "java"
