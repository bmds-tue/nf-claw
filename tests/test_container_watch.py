"""Task containers are observed as they start, so their images are recorded even if removed later."""
import json
import os
import time

from runner import container_watch
from runner import environment_record as env_record

DIGEST = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "e" * 64

# `events` replays the lines of $FAKE_EVENTS, then stays open like the real stream; `container
# inspect` answers from $FAKE_CONTAINERS/<id>.json; `image inspect` knows one image by its ID.
FAKE_DOCKER = r"""#!/usr/bin/env bash
case "$1 $2" in
"events --filter") cat "$FAKE_EVENTS"; exec sleep 600 ;;
"container inspect") cat "$FAKE_CONTAINERS/$3.json" 2>/dev/null || exit 1 ;;
"image inspect")
  [ "$3" = "$FAKE_IMAGE_ID" ] || { echo "Error: No such image: $3" >&2; exit 1; }
  printf '[{"Id": "%s", "RepoDigests": ["quay.io/biocontainers/fastqc@%s"], "Os": "linux", "Architecture": "amd64"}]\n' "$FAKE_IMAGE_ID" "$FAKE_DIGEST"
  ;;
*) exit 1 ;;
esac
"""


def _fake_docker(tmp_path, monkeypatch, events, containers):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(FAKE_DOCKER)
    (bin_dir / "docker").chmod(0o755)
    (tmp_path / "events").write_text("".join(json.dumps(event) + "\n" for event in events))
    store = tmp_path / "containers"
    store.mkdir()
    for cid, data in containers.items():
        (store / f"{cid}.json").write_text(json.dumps([data]))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_EVENTS", str(tmp_path / "events"))
    monkeypatch.setenv("FAKE_CONTAINERS", str(store))
    monkeypatch.setenv("FAKE_IMAGE_ID", IMAGE_ID)
    monkeypatch.setenv("FAKE_DIGEST", DIGEST)


def _event(cid, name):
    return {"status": "start", "id": cid, "Type": "container", "Action": "start",
            "Actor": {"ID": cid, "Attributes": {"name": name}}}


def test_only_this_runs_task_containers_are_recorded(tmp_path, monkeypatch):
    work = tmp_path / "work"
    reference = "quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0"
    _fake_docker(tmp_path, monkeypatch, [
        _event("mine", "nxf-abc"), _event("other_run", "nxf-def"), _event("not_nextflow", "web"),
        _event("gone", "nxf-ghi"),
    ], {
        "mine": {"Image": IMAGE_ID, "Config": {"Image": reference, "WorkingDir": f"{work}/ab/cdef"}},
        "other_run": {"Image": IMAGE_ID, "Config": {"Image": "quay.io/x:1", "WorkingDir": "/elsewhere/ab/cd"}},
        "not_nextflow": {"Image": IMAGE_ID, "Config": {"Image": "quay.io/y:1", "WorkingDir": f"{work}/x"}},
    })
    watch = container_watch.ContainerWatch("docker", work, dict(os.environ)).start()
    deadline = time.monotonic() + 10
    while not watch.observed and time.monotonic() < deadline:
        time.sleep(0.05)
    observed = watch.stop()
    assert list(observed) == [reference]
    (identity,) = observed[reference]
    assert identity["id"] == IMAGE_ID and identity["digest"] == DIGEST
    assert identity["source"] == "task container at start"


def test_a_missing_engine_observes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    watch = container_watch.ContainerWatch("docker", tmp_path, {"PATH": str(tmp_path)}).start()
    assert watch.stop() == {}


def test_engine_is_taken_from_the_profile():
    assert container_watch.engine_for("test,docker") == "docker"
    assert container_watch.engine_for("podman,test") == "podman"
    assert container_watch.engine_for("test,singularity") is None


def _capture_with(tmp_path, monkeypatch, *, observed=None, previous=None, inspect=None):
    out = tmp_path / "out"
    (out / ".nextflow").mkdir(parents=True)
    (out / ".nextflow" / "history").write_text("2026-10-15 10:00:00\t1s\trun_a\tOK\tabc\tsess\tcmd\n")
    monkeypatch.setattr(env_record, "tasks", lambda *a, **k: [
        {"process": "P:FASTQC", "container": "quay.io/tool:1", "status": "COMPLETED", "workdir": None}])
    monkeypatch.setattr(env_record, "engine_details", lambda engine, env: {"name": engine})
    monkeypatch.setattr(env_record, "resolve_registry_image", inspect or (
        lambda engine, reference, env, image=None: {"kind": "unresolved", "reason": "No such image"}))
    return env_record.capture(out, log_path=out / ".nextflow.log", profile="docker",
                              observed=observed, previous=previous)


def test_an_observed_identity_outlives_the_image(tmp_path, monkeypatch):
    seen = {"kind": "registry", "repository": "quay.io/tool", "id": IMAGE_ID, "digest": DIGEST}
    record = _capture_with(tmp_path, monkeypatch, observed={"quay.io/tool:1": [seen]})
    assert record["images"]["quay.io/tool:1"] == seen
    assert record["pinned_containers"] == {"P:FASTQC": f"quay.io/tool@{DIGEST}"}


def test_a_tag_that_ran_two_images_is_not_pinned(tmp_path, monkeypatch):
    one = {"kind": "registry", "repository": "quay.io/tool", "id": IMAGE_ID, "digest": DIGEST}
    two = {**one, "id": "sha256:" + "f" * 64, "digest": "sha256:" + "b" * 64}
    record = _capture_with(tmp_path, monkeypatch, observed={"quay.io/tool:1": [one, two]})
    assert record["images"]["quay.io/tool:1"]["kind"] == "multiple"
    assert record["pinned_containers"] == {} and record["issues"]


def test_an_earlier_attempt_names_an_image_removed_since(tmp_path, monkeypatch):
    earlier = {"kind": "registry", "repository": "quay.io/tool", "id": IMAGE_ID, "digest": DIGEST}
    record = _capture_with(tmp_path, monkeypatch, previous={"images": {"quay.io/tool:1": earlier}})
    assert record["images"]["quay.io/tool:1"]["digest"] == DIGEST
    assert record["images"]["quay.io/tool:1"]["source"] == "recorded by an earlier attempt of this run"


def test_a_digest_reference_identifies_an_image_the_engine_removed(monkeypatch):
    monkeypatch.setattr(env_record, "_run", lambda *a, **k: None)
    image = env_record.resolve_registry_image("docker", f"quay.io/tool@{DIGEST}", None)
    assert image["kind"] == "registry" and image["digest"] == DIGEST
    assert image["source"] == "reference digest"
