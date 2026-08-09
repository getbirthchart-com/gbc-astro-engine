"""Versioned orb profile for cross-chart aspects.

Why this exists at all
----------------------
Not because the natal orbs were measured to be wrong here. The hypothesis was
that synastry would be far denser than a natal chart, by analogy with transits,
where natal orbs left 27 to 44 aspects permanently active and forced a much
tighter profile. That hypothesis was tested and **did not hold**: across thirty
random pairs, natal orbs make 30.2% of the 144 ordered cross-pairs aspect,
against 30.9% of the 66 pairs in a natal chart. The rates are the same. Only the
absolute count is larger, because a full A-by-B product has more pairs than a
combination of one chart with itself.

The profile exists for a different and better reason: **decoupling**. While
synastry inherited the natal aspect profile, any future change to natal orbs
would silently move every cross aspect with it. That would change which contacts
exist, and therefore which evidence IDs exist, invalidating stored references and
scores that were computed against them. Synastry orbs have to be versioned on
their own so they change only when someone decides they should.

The values
----------
Measured over the same thirty pairs, the share of contacts sitting in the
outermost degree of their allowed orb:

    conjunction   11%
    sextile       21%   <- twice the others
    square        12%
    trine         16%
    opposition    10%

The sextile is the outlier. Five degrees is generous for the weakest of the
major aspects, and a fifth of all sextiles found were near-misses at the edge of
it. It is tightened by two degrees; everything else by one.

    natal      8 / 5 / 7 / 7 / 8    mean 43.4 contacts   (28-59)
    chosen     7 / 3 / 6 / 6 / 7    mean 35.0 contacts   (23-44)

The floor matters as much as the mean. Dimension scoring needs enough evidence
in every pair to populate every dimension, and a pair with too few contacts
produces empty dimensions that are indistinguishable from genuinely absent
themes. Twenty-three contacts is the worst case here; tightening further drops
the worst case into the teens, which is why the tighter options measured were
not taken.

Composite is not synastry
-------------------------
A composite chart is a chart: midpoint positions read the way a natal chart is
read. It keeps the natal orb profile, and the relationship profile therefore
carries both, rather than letting one setting govern two different things.
"""

from __future__ import annotations

from gbc_astro.profiles.model import AspectProfile, AspectRule

SYNASTRY_ASPECT_PROFILE_V1 = AspectProfile(
    id="synastry-major-v1",
    version="1.0.0",
    rules=(
        AspectRule("conjunction", 0.0, 7.0),
        AspectRule("sextile", 60.0, 3.0),
        AspectRule("square", 90.0, 6.0),
        AspectRule("trine", 120.0, 6.0),
        AspectRule("opposition", 180.0, 7.0),
    ),
)
