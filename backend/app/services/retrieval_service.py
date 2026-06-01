import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeBase
from app.services.vector_schema import get_knowledge_embedding_dimension, validate_embedding_dimensions


DEFAULT_MIN_RETRIEVAL_SCORE = 0.25
DEFAULT_VECTOR_RECALL = 12
DEFAULT_KEYWORD_RECALL = 12
STRONG_VECTOR_SIMILARITY = 0.88

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "教务服务": ("教务", "选课", "课程", "成绩", "考试", "缓考", "重修", "学籍", "毕业", "转专业", "证明"),
    "图书馆服务": ("图书馆", "借书", "借阅", "续借", "座位", "预约", "研修间", "文献", "电子资源", "馆际"),
    "校园卡服务": ("校园卡", "一卡通", "饭卡", "卡丢", "丢卡", "挂失", "补卡", "补办", "充值", "余额", "食堂扣费"),
    "宿舍服务": ("宿舍", "公寓", "床位", "调宿", "退宿", "晚归", "留宿", "空调", "宿管"),
    "奖助学金": ("奖学金", "助学金", "助学贷款", "困难认定", "勤工助学", "绿色通道", "补助"),
    "就业服务": ("就业", "招聘", "实习", "简历", "面试", "档案", "签约", "协议书", "基层项目"),
    "医疗服务": ("校医院", "医院", "医保", "挂号", "就诊", "体检", "疫苗", "病假", "急症", "转诊"),
    "后勤报修": ("报修", "维修", "漏水", "停电", "水电", "电梯", "路灯", "保洁", "家具", "管道"),
    "校园网络": ("校园网", "网络", "wifi", "wi-fi", "vpn", "统一身份认证", "密码", "账号", "掉线", "mac"),
}

QUERY_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "丢": ("遗失", "挂失", "补办", "补卡"),
    "丢了": ("遗失", "挂失", "补办", "补卡"),
    "丢失": ("遗失", "挂失", "补办", "补卡"),
    "坏了": ("故障", "维修", "报修"),
    "漏水": ("水电", "管道", "爆裂", "报修"),
    "座位": ("预约", "签到", "研修间"),
    "借书": ("借阅", "续借", "图书"),
    "生病": ("校医院", "就诊", "挂号"),
    "上网": ("校园网", "网络", "wifi", "账号"),
}

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*|[\u4e00-\u9fff]{2,}")


@dataclass
class RetrievalCandidate:
    item: KnowledgeBase
    vector_similarity: float = 0.0
    keyword_score: float = 0.0


@dataclass
class RetrievalResult:
    item: KnowledgeBase
    score: float
    vector_similarity: float
    keyword_score: float
    category_match: bool
    match_reason: str


def detect_query_category(question: str) -> str | None:
    normalized = question.lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in normalized:
                score += 2 if len(keyword) >= 3 else 1
        if score:
            scores[category] = score

    if not scores:
        return None
    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def extract_query_terms(question: str) -> list[str]:
    normalized = question.lower()
    terms: set[str] = set()
    for token in TOKEN_RE.findall(normalized):
        if len(token) >= 2:
            terms.add(token)

    for trigger, expansions in QUERY_EXPANSIONS.items():
        if trigger in normalized:
            terms.update(expansion.lower() for expansion in expansions)

    category = detect_query_category(question)
    if category:
        terms.add(category.lower())
        terms.update(keyword.lower() for keyword in CATEGORY_KEYWORDS[category])

    return sorted(terms, key=lambda term: (-len(term), term))


def keyword_score(question: str, item: KnowledgeBase) -> float:
    terms = extract_query_terms(question)
    if not terms:
        return 0.0

    haystack = "\n".join(
        [
            item.title or "",
            item.category or "",
            item.content or "",
            item.source or "",
        ]
    ).lower()
    title = (item.title or "").lower()
    category = (item.category or "").lower()

    score = 0.0
    max_score = 0.0
    for term in terms:
        weight = min(max(len(term) / 4, 0.5), 2.0)
        max_score += weight
        if term in title:
            score += weight * 1.4
        elif term in category:
            score += weight * 1.2
        elif term in haystack:
            score += weight

    return min(score / max(max_score, 1.0), 1.0)


