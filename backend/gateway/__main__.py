"""Gateway entry point, run from the repo root:

    python -m backend.gateway                       # Qdrant Server from .env (Docker)
    python -m backend.gateway --qdrant embedded     # no Docker: qdrant-client local mode
"""
import argparse
import os

import uvicorn

from ..common.config import settings
from ..common.log import Log
from ..device.embed import get_embedder
from .app import create_app
from .core import Gateway
from .server import FleetServer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=settings.gateway_port)
    ap.add_argument("--qdrant", choices=["server", "embedded"], default=settings.qdrant_mode)
    ap.add_argument("--embedder", default="fastembed", choices=["fastembed", "hash"])
    args = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    log = Log("gateway")
    gw = Gateway(FleetServer(mode=args.qdrant), settings.path(settings.runtime_dir) / "gateway" / "gateway.db",
                 lambda: get_embedder(args.embedder), log=log)
    log("start", port=args.port, server=gw.server.describe())
    uvicorn.run(create_app(gw), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
