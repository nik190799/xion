"""FastAPI surface for xion-ops.

The server is intentionally localhost-first. Public exposure and stronger
operator auth are separate production hardening work; this surface exists so
local dashboards, CI, and future runtime callers do not shell out.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from xion_ops.jobs import JobRunner
from xion_ops.registry import get_deployer, get_service, service_names
from xion_ops.types import DeployContext

try:  # pragma: no cover - import guard keeps CLI usable without api extra.
    from fastapi import Depends, FastAPI, Header, HTTPException
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    Depends = Header = HTTPException = None  # type: ignore[assignment]


runner = JobRunner(repo_root=Path("."))


def create_app():
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("xion-ops-server requires the FastAPI optional dependency")

    app = FastAPI(title="xion-ops", version="0.1.0")

    def _auth(authorization: str | None = Header(default=None)) -> None:
        expected = os.environ.get("XION_OPS_BEARER")
        if expected and authorization != f"Bearer {expected}":
            raise HTTPException(status_code=401, detail="unauthorized")
        if not expected:
            raise HTTPException(status_code=503, detail="XION_OPS_BEARER is not configured")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/services", dependencies=[Depends(_auth)])
    def services() -> dict[str, Any]:
        return {"services": service_names()}

    @app.get("/balances", dependencies=[Depends(_auth)])
    def balances() -> list[dict[str, Any]]:
        from xion_ops.cli import _report_to_dict

        reports = []
        for name in service_names():
            reports.extend(get_service(name).balances())
        return [_report_to_dict(report) for report in reports]

    @app.get("/balances/{service}", dependencies=[Depends(_auth)])
    def service_balances(service: str) -> list[dict[str, Any]]:
        from xion_ops.cli import _report_to_dict

        return [_report_to_dict(report) for report in get_service(service).balances()]

    @app.get("/services/{service}/health", dependencies=[Depends(_auth)])
    def service_health(service: str) -> dict[str, Any]:
        return get_service(service).health().__dict__

    @app.post("/akash/deploy", dependencies=[Depends(_auth)])
    def akash_deploy(body: dict[str, Any]) -> dict[str, Any]:
        job = runner.start(
            "akash.deploy",
            lambda: get_deployer("relay-akash").run(DeployContext(repo_root=Path("."), params=body)),
        )
        return {"job_id": job.id}

    @app.post("/akash/close", dependencies=[Depends(_auth)])
    def akash_close(body: dict[str, Any]) -> dict[str, Any]:
        result = get_service("akash").close_deployment(str(body["dseq"]))  # type: ignore[attr-defined]
        return {"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}

    @app.post("/arweave/publish/{kind}", dependencies=[Depends(_auth)])
    def arweave_publish(kind: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = body or {}
        job = runner.start(
            f"arweave.publish.{kind}",
            lambda: get_service("arweave").publish_kind(kind, payload.get("path")),  # type: ignore[attr-defined]
        )
        return {"job_id": job.id}

    @app.post("/chutes/deploy", dependencies=[Depends(_auth)])
    def chutes_deploy(body: dict[str, Any]) -> dict[str, Any]:
        job = runner.start(
            "chutes.deploy",
            lambda: get_deployer("relay-chutes").run(DeployContext(repo_root=Path("."), params=body)),
        )
        return {"job_id": job.id}

    @app.post("/base-evm/deploy/{contract}", dependencies=[Depends(_auth)])
    def base_evm_deploy(contract: str, body: dict[str, Any]) -> dict[str, Any]:
        params = dict(body)
        params["contract"] = contract
        job = runner.start(
            f"base-evm.deploy.{contract}",
            lambda: get_deployer("base-contracts").run(DeployContext(repo_root=Path("."), params=params)),
        )
        return {"job_id": job.id}

    @app.post("/deploy/{deployer}", dependencies=[Depends(_auth)])
    def deploy(deployer: str, body: dict[str, Any]) -> dict[str, Any]:
        job = runner.start(
            f"deploy.{deployer}",
            lambda: get_deployer(deployer).run(DeployContext(repo_root=Path("."), params=body)),
        )
        return {"job_id": job.id}

    @app.get("/jobs/{job_id}", dependencies=[Depends(_auth)])
    def job(job_id: str) -> dict[str, Any]:
        record = runner.get(job_id)
        if not record:
            raise HTTPException(status_code=404, detail="job not found")
        return record.to_dict()

    @app.get("/deployment-records", dependencies=[Depends(_auth)])
    def deployment_records() -> list[dict[str, Any]]:
        root = Path("genesis/DEPLOYMENT_RECORDS")
        if not root.exists():
            return []
        records = []
        for path in sorted(root.glob("*.json")):
            if path.name == "jobs.jsonl":
                continue
            records.append(json.loads(path.read_text(encoding="utf-8")))
        return records

    return app


app = create_app() if FastAPI is not None else None


def main() -> None:
    import uvicorn

    uvicorn.run("xion_ops.server:app", host="127.0.0.1", port=9100)

