# 04 — Canonical JSON Contract

## 1. Schema policy

- Stable public schema
- SemVer schema version
- additive changes preferred
- breaking changes require new major schema version
- values are machine-friendly; display strings belong to UI layer

## 2. Natal chart example

```json
{
  "schemaVersion": "1.0.0",
  "meta": {
    "engine": "gbc-astro",
    "engineVersion": "0.1.0",
    "ephemerisProvider": "swiss",
    "ephemerisDataVersion": "provider-reported",
    "timezoneDataVersion": "provider-reported",
    "calculationProfile": "western-modern-v1",
    "houseSystem": "placidus",
    "aspectProfile": "modern-major-v1",
    "zodiac": "tropical"
  },
  "subject": {
    "localDateTime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "utcDateTime": "1992-11-03T07:35:00Z",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "birthTimeKnown": true
  },
  "angles": {
    "ascendant": {
      "longitude": 0.0,
      "sign": "Aries",
      "degreeInSign": 0.0
    },
    "mc": {
      "longitude": 0.0,
      "sign": "Aries",
      "degreeInSign": 0.0
    },
    "descendant": {},
    "ic": {}
  },
  "bodies": {
    "sun": {
      "longitude": 0.0,
      "latitude": 0.0,
      "distance": null,
      "speedLongitude": 0.0,
      "retrograde": false,
      "sign": "Aries",
      "degreeInSign": 0.0,
      "house": 1
    }
  },
  "houses": [
    {
      "number": 1,
      "cuspLongitude": 0.0,
      "sign": "Aries",
      "degreeInSign": 0.0
    }
  ],
  "aspects": [
    {
      "a": "sun",
      "b": "moon",
      "type": "trine",
      "exactAngle": 120.0,
      "actualAngle": 118.8,
      "orb": 1.2,
      "phase": "applying"
    }
  ],
  "derived": {
    "bigThree": {
      "sun": "Scorpio",
      "moon": "Pisces",
      "rising": "Gemini"
    },
    "moonPhase": {},
    "elements": {},
    "modalities": {},
    "hemispheres": {},
    "quadrants": {}
  },
  "warnings": []
}
```

Numerical values above are placeholders in the schema example and must never be used as golden expected astronomy values.

## 3. Warning object

```json
{
  "code": "UNKNOWN_BIRTH_TIME",
  "severity": "warning",
  "message": "Time-sensitive chart fields were omitted.",
  "fieldsAffected": ["angles", "houses", "houseAssignments"]
}
```

## 4. Error object at API boundary

```json
{
  "error": {
    "code": "AMBIGUOUS_LOCAL_TIME",
    "message": "The supplied local datetime occurs twice due to a DST transition.",
    "details": {
      "timezone": "America/New_York",
      "localDateTime": "..."
    }
  }
}
```

## 5. Synastry contract

```json
{
  "schemaVersion": "1.0.0",
  "meta": {},
  "chartA": {},
  "chartB": {},
  "crossAspects": [],
  "aBodiesInBHouses": [],
  "bBodiesInAHouses": [],
  "angleInteractions": [],
  "warnings": []
}
```

## 6. Transit contract

```json
{
  "schemaVersion": "1.0.0",
  "meta": {},
  "natalChartId": null,
  "targetInstant": "...",
  "transitBodies": {},
  "transitToNatalAspects": [],
  "transitHousePlacements": [],
  "warnings": []
}
```

## 7. Event-search contract

```json
{
  "query": {
    "type": "planet_return",
    "body": "saturn",
    "from": "...",
    "to": "..."
  },
  "events": [
    {
      "instantUtc": "...",
      "longitude": 0.0,
      "direction": "direct",
      "precisionSeconds": 1
    }
  ]
}
```

## 8. Serialization requirements

- UTC timestamps use ISO 8601 `Z`
- local timestamps retain timezone separately
- no locale-formatted numbers in canonical JSON
- angles in decimal degrees
- UI may derive DMS formatting
- enums are lowercase stable identifiers
