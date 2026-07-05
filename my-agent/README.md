# my-agent：从零搭建你的 Coding Agent

> 这是你第1章-第6章的核心产出目录。每章实现一个模块，最终第6章拼装成完整 Agent。

## 目录结构

```
my-agent/
├── llm.py              # 第1章：LLM 客户端
├── tools.py            # 第2章：ToolRegistry
├── agent.py            # 第3章：Agent 主循环
├── context.py          # 第4章：ContextManager
├── memory.py           # 第4章：Memory
├── coding_tools/       # 第5章：具体工具实现
│   ├── __init__.py
│   ├── read.py
│   ├── write.py
│   ├── edit.py
│   ├── list_dir.py
│   └── bash.py
├── main.py             # 第6章：组装入口
└── tests/              # 各章节的测试用例
    ├── test_llm.py
    ├── test_tools.py
    ├── test_agent.py
    ├── test_context.py
    ├── test_memory.py
    └── test_coding_tools.py
```

## 搭建路线

| 章节 | 产出文件 | 核心接口 |
|-----|---------|---------|
| 1 | `llm.py` | `LLMClient.chat()` / `.chat_stream()` / `.count_tokens()` |
| 2 | `tools.py` | `ToolRegistry.register()` / `.to_schemas()` / `.invoke()` |
| 3 | `agent.py` | `Agent.run()` — LLM + Tools + Loop |
| 4 | `context.py` + `memory.py` | `ContextManager.compress()` + `Memory.add/search()` |
| 5 | `coding_tools/*.py` | 5 个工具函数注册到 ToolRegistry |
| 6 | `main.py` | 把所有零件拼起来，跑通一个真任务 |

## 验证方式

```bash
cd my-agent
python -m pytest tests/ -v
```

每章只需要让当前章节的测试通过即可。

## 新增:
流式传输，沙箱隔离，webUI

详见
my-agent-v2