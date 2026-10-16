"""A provenance bundle carries what its replay runs: source, configs and container identities."""
import gzip
import hashlib
import io
import json
import os
import stat
import subprocess
import tarfile

import pytest

from runner import environment_record as env_record
from runner import provenance, replay_guard
from runner.submodule import SubmoduleStatus

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
IMAGE = "quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0"
SESSION = "6d412da1-8678-4af4-be34-db0c996ee184"

# A stand-in for Nextflow: `run` records a session the way the engine does (history, log, one task
# whose wrapper invokes docker) and prints the pipeline's main.nf; `log` lists that task.
FAKE_NEXTFLOW = r"""#!/usr/bin/env bash
set -eu
case "$1" in
run)
  cat "$2/main.nf"
  if [ -n "${FAKE_MUTATE:-}" ]; then echo "// edited while it ran" >> "$FAKE_MUTATE"; fi
  mkdir -p .nextflow work/ab/cdef
  printf '2026-10-15 10:00:00\t1s\tfake_run\tOK\tabc\t%s\tnextflow run\n' "$FAKE_SESSION" >> .nextflow/history
  printf 'docker run -i --rm %s /bin/bash -c "eval $(nxf_main)"\n' "$FAKE_IMAGE" > work/ab/cdef/.command.run
  mkdir -p "work/stage-$FAKE_SESSION/11/22"
  printf 'remote bytes' > "work/stage-$FAKE_SESSION/11/22/reads.fq"
  {
    echo "  Runtime: Groovy 4.0.28 on OpenJDK 64-Bit Server VM 17.0.20"
    echo "Oct-15 10:00:00.000 [main] INFO  org.pf4j.AbstractPluginManager - Start plugin '${FAKE_PLUGIN:-nf-schema@2.5.1}'"
    echo "Oct-15 10:00:01.000 [FileTransfer-1] DEBUG nextflow.file.FilePorter - Copying foreign file https://example.org/reads.fq to work dir: $PWD/work/stage-$FAKE_SESSION/11/22/reads.fq"
  } > .nextflow.log
  ;;
log)
  printf 'NFCORE_DEMO:DEMO:FASTQC\t%s\tCOMPLETED\t%s\n' "$FAKE_IMAGE" "$PWD/work/ab/cdef"
  ;;
esac
"""

# A stand-in for docker: the identity of FAKE_IMAGE is whatever FAKE_DIGEST says.
FAKE_DOCKER = r"""#!/usr/bin/env bash
case "$1 $2" in
"image inspect")
  ref="$3"
  repo="${ref%@*}"; repo="${repo%:*}"
  printf '[{"Id": "%s", "RepoTags": ["%s"], "RepoDigests": ["%s@%s"], "Os": "linux", "Architecture": "amd64", "Size": 42}]\n' \
    "$FAKE_DIGEST" "$FAKE_IMAGE" "$repo" "$FAKE_DIGEST"
  ;;
"version --format") echo "29.1.3" ;;
*) exit 1 ;;
esac
"""


@pytest.fixture(autouse=True)
def _no_engine_probe(monkeypatch):
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "test engine")


@pytest.fixture
def fake_tools(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("nextflow", FAKE_NEXTFLOW), ("docker", FAKE_DOCKER)):
        (bin_dir / name).write_text(text)
        (bin_dir / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_SESSION", SESSION)
    monkeypatch.setenv("FAKE_IMAGE", IMAGE)
    monkeypatch.setenv("FAKE_DIGEST", DIGEST_A)
    return bin_dir


def _git_pipeline(tmp_path, files=None):
    path = tmp_path / "up"
    path.mkdir()
    for name, text in (files or {"main.nf": "original workflow\n"}).items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    for args in (("init", "-q"), ("add", "."),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.com",
                  "commit", "-qm", "original")):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
    commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            check=True, capture_output=True, text=True).stdout.strip()
    return SubmoduleStatus("demo", path, True, True, "1.0.0", commit, ())


