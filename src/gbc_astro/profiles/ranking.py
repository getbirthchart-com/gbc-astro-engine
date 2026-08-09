"""Versioned profile for ranking a pair's strongest and hardest contacts.

What the penalty actually buys, measured
----------------------------------------
The roadmap asks at V1.5 section 9 for a ranking that avoids returning five
near-duplicate contacts. The obvious reading is that a naive top five covers few
dimensions. Measured over thirty random pairs, that reading is wrong:

    penalty   distinct dimensions in top 5   commonest dimension's share
      1.00 (off)        5.10 of 6                      31%
      0.55              5.97 of 6                      25%

A plain sort already reaches five of six dimensions, because a single contact
touches several -- a Sun-Moon contact is emotional, growth and stability at
once -- so five contacts sprawl across nearly everything whatever the order.

The duplication a reader actually notices is **the same planet over and over**,
and that is where the penalty earns its place:

    penalty   distinct bodies in top 5   commonest body's share of 5 picks
      1.00 (off)      6.57                          2.57
      0.55            7.53                          2.10

Penalising a repeated dimension demotes a repeated body as a consequence,
because contacts that repeat a planet repeat its dimensions. The gain is real
and it is this, not the dimension coverage the section title suggests.

How diversity is produced
-------------------------
Greedy selection with a coverage penalty. Each contact is ranked by the total
magnitude it contributes across dimensions, and every time a dimension is
already represented by an earlier pick, later candidates touching that dimension
are multiplied by `diversity_penalty`. Two picks into the same dimension are
penalised twice, three times three, and so on.

Below 0.55 the measurements stop moving -- 0.30 and 0.10 give the same coverage
-- so a harsher penalty buys nothing and only makes the order harder to explain.

The alternative -- one pick per dimension, round robin -- was rejected because
it would promote a weak contact over a much stronger one purely for being
unrepresented, and would cap the list at the number of dimensions. A penalty
lets a genuinely dominant theme take two slots while still making the third
expensive.

Nothing is excluded. The penalty reorders; it never removes a contact from
consideration, so a pair whose whole story is one dimension still gets a full
list.

Why the ranking follows the relationship type
---------------------------------------------
The rank basis is the sum of the contact's *dimension* values, which already
carry both the dimension mapping and the relationship-type weight. So the top
contacts for a working relationship differ from those for a romantic one
without this profile knowing anything about relationship types. A contact that
speaks to no scored dimension ranks at zero, which is correct: it has no bearing
on anything being scored.

Challenging is not bad
----------------------
The two lists are separated by the sign of the contribution, and the hard list
is named for what it is -- friction, effort, the places a relationship has to be
worked at. The roadmap is explicit that challenging geometry must not be
labelled universally bad, and nothing here ranks a pair worse for having it. A
relationship with no hard contacts at all is usually one with nothing much
happening.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankingProfile:
    id: str
    version: str
    rationale: str
    # How many to return in each list.
    top_count: int
    # Multiplier applied to a candidate for each time one of its dimensions has
    # already been picked. 1.0 disables diversity entirely and reduces this to a
    # plain sort by strength.
    diversity_penalty: float
    # A contact touching no scored dimension ranks at zero rather than being
    # dropped, so the flag records that this is a decision.
    include_undimensioned: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "topCount": self.top_count,
            "diversityPenalty": self.diversity_penalty,
            "includeUndimensioned": self.include_undimensioned,
        }


SYNASTRY_RANKING_V1 = RankingProfile(
    id="synastry-ranking-v1",
    version="1.0.0",
    rationale=(
        "Contacts are ranked by the magnitude they contribute across dimensions, "
        "then penalised for repeating a dimension an earlier pick already "
        "covered. Measured over thirty pairs, this barely changes how many "
        "dimensions a top five covers -- a plain sort already reaches five of "
        "six -- but it cuts planet repetition, which is the duplication a reader "
        "actually notices: the commonest body falls from 2.57 of five picks to "
        "2.10. Below 0.55 the numbers stop moving. Because the rank basis is the "
        "dimension values, which already carry the relationship-type weight, a "
        "working relationship's top contacts differ from a romantic one's "
        "without this profile knowing that relationship types exist."
    ),
    top_count=5,
    diversity_penalty=0.55,
)
