# 项目结构分析报告

## 1. 项目概述

这是一个基于第一代个人agent的2.0版本项目，实现了流式输出、WebUI访问。项目采用分层模块化架构，是一个教程风格的编码代理系统。

## 2. 目录结构

```
my-agent/
├── .claude/                    # Claude配置目录
├── .git/                       # Git版本控制
├── .gitignore                  # Git忽略文件
├── .mimocode/                  # MiMo配置目录
├── .venv/                      # Python虚拟环境（根目录）
├── LICENSE                     # MIT许可证
├── README.md                   # 项目说明文档
└── my-agent/                   # 主项目目录
    ├── .env                    # 环境配置文件
    ├── .pytest_cache/          # pytest缓存
    ├── .venv/                  # Python虚拟环境（子目录）
    ├── __pycache__/            # Python字节码缓存
    ├── agent.py                # 代理主循环模块
    ├── coding_tools/           # 编码工具包
    │   ├── __init__.py         # 工具注册初始化
    │   ├── bash.py             # Shell命令执行工具
    │   ├── edit.py             # 文件编辑工具
    │   ├── list_dir.py         # 目录列表工具
    │   ├── read.py             # 文件读取工具
    │   └── write.py            # 文件写入工具
    ├── context.py              # 上下文管理模块
    ├── interfaces.py           # 抽象基类定义
    ├── llm.py                  # LLM客户端模块
    ├── main.py                 # CLI入口点
    ├── memory.py               # 向量记忆模块
    ├── README.md               # 详细章节文档
    ├── requirements.txt        # 依赖列表
    ├── run_web.py              # WebUI启动脚本
    ├── test_web_ui.py          # WebUI测试文件
    ├── tools.py                # 工具注册表
    ├── web_ui.py               # Gradio Web界面
    └── WEBUI.md                # WebUI使用指南
```

## 3. 技术栈

| 技术 | 用途 | 版本要求 |
|------|------|----------|
| Python | 主要编程语言 | 3.10+ |
| OpenAI SDK | LLM API集成 | >=1.0.0 |
| tiktoken | Token计数 | >=0.5.0 |
| python-dotenv | 环境变量管理 | >=1.0.0 |
| Gradio | Web界面框架 | >=4.0.0 |
| pytest | 测试框架 | >=7.0.0 |

## 4. 架构设计

### 4.1 分层架构

```
┌─────────────────────────────────────┐
│           表示层 (Presentation)      │
│   main.py (CLI) + web_ui.py (Web)   │
├─────────────────────────────────────┤
│           代理层 (Agent)             │
│        agent.py (主循环)            │
├─────────────────────────────────────┤
│           工具层 (Tools)             │
│   tools.py + coding_tools/*         │
├─────────────────────────────────────┤
│           LLM层 (LLM)               │
│        llm.py (API客户端)           │
├─────────────────────────────────────┤
│           持久化层 (Persistence)     │
│   memory.py + context.py            │
└─────────────────────────────────────┘
```

### 4.2 核心模块功能

#### `llm.py` - LLM客户端
- 封装OpenAI兼容API
- 支持同步和流式输出
- 提供4种方法：`chat`, `chat_with_tools`, `chat_stream`, `chat_stream_with_tools`
- 使用tiktoken进行token计数

#### `tools.py` - 工具注册表
- 基于装饰器的工具注册
- 自动生成OpenAI函数调用JSON Schema
- 从函数签名和类型注解提取参数信息
- 支持工具调用和结果返回

#### `agent.py` - 代理主循环
- 实现ReAct风格的交互循环
- 支持同步`run()`和流式`run_stream()`执行
- 自动处理工具调用（单个执行或并发执行）
- 集成记忆系统和上下文管理

#### `context.py` - 上下文管理
- 基于token预算的对话压缩
- 保留系统提示和最近对话
- 使用LLM生成对话摘要

#### `memory.py` - 向量记忆
- 基于嵌入的向量存储
- 支持余弦相似度搜索
- 优雅降级：嵌入不可用时回退到关键词匹配
- 支持JSON持久化

### 4.3 工具系统

`coding_tools/` 包含5个编码工具：

| 工具 | 功能 | 安全特性 |
|------|------|----------|
| `read_file` | 读取文件内容，支持行号和分页 | 无 |
| `write_file` | 写入文件，防止意外覆盖 | 需要显式设置overwrite=True |
| `edit_file` | 精确字符串替换 | 要求唯一匹配 |
| `list_dir` | 列出目录内容 | 无 |
| `bash` | 执行Shell命令 | 危险命令过滤，输出截断，超时控制 |

### 4.4 入口点

1. **CLI REPL** - `python main.py`
   - 交互式终端会话
   - 流式输出和进度显示

2. **Web UI (直接)** - `python web_ui.py --host 0.0.0.0 --port 7860`
   - Gradio服务器
   - 双栏界面：文件树 + 聊天机器人

3. **Web UI (便捷)** - `python run_web.py`
   - 自动检查依赖
   - 使用默认配置启动

## 5. 关键设计模式

### 5.1 装饰器模式
工具注册使用装饰器自动生成Schema，简化开发。

### 5.2 代理循环模式
ReAct风格：思考 → 行动 → 观察 → 循环

### 5.3 并发执行
多个工具调用使用`ThreadPoolExecutor`并发执行（最多5个worker）。

### 5.4 优雅降级
记忆系统在嵌入API不可用时自动回退到关键词匹配。

### 5.5 流式处理
所有主要接口都支持流式输出，实现实时反馈。

## 6. 配置管理

### 6.1 环境变量 (`.env`)
```
BASE_URL=https://api.deepseek.com
API_KEY=your_api_key
MODEL_ID=deepseek-v4-flash
EMBEDDING_BASE_URL=  # 可选
EMBEDDING_API_KEY=    # 可选
EMBEDDING_MODEL=      # 可选
```

### 6.2 系统提示
代理有预定义的工作流程：
1. 先使用`list_dir`和`read_file`了解项目
2. 使用`write_file`和`edit_file`进行修改
3. 使用`bash`验证结果

## 7. 测试结构

- `test_web_ui.py` - WebUI冒烟测试（4个测试）
- `.pytest_cache` - 记录了14个测试节点ID
- `tests/`目录在文档中提到但不存在于文件系统

## 8. 部署方式

### 8.1 本地部署
```bash
cd my-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -q
python run_web.py
```