def _launch(tmp_path, st, *, configs=(), resume=False):
    """What `nfclaw run` does around the engine: run it from the outdir, then write the bundle."""
    out = tmp_path / "out"
    out.mkdir()
    command = ["nextflow", "run", str(st.path), "-profile", "docker"]
    for config in configs:
        command += ["-c", str(config)]
    if resume:
        command.append("-resume")
    subprocess.run(command, cwd=out, check=True, capture_output=True)
    snapshot, inventory = provenance.snapshot_inputs(list(configs))
    return provenance.write(outdir=out, pipeline="demo", command_str=subprocess.list2cmdline(command),
                            submodule=st, input_paths=[], config_paths=tuple(configs),
                            config_checksums=snapshot, config_inventory=inventory,
                            pipeline_checksums=provenance.hash_pipeline(st.path), history_offset=0)


def _replay(prov, target, **env):
    return subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, text=True,
                          env={**os.environ, **env})


# -- the pipeline source archive ---------------------------------------------------------------

def test_archive_holds_exactly_the_recorded_source_deterministically(tmp_path):
    st = _git_pipeline(tmp_path, {"main.nf": "workflow\n", "bin/tool.py": "print(1)\n"})
    (st.path / "bin" / "tool.py").chmod(0o755)
    (st.path / "untracked.txt").write_text("not part of the pipeline\n")
    checksums = provenance.hash_pipeline(st.path)
    first = replay_guard.write_pipeline_archive(st.path, checksums, tmp_path / "a.tar.gz")
    second = replay_guard.write_pipeline_archive(st.path, checksums, tmp_path / "b.tar.gz")
    assert first == second == hashlib.sha256((tmp_path / "a.tar.gz").read_bytes()).hexdigest()
    with tarfile.open(tmp_path / "a.tar.gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
    assert sorted(members) == ["bin/tool.py", "main.nf"]
    assert members["bin/tool.py"].mode == 0o755 and members["main.nf"].mode == 0o644
    assert {m.mtime for m in members.values()} == {0}


def test_archive_refuses_source_that_changed_since_launch(tmp_path):
    st = _git_pipeline(tmp_path)
    checksums = provenance.hash_pipeline(st.path)
    (st.path / "main.nf").write_text("edited after launch\n")
    with pytest.raises(ValueError, match="changed since launch"):
        replay_guard.write_pipeline_archive(st.path, checksums, tmp_path / "a.tar.gz")
    assert not (tmp_path / "a.tar.gz").exists() and not list(tmp_path.glob(".a.tar.gz.*"))


def test_bundle_records_its_source_archive(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    archive = manifest["pipeline_archive"]
    assert archive["file"] == "pipeline-source.tar.gz" and archive["files"] == 1
    assert archive["sha256"] == hashlib.sha256((prov / archive["file"]).read_bytes()).hexdigest()


@pytest.mark.parametrize("change", ["tracked_bytes", "head", "deleted"])
def test_replay_runs_the_archived_source_whatever_happens_to_the_checkout(tmp_path, fake_tools, change):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    if change == "tracked_bytes":
        (st.path / "main.nf").write_text("different scientific algorithm\n")
    elif change == "head":
        subprocess.run(["git", "-C", str(st.path), "-c", "user.name=Test", "-c",
                        "user.email=test@example.com", "commit", "--allow-empty", "-qm", "new"],
                       check=True)
    else:
        subprocess.run(["rm", "-rf", str(st.path)], check=True)
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode == 0, result.stderr
    assert "original workflow" in result.stdout and "different" not in result.stdout
    restored = tmp_path / "fresh" / "provenance" / "pipeline" / "main.nf"
    assert restored.read_text() == "original workflow\n"
    source = json.loads((tmp_path / "fresh" / "provenance" / "pipeline-source.json").read_text())
    assert source["from"] == "archive" and source["path"] == str(restored.parent)
    assert "bundle's pipeline source archive" in result.stdout
    if change == "deleted":
        assert "pipeline checkout is missing" in source["reason"]


def test_replay_runs_the_recorded_checkout_while_it_is_intact(tmp_path, fake_tools):
    # Paths that embed the pipeline directory (nf-core's `${projectDir}/assets/...` defaults) then
    # keep the values the original run had.
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode == 0, result.stderr
    source = json.loads((tmp_path / "fresh" / "provenance" / "pipeline-source.json").read_text())
    assert source == {"from": "checkout", "path": str(st.path)}
    assert not (tmp_path / "fresh" / "provenance" / "pipeline").exists()
    assert "running the recorded pipeline checkout" in result.stdout


def test_a_checkout_edited_while_the_replay_ran_fails_it(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    result = _replay(prov, tmp_path / "fresh", FAKE_MUTATE=str(st.path / "main.nf"))
    assert result.returncode == 1
    log = (tmp_path / "fresh" / "provenance" / "logs" / "run.log").read_text()
    assert log.rstrip().endswith("failed after Nextflow succeeded (local dependencies changed)")
    assert "pipeline source content changed" in log


@pytest.mark.parametrize("tamper", ["archive_bytes", "member_bytes"])
def test_replay_refuses_an_altered_source_archive(tmp_path, fake_tools, tamper):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    archive = prov / "pipeline-source.tar.gz"
    if tamper == "archive_bytes":
        archive.write_bytes(archive.read_bytes() + b"\0")
    else:
        # A well-formed archive whose member differs from pipeline.sha256, with a matching manifest
        # digest: the per-file check, not only the archive digest, must refuse it.
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz, \
                tarfile.open(fileobj=gz, mode="w") as tar:
            data = b"another algorithm\n"
            info = tarfile.TarInfo("main.nf")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        archive.write_bytes(buffer.getvalue())
        manifest = json.loads((prov / "run_manifest.json").read_text())
        manifest["pipeline_archive"]["sha256"] = hashlib.sha256(buffer.getvalue()).hexdigest()
        (prov / "run_manifest.json").write_text(json.dumps(manifest))
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode != 0 and "original workflow" not in result.stdout
    assert "pipeline" in result.stderr.lower()


def test_extraction_refuses_an_existing_destination(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    (tmp_path / "dest").mkdir()
    with pytest.raises(FileExistsError):
        replay_guard.check_pipeline_archive(prov, manifest, tmp_path / "dest")


# -- external configs --------------------------------------------------------------------------

def test_replay_uses_the_bundled_copy_of_an_external_config(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    config = tmp_path / "site.config"
    config.write_text("params.threshold = 0.01\n")
    prov = _launch(tmp_path, st, configs=[config])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    entry = manifest["bundled_configs"][str(config)]
    assert entry == {"file": "configs/01-site.config", "replay": True,
                     "sha256": hashlib.sha256(b"params.threshold = 0.01\n").hexdigest()}
    assert (prov / entry["file"]).read_text() == "params.threshold = 0.01\n"
    script = (prov / "commands.sh").read_text()
    assert '-c "$_script_dir"/configs/01-site.config' in script and str(config) not in script
    config.unlink()                                  # the replay no longer needs the original
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode == 0, result.stderr


def test_a_bundled_config_copy_is_guarded(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    config = tmp_path / "site.config"
    config.write_text("params.threshold = 0.01\n")
    prov = _launch(tmp_path, st, configs=[config])
    (prov / "configs" / "01-site.config").write_text("params.threshold = 0.99\n")
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode != 0 and "original workflow" not in result.stdout
    assert "configs content changed" in result.stderr


def test_a_config_that_includes_others_replays_from_its_original_place(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    (tmp_path / "base.config").write_text("process.cpus = 2\n")
    config = tmp_path / "site.config"
    config.write_text("includeConfig 'base.config'\n")
    prov = _launch(tmp_path, st, configs=[config])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["bundled_configs"][str(config)]["replay"] is False
    assert f"-c {config}" in (prov / "commands.sh").read_text()
    config.write_text("includeConfig 'other.config'\n")
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode != 0 and "configs content changed" in result.stderr


# -- the execution environment -----------------------------------------------------------------

def test_bundle_records_container_identities_plugins_and_remote_inputs(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    environment = json.loads((prov / "environment.json").read_text())
    assert environment["run"] == {"name": "fake_run", "session_id": SESSION}
    assert environment["container_engine"] == {"name": "docker", "version": "29.1.3"}
    assert environment["processes"] == {"NFCORE_DEMO:DEMO:FASTQC": {
        "containers": [IMAGE], "tasks": 1, "without_container": 0}}
    image = environment["images"][IMAGE]
    assert image["kind"] == "registry" and image["digest"] == DIGEST_A
    assert image["repository"] == "quay.io/biocontainers/fastqc" and image["platform"] == "linux/amd64"
    assert environment["pinned_containers"] == {
        "NFCORE_DEMO:DEMO:FASTQC": f"quay.io/biocontainers/fastqc@{DIGEST_A}"}
    assert environment["nextflow_plugins"] == ["nf-schema@2.5.1"]
    assert environment["nextflow_runtime"].startswith("Groovy 4.0.28")
    assert environment["remote_inputs"] == {"https://example.org/reads.fq": {
        "sha256": hashlib.sha256(b"remote bytes").hexdigest(), "size": 12}}
    assert environment["issues"] == []
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["environment_record"]["sha256"] == hashlib.sha256(
        (prov / "environment.json").read_bytes()).hexdigest()
    assert manifest["execution_environment"]["pinned_processes"] == 1


def test_replay_pins_each_process_to_the_recorded_digest(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    pins = (prov / "containers.config").read_text()
    assert ("withName: 'NFCORE_DEMO:DEMO:FASTQC' {\n"
            f"        container = 'quay.io/biocontainers/fastqc@{DIGEST_A}'") in pins
    script = (prov / "commands.sh").read_text()
    assert '-c "$_script_dir"/containers.config --outdir "$target"' in script


def test_a_faithful_replay_records_and_matches_its_environment(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode == 0, result.stderr
    assert "execution environment identical" in result.stderr
    check = json.loads((tmp_path / "fresh" / "provenance" / "environment_check.json").read_text())
    assert check["status"] == "identical" and check["mismatches"] == []
    log = (tmp_path / "fresh" / "provenance" / "logs" / "run.log").read_text()
    assert log.rstrip().endswith(": success")


@pytest.mark.parametrize("drift,expected", [
    ({"FAKE_DIGEST": DIGEST_B}, "another image than the recorded"),
    ({"FAKE_PLUGIN": "nf-schema@2.6.0"}, "Nextflow plugins differ"),
])
def test_a_replay_in_another_environment_fails_after_nextflow(tmp_path, fake_tools, drift, expected):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    result = _replay(prov, tmp_path / "fresh", **drift)
    assert result.returncode == 1
    assert expected in result.stderr
    log = (tmp_path / "fresh" / "provenance" / "logs" / "run.log").read_text()
    assert log.rstrip().endswith("failed after Nextflow succeeded (execution environment differs "
                                 "from the recording)")


def test_a_changed_remote_input_fails_the_replay(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    environment = json.loads((prov / "environment.json").read_text())
    environment["remote_inputs"]["https://example.org/reads.fq"]["sha256"] = "0" * 64
    (prov / "environment.json").write_text(json.dumps(environment))
    manifest = json.loads((prov / "run_manifest.json").read_text())
    manifest["environment_record"]["sha256"] = hashlib.sha256(
        (prov / "environment.json").read_bytes()).hexdigest()
    (prov / "run_manifest.json").write_text(json.dumps(manifest))
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode == 1 and "remote input https://example.org/reads.fq changed" in result.stderr


@pytest.mark.parametrize("name", ["environment.json", "containers.config"])
def test_replay_refuses_an_edited_environment_record(tmp_path, fake_tools, name):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    (prov / name).write_text((prov / name).read_text() + "\n")
    result = _replay(prov, tmp_path / "fresh")
    assert result.returncode != 0 and "original workflow" not in result.stdout
    assert f"recorded bundle file changed: {name}" in result.stderr


def test_a_resumed_launch_records_its_own_session(tmp_path, fake_tools):
    out = tmp_path / "out"
    (out / ".nextflow").mkdir(parents=True)
    (out / ".nextflow" / "history").write_text(
        "2026-10-14 10:00:00\t1s\tearlier_run\tERR\tabc\tother-session\tnextflow run\n")
    st = _git_pipeline(tmp_path)
    subprocess.run(["nextflow", "run", str(st.path)], cwd=out, check=True, capture_output=True)
    prov = provenance.write(outdir=out, pipeline="demo", command_str=f"nextflow run {st.path}",
                            submodule=st, input_paths=[], history_offset=1)
    assert json.loads((prov / "environment.json").read_text())["run"]["name"] == "fake_run"


def test_a_launch_that_never_started_a_session_records_that(tmp_path, fake_tools):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="demo", command_str="nextflow run x",
                            submodule=SubmoduleStatus("demo", tmp_path / "up", True, True, "1", "x", ()),
                            input_paths=[], history_offset=0)
    environment = json.loads((prov / "environment.json").read_text())
    assert environment["run"] is None and "no task ran" in environment["issues"][0]
    assert not (prov / "containers.config").exists()


# -- recorder units ----------------------------------------------------------------------------

@pytest.mark.parametrize("reference,expected", [
    ("quay.io/biocontainers/fastqc:0.12.1", ("quay.io/biocontainers/fastqc", "0.12.1", None)),
    ("localhost:5000/tool:1", ("localhost:5000/tool", "1", None)),
    (f"ubuntu@{DIGEST_A}", ("ubuntu", None, DIGEST_A)),
    ("registry:5000/a/b", ("registry:5000/a/b", None, None)),
])
def test_split_reference(reference, expected):
    assert env_record.split_reference(reference) == expected


@pytest.mark.parametrize("repository,expected", [
    ("ubuntu", "docker.io/library/ubuntu"),
    ("immcantation/airrflow", "docker.io/immcantation/airrflow"),
    ("index.docker.io/nfcore/sarek", "docker.io/nfcore/sarek"),
    ("docker.io/ubuntu", "docker.io/library/ubuntu"),
    ("docker.io/library/ubuntu", "docker.io/library/ubuntu"),
    ("registry-1.docker.io/ubuntu", "docker.io/library/ubuntu"),
    ("quay.io/biocontainers/fastqc", "quay.io/biocontainers/fastqc"),
    ("localhost/tool", "localhost/tool"),
])
def test_normalize_repository(repository, expected):
    assert env_record.normalize_repository(repository) == expected


def _record(images, processes, engine="docker"):
    return {"container_engine": {"name": engine}, "images": images, "processes": processes}


def test_pins_skip_what_a_digest_cannot_name():
    images = {
        "quay.io/a:1": {"kind": "registry", "repository": "quay.io/a", "digest": DIGEST_A},
        "quay.io/b:1": {"kind": "registry", "repository": "quay.io/b"},                    # no digest
        "wave.seqera.io/wt/tok/c:1": {"kind": "registry", "repository": "wave.seqera.io/wt/tok/c",
                                      "digest": DIGEST_A},                                    # ephemeral
    }
    processes = {
        "P:ONE": {"containers": ["quay.io/a:1"], "without_container": 0},
        "P:TWO": {"containers": ["quay.io/b:1"], "without_container": 0},
        "P:THREE": {"containers": ["quay.io/a:1", "quay.io/b:1"], "without_container": 0},
        "P:FOUR": {"containers": ["wave.seqera.io/wt/tok/c:1"], "without_container": 0},
        "P:FIVE": {"containers": ["quay.io/a:1"], "without_container": 1},
    }
    assert env_record.pins(_record(images, processes)) == {"P:ONE": f"quay.io/a@{DIGEST_A}"}
    assert env_record.pins(_record(images, processes, engine="singularity")) == {}


def test_registry_identity_uses_the_digest_of_its_own_repository(tmp_path, monkeypatch):
    inspect = [{"Id": "sha256:" + "c" * 64, "Os": "linux", "Architecture": "arm64", "Variant": "v8",
                "RepoDigests": [f"mirror.example.org/tool@{DIGEST_B}", f"quay.io/tool@{DIGEST_A}"]}]
    monkeypatch.setattr(env_record, "_run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, json.dumps(inspect), ""))
    image = env_record.resolve_registry_image("docker", "quay.io/tool:1", None)
    assert image["digest"] == DIGEST_A and image["platform"] == "linux/arm64/v8"
    assert image["repo_digests"] == [f"mirror.example.org/tool@{DIGEST_B}", f"quay.io/tool@{DIGEST_A}"]
    podman = [{"Id": "d" * 64, "RepoDigests": []}]
    monkeypatch.setattr(env_record, "_run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, json.dumps(podman), ""))
    image = env_record.resolve_registry_image("podman", "quay.io/tool:1", None)
    assert image["id"] == "sha256:" + "d" * 64 and "digest" not in image


def test_an_image_the_engine_no_longer_has_is_recorded_as_unresolved(monkeypatch):
    monkeypatch.setattr(env_record, "_run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 1, "", "Error response from daemon: No such image: quay.io/tool:1\n"))
    image = env_record.resolve_registry_image("docker", "quay.io/tool:1", None)
    assert image == {"kind": "unresolved",
                     "reason": "`docker image inspect` failed: Error response from daemon: "
                               "No such image: quay.io/tool:1"}


def test_file_images_are_hashed(tmp_path):
    image = tmp_path / "tool.img"
    image.write_bytes(b"squashfs")
    assert env_record.resolve_file_image(str(image)) == {
        "kind": "file", "path": str(image), "sha256": hashlib.sha256(b"squashfs").hexdigest(), "size": 8}
    assert env_record.resolve_file_image(str(tmp_path / "gone.img"))["kind"] == "unresolved"


def test_engine_is_read_from_the_task_wrapper(tmp_path):
    work = tmp_path / "w"
    work.mkdir()
    (work / ".command.run").write_text("singularity exec -B /x /cache/tool.img /bin/bash -c ...\n")
    tasks = [{"container": "/cache/tool.img", "workdir": str(work)}]
    assert env_record.engine_of(tasks, "docker") == "singularity"
    assert env_record.engine_of([{"container": "x", "workdir": None}], "test,podman") == "podman"
    assert env_record.engine_of([], "test") is None


def test_log_facts_follow_the_session_across_rotated_logs(tmp_path):
    session_line = f"x [main] DEBUG nextflow.Session - Session UUID: {SESSION}\n"
    log = tmp_path / ".nextflow.log"
    log.write_text(
        session_line +
        "  Runtime: Groovy 4.0.28 on OpenJDK 17\n"
        "  Version: 25.10.4 build 11173\n"
        "x DEBUG nextflow.plugin.BasePlugin - Plugin started nf-schema@2.5.1\n"
        "x INFO  org.pf4j.AbstractPluginManager - Start plugin 'nf-schema@2.5.1'\n"
        f"x DEBUG FilePorter - Local cache found for foreign file https://e.org/a.fq at /w/stage-{SESSION}/1/a.fq\n")
    # An earlier attempt of the same (resumed) session, staged in the pre-23 shared layout.
    (tmp_path / ".nextflow.log.1").write_text(
        session_line +
        "x DEBUG FilePorter - Copying foreign file https://e.org/b.fq to work dir: /w/stage/2a/b3/b.fq\n"
        "x INFO  org.pf4j.AbstractPluginManager - Start plugin 'nf-old@1.0.0'\n")
    # Another session's log is not this run's.
    (tmp_path / ".nextflow.log.2").write_text(
        "x [main] DEBUG nextflow.Session - Session UUID: 00000000-0000-0000-0000-000000000000\n"
        "x DEBUG FilePorter - Copying foreign file https://e.org/c.fq to work dir: /w/stage/3/c.fq\n")
    facts = env_record.log_facts(log, SESSION)
    assert facts["runtime"] == "Groovy 4.0.28 on OpenJDK 17" and facts["build"] == "25.10.4 build 11173"
    assert facts["plugins"] == ["nf-schema@2.5.1"]
    assert facts["staged"] == {"https://e.org/a.fq": f"/w/stage-{SESSION}/1/a.fq",
                               "https://e.org/b.fq": "/w/stage/2a/b3/b.fq"}


def test_log_facts_of_a_log_that_names_no_session_use_only_the_current_log(tmp_path):
    (tmp_path / ".nextflow.log").write_text(
        "x DEBUG FilePorter - Copying foreign file https://e.org/a.fq to work dir: /w/stage/1/a.fq\n")
    (tmp_path / ".nextflow.log.1").write_text(
        "x DEBUG FilePorter - Copying foreign file https://e.org/b.fq to work dir: /w/stage/2/b.fq\n")
    assert env_record.log_facts(tmp_path / ".nextflow.log", SESSION)["staged"] == {
        "https://e.org/a.fq": "/w/stage/1/a.fq"}


def test_remote_directories_are_recorded_by_tree_digest(tmp_path):
    staged = tmp_path / "db"
    (staged / "sub").mkdir(parents=True)
    (staged / "sub" / "x").write_text("1")
    record = env_record.remote_inputs({"s3://bucket/db/": str(staged), "s3://b/f": "s3://b/f"})
    assert record["s3://bucket/db/"]["type"] == "directory" and record["s3://bucket/db/"]["files"] == 1
    assert "unresolved" in record["s3://b/f"]


def test_compare_separates_mismatches_from_undecidable_entries():
    registry = {"kind": "registry", "repository": "quay.io/a", "digest": DIGEST_A}
    original = {"nextflow_plugins": ["nf-schema@2.5.1"], "container_engine": {"name": "docker"},
                "images": {"quay.io/a:1": registry, "/c/x.img": {"kind": "file", "path": "/c/x.img",
                                                                  "sha256": "1" * 64}},
                "processes": {"A": {"containers": ["quay.io/a:1"]}, "B": {"containers": ["/c/x.img"]},
                              "C": {"containers": ["quay.io/a:1"]}},
                "remote_inputs": {"https://e.org/a": {"sha256": "2" * 64}}}
    same = json.loads(json.dumps(original))
    assert env_record.compare(original, same)["status"] == "identical"
    replay = json.loads(json.dumps(original))
    replay["images"] = {f"quay.io/a@{DIGEST_A}": registry,
                        "/elsewhere/x.img": {"kind": "file", "path": "/elsewhere/x.img",
                                             "sha256": "3" * 64}}
    replay["processes"] = {"A": {"containers": [f"quay.io/a@{DIGEST_A}"]},
                           "B": {"containers": ["/elsewhere/x.img"]}}
    result = env_record.compare(original, replay)
    assert result["status"] == "unverified" and result["mismatches"] == []
    assert any(line.startswith("B:") for line in result["unverified"])
    assert any("only in the recording: C" in line for line in result["notes"])
    replay["remote_inputs"] = {"https://e.org/a": {"sha256": "4" * 64}}
    assert env_record.compare(original, replay)["status"] == "differs"


def test_pin_config_is_valid_nextflow_syntax_for_each_process():
    text = env_record.pin_config({"pinned_containers": {
        "NFCORE_X:Y:FASTQC": f"quay.io/biocontainers/fastqc@{DIGEST_A}"}})
    assert text.count("withName:") == 1 and text.rstrip().endswith("}")
    assert "process {\n    withName: 'NFCORE_X:Y:FASTQC' {\n" in text
    assert env_record.pin_config({"pinned_containers": {}}) is None


def test_bundled_scripts_need_only_the_standard_library():
    for module in (env_record, replay_guard):
        source = open(module.__file__, encoding="utf-8").read()
        assert "from runner" not in source and "import runner" not in source


def test_commands_sh_stays_executable_and_extracts_before_launch(tmp_path, fake_tools):
    st = _git_pipeline(tmp_path)
    prov = _launch(tmp_path, st)
    assert (prov / "commands.sh").stat().st_mode & stat.S_IXUSR
    script = (prov / "commands.sh").read_text()
    assert script.index("--pipeline-source") < script.index('nextflow run "$pipeline"')


def test_missing_task_records_on_either_side_are_not_called_identical():
    recorded = {"processes": {"A": {"containers": ["quay.io/a:1"]}},
                "images": {"quay.io/a:1": {"kind": "registry", "digest": DIGEST_A}}}
    unread = {"processes": {}, "images": {}, "issues": ["task records could not be read: boom"]}
    for original, replay in ((recorded, unread), (unread, recorded)):
        result = env_record.compare(original, replay)
        assert result["status"] == "unverified"
        assert "no task records" in result["unverified"][0]


def test_a_remote_input_staged_by_only_one_run_is_a_mismatch():
    original = {"remote_inputs": {"https://e.org/a": {"sha256": "1" * 64}}}
    replay = {"remote_inputs": {"https://e.org/a": {"sha256": "1" * 64},
                                "https://e.org/new_sample.fq": {"sha256": "2" * 64}}}
    result = env_record.compare(original, replay)
    assert result["status"] == "differs"
    assert result["mismatches"] == ["remote inputs staged only in the replay: https://e.org/new_sample.fq"]


def test_bundled_scripts_match_the_code_that_wrote_commands_sh(tmp_path, fake_tools, monkeypatch):
    # nfclaw upgraded on disk while a run is in progress: the bundle keeps the scripts its own
    # commands.sh calls, not whatever the files on disk hold by the time the run ends.
    st = _git_pipeline(tmp_path)
    loaded = dict(provenance._BUNDLED_SCRIPTS)
    original_read = provenance.Path.read_bytes

    def upgraded(path):
        if path.name in loaded and path.parent.name == "runner":
            return b"# a different nfclaw release\n"
        return original_read(path)
    monkeypatch.setattr(provenance.Path, "read_bytes", upgraded)
    prov = _launch(tmp_path, st)
    for name, script in loaded.items():
        assert original_read(prov / name) == script


def test_an_official_docker_hub_image_named_with_its_registry_gets_its_digest(monkeypatch):
    inspect = [{"Id": DIGEST_A, "RepoDigests": [f"docker.io/library/ubuntu@{DIGEST_A}"]}]
    monkeypatch.setattr(env_record, "_run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, json.dumps(inspect), ""))
    image = env_record.resolve_registry_image("docker", "docker.io/ubuntu:20.04", None)
    assert image["repository"] == "docker.io/library/ubuntu" and image["digest"] == DIGEST_A
    record = {"container_engine": {"name": "docker"}, "images": {"docker.io/ubuntu:20.04": image},
              "processes": {"P:CAT": {"containers": ["docker.io/ubuntu:20.04"], "without_container": 0}}}
    assert env_record.pins(record) == {"P:CAT": f"docker.io/library/ubuntu@{DIGEST_A}"}


def test_a_spent_deadline_leaves_the_gap_recorded_instead_of_probing(tmp_path, fake_tools):
    import time

    out = tmp_path / "out"
    out.mkdir()
    st = _git_pipeline(tmp_path)
    subprocess.run(["nextflow", "run", str(st.path)], cwd=out, check=True, capture_output=True)
    record = env_record.capture(out, log_path=out / ".nextflow.log", profile="docker",
                                deadline=time.monotonic() - 1)
    assert record["run"]["name"] == "fake_run" and record["processes"] == {}
    assert any("deadline ended the recording" in issue for issue in record["issues"])
    assert env_record._deadline is None                 # never leaks into a later capture


@pytest.fixture
def served(tmp_path):
    """A local HTTP server for files under tmp_path/www; yields its base URL."""
    import functools
    import http.server
    import threading

    root = tmp_path / "www"
    root.mkdir()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield root, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_a_samplesheet_the_pipeline_validated_itself_is_recorded(tmp_path, fake_tools, served):
    root, base = served
    (root / "samplesheet.csv").write_text("sample,fastq_1\nA,https://example.org/reads.fq\n")
    out = tmp_path / "out"
    out.mkdir()
    st = _git_pipeline(tmp_path)
    subprocess.run(["nextflow", "run", str(st.path)], cwd=out, check=True, capture_output=True)
    with (out / ".nextflow.log").open("a") as log:
        log.write(f"x DEBUG n.v.v.evaluators.SchemaEvaluator - Validation of file "
                  f"'{base}/samplesheet.csv' passed!\n")
    record = env_record.capture(out, log_path=out / ".nextflow.log", profile="docker")
    entry = record["remote_inputs"][f"{base}/samplesheet.csv"]
    assert entry["sha256"] == hashlib.sha256((root / "samplesheet.csv").read_bytes()).hexdigest()
    assert "not staged" in entry["read_by"]
    assert "https://example.org/reads.fq" in record["remote_inputs"]          # the staged file too


def test_a_validated_file_that_cannot_be_read_again_is_unresolved(served, monkeypatch):
    root, base = served
    assert "unresolved" in env_record.fetch_digest(f"{base}/missing.csv")
    (root / "big.csv").write_bytes(b"x" * 2048)
    monkeypatch.setattr(env_record, "FETCH_LIMIT", 1024)
    assert "larger than" in env_record.fetch_digest(f"{base}/big.csv")["unresolved"]


def test_log_facts_list_the_files_validation_read():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / ".nextflow.log"
        log.write_text("x Validation of file 'https://e.org/sheet.csv' passed!\n"
                       "x Validation of file 'https://e.org/sheet.csv' passed!\n"
                       "x Validation of file '/local/sheet.csv' passed!\n")
        assert env_record.log_facts(log, None)["validated"] == ["https://e.org/sheet.csv"]
