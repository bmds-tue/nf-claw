# MCP execution workflow

## Using nf-claw through MCP

`nfclaw mcp` serves this library to MCP clients (Claude Code, Codex, Antigravity, Hermes, …) on stdio; setup per client is in [`docs/mcp.md`](mcp.md). Each tool runs the `nfclaw` command it names, so everything in this guide applies unchanged:

- **Find and read:** `list_pipelines(query)`, then `show_pipeline(pipeline)` for its `skill.md`, or `show_pipeline(pipeline, document="reference", grep="…")` for any other parameter.
- **Run:** `run_pipeline(pipeline, outdir, input, params={…}, check=true)` validates and prints the command; without `check` it starts a detached job and returns its `job_id`. Pipeline parameters go in `params` under their schema names; nfclaw's own options (`profile`, `resume`, `nxf_env`, `limit_cpus`, …) are separate arguments.
- **Follow:** `get_job(job_id, wait_seconds=N)` reports `running` (`preparing` / `launched`), `succeeded`, `failed`, `cancelled` or `lost`, with `nfclaw status`'s report and the latest output. A job survives the client and the server: any later session reads it back (`list_jobs`).
- **Chain:** `run_chain(spec, outdir)` runs `nfclaw chain run` on the spec given as JSON; `run_status(outdir, chain=true)` verifies the lineage.
- **Stop:** `cancel_job(job_id)` stops it as `kill <nfclaw pid>` does; continue later with `resume=true`.

Use absolute paths and a new `outdir` per run, exactly as on the command line.

---

