"""Stable package constants."""

ENGINE_NAME = "gbc-astro"
# Distribution/PyPI version. Independent of ENGINE_VERSION so a packaging
# release can ship without claiming new calculation behavior.
PACKAGE_VERSION = "1.12.2"
ENGINE_VERSION = "1.12.1"
SCHEMA_VERSION = "1.3.0"
SYNASTRY_SCHEMA_VERSION = "1.4.0"
COMPOSITE_SCHEMA_VERSION = "1.2.1"
DAVISON_SCHEMA_VERSION = "1.0.0"
SCORE_SCHEMA_VERSION = "1.3.0"
TRANSIT_SCHEMA_VERSION = "1.1.0"
EVENT_SCHEMA_VERSION = "1.0.0"
RETURN_SCHEMA_VERSION = "1.0.0"
TRANSFORM_SCHEMA_VERSION = "1.0.0"

BODY_IDS = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_node",
    "mean_node",
    "chiron",
)

# Bodies eligible to form an aspect. Narrower than BODY_IDS on purpose: a
# chart publishes both the true and the mean lunar node, but they are one point
# computed two ways, about a degree apart. Letting both aspect would double
# every node contact and put a content-free "node conjunct node" in every chart.
# The true node is the one carried here because it is the position the node
# actually holds; the mean node stays available in `bodies` for callers who
# want the smoothed value.
ASPECT_BODIES = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_node",
    "chiron",
)

CLASSICAL_BALANCE_BODIES = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)

SIGN_IDS = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

