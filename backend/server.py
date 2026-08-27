"""
FastAPI Server and Web Dashboard for Congressional Civic Analytics & Dossiers
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, VIDEOS_DIR, CARDS_DIR
from backend.models import CongressionalProfile, FullLeaderboardResponse
from backend.ingestion.congress_api import search_members, get_category_deep_dive_bills
from backend.analytics.constituent_sync import build_district_deep_dive_dossier
from backend.analytics.scouting_model import (
    build_full_profile,
    get_full_leaderboard,
    generate_head_to_head_comparison
)
from backend.scheduler import (
    get_sync_status,
    run_data_sync,
    weekly_sync_loop
)
from backend.video_engine.video_assembler import render_scouting_video
from backend.video_engine.graphics_generator import generate_all_slides

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start automated background sync task (runs every Saturday at 02:00 UTC)
    sync_task = asyncio.create_task(weekly_sync_loop())
    yield
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Congressional Civic Analytics API",
    description="High-resolution voting records, district demographic correlations, and policy vertical dossiers for US Congress members.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# CORE API ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/system/status")
async def api_system_status():
    """Retrieve data synchronization status and last/next scheduled update times."""
    return get_sync_status()

@app.post("/api/admin/sync")
async def api_admin_sync():
    """Trigger on-demand data synchronization across all 537 Congress members."""
    try:
        result = await run_data_sync()
        return result
    except Exception as e:
        logger.exception("Manual data sync failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1)):
    """Search for Congress members by name, state, chamber, or district."""
    results = search_members(q)
    return {"query": q, "count": len(results), "results": results}

@app.get("/api/profile/{bioguide_id}")
async def api_profile(bioguide_id: str, timeframe: str = Query("career")):
    """Retrieve full lawmaker dossier, performance indicators, constituent sync, and voting breakdown."""
    try:
        profile = build_full_profile(bioguide_id, timeframe=timeframe)
        return profile.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to build profile")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/district-dossier/{bioguide_id}")
async def api_district_dossier(bioguide_id: str, timeframe: str = Query("career")):
    """Retrieve exhaustive District Demographics Deep-Dive correlating Census ACS data to the lawmaker's voting record."""
    try:
        profile = build_full_profile(bioguide_id, timeframe=timeframe)
        dossier = build_district_deep_dive_dossier(profile.constituents, profile.voting, profile.bio)
        return dossier.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate district dossier")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/category/{bioguide_id}/{category_name}")
async def api_category_deep_dive(bioguide_id: str, category_name: str, timeframe: str = Query("career")):
    """Retrieve comprehensive bill listings, plain-English summaries, and vote breakdowns for a policy vertical."""
    try:
        deep_dive = get_category_deep_dive_bills(bioguide_id, category_name, timeframe=timeframe)
        return deep_dive.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to fetch category deep-dive for {category_name}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compare")
async def api_compare(
    m1: str = Query(..., description="First Bioguide ID"),
    m2: str = Query(..., description="Second Bioguide ID"),
    timeframe: str = Query("career")
):
    """Generate head-to-head policy and voting comparison between two members of Congress."""
    try:
        comparison = generate_head_to_head_comparison(m1, m2, timeframe=timeframe)
        return comparison.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate head-to-head comparison")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leaderboard")
async def api_leaderboard():
    """Retrieve full category leaderboards partitioned by Democrats vs Republicans with Independents spotlight."""
    try:
        leaderboards = get_full_leaderboard()
        return leaderboards.model_dump()
    except Exception as e:
        logger.exception("Failed to generate leaderboards")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# VIDEO & GRAPHICS ENGINE ENDPOINTS
# -------------------------------------------------------------
class VideoGenerationRequest(BaseModel):
    bioguide_id: str
    format: str = "shorts"  # "shorts" (9:16) or "broadcast" (16:9)
    fps: int = 24

@app.post("/api/video/generate")
async def api_generate_video(req: VideoGenerationRequest):
    """Trigger automated video generation for a lawmaker."""
    try:
        profile = build_full_profile(req.bioguide_id)
        is_vertical = req.format.lower() == "shorts"
        
        video_path = render_scouting_video(profile, is_vertical=is_vertical, fps=req.fps)
        
        member_slug = profile.bio.full_name.lower().replace(" ", "_")
        orientation = "shorts" if is_vertical else "broadcast"
        filename = f"{member_slug}_{orientation}.mp4"
        
        return {
            "status": "success",
            "member": profile.bio.full_name,
            "format": req.format,
            "filename": filename,
            "video_url": f"/api/video/{filename}",
            "file_size_bytes": video_path.stat().st_size
        }
    except Exception as e:
        logger.exception("Failed to generate video")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/video/{filename}")
async def api_stream_video(filename: str):
    """Stream or download a rendered MP4 video."""
    video_file = VIDEOS_DIR / filename
    if not video_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(path=video_file, media_type="video/mp4", filename=filename)

@app.get("/api/card/{member_slug}/{orientation}/{slide_name}")
async def api_get_card(member_slug: str, orientation: str, slide_name: str):
    """Retrieve generated PNG slide graphic."""
    card_file = CARDS_DIR / f"{member_slug}_{orientation}" / f"{slide_name}.png"
    if not card_file.exists():
        raise HTTPException(status_code=404, detail="Slide image not found")
    return FileResponse(path=card_file, media_type="image/png")

# -------------------------------------------------------------
# STATIC WEB APPLICATION
# -------------------------------------------------------------
WEB_DIR = BASE_DIR / "web"
if (WEB_DIR / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = BASE_DIR / "web" / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Congressional Civic Analytics Dashboard</h1>")
