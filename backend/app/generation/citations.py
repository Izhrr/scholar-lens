import re
from dataclasses import dataclass

from app.generation.prompts import ABSTAIN_TOKEN

_MARKER_GROUP = re.compile(r"\[\s*(S\d+(?:\s*,\s*S\d+)*)\s*\]")
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([.,;:!?])")
_DOUBLE_SPACE = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True)
class CitedAnswer:
    text: str
    # citation number (1-based, order of first use) -> index into the retrieved chunks
    citations: dict[int, int]
    abstained: bool

    @property
    def grounded(self) -> bool:
        return bool(self.citations)


def resolve_citations(raw: str, source_count: int) -> CitedAnswer:
    """Turn [S#] markers into [n] citations, dropping any marker that points nowhere."""
    if not raw.strip() or ABSTAIN_TOKEN in raw:
        return CitedAnswer(text="", citations={}, abstained=True)

    source_to_citation: dict[int, int] = {}

    def replace(match: re.Match[str]) -> str:
        rendered = []
        for token in match.group(1).split(","):
            source_index = int(token.strip()[1:]) - 1
            if not 0 <= source_index < source_count:
                continue
            if source_index not in source_to_citation:
                source_to_citation[source_index] = len(source_to_citation) + 1
            marker = f"[{source_to_citation[source_index]}]"
            if marker not in rendered:
                rendered.append(marker)
        return "".join(rendered)

    text = _MARKER_GROUP.sub(replace, raw)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _DOUBLE_SPACE.sub(" ", text).strip()
    citations = {number: index for index, number in source_to_citation.items()}
    return CitedAnswer(text=text, citations=citations, abstained=False)
