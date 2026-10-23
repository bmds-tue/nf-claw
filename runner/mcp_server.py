"""A Model Context Protocol server on stdin/stdout, built on the standard library alone.

This module is the protocol: JSON-RPC 2.0 framing (one message per line), version negotiation,
dispatch, cancellation and progress. It knows nothing about nfclaw — the tools, resources and prompt
come from a handler object (`runner.mcp_tools.NfclawTools`), so the protocol is tested on its own
and the nfclaw side never deals with JSON-RPC.

The server is *dual-era*, as the 2026-07-28 revision of MCP describes:
- **modern** clients (2026-07-28) send their protocol version in every request's `_meta`;
there is no
  handshake, `server/discover` describes the server, and each request is served on its own;
- **legacy** clients (2024-11-05 … 2025-11-25) open with `initialize` and are served
under the version
  that handshake negotiated — which is what most clients in use speak.
Requests are answered concurrently, so a tool waiting on a long job never blocks another request,
and the server keeps its stdout to itself: see `serve_stdio`.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

# Newest first. Modern versions are declared per request; legacy ones are negotiated
# by `initialize`.
MODERN_VERSIONS = ("2026-07-28",)
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PROTOCOL_VERSIONS = MODERN_VERSIONS + LEGACY_VERSIONS
LATEST = PROTOCOL_VERSIONS[0]
LATEST_LEGACY = LEGACY_VERSIONS[0]

_META_VERSION = "io.modelcontextprotocol/protocolVersion"
_META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
RESOURCE_NOT_FOUND = -32002              # legacy code; modern servers report -32602
UNSUPPORTED_PROTOCOL_VERSION = -32022

# Modern results that clients may cache: how long they stay fresh, and whether they hold anything
# private. The tool, prompt and template lists are fixed for the life of the process; resources are
# files of the local checkout.
_CACHE_HINTS = {
    "server/discover": (3_600_000, "public"),
    "tools/list": (3_600_000, "public"),
    "prompts/list": (3_600_000, "public"),
    "resources/templates/list": (3_600_000, "public"),
    "resources/list": (300_000, "private"),
    "resources/read": (60_000, "private"),
}


class RpcError(Exception):
    """A request the server rejects at the protocol level (unknown tool, bad parameters)."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def at_least(version: str, minimum: str) -> bool:
    """Whether protocol `version` includes what `minimum` introduced."""
    if version not in PROTOCOL_VERSIONS or minimum not in PROTOCOL_VERSIONS:
        return False
    return PROTOCOL_VERSIONS.index(version) <= PROTOCOL_VERSIONS.index(minimum)


@dataclass
class Context:
    """What a handler may use while serving one request."""

    protocol_version: str = LATEST_LEGACY
    # Set when the client cancels this request, or the server is shutting down: stop waiting.
    cancelled: threading.Event = field(default_factory=threading.Event)
    # Only a client's cancellation withdraws the response; at shutdown it is still sent.
    withdrawn: bool = False
    _notify: Callable[[str, dict], None] | None = None
    _progress_token: Any = None
    _last_progress: float = -1.0

    def progress(self, progress: float, total: float | None = None,
                 message: str | None = None) -> None:
        """Report progress, if the client asked for it (sent a progress token). Never decreases."""
        if self._progress_token is None or self._notify is None or progress <= self._last_progress:
            return
        self._last_progress = progress
        params: dict = {"progressToken": self._progress_token, "progress": progress}
        if total is not None:
            params["total"] = total
        if message and at_least(self.protocol_version, "2025-03-26"):
            params["message"] = message
        self._notify("notifications/progress", params)


class Handler(Protocol):
    """What the server serves. Tool results are MCP `CallToolResult` dicts (see `tool_result`)."""

    def list_tools(self, ctx: Context) -> list[dict]: ...
    def call_tool(self, name: str, arguments: dict, ctx: Context) -> dict: ...
    def list_resources(self, ctx: Context) -> list[dict]: ...
    def list_resource_templates(self, ctx: Context) -> list[dict]: ...
    def read_resource(self, uri: str, ctx: Context) -> list[dict]: ...
    def list_prompts(self, ctx: Context) -> list[dict]: ...
    def get_prompt(self, name: str, arguments: dict, ctx: Context) -> dict: ...


