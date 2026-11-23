from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .extractor import extract_infotree, is_lean_available
from .fixtures import REPO_ROOT, get_curated_examples, list_example_summaries
from .schemas import (
    CreateSessionRequest,
    FlagRecord,
    LineRevision,
    LineStatus,
    ModelConfig,
    RegenerateLineRequest,
    RetranslateRequest,
    TranslationSession,
    UpdateLineRequest,
    utc_now_iso,
)
from .storage import (
    export_hitl_jsonl,
    export_session_latex,
    list_sessions,
    load_model_config,
    load_session,
    save_model_config,
    save_session,
)
from .translator import regenerate_single_line, translate_infotree

app = FastAPI(
    title="Lost In Translation API",
    version="0.1.0",
    description="Lean 4 InfoTree to Faithful LaTeX Workbench with Human-in-the-Loop Provenance Auditing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _session_response(session: TranslationSession) -> dict:
    data = session.model_dump()
    data["metrics"] = session.compute_metrics().model_dump()
    return data


@app.get("/api/health")
async def health() -> dict:
    cfg = load_model_config()
    symbolic_model = (
        "lit-symbolic-literal-v0.2"
        if cfg.symbolic_variant == "symbolic_literal_v0_2"
        else "lit-symbolic-literal-v0.1"
    )
    return {
        "status": "ok",
        "version": "0.1.0",
        "lean4_cli_available": is_lean_available(),
        "backend_mode": cfg.backend_mode,
        "symbolic_variant": cfg.symbolic_variant,
        "model_name": cfg.model_name if cfg.backend_mode == "openai_compatible_lm" else symbolic_model,
    }


@app.get("/api/examples")
async def get_examples() -> list[dict]:
    return [ex.model_dump() for ex in list_example_summaries()]


@app.get("/api/sessions")
async def get_sessions() -> list[dict]:
    sessions = list_sessions()
    return [
        {
            "session_id": s.session_id,
            "title": s.title,
            "subtitle": s.subtitle,
            "example_key": s.example_key,
            "updated_at": s.updated_at,
            "model_id": s.model_id,
            "metrics": s.compute_metrics().model_dump(),
        }
        for s in sessions
    ]


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest) -> dict:
    cfg = load_model_config()
    examples = get_curated_examples()

    if req.example_key:
        if req.example_key not in examples:
            raise HTTPException(status_code=404, detail=f"Unknown example_key '{req.example_key}'")
        ex = examples[req.example_key]
        infotree = ex.infotree.model_copy(deep=True)
        lines, eff_model = await translate_infotree(
            infotree=infotree,
            config=cfg,
            fidelity_mode=req.fidelity_mode,
            example_key=req.example_key,
        )
        session = TranslationSession(
            session_id=f"{req.example_key}-{uuid.uuid4().hex[:6]}",
            title=req.title or ex.title,
            subtitle=ex.subtitle,
            example_key=req.example_key,
            infotree=infotree,
            lines=lines,
            model_id=eff_model,
            backend_mode=cfg.backend_mode,
        )
        save_session(session)
        return _session_response(session)

    if not req.lean_source or not req.lean_source.strip():
        raise HTTPException(status_code=400, detail="Provide either example_key or non-empty lean_source.")

    infotree = extract_infotree(req.lean_source, symbolic_variant=cfg.symbolic_variant)
    lines, eff_model = await translate_infotree(
        infotree=infotree,
        config=cfg,
        fidelity_mode=req.fidelity_mode,
    )
    session = TranslationSession(
        session_id=f"custom-{uuid.uuid4().hex[:8]}",
        title=req.title or f"Proof: {infotree.theorem_name}",
        subtitle=f"Extracted via {infotree.extractor_mode}",
        example_key=None,
        infotree=infotree,
        lines=lines,
        model_id=eff_model,
        backend_mode=cfg.backend_mode,
    )
    save_session(session)
    return _session_response(session)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_response(session)


@app.patch("/api/sessions/{session_id}/lines/{line_id}")
async def update_line(session_id: str, line_id: str, req: UpdateLineRequest) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    line = next((pl for pl in session.lines if pl.line_id == line_id), None)
    if not line:
        raise HTTPException(status_code=404, detail="Proof line not found")

    if req.latex is not None and req.latex != line.latex:
        line.latex = req.latex
        line.revisions.append(
            LineRevision(
                revision_index=len(line.revisions),
                latex=req.latex,
                source="human_edit",
                model_id="human-reviewer",
                fidelity_mode=line.derivation.fidelity_mode,
                justification="Direct human LaTeX refinement in HITL workbench.",
            )
        )
        if req.status is None:
            line.status = LineStatus.EDITED

    if req.flag_categories:
        flag = FlagRecord(
            id=f"flg-{uuid.uuid4().hex[:6]}",
            categories=req.flag_categories,
            comment=(req.flag_comment or "").strip(),
            resolved=False,
        )
        line.flags.append(flag)
        line.status = LineStatus.FLAGGED

    if req.resolve_flags:
        for fl in line.flags:
            fl.resolved = True
        if line.status == LineStatus.FLAGGED and req.status is None:
            line.status = LineStatus.VERIFIED

    if req.status is not None:
        line.status = req.status
        if req.status == LineStatus.VERIFIED:
            for fl in line.flags:
                fl.resolved = True

    session.updated_at = utc_now_iso()
    save_session(session)
    return _session_response(session)


