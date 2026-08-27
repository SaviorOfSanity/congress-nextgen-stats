"""
Command Line Interface (CLI) for Congressional NextGenStats Engine
"""
import sys
import argparse
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.ingestion.congress_api import search_members
from backend.analytics.scouting_model import build_full_profile
from backend.video_engine.video_assembler import render_scouting_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def cmd_search(args):
    """Search for Congress members."""
    results = search_members(args.query)
    print(f"\nFound {len(results)} members matching '{args.query}':\n" + "=" * 60)
    for r in results:
        dist_str = f"-{r['district']:02d}" if r.get('district') is not None else ""
        print(f"[{r['bioguide_id']}] {r['full_name']:<28} {r['party'][0]}-{r['state']}{dist_str:<4} ({r['chamber']})")
    print("=" * 60)

def cmd_scout(args):
    """Display complete NFL Draft style scouting report in terminal."""
    profile = build_full_profile(args.bioguide)
    bio = profile.bio
    sc = profile.scouting
    m = sc.combine_measurables
    c = profile.constituents
    al = profile.alignment
    fn = profile.finance

    print("\n" + "═" * 70)
    print(f" ★ CONGRESSIONAL NEXTGENSTATS DRAFT SCOUTING REPORT ★")
    print("═" * 70)
    print(f" PROSPECT: {bio.full_name.upper()} ({bio.party[0]}-{c.district_code})")
    print(f" CHAMBER:  {bio.chamber.upper()} OF REPRESENTATIVES | TERMS SERVED: {bio.terms_served}")
    if bio.leadership_role:
        print(f" ROLE:     {bio.leadership_role}")
    print("─" * 70)
    print(f" DRAFT GRADE:     {sc.draft_grade:<6} | DRAFT ARCHETYPE: {sc.draft_archetype}")
    print(f" PRO COMPARISON:  {sc.pro_comparison_name}")
    print(f" COMPARISON TAPE: {sc.pro_comparison_desc}")
    print("─" * 70)
    print(f" COMBINE MEASURABLES:")
    print(f"   • Party Line Loyalty:       {m.party_loyalty:.1f}%")
    print(f"   • Constituent Sync Score:   {m.constituent_sync:.1f}%")
    print(f"   • Floor Attendance Rate:    {m.floor_attendance:.1f}%")
    print(f"   • Legislative Motor Rating: {m.legislative_motor:.0f}/100")
    print(f"   • Bipartisanship Velocity:  {m.bipartisanship_velocity:.1f}%")
    print(f"   • PAC Dependency:           {m.pac_dependency:.1f}% ({'Grassroots' if m.pac_dependency < 10 else 'Corporate/PAC'})")
    print("─" * 70)
    print(f" DISTRICT IMPACT & CONSTITUENT SYNC ({c.district_code}):")
    print(f"   • Median Income: ${c.median_household_income:,} | Poverty: {c.poverty_rate_pct:.1f}% | Lean: {c.partisan_lean_pvi}")
    print(f"   • Top Alignment:  {', '.join(al.top_alignment_areas)}")
    print(f"   • Primary Dissonance: {', '.join(al.top_divergence_areas)}")
    print("─" * 70)
    print(f" FILM ROOM VERDICT:")
    print(f"   {sc.film_room_verdict}")
    print("═" * 70 + "\n")

def cmd_generate_video(args):
    """Generate high-definition MP4 scouting video."""
    profile = build_full_profile(args.bioguide)
    is_vertical = args.format.lower() == "shorts"
    print(f"\nRendering {args.format.upper()} video for {profile.bio.full_name}...")
    vpath = render_scouting_video(profile, is_vertical=is_vertical, fps=args.fps)
    print(f"\n✔ Video successfully generated at:\n  {vpath.resolve()}\n")

def cmd_serve(args):
    """Start local web dashboard server."""
    import uvicorn
    print(f"\nStarting Congressional NextGenStats Web Dashboard on http://{args.host}:{args.port}")
    uvicorn.run("backend.server:app", host=args.host, port=args.port, reload=False)

def main():
    parser = argparse.ArgumentParser(description="Congressional NextGenStats & Scouting Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search
    p_search = subparsers.add_parser("search", help="Search members of Congress")
    p_search.add_argument("query", type=str, help="Name, state, or chamber")
    p_search.set_defaults(func=cmd_search)

    # Scout
    p_scout = subparsers.add_parser("scout", help="Display full scouting report")
    p_scout.add_argument("--bioguide", "-b", required=True, help="Bioguide ID (e.g. O000172)")
    p_scout.set_defaults(func=cmd_scout)

    # Video
    p_video = subparsers.add_parser("generate-video", help="Render scouting video (.mp4)")
    p_video.add_argument("--bioguide", "-b", required=True, help="Bioguide ID (e.g. O000172)")
    p_video.add_argument("--format", "-f", choices=["shorts", "broadcast"], default="shorts", help="Video format (shorts: 9:16, broadcast: 16:9)")
    p_video.add_argument("--fps", type=int, default=24, help="Video frame rate")
    p_video.set_defaults(func=cmd_generate_video)

    # Serve
    p_serve = subparsers.add_parser("serve", help="Run web dashboard")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host address")
    p_serve.add_argument("--port", type=int, default=8000, help="Port number")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)

if __name__ == "__main__":
    main()
