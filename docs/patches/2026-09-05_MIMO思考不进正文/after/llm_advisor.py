import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
import config
from knowledge.knowledge_base import EelKnowledgeBase, RAGEngine

_log = logging.getLogger("advisor")


class FisheryAdvisor:
    def __init__(self):
        self.kb = EelKnowledgeBase()
        self.rag = RAGEngine()
        _log.info("RAG 引擎就绪: %d 个知识块已索引", len(self.rag.chunks))

        # 初始使用系统默认（config.py / .env）；启用某已存方案由 app 层 reconfigure 热切换
        self.reconfigure(config.LLM_BASE_URL, config.LLM_API_KEY, config.LLM_MODEL)

        self._base_system_prompt = (
            "你是一位资深的水产养殖专家，尤其专精于鳗鲡工厂化养殖。"
            "你会根据用户提供的传感器数据和鳗鲡养殖专业知识，"
            "进行环境评估、风险预警和管理建议。"
            "请使用简洁、专业的中文回答，优先使用 Markdown 格式（加粗、列表、表格）。"
            "如果数据为 '--'，说明传感器未连接或未获取到数据。"
            "回答时优先引用鳗鲡养殖的具体参数标准，而非泛泛而谈。"
        )

    def reconfigure(self, base_url, api_key, model):
        """运行时热切换 LLM 服务：换一套「地址 + Key + 模型」立即生效，无需重启。

        - api_key 为空 → self.client 置 None，调用方会返回“LLM 未启用”提示；
        - 传回 config 的默认三件套即回落到系统默认。
        """
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        try:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key) if self.api_key else None
        except Exception as e:
            _log.error("创建 LLM client 失败: %s", e)
            self.client = None

    def _extra_no_thinking(self):
        """返回“关闭模型思考”所需的 extra_body 参数；无法关闭的模型返回 None。

        2026-09-05：现阶段默认全关思考（省时省 token）。思考开关做成可选项见 ROADMAP。
        - DeepSeek V4 系：思考模式可开关 → thinking.disabled
        - Qwen3.x 系：混合思考模型 → enable_thinking=False
        - MiMo-V2.5：平台暂未提供公开关闭参数 → 保持原样（该模型带“深度思考”属性）
        """
        m = (self.model or "").lower()
        if m.startswith("deepseek-v4"):
            return {"thinking": {"type": "disabled"}}
        if m.startswith("qwen"):
            return {"enable_thinking": False}
        return None

    def _format_chunks(self, chunks):
        """将检索到的知识块格式化为 LLM 可读文本。"""
        lines = []
        for text, ctype, score in chunks:
            lines.append(f"[{ctype}] (相关度 {score:.2f}) {text}")
        return "\n".join(lines)

    # ---------- 诊断模式 ----------

    def get_advice(self, sensor_data):
        if self.client is None:
            return "⚠️ LLM 功能未启用：请设置 DEEPSEEK_API_KEY 环境变量"
        try:
            temp = sensor_data.get("temp", "--")
            ph = sensor_data.get("ph", "--")
            oxy = sensor_data.get("oxygen", "--")

            # 1. 规则诊断（永远注入，体积小且关键）
            rule_guide = self.kb.diagnostic_guide(temp, ph, oxy)

            # 2. RAG 检索：根据传感器状态检索相关知识块
            rag_query = f"水温{temp} pH{ph} 溶解氧{oxy} 养殖管理建议"
            rag_chunks = self.rag.retrieve(rag_query, top_k=4)
            rag_text = self._format_chunks(rag_chunks)

            user_content = (
                f"当前鱼塘实时采样数据：\n"
                f"1. 水温: {temp} °C\n"
                f"2. pH值: {ph}\n"
                f"3. 溶解氧: {oxy} mg/L\n\n"
                f"---\n"
                f"## 当前数据诊断\n\n{rule_guide}\n\n"
                f"---\n"
                f"## 相关知识库参考\n\n{rag_text}\n\n"
                f"---\n"
                f"请结合以上数据、诊断和知识参考，对当前养殖环境进行综合评估，"
                f"给出具体的管理建议和风险预警。"
            )

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._base_system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                top_p=0.95,
                max_tokens=config.LLM_REPORT_MAX_TOKENS,
                stream=False,
                # 2026-09-05：默认关闭思考 → 必须放 extra_body（SDK 非标准参数不能展开成顶层参数）
                extra_body=self._extra_no_thinking() or {},
            )
            return completion.choices[0].message.content
        except Exception as e:
            _log.error("LLM Advisor Error: %s", e)
            return f"诊断过程出现异常: {str(e)}"

    # ---------- 自由对话模式 ----------

    def ask_question(self, question, sensor_data):
        if self.client is None:
            return "⚠️ LLM 功能未启用：请设置 DEEPSEEK_API_KEY 环境变量"
        try:
            temp = sensor_data.get("temp", "--")
            ph = sensor_data.get("ph", "--")
            oxy = sensor_data.get("oxygen", "--")

            context_data = f"(当前环境参考：水温{temp}℃, pH{ph}, 溶解氧{oxy}mg/L)"

            # 1. 规则诊断
            rule_guide = self.kb.diagnostic_guide(temp, ph, oxy)

            # 2. RAG 检索：用用户问题 + 传感器数据组合查询
            rag_query = f"{question} 水温{temp} pH{ph} 溶解氧{oxy}"
            rag_chunks = self.rag.retrieve(rag_query, top_k=5)
            rag_text = self._format_chunks(rag_chunks)

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._base_system_prompt},
                    {"role": "user", "content": (
                        f"{context_data}\n"
                        f"---\n"
                        f"## 当前数据诊断\n\n{rule_guide}\n\n"
                        f"---\n"
                        f"## 相关知识库参考（RAG 检索）\n\n{rag_text}\n\n"
                        f"---\n"
                        f"用户的问题是：{question}"
                    )}
                ],
                # 2026-09-05：默认关闭思考 → 必须放 extra_body（SDK 非标准参数不能展开成顶层参数）
                extra_body=self._extra_no_thinking() or {},
                temperature=0.7,
                max_tokens=config.LLM_CHAT_MAX_TOKENS,
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception as e:
            _log.error("LLM Chat Error: %s", e)
            return f"对话功能暂时不可用: {str(e)}"

    # ---------- 流式（打字机）模式 ----------
    # 与上方非流式 get_advice / ask_question 构造保持一致，仅 stream=True + yield，供 app.py 的 SSE 端点使用。
    # 非流式方法保留（旧接口/回退）。2026-09-05 应用内对话与报告已切流式。

    def stream_advice(self, sensor_data):
        """诊断报告流式：逐段 yield 正文；结尾可能追加“被截断”提示。"""
        if self.client is None:
            yield "⚠️ LLM 功能未启用：请设置 DEEPSEEK_API_KEY 环境变量"
            return
        try:
            temp = sensor_data.get("temp", "--")
            ph = sensor_data.get("ph", "--")
            oxy = sensor_data.get("oxygen", "--")
            rule_guide = self.kb.diagnostic_guide(temp, ph, oxy)
            rag_chunks = self.rag.retrieve(f"水温{temp} pH{ph} 溶解氧{oxy} 养殖管理建议", top_k=4)
            rag_text = self._format_chunks(rag_chunks)
            user_content = (
                f"当前鱼塘实时采样数据：\n1. 水温: {temp} °C\n2. pH值: {ph}\n3. 溶解氧: {oxy} mg/L\n\n"
                f"---\n## 当前数据诊断\n\n{rule_guide}\n\n"
                f"---\n## 相关知识库参考\n\n{rag_text}\n\n"
                f"---\n请结合以上数据、诊断和知识参考，对当前养殖环境进行综合评估，给出具体的管理建议和风险预警。"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self._base_system_prompt},
                          {"role": "user", "content": user_content}],
                temperature=0.7, top_p=0.95,
                max_tokens=config.LLM_REPORT_MAX_TOKENS, stream=True,
                extra_body=self._extra_no_thinking() or {})
            # 2026-09-05 修订：只发正式正文 content；思考(reasoning_content)不进正文——
            # 否则“无法关思考”的模型（如 MiMo）会把思考草稿当回答显示。
            truncated = False
            content_seen = False
            for chunk in resp:
                if not chunk.choices:
                    continue
                d = chunk.choices[0].delta
                piece = getattr(d, "content", None)
                if piece:
                    content_seen = True
                    yield str(piece)
                if chunk.choices[0].finish_reason == "length":
                    truncated = True
            if truncated:
                yield "\n\n> ⚠️ 内容超长被截断，可让我分点续写。"
            elif not content_seen:
                yield "\n\n> ⚠️ 该模型未输出正式正文（思考过长或平台把正文放其它字段），建议换 DeepSeek/Qwen 或缩短问题。"
        except Exception as e:
            _log.error("LLM Advisor Stream Error: %s", e)
            yield f"诊断过程出现异常: {str(e)}"

    def stream_answer(self, question, sensor_data):
        """自由对话流式：逐段 yield 正文；结尾可能追加“被截断”提示。"""
        if self.client is None:
            yield "⚠️ LLM 功能未启用：请设置 DEEPSEEK_API_KEY 环境变量"
            return
        try:
            temp = sensor_data.get("temp", "--")
            ph = sensor_data.get("ph", "--")
            oxy = sensor_data.get("oxygen", "--")
            context_data = f"(当前环境参考：水温{temp}℃, pH{ph}, 溶解氧{oxy}mg/L)"
            rule_guide = self.kb.diagnostic_guide(temp, ph, oxy)
            rag_chunks = self.rag.retrieve(f"{question} 水温{temp} pH{ph} 溶解氧{oxy}", top_k=5)
            rag_text = self._format_chunks(rag_chunks)
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self._base_system_prompt},
                          {"role": "user", "content": (
                              f"{context_data}\n---\n## 当前数据诊断\n\n{rule_guide}\n\n"
                              f"---\n## 相关知识库参考（RAG 检索）\n\n{rag_text}\n\n"
                              f"---\n用户的问题是：{question}"
                          )}],
                temperature=0.7,
                max_tokens=config.LLM_CHAT_MAX_TOKENS, stream=True,
                extra_body=self._extra_no_thinking() or {})
            # 2026-09-05 修订：只发正式正文 content；思考(reasoning_content)不进正文——
            # 否则“无法关思考”的模型（如 MiMo）会把思考草稿当回答显示。
            truncated = False
            content_seen = False
            for chunk in resp:
                if not chunk.choices:
                    continue
                d = chunk.choices[0].delta
                piece = getattr(d, "content", None)
                if piece:
                    content_seen = True
                    yield str(piece)
                if chunk.choices[0].finish_reason == "length":
                    truncated = True
            if truncated:
                yield "\n\n> ⚠️ 内容超长被截断，可让我分点续写。"
            elif not content_seen:
                yield "\n\n> ⚠️ 该模型未输出正式正文（思考过长或平台把正文放其它字段），建议换 DeepSeek/Qwen 或缩短问题。"
        except Exception as e:
            _log.error("LLM Chat Stream Error: %s", e)
            yield f"对话功能暂时不可用: {str(e)}"


if __name__ == "__main__":
    advisor = FisheryAdvisor()
    print("\n=== RAG 检索测试 ===")
    for q in [
        "水温32度鱼不吃料怎么办",
        "鱼身上有白点是什么病",
        "pH值偏低怎么调节",
        "鳗苗阶段投喂要注意什么",
    ]:
        chunks = advisor.rag.retrieve(q, top_k=3)
        print(f"\n查询: {q}")
        for text, ctype, score in chunks:
            print(f"  [{ctype}] ({score:.2f}) {text[:100]}...")
