"""Shared fixtures: a gateway on in-memory Qdrant and devices wired to it in-process.

Uses the HashEmbedder so tests need no model files, and TestClient as the device's HTTP
client, so device -> gateway sync runs through the real HTTP routes without a server.
"""
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.common.config import settings
from backend.common.log import Log
from backend.device.classifier import KeywordClassifier
from backend.device.core import Device
from backend.device.embed import HashEmbedder
from backend.device.hermes import Hermes
from backend.gateway.app import create_app
from backend.gateway.core import Gateway
from backend.gateway.server import FleetServer


def pytest_configure(config):
    # Fast local temp dir, wiped every run. Each Edge shard pre-allocates ~30-80 MB (WAL and
    # segments), so shards are also deleted as soon as each test finishes (see make_device).
    if not config.option.basetemp:
        config.option.basetemp = str(Path(tempfile.gettempdir()) / "smaran-pytest")


@pytest.fixture
def embedder():
    return HashEmbedder()


@pytest.fixture
def gateway(tmp_path, embedder):
    gw = Gateway(FleetServer(mode="embedded", path=":memory:"), tmp_path / "gw.db", lambda: embedder,
                 log=Log("gateway-test", tmp_path / "logs"))
    gw.seed(settings.path("seed/manuals"))
    return gw


@pytest.fixture
def gateway_client(gateway):
    return TestClient(create_app(gateway))


@pytest.fixture
def make_device(tmp_path, embedder, gateway_client):
    made = []

    def _make(device_id: str) -> tuple[Device, Hermes]:
        d = Device(device_id, tmp_path / f"device-{device_id}", embedder, KeywordClassifier(),
                   http=gateway_client, log=Log(f"device-{device_id}-test", tmp_path / "logs"))
        made.append(d)
        return d, Hermes(d)

    yield _make
    for d in made:
        d.close()
        shutil.rmtree(d.root, ignore_errors=True)


class FakeLLM:
    """Stands in for the local SLM / cloud model in tests."""
    kind = "fake"

    def __init__(self, reply="ok [1]", fail=False, model="fake-slm"):
        self.reply, self.fail, self.model, self.calls = reply, fail, model, []
        self.base_url = "fake://"

    def available(self, *a, **k):
        return True

    def chat(self, messages, json_mode=False, max_tokens=0):
        self.calls.append(messages)
        if self.fail:
            raise RuntimeError("model down")
        return self.reply


@pytest.fixture
def campus_gateway(tmp_path, embedder):
    """A gateway seeded with campus knowledge (the personal-companion domain)."""
    gw = Gateway(FleetServer(mode="embedded", path=":memory:"), tmp_path / "gw-campus.db", lambda: embedder,
                 log=Log("gateway-campus", tmp_path / "logs"))
    gw.seed(settings.path("seed/campus"))
    return gw


@pytest.fixture
def campus_client(campus_gateway):
    return TestClient(create_app(campus_gateway))


@pytest.fixture
def make_companion(tmp_path, embedder, campus_client):
    gateway_client = campus_client
    from backend.companion.llm import CloudLLM, GeminiLLM, ModelRouter
    from backend.companion.service import Companion
    from backend.device.classifier import PersonalClassifier
    made = []

    def _make(device_id="A", local=None, cloud=None, gemini=None, http="gateway", use_local=True):
        root = tmp_path / f"device-{device_id}"
        d = Device(device_id, root, embedder, PersonalClassifier(),
                   http=gateway_client if http == "gateway" else http, log=Log(f"dev-{device_id}", tmp_path / "logs"))
        router = ModelRouter(local=local or FakeLLM(fail=True), cloud=cloud or CloudLLM(),
                             gemini=gemini or GeminiLLM(), online=lambda: d.online,
                             use_local=use_local)
        c = Companion(d, Hermes(d), router)
        made.append(d)
        return c

    yield _make
    for d in made:
        d.close()
        shutil.rmtree(d.root, ignore_errors=True)
