import re
from typing import Dict, List

from app.services.llm.base import LLMClient


class FallbackLLMClient(LLMClient):
    """Evidence-based local fallback used when external model calls are unavailable."""

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        prompt = messages[-1].get("content", "") if messages else ""
        context_match = re.search(r"知识库内容：\s*(.*?)\s*用户问题：", prompt, re.S)
        question_match = re.search(r"用户问题：\s*(.*?)\s*请生成回答：", prompt, re.S)
        context = context_match.group(1).strip() if context_match else ""
        question = question_match.group(1).strip() if question_match else "该问题"

        if not context or "未检索到相关知识" in context:
            return "当前知识库中没有找到明确依据，建议联系相关部门确认最新信息。"

        snippets = []
        for block in re.split(r"\n(?=\[\d+\])", context):
            cleaned = block.strip()
            if not cleaned:
                continue
            lines = cleaned.splitlines()
            title = re.sub(r"^\[\d+\]\s*", "", lines[0]).strip()
            content = " ".join(line.strip() for line in lines[1:] if line.strip())
            snippets.append((title, content))

        if not snippets:
            return "当前知识库中没有找到明确依据，建议联系相关部门确认最新信息。"

        answer_lines = [f"关于“{question}”，可参考以下校内知识："]
        for index, (title, content) in enumerate(snippets[:3], start=1):
            answer_lines.append(f"{index}. {title}：{content}")
        answer_lines.append("如信息涉及最新办理时间、地点或政策，请联系相关部门确认。")
        return "\n".join(answer_lines)

