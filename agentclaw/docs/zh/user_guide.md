# AgentClaw 用户指南

> 声明式 AI 工作流框架 - 通过配置构建，而非编码

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [LLM 节点](#llm-节点)
4. [视觉模型](#视觉模型)
5. [多轮对话](#多轮对话)
6. [输出控制](#输出控制)
7. [条件路由](#条件路由)
8. [Human-in-Loop](#human-in-loop)
9. [自定义节点](#自定义节点)
10. [并行执行](#并行执行)
11. [子工作流](#子工作流)
12. [工具集成](#工具集成)
13. [MCP 集成](#mcp-集成)
14. [Skills 技能系统](#skills-技能系统)
15. [文档解析](#文档解析)
16. [提示词管理](#提示词管理)
17. [模型配置](#模型配置)
18. [日志系统](#日志系统)
19. [边注册](#边注册)
20. [服务部署](#服务部署)
21. [Admin Dashboard](#admin-dashboard)
22. [定时任务](#定时任务)
23. [CLI 命令](#cli-命令)
24. [配置参考](#配置参考)

---

## 快速开始

### 安装

```bash
pip install agentclaw-ai
```

### 最小示例

```python
from agentclaw import Workflow, LLMNode, LLMManager

workflow = Workflow(id="hello", name="Hello")
workflow.use(LLMManager())
workflow.add_node(LLMNode(id="chat", system_prompt="你是友好的助手"))

import asyncio
result = asyncio.run(workflow.run({"user_input": "你好"}))
print(result["state"]["chat"])
```

### 配置模型

创建 `models.json`：

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

## 核心概念

### Workflow（工作流）

工作流是节点的有序集合，定义了 AI Agent 的执行逻辑。

```python
workflow = Workflow(
    id="my_workflow",    # 唯一标识，用于 API 路由
    name="我的工作流",    # 显示名称
    version="1.0.0"      # 版本号
)
```

### 节点类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `LLMNode` | LLM 调用 | 对话、分析、生成 |
| `HumanNode` | 等待用户输入 | 审批、确认 |
| `@workflow.node()` | 自定义函数 | 数据处理、API 调用 |
| `CustomNode` | 自定义类节点 | 复杂逻辑封装 |
| `MCPNode` | MCP 工具调用 | 直接调用 MCP 工具 |
| `DocumentNode` | 文档解析 | PDF、Word 转文本 |
| `AgentNode` | 子工作流 | 嵌套执行 |

### State（状态）

节点间通过 state 传递数据，每个节点返回的字典会合并到 state 中。

```python
# 节点 A 返回
{"analysis": "分析结果"}

# 节点 B 可以读取
state["analysis"]  # "分析结果"
```

#### 系统保留字段

| 字段名 | 说明 |
|--------|------|
| `__messages__` | 对话历史 |
| `__interrupted__` | 中断标记 |
| `__status__` | 状态 |
| `__interrupt_info__` | 中断信息 |
| `__interrupt_node__` | 中断节点 |
| `__error__` | 错误信息 |

> ⚠️ 用户定义的 State 字段不应使用 `__` 开头的名称。

#### 输入参数定义（inputs）

使用 `inputs` 参数定义工作流的输入参数，支持三种写法：

```python
from agentclaw import Workflow, Input

# 方式 1：字典简写（快速原型）
workflow = Workflow(
    id="simple",
    name="简单示例",
    inputs={"query": str, "count": int}
)

# 方式 2：Input 对象（推荐，支持约束和描述）
workflow = Workflow(
    id="with_constraints",
    name="带约束示例",
    inputs=[
        Input("query", str, required=True, description="查询内容"),
        Input("count", int, default=10, min=1, max=100),
        Input("language", str, default="zh", description="语言"),
    ]
)

# 方式 3：Pydantic BaseModel（复杂场景）
from pydantic import BaseModel, Field

class MyInputs(BaseModel):
    query: str = Field(..., description="查询内容")
    count: int = Field(default=10, ge=1, le=100)

workflow = Workflow(id="pydantic", name="Pydantic 示例", inputs=MyInputs)
```

**Input 参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 参数名称 |
| `type` | type | 参数类型（str, int, float, bool, list） |
| `required` | bool | 是否必填，默认 False |
| `default` | Any | 默认值 |
| `description` | str | 参数描述 |
| `min` / `max` | number | 数值范围约束 |
| `min_length` / `max_length` | int | 字符串长度约束 |

#### 特殊输入类型

支持文件、图片、音频等特殊输入类型：

```python
from agentclaw import Input, Image, File, Audio

workflow = Workflow(
    id="multimodal",
    name="多模态输入",
    inputs=[
        Input("query", str, required=True),
        Input("image", Image, description="上传图片"),
        Input("document", File, description="上传文档"),
        Input("audio", Audio, description="上传音频"),
    ]
)
```

#### 用户输入字段（user_input）

在智能体对话场景中，使用 `user_input` 参数指定对话输入字段：

```python
workflow = Workflow(
    id="chat_agent",
    name="对话智能体",
    inputs=[
        Input("user_input", str, required=True, description="用户输入"),
        Input("language", str, default="zh", description="语言"),
    ],
    user_input="user_input",  # 指定用户输入字段
)
```

---

## LLM 节点

### 基础用法

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="你是一个友好的助手"
))
```

框架自动：
- 读取 `state["user_input"]` 作为用户消息
- 调用 LLM 获取响应
- 将响应存入 `state["chat"]`（默认用节点名）

### 指定输出键

```python
workflow.add_node(LLMNode(
    id="analyze",
    system_prompt="分析用户意图",
    output_key="intent"  # 结果存入 state["intent"]
))
```

### JSON 输出

```python
workflow.add_node(LLMNode(
    id="classify",
    system_prompt="分类意图，返回 JSON: {\"type\": \"question|complaint\"}",
    output_format="json"  # 自动解析为字典
))
```

### 使用变量

system_prompt 支持 `{variable}` 语法，自动从 state 填充：

```python
workflow.add_node(LLMNode(
    id="summarize",
    system_prompt="基于分析结果({analysis})生成摘要"
))
```

### 指定模型

```python
workflow.add_node(LLMNode(
    id="vision_task",
    system_prompt="描述图片内容",
    model_id="qwen-vl"  # 使用 models.json 中配置的模型
))
```

### Agent 增强模式

LLMNode 支持 Agent 增强功能：

设置 `agent_style="agentic"` 会为该节点启用 Agent Runtime Harness。Harness 不需要单独启动进程；当这个 agentic `LLMNode` 运行时会自动启动，并负责模型/工具循环、工具后处理决策、进度反馈和最终回复生成。

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是编程助手",
    enable_builtin_skills=True,  # 启用内置 skills（如 agent_creator）
    enable_builtin_tools=True,   # 启用内置工具（包含 planning tools）
    agent_style="agentic",     # 使用增强提示词模板
))
```

| 配置 | 说明 |
|------|------|
| `enable_builtin_skills` | 启用内置 skills（当前包含 `agent_creator`） |
| `enable_builtin_tools` | 启用内置工具（包含任务规划工具） |
| `agent_style` | `"default"` 或 `"agentic"`，agentic 模式会启动 Agent Runtime Harness 并注入增强系统提示词 |

---

## 图片输入

### 在 inputs 中定义图片类型

推荐使用 `Image` 类型在工作流输入中定义图片参数：

```python
from agentclaw import Workflow, Input, LLMNode
from agentclaw.inputs import Image

workflow = Workflow(
    id="image_analyzer",
    name="图像分析",
    inputs=[
        Input("user_input", str, required=True, description="用户问题"),
        Input("image", Image, description="上传图片"),
    ]
)

workflow.add_node(LLMNode(
    id="analyze",
    system_prompt="描述这张图片的内容",
    model_id="qwen-vl",      # 视觉模型
    images_key="image"       # 从 state["image"] 读取
))
```

### 支持的图片格式

| 格式 | 扩展名 |
|------|--------|
| JPEG | .jpg, .jpeg |
| PNG | .png |
| GIF | .gif |
| WebP | .webp |

### API 调用时传递图片

```bash
# 使用 Base64 传递图像
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "image_analyzer",
    "inputs": {
      "user_input": "描述这张图片",
      "image": "data:image/png;base64,iVBORw0KGgo..."
    }
  }'

# 使用 URL 传递图像
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "image_analyzer",
    "inputs": {
      "user_input": "这是什么动物？",
      "image": "https://example.com/cat.jpg"
    }
  }'
```

---

## 多轮对话

### 启用会话上下文

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="你是友好的助手",
    use_context=True,          # 加载历史消息（默认 True）
    save_to_context=True,      # 保存对话到历史（默认 True）
    max_context_messages=20    # 最大历史条数
))
```

### 跨请求会话

使用 `thread_id` 实现会话持久化：

```python
# 第一次对话
result1 = await workflow.run(
    {"user_input": "我叫小明"},
    thread_id="session_001"
)

# 第二次对话（自动恢复上下文）
result2 = await workflow.run(
    {"user_input": "我叫什么？"},
    thread_id="session_001"
)
# LLM 可以回答 "你叫小明"
```

---

## 输出控制

### output() 函数

在节点中向用户实时输出内容：

```python
from agentclaw import output

@workflow.node("process")
async def process(state):
    await output("处理中...")  # 立即推送给用户
    return {}
```

### output() 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | Any | 必填 | 输出内容（字符串或 async iterator） |
| `node` | str | None | 节点名称（标识输出来源） |
| `save_to_context` | bool | False | 是否保存到 `__messages__` |
| `stream` | bool | True | 是否流式输出 |
| `silent` | bool | False | 静默模式（只保存不输出） |

### 流式输出

`output()` 函数默认就是流式输出（`stream=True`）。当传入 async iterator 时，会逐个 chunk 推送给用户：

```python
from agentclaw import output
from agentclaw.utils.stream import fake_stream

@workflow.node("stream_demo")
async def stream_demo(state):
    # 使用 fake_stream 将文本转为流式输出
    result = await output(
        fake_stream("你好，我是助手！"),
        stream=True,  # 默认就是 True，可省略
    )
    return {"result": result}
```

关闭流式输出（等待收集完再一次性推送）：

```python
@workflow.node("batch_output")
async def batch_output(state):
    result = await output(
        fake_stream("这段文字会一次性输出"),
        stream=False,  # 收集完再一次性输出
    )
    return {"result": result}
```

### 保存到上下文

开场白、角色设定等需要保存到对话历史：

```python
@workflow.node("greeting")
async def greeting(state):
    await output("喵～我是你的小助手喵～", save_to_context=True)
    return {}
```

### LLMNode 流式输出

使用 `LLMNode` 的 `stream` 和 `output_to_user` 参数：

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="你是友好的助手",
    stream=True,           # 启用流式输出
    output_to_user=True,   # 输出给用户
))
```

---

## 条件路由

### 声明式路由

```python
# 分类节点
workflow.add_node(LLMNode( 
    id="classify",
    system_prompt="分类意图，返回 JSON: {\"intent\": \"question|complaint\"}",
    output_format="json",
    output_key="result"
))

# 处理节点
workflow.add_node(LLMNode(id="answer", system_prompt="回答问题"))
workflow.add_node(LLMNode(id="handle", system_prompt="处理投诉"))

# 路由配置
workflow.add_router(
    after="classify",
    routes={
        "question": "answer",
        "complaint": "handle",
        "default": "__end__"
    },
    condition="result.intent"  # 支持嵌套字段 a.b.c
)
```

### 函数式路由

```python
workflow.add_router(
    after="assess",
    routes={"high": "escalate", "low": "auto"},
    condition=lambda state: "high" if state.get("score", 0) > 70 else "low"
)
```

---

## Human-in-Loop

### 等待用户输入

```python
from agentclaw.node.human import HumanNode

workflow.add_node(HumanNode(
    id="wait_input",
    feedback_field="user_input"  # 等待用户提供此字段
))
```

### HumanNode 配置

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `id` | 必填 | 节点名称 |
| `feedback_field` | "feedback" | 等待用户提供的字段名 |
| `save_to_context` | True | 是否将用户输入保存到对话历史 |

### 危险操作确认

在 `agent_style="agentic"` 的节点中，危险操作确认由 Harness 自动接管。Harness 会在工具 schema 中加入仅供运行时使用的风险字段，要求模型按明确标准判断本次调用风险；执行前运行时会计算 `最终风险 = max(工具固有风险, 模型判断风险)`。其中 `shell` 和 `python` 的工具固有风险至少是 `medium`，即使模型判断为 `low` 也不会降级。

风险判断标准:

| 风险 | 判断标准 |
|------|----------|
| `low` | 只读检查、本地列表、纯计算、无副作用的信息检索 |
| `medium` | 命令或代码执行、本地文件/配置变更、安装依赖、网络/API 调用、可能影响运行状态但通常可恢复的操作 |
| `high` | 删除/覆盖等不可逆操作、泄露密钥、修改认证/权限/部署、生产或外部数据变更、sudo/提权、对外发送消息/支付、影响范围不清的操作 |

**Sudo 权限支持:**

当需要执行需要 sudo 权限的命令时（如 docker、systemctl），Agent 可以请求用户提供密码:

```python
# 1. Agent 请求 sudo 确认
confirm_action(
    action="查看 Docker 容器",
    description="执行命令: docker ps -a",
    require_sudo=True  # 前端会显示密码输入框
)

# 2. 用户确认后，Agent 执行命令
execute_sudo_command(command="docker ps -a")
```

**工作流程:**
1. Agent 调用 `confirm_action(require_sudo=True)`
2. 前端收到 SSE 事件，显示确认对话框和密码输入框
3. 用户输入密码并确认
4. 密码存储在当前会话的 state 中（不持久化）
5. Agent 使用 `execute_sudo_command` 执行命令
6. 命令执行完成后，密码自动清除

**安全特性:**
- 密码仅在内存中临时存储
- 密码仅在当前 workflow 会话有效
- 执行完成后自动清理
- 30 秒超时保护

### 审批流程

```python
# 生成内容
workflow.add_node(LLMNode(
    id="generate",
    system_prompt="生成营销文案：{user_input}",
    output_key="content"
))

# 等待审批
workflow.add_node(HumanNode(
    id="approval",
    feedback_field="approved",
    save_to_context=False,  # 审批结果不加入对话历史
))

# 处理结果
@workflow.node("publish")
async def publish(state):
    if state.get("approved"):
        return {"status": "published"}
    return {"status": "rejected"}
```

### 使用流程

```python
# 第一次执行，生成内容后中断
result = await workflow.run({"user_input": "写产品介绍"})
thread_id = result["thread_id"]

# 用户审批后恢复
result = await workflow.run(
    {"approved": True},
    resume_from=thread_id
)
```

---

## 自定义节点

### 装饰器语法（推荐）

```python
@workflow.node("fetch_data")
async def fetch_data(state):
    data = await fetch_api(state["url"])
    return {"data": data}
```

### 函数式节点装饰器

使用 `@node` 装饰器创建独立的可复用节点：

```python
from agentclaw import node

@node("upper")
def to_upper(text):  # 参数名自动从 state 取值
    return {"upper_text": text.upper()}

@node("calc")
def calculate(a, b):
    return {"sum": a + b, "product": a * b}

@node("fetch")
async def fetch_data(url):
    data = await http_get(url)
    return {"data": data}

# 添加到工作流
workflow.add_node(to_upper)
workflow.add_node(calculate)
```

### 类式自定义节点

继承 `CustomNode` 创建可配置的节点类：

```python
from agentclaw import CustomNode

class PrefixNode(CustomNode):
    def __init__(self, id, prefix=">>", **kwargs):
        super().__init__(id, **kwargs)
        self.prefix = prefix
    
    def process(self, text):  # 参数名自动从 state 取值
        return {"result": self.prefix + text}

# 使用
workflow.add_node(PrefixNode("add_prefix", prefix="[INFO] "))
```

---

## 并行执行

通过 `add_edge` 将一个节点连接到多个目标节点，这些目标节点会自动并行执行：

```python
workflow = Workflow(id="parallel_demo", name="并行示例")

# 定义节点
workflow.add_node(LLMNode(id="start", system_prompt="开始处理"))
workflow.add_node(LLMNode(id="sentiment", system_prompt="分析情感倾向"))
workflow.add_node(LLMNode(id="keywords", system_prompt="提取关键词"))
workflow.add_node(LLMNode(id="summary", system_prompt="生成摘要"))
workflow.add_node(LLMNode(id="merge", system_prompt="合并分析结果"))

# 设置边：start 同时连接三个分析节点（并行执行）
workflow.add_edge("__start__", "start")
workflow.add_edge("start", "sentiment")
workflow.add_edge("start", "keywords")
workflow.add_edge("start", "summary")

# 三个分析节点都指向 merge（自动等待所有并行任务完成）
workflow.add_edge("sentiment", "merge")
workflow.add_edge("keywords", "merge")
workflow.add_edge("summary", "merge")
workflow.add_edge("merge", "__end__")
```

### 并行执行规则

1. 当一个节点通过 `add_edge` 连接到多个目标时，这些目标会并行执行
2. 当多个并行节点都指向同一个后继节点时，框架会自动等待所有并行任务完成后再执行后继节点
3. 并行节点的结果会自动合并到 state 中

---

## 子工作流

在自定义节点中调用另一个工作流：

```python
# 定义子工作流
sub_workflow = Workflow(id="sub_task", name="子任务")
sub_workflow.use(LLMManager())
sub_workflow.add_node(LLMNode(id="process", system_prompt="处理子任务"))

# 主工作流中调用
@main_workflow.node("call_sub")
async def call_sub(state):
    result = await sub_workflow.run(
        inputs={"user_input": state["sub_input"]},
        thread_id=f"{state.get('thread_id')}_sub"
    )
    return {"sub_result": result["state"]["process"]}
```

---

## 工具集成

### 默认方式：`@workflow.tool` 自动注册

对于工作流内本地工具，推荐直接使用 `@workflow.tool`。  
AgentClaw 会自动创建并挂载当前工作流的本地 ToolKit。

```python
from agentclaw import Workflow, LLMNode

workflow = Workflow(id="tool_agent", name="工具智能体")

@workflow.tool
async def search(query: str, limit: int = 10) -> str:
    """
    搜索网页

    Args:
        query: 搜索关键词
        limit: 返回数量限制
    """
    return f"搜索结果: {query}, limit={limit}"

workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是智能助手，可以使用工具完成任务",
    tools=["search"],
    tool_choice="auto",
))
```

### 高级方式：`register_toolkit(...)`（复用/插件化）

当你需要跨工作流复用工具集，或从插件模块导入工具时，使用显式注册。

使用 `@toolkit.tool` 定义工具，再注册到 workflow：

```python
from agentclaw import ToolKit

toolkit = ToolKit()

@toolkit.tool
async def search(query: str, limit: int = 10) -> str:
    """
    搜索网页
    
    Args:
        query: 搜索关键词
        limit: 返回数量限制
    """
    return f"搜索结果: {query}"

@toolkit.tool
async def calculate(expression: str) -> str:
    """计算数学表达式"""
    return str(eval(expression))

# 默认合并到工作流主工具集
workflow.register_toolkit(toolkit)

# 可选：同名工具覆盖
# workflow.register_toolkit(toolkit, overwrite=True)
```

### 兼容方式：`workflow.use(toolkit)`

历史代码中的 `workflow.use(toolkit)` 依然兼容可用。

### 参数描述提取

框架支持三种方式提取参数描述（优先级从高到低）：

```python
# 方式1：手动注入（最高优先级）
@toolkit.tool(params={
    "query": {"description": "搜索关键词"},
    "limit": {"description": "返回数量限制"}
})
async def search(query: str, limit: int = 10) -> str:
    """搜索数据库"""
    ...

# 方式2：使用 Annotated 类型
from typing import Annotated

@toolkit.tool
async def search(
    query: Annotated[str, "搜索关键词"],
    limit: Annotated[int, "返回数量限制"] = 10
) -> str:
    """搜索数据库"""
    ...

# 方式3：从 docstring 提取（Google style）
@toolkit.tool
async def search(query: str, limit: int = 10) -> str:
    """
    搜索数据库
    
    Args:
        query: 搜索关键词
        limit: 返回数量限制
    """
    ...
```

### LLM 自动调用工具

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是智能助手，可以使用工具完成任务",
    tools=["search", "calculate"],  # 工具名称列表
    tool_choice="auto",             # auto / required / none
    max_tool_rounds=5,              # 最大工具调用轮数
))
```

---

## MCP 集成

MCP (Model Context Protocol) 是标准化的工具协议。

### 配置 MCP Server

创建 `mcp.json`：

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "12306": {
      "command": "npx",
      "args": ["-y", "12306-mcp"]
    },
    "fetch-sse": {
      "transport": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### 传输类型

| 类型 | 说明 | 配置示例 |
|------|------|----------|
| `stdio` | 本地进程通信（默认） | `"command": "npx", "args": [...]` |
| `sse` | Server-Sent Events | `"transport": "sse", "url": "..."` |
| `streamable_http` | HTTP Streamable | `"transport": "streamable_http", "url": "..."` |

### 方式一：LLMNode 自动调用

无需 Parallel API Key 的网页搜索与内容提取示例，请参阅
[Parallel Search MCP](../../../examples/parallel_search/README.md)。示例使用现有的
Streamable HTTP 传输，并提供工作流配置方式。

```python
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是助手，可以使用工具完成任务",
    tools=["fetch", "get-tickets"],  # MCP 工具名
    tool_choice="auto",
    max_tool_rounds=5,
))
```

### 方式二：MCPNode 直接调用

```python
from agentclaw import MCPNode

workflow.add_node(MCPNode(
    id="fetch_page",
    server="fetch",           # MCP Server 名称
    tool="fetch",             # 工具名称
    output="page_content",    # 输出到 state["page_content"]
    arguments={"url": "{target_url}"},  # 从 state 获取参数
))
```

### MCPNode 配置

| 配置 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 节点唯一标识 |
| `server` | 是 | MCP Server 名称（mcp.json 中的 key） |
| `tool` | 是 | 工具名称 |
| `output` | 是 | 输出参数名 |
| `arguments` | 否 | 工具参数，支持 `{key}` 模板 |

### MCPPipelineNode 管道节点

按顺序执行多个 MCP 工具：

```python
from agentclaw import MCPPipelineNode

workflow.add_node(MCPPipelineNode(
    id="train_query",
    steps=[
        {"server": "12306", "tool": "get-current-date", "output": "query_date"},
        {"server": "12306", "tool": "get-station-code-of-citys", 
         "arguments": {"citys": "{from_city}|{to_city}"}, "output": "station_codes"},
        {"server": "12306", "tool": "get-tickets",
         "arguments": {"date": "{query_date}", "fromStation": "{from_code}"},
         "output": "tickets"},
    ],
))
```

---

## Skills 技能系统

Skills 是 Anthropic 定义的技能规范，用于向 LLM 注入领域知识。

### 安装技能

将技能文件夹复制到项目的 `skills/` 目录即可：

```bash
# 从 GitHub 克隆技能
git clone https://github.com/example/skill-pdf.git skills/pdf

# 或直接复制
cp -r ~/downloads/skill-pdf skills/pdf
```

如果 skill 包含 `requirements.txt`，AgentClaw 会在加载或使用 skill 时自动初始化隔离环境。

### 技能目录结构

```
skills/
├── pdf/
│   ├── SKILL.md           # 技能定义（必需）
│   ├── scripts/           # 可执行脚本
│   │   ├── convert.py
│   │   └── requirements.txt
│   └── reference/         # 参考文档
│       └── api.md
└── text-utils/
    ├── SKILL.md
    └── scripts/
        └── transform.py
```

### SKILL.md 格式

```markdown
---
name: pdf
description: PDF 文档处理技能，支持转换、提取、合并等操作
---

# PDF 处理技能

## Overview

这个技能用于处理 PDF 文档...

## Instructions

当用户需要处理 PDF 时：
1. 使用 convert.py 转换格式
2. 使用 extract.py 提取内容

## Examples

**输入**: 将 report.pdf 转换为图片
**输出**: 调用 convert.py --format png report.pdf
```

### 在 LLMNode 中使用

```python
# 显式指定技能
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是文档处理助手",
    skills=["pdf", "text-utils"],  # 技能名称列表
))

# 自动匹配技能（根据 user_input 匹配相关技能）
workflow.add_node(LLMNode(
    id="agent",
    system_prompt="你是智能助手",
    skills="*",  # 自动匹配
))
```

### 技能环境

技能可以有独立的 Python 虚拟环境：

```python
# skills/pdf/scripts/requirements.txt
pdf2image==1.16.3
PyPDF2==3.0.1
```

框架自动：
1. 检测 `requirements.txt`
2. 创建隔离的虚拟环境
3. 安装依赖
4. 执行脚本时使用该环境

---

## 文档解析

### DocumentNode

将各种文档格式转换为 Markdown：

```python
from agentclaw import DocumentNode

workflow.add_node(DocumentNode(
    id="parse_doc",
    input_key="document",      # state 中文档路径的 key
    output_key="doc_content",  # 解析结果存储的 key
    include_metadata=True,     # 是否包含元数据
    max_length=10000,          # 最大输出长度
))
```

### 支持格式

- PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx)
- HTML, 图片 (OCR), 音频 (转录)

### DocumentExtractNode

解析并提取特定信息：

```python
from agentclaw import DocumentExtractNode

workflow.add_node(DocumentExtractNode(
    id="extract",
    input_key="document",
    extract_sections=["摘要", "结论"],  # 提取指定章节
    extract_tables=True,                 # 提取表格
))
```

### 依赖安装

```bash
pip install markitdown[all]
```

---

## 提示词管理

提示词通过 `LLMNode` 的 `system_prompt` 参数直接定义，框架会自动管理。

### 基础用法

```python
workflow.add_node(LLMNode(
    id="chat",
    system_prompt="你是一个友好的助手，帮助用户解答问题。"
))
```

### 使用变量

提示词支持 `{variable}` 语法，自动从 state 填充：

```python
workflow.add_node(LLMNode(
    id="summarize",
    system_prompt="基于以下分析结果生成摘要：{analysis}"
))
```

### 提示词热更新（生产环境）

配置数据库后，提示词支持通过 Admin API 运行时更新：

```bash
# 更新提示词
curl -X PUT http://localhost:8000/admin/prompts/my_workflow/chat \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "新的提示词内容"}'

# 重置为默认值
curl -X POST http://localhost:8000/admin/prompts/my_workflow/chat/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 模型配置

### models.json 完整配置

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

### 模型参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | string | 必填 | 模型唯一标识 |
| `model` | string | 必填 | 模型名称 |
| `api_key` | string | 必填 | API 密钥 |
| `base_url` | string | 必填 | API 基础 URL |
| `type` | string | "chat" | 模型类型：chat / embedding / rerank |
| `supports_vision` | boolean | false | 该 chat 模型是否支持图片输入 |
| `temperature` | float | 0.1 | 温度参数（0-2） |
| `max_tokens` | int | 8192 | 最大输出 token 数 |
| `timeout` | int | 240 | 请求超时时间（秒） |

### 参数优先级

```
models.json (模型默认值) < LLMNode.model_params (节点覆盖)
```

```python
# 节点级别覆盖
workflow.add_node(LLMNode(
    id="classify",
    system_prompt="分类意图",
    model_params={"temperature": 0.0, "max_tokens": 100}
))
```

### 自动降级

```python
from agentclaw import LLMManager

llm = LLMManager(
    default="qwen3-next",       # 默认模型
    fallback="qwen3-32b",       # 降级模型
    auto_fallback=True,         # 启用自动降级
    fallback_threshold=3,       # 连续失败 3 次后降级
    fallback_duration=300,      # 降级持续 5 分钟后尝试恢复
)
workflow.use(llm)
```

### 节点级降级

```python
workflow.add_node(LLMNode(
    id="critical_task",
    system_prompt="重要任务",
    fallback_model_id="backup-model",  # 节点级降级模型
    auto_fallback=True,
    fallback_threshold=2,
))
```

---

## 日志系统

### 基础使用

```python
from agentclaw.logger.config import get_logger, setup_logging

# 初始化日志
setup_logging(
    level="INFO",              # DEBUG / INFO / WARNING / ERROR
    log_file="logs/app.log",   # 可选：输出到文件
    format_style="simple",     # simple / detailed
)

# 在模块中使用
logger = get_logger(__name__)
logger.info("工作流开始执行")
```

### 动态调整级别

```python
from agentclaw.logger.config import set_log_level

set_log_level("DEBUG")
```

---

## 边注册

### 特殊节点

| 节点名 | 说明 |
|--------|------|
| `__start__` | 工作流入口点 |
| `__end__` | 工作流结束点 |

### 手动连接（必需）

```python
workflow = Workflow(id="demo", name="Demo")

workflow.add_node(LLMNode(id="A", ...))
workflow.add_node(LLMNode(id="B", ...))

workflow.add_edge("__start__", "A")
workflow.add_edge("A", "B")
workflow.add_edge("B", "__end__")
```

### 条件边

```python
workflow.add_conditional_edge(
    source="classify",
    condition=lambda state: state.get("result", {}).get("intent", "default"),
    targets={
        "question": "answer",
        "complaint": "handle",
        "default": "__end__"
    }
)
```

---

## 服务部署

### 快速启动

```bash
# 初始化项目
agentclaw init my-project
cd my-project

# 启动服务
agentclaw serve
```

或使用 Python：

```python
# server.py
import agents  # 导入 agents 模块，自动注册所有工作流

from agentclaw import AgentClawServer

server = AgentClawServer()
server.run()
```

### 发布工作流

```python
from agentclaw import WorkflowRegistry

WorkflowRegistry.register(workflow, stream=True)

server = AgentClawServer()
server.run()
```

### API 调用

```bash
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Authorization: Bearer <WORKFLOW_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my_workflow",
    "response_mode": "blocking",
    "conversation_id": "session_001",
    "user": "你好",
    "user_id": "user_123",
    "inputs": {"locale": "zh-CN"}
  }'
```

`<WORKFLOW_API_KEY>` 可以是全局环境变量 `WORKFLOW_API_KEY`，也可以是在该工作流开启 **发布 API** 后使用其独立 `workflow_api_key`。全局 Key 可以执行所有工作流；工作流级密钥只允许执行对应工作流，且不会获得调度器、渠道推送、文件列表、Dashboard 管理等 Admin 能力。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `workflow_id` | string | 是 | 工作流 ID |
| `user` | string | 否 | 用户消息文本（对话输入 / HumanNode 续跑输入） |
| `user_id` | string | 否 | 调用方身份元数据 |
| `response_mode` | string | 否 | `blocking` 或 `streaming`，默认 `blocking` |
| `conversation_id` | string | 否 | 会话 ID，用于多轮对话 |
| `inputs` | object | 否 | 结构化工作流输入 |

说明：
- 推荐使用 `response_mode`；当前版本仍兼容旧字段 `mode`
- 若工作流配置了 `user_input="<field>"`，当 `inputs["<field>"]` 缺失时，顶层 `user` 会自动映射到该字段。
- 若同时传 `user` 与 `inputs["<field>"]`，两者必须一致，否则返回 `400 INVALID_REQUEST`。

### 响应格式

非流式响应：

```json
{
    "outputs": [],
    "state": {
        "user_input": "你好",
        "response": "您好！有什么可以帮您的？"
    },
    "metadata": {
        "workflow_id": "my_workflow",
        "thread_id": "session_001",
        "duration_ms": 1234
    }
}
```

流式响应（SSE）：

```
event: start
data: {"type": "start", "workflow_id": "my_workflow"}

event: output
data: {"type": "output", "node": "chat", "data": "你好"}

event: result
data: {"type": "result", "data": {...}}

event: end
data: {"type": "end"}
```

### 匿名公开 Agent

如果希望用户无需登录即可打开一个对话页面，需要在 Dashboard 的工作流配置中开启「公开发布」。默认不公开；内置智能体不能公开分享。

公开发布使用独立的 `share_token` 和同源浏览器会话，不使用 `WORKFLOW_API_KEY`。复制出的链接形如：

```text
http://localhost:8000/dashboard/agent/my_workflow?share_token=<PUBLIC_SHARE_TOKEN>
```

公开页会自动完成以下调用：

1. `GET /api/public/workflows/{workflow_id}?share_token=...` 读取展示所需的最小工作流信息。
2. `POST /api/public/workflows/{workflow_id}/session?share_token=...` 建立短期 HttpOnly 会话 cookie。
3. `POST /api/public/workflows/{workflow_id}/run` 使用同源 cookie 和 `X-AgentClaw-Public-Session: 1` 执行工作流。

匿名公开执行有几条限制：

- 文件附件和文件型输入不可用。
- 请求级模型切换、`user_id` 和人工确认设置会被忽略。
- `rate_limit` 只作用于匿名公开执行和公开会话 API，可写成 `10/min`、`100/hour`。
- `public_conversation_limit` 与 `public_message_limit` 控制每客户端公开会话数量和单次会话消息数量。
- 如果公网部署在可信反向代理后面，且代理会清理外部传入的 `X-Forwarded-*` 头，再开启 `AGENTCLAW_TRUST_PROXY_HEADERS=1`。

### 生产环境配置

```bash
# .env
ADMIN_TOKEN=your-secure-token

# PostgreSQL（可选）
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=password
PG_DATABASE=agentclaw

# Redis（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 数据库依赖说明

AgentClaw 可以在无数据库的情况下运行，但部分功能会受限：

| 功能 | 无 PostgreSQL | 无 Redis |
|------|--------------|----------|
| 基础工作流执行 | ✅ 正常 | ✅ 正常 |
| 多轮对话（单次会话） | ✅ 正常 | ✅ 正常 |
| 多轮对话（跨会话持久化） | ❌ 不可用 | ✅ 正常 |
| 执行追踪/日志 | ❌ 不可用 | ✅ 正常 |
| Admin Dashboard | ⚠️ 仅工作流列表可用 | ✅ 正常 |
| 提示词热更新 | ❌ 不可用 | ⚠️ 单实例可用，多实例需 Redis |
| LangGraph 引擎 | ❌ 需要 PostgreSQL 做 Checkpointer | ✅ 正常 |
| MCP 集成 | ✅ 正常 | ✅ 正常 |
| Skills 技能系统 | ✅ 正常 | ✅ 正常 |

说明：
- 无数据库时使用 builtin 引擎，支持完整的工作流功能
- MCP 和 Skills 不依赖数据库，完全基于本地文件和配置
- LangGraph 引擎需要 PostgreSQL 作为状态检查点存储（Checkpointer）

建议：
- 开发环境：可不配置数据库，使用 builtin 引擎
- 生产环境：建议配置 PostgreSQL，用于追踪和持久化

---

## Admin Dashboard

Admin Dashboard 是可视化管理界面，用于监控工作流执行、管理提示词、查看追踪日志等。

### 启动前端

```bash
# 进入前端目录
cd agentclaw/admin-dashboard

# 安装依赖（首次）
npm install

# 开发模式启动
npm run dev
```

默认访问地址：http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录，可部署到任意静态服务器。

### 功能概览

| 功能 | 说明 | 依赖 |
|------|------|------|
| 工作流列表 | 查看已注册的工作流 | 无 |
| 工作流详情 | 查看节点结构和配置 | 无 |
| 执行追踪 | 查看执行日志和耗时 | PostgreSQL |
| 提示词管理 | 在线编辑和热更新提示词 | PostgreSQL |
| Agent 对话 | 在线测试工作流 | 无 |

### 配置后端地址

编辑 `agentclaw/admin-dashboard/src/api/index.js`：

```javascript
const API_BASE = 'http://localhost:8000'  // 修改为你的后端地址
```

---

## 定时任务

定时任务模块为工作流提供自动化调度能力，支持 cron 表达式、间隔触发和一次性触发。

### 触发器类型

| 类型 | 说明 | 配置示例 |
| ---- | ---- | -------- |
| `cron` | Cron 表达式 | `"expression": "0 9 * * 1-5"` (周一到周五 9 点) |
| `interval` | 固定间隔 | `"minutes": 30` (每 30 分钟) |
| `date` | 一次性定时 | `"run_date": "2026-03-20T09:00:00"` |

### 创建定时任务

通过 API 创建：

```bash
curl -X POST http://localhost:8000/api/scheduler/jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日报表",
    "workflow_id": "report_workflow",
    "trigger": {
      "type": "cron",
      "expression": "0 9 * * *",
      "timezone": "Asia/Shanghai"
    },
    "inputs": {
      "user_input": "生成今日报表"
    },
    "config": {
      "timeout": 600,
      "retry_count": 2
    }
  }'
```

### 任务管理

| 操作 | API | 说明 |
| ---- | --- | ---- |
| 列取任务 | `GET /api/scheduler/jobs` | 支持 `status` 筛选 |
| 任务详情 | `GET /api/scheduler/jobs/{id}` | 包含下次执行时间 |
| 更新任务 | `PUT /api/scheduler/jobs/{id}` | 部分更新 |
| 删除任务 | `DELETE /api/scheduler/jobs/{id}` | |
| 暂停 | `POST /api/scheduler/jobs/{id}/pause` | |
| 恢复 | `POST /api/scheduler/jobs/{id}/resume` | |
| 手动触发 | `POST /api/scheduler/jobs/{id}/trigger` | 立即执行一次 |

### 执行记录

每次执行自动记录状态、耗时、输入输出和错误信息：

```bash
# 查看执行历史
curl http://localhost:8000/api/scheduler/jobs/{id}/executions \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 查看某次执行详情
curl http://localhost:8000/api/scheduler/jobs/{id}/executions/{eid} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

执行状态：`pending` → `running` → `success` / `failed` / `timeout`

### Webhook 触发

任务可配置 Webhook，允许外部系统通过 HTTP 请求触发执行：

```bash
# 创建任务时启用 webhook
curl -X POST http://localhost:8000/api/scheduler/jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "外部触发任务",
    "workflow_id": "my_workflow",
    "trigger": {"type": "cron", "expression": "0 9 * * *"},
    "inputs": {"user_input": "默认输入"},
    "webhook": {
      "enabled": true,
      "secret": "your-secret-key",
      "allow_input_override": true
    }
  }'

# 通过 webhook 触发（可覆盖 inputs）
curl -X POST http://localhost:8000/api/scheduler/jobs/{id}/webhook \
  -H "X-Webhook-Secret: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "webhook 传入的参数"}'
```

- `X-Webhook-Secret` 必须与配置的 `secret` 一致，否则返回 `403`
- Webhook 未启用时返回 `400`
- `allow_input_override` 为 `true` 时，请求体作为 inputs 覆盖

### 任务配置

```python
{
    "timeout": 300,        # 执行超时（秒）
    "retry_count": 3,      # 失败重试次数
    "retry_interval": 60,  # 重试间隔（秒），指数退避
    "concurrency": "skip", # skip（跳过）| queue（排队）| parallel（并行）
    "max_instances": 1     # 最大并发实例数
}
```

### 并发控制

- **skip**（默认）：如果任务正在运行，跳过本次执行
- **queue**：排队等待上一次完成
- **parallel**：允许并行执行（需设置 `max_instances`）

多进程部署时（`uvicorn --workers N`），通过 PostgreSQL advisory lock 保证同一任务不被多个进程同时触发。

### Admin Dashboard 管理

在 Admin Dashboard 的「定时任务」页面可以：

- 查看所有任务列表和状态
- 通过可视化 Cron 构建器创建任务（支持日历选择、星期选择、时间选择）
- 查看任务详情和执行历史
- 暂停/恢复/手动触发/删除任务
- 查看和复制 Webhook URL

### 依赖

定时任务模块需要 PostgreSQL 用于任务持久化和分布式锁。相关依赖：

```toml
apscheduler = "^3.10.0"
croniter = "^2.0.0"
```

---

## CLI 命令

### 项目管理

```bash
# 初始化项目
agentclaw init [path]

# 启动项目
agentclaw up [-p PORT] [-h HOST] [-d PROJECT_DIR] [--reload] [--mode docker|remote]

# 启动服务
agentclaw serve [-p PORT] [-h HOST] [-d PROJECT_DIR] [--reload]
```

---

## 配置参考

### LLMNode 配置

| 配置 | 默认值 | 说明 |
|-----|-------|------|
| `id` | 必填 | 节点名称 |
| `system_prompt` | None | 系统提示词 |
| `user_prompt` | None | 用户消息模板 |
| `output_key` | id | 输出存储键 |
| `output_format` | "text" | text / json |
| `output_to_user` | False | 是否输出给用户 |
| `model_id` | None | 指定模型 |
| `model_params` | None | 模型参数覆盖 |
| `stream` | False | 流式输出 |
| `use_context` | True | 加载历史消息 |
| `save_to_context` | True | 保存对话到历史 |
| `max_context_messages` | 20 | 最大历史条数 |
| `tools` | None | 工具名称列表 |
| `tool_choice` | "auto" | auto / required / none |
| `max_tool_rounds` | None | 最大工具调用轮数（默认继承环境变量 `MAX_TOOL_ROUNDS`） |
| `skills` | None | 技能列表或 "*" 自动匹配 |
| `enable_builtin_skills` | False | 启用内置 skills（如 agent_creator） |
| `enable_builtin_tools` | False | 启用内置工具（包含任务规划工具） |
| `agent_style` | "default" | default / agentic |
| `images_key` | "" | 图片在 state 中的 key |
| `inject_files` | None | 是否将 `__files__` 自动注入提示词 |
| `enable_memory` | False | 是否注入当前工作流的 `memory.md` |
| `fallback_model_id` | None | 节点级降级模型 |
| `auto_fallback` | None | 节点级自动降级开关 |
| `fallback_threshold` | None | 节点级失败阈值 |
| `enable_compression` | True | 启用上下文压缩 |
| `compression_threshold` | 100000 | 压缩阈值（token数） |
| `compression_model` | None | 压缩所用模型（默认使用当前模型） |

### HumanNode 配置

| 配置 | 默认值 | 说明 |
|-----|-------|------|
| `id` | 必填 | 节点名称 |
| `feedback_field` | "feedback" | 等待用户提供的字段 |
| `interrupt` | True | 是否中断等待 |
| `save_to_context` | True | 保存用户输入到对话历史 |

### Workflow 配置

| 配置 | 默认值 | 说明 |
|-----|-------|------|
| `id` | 必填 | 唯一标识 |
| `name` | 必填 | 显示名称 |
| `version` | "1.0.0" | 版本号 |
| `description` | "" | 描述 |
| `timeout` | 300 | 超时时间（秒） |
| `inputs` | None | 输入参数定义 |
| `user_input` | None | 用户输入字段名 |
| `auth_required` | False | 预留字段，当前个人版不生效 |
| `allowed_roles` | None | 预留字段，当前个人版不做角色校验 |
| `rate_limit` | None | Public Agent 匿名执行/公开会话限流，如 `10/min` |
| `public_share_enabled` | False | 是否允许匿名公开发布，默认关闭 |
| `public_share_token` | None | 公开分享 token，开启公开发布时自动生成 |
| `api_published` | True | 是否允许使用该工作流独立 API Key 调用 `/api/workflow/run`；不影响全局 `WORKFLOW_API_KEY` |
| `workflow_api_key` | None | 当前工作流独立执行密钥 |
| `safe_guard_apply_api` | False | 是否在该工作流 API 调用前检查用户输入 |
| `safe_guard_apply_public` | True | 是否在该工作流公开智能体、公开房间和玩家聊天中检查用户输入 |
| `public_conversation_limit` | 20 | 每客户端公开会话数量上限 |
| `public_message_limit` | 200 | 公开会话单次消息数量上限 |
| `inject_as_agentic_capability` | True | 是否把工作流名称、描述与输入参数注入内置智能体能力目录，用于复用现有能力；关闭后不影响直接执行 |
| `tracing` | True | 启用追踪 |
| `publish_as_mcp` | False | 发布为 MCP Server |

说明：`auth_required` 和 `allowed_roles` 是为后续多用户版本保留的字段。当前公网部署时，请依赖 `ADMIN_TOKEN`、Workflow API Key、公开发布开关和限流/配额来控制访问。

### 环境变量

| 变量 | 说明 |
|------|------|
| `ADMIN_TOKEN` | Admin API 认证 Token |
| `WORKFLOW_API_KEY` | 全局工作流执行 Bearer Key，不具备 Admin 权限，可执行所有工作流 |
| `MCP_TOKEN` | MCP 鉴权令牌，通过 `Authorization: Bearer <MCP_TOKEN>` 发送 |
| `PG_HOST` | PostgreSQL 主机 |
| `PG_PORT` | PostgreSQL 端口；Docker 模式下也是宿主机映射端口 |
| `PG_USER` | PostgreSQL 用户 |
| `PG_PASSWORD` | PostgreSQL 密码 |
| `PG_DATABASE` | PostgreSQL 数据库 |
| `REDIS_HOST` | Redis 主机 |
| `REDIS_PORT` | Redis 端口；Docker 模式下也是宿主机映射端口 |
| `MINIO_API_PORT` | Docker 模式下 MinIO API 宿主机映射端口 |
| `MINIO_CONSOLE_PORT` | Docker 模式下 MinIO Console 宿主机映射端口 |
| `MILVUS_PORT` | Docker 模式下 Milvus gRPC/API 宿主机映射端口 |
| `MILVUS_HTTP_PORT` | Docker 模式下 Milvus HTTP/metrics 宿主机映射端口 |
| `ADMINER_PORT` | Docker 模式下 Adminer 宿主机映射端口 |
| `AGENTCLAW_MCP_PROXY` | 远程 MCP 专用代理地址 |
| `AGENTCLAW_TRUST_PROXY_HEADERS` | 是否信任反向代理传入的 `X-Forwarded-*`，默认关闭 |
| `AGENTCLAW_CONTENT_SECURITY_POLICY` | 覆盖默认 CSP 安全头，留空使用内置策略 |
| `AGENTCLAW_DUMP_LLM_FAILURE_PAYLOAD` | 是否 dump 失败的 LLM 请求载荷，默认关闭 |
| `MAX_TOOL_ROUNDS` | 最大工具调用轮数（默认 0，表示不限制） |
| `MAX_CONTEXT_MESSAGES` | 最大历史消息条数（默认 0，表示不限制） |
| `TOOL_RESULT_MAX_LENGTH` | 工具结果最大长度（默认 20000） |
| `SCHEDULER_TIMEZONE` | 定时任务时区（默认 Asia/Shanghai） |
| `SCHEDULER_MAX_WORKERS` | 定时任务执行线程数（默认 10） |

---

## 错误处理

### 节点级错误策略

```python
from agentclaw import LLMNode, ErrorStrategy

LLMNode(
    id="risky_call",
    system_prompt="...",
    on_error=ErrorStrategy.RETRY,   # ABORT / SKIP / RETRY / FALLBACK
    max_retries=3,
)
```

### 工作流级异常

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
    print("工作流超时")
except WorkflowCancelledError:
    print("工作流被取消")
except NodeExecutionError as e:
    print(f"节点 {e.node_id} 执行失败")
```

---

## 下一步

- [API 参考](./api_reference.md) - 完整 API 文档
- [最佳实践](./best_practices.md) - 推荐模式
