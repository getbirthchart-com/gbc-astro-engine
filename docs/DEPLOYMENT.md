# Deployment

The engine is a stateless HTTP service. It holds no database, no chart IDs and
no user data: every request carries its own input and gets its answer back.
Scaling it is adding replicas.

## The one thing that will bite you

Ephemeris data is **not** in the image and **not** in the repository. Swiss
Ephemeris files and JPL kernels carry redistribution terms, so an image that
embedded them could not be pushed to a shared registry without checking those
terms first.

A container without that data **starts perfectly and then fails every chart
request**. That is why there are two probes:

| Probe | Answers | Use for |
|---|---|---|
| `GET /health` | is the process alive | liveness |
| `GET /ready` | can it actually calculate | readiness, load balancer |

`/ready` runs a real calculation through the provider. It returns:

- `200 ready` — everything available
- `200 degraded` — optional bodies missing, typically Chiron without
  `seas_18.se1`; core charts still work, so this does not take the service down
- `503 not_ready` — required data or the provider dependency is absent

Point your orchestrator's readiness probe at `/ready` and its liveness probe at
`/health`. Using `/health` for both is the mistake this section exists to
prevent: the service would be marked healthy while failing every request.

## Provision the data

```bash
./scripts/fetch-ephemeris.sh ./ephemeris
```

Fetches `sepl_18.se1`, `semo_18.se1` and `seas_18.se1` (about 2 MB total),
covering 1800–2399 which contains the v0.1 production range of 1900–2026.

Add `--with-jpl` to also fetch `de440s.bsp` (~32 MB). That kernel is only needed
to run the validation gates, never to serve a chart, so production does not need
it.

## Docker Compose

```bash
./scripts/fetch-ephemeris.sh ./ephemeris
docker compose up --build -d
curl -fsS localhost:8000/ready
```

The compose file mounts `./ephemeris` read-only and binds the port to
`127.0.0.1` only, on the assumption that a reverse proxy or the frontend's
server sits in front. Remove the `127.0.0.1:` prefix deliberately, not by
accident.

## Plain Docker

```bash
docker build -t gbc-astro-engine .
docker run -d --name gbc-engine \
  -p 127.0.0.1:8000:8000 \
  -v "$PWD/ephemeris:/opt/gbc/ephemeris:ro" \
  gbc-astro-engine
```

The image runs as a non-root user (uid 10001) and writes nothing at runtime, so
the filesystem can be mounted read-only if your platform supports it.

## Without Docker

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install ".[api,swiss]"
export GBC_SWISS_EPHE_PATH=/opt/gbc/ephemeris/swiss
uvicorn gbc_astro.api.app:app --host 0.0.0.0 --port 8000
```

## Environment

| Variable | Required | Notes |
|---|---|---|
| `GBC_SWISS_EPHE_PATH` | yes | Directory holding the `.se1` files |
| `GBC_JPL_EPHEMERIS_PATH` | no | Only for validation gates |
| `GBC_API_CORS_ORIGINS` | no | Comma-separated. **Leave unset** unless a browser genuinely calls this service directly |

CORS is off by default and should usually stay off. The intended path is
browser → Next.js server action → engine, so the browser never talks to this
service and no CORS header is needed.

## Platform notes

**Fly.io / Railway / Render** — mount a volume for `/opt/gbc/ephemeris` and run
the fetch script as a release step, or bake the data into a private image if
your registry is private and the licence terms permit it. Set the health check
path to `/ready`.

**Cloud Run** — no persistent volumes, so fetch the data into the image at build
time from a private registry, or mount a GCS bucket via the volume mount
feature. Set the startup probe to `/ready`.

**Kubernetes** — an init container running `scripts/fetch-ephemeris.sh` into an
`emptyDir` works well; use `/ready` for `readinessProbe` and `/health` for
`livenessProbe`.

## Before going live

Not implemented here, deliberately, because they belong to the deployment rather
than the engine:

- **Authentication.** The API is unauthenticated. If it is reachable from
  outside your network, put a proxy with an API key or mTLS in front of it.
- **Rate limiting.** Same.

Both were flagged as deployment concerns when the HTTP adapter was built, and
that has not changed. Do not expose this service to the public internet
unauthenticated.

## Verifying a deployment

```bash
curl -fsS "$URL/ready"                                  # must be 200 "ready"
curl -fsS -X POST "$URL/v1/charts/natal" \
  -H 'Content-Type: application/json' \
  -d '{"local_date":"1992-11-03","local_time":"14:35",
       "timezone":"Asia/Ho_Chi_Minh","latitude":21.0285,"longitude":105.8542}'
```

A `503` from `/ready` with `"status": "not_ready"` means the ephemeris volume is
not mounted where `GBC_SWISS_EPHE_PATH` points. The response says which files
are missing.

## What has and has not been verified

The wheel build, the extras install, the uvicorn entrypoint, all endpoints and
the healthcheck command were each executed from a clean virtual environment
built the same way the image builds. The Docker image itself has **not** been
built and run: no Docker daemon was available on the machine where this was
written. Build it once before relying on it.
