import uuid

from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.fusion import reciprocal_rank_fusion


def ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i + 1) for i in range(n)]


def test_tokenize_lowercases_and_splits_unicode_words():
    assert tokenize("Dense-Retrieval, BM25 & naïve!") == ["dense", "retrieval", "bm25", "naïve"]


def test_bm25_ranks_matching_chunk_first_and_filters_by_paper():
    c1, c2, c3 = ids(3)
    paper_a, paper_b = uuid.uuid4(), uuid.uuid4()
    index = BM25Index()
    index.build(
        [
            (c1, paper_a, "transformers use self attention over tokens"),
            (c2, paper_b, "dense retrieval embeds passages into vectors"),
            (c3, paper_b, "sparse retrieval such as bm25 matches exact terms"),
        ]
    )

    assert index.search("dense retrieval", top_k=2)[0] == c2
    assert index.search("attention", top_k=5, paper_ids=[paper_b]) == []
    assert set(index.search("retrieval", top_k=5, paper_ids=[paper_b])) == {c2, c3}


def test_bm25_empty_index_and_empty_query():
    index = BM25Index()
    assert index.search("anything", top_k=5) == []
    index.build([(uuid.uuid4(), uuid.uuid4(), "some text")])
    assert index.search("   ", top_k=5) == []


def test_rrf_sums_contributions_and_dedups():
    a, b, c = ids(3)
    fused = reciprocal_rank_fusion([[a, b], [b, c]], k=60)
    scores = dict(fused)

    assert fused[0][0] == b
    assert scores[b] == 1 / 62 + 1 / 61
    assert scores[a] == 1 / 61
    assert scores[c] == 1 / 62
    assert len(fused) == 3


def test_rrf_ties_keep_first_seen_order():
    a, b = ids(2)
    fused = reciprocal_rank_fusion([[a], [b]], k=60)
    assert [doc for doc, _ in fused] == [a, b]


def test_rrf_ignores_duplicates_within_one_list():
    a = ids(1)[0]
    assert dict(reciprocal_rank_fusion([[a, a]], k=60))[a] == 1 / 61
