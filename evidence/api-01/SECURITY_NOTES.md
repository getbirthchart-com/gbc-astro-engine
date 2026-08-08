# Security Notes — API-01

- **Stateless:** no chart persistence, no database, no Redis
- **No geocoder:** requires resolved lat/lng/timezone
- **CORS:** disabled by default; optional explicit `GBC_API_CORS_ORIGINS`
- **Logging:** operational fields only (duration, error code, unknown_time flag). Does not log full birth date/time/coordinates payloads
- **Errors:** unexpected exceptions return `INTERNAL_ERROR` without stack traces to clients
- **Secrets:** none required for natal calculation beyond optional ephemeris path env
- **Network auth / rate limits:** deployment concern for production exposure
- **Preferred topology:** Browser → Next.js server → this API (not direct browser CORS `*`)
