import json
import re
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.ai_errors import AIServiceError
from app.services.embedding.base import EmbeddingClient
from app.services.llm.base import LLMClient
from app.services.qa_service import (
    create_qa_record,
    get_or_create_conversation_session,
    list_recent_session_records,
    update_conversation_session_summary,
)
from app.services.retrieval_service import retrieve_hybrid_knowledge


SYSTEM_PROMPT = "你是高校校园服务智能问答助手。"
DIRECT_RESPONSE_PROVIDER = "system"

CASUAL_GREETINGS = {
    # 英文
    "hi", "hello", "hey", "yo", "hola", "howdy",
    # 中文问候
    "你好", "您好", "你好呀", "您好呀", "你好啊",
    "嗨", "嗨喽", "哈喽", "嘿",
    "在吗", "在不在", "在嘛", "在啊",
    # 时段问候
    "早上好", "上午好", "下午好", "晚上好", "中午好",
    "早安", "午安", "晚安",
    # 询问身份
    "你是谁", "你叫什么", "你叫什么名字", "你是干什么的",
    "你是什么", "你是什么机器人", "你是什么助手",
    "介绍一下你自己", "自我介绍",
    # 能力询问
    "你能做什么", "你会做什么", "你可以做什么",
    "你有什么功能", "你有什么用", "你能帮我什么",
    "怎么用", "怎么使用", "怎么玩",
}
CASUAL_THANKS = {
    "谢谢", "谢谢你", "感谢", "感谢你", "多谢", "多谢你",
    "谢啦", "谢了", "辛苦了", "辛苦啦", "麻烦了", "麻烦你了",
    "好的", "好", "ok", "okay", "okey",
    "知道了", "明白了", "了解了", "收到", "懂了",
}
CASUAL_FAREWELL = {
    "再见", "拜拜", "bye", "byebye", "bye bye", "goodbye",
    "下次见", "回见", "走了", "先走了",
}
CASUAL_PRAISE = {
    "厉害", "牛", "不错", "很棒", "真棒", "太棒了",
    "666", "nb", "yyds", "可以的", "行",
}
CASUAL_PUNCTUATION_RE = re.compile(r"[\s,，。.!！?？~～、]+")
REFERENCE_SOURCE_RE = re.compile(r"引用来源[:：]")
MAX_SUMMARY_LENGTH = 500
SUMMARY_RESPONSE_LIMIT = 160


def format_recent_turns(recent_turns: List[Dict]) -> str:
    if not recent_turns:
        return "暂无历史对话。"
    return "\n".join(
        f"{index}. 用户：{item['question']}\n   助手：{item['answer']}"
        for index, item in enumerate(recent_turns, start=1)
    )


def build_prompt(
    question: str,
    context_items: List[Dict],
    conversation_summary: str = "",
    recent_turns: Optional[List[Dict]] = None,
) -> str:
    if context_items:
        context = "\n\n".join(
            (
                f"[{item.get('citation_index') or index}] {item['title']}（{item.get('category', '未分类')}，"
                f"来源：{item.get('source') or '校内知识库'}，"
                f"相关度：{item.get('relevance_score', '未知')}，"
                f"命中原因：{item.get('match_reason') or '语义相似'}）\n{item['content']}"
            )
            for index, item in enumerate(context_items, start=1)
        )
    else:
        context = "未检索到相关知识。"

    summary = conversation_summary.strip() or "暂无会话摘要。"
    recent_context = format_recent_turns(recent_turns or [])

    return f"""你是高校校园服务智能问答助手。
你的任务是根据提供的校园知识库内容，回答学生、教师或工作人员的问题。

请遵守以下规则：
1. 优先根据知识库内容回答。
2. 如果知识库中没有明确答案，请说明"当前知识库中没有找到明确依据"，不要编造。
3. 回答要简洁、清楚、适合校园服务场景。
4. 涉及流程类问题时，尽量分步骤回答。
5. 涉及地点、时间、电话、网址等信息时，要原样引用知识库内容。
6. 回答末尾可以提示用户联系相关部门确认最新信息。
7. 回答控制在 300 字以内，不要展开与问题无关的知识。
8. 使用引用编号标注依据，例如“需要先挂失[1]”。
9. 回答末尾列出引用来源，格式为“引用来源：[1] 标题 - 来源”，且“引用来源”前必须空一行。

会话摘要：
{summary}

最近 3 轮对话：
{recent_context}

知识库内容：
{context}

当前问题：
{question}

请生成回答："""


