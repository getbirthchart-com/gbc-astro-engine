"""Bounded evidence contexts and a deterministic report outline.

Neither of these produces prose and neither calls a model. They select and order
facts that already exist, and every identifier they emit resolves to something
in the synastry result or the score.

Why bounded matters more than it looks
--------------------------------------
An unbounded evidence context is how a prompt ends up carrying four hundred
contacts, most of them irrelevant to the question asked, and how a downstream
model ends up asserting whichever of them it happened to notice. The cap is
therefore part of the contract rather than a caller's responsibility, and the
context says how much it left behind so nobody mistakes the top of a list for
the whole of one.

Why an empty section is still a section
---------------------------------------
A couple with an unknown birth time has no house overlays. Dropping the section
would read as a topic that did not apply to them; emitting it as unavailable
with the reason reads as what it is -- a question the geometry could not answer.
The same distinction the dimension scores draw between silent and neutral.
"""

from __future__ import annotations

from gbc_astro.models.relationship import (
    EvidenceContext,
    RelationshipScore,
    ReportOutline,
    ReportSectionResult,
    SynastryChart,
)
from gbc_astro.profiles.report import (
    TOPIC_DIRECTION,
    TOPIC_OVERALL,
    TOPIC_PATTERNS,
    ReportProfile,
    resolve_topic,
)


def _contribution_evidence(
    score: RelationshipScore, topic: str
) -> list[tuple[float, str]]:
    """Scored contacts relevant to a topic, as (magnitude, evidence id).

    `overall` takes every contribution; a dimension topic takes only the
    contributions that speak to that dimension, ranked by what they contributed
    to it rather than by their raw value -- a contact can be large overall and
    say little about communication.
    """
    ranked: list[tuple[float, str]] = []
    for contribution in score.contributions:
        if topic == TOPIC_OVERALL:
            ranked.append((abs(contribution.value), contribution.evidence_id))
            continue
        value = contribution.dimension_values.get(topic)
        if value is not None:
            ranked.append((abs(value), contribution.evidence_id))
    return ranked


def build_evidence_context(
    synastry: SynastryChart,
    score: RelationshipScore,
    topic: str,
    profile: ReportProfile,
) -> EvidenceContext:
    """A bounded, deterministic slice of the geometry for one topic.

    Selection is by magnitude with ties broken on the evidence id, so the same
    pair and topic always yield the same context.
    """
    resolved = resolve_topic(topic)

    if resolved == TOPIC_PATTERNS:
        candidates = [
            (float(len(pattern.evidence_ids)), pattern.id)
            for pattern in synastry.patterns
        ]
    elif resolved == TOPIC_DIRECTION:
        candidates = [
            (float(theme.contact_count), evidence_id)
            for theme in synastry.directional_themes
            for evidence_id in theme.evidence_ids
        ]
    else:
        candidates = _contribution_evidence(score, resolved)

    # Descending magnitude, then ascending id, so the order never depends on
    # dictionary iteration or on two contacts happening to tie.
    ordered = sorted(
        set(candidates), key=lambda item: (-item[0], item[1])
    )
    selected = ordered[: profile.maximum_evidence]

    dimension = next(
        (item for item in score.dimensions if item.dimension == resolved), None
    )

    return EvidenceContext(
        topic=resolved,
        evidence_ids=tuple(name for _value, name in selected),
        available_count=len(ordered),
        truncated=len(ordered) > len(selected),
        dimension=dimension,
        provenance={
            "engine": score.engine,
            "engineVersion": score.engine_version,
            "scoringProfile": score.scoring_profile,
            "scoringProfileVersion": score.scoring_profile_version,
            "dimensionProfile": score.dimension_profile,
            "dimensionProfileVersion": score.dimension_profile_version,
            "relationshipType": score.relationship_type,
            "relationshipTypeVersion": score.relationship_type_version,
            "rankingProfile": score.ranking_profile,
            "reportProfile": profile.id,
            "reportProfileVersion": profile.version,
            "synastrySchemaVersion": synastry.schema_version,
        },
    )