@app.post("/api/sessions/{session_id}/lines/{line_id}/regenerate")
async def regenerate_line(session_id: str, line_id: str, req: RegenerateLineRequest) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    line = next((pl for pl in session.lines if pl.line_id == line_id), None)
    if not line:
        raise HTTPException(status_code=404, detail="Proof line not found")

    cfg = load_model_config()
    try:
        new_latex, new_deriv = await regenerate_single_line(
            infotree=session.infotree,
            line=line,
            config=cfg,
            fidelity_mode=req.fidelity_mode,
            instruction=req.instruction,
            use_active_flags=req.use_active_flags,
            temperature_override=req.temperature,
            example_key=session.example_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}") from exc

    line.latex = new_latex
    line.derivation = new_deriv
    line.revisions.append(
        LineRevision(
            revision_index=len(line.revisions),
            latex=new_latex,
            source="regeneration",
            model_id=new_deriv.model_id,
            fidelity_mode=req.fidelity_mode,
            instruction=req.instruction,
            justification=new_deriv.justification,
        )
    )
    # Move back to unreviewed so the human verifies the newly regenerated output
    line.status = LineStatus.UNREVIEWED
    session.updated_at = utc_now_iso()
    save_session(session)
    return _session_response(session)


@app.post("/api/sessions/{session_id}/lines/{line_id}/revert/{rev_idx}")
async def revert_line_revision(session_id: str, line_id: str, rev_idx: int) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    line = next((pl for pl in session.lines if pl.line_id == line_id), None)
    if not line:
        raise HTTPException(status_code=404, detail="Proof line not found")
    rev = next((r for r in line.revisions if r.revision_index == rev_idx), None)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    line.latex = rev.latex
    line.status = LineStatus.EDITED if rev.source == "human_edit" else LineStatus.UNREVIEWED
    session.updated_at = utc_now_iso()
    save_session(session)
    return _session_response(session)


@app.post("/api/sessions/{session_id}/retranslate")
async def retranslate_session(session_id: str, req: RetranslateRequest) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cfg = load_model_config()
    infotree = extract_infotree(req.lean_source, symbolic_variant=cfg.symbolic_variant)
    lines, eff_model = await translate_infotree(
        infotree=infotree,
        config=cfg,
        fidelity_mode=req.fidelity_mode,
        example_key=session.example_key if req.lean_source.strip() == session.infotree.source_code.strip() else None,
    )
    session.infotree = infotree
    session.lines = lines
    session.model_id = eff_model
    session.backend_mode = cfg.backend_mode
    session.updated_at = utc_now_iso()
    save_session(session)
    return _session_response(session)


@app.get("/api/sessions/{session_id}/export/latex")
async def export_latex(session_id: str, provenance: bool = True) -> PlainTextResponse:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    content = export_session_latex(session, include_provenance=provenance)
    return PlainTextResponse(
        content=content,
        media_type="application/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{session.infotree.theorem_name}.tex"'},
    )


@app.get("/api/sessions/{session_id}/export/dataset")
async def export_dataset(session_id: str) -> PlainTextResponse:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    content = export_hitl_jsonl(session)
    return PlainTextResponse(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{session.infotree.theorem_name}_hitl.jsonl"'},
    )


@app.get("/api/config/model")
async def get_model_config() -> dict:
    return load_model_config().model_dump()


@app.put("/api/config/model")
async def update_model_config(cfg: ModelConfig) -> dict:
    save_model_config(cfg)
    return cfg.model_dump()


@app.post("/api/config/model/test")
async def test_model_connection(cfg: ModelConfig) -> dict:
    if cfg.backend_mode == "symbolic_baseline":
        variant_label = (
            "v0.2 (balanced-argument operators & Greek symbols)"
            if cfg.symbolic_variant == "symbolic_literal_v0_2"
            else "v0.1 (frozen token-level baseline)"
        )
        return {"ok": True, "detail": f"Built-in Symbolic-Literal {variant_label} active (zero external dependencies)."}
    url = cfg.base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
            models = [m.get("id", "") for m in payload.get("data", [])] if isinstance(payload, dict) else []
            return {
                "ok": True,
                "detail": f"Connected to {cfg.base_url}. Found {len(models)} model(s).",
                "available_models": models[:20],
            }
    except Exception as exc:
        return {"ok": False, "detail": f"Connection failed: {exc}", "available_models": []}


# Serve compiled frontend automatically when running production build
_DIST_DIR: Path = REPO_ROOT / "frontend" / "dist"
if _DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_DIST_DIR), html=True), name="frontend")
