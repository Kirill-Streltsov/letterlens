# Development

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | any | Docker Desktop |
| uv | 0.5 or later | `pip install uv` or `brew install uv` |
| Node.js | 22 or later | `brew install node` |
| Xcode | 26 or later (iOS only) | App Store; then `brew install xcodegen` |

## Run locally

```bash
make seed    # PostgreSQL in Docker (port 5433), migrations, demo data
make api     # http://localhost:8000, API docs at /docs
make web     # http://localhost:3000
```

The local API uses the offline model provider and the dev authentication. Sign in
as `demo-client` or `counsellor-anna`.

To use a real model locally:

