"""Run anonymous web search or fetch through AgentClaw's MCP manager."""

import argparse
import asyncio
from pathlib import Path
from uuid import uuid4

from agentclaw import MCPManager


async def run(args: argparse.Namespace) -> None:
    manager = MCPManager.from_config(Path(__file__).with_name("mcp.json"))
    try:
        await manager.connect("parallel-search")
        # One session per invocation, shared by related search and fetch calls.
        session_id = str(uuid4())
        if args.query:
            result = await manager.call_tool_on_server(
                "parallel-search",
                "web_search",
                {
                    "objective": args.query,
                    "search_queries": [args.query],
                    "session_id": session_id,
                },
            )
            print(result)
        if args.url:
            result = await manager.call_tool_on_server(
                "parallel-search",
                "web_fetch",
                {"urls": args.url, "session_id": session_id},
            )
            print(result)
    finally:
        await manager.disconnect_all()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="Search objective and keyword query")
    parser.add_argument("--url", action="append", help="HTTP(S) URL to fetch; repeat for multiple pages")
    args = parser.parse_args()
    if not args.query and not args.url:
        parser.error("provide a search query or --url")
    if args.url and len(args.url) > 20:
        parser.error("web_fetch accepts at most 20 URLs per call")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
