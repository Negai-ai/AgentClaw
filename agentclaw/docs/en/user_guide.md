# AgentClaw User Guide

> Declarative AI Workflow Framework - Build with configuration, not code

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [LLM Node](#llm-node)
4. [Image Input](#image-input)
5. [Multi-turn Conversations](#multi-turn-conversations)
6. [Output Control](#output-control)
7. [Conditional Routing](#conditional-routing)
8. [Human-in-Loop](#human-in-loop)
9. [Custom Nodes](#custom-nodes)
10. [Parallel Execution](#parallel-execution)
11. [Sub-workflows](#sub-workflows)
12. [Tool Integration](#tool-integration)
13. [MCP Integration](#mcp-integration)
14. [Skills System](#skills-system)
15. [Document Parsing](#document-parsing)
16. [Prompt Management](#prompt-management)
17. [Model Configuration](#model-configuration)
18. [Logging](#logging)
19. [Edge Registration](#edge-registration)
20. [Service Deployment](#service-deployment)
21. [Admin Dashboard](#admin-dashboard)
22. [Scheduled Tasks](#scheduled-tasks)
23. [CLI Commands](#cli-commands)
24. [Configuration Reference](#configuration-reference)

---

## Quick Start

### Installation

```bash
pip install agentclaw-ai
```

### Minimal Example

```python
from agentclaw import Workflow, LLMNode, LLMManager

workflow = Workflow(id="hello", name="Hello")
workflow.use(LLMManager())
workflow.add_node(LLMNode(id="chat", system_prompt="You are a friendly assistant"))

import asyncio
result = asyncio.run(workflow.run({"user_input": "Hello"}))
print(result["state"]["chat"])
```

### Configure Models

Create `models.json`:

```json
{
    "default": "qwen",
    "models": [
        {
            "id": "qwen",
            "model": "qwen/qwen3-235b",
            "api_key": "your-key",
            "base_url": "https://api.example.com/v1"
        }
    ]
}
```

---

## Core Concepts

### Workflow

A workflow is an ordered collection of nodes that defines AI Agent execution logic.

```python
workflow = Workflow(
    id="my_workflow",    # Unique ID for API routing
    name="My Workflow",  # Display name
    version="1.0.0"      # Version
)
```

### Node Types

| Type | Purpose | Example |
|------|---------|---------|
| `LLMNode` | LLM calls | Conversation, analysis, generation |
| `HumanNode` | Wait for user input | Approval, confirmation |
| `@workflow.node()` | Custom function | Data processing, API calls |
| `CustomNode` | Custom class node | Complex logic encapsulation |
| `MCPNode` | MCP tool call | Direct MCP tool invocation |
| `DocumentNode` | Document parsing | PDF, Word to text |
| `AgentNode` | Sub-workflow | Nested execution |

### State

Nodes pass data through state. Each node's returned dict is merged into state.

```python
# Node A returns
{"analysis": "Analysis result"}

# Node B can read
state["analysis"]  # "Analysis result"
```

#### System Reserved Fields

| Field | Description |
|-------|-------------|
| `__messages__` | Conversation history |
| `__interrupted__` | Interrupt flag |
| `__status__` | Workflow status |
| `__interrupt_info__` | Interrupt metadata |
| `__interrupt_node__` | Interrupted node id |
| `__error__` | Error information |

> User-defined state fields should not start with `__`.

#### Input Parameter Definition (inputs)

Use the `inputs` parameter to define workflow inputs. Three styles are supported:

```python
from agentclaw import Workflow, Input

# Method 1: dict shorthand (quick prototyping)
workflow = Workflow(
    id="simple",
    name="Simple Example",
    inputs={"query": str, "count": int}
)

# Method 2: Input objects (recommended)
workflow = Workflow(
    id="with_constraints",
    name="With Constraints",
    inputs=[
        Input("query", str, required=True, description="Query content"),
        Input("count", int, default=10, min=1, max=100),
        Input("language", str, default="en", description="Language"),
    ]
)

# Method 3: Pydantic BaseModel (complex schemas)
from pydantic import BaseModel, Field

class MyInputs(BaseModel):
    query: str = Field(..., description="Query content")
    count: int = Field(default=10, ge=1, le=100)

workflow = Workflow(id="pydantic", name="Pydantic Example", inputs=MyInputs)
```

**Input parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Parameter name |
| `type` | type | Parameter type such as `str`, `int`, `float`, `bool`, or `list` |
| `required` | bool | Whether the field is required, default `False` |
| `default` | Any | Default value |
| `description` | str | Field description |
| `min` / `max` | number | Numeric range constraints |
| `min_length` / `max_length` | int | String length constraints |

#### Special Input Types

Special types such as files, images, and audio are supported:

```python
from agentclaw import Input
from agentclaw.inputs import Image, File, Audio

workflow = Workflow(
    id="multimodal",
    name="Multimodal Input",
    inputs=[
        Input("query", str, required=True),
        Input("image", Image, description="Upload image"),
        Input("document", File, description="Upload document"),
        Input("audio", Audio, description="Upload audio"),
    ]
)
```

#### User Input Field (`user_input`)

In agent-style conversation workflows, use `user_input` to designate which input field receives the conversation text:

```python
workflow = Workflow(
    id="chat_agent",
    name="Chat Agent",
    inputs=[
        Input("user_input", str, required=True, description="User message"),
        Input("language", str, default="en", description="Language"),
    ],
    user_input="user_input",
)
```

---

## LLM Node

### Basic Usage

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="You are a friendly assistant"
))
```

The framework automatically:
- Reads `state["user_input"]` as user message
- Calls LLM for response
- Stores response in `state["chat"]` (default: node name)

### Specify Output Key

```python
workflow.add_node(LLMNode(
    id="analyze",
    system_prompt="Analyze the user's intent",
    output_key="intent"
))
```

### JSON Output

```python
workflow.add_node(LLMNode(
    id="classify",
    system_prompt='Classify intent, return JSON: {"type": "question|complaint"}',
    output_format="json"
))
```

### Using Variables

system_prompt supports `{variable}` syntax:

```python
workflow.add_node(LLMNode(
    id="summarize",
    system_prompt="Based on analysis ({analysis}), generate summary"
))
```

### Specify Model

```python
workflow.add_node(LLMNode(
    id="vision_task",
    system_prompt="Describe the image",
    model_id="qwen-vl"
))
```

### Agent Enhancement Mode

Setting `agent_style="agentic"` enables the Agent Runtime Harness for that node. The Harness does not require a separate process; it starts automatically when the agentic `LLMNode` runs and manages the model/tool loop, post-tool decisions, progress feedback, and final response generation.

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You are a coding assistant",
    enable_builtin_skills=True,  # Enable built-in skills (e.g. agent_creator)
    enable_builtin_tools=True,   # Enable built-in tools (planning/tools bundle)
    agent_style="agentic",     # Use enhanced prompt template
))
```

| Config | Description |
|--------|-------------|
| `enable_builtin_skills` | Enable built-in skills such as `agent_creator` |
| `enable_builtin_tools` | Enable built-in tools, including planning tools |
| `agent_style` | `"default"` or `"agentic"`; `agentic` starts the Agent Runtime Harness and injects an enhanced system prompt template |

---

## Image Input

### Define Image Type in inputs

Use `Image` type to define image parameters in workflow inputs:

```python
from agentclaw import Workflow, Input, LLMNode
from agentclaw.inputs import Image

workflow = Workflow(
    id="image_analyzer",
    name="Image Analysis",
    inputs=[
        Input("user_input", str, required=True, description="User question"),
        Input("image", Image, description="Upload image"),
    ]
)

workflow.add_node(LLMNode(
    id="analyze",
    system_prompt="Describe the content of this image",
    model_id="qwen-vl",       # Vision model configured in models.json
    images_key="image"        # Read from state["image"]
))
```

### Supported Image Formats

| Format | Extension |
|--------|-----------|
| JPEG | `.jpg`, `.jpeg` |
| PNG | `.png` |
| GIF | `.gif` |
| WebP | `.webp` |

### API Call with Image

```bash
# Using Base64
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "image_analyzer",
    "inputs": {
      "user_input": "Describe this image",
      "image": "data:image/png;base64,iVBORw0KGgo..."
    }
  }'

# Using URL
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "image_analyzer",
    "inputs": {
      "user_input": "What animal is this?",
      "image": "https://example.com/cat.jpg"
    }
  }'
```

---

## Multi-turn Conversations

### Enable Session Context

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="You are a friendly assistant",
    use_context=True,          # Load history (default True)
    save_to_context=True,      # Save to history (default True)
    max_context_messages=20    # Max history count
))
```

### Cross-request Sessions

Use `thread_id` for session persistence:

```python
# First conversation
result1 = await workflow.run(
    {"user_input": "My name is John"},
    thread_id="session_001"
)

# Second conversation (auto-restore context)
result2 = await workflow.run(
    {"user_input": "What's my name?"},
    thread_id="session_001"
)
```

---

## Output Control

### output() Function

Output content to users in real-time from nodes:

```python
from agentclaw import output

@workflow.node("process")
async def process(state):
    await output("Processing...")  # Immediately push to user
    return {}
```

### output() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | Any | Required | Output content (string or async iterator) |
| `node` | str | None | Node name (identifies output source) |
| `save_to_context` | bool | False | Save to `__messages__` |
| `stream` | bool | True | Enable streaming output |
| `silent` | bool | False | Silent mode (save only, no output) |

### Streaming Output

`output()` function streams by default (`stream=True`). When passing an async iterator, it pushes chunks to users one by one:

```python
from agentclaw import output
from agentclaw.utils.stream import fake_stream

@workflow.node("stream_demo")
async def stream_demo(state):
    # Use fake_stream to convert text to streaming output
    result = await output(
        fake_stream("Hello, I'm your assistant!"),
        stream=True,  # Default is True, can be omitted
    )
    return {"result": result}
```

Disable streaming (collect all then push at once):

```python
@workflow.node("batch_output")
async def batch_output(state):
    result = await output(
        fake_stream("This text will be output all at once"),
        stream=False,  # Collect then output at once
    )
    return {"result": result}
```

### Save to Context

For greetings, role settings that need to be saved to conversation history:

```python
@workflow.node("greeting")
async def greeting(state):
    await output("Hello! I'm your assistant.", save_to_context=True)
    return {}
```

### LLMNode Streaming

Use `LLMNode`'s `stream` and `output_to_user` parameters:

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="You are a friendly assistant",
    stream=True,           # Enable streaming
    output_to_user=True,   # Output to user
))
```

---

## Conditional Routing

### Declarative Routing

```python
workflow.add_node(LLMNode( 
    id="classify",
    system_prompt='Classify intent, return JSON: {"intent": "question|complaint"}',
    output_format="json",
    output_key="result"
))

workflow.add_router(
    after="classify",
    routes={
        "question": "answer",
        "complaint": "handle",
        "default": "__end__"
    },
    condition="result.intent"
)
```

### Function-based Routing

```python
workflow.add_router(
    after="assess",
    routes={"high": "escalate", "low": "auto"},
    condition=lambda state: "high" if state.get("score", 0) > 70 else "low"
)
```

---

## Human-in-Loop

### Wait for User Input

```python
from agentclaw import HumanNode

workflow.add_node(HumanNode(
    id="wait_input",
    feedback_field="user_input"
))
```

### HumanNode Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `id` | Required | Node name |
| `feedback_field` | `"feedback"` | Field that waits for user input |
| `save_to_context` | `True` | Whether to store the user reply in conversation history |

### Dangerous Operation Confirmation

For `agent_style="agentic"` nodes, dangerous-operation confirmation is handled automatically by the Harness. The Harness adds a runtime-only risk field to tool schemas so the model can classify the specific call, then applies `final_risk = max(inherent_tool_risk, model_assessed_risk)` before execution. `shell` and `python` have at least medium inherent risk even when the model marks a call as low risk.

Risk criteria:

| Risk | Criteria |
|------|----------|
| `low` | Read-only inspection, local listing, pure calculation, or information retrieval with no side effects |
| `medium` | Commands or code execution, local file/config changes, dependency installs, network/API calls, or reversible actions that may affect runtime state |
| `high` | Destructive or irreversible operations, secret exposure, auth/permission/deployment changes, production or external data mutation, sudo/privilege escalation, external sends/payments, or unclear blast radius |

**Sudo support**

When the agent needs to run a privileged command such as `docker` or `systemctl`, it can ask the user for sudo confirmation:

```python
confirm_action(
    action="Inspect Docker containers",
    description="Run: docker ps -a",
    require_sudo=True
)

execute_sudo_command(command="docker ps -a")
```

**Flow**

1. The agent calls `confirm_action(require_sudo=True)`.
2. The frontend receives an SSE event and shows a confirmation dialog with a password field.
3. The user confirms and provides the password.
4. The password is stored only in the current session state and is not persisted.
5. The agent runs `execute_sudo_command`.
6. The password is cleared automatically after execution.

**Security**

- Passwords are kept in memory only.
- They are valid only for the current workflow session.
- They are cleared automatically after command execution.
- A 30-second timeout is enforced.

### Approval Flow

```python
workflow.add_node(LLMNode(
    id="generate",
    system_prompt="Generate marketing copy: {user_input}",
    output_key="content"
))

workflow.add_node(HumanNode(
    id="approval",
    feedback_field="approved",
    save_to_context=False,
))

# First execution - interrupts at approval
result = await workflow.run({"user_input": "Write product intro"})
thread_id = result["thread_id"]

# Resume after approval
result = await workflow.run({"approved": True}, resume_from=thread_id)
```

### Usage Flow

```python
# First run: generate content, then interrupt
result = await workflow.run({"user_input": "Write a product introduction"})
thread_id = result["thread_id"]

# Resume after approval
result = await workflow.run(
    {"approved": True},
    resume_from=thread_id
)
```

---

## Custom Nodes

### Decorator Syntax

```python
@workflow.node("fetch_data")
async def fetch_data(state):
    data = await fetch_api(state["url"])
    return {"data": data}
```

### Function Node Decorator

```python
from agentclaw import node

@node("upper")
def to_upper(text):  # Parameter names auto-match state keys
    return {"upper_text": text.upper()}

@node("calc")
def calculate(a, b):
    return {"sum": a + b, "product": a * b}

workflow.add_node(to_upper)
```

### Class-based Custom Node

```python
from agentclaw import CustomNode

class PrefixNode(CustomNode):
    def __init__(self, id, prefix=">>", **kwargs):
        super().__init__(id, **kwargs)
        self.prefix = prefix
    
    def process(self, text):
        return {"result": self.prefix + text}

workflow.add_node(PrefixNode("add_prefix", prefix="[INFO] "))
```

---

## Parallel Execution

Connect one node to multiple targets using `add_edge`, and they will execute in parallel automatically:

```python
workflow = Workflow(id="parallel_demo", name="Parallel Demo")

# Define nodes
workflow.add_node(LLMNode(id="start", system_prompt="Start processing"))
workflow.add_node(LLMNode(id="sentiment", system_prompt="Analyze sentiment"))
workflow.add_node(LLMNode(id="keywords", system_prompt="Extract keywords"))
workflow.add_node(LLMNode(id="merge", system_prompt="Merge analysis results"))

# Set edges: start connects to multiple analysis nodes (parallel execution)
workflow.add_edge("__start__", "start")
workflow.add_edge("start", "sentiment")
workflow.add_edge("start", "keywords")

# Both analysis nodes point to merge (auto-wait for all parallel tasks)
workflow.add_edge("sentiment", "merge")
workflow.add_edge("keywords", "merge")
workflow.add_edge("merge", "__end__")
```

### Parallel Execution Rules

1. When a node connects to multiple targets via `add_edge`, those targets execute in parallel
2. When multiple parallel nodes point to the same successor, the framework auto-waits for all parallel tasks to complete
3. Results from parallel nodes are automatically merged into state

---

## Sub-workflows

```python
sub_workflow = Workflow(id="sub_task", name="Sub Task")
sub_workflow.add_node(LLMNode(id="process", system_prompt="Process sub task"))

@main_workflow.node("call_sub")
async def call_sub(state):
    result = await sub_workflow.run(
        inputs={"user_input": state["sub_input"]},
        thread_id=f"{state.get('thread_id')}_sub"
    )
    return {"sub_result": result["state"]["process"]}
```

---

## Tool Integration

### Default: `@workflow.tool` Auto Registration

For workflow-local tools, use `@workflow.tool` directly.  
AgentClaw automatically creates/attaches a local toolkit for this workflow.

```python
from agentclaw import Workflow, LLMNode

workflow = Workflow(id="tool_agent", name="Tool Agent")

@workflow.tool
async def search(query: str, limit: int = 10) -> str:
    """
    Search the web

    Args:
        query: Search keywords
        limit: Result limit
    """
    return f"Results: {query}, limit={limit}"

workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You are an assistant that can use tools",
    tools=["search"],
    tool_choice="auto",
))
```

### Advanced: `register_toolkit(...)` for Reuse/Plugins

Use explicit toolkit registration when tools are shared across workflows or come from plugin modules.

```python
from agentclaw import ToolKit

toolkit = ToolKit()

@toolkit.tool
async def search(query: str, limit: int = 10) -> str:
    """
    Search the web
    
    Args:
        query: Search keywords
        limit: Result limit
    """
    return f"Results: {query}"

# Merge into workflow primary toolkit (default)
workflow.register_toolkit(toolkit)

# Optional conflict strategy
# workflow.register_toolkit(toolkit, overwrite=True)
```

### Compatibility: `workflow.use(toolkit)`

Existing code using `workflow.use(toolkit)` remains supported for backward compatibility.

### Parameter Description Extraction

AgentClaw supports three ways to extract tool parameter descriptions, in descending priority order:

```python
# Method 1: manual injection (highest priority)
@toolkit.tool(params={
    "query": {"description": "Search keywords"},
    "limit": {"description": "Maximum number of results"},
})
async def search(query: str, limit: int = 10) -> str:
    """Search the database"""
    ...

# Method 2: Annotated types
from typing import Annotated

@toolkit.tool
async def search(
    query: Annotated[str, "Search keywords"],
    limit: Annotated[int, "Maximum number of results"] = 10,
) -> str:
    """Search the database"""
    ...

# Method 3: docstring extraction (Google style)
@toolkit.tool
async def search(query: str, limit: int = 10) -> str:
    """
    Search the database

    Args:
        query: Search keywords
        limit: Maximum number of results
    """
    ...
```

### LLM Auto Tool Calls

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You are an assistant that can use tools",
    tools=["search"],
    tool_choice="auto",
    max_tool_rounds=5,
))
```

---

## MCP Integration

### Configure MCP Server

Create `mcp.json`:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "fetch-sse": {
      "transport": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### Transport Types

| Type | Description | Example |
|------|-------------|---------|
| `stdio` | Local process communication (default) | `"command": "npx", "args": [...]` |
| `sse` | Server-Sent Events | `"transport": "sse", "url": "..."` |
| `streamable_http` | HTTP streamable transport | `"transport": "streamable_http", "url": "..."` |

### LLMNode Auto Call

For a runnable web search and page-fetch example without a Parallel API key,
see [Parallel Search MCP](../../../examples/parallel_search/README.md). It uses
the existing Streamable HTTP transport and includes workflow configuration.

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You can use tools",
    tools=["fetch"],
    tool_choice="auto",
))
```

### MCPNode Direct Call

```python
from agentclaw import MCPNode

workflow.add_node(MCPNode(
    id="fetch_page",
    server="fetch",
    tool="fetch",
    output="page_content",
    arguments={"url": "{target_url}"},
))
```

### MCPNode Configuration

| Config | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Unique node id |
| `server` | Yes | MCP server name from `mcp.json` |
| `tool` | Yes | Tool name |
| `output` | Yes | Output key in state |
| `arguments` | No | Tool arguments, supports `{key}` templates |

### MCPPipelineNode

Execute multiple MCP tools in order:

```python
from agentclaw import MCPPipelineNode

workflow.add_node(MCPPipelineNode(
    id="train_query",
    steps=[
        {"server": "12306", "tool": "get-current-date", "output": "query_date"},
        {
            "server": "12306",
            "tool": "get-station-code-of-citys",
            "arguments": {"citys": "{from_city}|{to_city}"},
            "output": "station_codes",
        },
        {
            "server": "12306",
            "tool": "get-tickets",
            "arguments": {"date": "{query_date}", "fromStation": "{from_code}"},
            "output": "tickets",
        },
    ],
))
```

---

## Skills System

Skills are Anthropic's specification for injecting domain knowledge into LLMs.

### Installing Skills

Copy skill folders to your project's `skills/` directory:

```bash
# Clone from GitHub
git clone https://github.com/example/skill-pdf.git skills/pdf

# Or copy directly
cp -r ~/downloads/skill-pdf skills/pdf
```

If a skill includes `requirements.txt`, AgentClaw initializes its isolated environment automatically when the skill is loaded or used.

### Skill Directory Structure

```
skills/
├── pdf/
│   ├── SKILL.md           # Skill definition (required)
│   ├── scripts/           # Executable scripts
│   │   └── convert.py
│   └── reference/         # Reference docs
└── text-utils/
    └── SKILL.md
```

### `SKILL.md` Format

```markdown
---
name: pdf
description: PDF processing skill for conversion, extraction, and merging
---

# PDF Processing Skill

## Overview

This skill is used to process PDF files...

## Instructions

When the user needs to work with PDFs:
1. Use `convert.py` for format conversion
2. Use `extract.py` for content extraction

## Examples

**Input**: Convert `report.pdf` into images
**Output**: Run `convert.py --format png report.pdf`
```

### Using Skills in LLMNode

```python
# Explicit skill list
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You are a document assistant",
    skills=["pdf", "text-utils"],
))

# Auto-match skills (based on user_input)
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="You are a smart assistant",
    skills="*",
))
```

### Skill Environment

Skills can have their own isolated Python virtual environment:

```python
# skills/pdf/scripts/requirements.txt
pdf2image==1.16.3
PyPDF2==3.0.1
```

The framework automatically:

1. Detects `requirements.txt`
2. Creates an isolated environment
3. Installs dependencies
4. Runs scripts inside that environment

---

## Document Parsing

### DocumentNode

```python
from agentclaw import DocumentNode

workflow.add_node(DocumentNode(
    id="parse_doc",
    input_key="document",
    output_key="doc_content",
    include_metadata=True,
    max_length=10000,
))
```

### Supported Formats

- PDF, Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`)
- HTML, images (OCR), audio (transcription)

### DocumentExtractNode

Parse a document and extract specific information:

```python
from agentclaw import DocumentExtractNode

workflow.add_node(DocumentExtractNode(
    id="extract",
    input_key="document",
    extract_sections=["Summary", "Conclusion"],
    extract_tables=True,
))
```

### Dependency Installation

```bash
pip install markitdown[all]
```

---

## Prompt Management

Prompts are defined directly via the `system_prompt` parameter of `LLMNode`. The framework manages them automatically.

### Basic Usage

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="You are a friendly assistant that helps users with their questions."
))
```

### Using Variables

Prompts support `{variable}` syntax, automatically populated from state:

```python
workflow.add_node(LLMNode(
    id="summarize",
    system_prompt="Generate a summary based on the following analysis: {analysis}"
))
```

### Hot Reload (Production)

With database configured, prompts can be updated at runtime via Admin API:

```bash
# Update prompt
curl -X PUT http://localhost:8000/admin/prompts/my_workflow/chat \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "New prompt content"}'

# Reset to default
curl -X POST http://localhost:8000/admin/prompts/my_workflow/chat/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Model Configuration

### models.json

```json
{
    "default": "qwen3-next",
    "fallback": "qwen3-32b",
    "vision": "qwen-vl",
    "models": [
        {
            "id": "qwen3-next",
            "model": "qwen/qwen3-235b-a22b",
            "api_key": "your-api-key",
            "base_url": "https://openrouter.ai/api/v1",
            "type": "chat",
            "temperature": 0.1,
            "max_tokens": 8192,
            "timeout": 240
        },
        {
            "id": "qwen-vl",
            "model": "qwen/qwen-2.5-vl-72b-instruct",
            "api_key": "your-api-key",
            "base_url": "https://openrouter.ai/api/v1",
            "type": "chat",
            "supports_vision": true
        }
    ]
}
```

### Model Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | string | required | Unique model identifier |
| `model` | string | required | Model name |
| `api_key` | string | required | API key |
| `base_url` | string | required | API base URL |
| `type` | string | "chat" | Model type: chat / embedding / rerank |
| `supports_vision` | boolean | false | Whether this chat model supports image input |
| `temperature` | float | 0.1 | Temperature (0-2) |
| `max_tokens` | int | 8192 | Maximum output tokens |
| `timeout` | int | 240 | Request timeout (seconds) |

### Parameter Priority

```
models.json (model defaults) < LLMNode.model_params (node override)
```

```python
# Node-level override
workflow.add_node(LLMNode(
    id="classify",
    system_prompt="Classify intent",
    model_params={"temperature": 0.0, "max_tokens": 100}
))
```

### Auto Fallback

```python
from agentclaw import LLMManager

llm = LLMManager(
    default="qwen3-next",
    fallback="qwen3-32b",
    auto_fallback=True,
    fallback_threshold=3,
    fallback_duration=300,
)
workflow.use(llm)
```

### Node-Level Fallback

```python
workflow.add_node(LLMNode(
    id="critical_task",
    system_prompt="Important task",
    fallback_model_id="backup-model",
    auto_fallback=True,
    fallback_threshold=2,
))
```

---

## Logging

### Basic Usage

```python
from agentclaw.logger.config import get_logger, setup_logging

# Initialize logging
setup_logging(
    level="INFO",              # DEBUG / INFO / WARNING / ERROR
    log_file="logs/app.log",   # Optional: output to file
    format_style="simple",     # simple / detailed
)

# Use in modules
logger = get_logger(__name__)
logger.info("Workflow started")
```

### Dynamic Level Adjustment

```python
from agentclaw.logger.config import set_log_level

set_log_level("DEBUG")
```

---

## Edge Registration

### Special Nodes

| Node | Description |
|------|-------------|
| `__start__` | Workflow entry point |
| `__end__` | Workflow end point |

### Manual Link (required)

```python
workflow = Workflow(id="demo")
workflow.add_edge("__start__", "A")
workflow.add_edge("A", "B")
workflow.add_edge("B", "__end__")
```

### Conditional Edges

```python
workflow.add_conditional_edge(
    source="classify",
    condition=lambda state: state.get("result", {}).get("intent", "default"),
    targets={
        "question": "answer",
        "complaint": "handle",
        "default": "__end__",
    }
)
```

---

## Service Deployment

### Quick Start

```bash
agentclaw init my-project
cd my-project
agentclaw serve
```

Or with Python:

```python
import agents
from agentclaw import AgentClawServer

server = AgentClawServer()
server.run()
```

### Publish Workflow

```python
from agentclaw import WorkflowRegistry

WorkflowRegistry.register(workflow, stream=True)

server = AgentClawServer()
server.run()
```

### API Call

```bash
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my_workflow",
    "response_mode": "blocking",
    "conversation_id": "session_001",
    "user": "Hello",
    "user_id": "user_123",
    "inputs": {"locale": "en-US"}
  }'
```

`<WORKFLOW_API_KEY>` can be the global `WORKFLOW_API_KEY` environment variable, or the workflow's own `workflow_api_key` when **Publish API** is enabled for that workflow. The global key can execute all workflows. A workflow-specific key is scoped to that workflow only and does not grant Admin capabilities such as scheduler management, channel push, file listing, or Dashboard management.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow_id` | string | Yes | Workflow ID |
| `user` | string | No | User message text (chat/HumanNode continuation input) |
| `user_id` | string | No | Caller identity metadata |
| `response_mode` | string | No | `blocking` or `streaming`, default `blocking` |
| `conversation_id` | string | No | Session ID |
| `inputs` | object | No | Structured workflow inputs |

Notes:
- Prefer `response_mode`; the current version still accepts the legacy `mode` field.
- If workflow defines `user_input="<field>"`, top-level `user` is normalized to `inputs["<field>"]` when that key is missing.
- If both `user` and `inputs["<field>"]` are provided, they must be identical or the API returns `400 INVALID_REQUEST`.

### Response Format

Non-streaming response:

```json
{
    "outputs": [],
    "state": {
        "user_input": "Hello",
        "response": "Hello! How can I help you?"
    },
    "metadata": {
        "workflow_id": "my_workflow",
        "thread_id": "session_001",
        "duration_ms": 1234
    }
}
```

Streaming response (SSE):

```text
event: start
data: {"type": "start", "workflow_id": "my_workflow"}

event: output
data: {"type": "output", "node": "chat", "data": "Hello"}

event: result
data: {"type": "result", "data": {...}}

event: end
data: {"type": "end"}
```

### Anonymous Public Agent

To let users open a chat page without logging in, enable "Public publishing" in the Dashboard workflow configuration. It is off by default, and built-in agents cannot be publicly shared.

Public publishing uses a separate `share_token` and same-origin browser session. It does not use `WORKFLOW_API_KEY`. Generated links look like:

```text
http://localhost:8000/dashboard/agent/my_workflow?share_token=<PUBLIC_SHARE_TOKEN>
```

The public page automatically performs this sequence:

1. `GET /api/public/workflows/{workflow_id}?share_token=...` reads the minimal workflow metadata for display.
2. `POST /api/public/workflows/{workflow_id}/session?share_token=...` opens a short-lived HttpOnly session cookie.
3. `POST /api/public/workflows/{workflow_id}/run` executes the workflow with the same-origin cookie and `X-AgentClaw-Public-Session: 1`.

Anonymous public execution has these limits:

- File attachments and file-type inputs are not supported.
- Request-level model switching, `user_id`, and human confirmation settings are ignored.
- `rate_limit` applies only to anonymous public runs and public conversation APIs. Examples: `10/min`, `100/hour`.
- `public_conversation_limit` and `public_message_limit` control public conversation count per client and message count per conversation update.
- If deploying behind a trusted reverse proxy that strips externally supplied `X-Forwarded-*` headers, enable `AGENTCLAW_TRUST_PROXY_HEADERS=1`; otherwise leave it off.

### Production Configuration

```bash
# .env
ADMIN_TOKEN=your-secure-token

# PostgreSQL (optional)
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=password
PG_DATABASE=agentclaw

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Database Dependencies

AgentClaw can run without databases, but some features will be limited:

| Feature | Without PostgreSQL | Without Redis |
|---------|-------------------|---------------|
| Basic workflow execution | ✅ Works | ✅ Works |
| Multi-turn chat (single session) | ✅ Works | ✅ Works |
| Multi-turn chat (cross-session) | ❌ Unavailable | ✅ Works |
| Execution tracing/logs | ❌ Unavailable | ✅ Works |
| Admin Dashboard | ⚠️ Only workflow list available | ✅ Works |
| Prompt hot reload | ❌ Unavailable | ⚠️ Single instance OK, multi-instance needs Redis |
| LangGraph engine | ❌ Requires PostgreSQL for Checkpointer | ✅ Works |
| MCP Integration | ✅ Works | ✅ Works |
| Skills System | ✅ Works | ✅ Works |

Notes:
- Without database, builtin engine is used with full workflow functionality
- MCP and Skills don't depend on databases, fully based on local files and config
- LangGraph engine requires PostgreSQL as state checkpoint storage (Checkpointer)

Recommendations:
- Development: No database needed, use builtin engine
- Production: Configure PostgreSQL for tracing and persistence

---

## Admin Dashboard

Admin Dashboard is a visual management interface for monitoring workflow execution, managing prompts, viewing trace logs, etc.

### Start Frontend

```bash
# Enter frontend directory
cd agentclaw/admin-dashboard

# Install dependencies (first time)
npm install

# Start in dev mode
npm run dev
```

Default URL: http://localhost:5173

### Build for Production

```bash
npm run build
```

Build output is in `dist/` directory, can be deployed to any static server.

### Features Overview

| Feature | Description | Dependency |
|---------|-------------|------------|
| Workflow List | View registered workflows | None |
| Workflow Details | View node structure and config | None |
| Execution Tracing | View execution logs and timing | PostgreSQL |
| Prompt Management | Online edit and hot reload prompts | PostgreSQL |
| Agent Chat | Test workflows online | None |

### Configure Backend URL

Edit `agentclaw/admin-dashboard/src/api/index.js`:

```javascript
const API_BASE = 'http://localhost:8000'  // Change to your backend URL
```

---

## Scheduled Tasks

The scheduler module provides automated scheduling for workflows, supporting cron expressions, interval triggers, and one-time triggers.

### Trigger Types

| Type | Description | Example |
| ---- | ----------- | ------- |
| `cron` | Cron expression | `"expression": "0 9 * * 1-5"` (weekdays at 9am) |
| `interval` | Fixed interval | `"minutes": 30` (every 30 minutes) |
| `date` | One-time schedule | `"run_date": "2026-03-20T09:00:00"` |

### Create a Scheduled Job

Via API:

```bash
curl -X POST http://localhost:8000/api/scheduler/jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "workflow_id": "report_workflow",
    "trigger": {
      "type": "cron",
      "expression": "0 9 * * *",
      "timezone": "Asia/Shanghai"
    },
    "inputs": {
      "user_input": "Generate daily report"
    },
    "config": {
      "timeout": 600,
      "retry_count": 2
    }
  }'
```

### Job Management

| Action | API | Description |
| ------ | --- | ----------- |
| List jobs | `GET /api/scheduler/jobs` | Supports `status` filter |
| Job details | `GET /api/scheduler/jobs/{id}` | Includes next run time |
| Update job | `PUT /api/scheduler/jobs/{id}` | Partial update |
| Delete job | `DELETE /api/scheduler/jobs/{id}` | |
| Pause | `POST /api/scheduler/jobs/{id}/pause` | |
| Resume | `POST /api/scheduler/jobs/{id}/resume` | |
| Manual trigger | `POST /api/scheduler/jobs/{id}/trigger` | Execute once immediately |

### Execution History

Each execution automatically records status, duration, inputs/outputs, and errors:

```bash
# View execution history
curl http://localhost:8000/api/scheduler/jobs/{id}/executions \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# View execution details
curl http://localhost:8000/api/scheduler/jobs/{id}/executions/{eid} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Execution states: `pending` -> `running` -> `success` / `failed` / `timeout`

### Webhook Trigger

Jobs can be configured with a Webhook, allowing external systems to trigger execution via HTTP:

```bash
# Create job with webhook enabled
curl -X POST http://localhost:8000/api/scheduler/jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "External Trigger Job",
    "workflow_id": "my_workflow",
    "trigger": {"type": "cron", "expression": "0 9 * * *"},
    "inputs": {"user_input": "default input"},
    "webhook": {
      "enabled": true,
      "secret": "your-secret-key",
      "allow_input_override": true
    }
  }'

# Trigger via webhook (can override inputs)
curl -X POST http://localhost:8000/api/scheduler/jobs/{id}/webhook \
  -H "X-Webhook-Secret: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "webhook parameter"}'
```

- `X-Webhook-Secret` must match the configured `secret`, otherwise returns `403`
- Returns `400` if webhook is not enabled
- When `allow_input_override` is `true`, request body overrides inputs

### Job Configuration

```python
{
    "timeout": 300,        # Execution timeout (seconds)
    "retry_count": 3,      # Retry count on failure
    "retry_interval": 60,  # Retry interval (seconds), exponential backoff
    "concurrency": "skip", # skip | queue | parallel
    "max_instances": 1     # Max concurrent instances
}
```

### Concurrency Control

- **skip** (default): Skip execution if the job is already running
- **queue**: Queue and wait for the previous run to finish
- **parallel**: Allow parallel execution (set `max_instances`)

In multi-process deployments (`uvicorn --workers N`), PostgreSQL advisory locks ensure the same job is not triggered by multiple processes simultaneously.

### Admin Dashboard

In the Admin Dashboard "Scheduled Tasks" page you can:

- View all jobs and their status
- Create jobs with a visual Cron builder (calendar, weekday, time picker)
- View job details and execution history
- Pause/resume/manually trigger/delete jobs
- View and copy Webhook URL

### Dependencies

The scheduler module requires PostgreSQL for job persistence and distributed locks. Dependencies:

```toml
apscheduler = "^3.10.0"
croniter = "^2.0.0"
```

---

## CLI Commands

### Project Management

```bash
agentclaw init [path]
agentclaw up [-p PORT] [-h HOST] [-d PROJECT_DIR] [--reload] [--mode docker|remote]
agentclaw serve [-p PORT] [-h HOST] [-d PROJECT_DIR] [--reload]
```

---

## Configuration Reference

### LLMNode Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `id` | Required | Node name |
| `system_prompt` | None | System prompt |
| `user_prompt` | None | User message template |
| `output_key` | id | Output storage key |
| `output_format` | "text" | text / json |
| `output_to_user` | False | Output to user |
| `model_id` | None | Specify model |
| `model_params` | None | Model parameter overrides |
| `stream` | False | Streaming output |
| `use_context` | True | Load history messages |
| `save_to_context` | True | Save conversation to history |
| `max_context_messages` | 20 | Maximum history message count |
| `tools` | None | Tool name list |
| `max_tool_rounds` | None | Max tool call rounds (inherits `MAX_TOOL_ROUNDS` by default) |
| `skills` | None | Skill list or "*" |
| `enable_builtin_skills` | False | Enable built-in skills (e.g. agent_creator) |
| `enable_builtin_tools` | False | Enable built-in tools (includes planning tools) |
| `agent_style` | "default" | default / agentic |
| `images_key` | "" | Image key in state |
| `inject_files` | None | Whether to inject `__files__` into the prompt |
| `enable_memory` | False | Whether to inject the workflow `memory.md` into the prompt |
| `fallback_model_id` | None | Node-level fallback model |
| `auto_fallback` | None | Enable node-level auto fallback |
| `fallback_threshold` | None | Node-level failure threshold |
| `enable_compression` | True | Enable context compression |
| `compression_threshold` | 100000 | Compression threshold (token count) |
| `compression_model` | None | Model for compression (uses current model if None) |

### HumanNode Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `id` | Required | Node name |
| `feedback_field` | `"feedback"` | Field that waits for user input |
| `interrupt` | True | Whether to interrupt and wait |
| `save_to_context` | True | Save user input into conversation history |

### Workflow Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `id` | Required | Unique identifier |
| `name` | Required | Display name |
| `version` | `"1.0.0"` | Version |
| `description` | `""` | Description |
| `timeout` | 300 | Timeout in seconds |
| `inputs` | None | Input parameter definitions |
| `user_input` | None | User input field name |
| `auth_required` | False | Reserved field; no effect in the current personal edition |
| `allowed_roles` | None | Reserved field; no role checks in the current personal edition |
| `rate_limit` | None | Public Agent anonymous run/conversation rate limit, e.g. `10/min` |
| `public_share_enabled` | False | Whether anonymous public publishing is allowed; off by default |
| `public_share_token` | None | Public share token, generated when public publishing is enabled |
| `api_published` | True | Whether the workflow-specific API key is accepted by `/api/workflow/run`; global `WORKFLOW_API_KEY` is unaffected |
| `workflow_api_key` | None | Workflow-specific execution key |
| `safe_guard_apply_api` | False | Whether this workflow checks user input before API runs |
| `safe_guard_apply_public` | True | Whether this workflow checks user input on public agents, public rooms, and player chat |
| `public_conversation_limit` | 20 | Public conversation quota per client |
| `public_message_limit` | 200 | Public message quota per conversation update |
| `inject_as_agentic_capability` | True | Whether to inject the workflow name, description, and inputs into the built-in agent capability catalog for reuse; disabling it does not affect direct execution |
| `tracing` | True | Enable tracing |
| `publish_as_mcp` | False | Publish as MCP server |

Note: `auth_required` and `allowed_roles` are reserved for a future multi-user edition. For public deployments today, rely on `ADMIN_TOKEN`, Workflow API Keys, the public publishing switch, and rate/quota settings.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ADMIN_TOKEN` | Admin API auth token |
| `WORKFLOW_API_KEY` | Global workflow execution Bearer key; no Admin permissions; can execute all workflows |
| `MCP_TOKEN` | MCP authentication token; send as `Authorization: Bearer <MCP_TOKEN>` |
| `PG_HOST` | PostgreSQL host |
| `PG_PORT` | PostgreSQL port; also the Docker host-mapped port in Docker mode |
| `PG_USER` | PostgreSQL user |
| `PG_PASSWORD` | PostgreSQL password |
| `PG_DATABASE` | PostgreSQL database |
| `REDIS_HOST` | Redis host |
| `REDIS_PORT` | Redis port; also the Docker host-mapped port in Docker mode |
| `MINIO_API_PORT` | MinIO API host-mapped port in Docker mode |
| `MINIO_CONSOLE_PORT` | MinIO Console host-mapped port in Docker mode |
| `MILVUS_PORT` | Milvus gRPC/API host-mapped port in Docker mode |
| `MILVUS_HTTP_PORT` | Milvus HTTP/metrics host-mapped port in Docker mode |
| `ADMINER_PORT` | Adminer host-mapped port in Docker mode |
| `AGENTCLAW_MCP_PROXY` | Proxy URL used only for remote MCP outbound requests |
| `AGENTCLAW_TRUST_PROXY_HEADERS` | Whether to trust reverse-proxy `X-Forwarded-*` headers; off by default |
| `AGENTCLAW_CONTENT_SECURITY_POLICY` | Override the default CSP security header; leave empty for built-in policy |
| `AGENTCLAW_DUMP_LLM_FAILURE_PAYLOAD` | Whether to dump failed LLM request payloads; off by default |
| `MAX_TOOL_ROUNDS` | Max tool call rounds (default 0, unlimited) |
| `MAX_CONTEXT_MESSAGES` | Max history messages (default 0, unlimited) |
| `TOOL_RESULT_MAX_LENGTH` | Max tool result length (default 20000) |
| `SCHEDULER_TIMEZONE` | Scheduler timezone (default Asia/Shanghai) |
| `SCHEDULER_MAX_WORKERS` | Scheduler execution thread count (default 10) |

---

## Error Handling

### Node-Level Error Strategy

```python
from agentclaw import LLMNode, ErrorStrategy

LLMNode(
    id="risky_call",
    system_prompt="...",
    on_error=ErrorStrategy.RETRY,   # ABORT / SKIP / RETRY / FALLBACK
    max_retries=3,
)
```

### Workflow-Level Exceptions

```python
from agentclaw import (
    AgentClawError,
    WorkflowCancelledError,
    WorkflowTimeoutError,
    NodeExecutionError,
)

try:
    result = await workflow.run(inputs)
except WorkflowTimeoutError:
    print("Workflow timeout")
except WorkflowCancelledError:
    print("Workflow cancelled")
except NodeExecutionError as e:
    print(f"Node {e.node_id} failed")
```

---

## Next Steps

- [API Reference](./api_reference.md) - Complete API documentation
- [Best Practices](./best_practices.md) - Recommended patterns
