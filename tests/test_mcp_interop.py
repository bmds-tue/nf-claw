"""`nfclaw mcp` against the official MCP Python SDK — the client library Hermes and many other
agents use — over real stdio, in both protocol eras. Skipped when the SDK is not installed
(`pip install mcp`); the protocol itself is covered without it by test_mcp_server.py."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOOLS = {"list_pipelines", "show_pipeline", "list_versions", "chain_edges", "run_pipeline",
         "run_chain", "get_job", "list_jobs", "cancel_job", "run_status", "verify_replay"}


def _server(tmp_path) -> StdioServerParameters:
    env = {**os.environ, "PYTHONPATH": str(ROOT), "NFCLAW_STATE_DIR": str(tmp_path / "state")}
    return StdioServerParameters(command=sys.executable, args=["-m", "runner", "mcp"], env=env,
                                 cwd=str(tmp_path))


def _structured(result):
    return getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)


def test_the_sdk_client_works_through_the_initialize_handshake(tmp_path):
    async def main():
        async with stdio_client(_server(tmp_path)) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert init.serverInfo.name == "nfclaw" if hasattr(init, "serverInfo") \
                    else init.server_info.name == "nfclaw"
                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == TOOLS
                found = await session.call_tool("list_pipelines", {"query": "rnaseq", "limit": 2})
                assert not (getattr(found, "isError", None) or getattr(found, "is_error", None))
                assert _structured(found)["pipelines"][0]["name"] == "rnaseq"
                bad = await session.call_tool("show_pipeline", {"pipeline": "nosuch"})
                assert getattr(bad, "isError", None) or getattr(bad, "is_error", None)
                skill = await session.read_resource("nfclaw://pipelines/demo/skill")
                assert skill.contents[0].text == \
                    (ROOT / "pipelines" / "demo" / "skill.md").read_text()
                prompt = await session.get_prompt("use_pipeline", {"pipeline": "demo"})
                assert "nf-core/demo" in prompt.messages[0].content.text
    asyncio.run(main())


@pytest.mark.skipif(not hasattr(mcp, "Client"), reason="this SDK predates the 2026-07-28 client")
def test_the_sdk_client_negotiates_the_modern_protocol(tmp_path):
    async def main():
        async with mcp.Client(_server(tmp_path), mode="auto") as client:
            assert client.session.protocol_version == "2026-07-28"
            tools = await client.list_tools()
            assert {t.name for t in tools.tools} == TOOLS
            found = await client.call_tool("list_pipelines", {"query": "sarek", "limit": 1})
            assert _structured(found)["pipelines"][0]["name"] == "sarek"
            guide = await client.read_resource("nfclaw://guide")
            assert guide.contents[0].text == (ROOT / "AGENTS.md").read_text()
    asyncio.run(main())
