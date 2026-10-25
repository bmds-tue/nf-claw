"""Opt-in isolated Docker retagging experiment; never prunes shared images or caches.

Set NFCLAW_CONTAINER_LIVE=1 and NFCLAW_LIVE_IMAGE_ONE/TWO to two existing
images containing /bin/sh and sleep. The experiment creates only a unique tag
and two network-isolated, read-only, resource-limited containers, then removes
those exact objects. It performs no image pull.
"""
import json
import os
import subprocess
import threading
import time
import uuid

import pytest

from runner import container_watch

pytestmark = pytest.mark.skipif(os.environ.get("NFCLAW_CONTAINER_LIVE") != "1",
                                reason="requires opt-in isolated live Docker experiment")


def test_live_retag_before_async_inspection_retains_both_actual_images(monkeypatch, tmp_path):
    one, two = os.environ.get("NFCLAW_LIVE_IMAGE_ONE"), os.environ.get("NFCLAW_LIVE_IMAGE_TWO")
    assert one and two, "select two cached images with /bin/sh and sleep"

    def docker(*args):
        return subprocess.check_output(["docker", *args], text=True, timeout=30).strip()

    images = [json.loads(docker("image", "inspect", image))[0]["Id"] for image in (one, two)]
    assert images[0] != images[1], "the experiment requires different image IDs"
    token = uuid.uuid4().hex
    tag = f"nfclaw-identity-{token}:mutable"
    containers = []
    inspect = container_watch.ContainerWatch._inspect
    ready = threading.Event()

    def delayed_inspect(watch):
        ready.wait(timeout=30)
        inspect(watch)

    monkeypatch.setattr(container_watch.ContainerWatch, "_inspect", delayed_inspect)
    watch = container_watch.ContainerWatch("docker").start()
    try:
        time.sleep(1)  # allow Docker to establish the event subscription
        for index, image in enumerate(images):
            docker("tag", image, tag)
            cid = docker("run", "-d", "--name", f"nxf-identity-{token}-{index}",
                "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt",
                "no-new-privileges", "--memory", "64m", "--cpus", "0.1", "--entrypoint",
                "/bin/sh", tag, "-c", "sleep 300")
            containers.append(cid)
            time.sleep(1)
        # The tag already refers to TWO before either queued inspection can start.
        ready.set()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with watch._lock:
                if len(watch.observed.get(tag, {})) == 2:
                    break
            time.sleep(0.1)
        observed = watch.stop()
        assert {item["id"] for item in observed[tag]} == set(images)
        by_container = {cid: item["id"] for item in observed[tag] for cid in item["container_ids"]}
        assert by_container == dict(zip(containers, images, strict=True))
        (tmp_path / "container-identity-evidence.json").write_text(json.dumps(
            {"expected": by_container, "observed": observed[tag]}, indent=2) + "\n")
    finally:
        ready.set()
        watch.stop()
        for cid in containers:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=30)
        subprocess.run(["docker", "image", "rm", tag], capture_output=True, timeout=30)
