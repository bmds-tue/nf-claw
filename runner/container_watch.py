"""Observe images as task containers start, so the run records the images it actually ran.

Every start event queues its container ID. Container inspection determines the immutable
image ID; only then is that image inspected. Tags may move before either queued probe runs.
Immutable image/repository pairs are cached, while distinct containers remain attributable.
Missing container evidence is retained explicitly instead of replaced by a later tag lookup.
"""
from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
from pathlib import Path

from runner import environment_record

ENGINES = environment_record.REGISTRY_ENGINES


def engine_for(profile: str) -> str | None:
    """The registry engine a profile selects by name (`docker`, `podman`), if any."""
    names = [part.strip() for part in profile.split(",")]
    return next((name for name in reversed(names) if name in ENGINES), None)


def _reference(event: dict) -> str | None:
    actor = event.get("Actor") if isinstance(event.get("Actor"), dict) else {}
    attributes = actor.get("Attributes") if isinstance(actor.get("Attributes"), dict) else {}
    for value in (event.get("from"), attributes.get("image"), event.get("Image")):  # docker, podman
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

    def __init__(self, engine: str, work_dir: Path | None = None,
                 env: dict[str, str] | None = None):
        self.engine = engine
        self.work_dir = work_dir
        self.env = env
        self.observed: dict[str, dict[str, dict]] = {}
        self._checked: set[str] = set()
        self._images: dict[tuple[str, str], dict] = {}
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
            if name and not name.startswith("nxf-"):
                continue
            actor = event.get("Actor") if isinstance(event.get("Actor"), dict) else {}
            cid = actor.get("ID") or event.get("id") or event.get("ID")
            cid = cid if isinstance(cid, str) else ""
            key = cid or "missing:" + (reference or "unknown")
            if key not in self._checked:
                self._checked.add(key)
                self._queue.put((cid, reference))
        self._queue.put(None)

    def _inspect(self) -> None:
        while (item := self._queue.get()) is not None:
            cid, reference = item
            try:
                container = environment_record.container_image(self.engine, cid, self.env)
                reference = reference or container.get("reference")
                if not isinstance(reference, str) or not reference:
                    continue
                if container.get("kind") == "unresolved":
                    identity = container
                else:
                    key = (reference, container["id"])
                    identity = self._images.get(key)
                    if identity is None:
                        identity = environment_record.resolve_registry_image(
                            self.engine, reference, self.env, at_start=True,
                            image_id=container["id"])
                        self._images[key] = identity
            except Exception:          # one unreadable image must not end the observation
                identity = {"kind": "unresolved", "reason": "container image inspection failed"}
            if not reference:
                continue
            with self._lock:
                images = self.observed.setdefault(reference, {})
                key = identity.get("id") or "unresolved:" + cid
                entry = images.setdefault(key, {**identity, "container_ids": []})
                if cid and cid not in entry["container_ids"]:
                    entry["container_ids"].append(cid)

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
