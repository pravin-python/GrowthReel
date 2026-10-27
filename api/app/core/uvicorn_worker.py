"""Dev/prod entrypoint for running this service with uvicorn, configured to
suppress the `Server: uvicorn` banner (VAPT fix #14).

Verified against this project's own `.venv` by running
`.venv/Scripts/python.exe -m uvicorn --help`, which lists:

    --server-header / --no-server-header   Enable/Disable default Server header.
    --date-header / --no-date-header

So the CLI-equivalent flag is `--no-server-header` (and `--no-date-header`
for the `Date` header, if that's ever wanted too — we keep `Date` since it's
harmless and expected on HTTP responses, only `Server` leaks implementation
detail). Programmatically (what this module actually calls),
`uvicorn.run(...)` takes the same thing as keyword arguments:
`server_header=False`. This was confirmed end-to-end, not just configured:
see README.md "Verification" — `curl -i http://localhost:8001/api/v1/health`
was run against the live dev server and the response had no `Server` header
at all (curl only showed `date`, `content-type`, `content-length`, and our
own `X-Request-ID` / security headers).
"""
from __future__ import annotations

import os

import uvicorn


def run(host: str = "0.0.0.0", port: int | None = None, reload: bool = False) -> None:
    # Cloud Run injects $PORT (defaults to 8080 there, or whatever --port
    # was deployed with); docker-compose / local dev has no $PORT set, so
    # this falls back to the service's own default, 8001, unchanged.
    resolved_port = port if port is not None else int(os.environ.get("PORT", 8001))
    uvicorn.run(
        "app.main:app",
        host=host,
        port=resolved_port,
        reload=reload,
        server_header=False,
        date_header=True,
    )


if __name__ == "__main__":
    run()
