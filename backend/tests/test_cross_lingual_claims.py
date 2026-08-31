"""
Unit and Integration Test Suite for Cross-Lingual Claim Verification (Phase 11)
Validates entity translation, cross-lingual search query generation,
and multilingual relevance matching across 20 distinct claims in French, German,
Japanese, Korean, and International English domains.
"""

import pytest
from app.models.verification_models import Claim, InputType, Verifiability
from app.models.reasoning_ir import FactSlots, CompoundFactSlot
from app.agents.fast_verifier import FastClaimVerifierAgent, INTL_ENTITY_MAP, INTL_ENTITY_EN_NAMES


CROSS_LINGUAL_20_CLAIMS = [
    # 1. French / European Governance
    {
        "id": "XLING-01",
        "claim": "巴黎市民在2024年投票公投通过对重型SUV车辆停放费用提高至原有水平的三倍。",
        "entity": "巴黎",
        "expected_lang": "fr",
        "target_keywords": ["Paris", "SUV", "parking"]
    },
    {
        "id": "XLING-02",
        "claim": "法国巴黎圣母院于2024年12月8日举行修复后首次向公众重新开放仪式。",
        "entity": "巴黎",
        "expected_lang": "fr",
        "target_keywords": ["Paris"]
    },
    {
        "id": "XLING-03",
        "claim": "卢浮宫阿布扎比博物馆位于阿联酋萨迪亚特岛。",
        "entity": "卢浮宫",
        "expected_lang": "fr",
        "target_keywords": ["Louvre"]
    },
    # 2. German / Industrial & Energy
    {
        "id": "XLING-04",
        "claim": "大众汽车集团考虑在2024年首次关闭其在德国本土的制造工厂以削减成本。",
        "entity": "大众汽车",
        "expected_lang": "en",
        "target_keywords": ["Volkswagen", "factory"]
    },
    {
        "id": "XLING-05",
        "claim": "德国柏林参议院在2024年就商业地产能效升级标准达成联合决议。",
        "entity": "柏林",
        "expected_lang": "de",
        "target_keywords": ["Berlin"]
    },
    # 3. Japanese / Asian Tech & Gaming
    {
        "id": "XLING-06",
        "claim": "任天堂社长古川俊太郎在2024年5月确认将在本财年内公布 Nintendo Switch 后续机型。",
        "entity": "任天堂",
        "expected_lang": "en",
        "target_keywords": ["Nintendo"]
    },
    {
        "id": "XLING-07",
        "claim": "丰田汽车计划在2027至2028年实现全固态电池全电动汽车的商业化投产。",
        "entity": "丰田",
        "expected_lang": "en",
        "target_keywords": ["Toyota"]
    },
    {
        "id": "XLING-08",
        "claim": "东京都知事小池百合子在2024年7月的东京都知事选举中第三次当选。",
        "entity": "东京",
        "expected_lang": "ja",
        "target_keywords": ["Tokyo"]
    },
    # 4. Korean / Semiconductor
    {
        "id": "XLING-09",
        "claim": "三星电子在2024年完成了第五代高带宽内存HBM3E芯片的英伟达认证测试。",
        "entity": "三星",
        "expected_lang": "en",
        "target_keywords": ["Samsung"]
    },
    {
        "id": "XLING-10",
        "claim": "首尔市政府在2024年全面推广气温减缓气候同行公共交通卡。",
        "entity": "首尔",
        "expected_lang": "ko",
        "target_keywords": ["Seoul"]
    },
    # 5. International Regulation & Policy
    {
        "id": "XLING-11",
        "claim": "欧盟《人工智能法案》（EU AI Act）于2024年8月1日正式在欧盟全境生效实施。",
        "entity": "AI法案",
        "expected_lang": "en",
        "target_keywords": ["AI Act"]
    },
    {
        "id": "XLING-12",
        "claim": "世界卫生组织（WHO）在2024年8月宣布猴痘疫情（Mpox）构成国际关注的突发公共卫生事件。",
        "entity": "世卫",
        "expected_lang": "en",
        "target_keywords": ["WHO"]
    },
    {
        "id": "XLING-13",
        "claim": "欧洲空间局（ESA）发射的木星冰月探测器（JUICE）于2024年8月完成首次月球-地球双重引力助推。",
        "entity": "欧空局",
        "expected_lang": "en",
        "target_keywords": ["ESA"]
    },
    {
        "id": "XLING-14",
        "claim": "美国FDA在2023年7月正式完全批准了阿尔茨海默病新药Leqembi。",
        "entity": "FDA",
        "expected_lang": "en",
        "target_keywords": ["FDA"]
    },
    {
        "id": "XLING-15",
        "claim": "加州法律规定自2024年4月1日起快餐行业从业人员最低法定保底时薪上调至20美元。",
        "entity": "加州",
        "expected_lang": "en",
        "target_keywords": ["California", "fast food"]
    },
    # 6. Global Sports, History & Culture
    {
        "id": "XLING-16",
        "claim": "卡洛斯·阿尔卡拉斯（Carlos Alcaraz）在2024年摘得法国网球公开赛与温网男单双料桂冠。",
        "entity": "阿尔卡拉斯",
        "expected_lang": "en",
        "target_keywords": ["Alcaraz", "tennis"]
    },
    {
        "id": "XLING-17",
        "claim": "波士顿凯尔特人队在2024年总决赛击败独行侠赢得队史第18座NBA总冠军奖杯。",
        "entity": "凯尔特人",
        "expected_lang": "en",
        "target_keywords": ["Celtics"]
    },
    {
        "id": "XLING-18",
        "claim": "皮克斯动画电影《头脑特工队2》（Inside Out 2）2024年全球票房破16亿美元成为影史动画冠军。",
        "entity": "皮克斯",
        "expected_lang": "en",
        "target_keywords": ["Pixar", "Inside Out"]
    },
    {
        "id": "XLING-19",
        "claim": "波音公司在2024年正式达成以47亿美元全股票交易收购势必锐航空系统公司（Spirit AeroSystems）。",
        "entity": "波音",
        "expected_lang": "en",
        "target_keywords": ["Boeing"]
    },
    {
        "id": "XLING-20",
        "claim": "美国太空总署（NASA）阿波罗11号任务于1969年7月20日实现人类首次登月。",
        "entity": "阿波罗",
        "expected_lang": "en",
        "target_keywords": ["Apollo"]
    }
]


