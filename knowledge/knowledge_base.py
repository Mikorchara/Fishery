"""鳗鲡养殖知识图谱 — RAG 检索引擎 + 规则诊断。"""
import json
import os
import numpy as np


class EelKnowledgeBase:
    """规则引擎：传感器阈值诊断（不做检索，只做硬规则评估）。"""

    def __init__(self, kg_path: str = None):
        if kg_path is None:
            kg_path = os.path.join(os.path.dirname(__file__), "eel_knowledge.json")
        with open(kg_path, "r", encoding="utf-8") as f:
            self.kg = json.load(f)

    # ---------- 统一告警阈值（唯一数据源）----------

    # (level, condition_func, message_template)
    # 顺序：critical 优先在前
    ALARM_RULES = [
        # 水温
        ("critical", lambda t, p, o: t < 15,  "水温极低 ({t}°C)：停止摄食、免疫力严重下降"),
        ("warning",  lambda t, p, o: t < 20,  "水温偏低 ({t}°C)：摄食减少、生长缓慢"),
        ("critical", lambda t, p, o: t > 33,  "水温过高 ({t}°C)：热应激，需立即降温"),
        ("warning",  lambda t, p, o: t > 30,  "水温偏高 ({t}°C)：溶氧需求增大"),
        # pH
        ("critical", lambda t, p, o: p < 6.5, "pH 过低 ({p})：酸中毒风险"),
        ("warning",  lambda t, p, o: p < 7.0, "pH 偏低 ({p})"),
        ("critical", lambda t, p, o: p > 9.0, "pH 过高 ({p})：氨氮毒性剧增"),
        ("warning",  lambda t, p, o: p > 8.5, "pH 偏高 ({p})：氨氮毒性增强"),
        # 溶解氧
        ("critical", lambda t, p, o: o < 1.0, "溶氧极低 ({o} mg/L)：大面积死亡风险"),
        ("critical", lambda t, p, o: o < 3.0, "溶氧低 ({o} mg/L)：鱼群浮头、停止摄食"),
        ("warning",  lambda t, p, o: o < 5.0, "溶氧偏低 ({o} mg/L)：摄食量减少"),
    ]

    def get_alarms(self, temp, ph, oxygen):
        """返回告警列表 [(level, message), ...]，与 diagnostic_guide 共享同一套阈值。"""
        alarms = []
        try: t = float(temp)
        except (ValueError, TypeError): t = None
        try: p_val = float(ph)
        except (ValueError, TypeError): p_val = None
        try: o = float(oxygen)
        except (ValueError, TypeError): o = None

        for level, condition, template in self.ALARM_RULES:
            try:
                if condition(t, p_val, o):
                    msg = template.format(t=t, p=p_val, o=o)
                    alarms.append((level, msg))
            except TypeError:
                pass
        return alarms

    # ---------- 规则诊断（不依赖检索）----------

    def diagnostic_guide(self, temp, ph, oxygen):
        """根据传感器值生成分级预警文本。"""
        wq = self.kg["water_quality"]
        hints = []

        try:
            t = float(temp)
            if t < 15:
                hints.append(f"水温 {t}°C 极低：停止摄食、免疫力严重下降，需立即加温")
            elif t < 20:
                hints.append(f"水温 {t}°C 偏低：摄食减少、生长缓慢，建议加温至 25-30°C")
            elif t < 25:
                hints.append(f"水温 {t}°C 略低：摄食正常但未达最佳生长温度 (27-29°C)")
            elif t <= 30:
                hints.append(f"水温 {t}°C 适宜：最适生长区间，饲料转化率高")
            elif t <= 33:
                hints.append(f"水温 {t}°C 偏高：溶氧需求增大，需加强增氧")
            else:
                hints.append(f"水温 {t}°C 过高：热应激，需降温（换水、遮阳）")
        except ValueError:
            hints.append(f"水温数据无效 ({temp})")

        try:
            p = float(ph)
            if p < 6.5:
                hints.append(f"pH {p} 过低：酸中毒风险，建议换水+泼洒生石灰")
            elif p < 7.0:
                hints.append(f"pH {p} 偏酸：注意底部有机质积累，监测氨氮")
            elif p <= 8.0:
                hints.append(f"pH {p} 正常")
            elif p <= 8.5:
                hints.append(f"pH {p} 偏碱：氨氮毒性增强，如氨氮偏高需警惕")
            elif p <= 9.0:
                hints.append(f"pH {p} 偏高：氨氮毒性显著上升，建议换水+有机酸调节")
            else:
                hints.append(f"pH {p} 极高：鳃损伤风险，氨氮中毒风险极高")
        except ValueError:
            hints.append(f"pH 数据无效 ({ph})")

        try:
            o = float(oxygen)
            if o < 1.0:
                hints.append(f"溶氧 {o} mg/L 严重缺氧：浮头、死亡风险，立即全开增氧机+换水")
            elif o < 3.0:
                hints.append(f"溶氧 {o} mg/L 缺氧：停止摄食，加强增氧，停止投喂")
            elif o < 5.0:
                hints.append(f"溶氧 {o} mg/L 偏低：摄食减少，增加增氧时间")
            elif o <= 8.0:
                hints.append(f"溶氧 {o} mg/L 正常")
            else:
                hints.append(f"溶氧 {o} mg/L 充足")
        except ValueError:
            hints.append(f"溶氧数据无效 ({oxygen})")

        wq = self.kg.get("water_quality", {})
        if wq:
            hints.append("---")
            hints.append(
                f"温度适宜范围: {wq['temperature']['optimal_range'][0]}-{wq['temperature']['optimal_range'][1]}°C | "
                f"pH 适宜范围: {wq['ph']['optimal_range'][0]}-{wq['ph']['optimal_range'][1]} | "
                f"溶氧适宜范围: {wq['dissolved_oxygen']['optimal_range'][0]}-{wq['dissolved_oxygen']['optimal_range'][1]} mg/L"
            )

        return "\n".join(f"- {h}" for h in hints)


