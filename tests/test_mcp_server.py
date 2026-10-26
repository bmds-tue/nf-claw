"""The MCP protocol layer (runner.mcp_server), driven over real pipes with a stand-in handler.

What a client relies on: the handshake and version negotiation, JSON-RPC errors with the right
codes, notifications that get no reply, concurrent requests (a long tool call never blocks a ping),
cancellation, progress, and a stdout that carries protocol messages and nothing else.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

from runner import mcp_server
from runner.mcp_server import RESOURCE_NOT_FOUND, RpcError, Server, tool_result

ROOT = Path(__file__).resolve().parent.parent


class FakeHandler:
    def __init__(self):
        self.slow_started = threading.Event()

    def list_tools(self, ctx):
        schema = {"type": "object", "properties": {}, "required": []}
        return [{"name": n, "title": n.title(), "description": n, "inputSchema": schema,
                 "annotations": {"readOnlyHint": True}, "_meta": {"x/alwaysLoad": True}}
                for n in ("echo", "slow", "boom")]

    def call_tool(self, name, arguments, ctx):
        if name == "echo":
            return tool_result(json.dumps(arguments), {"arguments": arguments})
        if name == "slow":
            self.slow_started.set()
            ctx.progress(1, None, "waiting")
            ctx.cancelled.wait(arguments.get("seconds", 30))
            return tool_result("slow finished")
        raise RuntimeError("kaput")

    def list_resources(self, ctx):
        return [{"uri": "x://a", "name": "a"}]

    def list_resource_templates(self, ctx):
        return []

    def read_resource(self, uri, ctx):
        if uri == "x://a":
            return [{"uri": uri, "text": "A"}]
        raise RpcError(RESOURCE_NOT_FOUND, f"resource not found: {uri}")

    def list_prompts(self, ctx):
        return [{"name": "p"}]

    def get_prompt(self, name, arguments, ctx):
        return {"messages": [{"role": "user", "content": {"type": "text", "text": name}}]}


class Session:
    """A client on the other end of a pipe pair, with a reader thread so reads can time out."""

    def __init__(self, handler=None, **server_options):
        self.handler = handler or FakeHandler()
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        self._to_server = os.fdopen(w1, "wb")
        self.server = Server(self.handler, name="test", version="9.9", instructions="read me",
                             title="Test", **server_options)
        self.thread = threading.Thread(target=self.server.run,
                                       args=(os.fdopen(r1, "rb"), os.fdopen(w2, "wb")), daemon=True)
        self.thread.start()
        self.messages: queue.Queue = queue.Queue()
        reader = os.fdopen(r2, "rb")
        threading.Thread(target=self._read, args=(reader,), daemon=True).start()

    def _read(self, reader):
        for line in iter(reader.readline, b""):
            self.messages.put(json.loads(line))

    def send(self, message):
        data = message if isinstance(message, bytes) else json.dumps(message).encode()
        self._to_server.write(data + b"\n")
        self._to_server.flush()

    def recv(self, timeout=10.0):
        return self.messages.get(timeout=timeout)

    def request(self, rid, method, params=None, timeout=10.0):
        message = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        while True:
            reply = self.recv(timeout)
            if reply.get("id") == rid:
                return reply

    def initialize(self, version="2025-06-18"):
        reply = self.request(0, "initialize", {"protocolVersion": version, "capabilities": {},
                                               "clientInfo": {"name": "c", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return reply

    def close(self):
        self._to_server.close()
        self.thread.join(10)


@pytest.fixture
def session():
    s = Session()
    yield s
    s.close()


@pytest.mark.parametrize("version", mcp_server.LEGACY_VERSIONS)
def test_initialize_echoes_a_supported_version(session, version):
    result = session.initialize(version)["result"]
    assert result["protocolVersion"] == version
    assert result["serverInfo"]["name"] == "test" and result["instructions"] == "read me"
    assert set(result["capabilities"]) == {"tools", "resources", "prompts"}
    assert ("title" in result["serverInfo"]) == mcp_server.at_least(version, "2025-06-18")


@pytest.mark.parametrize("version", ["1999-01-01", "2026-07-28"])
def test_initialize_answers_any_other_version_with_the_latest_handshake_one(session, version):
    # 2026-07-28 has no handshake: a client opening with `initialize` gets the newest version
    # that has.
    assert session.initialize(version)["result"]["protocolVersion"] == mcp_server.LATEST_LEGACY


def test_notifications_get_no_reply_and_ping_gets_an_empty_result(session):
    session.initialize()
    session.send({"jsonrpc": "2.0", "method": "notifications/whatever", "params": {}})
    assert session.request(1, "ping") == {"jsonrpc": "2.0", "id": 1, "result": {}}


def test_protocol_errors_carry_the_jsonrpc_codes(session):
    session.initialize()
    assert session.request(1, "no/such/method")["error"]["code"] == -32601
    session.send(b"{not json")
    reply = session.recv()
    assert reply["id"] is None and reply["error"]["code"] == -32700
    session.send({"id": 2, "method": "ping"})                      # no "jsonrpc": "2.0"
    assert session.recv()["error"]["code"] == -32600
    assert session.request(3, "tools/call", {"name": "nope"})["error"]["code"] == -32602
    assert session.request(4, "tools/call", {"name": "echo", "arguments": [1]})["error"]["code"] \
        == -32602
    assert session.request(5, "resources/read", {"uri": "x://b"})["error"]["code"] == -32002


def test_string_and_numeric_request_ids_are_kept_apart(session):
    session.initialize()
    assert session.request("7", "ping")["id"] == "7"
    assert session.request(7, "ping")["id"] == 7


def test_tool_definitions_and_results_follow_the_negotiated_version():
    old, new = Session(), Session()
    try:
        old.initialize("2024-11-05")
        new.initialize("2025-06-18")
        old_tool = old.request(1, "tools/list")["result"]["tools"][0]
        new_tool = new.request(1, "tools/list")["result"]["tools"][0]
        assert "annotations" not in old_tool and "title" not in old_tool
        assert "_meta" not in old_tool                # a Tool's _meta came with 2025-06-18
        assert new_tool["annotations"] == {"readOnlyHint": True} and new_tool["title"] == "Echo"
        assert new_tool["_meta"] == {"x/alwaysLoad": True}
        old_result = old.request(2, "tools/call", {"name": "echo", "arguments": {"a": 1}})["result"]
        new_result = new.request(2, "tools/call", {"name": "echo", "arguments": {"a": 1}})["result"]
        assert old_result == {"content": [{"type": "text", "text": '{"a": 1}'}]}
        assert new_result["structuredContent"] == {"arguments": {"a": 1}}
    finally:
        old.close()
        new.close()


def test_a_tool_that_raises_is_a_failed_call_not_a_dead_server(session):
    session.initialize()
    result = session.request(1, "tools/call", {"name": "boom"})["result"]
    assert result["isError"] is True and "kaput" in result["content"][0]["text"]
    assert session.request(2, "ping")["result"] == {}


def test_a_long_tool_call_does_not_block_other_requests(session):
    session.initialize()
    session.send({"jsonrpc": "2.0", "id": "slow", "method": "tools/call",
                  "params": {"name": "slow", "arguments": {"seconds": 30}}})
    assert session.handler.slow_started.wait(10)
    assert session.request(1, "ping")["result"] == {}             # answered while slow waits
    assert session.request(2, "resources/list")["result"]["resources"][0]["uri"] == "x://a"
    session.send({"jsonrpc": "2.0", "method": "notifications/cancelled",
                  "params": {"requestId": "slow", "reason": "test"}})
    # The cancelled call gets no response; the next request is answered normally.
    assert session.request(3, "ping") == {"jsonrpc": "2.0", "id": 3, "result": {}}
    with pytest.raises(queue.Empty):
        session.recv(timeout=0.5)


def test_progress_is_reported_when_the_client_asks_for_it(session):
    session.initialize()
    session.send({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": "slow", "arguments": {"seconds": 0},
                             "_meta": {"progressToken": "tok"}}})
    progress = session.recv()
    assert progress["method"] == "notifications/progress"
    assert progress["params"] == {"progressToken": "tok", "progress": 1, "message": "waiting"}
    assert session.recv()["result"]["content"][0]["text"] == "slow finished"


def test_a_batch_gets_one_array_reply(session):
    session.initialize()
    session.send([{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                  {"jsonrpc": "2.0", "method": "notifications/initialized"},
                  {"jsonrpc": "2.0", "id": 2, "method": "nope"}])
    reply = session.recv()
    assert [r["id"] for r in reply] == [1, 2] and reply[1]["error"]["code"] == -32601


def test_requests_already_sent_are_answered_when_the_client_closes_its_end():
    s = Session()
    s.initialize()
    s.send({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"x": "y"}}})
    s.close()
    assert s.recv(timeout=5)["id"] == 1


def test_stdout_carries_only_protocol_messages(tmp_path):
    # A tool that prints, writes to fd 1 and runs a child that writes to its stdout and reads its
    # stdin: none of it may reach the client's stream, and the child must not eat a request.
    script = tmp_path / "server.py"
    script.write_text(textwrap.dedent("""
        import os, subprocess, sys
        from runner import mcp_server
        from runner.mcp_server import tool_result

        class Noisy:
            def list_tools(self, ctx):
                return [{"name": "noisy", "description": "", "inputSchema": {"type": "object"}}]
            def call_tool(self, name, arguments, ctx):
                print("stray print")
                os.write(1, b"raw write to fd 1\\n")
                subprocess.run(["sh", "-c", "echo child stdout; cat > /dev/null"], timeout=10)
                return tool_result("clean")
            def list_resources(self, ctx): return []
            def list_resource_templates(self, ctx): return []
            def read_resource(self, uri, ctx): return []
            def list_prompts(self, ctx): return []
            def get_prompt(self, name, arguments, ctx): return {"messages": []}

        sys.exit(mcp_server.serve_stdio(Noisy(), name="noisy", version="1"))
    """))
    requests = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
                 "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                            "clientInfo": {"name": "c", "version": "1"}}},
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "noisy", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 2, "method": "ping"}]
    proc = subprocess.run([sys.executable, str(script)],
                          input="".join(json.dumps(r) + "\n" for r in requests),
                          capture_output=True, text=True, timeout=60,
                          env={**os.environ, "PYTHONPATH": str(ROOT)})
    replies = [json.loads(line) for line in proc.stdout.splitlines()]   # every line is JSON
    assert sorted(r["id"] for r in replies) == [0, 1, 2]
    assert next(r for r in replies if r["id"] == 1)["result"]["content"][0]["text"] == "clean"
    for noise in ("stray print", "raw write to fd 1", "child stdout"):
        assert noise in proc.stderr and noise not in proc.stdout


# --- the modern era (2026-07-28): no handshake, the version travels in every request -------------

MODERN = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
          "io.modelcontextprotocol/clientInfo": {"name": "c", "version": "1"},
          "io.modelcontextprotocol/clientCapabilities": {}}


def test_server_discover_describes_the_server_with_cache_hints(session):
    result = session.request(1, "server/discover", {"_meta": MODERN})["result"]
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == list(mcp_server.PROTOCOL_VERSIONS)
    assert set(result["capabilities"]) == {"tools", "resources", "prompts"}
    assert result["instructions"] == "read me"
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "test"
    assert result["ttlMs"] >= 0 and result["cacheScope"] == "public"


def test_modern_requests_are_served_without_a_handshake(session):
    tools = session.request(1, "tools/list", {"_meta": MODERN})["result"]
    assert tools["resultType"] == "complete" and tools["cacheScope"] == "public"
    assert tools["tools"][0]["annotations"] == {"readOnlyHint": True}
    call = session.request(2, "tools/call", {"name": "echo", "arguments": {"a": 1},
                                             "_meta": MODERN})["result"]
    assert call["resultType"] == "complete" and call["structuredContent"] == {"arguments": {"a": 1}}
    assert "ttlMs" not in call                                    # a tool call is not cacheable
    read = session.request(3, "resources/read", {"uri": "x://a", "_meta": MODERN})["result"]
    assert read["cacheScope"] == "private" and read["contents"][0]["text"] == "A"


def test_a_modern_request_for_an_unknown_version_lists_the_supported_ones(session):
    meta = {**MODERN, "io.modelcontextprotocol/protocolVersion": "2099-01-01"}
    error = session.request(1, "tools/list", {"_meta": meta})["error"]
    assert error["code"] == -32022
    assert error["data"] == {"supported": list(mcp_server.PROTOCOL_VERSIONS),
                             "requested": "2099-01-01"}


def test_resource_not_found_uses_each_eras_code(session):
    reply = session.request(1, "resources/read", {"uri": "x://b", "_meta": MODERN})
    assert reply["error"]["code"] == -32602
    session.initialize()
    assert session.request(2, "resources/read", {"uri": "x://b"})["error"]["code"] == -32002


def test_both_eras_are_served_by_one_process(session):
    assert session.request(1, "server/discover", {"_meta": MODERN})["result"]["resultType"]
    session.initialize("2025-03-26")
    legacy = session.request(2, "tools/list")["result"]
    assert "resultType" not in legacy and "title" not in legacy["tools"][0]
    modern = session.request(3, "tools/list", {"_meta": MODERN})["result"]
    assert modern["resultType"] == "complete" and modern["tools"][0]["title"] == "Echo"


@pytest.mark.parametrize('token', ['9007199254740993.0', '0.1000000000000000000001',
                                 '1e-9999', '1e9999'])
def test_wire_numbers_reach_pipeline_flags_and_response_without_rounding(tmp_path, token):
    from decimal import Decimal
    from runner import exact_json, mcp_tools

    class NumericHandler(FakeHandler):
        def call_tool(self, name, arguments, ctx):
            flags = mcp_tools.NfclawTools(ROOT, cwd=str(tmp_path)).run_argv({
                'pipeline': 'demo', 'outdir': 'out', 'params': arguments})
            return tool_result('numeric flags', {'flags': flags, 'values': arguments})

    class NumericSession(Session):
        def _read(self, reader):
            for line in iter(reader.readline, b""):
                self.messages.put(json.loads(line, parse_float=Decimal))

    client = NumericSession(NumericHandler())
    try:
        client.initialize()
        client.send(('{"jsonrpc":"2.0","id":1,"method":"tools/call",'
                     '"params":{"name":"echo","arguments":{"ratio":' + token + '}}}')
                    .encode())
        reply = client.recv()
        assert 'error' not in reply, reply
        result = reply['result']['structuredContent']
        flag = next(v for v in result['flags'] if v.startswith('--ratio='))
        assert Decimal(flag.split('=', 1)[1]) == Decimal(token)
        # Check serialization independently of the client's ordinary float decoder.
        assert exact_json.loads(exact_json.dumps(result['values']))['ratio'] == \
            exact_json.number(token)
    finally:
        client.close()


def test_eight_long_polls_leave_ping_status_and_cancellation_responsive():
    class PollingHandler(FakeHandler):
        def __init__(self):
            super().__init__()
            self.ready = threading.Condition()
            self.started = 0

        def list_tools(self, ctx):
            return [{"name": name, "inputSchema": {"type": "object"}}
                    for name in ("get_job", "cancel_job")]

        def call_tool(self, name, arguments, ctx):
            if name == 'get_job' and arguments.get('wait_seconds'):
                with self.ready:
                    self.started += 1
                    self.ready.notify_all()
                ctx.cancelled.wait(30)
            return tool_result(name)

    handler = PollingHandler()
    client = Session(handler)
    try:
        client.initialize()
        for rid in range(10, 18):
            client.send({'jsonrpc': '2.0', 'id': rid, 'method': 'tools/call',
                         'params': {'name': 'get_job', 'arguments': {'wait_seconds': 30}}})
        with handler.ready:
            assert handler.ready.wait_for(lambda: handler.started == 8, timeout=5)
        assert client.request(20, 'ping', timeout=1)['result'] == {}
        for rid, name in [(21, 'get_job'), (22, 'cancel_job')]:
            reply = client.request(rid, 'tools/call',
                                   {'name': name, 'arguments': {'wait_seconds': 0}}, timeout=1)
            assert reply['result']['content'][0]['text'] == name
    finally:
        client.close()


def test_cancellation_waits_preserve_ping_and_immediate_cancellation_capacity(
        tmp_path, monkeypatch):
    from types import SimpleNamespace
    from runner import jobs, mcp_tools
    handler = mcp_tools.NfclawTools(ROOT, cwd=str(tmp_path))
    ready = threading.Condition()
    started = []
    job = SimpleNamespace(id='fixture')
    monkeypatch.setattr(jobs, 'load', lambda _id: job)
    monkeypatch.setattr(jobs, 'cancel', lambda _job: True)

    def wait(job_id, seconds, ctx):
        if seconds:
            with ready:
                started.append(job_id)
                ready.notify_all()
            ctx.cancelled.wait(30)
        return job

    monkeypatch.setattr(handler, '_wait', wait)
    monkeypatch.setattr(handler, '_job_result', lambda *a, **k: tool_result('stop requested'))
    client = Session(handler, waiting_tools=('run_pipeline', 'run_chain', 'replay_run'),
                     control_tools=('cancel_job',))
    try:
        client.initialize()
        for rid in range(10, 18):
            client.send({'jsonrpc': '2.0', 'id': rid, 'method': 'tools/call',
                         'params': {'name': 'cancel_job', 'arguments': {'job_id': 'fixture'}}})
        with ready:
            assert ready.wait_for(lambda: len(started) == 8, timeout=5)
        assert client.request(20, 'ping', timeout=1)['result'] == {}
        reply = client.request(21, 'tools/call', {'name': 'cancel_job', 'arguments': {
            'job_id': 'fixture', 'wait_seconds': 0}}, timeout=1)
        assert reply['result']['content'][0]['text'] == 'stop requested'
    finally:
        client.close()
