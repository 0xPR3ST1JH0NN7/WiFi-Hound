"""REST API for WiFi-Hound."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from wifihound import parsers
from wifihound.enrichment import oui
from wifihound.graph import WifiGraph
from wifihound.operations import OperationError, deauth as deauth_op, offensive_enabled

router = APIRouter(prefix="/api")

# Single in-memory graph for the running session.
STATE = WifiGraph()


# --------------------------------------------------------------------- import
@router.post("/import")
async def import_capture(file: UploadFile = File(...)):
    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="ignore")
    parser = parsers.detect_parser(text, file.filename or "")
    if parser is None:
        raise HTTPException(
            status_code=415,
            detail="Unrecognized capture format. Supported: "
            + ", ".join(p.name for p in parsers.all_parsers()),
        )
    scan = parser.parse(text, file.filename or "")
    oui.enrich_scan(scan)  # vendors are cheap and offline — do it on import
    STATE.load(scan)
    return {
        "summary": STATE.stats(),
        "parser": parser.id,
        **STATE.to_cytoscape(),
    }


# ---------------------------------------------------------------------- reads
@router.get("/graph")
def get_graph():
    return {"summary": STATE.stats(), **STATE.to_cytoscape()}


@router.get("/stats")
def get_stats():
    return STATE.stats()


@router.get("/parsers")
def get_parsers():
    return [{"id": p.id, "name": p.name, "extensions": list(p.extensions)}
            for p in parsers.all_parsers()]


@router.get("/node/{node_id}")
def get_node(node_id: str):
    info = STATE.node(node_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return info


@router.get("/search")
def search(q: str = ""):
    return {"query": q, "results": STATE.search(q)}


@router.get("/path")
def path(source: str, target: str):
    return {"source": source, "target": target,
            "path": STATE.path(source, target)}


@router.get("/config")
def config():
    return {"offensive_enabled": offensive_enabled()}


# ------------------------------------------------------------------ enrichment
@router.post("/enrich/oui")
def enrich_oui():
    if STATE.scan is None:
        raise HTTPException(status_code=400, detail="No capture loaded")
    resolved = oui.enrich_scan(STATE.scan)
    STATE.load(STATE.scan)  # rebuild so vendor flows into the graph elements
    return {"resolved": resolved, **STATE.to_cytoscape()}


# ------------------------------------------------------------------ offensive
class DeauthRequest(BaseModel):
    interface: str
    bssid: str
    client: str | None = None
    count: int = 5
    acknowledged: bool = False
    dry_run: bool = False


@router.post("/operations/deauth")
def operations_deauth(req: DeauthRequest):
    try:
        return deauth_op.deauth(
            interface=req.interface,
            bssid=req.bssid,
            client=req.client,
            count=req.count,
            acknowledged=req.acknowledged,
            dry_run=req.dry_run,
        )
    except OperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