# ================================================================
# RAG 引擎
# ================================================================

def _chunk_knowledge(kg: dict):
    """将知识图谱 JSON 拆分为可检索的文本块。"""
    chunks = []

    # -- 水质参数 --
    wq = kg["water_quality"]
    for key, data in wq.items():
        unit = data.get("unit", "")
        safe = data.get("optimal_range", data.get("safe_range", []))
        guidance = data.get("guidance", {})
        text = f"水质参数 {key}：适宜范围 {safe[0]}-{safe[1]}{' ' + str(unit) if unit else ''}。"
        if guidance:
            text += " " + " ".join(f"{k}: {v}" for k, v in guidance.items())
        chunks.append({"id": f"wq_{key}", "type": "water_quality", "text": text,
                       "keywords": [key]})

    # -- 生长阶段 --
    for stage in kg["life_cycle"]["stages"]:
        kp = stage.get("key_params", {})
        params_text = "；".join(f"{k}: {v}" for k, v in kp.items()) if kp else ""
        parts = [f"鳗鲡生长阶段：{stage['name']}"]
        if stage.get("size"):
            parts.append(f"规格：{stage['size']}")
        if stage.get("duration"):
            parts.append(f"周期：{stage['duration']}")
        if stage.get("habitat"):
            parts.append(f"环境：{stage['habitat']}")
        if stage.get("note"):
            parts.append(f"备注：{stage['note']}")
        text = "。".join(parts) + "。" + params_text
        chunks.append({"id": f"stage_{stage['name']}", "type": "life_cycle", "text": text,
                       "keywords": [stage["name"]]})

    # -- 病害 --
    for d in kg["diseases"]:
        text = (
            f"病害：{d['name']}。病原体：{d['pathogen']}。"
            f"症状：{'、'.join(d['symptoms'])}。"
            f"高发条件：{'、'.join(d['triggers'])}。"
            f"治疗：{'；'.join(d['treatment'])}。"
            f"预防：{'；'.join(d['prevention'])}。"
        )
        chunks.append({"id": f"disease_{d['name']}", "type": "disease", "text": text,
                       "keywords": d["symptoms"] + d["triggers"]})

    # -- 投喂管理 --
    fg = kg["feeding_management"]
    fr_text = "投喂率与水温关系：" + "；".join(
        f"{k.replace('_', ' ')}: {v}" for k, v in fg["feeding_rate_by_temperature"].items()
    )
    chunks.append({"id": "feeding_rate", "type": "feeding", "text": fr_text, "keywords": ["投喂", "水温", "饲料"]})

    pr_text = "投喂原则：" + "；".join(fg["key_principles"])
    chunks.append({"id": "feeding_principles", "type": "feeding", "text": pr_text, "keywords": ["投喂", "原则"]})

    freq_text = "投喂频率：" + "；".join(f"{k}: {v}" for k, v in fg["feeding_frequency"].items())
    chunks.append({"id": "feeding_freq", "type": "feeding", "text": freq_text, "keywords": ["投喂", "频率"]})

    # -- 环境管理 --
    em = kg["environmental_management"]
    for key in ["water_exchange", "aeration", "light_management", "stocking_density", "grading"]:
        data = em[key]
        text = f"{key}："
        if isinstance(data, dict):
            text += "；".join(f"{k}: {v}" for k, v in data.items() if k != "method")
            if "method" in data:
                text += "。方法：" + "、".join(data["method"])
        else:
            text += str(data)
        chunks.append({"id": f"env_{key}", "type": "environment", "text": text, "keywords": [key]})

    # -- 常见问题 --
    for name, problem in kg["common_problems"].items():
        text = (
            f"常见问题 {name}：可能原因——{'、'.join(problem['causes'])}。"
            f"处理措施——{'；'.join(problem['actions'])}。"
        )
        chunks.append({"id": f"problem_{name}", "type": "problem", "text": text,
                       "keywords": problem["causes"]})

    # -- 关键关系 --
    rels = kg["key_relationships"]
    rel_text = "水质耦合关系：" + "；".join(f"{k}: {v}" for k, v in rels.items())
    chunks.append({"id": "relationships", "type": "relationships", "text": rel_text,
                   "keywords": list(rels.keys())})

    return chunks