# Which part of the result each declared source reads from, and what to say when
# it is empty. The reasons are specific because "no data" tells a reader nothing
# about whether to ask again with a birth time.
_SOURCE_REASONS = {
    "aBodiesInBHouses": "one chart has no houses, so this overlay direction is unavailable",
    "bBodiesInAHouses": "one chart has no houses, so this overlay direction is unavailable",
    "pointContacts": "no derived point contact falls inside the two-degree orb",
    "patterns": "no named configuration reached its threshold for this pair",
    "rulerInteractions": "a chart without houses has no house rulers to send",
    "directionalThemes": "no directional contact was found",
}


def _section_evidence(
    synastry: SynastryChart,
    score: RelationshipScore,
    source: str,
    topic: str,
) -> list[str]:
    """What one declared source contributes to a section.

    `contributions` is filtered by the section's topic. A communication section
    citing all fifty scored contacts would be citing the whole chart and calling
    it communication, which is worse than citing nothing.
    """
    if source == "topStrengths":
        return [contact.evidence_id for contact in score.top_strengths]
    if source == "topChallenges":
        return [contact.evidence_id for contact in score.top_challenges]
    if source == "dimensions":
        return []
    if source == "contributions":
        return [
            contribution.evidence_id
            for contribution in score.contributions
            if topic == TOPIC_OVERALL or topic in contribution.dimension_values
        ]
    if source == "patterns":
        return [pattern.id for pattern in synastry.patterns]
    if source == "pointContacts":
        return [contact.id for contact in synastry.point_contacts]
    if source == "rulerInteractions":
        return [item.id for item in synastry.ruler_interactions]
    if source == "directionalThemes":
        return [
            evidence_id
            for theme in synastry.directional_themes
            for evidence_id in theme.evidence_ids
        ]
    if source == "aBodiesInBHouses":
        return [overlay.id for overlay in synastry.a_bodies_in_b_houses]
    if source == "bBodiesInAHouses":
        return [overlay.id for overlay in synastry.b_bodies_in_a_houses]
    return []


def build_report_outline(
    synastry: SynastryChart,
    score: RelationshipScore,
    profile: ReportProfile,
) -> ReportOutline:
    """Section identifiers, in order, with the evidence each rests on.

    No prose. A section whose sources are all empty is still emitted, marked
    unavailable with the reason, because a silently missing section reads as a
    topic that did not apply rather than one the geometry could not answer.
    """
    sections: list[ReportSectionResult] = []

    for section in sorted(profile.sections, key=lambda item: item.priority):
        evidence: list[str] = []
        empty_sources: list[str] = []
        for source in section.sources:
            found = _section_evidence(synastry, score, source, section.topic)
            if found:
                evidence.extend(found)
            elif source != "dimensions":
                empty_sources.append(source)

        score_ids: tuple[str, ...] = ()
        if "dimensions" in section.sources:
            score_ids = (
                tuple(item.dimension for item in score.dimensions)
                if section.topic == TOPIC_OVERALL
                else (section.topic,)
            )

        available = bool(evidence) or bool(score_ids)
        reason = None
        if not available:
            # Deduplicated: both overlay directions share a reason, and saying
            # it twice reads as two separate problems.
            reasons: list[str] = []
            for source in empty_sources:
                text = _SOURCE_REASONS.get(source, f"{source} is empty")
                if text not in reasons:
                    reasons.append(text)
            reason = "; ".join(reasons) or "no evidence for this section"

        # Capped like an evidence context, and for the same reason: a section
        # listing a hundred and thirty facts is a section nobody can render.
        # The full count travels alongside so the cap is visible.
        unique = sorted(set(evidence))
        sections.append(
            ReportSectionResult(
                section_id=section.id,
                priority=section.priority,
                topic=section.topic,
                evidence_ids=tuple(unique[: profile.maximum_evidence]),
                available_count=len(unique),
                truncated=len(unique) > profile.maximum_evidence,
                score_ids=score_ids,
                available=available,
                unavailable_reason=reason,
            )
        )

    return ReportOutline(
        profile=profile.id,
        profile_version=profile.version,
        sections=tuple(sections),
    )
