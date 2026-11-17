"""
FastAPI Server and Web Dashboard for Congressional Civic Analytics & Dossiers
"""
import os
import hmac
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, VIDEOS_DIR, CARDS_DIR, ADMIN_API_KEY, ALLOWED_ORIGINS
from backend.models import (
    CongressionalProfile, 
    FullLeaderboardResponse,
    MethodologyDocumentationResponse,
    MethodologyDataSource,
    MethodologyFormulaDoc,
    VoterMatchmakerRequest,
    VoterMatchmakerResponse
)
from backend.ingestion.congress_api import search_members, get_category_deep_dive_bills
from backend.ingestion.committees_data import get_committee_dossier
from backend.analytics.constituent_sync import build_district_deep_dive_dossier
from backend.analytics.scouting_model import (
    build_full_profile,
    get_full_leaderboard,
    generate_head_to_head_comparison,
    generate_rating_breakdown,
    get_all_party_rankings,
    calculate_voter_match
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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key", "Authorization"],
)

_SYNC_LOCK = asyncio.Lock()
_LAST_SYNC_TRIGGER_TS: float = 0.0
_VIDEO_SEM = asyncio.Semaphore(1)


def require_admin_access(request: Request) -> None:
    """
    Protect resource-intensive or mutating routes when exposed via Cloudflare Tunnel.
    - If ADMIN_API_KEY is configured: requires matching X-Admin-Key or Bearer token.
    - If ADMIN_API_KEY is unset: permits only direct loopback requests (no tunnel/proxy headers).
    """
    provided = (request.headers.get("x-admin-key") or "").strip()
    if not provided:
        auth_hdr = (request.headers.get("authorization") or "").strip()
        if auth_hdr.lower().startswith("bearer "):
            provided = auth_hdr[7:].strip()

    if ADMIN_API_KEY:
        if not provided or not hmac.compare_digest(provided, ADMIN_API_KEY):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: valid X-Admin-Key header required.",
            )
        return

    client_host = request.client.host if request.client else ""
    is_proxied = bool(
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or request.headers.get("x-forwarded-host")
        or request.headers.get("forwarded")
    )
    if is_proxied or client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(
            status_code=403,
            detail="Forbidden from external network: set ADMIN_API_KEY env var or protect route with Cloudflare Access.",
        )


# -------------------------------------------------------------
# HEALTH & SYSTEM STATUS ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "congress-civic-analytics", "version": "2.5.0"}

@app.get("/api/system/status")
async def system_status():
    """Return database ingestion status, last sync timestamp, and next scheduled update."""
    return get_sync_status()

@app.post("/api/admin/sync")
async def trigger_manual_sync(request: Request, background_tasks: BackgroundTasks, _auth: None = Depends(require_admin_access)):
    """Trigger on-demand data refresh across all roll calls, committees, and disclosures."""
    global _LAST_SYNC_TRIGGER_TS
    now = time.monotonic()
    if now - _LAST_SYNC_TRIGGER_TS < 30.0:
        raise HTTPException(status_code=429, detail="Sync cooldown active; please wait 30 seconds between syncs.")
    if _SYNC_LOCK.locked():
        raise HTTPException(status_code=409, detail="A data synchronization job is already running.")

    async with _SYNC_LOCK:
        _LAST_SYNC_TRIGGER_TS = time.monotonic()
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
        profile = build_full_profile(bioguide_id, timeframe=timeframe, fetch_live=True)
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

@app.get("/api/category/{bioguide_id}/{category_name:path}")
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

@app.post("/api/voter-matchmaker")
async def api_voter_matchmaker(request: VoterMatchmakerRequest):
    """Match a voter's key issue choices against every candidate's actual roll call voting record."""
    try:
        match_response = calculate_voter_match(request)
        return match_response.model_dump()
    except Exception as e:
        logger.exception("Failed to compute voter matches")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/district-lookup/{query}")
