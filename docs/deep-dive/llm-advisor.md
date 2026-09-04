# llm_advisor 源码走读（新手友好）

> 目标：对着 `core/llm_advisor.py`，从第一行到最后一行，搞懂「问 AI 一句话，代码到底做了什么」。
> 前置：先看 `docs/deep-dive/llm-services.md` 的架构总览与 `docs/structure.md` 的 ② 调用链。

---

## 0. 这个文件在整个系统里是谁

```
app.py（接线员）
   └─ 把 /chat_ai、/get_ai_advice 转给 →  llm_advisor.py（本文件 = 大脑）
                                             ├─ 决定「连谁」：OpenAI(base_url, api_key, model)
                                             ├─ 决定「怎么答」：拼 prompt（人设 + 规则 + RAG）
                                             └─ 决定「答什么料」：knowledge/（本地规则+知识库）
```

它**只负责一件事**：把「用户问题 + 现场数据」变成一份发给 LLM 的材料，收回答，原样返回给 app.py。

---

## 1. 文件骨架

```
import 部分                  → 拿工具（openai SDK / config / 本地知识库）
class FisheryAdvisor:        ← 唯一的一个类
 ├─ __init__()                 出生时：建好本地引擎 + 连默认模型
 ├─ reconfigure()              换“连谁”（设置弹窗热切换用）
 ├─ _format_chunks()           把检索出的知识块拼成纯文本
 ├─ get_advice()               「生成诊断报告」入口
 ├─ ask_question()             「自由对话」入口
 └─ __main__ 测试区            不联网也能跑：只测 RAG 检索打不打得准
```

> 注意：**诊断(get_advice) 和 对话(ask_question) 几乎一模一样**，只差 3 处（见 §5 表格）。
> 先读懂其中一个，另一个就通了。

---

## 2. import 部分在干嘛

```python
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openai import OpenAI                       # 官方 SDK：真正发网络请求的“邮差”
import config                                   # 默认三件套 + 项目所有配置
from knowledge.knowledge_base import EelKnowledgeBase, RAGEngine   # 本地知识
```

- `sys.path.insert(...)`：让脚本**从项目根 import**（无论从哪运行都能找到 `config`、`knowledge`）。复制粘贴到别的项目要改层数。
- `OpenAI`：不是我们写的，是 openai 库提供的客户端；**所有“发消息给模型”的底层网络都是它干的**。
- `EelKnowledgeBase`（规则）+ `RAGEngine`（检索）：本地知识，见 `deep-dive/llm-services.md` §4。

---

## 3. 出生时的 `__init__` —— 这个“人”一上场就先备好两样东西

```python
def __init__(self):
    self.kb = EelKnowledgeBase()      # ① 本地“规则专家”：不用联网，给温度就告诉你该不该报警
    self.rag = RAGEngine()            # ② 本地“图书馆管理员”：31 个知识块，按相关度打分
    _log.info("RAG 引擎就绪: %d 个知识块已索引", len(self.rag.chunks))

    self.reconfigure(config.LLM_BASE_URL, config.LLM_API_KEY, config.LLM_MODEL)
    # ↑ 一句话：先按“系统默认”连上模型（config.py / .env）
    #   之后网页设置弹窗会再调 reconfigure() 把它换成用户选的方案

    self._base_system_prompt = (
        "你是一位资深的水产养殖专家……"   # ← 人设，固定不动，每次都发给模型
    )
```

要点：
- `kb` / `rag` 是**本地、免费、毫秒级**能力——就算没网络、没 Key，规则告警照样工作（`/check_alarm` 就走它们）。
- `self.client`（真正的模型连接）是**后来才被 reconfigure 建出来的**，不是写死在 __init__ 里。

---

## 4. `reconfigure()` —— 换“连谁”的唯一入口（本文件灵魂）

```python
def reconfigure(self, base_url, api_key, model):
    self.base_url = (base_url or "").strip().rstrip("/")   # 地址去空格、去结尾斜杠
    self.api_key  = (api_key or "").strip()
    self.model    = (model or "").strip()
    try:
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key) if self.api_key else None
    except Exception as e:
        self.client = None
```

- 三行赋值 = 记住“用哪家”；
- `self.client = OpenAI(...)` = **现场重造一个连接壳**（很轻，不发起网络请求，只是“拿着钥匙和地址待命”）；
- `api_key` 为空 → `client=None` → 后面每个方法开头都检查它，没 Key 就返回“未启用”，**不会崩**。

> 为什么“热切换”这么快？因为真正的联网只发生在 `chat.completions.create()` 那一刻，
> 换服务 = 换 `base_url/key/model` 这三个字符串 + 重建一个壳，代价几乎为零。

---