def tool_result(text: str, structured: dict | None = None, *, error: bool = False) -> dict:
    """A `CallToolResult`: the text the model reads, the same facts as structured data, and whether
    the call failed (a failed call is still a result, so the model can read why and correct it)."""
    result: dict = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        result["structuredContent"] = structured
    if error:
        result["isError"] = True
    return result


def _shape_tool(tool: dict, version: str) -> dict:
    """Drop the fields a client on an older protocol version does not know."""
    tool = dict(tool)
    if not at_least(version, "2025-06-18"):
        tool.pop("title", None)
        tool.pop("outputSchema", None)
    if not at_least(version, "2025-03-26"):
        tool.pop("annotations", None)
    return tool


def _shape_result(result: dict, version: str) -> dict:
    if not at_least(version, "2025-06-18") and "structuredContent" in result:
        result = {k: v for k, v in result.items() if k != "structuredContent"}
    return result


def _requested_version(params: Any) -> str | None:
    meta = params.get("_meta") if isinstance(params, dict) else None
    version = meta.get(_META_VERSION) if isinstance(meta, dict) else None
    return version if isinstance(version, str) else None


class Server:
    def __init__(self, handler: Handler, *, name: str, version: str, instructions: str = "",
                 title: str | None = None, max_workers: int = 8):
        self.handler = handler
        self.info = {"name": name, "version": version}
        self.title = title
        self.instructions = instructions
        self.protocol_version = LATEST_LEGACY         # legacy clients: set by `initialize`
        self._out = None
        self._write_lock = threading.Lock()
        self._inflight: dict[Any, Context] = {}
        self._inflight_lock = threading.Lock()
        self._closing = threading.Event()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="mcp")

    # --- transport ------------------------------------------------------------------------------

    def run(self, inp, out) -> int:
        """Serve until the client closes stdin. `inp`/`out` are binary streams."""
        self._out = out
        try:
            for raw in iter(inp.readline, b""):
                line = raw.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except ValueError as exc:
                    self._send(_error(None, PARSE_ERROR, f"parse error: {exc}"))
                    continue
                self._receive(message)
        except (KeyboardInterrupt, BrokenPipeError):
            pass
        finally:
            # The client closed the stream: answer what it already asked, but end every wait now.
            self._closing.set()
            with self._inflight_lock:
                for ctx in self._inflight.values():
                    ctx.cancelled.set()
            self._pool.shutdown(wait=True)
        return 0

    def _send(self, message: dict | list) -> None:
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with self._write_lock:
            try:
                self._out.write(data + b"\n")
                self._out.flush()
            except (BrokenPipeError, ValueError, OSError):
                pass                                  # client gone; the read loop ends next

    def _notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _receive(self, message: Any) -> None:
        # The legacy handshake is answered in order, before anything that depends on the version it
        # negotiates; notifications are cheap; every other request runs on the pool so none blocks
        # another.
        if isinstance(message, dict) and message.get("method") == "initialize":
            response = self.handle(message)
            if response is not None:
                self._send(response)
        elif isinstance(message, dict) and "id" not in message:
            self.handle(message)
        else:
            if isinstance(message, dict):
                self._track(message)
            self._pool.submit(self._serve_one, message)

    def _track(self, message: dict) -> None:
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
        ctx = Context(protocol_version=self.protocol_version, _notify=self._notify,
                      _progress_token=meta.get("progressToken"))
        if self._closing.is_set():
            ctx.cancelled.set()
        with self._inflight_lock:
            self._inflight[_key(message.get("id"))] = ctx

    def _serve_one(self, message: Any) -> None:
        try:
            response = self.handle(message)
        except Exception as exc:                      # never let one request take the server down
            response = _error(message.get("id") if isinstance(message, dict) else None,
                              INTERNAL_ERROR, f"internal error: {exc}")
        if response is not None:
            self._send(response)

    # --- dispatch -------------------------------------------------------------------------------

    def handle(self, message: Any) -> dict | list | None:
        """The response to one message (or batch), or None when nothing is owed."""
        if isinstance(message, list):
            if not message:
                return _error(None, INVALID_REQUEST, "empty batch")
            replies = [r for r in (self.handle(m) for m in message) if r is not None]
            return replies or None
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error(message.get("id") if isinstance(message, dict) else None,
                          INVALID_REQUEST, "not a JSON-RPC 2.0 message")
        method = message.get("method")
        if "id" not in message:
            if isinstance(method, str):
                self._notification(method, message.get("params") or {})
            return None                               # a notification, or a response to us
        rid = message["id"]
        if not isinstance(method, str):
            return None if ("result" in message or "error" in message) else \
                _error(rid, INVALID_REQUEST, "request without a method")
        params = message.get("params", {})
        if params is None:
            params = {}
        with self._inflight_lock:
            ctx = self._inflight.get(_key(rid))
        if ctx is None:
            ctx = Context(_notify=self._notify)
        modern = False
        try:
            if not isinstance(params, dict):
                raise RpcError(INVALID_PARAMS, "params must be an object")
            modern = self._select_version(method, params, ctx)
            result = self._dispatch(method, params, ctx)
        except RpcError as exc:
            code = exc.code
            if modern and code == RESOURCE_NOT_FOUND:
                code = INVALID_PARAMS                 # 2026-07-28 aligned it with JSON-RPC
            reply = _error(rid, code, exc.message, exc.data)
        except Exception as exc:
            reply = _error(rid, INTERNAL_ERROR, f"internal error: {type(exc).__name__}: {exc}")
        else:
            if modern:
                result = self._modern_result(method, result)
            reply = {"jsonrpc": "2.0", "id": rid, "result": result}
        finally:
            with self._inflight_lock:
                self._inflight.pop(_key(rid), None)
        # A request the client cancelled gets no response (MCP cancellation).
        return None if ctx.withdrawn and method != "initialize" else reply

    def _select_version(self, method: str, params: dict, ctx: Context) -> bool:
        """Settle which protocol version serves this request; True if it is a modern one.

        A request naming its version in `_meta` is served under that version alone, and refused with
        the supported list when the server does not speak it. A request without one belongs to the
        legacy session that `initialize` opened."""
        requested = _requested_version(params)
        if method == "initialize" or requested is None:
            ctx.protocol_version = self.protocol_version
            return False
        if requested not in PROTOCOL_VERSIONS:
            raise RpcError(UNSUPPORTED_PROTOCOL_VERSION, "Unsupported protocol version",
                           {"supported": list(PROTOCOL_VERSIONS), "requested": requested})
        ctx.protocol_version = requested
        return requested in MODERN_VERSIONS

    def _modern_result(self, method: str, result: dict) -> dict:
        result = dict(result)
        result["resultType"] = "complete"
        meta = dict(result.get("_meta") or {})
        meta[_META_SERVER_INFO] = self._server_info(LATEST)
        result["_meta"] = meta
        if method in _CACHE_HINTS:
            result["ttlMs"], result["cacheScope"] = _CACHE_HINTS[method]
        return result

    def _notification(self, method: str, params: dict) -> None:
        if method == "notifications/cancelled" and isinstance(params, dict):
            with self._inflight_lock:
                ctx = self._inflight.get(_key(params.get("requestId")))
            if ctx is not None:
                ctx.withdrawn = True
                ctx.cancelled.set()
        # notifications/initialized, roots/list_changed, …: nothing to do.

    def _dispatch(self, method: str, params: dict, ctx: Context) -> dict:
        h = self.handler
        if method == "initialize":
            return self._initialize(params)
        if method == "server/discover":
            return self._discover()
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [_shape_tool(t, ctx.protocol_version) for t in h.list_tools(ctx)]}
        if method == "tools/call":
            name, arguments = params.get("name"), params.get("arguments") or {}
            if not isinstance(name, str):
                raise RpcError(INVALID_PARAMS, "tools/call needs a tool name")
            if not isinstance(arguments, dict):
                raise RpcError(INVALID_PARAMS, "tool arguments must be an object")
            if name not in {t["name"] for t in h.list_tools(ctx)}:
                raise RpcError(INVALID_PARAMS, f"unknown tool: {name}")
            try:
                result = h.call_tool(name, arguments, ctx)
            except RpcError:
                raise
            except Exception as exc:                  # a tool that broke is a failed call, not a
                result = tool_result(                 # protocol error: the model can read it
                    f"{name} failed unexpectedly: {type(exc).__name__}: {exc}", error=True)
            return _shape_result(result, ctx.protocol_version)
        if method == "resources/list":
            return {"resources": h.list_resources(ctx)}
        if method == "resources/templates/list":
            return {"resourceTemplates": h.list_resource_templates(ctx)}
        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                raise RpcError(INVALID_PARAMS, "resources/read needs a uri")
            return {"contents": h.read_resource(uri, ctx)}
        if method == "prompts/list":
            return {"prompts": h.list_prompts(ctx)}
        if method == "prompts/get":
            name, arguments = params.get("name"), params.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise RpcError(INVALID_PARAMS, "prompts/get needs a name and an arguments object")
            return h.get_prompt(name, arguments, ctx)
        raise RpcError(METHOD_NOT_FOUND, f"method not found: {method}")

    def _server_info(self, version: str) -> dict:
        info = dict(self.info)
        if self.title and at_least(version, "2025-06-18"):
            info["title"] = self.title
        return info

    def _initialize(self, params: dict) -> dict:
        requested = params.get("protocolVersion")
        self.protocol_version = requested if requested in LEGACY_VERSIONS else LATEST_LEGACY
        result = {
            "protocolVersion": self.protocol_version,
            "capabilities": {"tools": {"listChanged": False},
                             "resources": {"subscribe": False, "listChanged": False},
                             "prompts": {"listChanged": False}},
            "serverInfo": self._server_info(self.protocol_version),
        }
        if self.instructions:
            result["instructions"] = self.instructions
        return result

    def _discover(self) -> dict:
        result: dict = {"supportedVersions": list(PROTOCOL_VERSIONS),
                        "capabilities": {"tools": {}, "resources": {}, "prompts": {}}}
        if self.instructions:
            result["instructions"] = self.instructions
        return result


