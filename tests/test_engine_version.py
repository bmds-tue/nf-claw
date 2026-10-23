from runner import engine_version as ev


def test_required_spec_reads_manifest(tmp_path):
    cfg = tmp_path / "nextflow.config"
    cfg.write_text("manifest {\n    nextflowVersion = '!>=25.04.3'\n}\n")
    assert ev.required_spec(cfg) == "!>=25.04.3"


def test_required_spec_none_when_absent(tmp_path):
    cfg = tmp_path / "nextflow.config"
    cfg.write_text("manifest { name = 'x' }\n")
    assert ev.required_spec(cfg) is None


def test_warning_silent_when_satisfied():
    assert ev.warning("!>=25.04.3", "  version 25.10.5 build 5935\n") is None


def test_warning_silent_when_equal():
    assert ev.warning(">=24.04.0", "version 24.04.0 build 1") is None


def test_warning_when_installed_too_old():
    w = ev.warning("!>=26.04.0", "version 25.10.4 build 5935")
    assert w is not None
    assert "26.04.0" in w and "25.10.4" in w


def test_warning_silent_on_unparseable_spec():
    # operators / ranges we don't model → never contradict Nextflow's own enforcement
    assert ev.warning("==24.04.0", "version 23.10.0 build 1") is None
    assert ev.warning(">=24.04.0 && <25", "version 23.10.0") is None


def test_warning_silent_when_installed_unknown():
    assert ev.warning(">=24.04.0", "no version here") is None
    assert ev.warning(">=24.04.0", None) is None
    assert ev.warning(None, "version 24.04.0") is None


def test_check_silent_without_manifest_constraint(tmp_path):
    (tmp_path / "nextflow.config").write_text("manifest { name = 'x' }\n")
    assert ev.check(tmp_path) == []


def test_check_warns_when_too_old(tmp_path, monkeypatch):
    (tmp_path / "nextflow.config").write_text("manifest { nextflowVersion = '!>=26.04.0' }\n")
    monkeypatch.setattr(ev, "_installed_raw", lambda: "version 25.10.4 build 1")
    out = ev.check(tmp_path)
    assert len(out) == 1 and "26.04.0" in out[0]


def test_check_judges_the_pinned_version_when_given(tmp_path, monkeypatch):
    # With --nxf-ver, the engine that runs is the pin, not the installed launcher: judge that.
    (tmp_path / "nextflow.config").write_text("manifest { nextflowVersion = '!>=26.04.0' }\n")
    # launcher is fine...
    monkeypatch.setattr(ev, "_installed_raw", lambda: "version 26.10.0 build 1")
    out = ev.check(tmp_path, nxf_ver="25.10.2")  # ...but the pin is too old
    assert len(out) == 1 and "26.04.0" in out[0] and "25.10.2" in out[0]


def test_check_silent_when_pinned_version_satisfies(tmp_path, monkeypatch):
    (tmp_path / "nextflow.config").write_text("manifest { nextflowVersion = '!>=25.04.0' }\n")
    # would warn, but the pin is newer
    monkeypatch.setattr(ev, "_installed_raw", lambda: "version 20.0.0 build 1")
    assert ev.check(tmp_path, nxf_ver="25.10.2") == []


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