class RAGEngine:
    """TF-IDF 语义检索引擎：零额外依赖，支持中文。"""

    def __init__(self, kg_path: str = None):
        if kg_path is None:
            kg_path = os.path.join(os.path.dirname(__file__), "eel_knowledge.json")
        with open(kg_path, "r", encoding="utf-8") as f:
            self.kg = json.load(f)

        self.chunks = _chunk_knowledge(self.kg)
        self._texts = [c["text"] for c in self.chunks]
        self._vectorizer = None
        self._matrix = None
        self._build_index()

    def _build_index(self):
        """用 TfidfVectorizer 构建稀疏向量索引（char_wb 适配中文）。"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(2, 4), max_features=2000
            )
            self._matrix = self._vectorizer.fit_transform(self._texts)
        except ImportError:
            # sklearn 不可用时退化为关键词匹配
            self._vectorizer = None
            self._matrix = None

    def retrieve(self, query: str, top_k: int = 5):
        """混合检索：TF-IDF 语义分 + 关键词加分 → 最终排序。"""
        if self._vectorizer is None or self._matrix is None:
            return self._keyword_fallback(query, top_k)

        # 查询扩展：口语 → 术语
        expansions = {
            "不吃": "摄食 食欲 投喂", "不食": "摄食 投喂", "不吃料": "摄食 饲料 投喂",
            "浮头": "缺氧 溶氧 水面",
            "白点": "爱德华氏 脓肿 白点 气泡",
            "红": "充血 赤鳍", "烂": "溃烂 水霉",
            "死": "死亡 死亡率", "出血": "充血 赤鳍",
            "浑浊": "悬浮物 藻类 透明度",
            "苗": "玻璃鳗 鳗苗 黑仔鳗 elver",
        }
        expanded = query
        for k, v in expansions.items():
            if k in query:
                expanded += " " + v

        # TF-IDF 语义分
        q_vec = self._vectorizer.transform([expanded])
        tfidf_scores = (self._matrix @ q_vec.T).toarray().flatten()

        # 关键词加分：双向匹配（词在查询中，或查询中任意 2-gram 在关键词中）
        query_lower = query.lower()
        keyword_bonus = np.zeros(len(self.chunks))
        for i, c in enumerate(self.chunks):
            for kw in c.get("keywords", []):
                kw_l = kw.lower()
                if kw_l in query_lower or any(
                    query_lower[j:j+2] in kw_l for j in range(len(query_lower)-1)
                ):
                    keyword_bonus[i] += 0.3
                    break

        scores = tfidf_scores + keyword_bonus
        top_idx = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_idx:
            score = float(scores[idx])
            if score < 0.04:
                continue
            results.append((self.chunks[idx]["text"],
                           self.chunks[idx]["type"],
                           score))
        return results

    def _keyword_fallback(self, query: str, top_k: int):
        """关键词匹配回退（sklearn 不可用时）。"""
        scored = []
        query_lower = query.lower()
        for i, c in enumerate(self.chunks):
            score = 0
            for kw in c.get("keywords", []):
                if kw.lower() in query_lower:
                    score += 2
            if any(w in query_lower for w in c["text"][:80].split()):
                score += 1
            if score > 0:
                scored.append((i, score))
        scored.sort(key=lambda x: -x[1])
        return [(self.chunks[i]["text"], self.chunks[i]["type"], float(s))
                for i, s in scored[:top_k]]