def rerank_retrieval_candidates(
    question: str,
    candidates: Iterable[RetrievalCandidate],
    top_k: int,
    min_score: float = DEFAULT_MIN_RETRIEVAL_SCORE,
) -> list[RetrievalResult]:
    preferred_category = detect_query_category(question)
    merged: dict[int, RetrievalCandidate] = {}
    for candidate in candidates:
        existing = merged.get(candidate.item.id)
        candidate.keyword_score = max(candidate.keyword_score, keyword_score(question, candidate.item))
        if existing is None:
            merged[candidate.item.id] = candidate
        else:
            existing.vector_similarity = max(existing.vector_similarity, candidate.vector_similarity)
            existing.keyword_score = max(existing.keyword_score, candidate.keyword_score)

    results: list[RetrievalResult] = []
    for candidate in merged.values():
        category_match = preferred_category is not None and candidate.item.category == preferred_category
        category_boost = 1.0 if category_match else 0.0
        score = (
            candidate.vector_similarity * 0.50
            + candidate.keyword_score * 0.35
            + category_boost * 0.15
        )

        if not _passes_relevance_gate(candidate, category_match, score, min_score):
            continue

        results.append(
            RetrievalResult(
                item=candidate.item,
                score=round(score, 4),
                vector_similarity=round(candidate.vector_similarity, 4),
                keyword_score=round(candidate.keyword_score, 4),
                category_match=category_match,
                match_reason=build_match_reason(category_match, candidate.keyword_score, candidate.vector_similarity),
            )
        )

    results.sort(
        key=lambda result: (
            result.score,
            result.category_match,
            result.keyword_score,
            result.vector_similarity,
        ),
        reverse=True,
    )
    return results[:top_k]


def _passes_relevance_gate(
    candidate: RetrievalCandidate,
    category_match: bool,
    score: float,
    min_score: float,
) -> bool:
    if score < min_score:
        return False
    if category_match or candidate.keyword_score > 0:
        return True
    return candidate.vector_similarity >= STRONG_VECTOR_SIMILARITY


def build_match_reason(category_match: bool, keyword: float, vector: float) -> str:
    reasons: list[str] = []
    if category_match:
        reasons.append("分类匹配")
    if keyword > 0:
        reasons.append("关键词命中")
    if vector > 0:
        reasons.append("语义相似")
    return "、".join(reasons) or "语义相似"


def build_retrieved_knowledge(results: list[RetrievalResult]) -> list[dict]:
    payload: list[dict] = []
    for index, result in enumerate(results, start=1):
        payload.append(
            {
                "id": result.item.id,
                "title": result.item.title,
                "category": result.item.category,
                "content": result.item.content,
                "source": result.item.source,
                "citation_index": index,
                "relevance_score": result.score,
                "match_reason": result.match_reason,
            }
        )
    return payload


def retrieve_hybrid_knowledge(
    db: Session,
    question: str,
    query_embedding: list[float],
    top_k: int,
    min_score: float = DEFAULT_MIN_RETRIEVAL_SCORE,
    vector_recall: int = DEFAULT_VECTOR_RECALL,
    keyword_recall: int = DEFAULT_KEYWORD_RECALL,
) -> list[dict]:
    validate_embedding_dimensions(
        configured_dimension=len(query_embedding),
        database_dimension=get_knowledge_embedding_dimension(db.get_bind()),
    )
    candidates: list[RetrievalCandidate] = []
    candidates.extend(_vector_candidates(db, query_embedding, question, max(vector_recall, top_k)))
    candidates.extend(_keyword_candidates(db, question, max(keyword_recall, top_k)))
    ranked = rerank_retrieval_candidates(
        question=question,
        candidates=candidates,
        top_k=top_k,
        min_score=min_score,
    )
    return build_retrieved_knowledge(ranked)


def _vector_candidates(
    db: Session,
    query_embedding: list[float],
    question: str,
    limit: int,
) -> list[RetrievalCandidate]:
    distance = KnowledgeBase.embedding.cosine_distance(query_embedding)
    preferred_category = detect_query_category(question)
    candidates: list[RetrievalCandidate] = []

    if preferred_category:
        statement = (
            select(KnowledgeBase, distance.label("distance"))
            .where(KnowledgeBase.category == preferred_category)
            .order_by(distance)
            .limit(limit)
        )
        candidates.extend(_rows_to_vector_candidates(db.execute(statement).all()))

    remaining = max(limit - len(candidates), limit // 2)
    statement = select(KnowledgeBase, distance.label("distance")).order_by(distance).limit(remaining)
    candidates.extend(_rows_to_vector_candidates(db.execute(statement).all()))
    return candidates


def _rows_to_vector_candidates(rows) -> list[RetrievalCandidate]:
    candidates: list[RetrievalCandidate] = []
    for item, distance in rows:
        similarity = max(0.0, 1.0 - float(distance or 0.0))
        candidates.append(RetrievalCandidate(item=item, vector_similarity=similarity))
    return candidates


def _keyword_candidates(db: Session, question: str, limit: int) -> list[RetrievalCandidate]:
    terms = [term for term in extract_query_terms(question) if len(term) >= 2][:12]
    if not terms:
        return []

    filters = []
    for term in terms:
        pattern = f"%{term}%"
        filters.append(KnowledgeBase.title.ilike(pattern))
        filters.append(KnowledgeBase.category.ilike(pattern))
        filters.append(KnowledgeBase.content.ilike(pattern))
        filters.append(KnowledgeBase.source.ilike(pattern))

    statement = select(KnowledgeBase).where(or_(*filters)).limit(limit)
    return [
        RetrievalCandidate(item=item, keyword_score=keyword_score(question, item))
        for item in db.scalars(statement).all()
    ]
