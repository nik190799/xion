"""CLI tests for relay registry Chutes row updates."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from xion_ops import cli


def _sample_registry(tmp_path: Path) -> Path:
    p = tmp_path / "RELAY_REGISTRY.json"
    payload = {
        "as_of_utc_ns": 1,
        "payload_sha256": "old",
        "relays": [
            {"substrate": "akash", "endpoint": "https://akash.example:443"},
            {
                "substrate": "chutes",
                "endpoint": "https://old.chutes.ai",
                "chute_id": "c0",
                "image_id": "i0",
                "image_tag": "t0",
                "relay_id": "relay-chutes-test",
                "service": "xion-relay-chutes",
            },
        ],
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_registry_update_chutes_row_patches_relay(tmp_path: Path) -> None:
    path = _sample_registry(tmp_path)
    runner = CliRunner()
    res = runner.invoke(
        cli.main,
        [
            "registry",
            "update-chutes-row",
            "--endpoint",
            "https://nikhilkadalge-example.chutes.ai",
            "--chute-id",
            "89866bfc-5ddd-5382-b887-116d8901808f",
            "--image-id",
            "img-1",
            "--image-tag",
            "tag-9",
            "--instance-id",
            "inst-1",
            "--path",
            str(path),
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(path.read_text(encoding="utf-8"))
    row = data["relays"][1]
    assert row["endpoint"] == "https://nikhilkadalge-example.chutes.ai"
    assert row["chute_id"] == "89866bfc-5ddd-5382-b887-116d8901808f"
    assert row["instance_id"] == "inst-1"
    assert data["payload_sha256"] != "old"


def test_registry_update_chutes_row_rejects_non_chutes_substrate(tmp_path: Path) -> None:
    path = _sample_registry(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["relays"][1]["substrate"] = "akash"
    path.write_text(json.dumps(data), encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(
        cli.main,
        [
            "registry",
            "update-chutes-row",
            "--endpoint",
            "https://x.chutes.ai",
            "--chute-id",
            "89866bfc-5ddd-5382-b887-116d8901808f",
            "--image-id",
            "img",
            "--image-tag",
            "tag",
            "--path",
            str(path),
        ],
    )
    assert res.exit_code != 0
