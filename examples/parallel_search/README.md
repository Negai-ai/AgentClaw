# Parallel Search MCP

Search the web and fetch page excerpts through AgentClaw's existing MCP manager.
This example uses the anonymous [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp)
endpoint over Streamable HTTP. It needs no Parallel API key, model credentials,
model inference, database, or running AgentClaw server.

From the repository root, install the committed dependencies with
[uv](https://docs.astral.sh/uv/) and run:

```bash
uv sync --frozen
uv run --frozen python examples/parallel_search/search.py "Python asyncio TaskGroup documentation"
uv run --frozen python examples/parallel_search/search.py --url https://docs.python.org/3/library/asyncio-task.html
```

Use the committed lockfile for this example: AgentClaw's current HTTP MCP client
uses MCP SDK 1.x APIs that are no longer available in SDK 2.x.

You can combine a query and `--url` in one invocation, or repeat `--url` for up to
20 pages. The script loads the adjacent `mcp.json`, calls `web_search` and/or
`web_fetch`, prints the returned text, and closes the connections in `finally`.
It does not read or overwrite your project's MCP configuration. Connection,
network, and service errors propagate to the caller.

Anonymous searches use the service's `fast` mode. The free tier is intended for
exploration and light use and has rate limits; it is not unlimited. Fetch returns
excerpts by default. The service caps total excerpts to roughly 25,000 characters
per tool call. See the linked documentation for current limits.

## Use in a workflow

Merge the `parallel-search` entry from this example's `mcp.json` into your own
`mcpServers` object, preserving your existing entries. Keep the explicit
`streamable_http` transport and the AgentClaw `User-Agent` header.

Attach the configuration to your workflow and select the tools explicitly:

```python
from agentclaw import LLMNode, MCPToolKit

workflow.use(MCPToolKit.from_config("mcp.json"))
workflow.add_node(LLMNode(
    id="research",
    system_prompt="Search for sources and fetch relevant pages before answering. Cite source URLs.",
    tools=["web_search", "web_fetch"],
    tool_choice="auto",
    output_to_user=True,
))
```

Here `workflow` is your existing Workflow. Unlike the direct-call script, an
LLMNode needs your normal model configuration and may incur model inference costs.
The example does not change any built-in tools or model defaults.