def _key(request_id: Any) -> str:
    """Request ids may be strings or numbers; `1` and `"1"` are different requests."""
    return json.dumps(request_id)


def _error(rid: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": error}


def serve_stdio(handler: Handler, **server_kwargs) -> int:
    """Serve `handler` on this process's stdin/stdout, which then belong to the protocol alone.

    The protocol stream is moved to private descriptors first; fd 1 is pointed at stderr and fd 0 at
    /dev/null. A stray `print`, or a child process (git, nextflow, docker) that writes to its
    inherited stdout or reads its stdin, can then neither corrupt a message nor swallow one."""
    proto_in = os.fdopen(os.dup(0), "rb")
    proto_out = os.fdopen(os.dup(1), "wb")
    sys.stdout.flush()
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(2, 1)
    os.close(devnull)
    server = Server(handler, **server_kwargs)
    try:
        return server.run(proto_in, proto_out)
    finally:
        for stream in (proto_in, proto_out):
            try:
                stream.close()
            except OSError:
                pass


def serve(repo_root: Path) -> int:
    """`nfclaw mcp`: serve the nfclaw library and runner to an MCP client on stdio."""
    from runner import mcp_tools
    tools = mcp_tools.NfclawTools(repo_root)
    return serve_stdio(tools, name="nfclaw", title="nf-claw", version=mcp_tools.server_version(),
                       instructions=mcp_tools.INSTRUCTIONS)
