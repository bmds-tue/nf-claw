"""Observe each task container as it starts, so the run records the image it actually ran.

Reading image identities only after a run misses images removed while it ran (an `image prune`
on a shared host, a disk guard) and takes the identity of a tag re-pulled since. While Nextflow
runs, nfclaw follows the container engine's start events; each container whose working directory
lies in the run's work directory is inspected at once, while its image cannot be removed, and the
image ID it runs is resolved to its registry digest (runner.environment_record).

Best effort by design: a container that exits before it is inspected, or an engine without an
events stream, leaves that reference to the inspection after the run.
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


class ContainerWatch:
    """Follow `<engine> events` for container starts in `work_dir`; `stop()` returns what it saw."""

    def __init__(self, engine: str, work_dir: Path, env: dict[str, str] | None = None):
        self.engine = engine
        self.env = env
        roots = {str(work_dir.absolute())}
        try:
            roots.add(str(work_dir.resolve()))
        except OSError:
            pass
        self.roots = tuple(root.rstrip("/") + "/" for root in roots)
        self.observed: dict[str, dict[str, dict]] = {}
        self._images: dict[str, dict] = {}
        self._queue: queue.Queue = queue.Queue()
        self._process: subprocess.Popen | None = None
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    def start(self) -> "ContainerWatch":
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
            actor = event.get("Actor") if isinstance(event.get("Actor"), dict) else {}
            container = event.get("id") or event.get("ID") or actor.get("ID")
            name = (actor.get("Attributes") or {}).get("name") or event.get("Name") or ""
            # Nextflow names task containers `nxf-…`; anything else is another program's.
            if isinstance(container, str) and container and (not name or name.startswith("nxf-")):
                self._queue.put(container)
        self._queue.put(None)

    def _inspect(self) -> None:
        while (container := self._queue.get()) is not None:
            try:
                self._record(container)
            except Exception:          # one unreadable container must not end the observation
                continue

    def _record(self, container: str) -> None:
        result = environment_record._run([self.engine, "container", "inspect", container],
                                         env=self.env, timeout=30)
        if result is None or result.returncode != 0:
            return
        data = json.loads(result.stdout)
        data = data[0] if isinstance(data, list) and data else data
        if not isinstance(data, dict):
            return
        config = data.get("Config") if isinstance(data.get("Config"), dict) else {}
        workdir = config.get("WorkingDir") or ""
        if not any((workdir.rstrip("/") + "/").startswith(root) for root in self.roots):
            return
        reference = data.get("ImageName") or config.get("Image")       # podman, docker
        image_id = data.get("Image")
        if not isinstance(reference, str) or not reference or not isinstance(image_id, str):
            return
        if image_id not in self._images:
            self._images[image_id] = environment_record.resolve_registry_image(
                self.engine, reference, self.env, image=image_id)
        identity = self._images[image_id]
        if identity.get("kind") != "registry":
            return
        with self._lock:
            self.observed.setdefault(reference, {})[identity.get("id") or image_id] = identity

    def stop(self, timeout: float = 30) -> dict[str, list[dict]]:
        """End the observation; containers already queued are still inspected while time allows."""
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
