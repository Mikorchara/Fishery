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
        self.api_key = config.LLM_API_KEY
        self.base_url = config.LLM_BASE_URL
        self.model = config.LLM_MODEL

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

        self.kb = EelKnowledgeBase()
        self.rag = RAGEngine()
        _log.info("RAG 引擎就绪: %d 个知识块已索引", len(self.rag.chunks))

        self._base_system_prompt = (
            "你是一位资深的水产养殖专家，尤其专精于鳗鲡工厂化养殖。"
            "你会根据用户提供的传感器数据和鳗鲡养殖专业知识，"
            "进行环境评估、风险预警和管理建议。"
            "请使用简洁、专业的中文回答，优先使用 Markdown 格式（加粗、列表、表格）。"
            "如果数据为 '--'，说明传感器未连接或未获取到数据。"
            "回答时优先引用鳗鲡养殖的具体参数标准，而非泛泛而谈。"
        )

    def _format_chunks(self, chunks):
        """将检索到的知识块格式化为 LLM 可读文本。"""
        lines = []
        for text, ctype, score in chunks:
            lines.append(f"[{ctype}] (相关度 {score:.2f}) {text}")
        return "\n".join(lines)

    @staticmethod
    def _extract_reply(completion):
        """从 completion 提取回复文本（兼容 thinking 模式：content 可能为空，需回退 reasoning_content）。"""
        import re
        msg = completion.choices[0].message
        content = (getattr(msg, "content", "") or "").strip()
        if not content:
            content = (getattr(msg, "reasoning_content", "") or "").strip()
        # 清除可能残留的 thinking 块标记
        content = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.S).strip()
        return content or "（模型未返回有效回答，请稍后重试）"

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
                max_tokens=1024,
                stream=False,
            )
            return self._extract_reply(completion)
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
                temperature=0.7,
                max_tokens=1024,
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}}
            )
            return self._extract_reply(completion)
        except Exception as e:
            _log.error("LLM Chat Error: %s", e)
            return f"对话功能暂时不可用: {str(e)}"


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