## 5. 两个入口：get_advice vs ask_question

先读差异表，再看下面任一例子的逐步流水账：

| | `get_advice()`（诊断报告） | `ask_question()`（自由对话） |
|---|---|---|
| 什么时候被点 | 「生成当前环境实时诊断报告」 | 聊天框「发送」 |
| RAG 取几块 | `top_k=4` | `top_k=5` |
| 检索词 | 固定「水温X pHX 溶氧X …」 | 用「用户问题 + 水温X pHX…」 |
| user 结尾 | “请综合评估…给出建议” | “用户的问题是：{你的话}” |
| thinking | 无（一直普通模式） | **已去掉**（2026-09-04，省 token） |
| 其它 | 一模一样：`temperature=0.7, top_p=0.95, max_tokens=1024, stream=False` |

---

## 6. 逐步走一遍 `ask_question("水温32度怎么办", mcu_data)`

> 假设 `mcu_data = {"temp":"32","ph":"7.5","oxygen":"5.2",...}`

**第 1 步：先自检**
```python
if self.client is None:
    return "⚠️ LLM 功能未启用……"     # 没 Key / 没配置 → 直接温柔劝退
```

**第 2 步：取现场数据**
```python
temp, ph, oxy = sensor_data.get("temp","--"), ...   # 取不到就用 "--"
context_data = "(当前环境参考：水温32℃, pH7.5, 溶解氧5.2mg/L)"   # 先记一行“现场”
```

**第 3 步：问本地规则专家**（不花钱）
```python
rule_guide = self.kb.diagnostic_guide("32","7.5","5.2")
# → "- 水温 32.0°C 偏高：溶氧需求增大…\n- pH 7.5 正常…\n- 溶氧 5.2 mg/L 偏低…"
```

**第 4 步：问本地图书管理员**（不花钱）
```python
rag_query  = "水温32度怎么办 水温32 pH7.5 溶解氧5.2"
rag_chunks = self.rag.retrieve(rag_query, top_k=5)   # 31 块里按 TF-IDF 打分取前 5
rag_text   = self._format_chunks(rag_chunks)
# → "[water_quality] (相关度 0.42) 水温过高时的处理办法……\n[disease] ..."
```

**第 5 步：把上面所有料拼成一份“用户消息”**
```python
messages = [
    {"role": "system", "content": self._base_system_prompt},   # 人设（养殖专家）
    {"role": "user",   "content": (
        "(当前环境参考：…)\n---\n## 当前数据诊断\n\n{rule_guide}\n\n"
        "---\n## 相关知识库参考（RAG）\n\n{rag_text}\n\n"
        "---\n用户的问题是：水温32度怎么办"                     # 最后才是你的话
    )}
]
```

**第 6 步：花钱的时刻**——真正发去模型
```python
completion = self.client.chat.completions.create(
    model=self.model,        # 连的是“当前启用”的模型（默认 deepseek-v4-flash）
    messages=messages,       # 上面拼好的材料
    temperature=0.7, top_p=0.95, max_tokens=1024, stream=False,
)
return completion.choices[0].message.content   # 把模型整段回答取出来返回
```

> **为什么 prompt 要塞那么多规则和知识？**
> 因为模型不认识你的鱼塘，也不知道你的《鳗鲡手册》。本地规则+RAG = 把“权威答案片段”先塞给它，
> 让它照着答——这就是这个项目“AI 回答靠谱”的秘密，比裸问强很多。

---

## 7. 想改东西？改哪里速查

| 想改什么 | 改哪 |
|---|---|
| 让 AI 说话口吻/人设 | `__init__` 里的 `_base_system_prompt` |
| 回答更长/更短 | `max_tokens=1024`（两处都改） |
| 更保守/更放飞 | `temperature` |
| 检索更准(塞更多料) | `top_k`（get_advice=4 / ask_question=5） |
| 让它打字机式慢慢显示 | `stream=False → True` + 路由改 SSE（尚未做，见 llm-services.md §8） |
| 让它“记住上几句” | 加历史 messages（见 llm-services.md §6 建议 3） |
| 换模型服务 | 不用改代码——网页「LLM 服务设置」 |
| 诊断/对话两个函数重复，想合并 | 可抽公共 `_compose_and_call(user_content)`；低优先级 |

---

## 8. 一个小实验：不联网也能跑

文件底部自带测试：`python core/llm_advisor.py`
它只测第 4 步的 RAG 检索准不准（不碰网络、不花 Key）。看输出里每个问题命中的知识块类型，就能判断知识库覆盖好不好。

---

> 相关：`docs/deep-dive/llm-services.md`（架构/上下文/慢的分析）、`knowledge/knowledge_base.py`（规则+RAG 实现）。
