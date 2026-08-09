"""Response schemas for the HTTP adapter.

Why these exist
---------------
Every v1 route returned a bare `JSONResponse`, so FastAPI had nothing to
describe and published `{}` as the response schema for all seventeen of them.
A client vendoring the contract got request types and no response types at all,
which left it hand-writing the shape of every chart from an example and hoping.
That is exactly the drift the two-repo split and the pinned contract exist to
prevent, and an empty schema silently defeats both.

Documentation only, never filtering
-----------------------------------
These are attached with `responses={200: {"model": ...}}`, not with
`response_model=`. The difference matters more than it looks: `response_model`
makes FastAPI *coerce the payload through the model*, so a field the model
forgot would be silently dropped from the response. A documentation defect
would become a data defect. Declaring them under `responses` publishes the
schema and leaves `to_dict()` the sole author of what is actually sent.

That trade has a cost -- nothing forces these to stay true -- so
`tests/api/test_response_schemas.py` validates real engine output against every
model here. The models cannot quietly disagree with the wire format, because
the payload the engine really produces has to satisfy them.

`extra="allow"` throughout, deliberately: these describe a floor, not a
ceiling. A caller can rely on every field named here being present, and the
engine can add fields in a minor release without any client's parser rejecting
the payload.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Schema(BaseModel):
    model_config = ConfigDict(extra="allow")


class AnglePayload(_Schema):
    longitude: float
    sign: str
    degreeInSign: float


class BodyPayload(_Schema):
    longitude: float
    latitude: float
    distance: float | None = None
    speedLongitude: float | None = None
    retrograde: bool | None = None
    sign: str
    degreeInSign: float
    house: int | None = Field(
        default=None,
        description="Null when the birth time is unknown, because there are no houses.",
    )


class HouseCuspPayload(_Schema):
    number: int
    cuspLongitude: float
    sign: str
    degreeInSign: float


class AspectPayload(_Schema):
    a: str
    b: str
    type: str
    exactAngle: float
    actualAngle: float
    orb: float
    phase: str = Field(
        description=(
            "applying, separating, exact, or indeterminate. Indeterminate is a "
            "real answer, not a failure: two natal charts share no timeline, so "
            "cross-aspects between them have no direction of travel."
        )
    )


class WarningPayload(_Schema):
    code: str
    severity: str
    message: str
    fieldsAffected: list[str]


class ChartMetaPayload(_Schema):
    """Provenance. Every input that shaped the numbers, so a result is reproducible."""

    engine: str
    engineVersion: str
    ephemerisProvider: str
    ephemerisDataVersion: str
    timezoneDataVersion: str
    calculationProfile: str
    houseSystem: str | None = None
    aspectProfile: str
    zodiac: str
    houseAlgorithmVersion: str | None = None
    rulershipProfile: str | None = None
    rulershipProfileVersion: str | None = None
    dominantProfile: str | None = None
    dominantProfileVersion: str | None = None
    ayanamsa: str | None = Field(
        default=None, description="Present only when zodiac is sidereal."
    )
    ayanamsaVersion: str | None = None
    ayanamsaDegrees: float | None = None


class ChartSubjectPayload(_Schema):
    localDateTime: str
    timezone: str
    utcDateTime: str
    julianDay: float
    latitude: float
    longitude: float
    altitudeM: float | None = None
    birthTimeKnown: bool
    calendar: str


class MoonPhasePayload(_Schema):
    phaseAngle: float
    name: str
    waxing: bool | None = None


class RulerPlacementPayload(_Schema):
    """A ruling planet and where it actually sits, not just its name."""

    body: str
    sign: str | None = None
    house: int | None = None
    longitude: float | None = None
    retrograde: bool | None = None


class HouseRulerPayload(_Schema):
    house: int
    cuspSign: str
    ruler: RulerPlacementPayload
    coRulers: list[str] = Field(
        default_factory=list,
        description=(
            "Classical rulers displaced by the modern table. Reported, but not "
            "used to walk a dispositor chain, which needs a single next step."
        ),
    )


class DignityPayload(_Schema):
    body: str
    sign: str
    state: str = Field(
        description=(
            "domicile, exaltation, detriment, fall, peregrine or unrated. "
            "unrated is not peregrine: it marks a body the scheme assigns no "
            "rulership to at all, which is a different statement from a body "
            "that has dignities and is in none of them."
        )
    )
    exactExaltation: bool = False


class DispositorChainPayload(_Schema):
    body: str
    chain: list[str]
    finalDispositor: str | None = Field(
        default=None,
        description="Null when the chain closes in a loop instead of a self-ruler.",
    )
    loop: list[str] = Field(
        default_factory=list,
        description=(
            "The planets ruling each other's signs in a closed cycle. A chart "
            "can consist entirely of these and legitimately have no final "
            "dispositor anywhere."
        ),
    )


class DominantPlanetPayload(_Schema):
    body: str
    score: float
    rank: int
    components: dict[str, float] = Field(
        description=(
            "The score broken into its parts. Published so a caller can see "
            "what made a planet dominant rather than being handed a number to "
            "trust; the weights themselves are in meta.dominantProfile."
        )
    )


class DerivedPayload(_Schema):
    bigThree: dict[str, str | None]
    moonPhase: MoonPhasePayload | dict[str, Any]
    elements: dict[str, int]
    modalities: dict[str, int]
    polarities: dict[str, int]
    hemispheres: dict[str, int]
    quadrants: dict[str, int]
    chartRuler: RulerPlacementPayload | None = Field(
        default=None,
        description="Null when the chart has no Ascendant, so no rising sign is invented.",
    )
    houseRulers: list[HouseRulerPayload] = Field(default_factory=list)
    dignities: list[DignityPayload] = Field(default_factory=list)
    dispositors: list[DispositorChainPayload] = Field(default_factory=list)
    finalDispositors: list[str] = Field(
        default_factory=list,
        description="Empty is a real result: every chain closed in a loop.",
    )
    mutualReceptions: list[list[str]] = Field(default_factory=list)
    dominantPlanets: list[DominantPlanetPayload] = Field(default_factory=list)


class NatalChartResponse(_Schema):
    """The canonical natal chart, returned directly rather than in an envelope."""

    schemaVersion: str
    meta: ChartMetaPayload
    subject: ChartSubjectPayload
    angles: dict[str, AnglePayload] = Field(
        description="Empty when the birth time is unknown. No substitute is used."
    )
    bodies: dict[str, BodyPayload]
    houses: list[HouseCuspPayload] = Field(
        description="Empty when the birth time is unknown."
    )
    aspects: list[AspectPayload]
    derived: DerivedPayload
    warnings: list[WarningPayload] = Field(default_factory=list)


class ChartPatternPayload(_Schema):
    id: str = Field(
        description=(
            "Stable and derived from the figure itself, so the same pattern in "
            "the same chart always carries the same id."
        )
    )
    type: str
    bodies: list[str]
    maxLegOrb: float = Field(
        description="The widest leg in the figure, so a caller can judge how loose it is."
    )
    detail: dict[str, Any] = Field(default_factory=dict)


class PatternsResponse(_Schema):
    patternCount: int
    patterns: list[ChartPatternPayload] = Field(
        description=(
            "Empty is a common and correct result. Contained figures are "
            "suppressed: every grand cross holds two T-squares and every kite "
            "holds a grand trine."
        )
    )
    profile: dict[str, Any] = Field(
        description="The pattern profile, including every orb that decided a match."
    )


# --- relationship -----------------------------------------------------------


class CrossAspectPayload(AspectPayload):
    """A natal aspect plus an evidence id.

    Cross-chart contacts carry one and natal aspects do not, because everything
    downstream of synastry -- score contributions, evidence bundles, the report
    outline, the timing layer's activation marks -- addresses facts by id.
    """

    id: str


class HouseOverlayPayload(_Schema):
    id: str
    body: str
    bodyChart: str
    houseChart: str
    house: int
    bodyLongitude: float


class AngleInteractionPayload(_Schema):
    id: str
    body: str
    bodyChart: str
    angle: str
    angleChart: str
    type: str
    exactAngle: float
    actualAngle: float
    orb: float


class SynastryResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    chartA: NatalChartResponse
    chartB: NatalChartResponse
    crossAspects: list[CrossAspectPayload] = Field(
        description=(
            "Phase is always indeterminate here. Two natal charts are two frozen "
            "instants and share no timeline, so applying and separating have "
            "nothing to describe. Use a Davison chart for a real direction of "
            "travel."
        )
    )
    aBodiesInBHouses: list[HouseOverlayPayload]
    bBodiesInAHouses: list[HouseOverlayPayload]
    angleInteractions: list[AngleInteractionPayload]
    warnings: list[WarningPayload] = Field(default_factory=list)


class MidpointPayload(_Schema):
    bodyId: str
    longitudeA: float
    longitudeB: float
    separation: float
    ambiguous: bool = Field(
        description=(
            "True at exactly 180 degrees, where the two midpoints are equally "
            "valid and the choice between them is arbitrary. Flagged rather than "
            "silently resolved."
        )
    )


class CompositeChartResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    angles: dict[str, AnglePayload]
    bodies: dict[str, BodyPayload]
    houses: list[HouseCuspPayload]
    aspects: list[AspectPayload]
    midpoints: list[MidpointPayload]
    warnings: list[WarningPayload] = Field(default_factory=list)


class DavisonOriginPayload(_Schema):
    utcDateTime: str
    latitude: float
    longitude: float


class DavisonChartResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    chart: NatalChartResponse = Field(
        description="An ordinary natal chart, because that is what a Davison chart is."
    )
    derivedFrom: DavisonOriginPayload
    warnings: list[WarningPayload] = Field(default_factory=list)


class ScoreTotalsPayload(_Schema):
    supportive: float
    challenging: float
    activity: float
    balance: float
    activityBand: str
    balanceBand: str


class DimensionScorePayload(_Schema):
    dimension: str
    supportive: float
    challenging: float = Field(description="Zero or negative. Never netted against supportive.")
    activity: float
    profileWeight: float = Field(
        default=1.0,
        description=(
            "The relationship-type multiplier already folded into the numbers "
            "above, published so it need not be divided back out."
        ),
    )
    contactCount: int = Field(
        description=(
            "Coverage. A dimension with no contacts is not a zero -- zero means "
            "the geometry is neutral, absent means it is silent, and a pair with "
            "an unknown birth time is silent about everything the angles would "
            "have said."
        )
    )
    evidenceIds: list[str]


class ScoreContributionPayload(_Schema):
    kind: str
    evidenceId: str = Field(
        description="The synastry fact this line scores, resolvable in the synastry result."
    )
    a: str
    b: str
    type: str
    orb: float
    aspectWeight: float
    pairWeight: float
    orbFactor: float
    value: float
    dimensionValues: dict[str, float] = Field(
        default_factory=dict,
        description="What this contact contributed to each dimension it speaks to.",
    )


class CompatibilityResponse(_Schema):
    """A published scoring scheme, not a verdict.

    Every contribution that produced the totals is itemised and every weight is
    in `profile`, so the number can be audited rather than trusted.
    """

    schemaVersion: str
    meta: dict[str, Any]
    totals: ScoreTotalsPayload
    contributionCount: int
    contributions: list[ScoreContributionPayload]
    dimensions: list[DimensionScorePayload]
    profile: dict[str, Any]
    dimensionProfile: dict[str, Any]
    relationshipTypeProfile: dict[str, Any] = Field(
        default_factory=dict,
        description="Which relationship type reweighted the dimensions, and by how much.",
    )
    notes: list[str] = Field(default_factory=list)


# --- transformed charts -----------------------------------------------------


class TransformedChartResponse(_Schema):
    """Draconic, harmonic, secondary progressions and solar arc share one shape."""

    schemaVersion: str
    transform: str
    transformVersion: str
    meta: dict[str, Any]
    subject: ChartSubjectPayload
    bodies: dict[str, BodyPayload]
    angles: dict[str, AnglePayload]
    aspects: list[AspectPayload]
    warnings: list[WarningPayload] = Field(default_factory=list)


# --- forecast ---------------------------------------------------------------


class TransitAspectPayload(_Schema):
    id: str
    transitBody: str
    natalTarget: str
    natalTargetKind: str = Field(description="body or angle.")
    natalBody: str
    type: str
    exactAngle: float
    actualAngle: float
    orb: float
    phase: str = Field(
        description=(
            "Real here, unlike synastry: the transiting body moves while the "
            "natal point stays put, so applying and separating describe "
            "something that is actually happening."
        )
    )
    score: float
    rank: int


class TransitHousePlacementPayload(_Schema):
    transitBody: str
    natalHouse: int
    longitude: float


class TransitChartResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    targetInstant: str
    transitBodies: dict[str, BodyPayload]
    transitToNatalAspects: list[TransitAspectPayload]
    topAspects: list[TransitAspectPayload] = Field(
        description="The highest-ranked contacts under the published ranking profile."
    )
    transitHousePlacements: list[TransitHousePlacementPayload]
    warnings: list[WarningPayload] = Field(default_factory=list)


class ReturnHitPayload(_Schema):
    ordinal: int
    instantUtc: str
    julianDay: float
    longitude: float
    direction: str
    precisionSeconds: float
    chart: NatalChartResponse | None = None


class WindowPayload(_Schema):
    start: str
    end: str


class ReturnSearchResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    body: str
    natalLongitude: float
    window: WindowPayload
    hitCount: int
    hits: list[ReturnHitPayload] = Field(
        description=(
            "All of them, in order. A body stationing near its natal degree "
            "crosses it three times and each crossing is a real return. An empty "
            "list means the window was searched exhaustively and holds none."
        )
    )
    warnings: list[WarningPayload] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AstroEventPayload(_Schema):
    type: str
    body: str
    instantUtc: str
    julianDay: float
    longitude: float
    direction: str
    precisionSeconds: float = Field(
        description=(
            "How tightly the root was bracketed. Instants come from bisection, "
            "never from the nearest ephemeris sample."
        )
    )
    detail: dict[str, Any] = Field(default_factory=dict)


class EventQueryPayload(_Schema):
    type: str
    body: str
    # `from` is a Python keyword, so the wire name is carried by an alias rather
    # than left out of the schema, which would have hidden half the window.
    from_: str = Field(alias="from")
    to: str
    targetLongitude: float | None = None
    aspectAngle: float | None = None


class EventSearchResponse(_Schema):
    schemaVersion: str
    meta: dict[str, Any]
    query: EventQueryPayload
    eventCount: int
    events: list[AstroEventPayload]
    warnings: list[WarningPayload] = Field(default_factory=list)


# --- tables and maps --------------------------------------------------------


class EphemerisRowPayload(_Schema):
    instantUtc: str
    julianDay: float
    bodies: dict[str, BodyPayload]


class EphemerisResponse(_Schema):
    version: str
    engine: str
    engineVersion: str
    ephemerisProvider: str
    ephemerisDataVersion: str
    zodiac: str
    ayanamsa: str | None = None
    bodies: list[str]
    range: dict[str, Any]
    rowCount: int
    rows: list[EphemerisRowPayload]
    notes: list[str] = Field(default_factory=list)


class AcgPointPayload(_Schema):
    latitude: float
    longitude: float


class AcgLinePayload(_Schema):
    id: str
    body: str
    angle: str = Field(description="mc, ic, ascendant or descendant.")
    kind: str = Field(
        description=(
            "meridian for the MC and IC lines, which are straight; horizon for "
            "the rising and setting lines, which are not."
        )
    )
    pointCount: int
    points: list[AcgPointPayload]
    detail: dict[str, Any] = Field(default_factory=dict)


class AstrocartographyResponse(_Schema):
    """Where each body is angular on Earth for this chart's instant.

    A physical fact, so the lines do not move when the chart's zodiac changes.
    """

    version: str
    engine: str
    engineVersion: str
    method: str
    chartInstant: str
    siderealTimeDeg: float
    obliquity: float
    latitudeRange: list[float]
    latitudeStep: float
    lineCount: int
    lines: list[AcgLinePayload]
    notes: list[str] = Field(default_factory=list)


class OptionalBodyPayload(_Schema):
    bodyId: str
    available: bool = Field(
        description="Probed against the installed data files, not assumed."
    )
    kind: str
    reason: str | None = None


class CapabilitiesResponse(_Schema):
    coreBodies: list[str]
    optionalBodies: list[OptionalBodyPayload]
    optionalBodyNames: list[str]
    houseSystems: list[dict[str, Any]]
    ayanamsas: list[dict[str, Any]]
    numberedAsteroidFormat: str
