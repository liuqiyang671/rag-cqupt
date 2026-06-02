from app.models.knowledge import KnowledgeBase
from app.services.retrieval_service import (
    RetrievalCandidate,
    build_retrieved_knowledge,
    detect_query_category,
    keyword_score,
    rerank_retrieval_candidates,
)


def _knowledge(
    knowledge_id: int,
    title: str,
    category: str,
    content: str,
    source: str = "测试来源",
) -> KnowledgeBase:
    return KnowledgeBase(
        id=knowledge_id,
        title=title,
        category=category,
        content=content,
        source=source,
        embedding=[0.0] * 4096,
    )


def test_detect_query_category_prefers_campus_card_and_repair_intents():
    assert detect_query_category("校园卡丢了怎么办？") == "校园卡服务"
    assert detect_query_category("图书馆座位怎么预约？") == "图书馆服务"
    assert detect_query_category("宿舍漏水要怎么报修？") == "后勤报修"
    assert detect_query_category("宿舍严重漏水应该找谁？") == "后勤报修"


def test_keyword_score_uses_expanded_terms_for_common_student_language():
    card_item = _knowledge(
        1,
        "校园卡挂失与冻结",
        "校园卡服务",
        "校园卡遗失后，应尽快办理挂失。确认遗失后可办理补卡。",
    )
    library_item = _knowledge(
        2,
        "图书馆开放时间",
        "图书馆服务",
        "图书馆日常开放时间覆盖上午、下午和晚间学习时段。",
    )

    assert keyword_score("校园卡丢了怎么办？", card_item) > keyword_score("校园卡丢了怎么办？", library_item)


def test_rerank_combines_vector_keyword_and_category_signals():
    card_item = _knowledge(
        1,
        "校园卡挂失与冻结",
        "校园卡服务",
        "校园卡遗失后，应尽快通过服务平台办理挂失。",
    )
    library_item = _knowledge(
        2,
        "文献传递与馆际互借",
        "图书馆服务",
        "馆藏没有的论文可通过文献传递申请。",
    )

    results = rerank_retrieval_candidates(
        question="校园卡丢了怎么办？",
        candidates=[
            RetrievalCandidate(item=library_item, vector_similarity=0.96),
            RetrievalCandidate(item=card_item, vector_similarity=0.78),
        ],
        top_k=2,
        min_score=0.25,
    )

    assert [result.item.id for result in results] == [1, 2]
    assert results[0].match_reason == "分类匹配、关键词命中、语义相似"


def test_rerank_filters_low_relevance_without_category_or_keyword_match():
    weather_item = _knowledge(
        1,
        "图书馆开放时间",
        "图书馆服务",
        "图书馆日常开放时间覆盖上午、下午和晚间学习时段。",
    )

    results = rerank_retrieval_candidates(
        question="今天中午吃什么？",
        candidates=[RetrievalCandidate(item=weather_item, vector_similarity=0.72)],
        top_k=3,
        min_score=0.25,
    )

    assert results == []


def test_build_retrieved_knowledge_includes_relevance_metadata():
    card_item = _knowledge(
        7,
        "校园卡挂失与冻结",
        "校园卡服务",
        "校园卡遗失后，应尽快办理挂失。",
        source="校园卡服务中心指南",
    )
    results = rerank_retrieval_candidates(
        question="校园卡丢了怎么办？",
        candidates=[RetrievalCandidate(item=card_item, vector_similarity=0.91)],
        top_k=1,
        min_score=0.25,
    )

    payload = build_retrieved_knowledge(results)[0]

    assert payload["citation_index"] == 1
    assert payload["relevance_score"] > 0
    assert payload["match_reason"] == "分类匹配、关键词命中、语义相似"
    assert payload["source"] == "校园卡服务中心指南"
