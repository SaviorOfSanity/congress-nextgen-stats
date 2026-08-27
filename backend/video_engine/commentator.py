"""
Commentator Script Generator for NextGenStats Congressional Scouting Reports
Generates fast-paced, high-impact sports broadcast voiceover scripts.
"""
from typing import Dict, List
from backend.models import CongressionalProfile

def generate_commentator_script(profile: CongressionalProfile) -> Dict[str, str]:
    """
    Generate structured, high-energy commentary segments for the video generator.
    """
    bio = profile.bio
    scouting = profile.scouting
    m = scouting.combine_measurables
    align = profile.alignment
    demo = profile.constituents
    
    # Chamber and district wording
    dist_str = f"representing {demo.district_code}" if bio.district is not None else f"representing the state of {bio.state}"
    leadership_str = f", serving as {bio.leadership_role}," if bio.leadership_role else ""

    # Segment 1: Intro Hook & Prospect Reveal
    intro = (
        f"Welcome to the Congressional Film Room. On the draft board today: {bio.full_name}{leadership_str} {dist_str}. "
        f"Coming in as a {scouting.draft_grade} prospect, our analytics model classifies {bio.last_name} as a {scouting.draft_archetype}."
    )

    # Segment 2: Combine Measurables & Radar HUD
    measurables = (
        f"Breaking down the combine tape, {bio.last_name} posts a {m.floor_attendance:.1f} percent floor attendance rate, "
        f"backed by a {m.party_loyalty:.1f} percent party loyalty index and a {m.legislative_motor:.0f} rating on legislative motor. "
        f"{'With near-zero PAC dependency, this is a pure grassroots operation.' if m.pac_dependency < 10 else f'PAC contributions account for {m.pac_dependency:.1f} percent of funding.'}"
    )

    # Segment 3: Voting Policy Breakdown
    top_cat = list(profile.voting.category_breakdown.items())[0]
    second_cat = list(profile.voting.category_breakdown.items())[1]
    voting = (
        f"On the legislative voting tape, {bio.last_name} brings a {top_cat[1].support_pct:.0f} percent support rate on {top_cat[0]}, "
        f"and {second_cat[1].support_pct:.0f} percent on {second_cat[0]}. "
        f"{'Consistently anchors party-line packages while challenging cross-aisle alternatives.' if m.bipartisanship_velocity < 25 else 'Shows strong cross-aisle velocity with key bipartisan cosponsorships.'}"
    )

    # Segment 4: Constituent Sync & District Impact
    constituents = (
        f"Now to the home district match-up. {bio.last_name} clocks a {align.overall_sync_score:.1f} percent overall constituent sync score. "
        f"Top alignment shines in {align.top_alignment_areas[0] if align.top_alignment_areas else 'core appropriations'}. "
        f"{'Primary divergence emerges on ' + align.top_divergence_areas[0] + '.' if align.top_divergence_areas else ''}"
    )

    # Segment 5: Pro Comparison & Final Draft Grade
    verdict = (
        f"In the film room, the pro comparison matches {scouting.pro_comparison_name}. "
        f"Key strength: {scouting.strengths[0] if scouting.strengths else 'Caucus reliability'}. "
        f"Final draft grade: {scouting.draft_grade}. That's your NextGen Stats scouting breakdown."
    )

    return {
        "01_intro": intro,
        "02_measurables": measurables,
        "03_voting": voting,
        "04_constituents": constituents,
        "05_film_room": verdict
    }