class MockItem:
    def __init__(self, title: str, snippet: str, url: str):
        self.title = title
        self.snippet = snippet
        self.url = url
        self.is_synthetic = False


@pytest.fixture
def verifier():
    return FastClaimVerifierAgent(llm_provider=None, search_provider=None)


def test_cross_lingual_entity_map_completeness():
    """Verify all 20 cross-lingual test entities exist in INTL_ENTITY_MAP."""
    assert len(CROSS_LINGUAL_20_CLAIMS) == 20
    for case in CROSS_LINGUAL_20_CLAIMS:
        ent = case["entity"]
        assert ent in INTL_ENTITY_MAP, f"Entity {ent} missing from INTL_ENTITY_MAP"
        en_name, lang, domain_ctx = INTL_ENTITY_MAP[ent]
        assert len(en_name) > 0
        assert len(lang) == 2


@pytest.mark.parametrize("case", CROSS_LINGUAL_20_CLAIMS)
def test_cross_lingual_query_generation_and_expansion(verifier, case):
    """
    Verify that FastVerifier._build_directed_search_queries expands Chinese statements
    into precise multilingual / English queries containing target keywords.
    """
    claim = Claim(
        id=case["id"],
        original_input=case["claim"],
        input_type=InputType.TEXT,
        statement=case["claim"],
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="Cross-lingual evaluation test case",
        verified_as_of="2026-08-30"
    )
    fact_slots = FactSlots(
        entity=case["entity"],
        predicate="statement",
        compound_slots=[]
    )

    queries = verifier._build_directed_search_queries(claim, fact_slots)
    assert len(queries) > 0, f"Generated empty queries for {case['id']}"

    # Verify at least one query contains target keywords from cross-lingual mapping
    combined_queries = " ".join(queries).lower()
    for kw in case["target_keywords"]:
        assert kw.lower() in combined_queries, (
            f"Case {case['id']}: expected keyword '{kw}' not found in queries: {queries}"
        )


@pytest.mark.parametrize("case", CROSS_LINGUAL_20_CLAIMS)
def test_cross_lingual_relevance_matching(verifier, case):
    """
    Verify that an English/foreign search result containing the translated entity
    and key tokens achieves high relevance (>0.4), while an irrelevant page gets 0.05.
    """
    claim = Claim(
        id=case["id"],
        original_input=case["claim"],
        input_type=InputType.TEXT,
        statement=case["claim"],
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="Cross-lingual evaluation",
        verified_as_of="2026-08-30"
    )
    en_name = INTL_ENTITY_EN_NAMES.get(case["entity"], case["entity"])
    fact_slots = FactSlots(
        entity=case["entity"],
        predicate="verification",
        compound_slots=[]
    )

    # 1. Relevant foreign-language document
    relevant_item = MockItem(
        title=f"Official Report: {en_name} updates for 2024",
        snippet=f"The latest official documentation confirmed {en_name} announcement with detailed records.",
        url=f"https://www.example.org/{en_name.lower()}/report"
    )
    rel_score = verifier._evaluate_search_result_relevance(relevant_item, fact_slots, claim)
    assert rel_score >= 0.5, f"Case {case['id']}: Relevant document scored too low: {rel_score}"

    # 2. Completely irrelevant junk document (e.g. fashion sale or generic portal)
    junk_item = MockItem(
        title="Spring-Summer Women's Clothing Clearance Sale",
        snippet="Buy discount jackets, shoes, and accessories with free worldwide delivery.",
        url="https://www.randomshop.com/clearance"
    )
    junk_score = verifier._evaluate_search_result_relevance(junk_item, fact_slots, claim)
    assert junk_score <= 0.1, f"Case {case['id']}: Junk document scored too high: {junk_score}"