def normalize_casual_message(question: str) -> str:
    return CASUAL_PUNCTUATION_RE.sub("", question.strip().lower())


def normalize_answer_references(answer: str) -> str:
    """Ensure the final reference source list starts as a separate paragraph."""
    match = REFERENCE_SOURCE_RE.search(answer)
    if not match:
        return answer

    prefix = answer[: match.start()].rstrip()
    suffix = answer[match.start() :].lstrip()
    if not prefix:
        return suffix
    return f"{prefix}\n\n{suffix}"


def records_to_recent_turns(records: List) -> List[Dict]:
    return [{"question": record.question, "answer": record.answer} for record in records]


def fallback_conversation_summary(previous_summary: str, question: str, answer: str) -> str:
    parts = []
    if previous_summary.strip():
        parts.append(previous_summary.strip())
    parts.append(f"用户问：{question.strip()}")
    parts.append(f"助手答：{answer.strip()}")
    summary = "；".join(parts)
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary[:MAX_SUMMARY_LENGTH]


def build_summary_prompt(previous_summary: str, question: str, answer: str) -> str:
    return f"""请更新这段校园问答多轮会话摘要。
要求：
1. 只保留用户持续关注的事项、已确认的信息和待解决问题。
2. 不要罗列完整对话。
3. 控制在 {SUMMARY_RESPONSE_LIMIT} 字以内。
4. 只输出摘要文本。

旧摘要：
{previous_summary or "暂无"}

最新一轮：
用户：{question}
助手：{answer}

更新后的会话摘要："""


def build_casual_answer(question: str) -> Optional[str]:
    normalized = normalize_casual_message(question)
    if not normalized:
        return "你好，我是校园问答助手。你可以问我选课、校园卡、图书馆、宿舍、奖助学金、就业、医疗、后勤报修、校园网络等问题。"

    # 纯闲聊（精确匹配）才走快捷回复，含其他内容的放行给 LLM
    if normalized in CASUAL_GREETINGS:
        return "你好，我是校园问答助手。你可以问我选课、校园卡、图书馆、宿舍、奖助学金、就业、医疗、后勤报修、校园网络等问题。"

    if normalized in CASUAL_THANKS:
        return "不客气。我可以继续帮你查询校园服务事项，比如选课、校园卡、图书馆、宿舍、网络或后勤报修。"

    if normalized in CASUAL_FAREWELL:
        return "再见！如有校园服务问题随时回来问我。"

    if normalized in CASUAL_PRAISE:
        return "谢谢夸奖！有什么校园服务问题都可以问我。"

    return None


