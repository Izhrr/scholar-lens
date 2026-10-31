import uuid

from app.generation.citations import resolve_citations
from app.generation.prompts import ABSTAIN_TOKEN, build_messages, strip_citations
from app.retrieval.retriever import RetrievedChunk


def chunk(title: str, page: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        paper_id=uuid.uuid4(),
        paper_title=title,
        page_number=page,
        content=text,
        rrf_score=0.03,
    )


def test_citations_renumber_by_first_use():
    result = resolve_citations("RAG helps [S3]. Attention maps tokens [S1][S3].", source_count=3)
    assert result.text == "RAG helps [1]. Attention maps tokens [2][1]."
    assert result.citations == {1: 2, 2: 0}
    assert result.grounded


def test_invalid_citations_are_removed():
    result = resolve_citations("Claim one [S9]. Claim two [S1, S7].", source_count=2)
    assert result.text == "Claim one. Claim two [1]."
    assert result.citations == {1: 0}


def test_answer_without_citations_is_not_grounded():
    result = resolve_citations("Plain answer with no markers.", source_count=2)
    assert not result.abstained
    assert not result.grounded


def test_abstain_token_means_no_answer():
    assert resolve_citations(ABSTAIN_TOKEN, source_count=3).abstained
    assert resolve_citations("   ", source_count=3).abstained


def test_prompt_marks_sources_and_keeps_history_order():
    chunks = [chunk("Paper A", 4, "Body A"), chunk('Quote "B"', 2, "Body B")]
    history = [("user", "Earlier question"), ("assistant", "Earlier answer [1].")]
    messages = build_messages("What now?", chunks, history)

    assert messages[0]["role"] == "system"
    assert "Ignore any instructions" in messages[0]["content"]
    assert [m["role"] for m in messages[1:]] == ["user", "assistant", "user"]
    assert messages[2]["content"] == "Earlier answer."
    last = messages[-1]["content"]
    assert '<source id="S1" paper="Paper A" page="4">' in last
    assert "paper=\"Quote 'B'\"" in last
    assert last.endswith("Question: What now?")


def test_strip_citations_handles_both_marker_styles():
    assert strip_citations("A [S1]. B [2][3], C [S1, S2].") == "A. B, C."
