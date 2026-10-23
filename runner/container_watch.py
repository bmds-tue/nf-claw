"""Observe images as task containers start, so the run records the images it actually ran.

Reading image identities only after a run misses images removed while it ran (an `image prune`
on a shared host, a disk guard) and takes the identity of a tag re-pulled since. While Nextflow
runs, nfclaw follows the container engine's start events. The first time a Nextflow task container
(`nxf-…`) starts from an image reference, the image is inspected at once, while a container uses
it and it cannot be removed, and resolved to its image ID and registry digest
(runner.environment_record). A reference seen again after a while is inspected again, so a tag
re-pulled to other bytes mid-run shows up as two images rather than one.

One inspection per image reference keeps up with any number of containers on a busy host. Other
programs' references that start meanwhile are inspected too and simply never matched against the
run's processes. Best effort by design: a reference the engine cannot inspect, or an engine
without an events stream, is left to the inspection after the run.
"""
from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
import time
from pathlib import Path

from runner import environment_record

ENGINES = environment_record.REGISTRY_ENGINES
# How long a reference's identity stands before a later container start inspects it again.
RECHECK_SECONDS = 600


def engine_for(profile: str) -> str | None:
    """The registry engine a profile selects by name (`docker`, `podman`), if any."""
    names = [part.strip() for part in profile.split(",")]
    return next((name for name in reversed(names) if name in ENGINES), None)


def _reference(event: dict) -> str | None:
    actor = event.get("Actor") if isinstance(event.get("Actor"), dict) else {}
    attributes = actor.get("Attributes") if isinstance(actor.get("Attributes"), dict) else {}
    for value in (event.get("from"), attributes.get("image"), event.get("Image")):   # docker, podman
        if isinstance(value, str) and value and not value.startswith("sha256:"):
            return value
    return None


def _name(event: dict) -> str:
    actor = event.get("Actor") if isinstance(event.get("Actor"), dict) else {}
    attributes = actor.get("Attributes") if isinstance(actor.get("Attributes"), dict) else {}
    name = attributes.get("name") or event.get("Name") or ""
    return name if isinstance(name, str) else ""


class ContainerWatch:
    """Follow `<engine> events` for task container starts; `stop()` returns what it saw.

    `work_dir` is kept for the record; the observation is keyed by image reference and the run's
    own task records (`nextflow log`) select the references that belong to it.
    """

    def __init__(self, engine: str, work_dir: Path | None = None, env: dict[str, str] | None = None):
        self.engine = engine
        self.work_dir = work_dir
        self.env = env
        self.observed: dict[str, dict[str, dict]] = {}
        self._checked: dict[str, float] = {}
        self._queue: queue.Queue = queue.Queue()
        self._process: subprocess.Popen | None = None
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    def start(self) -> ContainerWatch:
        try:
            self._process = subprocess.Popen(
                [self.engine, "events", "--filter", "type=container", "--filter", "event=start",
                 "--format", "{{json .}}"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, errors="replace", env=self.env, start_new_session=True)
        except OSError:
            return self
        for target in (self._read, self._inspect):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)
        return self

    def _read(self) -> None:
        for line in self._process.stdout:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            name = _name(event)
            reference = _reference(event)
            # Nextflow names task containers `nxf-…`; anything else is another program's.
            if reference is None or (name and not name.startswith("nxf-")):
                continue
            now = time.monotonic()
            last = self._checked.get(reference)
            if last is None or now - last >= RECHECK_SECONDS:
                self._checked[reference] = now
                self._queue.put(reference)
        self._queue.put(None)

    def _inspect(self) -> None:
        while (reference := self._queue.get()) is not None:
            try:
                identity = environment_record.resolve_registry_image(
                    self.engine, reference, self.env, at_start=True)
            except Exception:          # one unreadable image must not end the observation
                continue
            if identity.get("kind") != "registry":
                continue
            with self._lock:
                self.observed.setdefault(reference, {})[identity.get("id") or reference] = identity

    def stop(self, timeout: float = 30) -> dict[str, list[dict]]:
        """End the observation; references already queued are still inspected while time allows."""
        if self._process is not None and self._process.poll() is None:
            try:
                os.killpg(self._process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self._process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        for thread in self._threads:
            thread.join(timeout=timeout)
        with self._lock:
            return {reference: list(images.values()) for reference, images in self.observed.items()}