async def api_district_lookup(query: str):
    """Resolve a U.S. street address (via Census Geocoder), 5-digit ZIP code, or 2-letter state abbreviation."""
    try:
        from backend.ingestion.census_api import (
            resolve_zip_to_state_district,
            geocode_address_to_district,
            STATE_BASELINES,
        )
        from backend.ingestion.congress_api import load_all_congress_members

        raw_q = query.strip()
        q = raw_q.upper()
        all_m = load_all_congress_members()

        matched_state = None
        matched_district = None
        exact_district = False
        matched_address = None
        resolution_method = "Statewide Match"

        if q.isdigit() and len(q) == 5:
            resolved = resolve_zip_to_state_district(q)
            matched_state = resolved["state"]
            matched_district = resolved.get("district")
            exact_district = bool(resolved.get("exact_district_match"))
            resolution_method = "Exact ZIP Table" if exact_district else "ZIP Prefix State Boundary (Multi-District)"
        elif len(q) == 2 and (q in STATE_BASELINES or any(m.get("bio", {}).get("state", "").upper() == q for m in all_m)):
            matched_state = q
            matched_district = None
            resolution_method = "State Delegation Lookup"
        elif len(raw_q) >= 8 and (" " in raw_q or "," in raw_q):
            geo = await asyncio.to_thread(geocode_address_to_district, raw_q)
            if not geo:
                raise HTTPException(
                    status_code=404,
                    detail="Street address could not be matched to a 119th Congressional District. Include street, city, and state (e.g. '350 5th Ave, New York, NY').",
                )
            matched_state = geo["state"]
            matched_district = geo["district"]
            exact_district = True
            matched_address = geo.get("matched_address")
            resolution_method = geo.get("resolution_method", "US Census Bureau Geocoder")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Enter a 5-digit ZIP code, full street address, or 2-letter state code (got '{query}').",
            )

        house_members = []
        senators = []

        for m in all_m:
            bio = m.get("bio", {})
            st = bio.get("state", "").upper()
            ch = bio.get("chamber", "")
            dist = bio.get("district")

            if st == matched_state:
                if ch == "Senate":
                    senators.append(bio)
                elif ch == "House":
                    if matched_district is not None and dist == matched_district:
                        house_members.insert(0, bio)
                    elif matched_district is None or exact_district is False:
                        house_members.append(bio)

        # Sort House members by district number when showing multiple
        if len(house_members) > 1 and not exact_district:
            house_members.sort(key=lambda b: (b.get("district") if b.get("district") is not None else 999))

        return {
            "query": query,
            "resolved_state": matched_state,
            "resolved_district": matched_district,
            "exact_district_match": exact_district,
            "matched_address": matched_address,
            "resolution_method": resolution_method,
            "needs_street_address_hint": (not exact_district and len(house_members) > 1),
            "house_representative": house_members[0] if house_members else None,
            "house_representatives": house_members[:20],
            "senators": senators[:2]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed district lookup")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ethics-dossier/{bioguide_id}")
async def api_ethics_dossier(bioguide_id: str):
    """Retrieve detailed Congressional Corruption & Scandal breakdown for a lawmaker."""
    try:
        profile = build_full_profile(bioguide_id)
        return {
            "bioguide_id": profile.bio.bioguide_id,
            "full_name": profile.bio.full_name,
            "party": profile.bio.party,
            "chamber": profile.bio.chamber,
            "state": profile.bio.state,
            "ethics_risk_score": profile.ethics_risk.ethics_risk_score,
            "risk_level_label": profile.ethics_risk.risk_level_label,
            "stock_trading_conflict_pts": profile.ethics_risk.stock_trading_conflict_pts,
            "pac_capture_pts": profile.ethics_risk.pac_capture_pts,
            "abnormal_wealth_pts": profile.ethics_risk.abnormal_wealth_pts,
            "ethics_oversight_pts": profile.ethics_risk.ethics_oversight_pts,
            "clean_indicators": profile.ethics_risk.clean_indicators,
            "conflict_drivers": profile.ethics_risk.conflict_drivers,
            "flagged_transactions_details": profile.ethics_risk.flagged_transactions_details,
            "oversight_inquiries": profile.ethics_risk.oversight_inquiries,
            "ethics_narrative": profile.ethics_risk.ethics_narrative,
            "stock_trading_profile": profile.stock_trading.model_dump(),
            "wealth_pl": profile.wealth_pl.model_dump()
        }
    except Exception as e:
        logger.exception("Failed to retrieve ethics dossier")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/family-conflicts/{bioguide_id}")
async def api_family_conflicts(bioguide_id: str):
    """Retrieve detailed Spousal Corporate Leadership, Dynastic Family Trusts, and Business Conflicts."""
    try:
        profile = build_full_profile(bioguide_id)
        return {
            "bioguide_id": profile.bio.bioguide_id,
            "full_name": profile.bio.full_name,
            "party": profile.bio.party,
            "family_conflicts": profile.family_conflicts.model_dump()
        }
    except Exception as e:
        logger.exception("Failed to retrieve family conflicts")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/super-pacs/{bioguide_id}")
async def api_super_pacs(bioguide_id: str):
    """Retrieve Super PAC Independent Expenditures, Dark Money ratios, and top outside groups."""
    try:
        profile = build_full_profile(bioguide_id)
        return {
            "bioguide_id": profile.bio.bioguide_id,
            "full_name": profile.bio.full_name,
            "party": profile.bio.party,
            "super_pac_spending": profile.super_pac_spending.model_dump()
        }
    except Exception as e:
        logger.exception("Failed to retrieve super pac spending")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# OPEN METHODOLOGY & DATA SOURCES CITATION ENDPOINT
