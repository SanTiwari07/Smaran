"""Device entry point, run from the repo root:

    python -m backend.device --id A            # port from .env (DEVICE_A_PORT, default 8001)
    python -m backend.device --id C --port 8003
"""
import argparse
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")   # the device never needs the internet

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from ..common.config import settings  # noqa: E402
from ..common.log import Log  # noqa: E402
from .app import create_app  # noqa: E402
from .classifier import load_classifier  # noqa: E402
from .core import Device  # noqa: E402
from .embed import get_embedder  # noqa: E402
from .hermes import Hermes  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--port", type=int)
    ap.add_argument("--embedder", default="fastembed", choices=["fastembed", "hash"])
    ap.add_argument("--classifier", default="auto", choices=["auto", "logreg", "rules"])
    args = ap.parse_args()

    port = args.port or settings.device_ports.get(args.id, 8000 + ord(args.id[0]) - 64)
    log = Log(f"device-{args.id}")
    http = httpx.Client(base_url=settings.gateway_url, timeout=5.0)
    device = Device(args.id, settings.path(settings.runtime_dir) / f"device-{args.id}",
                    get_embedder(args.embedder), load_classifier(args.classifier), http=http, log=log)
    log("start", port=port, gateway=settings.gateway_url, classifier=device.classifier.name)
    uvicorn.run(create_app(device, Hermes(device)), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
