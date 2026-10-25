"""Immutable container IDs survive tag changes before asynchronous inspection."""
import io
import json
import subprocess
from types import SimpleNamespace

import pytest

from runner import container_watch, environment_record

ONE, TWO = "sha256:" + "1" * 64, "sha256:" + "2" * 64
TAG = "quay.io/test/tool:latest"


@pytest.mark.parametrize("engine", ["docker", "podman"])
def test_every_start_is_bound_to_its_container_before_resolving_immutable_image(
        engine, monkeypatch):
    events = ([{"Actor": {"ID": cid, "Attributes": {"image": TAG, "name": "nxf-" + cid}}}
               for cid in ("first", "second")] if engine == "docker" else
              [{"ID": cid, "Image": TAG, "Name": "nxf-" + cid}
               for cid in ("first", "second")])
    images = {"first": ONE, "second": TWO}
    calls = []

    def inspect(command, **kw):
        calls.append(command)
        if command[1:3] == ["container", "inspect"]:
            cid = command[3]
            data = {"Id": cid, "Image": images[cid], "Config": {"Image": TAG}}
        elif command[1:3] == ["image", "inspect"]:
            # The tag has already moved before either queued inspection begins.
            image = TWO if command[3] == TAG else command[3]
            data = {"Id": image, "RepoDigests": ["quay.io/test/tool@" + image],
                    "Os": "linux", "Architecture": "amd64"}
        else:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, 0, json.dumps([data]), "")

    monkeypatch.setattr(environment_record, "_run", inspect)
    watch = container_watch.ContainerWatch(engine)
    watch._process = SimpleNamespace(stdout=io.StringIO(
        "".join(json.dumps(e) + "\n" for e in events)), poll=lambda: 0)
    watch._read()
    watch._inspect()
    observed = watch.stop()
    assert {identity["id"] for identity in observed[TAG]} == {ONE, TWO}
    assert {cid for item in observed[TAG] for cid in item["container_ids"]} == {"first", "second"}
    assert [engine, "container", "inspect", "first"] in calls
    assert [engine, "container", "inspect", "second"] in calls
    assert [engine, "image", "inspect", TAG] not in calls
    record = {"container_engine": {"name": engine}, "processes": {
        "P:TOOL": {"containers": [TAG], "without_container": 0}},
        "images": {TAG: {"kind": "multiple", "variants": observed[TAG]}}}
    assert environment_record.pins(record) == {}


def test_removed_container_leaves_explicit_missing_evidence(monkeypatch):
    monkeypatch.setattr(environment_record, "_run", lambda *a, **kw:
        subprocess.CompletedProcess(a[0], 1, "", "No such container"))
    watch = container_watch.ContainerWatch("docker")
    event = {"id": "removed", "from": TAG, "Actor": {"Attributes": {"name": "nxf-removed"}}}
    watch._process = SimpleNamespace(stdout=io.StringIO(json.dumps(event) + "\n"), poll=lambda: 0)
    watch._read()
    watch._inspect()
    identity, = watch.stop()[TAG]
    assert identity["kind"] == "unresolved"
    assert "container" in identity["reason"]
    assert identity["container_ids"] == ["removed"]