# -------------------------------------------------------------
@app.get("/api/methodology")
async def api_methodology():
    """Retrieve transparent documentation of all official data sources, APIs, mathematical formulas, and bias mitigation policies."""
    sources = [
        MethodologyDataSource(
            name="Voteview Roll Call Archive & Official Congress-Legislators Registry",
            provider="UCLA Political Science (Poole & Rosenthal) & unitedstates/congress-legislators",
            endpoint_or_source="voteview.com / unitedstates.github.io / api.congress.gov",
            update_frequency="Automated Weekly Every Saturday at 02:00 AM UTC (and on-demand)",
            description="Complete 117th-119th Congress House and Senate recorded roll calls (including amendment votes and party-divided vs. routine absence splits), official 119th committee rosters, and DW-NOMINATE spatial ideology scores.",
            verification_url="https://voteview.com/data"
        ),
        MethodologyDataSource(
            name="U.S. Census Bureau Geocoder & American Community Survey (ACS 5-Year)",
            provider="U.S. Department of Commerce & U.S. Census Bureau",
            endpoint_or_source="geocoding.geo.census.gov / api.census.gov/data/2023/acs/acs5",
            update_frequency="Real-Time Street Address Geocoding + Annual ACS Release Cycles",
            description="Keyless 119th Congressional District street geocoding paired with Census socioeconomic baselines (income, poverty, SNAP, Medicaid, foreign-born share, and sectors).",
            verification_url="https://geocoding.geo.census.gov/geocoder/"
        ),
        MethodologyDataSource(
            name="Federal Election Commission (OpenFEC) Campaign, Schedule A Geography & Super PAC Filings",
            provider="Federal Election Commission (FEC)",
            endpoint_or_source="api.open.fec.gov/v1/candidate, /schedules/schedule_a/by_state/by_candidate & /schedule_e",
            update_frequency="Live On-Demand Cache + Quarterly FEC Reporting Windows",
            description="Itemized and unitemized (<$200 grassroots) receipts, PAC contributions, campaign cash-on-hand/debt, In-State vs. Out-of-State Schedule A geographic splits, and Schedule E Super PAC independent expenditures.",
            verification_url="https://www.fec.gov/data"
        ),
        MethodologyDataSource(
            name="House Clerk STOCK Act PTR PDF Parser & Financial Disclosure Index",
            provider="Office of the Clerk of the U.S. House of Representatives & Ethics Committees",
            endpoint_or_source="disclosures-clerk.house.gov/public_disc/ptr-pdfs/ & financial-pdfs/",
            update_frequency="Weekly Index Sync + On-Demand Line-Item PTR PDF Parsing",
            description="Line-item equity purchase/sale extraction from public House Clerk PTR PDFs via pypdf, 45-day STOCK Act late-filing detection, and committee overlap scoring (Senate eFD remains linked via its interactive portal).",
            verification_url="https://disclosures-clerk.house.gov"
        )
    ]

    formulas = [
        MethodologyFormulaDoc(
            metric_name="5-Pillar Legislative Effectiveness Rating (0 to 100)",
            scale="100-Point 10-Point-Bracket Scale (A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: <60)",
            inputs=["Bills Sponsored / Passed Committee / Enacted", "Community Earmarks ($M)", "Constituent Sync %", "Floor Attendance %", "Abstain Penalty", "Grassroots Donor %", "PAC Dependency %", "Bipartisanship %"],
            formula_text="Score = Output(25) + DistrictSync(25) + Floor(20; Delegate rule-adjusted) + Grassroots/PAC(15: 9.5*(Small/75)+5.5*((65-PAC)/65)) + Bipartisanship(15: 15*(Bipart/38))",
            rationale="Evaluates job performance across legislative throughput, district alignment, attendance, clean fundraising, and cross-aisle coalition building—completely separate from ideology."
        ),
        MethodologyFormulaDoc(
            metric_name="Contested vs. Routine Vote Absence Split",
            scale="0% to 100% Missed (Classified by Party-Majority Split >15% vs. Routine Bipartisan Motions)",
            inputs=["Voteview Roll Call Party Splits", "Member Cast vs. Missed Votes"],
            formula_text="Divided_Absence% = Divided_Missed / Divided_Total; Routine_Absence% = Routine_Missed / Routine_Total",
            rationale="Distinguishes strategic or impactful absences on contested floor fights from routine suspension/procedural absences."
        ),
        MethodologyFormulaDoc(
            metric_name="In-State vs. Out-of-State Fundraising & Earmark-Donor Crosswalk",
            scale="0% to 100% Geographic Split + Crosswalk Overlap Flags",
            inputs=["OpenFEC Schedule A By-State Contributor Receipts", "Top Donor Industry Sectors", "Committee Jurisdiction & Earmark Categories"],
            formula_text="OutOfState% = Sum(NonHomeState_Itemized) / Total_State_Itemized; Flags Donor Sectors >=18% With Direct Committee Jurisdiction Overlap",
            rationale="Highlights nationalized outside donor funding vs. local district fundraising and checks whether appropriations earmark categories intersect major donor industries."
        ),
        MethodologyFormulaDoc(
            metric_name="Party Lean Spectrum & District Ideology Gap",
            scale="-1.00 (Far Left Blue) to +1.00 (Far Right Red)",
            inputs=["Voteview DW-NOMINATE Dimension 1", "District Partisan Lean PVI"],
            formula_text="Bar Position % = ((clamp(DW_NOMINATE, -1, +1) + 1) / 2) * 100",
            rationale="Places every lawmaker on a Blue-White-Red ideological continuum using actual roll-call voting distances and compares it to home district baseline lean."
        ),
        MethodologyFormulaDoc(
            metric_name="High-Pressure Floor Resilience Index (Clutch Rating)",
            scale="0 to 100",
            inputs=["Empirical Narrow-Margin Roll Calls (<=15 House / <=5 Senate)", "Narrow-Vote Attendance", "Close-Vote Party Cohesion"],
            formula_text="Clutch = clamp(45..99, (Narrow_Attendance_Ratio * 42) + (Narrow_Party_Unity * 0.54))",
            rationale="Measures reliability and caucus vs. maverick behavior on razor-thin floor roll calls extracted directly from Voteview."
        ),
        MethodologyFormulaDoc(
            metric_name="STOCK Act Conflict, 45-Day Late PTR & Scandal Risk Index",
            scale="0 to 100",
            inputs=["Parsed Clerk PTR Transactions", ">45-Day Late Filing Count", "PAC Capture", "Wealth Acceleration", "Committee Jurisdiction Overlap"],
            formula_text="Ethics Risk = StockTradingConflict(0-35) + PAC_Capture(0-30) + WealthMultiple(0-20) + Oversight(0-15)",
            rationale="Parses public House Clerk PTR PDFs line by line to flag committee-regulated sector trades and >45-day STOCK Act reporting delays."
        )
    ]

    mission = (
        "Congress Civic Analytics is dedicated to delivering open, nonpartisan, and transparent civic intelligence. "
        "Every Dossier surfaces a Data Provenance bar distinguishing live/verified government & academic datasets "
        "(Voteview roll calls, 119th official committee rosters, House Clerk PTR indexes, OpenFEC, Census Geocoder) "
        "from baseline heuristics where live PDFs or API keys are still optional."
    )

    bias_policy = (
        "All analytical models apply identical symmetric formulas across Democrats, Republicans, and Independents, "
        "including rule-fair adjustments for non-voting House Delegates (DC, PR, VI, GU, AS, MP) restricted by House Rule III."
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
async def api_generate_video(req: VideoGenerationRequest, request: Request, _auth: None = Depends(require_admin_access)):
    """Trigger automated video generation for a lawmaker (protected & concurrency-limited)."""
    if not (10 <= req.fps <= 60):
        raise HTTPException(status_code=400, detail="fps must be between 10 and 60")
    if req.format.lower() not in ("shorts", "broadcast"):
        raise HTTPException(status_code=400, detail="format must be 'shorts' or 'broadcast'")

    async with _VIDEO_SEM:
        try:
            profile = build_full_profile(req.bioguide_id)
            is_vertical = req.format.lower() == "shorts"

            video_path = await asyncio.to_thread(
                render_scouting_video,
                profile,
                is_vertical=is_vertical,
                fps=req.fps,
            )

            filename = video_path.name

            return {
                "status": "success",
                "member": profile.bio.full_name,
                "format": req.format,
                "filename": filename,
                "video_url": f"/api/video/{filename}",
                "file_size_bytes": video_path.stat().st_size
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Failed to generate video")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/video/{filename}")
async def api_stream_video(filename: str):
    """Stream or download a rendered MP4 video."""
    videos_root = VIDEOS_DIR.resolve()
    video_file = (videos_root / filename).resolve()
    if not video_file.is_relative_to(videos_root):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not video_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(path=video_file, media_type="video/mp4", filename=video_file.name)

@app.get("/api/card/{member_slug}/{orientation}/{slide_name}")
async def api_get_card(member_slug: str, orientation: str, slide_name: str):
    """Retrieve generated PNG slide graphic."""
    cards_root = CARDS_DIR.resolve()
    card_file = (cards_root / f"{member_slug}_{orientation}" / f"{slide_name}.png").resolve()
    if not card_file.is_relative_to(cards_root):
        raise HTTPException(status_code=400, detail="Invalid slide path")
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
