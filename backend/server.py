"""
FastAPI Server and Web Dashboard for Congressional Civic Analytics & Dossiers
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, VIDEOS_DIR, CARDS_DIR
from backend.models import (
    CongressionalProfile, 
    FullLeaderboardResponse,
    MethodologyDocumentationResponse,
    MethodologyDataSource,
    MethodologyFormulaDoc
)
from backend.ingestion.congress_api import search_members, get_category_deep_dive_bills
from backend.ingestion.committees_data import get_committee_dossier
from backend.analytics.constituent_sync import build_district_deep_dive_dossier
from backend.analytics.scouting_model import (
    build_full_profile,
    get_full_leaderboard,
    generate_head_to_head_comparison,
    generate_rating_breakdown,
    get_all_party_rankings
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
# HEALTH & SYSTEM STATUS ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "congress-civic-analytics", "version": "2.4.0"}

@app.get("/api/system/status")
async def system_status():
    """Return database ingestion status, last sync timestamp, and next scheduled update."""
    return get_sync_status()

@app.post("/api/admin/sync")
async def trigger_manual_sync(background_tasks: BackgroundTasks):
    """Trigger on-demand data refresh across all roll calls, committees, and census metrics."""
    try:
        res = await run_data_sync()
        return {"status": "success", "message": "Manual data synchronization complete", "sync_details": res}
    except Exception as e:
        logger.exception("Manual sync failed")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# LAWMAKER SEARCH & PROFILES
# -------------------------------------------------------------
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

@app.get("/api/rating-breakdown/{bioguide_id}")
async def api_rating_breakdown(bioguide_id: str, timeframe: str = Query("career")):
    """Retrieve comprehensive 5-pillar mathematical score explanation, positive drivers, and deductions."""
    try:
        profile = build_full_profile(bioguide_id, timeframe=timeframe)
        breakdown = generate_rating_breakdown(
            profile.bio,
            profile.scouting,
            profile.affiliations,
            profile.voting,
            profile.finance,
            profile.legislative_pipeline,
            profile.donor_influence,
            profile.alignment,
            profile.constituents
        )
        return breakdown.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate rating breakdown")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/committee/{committee_name}")
async def api_committee_dossier(committee_name: str):
    """Retrieve full Committee & Caucus dossier including jurisdiction, agency oversight, leadership, and member rosters."""
    try:
        dossier = get_committee_dossier(committee_name)
        return dossier.model_dump()
    except Exception as e:
        logger.exception(f"Failed to fetch committee dossier for {committee_name}")
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

@app.get("/api/party-rankings")
async def api_party_rankings():
    """Retrieve full roster of lawmakers with 5-pillar scores, output pipeline, and civic metrics for interactive party filtering & sorting."""
    try:
        rankings = get_all_party_rankings()
        return rankings.model_dump()
    except Exception as e:
        logger.exception("Failed to generate party rankings")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# OPEN METHODOLOGY & DATA SOURCES CITATION ENDPOINT
# -------------------------------------------------------------
@app.get("/api/methodology")
async def api_methodology():
    """Retrieve transparent documentation of all official data sources, APIs, mathematical formulas, and bias mitigation policies."""
    sources = [
        MethodologyDataSource(
            name="Congress.gov Official Legislative API & House/Senate Clerk Roll Calls",
            provider="Library of Congress & Office of the Clerk of the U.S. House / Secretary of the Senate",
            endpoint_or_source="api.congress.gov / clerk.house.gov / senate.gov",
            update_frequency="Automated Weekly Every Saturday at 02:00 AM UTC (and on-demand)",
            description="Official record of all roll call votes, statutory bill text, amendments, bill co-sponsorships, and committee referrals.",
            verification_url="https://api.congress.gov"
        ),
        MethodologyDataSource(
            name="U.S. Census Bureau American Community Survey (ACS 5-Year Estimates)",
            provider="U.S. Department of Commerce & U.S. Census Bureau",
            endpoint_or_source="api.census.gov/data/2022/acs/acs5",
            update_frequency="Annual Census Bureau Release Cycles",
            description="Socioeconomic baseline data per congressional district including median household income, poverty rate, SNAP assistance %, foreign-born %, Medicaid enrollment %, and employment sector concentrations.",
            verification_url="https://www.census.gov/programs-surveys/acs"
        ),
        MethodologyDataSource(
            name="Federal Election Commission (FEC) Electronic Campaign Filings",
            provider="Federal Election Commission (FEC)",
            endpoint_or_source="api.open.fec.gov/v1/candidate",
            update_frequency="Quarterly & Post-General FEC Reporting Windows",
            description="Itemized campaign receipts, small-dollar grassroots contributions (<$200), large individual donations, and corporate/union PAC contributions.",
            verification_url="https://www.fec.gov/data"
        ),
        MethodologyDataSource(
            name="Congressional STOCK Act Financial Disclosures",
            provider="House Committee on Ethics & Senate Select Committee on Ethics",
            endpoint_or_source="disclosures-clerk.house.gov / efdsearch.senate.gov",
            update_frequency="Monthly Periodic Transaction Reports (PTRs)",
            description="Stock, bond, and options transactions disclosed by members of Congress and spouses, cross-referenced against assigned committee NAICS codes.",
            verification_url="https://disclosures-clerk.house.gov"
        ),
        MethodologyDataSource(
            name="Voteview DW-NOMINATE Ideological Spatial Scaling",
            provider="UCLA Department of Political Science / Poole & Rosenthal",
            endpoint_or_source="voteview.com/data",
            update_frequency="Per-Congress Session Update",
            description="Dynamic Weighted NOMINATE spatial scaling measuring liberal-to-conservative voting distance (-1.0 to +1.0) along Dimension 1 (economic/redistributive) and Dimension 2 (social/regional).",
            verification_url="https://voteview.com"
        )
    ]

    formulas = [
        MethodologyFormulaDoc(
            metric_name="5-Pillar Legislative Effectiveness Rating (0 to 100)",
            scale="100-Point Scale (A+ through F)",
            inputs=["Bills Sponsored / Passed Committee / Enacted", "Community Earmarks ($M)", "Constituent Sync %", "Floor Attendance %", "Abstain Penalty", "Grassroots Donor %", "PAC Dependency %", "Bipartisanship %"],
            formula_text="Score = Output(25 max) + DistrictSync(25 max) + Floor(20 max) + PAC_Indep(15 max) + Bipartisanship(15 max)",
            rationale="Eliminates grade inflation by balancing legislative productivity, local constituent representation, floor reliability, clean fundraising, and cross-aisle dealmaking."
        ),
        MethodologyFormulaDoc(
            metric_name="Constituent Fidelity Index vs PAC Sway Index",
            scale="0.0% to 100.0%",
            inputs=["District Demographic Deciles", "Roll Call Voting Alignments", "Top PAC Donor Contributions"],
            formula_text="Fidelity = (Roll Calls Aligning with District Needs / Total Evaluated Policy Divergences) * 100",
            rationale="Quantifies whether a lawmaker represents home district economic realities or prioritizes major campaign donors when their interests conflict."
        ),
        MethodologyFormulaDoc(
            metric_name="High-Pressure Floor Resilience Index (Clutch Rating)",
            scale="0 to 100",
            inputs=["Roll Calls with <15 Vote Margin in House (<3 in Senate)", "Party Line Cohesion on Tight Votes", "Independent Defections"],
            formula_text="Clutch = (Narrow Margin Attendance * 0.40) + (Clutch Party Unity * 0.60) adjusted for tactical leverage",
            rationale="Measures legislative reliability during high-stakes floor showdowns, debt ceiling votes, and emergency appropriations."
        ),
        MethodologyFormulaDoc(
            metric_name="STOCK Act Committee Conflict Index",
            scale="0 to 100",
            inputs=["Periodic Transaction Reports (PTRs)", "Assigned Committee Jurisdictions", "Company NAICS Industry Codes"],
            formula_text="Conflict Index = Sum(Trade Volume * Committee Jurisdiction Weight) / Total Asset Holdings",
            rationale="Flags potential conflicts of interest where lawmakers trade equities in companies directly under their active committee regulatory supervision."
        ),
        MethodologyFormulaDoc(
            metric_name="Bipartisanship Velocity Index",
            scale="0.0% to 100.0%",
            inputs=["Cross-Party Co-sponsorships", "Bipartisan Compromise Roll Calls", "Solo Maverick Protests"],
            formula_text="Velocity = min(100.0, (Cross-Party Bill Cosponsorships / Total Cosponsorships) * 250.0)",
            rationale="Measures willingness to work across the aisle, co-author bipartisan legislation, and break gridlock."
        )
    ]

    mission = (
        "Congress Civic Analytics is dedicated to delivering open, nonpartisan, and mathematically rigorous civic intelligence. "
        "We empower citizens, journalists, and researchers with transparent legislative performance indicators grounded exclusively in official "
        "government public records—with zero paywalls and full algorithmic transparency."
    )

    bias_policy = (
        "All analytical models apply identical mathematical formulas and thresholds equally across Democrats, Republicans, and Independents. "
        "District demographics are sourced directly from the U.S. Census Bureau ACS, and voting data is verified against official House and Senate Clerk rolls. "
        "We welcome public scrutiny, academic audits, and open-source contributions to continuously refine our scoring models."
    )

    return MethodologyDocumentationResponse(
        mission_statement=mission,
        data_sources=sources,
        scoring_formulas=formulas,
        bias_mitigation_policy=bias_policy,
        open_source_audit_link="https://github.com/SaviorOfSanity/congress-nextgen-stats"
    ).model_dump()

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
