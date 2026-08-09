"""Versioned profile for the relationship timing layer.

Four things are timed and they are kept semantically distinct, because merging
them is the easy mistake and an unlabelled result is unusable:

* a transit to A's natal chart, and a transit to B's -- ordinary transits, each
  belonging to one person
* a transit that lands on a body already carrying a synastry contact, which
  marks that contact as currently activated
* transits to the composite chart, which belong to the relationship rather than
  to either person
* progressed contacts, which come in three forms that must never be pooled:
  progressed A to natal B, natal A to progressed B, and progressed A to
  progressed B

Activation is a graph, not an inference
---------------------------------------
"Transiting Jupiter is conjunct A's Venus, and A's Venus trines B's Moon" is two
facts joined by a shared body. Reporting the join is deterministic; reading
meaning into it is not, and none is read here. The activation cites both the
transit and the synastry contact rather than minting a third fact, for the same
reason ruler interactions cite rather than mint: the geometry is already
counted.

Orb
---
Activation uses the transit profile's own orbs, because the question is whether
a transit is active, and that has already been answered by the transit layer.
Nothing is re-derived with a second threshold.
"""

from __future__ import annotations

from dataclasses import dataclass

# The three progressed comparisons, named so they can never be pooled.
PROGRESSED_A_TO_NATAL_B = "progressed_a_to_natal_b"
NATAL_A_TO_PROGRESSED_B = "natal_a_to_progressed_b"
PROGRESSED_A_TO_PROGRESSED_B = "progressed_a_to_progressed_b"

PROGRESSED_DIRECTIONS: tuple[str, ...] = (
    PROGRESSED_A_TO_NATAL_B,
    NATAL_A_TO_PROGRESSED_B,
    PROGRESSED_A_TO_PROGRESSED_B,
)

# Progressed composite: progress each chart then recompute the composite, or
# progress the composite itself. The two are not the same and mixing them
# silently is what the roadmap warns against.
COMPOSITE_FROM_PROGRESSED_CHARTS = "progress_then_compose"
PROGRESSED_COMPOSITE_DIRECT = "compose_then_progress"


@dataclass(frozen=True)
class RelationshipTimingProfile:
    id: str
    version: str
    rationale: str
    # How many activations to return, ranked.
    top_activations: int
    progressed_directions: tuple[str, ...]
    progressed_composite_method: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "topActivations": self.top_activations,
            "progressedDirections": list(self.progressed_directions),
            "progressedCompositeMethod": self.progressed_composite_method,
            "notes": list(self.notes),
        }


RELATIONSHIP_TIMING_V1 = RelationshipTimingProfile(
    id="relationship-timing-v1",
    version="1.0.0",
    rationale=(
        "Transits, synastry activation, composite transits and progressed "
        "contacts are four different statements about time and are labelled "
        "separately throughout. Activation joins a transit to a synastry "
        "contact through a shared body and cites both rather than minting a "
        "third fact."
    ),
    top_activations=10,
    progressed_directions=PROGRESSED_DIRECTIONS,
    # Progress each natal chart, then compose. Chosen because every step is
    # already independently validated -- the progression numerics against
    # external references, and the composite midpoint geometry against its own
    # fixtures -- whereas progressing a composite would be progressing a chart
    # that has no instant of its own to progress from.
    progressed_composite_method=COMPOSITE_FROM_PROGRESSED_CHARTS,
    notes=(
        "A composite chart has no birth instant, so it cannot be progressed "
        "directly without inventing one. Each natal chart is progressed first "
        "and the composite is recomputed from the results.",
        "Activation is a shared-body join between two existing facts. No "
        "meaning is inferred from the join and no model is involved.",
    ),
)