class RAGService:
    def __init__(
        self,
        db: Session,
        embedding_client: EmbeddingClient,
        llm_client: LLMClient,
        model_provider: str,
        top_k: int,
        enable_query_rewriting: bool = True,
    ):
        self.db = db
        self.embedding_client = embedding_client
        self.llm_client = llm_client
        self.model_provider = model_provider
        self.top_k = top_k
        self.enable_query_rewriting = enable_query_rewriting

        # 初始化问题重写器
        if enable_query_rewriting:
            from app.services.query_rewriting import QueryRewriter, MultiQueryRetriever
            self.query_rewriter = QueryRewriter(llm_client, max_queries=3)
            self.multi_query_retriever = MultiQueryRetriever(
                db=db,
                embedding_client=embedding_client,
                top_k=top_k,
            )

    async def summarize_session(self, previous_summary: str, question: str, answer: str) -> str:
        fallback = fallback_conversation_summary(previous_summary, question, answer)
        try:
            summary = await self.llm_client.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_summary_prompt(previous_summary, question, answer)},
                ]
            )
        except AIServiceError:
            return fallback
        summary = re.sub(r"\s+", " ", summary).strip()
        return (summary or fallback)[:MAX_SUMMARY_LENGTH]

    async def ask(self, question: str, session_id: Optional[int] = None) -> Dict:
        conversation = get_or_create_conversation_session(self.db, session_id, question)
        recent_turns = records_to_recent_turns(list_recent_session_records(self.db, conversation.id, limit=3))
        casual_answer = build_casual_answer(question)
        if casual_answer is not None:
            record = create_qa_record(
                self.db,
                question=question,
                answer=casual_answer,
                retrieved_context=[],
                model_provider=DIRECT_RESPONSE_PROVIDER,
                session_id=conversation.id,
            )
            summary = fallback_conversation_summary(conversation.summary, question, casual_answer)
            conversation = update_conversation_session_summary(self.db, conversation, summary)
            return {
                "answer": casual_answer,
                "qa_record_id": record.id,
                "retrieved_context": [],
                "model_provider": DIRECT_RESPONSE_PROVIDER,
                "session_id": conversation.id,
                "conversation_summary": conversation.summary,
            }

        # 问题重写 + 多查询检索
        if self.enable_query_rewriting:
            queries = await self.query_rewriter.rewrite_query(question)
            context_items = await self.multi_query_retriever.retrieve(queries)
        else:
            query_embedding = await self.embedding_client.embed(question)
            context_items = retrieve_hybrid_knowledge(self.db, question, query_embedding, self.top_k)
        prompt = build_prompt(
            question=question,
            context_items=context_items,
            conversation_summary=conversation.summary,
            recent_turns=recent_turns,
        )
        answer = await self.llm_client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        answer = normalize_answer_references(answer)
        record = create_qa_record(
            self.db,
            question=question,
            answer=answer,
            retrieved_context=context_items,
            model_provider=self.model_provider,
            session_id=conversation.id,
        )
        summary = await self.summarize_session(conversation.summary, question, answer)
        conversation = update_conversation_session_summary(self.db, conversation, summary)
        return {
            "answer": answer,
            "qa_record_id": record.id,
            "retrieved_context": context_items,
            "model_provider": self.model_provider,
            "session_id": conversation.id,
            "conversation_summary": conversation.summary,
        }

    async def ask_stream(self, question: str, session_id: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Stream the RAG answer as SSE events."""
        try:
            conversation = get_or_create_conversation_session(self.db, session_id, question)
            recent_turns = records_to_recent_turns(list_recent_session_records(self.db, conversation.id, limit=3))
            casual_answer = build_casual_answer(question)
            if casual_answer is not None:
                metadata = {
                    "type": "metadata",
                    "retrieved_context": [],
                    "model_provider": DIRECT_RESPONSE_PROVIDER,
                    "session_id": conversation.id,
                    "conversation_summary": conversation.summary,
                }
                yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
                event = {"type": "chunk", "content": casual_answer}
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                record = create_qa_record(
                    self.db,
                    question=question,
                    answer=casual_answer,
                    retrieved_context=[],
                    model_provider=DIRECT_RESPONSE_PROVIDER,
                    session_id=conversation.id,
                )
                summary = fallback_conversation_summary(conversation.summary, question, casual_answer)
                conversation = update_conversation_session_summary(self.db, conversation, summary)
                done = {
                    "type": "done",
                    "qa_record_id": record.id,
                    "session_id": conversation.id,
                    "conversation_summary": conversation.summary,
                }
                yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
                return

            # 1. Retrieve relevant knowledge (with query rewriting if enabled)
            if self.enable_query_rewriting:
                queries = await self.query_rewriter.rewrite_query(question)
                context_items = await self.multi_query_retriever.retrieve(queries)
            else:
                query_embedding = await self.embedding_client.embed(question)
                context_items = retrieve_hybrid_knowledge(self.db, question, query_embedding, self.top_k)

            # 2. Send metadata event
            metadata = {
                "type": "metadata",
                "retrieved_context": context_items,
                "model_provider": self.model_provider,
                "session_id": conversation.id,
                "conversation_summary": conversation.summary,
            }
            yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"

            # 3. Stream LLM answer
            prompt = build_prompt(
                question=question,
                context_items=context_items,
                conversation_summary=conversation.summary,
                recent_turns=recent_turns,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            full_answer: List[str] = []
            async for chunk in self.llm_client.chat_stream(messages):
                full_answer.append(chunk)
                event = {"type": "chunk", "content": chunk}
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 4. Save QA record
            answer_text = normalize_answer_references("".join(full_answer))
            record = create_qa_record(
                self.db,
                question=question,
                answer=answer_text,
                retrieved_context=context_items,
                model_provider=self.model_provider,
                session_id=conversation.id,
            )
            summary = await self.summarize_session(conversation.summary, question, answer_text)
            conversation = update_conversation_session_summary(self.db, conversation, summary)

            # 5. Send done event
            done = {
                "type": "done",
                "qa_record_id": record.id,
                "session_id": conversation.id,
                "conversation_summary": conversation.summary,
            }
            yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
        except AIServiceError as exc:
            event = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
