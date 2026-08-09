"""Versioned profile for evidence selection and report structure.

Two products sit downstream of this file and neither of them is built here. An
"ask about us" feature needs a bounded, relevant slice of the geometry to put in
front of a language model; a couple report needs a deterministic running order.
Both need facts and section identifiers, and neither needs a sentence written by
the core. No prose is produced here and no model is called.

Bounded, and honest about it
----------------------------
Context selection has a hard cap. An unbounded context is how a prompt ends up
containing four hundred contacts, most of them irrelevant, and how a report ends
up with a section that lists everything. Every context therefore reports
`availableCount` alongside what it returned and a `truncated` flag, so a
consumer knows whether it is looking at the whole picture or the top of it.

Selection is by contribution magnitude, and ties break on the evidence id, so
the same pair and topic always produce the same context.

Sections are declared, not discovered
-------------------------------------
The running order lives here as data. A section with no evidence is still
emitted, marked unavailable with the reason, rather than silently dropped: a
couple with an unknown birth time has no house overlays, and a report that
quietly omits the section reads as though the topic did not apply to them.
"""

from __future__ import annotations

from dataclasses import dataclass

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.dimensions import DIMENSION_IDS

# Topics that are not dimensions. `overall` draws on everything; the rest map
# one to one onto a dimension.
TOPIC_OVERALL = "overall"
TOPIC_PATTERNS = "patterns"
TOPIC_DIRECTION = "direction"

TOPIC_IDS: tuple[str, ...] = (
    TOPIC_OVERALL,
    *DIMENSION_IDS,
    TOPIC_PATTERNS,
    TOPIC_DIRECTION,
)


@dataclass(frozen=True)
class ReportSection:
    """One section of a couple report, as an identifier and what feeds it."""

    id: str
    priority: int
    topic: str
    # Which parts of the synastry result this section draws on.
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "priority": self.priority,
            "topic": self.topic,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class ReportProfile:
    id: str
    version: str
    rationale: str
    # Hard cap on evidence returned for one topic.
    maximum_evidence: int
    sections: tuple[ReportSection, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "maximumEvidence": self.maximum_evidence,
            "topics": list(TOPIC_IDS),
            "sections": [section.to_dict() for section in self.sections],
        }


COUPLE_REPORT_V1 = ReportProfile(
    id="couple-report-v1",
    version="1.0.0",
    rationale=(
        "A running order and a bounded evidence selector, both as data. The "
        "core produces identifiers and facts; the words belong to whatever "
        "renders them. Sections with no evidence are emitted as unavailable "
        "with a reason rather than dropped, because a quietly missing section "
        "reads as a topic that did not apply rather than one that could not be "
        "answered."
    ),
    maximum_evidence=12,
    sections=(
        ReportSection(
            id="at_a_glance",
            priority=1,
            topic=TOPIC_OVERALL,
            sources=("dimensions", "topStrengths", "topChallenges"),
        ),
        ReportSection(
            id="strongest_connections",
            priority=2,
            topic=TOPIC_OVERALL,
            sources=("topStrengths",),
        ),
        ReportSection(
            id="main_challenges",
            priority=3,
            topic=TOPIC_OVERALL,
            sources=("topChallenges",),
        ),
        ReportSection(
            id="emotional_connection",
            priority=4,
            topic="emotional",
            sources=("dimensions", "contributions"),
        ),
        ReportSection(
            id="communication",
            priority=5,
            topic="communication",
            sources=("dimensions", "contributions"),
        ),
        ReportSection(
            id="attraction",
            priority=6,
            topic="attraction",
            sources=("dimensions", "contributions", "pointContacts"),
        ),
        ReportSection(
            id="long_term_stability",
            priority=7,
            topic="stability",
            sources=("dimensions", "contributions"),
        ),
        ReportSection(
            id="friction",
            priority=8,
            topic="conflict",
            sources=("dimensions", "contributions"),
        ),
        ReportSection(
            id="growth",
            priority=9,
            topic="growth",
            sources=("dimensions", "contributions"),
        ),
        ReportSection(
            id="directional_dynamics",
            priority=10,
            topic=TOPIC_DIRECTION,
            sources=("directionalThemes", "rulerInteractions"),
        ),
        ReportSection(
            id="house_overlays",
            priority=11,
            topic=TOPIC_DIRECTION,
            sources=("aBodiesInBHouses", "bBodiesInAHouses"),
        ),
        ReportSection(
            id="notable_patterns",
            priority=12,
            topic=TOPIC_PATTERNS,
            sources=("patterns",),
        ),
    ),
)


def resolve_topic(topic: str) -> str:
    normalised = topic.strip().lower()
    if normalised not in TOPIC_IDS:
        raise InvalidCalculationProfileError(
            "Unknown evidence topic.",
            {"topic": topic, "supported": list(TOPIC_IDS)},
        )
    return normalised
