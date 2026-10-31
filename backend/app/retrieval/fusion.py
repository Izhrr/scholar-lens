import uuid
from collections.abc import Sequence


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[uuid.UUID]], k: int = 60
) -> list[tuple[uuid.UUID, float]]:
    """Merge ranked lists: score(d) = sum over lists of 1 / (k + rank), rank starting at 1."""
    scores: dict[uuid.UUID, float] = {}
    first_seen: dict[uuid.UUID, int] = {}
    position = 0
    for ranking in rankings:
        seen_in_list: set[uuid.UUID] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen_in_list:
                continue
            seen_in_list.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in first_seen:
                first_seen[doc_id] = position
                position += 1
    return sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))
