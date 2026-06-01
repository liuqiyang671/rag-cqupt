from collections import Counter


EXPECTED_CATEGORIES = {
    "教务服务",
    "图书馆服务",
    "校园卡服务",
    "宿舍服务",
    "奖助学金",
    "就业服务",
    "医疗服务",
    "后勤报修",
    "校园网络",
}


def test_campus_seed_dataset_covers_all_service_categories():
    from app.data.campus_seed import CAMPUS_KNOWLEDGE_CATEGORIES, CAMPUS_KNOWLEDGE_ITEMS

    counts = Counter(item["category"] for item in CAMPUS_KNOWLEDGE_ITEMS)

    assert set(CAMPUS_KNOWLEDGE_CATEGORIES) == EXPECTED_CATEGORIES
    assert set(counts) == EXPECTED_CATEGORIES
    assert min(counts.values()) >= 8
    assert len(CAMPUS_KNOWLEDGE_ITEMS) >= 72


def test_campus_seed_dataset_items_are_complete_and_unique():
    from app.data.campus_seed import CAMPUS_KNOWLEDGE_ITEMS

    identities = {(item["category"], item["title"]) for item in CAMPUS_KNOWLEDGE_ITEMS}

    assert len(identities) == len(CAMPUS_KNOWLEDGE_ITEMS)
    assert all(item["title"].strip() for item in CAMPUS_KNOWLEDGE_ITEMS)
    assert all(item["category"].strip() for item in CAMPUS_KNOWLEDGE_ITEMS)
    assert all(len(item["content"].strip()) >= 80 for item in CAMPUS_KNOWLEDGE_ITEMS)
    assert all(item["source"].strip() for item in CAMPUS_KNOWLEDGE_ITEMS)
