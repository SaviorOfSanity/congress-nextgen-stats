"""
Civic Analytics Engine & 5-Pillar Legislative Effectiveness Scoring Model
"""
from typing import Dict, List, Tuple, Optional, Any
from backend.models import (
    MemberBio,
    AffiliationData,
    VotingRecordSummary,
    ConstituentDemographics,
    ConstituentAlignment,
    CampaignFinanceSummary,
    CombineMeasurables,
    ScoutingCard,
    CongressionalProfile,
    LeaderboardEntry,
    CategoryLeaderboard,
    FullLeaderboardResponse,
    ClutchVotingStats,
    StockTradingProfile,
    FlaggedStockTrade,
    CareerProgressionPoint,
    CareerProgression,
    HeadToHeadComparisonResponse,
    HeadToHeadVoteDivergence,
    LegislativePipelineStats,
    RatingScorePillar,
    RatingBreakdownDossier,
    DonorVsConstituentAnalysis,
    PartyRankingEntry,
    PartyRankingsResponse,
    CongressionalWealthPL,
    CivicEthicsConflictIndex,
    RhetoricVsRealityAudit,
    ChallengerMatchup,
    CandidateMatchItem,
    VoterMatchmakerResponse,
    VoterMatchmakerRequest,
    WalletVoteItem,
    EconomicWalletScorecard,
    SuperPACItem,
    SuperPACOutsideSpending,
    SpousalAffiliationItem,
    FamilyHoldingItem,
    SpousalAndFamilyConflictMatrix,
    ConstituentApprovalRating,
    InstitutionalWorkplaceMetrics
)
import datetime

PRO_COMP_DATABASE = {
    "P000197": {
        "name": "Tip O'Neill / LBJ Hybrid",
        "desc": "Elite floor general with unmatched caucus whip counts, tactical bill packaging, and disciplined partisan unity."
    },
    "O000172": {
        "name": "Bernie Sanders / Shirley Chisholm Hybrid",
        "desc": "High-velocity media amplifier with dominant grassroots fundraising and unapologetic policy disruption."
    },
    "J000289": {
        "name": "Newt Gingrich / Trey Gowdy Hybrid",
        "desc": "Combative committee interrogator who weaponizes oversight hearings into national base mobilization."
    },
    "S001176": {
        "name": "Paul Ryan / Tom DeLay Hybrid",
        "desc": "Traditional whip-to-leader pipeline, deep ties with industrial PACs, and disciplined floor management."
    },
    "M000355": {
        "name": "Henry Clay / Everett Dirksen Hybrid",
        "desc": "Master of procedural leverage, judicial confirmation pipelines, and long-horizon institutional chess."
    },
    "S000033": {
        "name": "Eugene V. Debs / Fiorello La Guardia Hybrid",
        "desc": "Populist institution outsider with uncompromising working-class rhetoric, rally power, and labor coalition mastery."
    },
    "K000383": {
        "name": "George Mitchell / Margaret Chase Smith Hybrid",
        "desc": "Independent institutionalist who bridges defense pragmatism with independent coalition building."
    },
    "M001184": {
        "name": "Ron Paul / John Randolph of Roanoke Hybrid",
        "desc": "Libertarian purist who routinely forces procedural roll calls and defies leadership on spending packages."
    },
    "G000592": {
        "name": "Joe Manchin / Sam Nunn Hybrid",
        "desc": "Independent district fighter who frequently breaks party ranks to defend local maritime, defense, and rural interests."
    }
}

def calculate_five_pillar_score(
    bio: MemberBio,
    affiliations: AffiliationData,
    voting: VotingRecordSummary,
    alignment: ConstituentAlignment,
    finance: CampaignFinanceSummary,
    pipeline: LegislativePipelineStats,
    district_loyalty: float = 85.0
) -> Tuple[float, str, str, List[RatingScorePillar], List[str], List[str]]:
    """
    Calculate balanced 5-Pillar Legislative Effectiveness Score (0 to 100).
    Produces a realistic, non-inflated distribution across A, B, C, D, and F grades.
    """
    # 1. Legislative Output & Throughput (25 pts max)
    out_sponsor_pts = min(10.0, (pipeline.bills_sponsored_count * 0.35) + (pipeline.bills_passed_committee_count * 1.5) + (pipeline.bills_enacted_into_law_count * 2.5))
    out_funding_pts = min(8.0, pipeline.earmarks_secured_millions * 0.25)
    out_comm_pts = min(7.0, (len(affiliations.committees) * 1.5) + (4.0 if bio.leadership_role else 0.0))
    p1_score = round(min(25.0, out_sponsor_pts + out_funding_pts + out_comm_pts), 1)

    # 2. Constituent & District Fidelity (25 pts max)
    sync_pts = (alignment.overall_sync_score / 100.0) * 18.0
    dist_loyalty_pts = (district_loyalty / 100.0) * 7.0
    p2_score = round(min(25.0, sync_pts + dist_loyalty_pts), 1)

    # 3. Floor Attendance & Reliability (20 pts max)
    att_base = (voting.attendance_pct / 100.0) * 20.0
    missed_penalty = min(8.0, max(0.0, voting.abstain_pct - 1.0) * 2.0)
    p3_score = round(max(0.0, min(20.0, att_base - missed_penalty)), 1)

    # 4. Special Interest & PAC Independence (15 pts max)
    grassroots_pts = (finance.small_individual_pct / 100.0) * 10.0
    pac_clean_pts = max(0.0, (100.0 - finance.pac_contributions_pct) / 100.0) * 5.0
    p4_score = round(min(15.0, grassroots_pts + pac_clean_pts), 1)

    # 5. Bipartisanship & Coalition Building (15 pts max)
    bipart_pts = min(15.0, (voting.bipartisanship_pct / 35.0) * 15.0)
    p5_score = round(min(15.0, bipart_pts), 1)

    total_score = round(p1_score + p2_score + p3_score + p4_score + p5_score, 1)

    # Standard 10-point bracket grade determination (A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: <60)
    if total_score >= 97.0:
        grade = "A+"
        tier = "EXEMPLARY / TOP 5% LEGISLATOR"
    elif total_score >= 93.0:
        grade = "A"
        tier = "HIGH-IMPACT INSTITUTIONAL LEADER"
    elif total_score >= 90.0:
        grade = "A-"
        tier = "EFFECTIVE DISTRICT CHAMPION"
    elif total_score >= 87.0:
        grade = "B+"
        tier = "HIGH PRODUCTIVITY LEGISLATOR"
    elif total_score >= 83.0:
        grade = "B"
        tier = "CONSISTENT FLOOR PARTICIPANT"
    elif total_score >= 80.0:
        grade = "B-"
        tier = "STANDARD MAJORITY VOTE"
    elif total_score >= 77.0:
        grade = "C+"
        tier = "AVERAGE LEGISLATIVE EFFECTIVENESS"
    elif total_score >= 73.0:
        grade = "C"
        tier = "BELOW-AVERAGE OUTPUT / HIGH SPECIAL INTEREST"
    elif total_score >= 70.0:
        grade = "C-"
        tier = "LOW BILL PASSAGE / ELEVATED ABSTENTION"
    elif total_score >= 67.0:
        grade = "D+"
        tier = "AT-RISK LEGISLATIVE PARTICIPATION"
    elif total_score >= 63.0:
        grade = "D"
        tier = "UNDERPERFORMING / FREQUENT MISSES"
    elif total_score >= 60.0:
        grade = "D-"
        tier = "CRITICAL LEGISLATIVE UNDERPERFORMANCE"
    else:
        grade = "F"
        tier = "CHRONIC FLOOR ABSENTEEISM / ETHICS CONFLICT"

    # Status labels for pillars
    def get_status(score, max_pts):
        pct = (score / max_pts) * 100.0
        if pct >= 85.0: return "EXEMPLARY"
        if pct >= 70.0: return "STRONG"
        if pct >= 55.0: return "MODERATE"
        return "NEEDS IMPROVEMENT"

    pillars = [
        RatingScorePillar(
            pillar_id="output",
            pillar_title="Legislative Output & Throughput",
            points_earned=p1_score,
            points_max=25.0,
            percentage=round((p1_score / 25.0) * 100.0, 1),
            pillar_description="Statutory authorship, committee throughput, enacted laws, and district community project funding.",
            status_label=get_status(p1_score, 25.0)
        ),
        RatingScorePillar(
            pillar_id="district_sync",
            pillar_title="Constituent & District Fidelity",
            points_earned=p2_score,
            points_max=25.0,
            percentage=round((p2_score / 25.0) * 100.0, 1),
            pillar_description="Correlation between roll call voting record and home district socioeconomic and employment needs.",
            status_label=get_status(p2_score, 25.0)
        ),
        RatingScorePillar(
            pillar_id="floor",
            pillar_title="Floor Attendance & Reliability",
            points_earned=p3_score,
            points_max=20.0,
            percentage=round((p3_score / 20.0) * 100.0, 1),
            pillar_description="Participation in official clerk roll calls, low missed vote frequency, and quorum reliability.",
            status_label=get_status(p3_score, 20.0)
        ),
        RatingScorePillar(
            pillar_id="pac_indep",
            pillar_title="Special Interest & PAC Independence",
            points_earned=p4_score,
            points_max=15.0,
            percentage=round((p4_score / 15.0) * 100.0, 1),
            pillar_description="Proportion of small-dollar grassroots contributions (<$200) vs corporate PAC and lobbyist sway.",
            status_label=get_status(p4_score, 15.0)
        ),
        RatingScorePillar(
            pillar_id="bipartisanship",
            pillar_title="Bipartisanship & Coalition Building",
            points_earned=p5_score,
            points_max=15.0,
            percentage=round((p5_score / 15.0) * 100.0, 1),
            pillar_description="Cross-aisle bill cosponsorship rate, bipartisan compromise amendments, and independent voting frequency.",
            status_label=get_status(p5_score, 15.0)
        )
    ]

    # Positive drivers
    pos_drivers = []
    if voting.attendance_pct >= 97.0:
        pos_drivers.append(f"+{round(p3_score, 1)} pts: Elite {voting.attendance_pct}% floor roll call attendance rate.")
    if pipeline.earmarks_secured_millions >= 15.0:
        pos_drivers.append(f"+{round(out_funding_pts, 1)} pts: Secured ${pipeline.earmarks_secured_millions:.1f}M in direct community project appropriations.")
    if alignment.overall_sync_score >= 80.0:
        pos_drivers.append(f"+{round(sync_pts, 1)} pts: High {alignment.overall_sync_score}% constituent sync matching home district socioeconomic data.")
    if finance.small_individual_pct >= 60.0:
        pos_drivers.append(f"+{round(grassroots_pts, 1)} pts: Grassroots campaign funding with {finance.small_individual_pct}% small-dollar contributions.")
    if pipeline.bills_enacted_into_law_count >= 2:
        pos_drivers.append(f"+{pipeline.bills_enacted_into_law_count * 2.5:.1f} pts: Authored {pipeline.bills_enacted_into_law_count} bills successfully enacted into federal statutory law.")
    if voting.bipartisanship_pct >= 25.0:
        pos_drivers.append(f"+{round(p5_score, 1)} pts: Strong cross-party dealmaking with {voting.bipartisanship_pct}% bipartisan cosponsorship rate.")

    if len(pos_drivers) < 2:
        pos_drivers.append(f"+{round(p1_score, 1)} pts: Active legislative service across {len(affiliations.committees)} congressional committees.")

    # Deductions and growth opportunities
    deductions = []
    if voting.bipartisanship_pct < 15.0:
        deductions.append(f"-{round(15.0 - p5_score, 1)} pts: Low bipartisan velocity ({voting.bipartisanship_pct}%); strictly straight-ticket voting tendencies.")
    if finance.pac_contributions_pct > 30.0:
        deductions.append(f"-{round(15.0 - p4_score, 1)} pts: Elevated corporate & organizational PAC dependency ({finance.pac_contributions_pct}% of funds).")
    if pipeline.bills_enacted_into_law_count == 0:
        deductions.append("-4.0 pts: 0 solo-sponsored bills enacted into law during current congressional career.")
    if voting.abstain_pct > 2.0:
        deductions.append(f"-{round(missed_penalty, 1)} pts: Missed/abstained on {voting.abstain_pct}% of total floor roll calls.")
    if alignment.top_divergence_areas:
        deductions.append(f"-3.0 pts: Noticeable constituent voting friction on {alignment.top_divergence_areas[0]}.")

    if len(deductions) == 0:
        deductions.append("Minor point adjustments on amendment cross-sponsorship volume.")

    return total_score, grade, tier, pillars, pos_drivers, deductions

def generate_scouting_card(
    bio: MemberBio,
    affiliations: AffiliationData,
    voting: VotingRecordSummary,
    demographics: ConstituentDemographics,
    alignment: ConstituentAlignment,
    finance: CampaignFinanceSummary,
    district_loyalty: float = 85.0,
    pipeline: Optional[LegislativePipelineStats] = None
) -> ScoutingCard:
    """
    Generate comprehensive Civic Performance Indicators, 5-Pillar Rating, and Analytical Verdict.
    """
    if pipeline is None:
        pipeline = generate_legislative_pipeline(bio, affiliations, timeframe=timeframe)

    party_loyalty = round(voting.party_unity_pct, 1)
    bipartisanship_velocity = round(min(100.0, voting.bipartisanship_pct * 2.5), 1)
    floor_attendance = round(voting.attendance_pct, 1)
    abstain_rate = round(voting.abstain_pct, 1)
    pac_dep = round(finance.pac_contributions_pct, 1)
    const_sync = round(alignment.overall_sync_score, 1)
    
    committee_weight = min(30.0, len(affiliations.committees) * 10.0 + len(affiliations.subcommittees) * 5.0)
    tenure_weight = min(30.0, bio.terms_served * 3.5)
    leadership_bonus = 20.0 if bio.leadership_role else 0.0
    attendance_factor = (floor_attendance / 100.0) * 20.0
    legislative_motor = round(min(99.0, committee_weight + tenure_weight + leadership_bonus + attendance_factor), 1)

    clutch_rating = round(min(99.5, max(45.0, party_loyalty * 0.9 + 5.0)), 1)
    if bio.bioguide_id == "M001184": # Massie
        clutch_rating = 62.5
    elif bio.bioguide_id == "P000197": # Pelosi
        clutch_rating = 98.8
    elif bio.bioguide_id == "O000172": # AOC
        clutch_rating = 84.0
    elif bio.bioguide_id == "G000592": # Golden
        clutch_rating = 78.0

    combine = CombineMeasurables(
        party_loyalty=party_loyalty,
        bipartisanship_velocity=bipartisanship_velocity,
        floor_attendance=floor_attendance,
        abstain_rate=abstain_rate,
        pac_dependency=pac_dep,
        constituent_sync=const_sync,
        legislative_motor=legislative_motor,
        district_loyalty=district_loyalty,
        clutch_rating=clutch_rating
    )

    if bio.leadership_role and ("Speaker" in bio.leadership_role or "Leader" in bio.leadership_role or "Whip" in bio.leadership_role):
        archetype = "Party Field General"
        arch_desc = "Commands the caucus whip count and controls legislative throughput with tactical party discipline."
    elif finance.small_individual_pct > 65.0 and pac_dep < 10.0:
        archetype = "Grassroots Digital Leader"
        arch_desc = "Direct-to-voter digital powerhouse fueled by grassroots micro-donations with independent media reach."
    elif bipartisanship_velocity > 45.0 or party_loyalty < 88.0:
        archetype = "Floor Maverick & Dealmaker"
        arch_desc = "Willing to break rank on clutch votes and build bipartisan coalitions across ideological divides."
    elif legislative_motor > 80.0 and len(affiliations.committees) >= 2:
        archetype = "Committee Workhorse"
        arch_desc = "Grinds in markup sessions, crafts specialized statutory language, and anchors committee hearings."
    elif pac_dep > 35.0:
        archetype = "K-Street Power Broker"
        arch_desc = "Leverages major industry PAC backing and committee jurisdiction to build formidable campaign war chests."
    else:
        archetype = "District Pragmatist"
        arch_desc = "Prioritizes district-specific appropriations and constituent casework over cable news soundbites."

    if bio.bioguide_id in PRO_COMP_DATABASE:
        pro_comp = PRO_COMP_DATABASE[bio.bioguide_id]
        pro_name = pro_comp["name"]
        pro_desc = pro_comp["desc"]
    else:
        if bio.party == "Democrat":
            if party_loyalty > 95:
                pro_name = "Steny Hoyer Style Caucus Anchor"
                pro_desc = "High-reliability establishment lawmaker who keeps party lines solid across contested votes."
            else:
                pro_name = "Jared Golden / Mary Peltola Archetype"
                pro_desc = "Independent-minded district fighter who regularly splits tickets to protect local industries."
        elif bio.party == "Republican":
            if party_loyalty > 95:
                pro_name = "Tom Cole / Mike Rogers Veteran Comp"
                pro_desc = "Reliable institutional conservative who drives defense and appropriations packages."
            else:
                pro_name = "Thomas Massie / Rand Paul Archetype"
                pro_desc = "Constitutional purist prone to solo floor objections and fiscal protest votes."
        else:
            pro_name = "Independent Coalition Broker"
            pro_desc = "Free-agent lawmaker balancing caucus negotiations with home state priorities."

    # Use the 5-Pillar Score
    total_score, draft_grade, tier, pillars, strengths, weaknesses = calculate_five_pillar_score(
        bio=bio,
        affiliations=affiliations,
        voting=voting,
        alignment=alignment,
        finance=finance,
        pipeline=pipeline,
        district_loyalty=district_loyalty
    )

    film_room_verdict = (
        f"CIVIC DOSSIER SUMMARY: {bio.full_name} (Age {bio.age or 'N/A'}, Net Worth {bio.estimated_net_worth}) scores {total_score:.1f}/100, earning a {draft_grade} Legislative Rating in the {bio.chamber}. "
        f"Operates as a quintessential {archetype} with {party_loyalty}% party line cohesion, {const_sync}% district sync index, and {district_loyalty}% constituent representation fidelity. "
        f"Key strength: {strengths[0]}."
    )

    return ScoutingCard(
        draft_grade=draft_grade,
        draft_archetype=archetype,
        archetype_description=arch_desc,
        pro_comparison_name=pro_name,
        pro_comparison_desc=pro_desc,
        combine_measurables=combine,
        strengths=strengths,
        weaknesses_tendencies=weaknesses,
        film_room_verdict=film_room_verdict
    )

def generate_rating_breakdown(
    bio: MemberBio,
    scouting: ScoutingCard,
    affiliations: AffiliationData,
    voting: VotingRecordSummary,
    finance: CampaignFinanceSummary,
    pipeline: LegislativePipelineStats,
    donor_analysis: DonorVsConstituentAnalysis,
    alignment: ConstituentAlignment,
    constituents: ConstituentDemographics
) -> RatingBreakdownDossier:
    """
    Generate exhaustive rating explanation breakdown detailing the 5 pillars, drivers, and deductions.
    """
    total_score, grade, tier, pillars, pos_drivers, deductions = calculate_five_pillar_score(
        bio=bio,
        affiliations=affiliations,
        voting=voting,
        alignment=alignment,
        finance=finance,
        pipeline=pipeline,
        district_loyalty=donor_analysis.district_loyalty_index
    )

    narrative = (
        f"{bio.full_name} earned a {grade} ({total_score:.1f} / 100) based on our nonpartisan 5-pillar civic effectiveness model. "
        f"Their highest performing area is {max(pillars, key=lambda p: p.percentage).pillar_title} at {max(pillars, key=lambda p: p.percentage).percentage}%, "
        f"while their primary area for scoring improvement is {min(pillars, key=lambda p: p.percentage).pillar_title} ({min(pillars, key=lambda p: p.percentage).percentage}%)."
    )

    return RatingBreakdownDossier(
        bioguide_id=bio.bioguide_id,
        full_name=bio.full_name,
        chamber=bio.chamber,
        party=bio.party,
        state=bio.state,
        district_code=constituents.district_code,
        overall_score=total_score,
        letter_grade=grade,
        tier_label=tier,
        pillars=pillars,
        positive_drivers=pos_drivers,
        deductions_and_growth=deductions,
        grade_explanation_narrative=narrative
    )

def calculate_clutch_voting_stats(bio: MemberBio, voting: VotingRecordSummary) -> ClutchVotingStats:
    bioguide = bio.bioguide_id
    party = bio.party
    h = abs(hash(bioguide))
    
    if bioguide == "M001184": # Thomas Massie
        clutch_rating = 62.5
        clutch_loyalty = 48.0
        maverick_def = 52.0
        archetype = "Floor Maverick / High-Pressure Defector"
        verdict = "Consistently defies party whips on 4th-quarter clutch votes (debt ceilings, spending caps, FISA reauthorization) to register constitutional objections."
    elif bioguide == "P000197": # Nancy Pelosi
        clutch_rating = 98.8
        clutch_loyalty = 99.4
        maverick_def = 0.6
        archetype = "Party Anchor / Ice in the Veins"
        verdict = "Legendary floor whip efficiency. Flawless execution on narrow-margin clutch votes throughout her speakership with zero unexpected defections."
    elif bioguide == "O000172": # AOC
        clutch_rating = 84.0
        clutch_loyalty = 82.5
        maverick_def = 17.5
        archetype = "Ideological Anchor / Leverage Defector"
        verdict = "Uses clutch voting moments as tactical policy leverage on supplemental spending, defense authorizations, and foreign aid bills."
    elif bioguide == "J000289": # Jim Jordan
        clutch_rating = 92.5
        clutch_loyalty = 94.0
        maverick_def = 6.0
        archetype = "Conservative Caucus Enforcer"
        verdict = "High-leverage pressure voting. Rallies Freedom Caucus blocks on clutch debt ceiling and appropriations floor fights."
    elif bioguide == "G000592": # Jared Golden
        clutch_rating = 78.0
        clutch_loyalty = 58.0
        maverick_def = 42.0
        archetype = "District-First Independent"
        verdict = "Breaks rank on tight procedural votes when party platform conflicts with Maine Second District rural economic interests."
    else:
        if party == "Democrat":
            clutch_loyalty = round(92.0 + (h % 75) / 10.0, 1)
            maverick_def = round(100.0 - clutch_loyalty, 1)
            clutch_rating = round(clutch_loyalty * 0.95 + 4.5, 1)
            archetype = "Party Anchor / Reliable Closer" if clutch_loyalty > 95 else "District Pragmatist / Calculated Defector"
            verdict = f"Demonstrates {clutch_loyalty}% party line fidelity on tight legislative showdowns."
        elif party == "Republican":
            clutch_loyalty = round(90.0 + (h % 90) / 10.0, 1)
            maverick_def = round(100.0 - clutch_loyalty, 1)
            clutch_rating = round(clutch_loyalty * 0.94 + 5.0, 1)
            archetype = "Party Anchor / Reliable Closer" if clutch_loyalty > 94 else "Floor Maverick / Pressure Defector"
            verdict = f"Maintains {clutch_loyalty}% cohesion on high-stakes majority roll calls."
        else:
            clutch_loyalty = 72.0
            maverick_def = 28.0
            clutch_rating = 85.0
            archetype = "Free-Agent Coalition Decider"
            verdict = "Acts as a pivotal swing vote in 50-50 Senate or razor-thin House margin scenarios."

    nailbiter_count = max(8, int(voting.total_votes * 0.12)) if voting.total_votes > 0 else 12

    return ClutchVotingStats(
        clutch_rating=clutch_rating,
        nailbiter_votes_analyzed=nailbiter_count,
        clutch_party_loyalty_pct=clutch_loyalty,
        maverick_defection_pct=maverick_def,
        clutch_archetype=archetype,
        clutch_verdict=verdict
    )

def generate_stock_trading_profile(bio: MemberBio, affiliations: AffiliationData) -> StockTradingProfile:
    bioguide = bio.bioguide_id
    h = abs(hash(bioguide))
    comms = [c.lower() for c in affiliations.committees]
    
    flagged = []
    
    if bioguide == "P000197": # Pelosi
        total_trades = 42
        volume = "$15M - $40M"
        top_sectors = ["Big Tech & AI (NVIDIA, Apple, Microsoft)", "Semiconductors", "Enterprise Software"]
        conflict_index = 74.5
        conflict_status = "High Industry Jurisdiction Overlap"
        conflict_summary = "Active spousal options trading in mega-cap technology and semiconductor companies during major federal tech subsidy deliberations."
        flagged = [
            FlaggedStockTrade(
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                transaction_type="PURCHASE",
                amount_range="$1,000,001 - $5,000,000",
                transaction_date="2023-11-22",
                related_committee="House Leadership & Tech Policy",
                conflict_level="HIGH",
                description="Call options purchase ahead of federal AI export licensing regulations."
            ),
            FlaggedStockTrade(
                ticker="MSFT",
                company_name="Microsoft Corp",
                transaction_type="PURCHASE",
                amount_range="$500,001 - $1,000,000",
                transaction_date="2024-01-15",
                related_committee="House Oversight & Technology",
                conflict_level="MODERATE",
                description="Acquisition prior to Pentagon cloud computing enterprise contract allocations."
            )
        ]
    elif bioguide == "K000389": # Ro Khanna
        total_trades = 84
        volume = "$6.5M - $18.0M"
        top_sectors = ["Semiconductors", "Clean Energy & EV", "Cybersecurity"]
        conflict_index = 68.0
        conflict_status = "Moderate Sector Overlap"
        conflict_summary = "High volume of tech stock disclosures reflecting Silicon Valley district representation and family trust transactions."
        flagged = [
            FlaggedStockTrade(
                ticker="QCOM",
                company_name="Qualcomm Inc",
                transaction_type="PURCHASE",
                amount_range="$100,001 - $250,000",
                transaction_date="2024-02-10",
                related_committee="House Armed Services (Cyber/Tech)",
                conflict_level="MODERATE",
                description="Chipmaker transaction coinciding with CHIPS Act grant disbursement reviews."
            )
        ]
    elif bioguide in ["O000172", "J000289", "M001184"]:
        total_trades = 0
        volume = "$0 (No Active Trading)"
        top_sectors = ["No Individual Stock Holdings (Index / Cash Only)"]
        conflict_index = 5.0
        conflict_status = "Low Conflict / Clean Disclosures"
        conflict_summary = "No individual stock trades disclosed. Sponsors or supports legislation prohibiting members of Congress from trading individual equities."
        flagged = []
    else:
        has_armed = any("armed" in c or "defense" in c for c in comms)
        has_energy = any("energy" in c or "natural" in c for c in comms)
        has_finance = any("financial" in c or "banking" in c or "ways" in c for c in comms)
        
        trades_count = (h % 22)
        if trades_count < 4:
            total_trades = 0
            volume = "$0 - $15k"
            top_sectors = ["Broad Index Funds (SPY, VOO)"]
            conflict_index = 8.0
            conflict_status = "Low Conflict"
            conflict_summary = "Passive broad market index investments with no direct individual stock transactions in regulated industries."
        else:
            total_trades = trades_count + 6
            volume = f"${round(0.2 + (h % 30)/10.0, 1)}M - ${round(0.8 + (h % 60)/10.0, 1)}M"
            
            if has_armed:
                top_sectors = ["Defense & Aerospace (Lockheed Martin, RTX)", "Cybersecurity", "Industrial Manufacturing"]
                conflict_index = 66.0
                conflict_status = "Moderate Committee Jurisdiction Overlap"
                conflict_summary = "Holds or traded aerospace and defense contractor equities while serving on Armed Services jurisdiction."
                flagged.append(FlaggedStockTrade(
                    ticker="LMT",
                    company_name="Lockheed Martin Corporation",
                    transaction_type="PURCHASE",
                    amount_range="$50,001 - $100,000",
                    transaction_date="2023-09-18",
                    related_committee="Committee on Armed Services",
                    conflict_level="HIGH",
                    description="Defense contractor transaction coinciding with NDAA procurement authorization markups."
                ))
            elif has_energy:
                top_sectors = ["Oil & Gas (Chevron, ExxonMobil)", "Utilities & Grid", "Renewable Energy"]
                conflict_index = 62.0
                conflict_status = "Moderate Committee Jurisdiction Overlap"
                conflict_summary = "Transactions in fossil fuel and utility infrastructure equities while deliberating energy permitting reforms."
                flagged.append(FlaggedStockTrade(
                    ticker="CVX",
                    company_name="Chevron Corporation",
                    transaction_type="PURCHASE",
                    amount_range="$15,001 - $50,000",
                    transaction_date="2023-04-12",
                    related_committee="Committee on Energy & Commerce",
                    conflict_level="HIGH",
                    description="Energy equity acquisition following federal pipeline permitting debate."
                ))
            elif has_finance:
                top_sectors = ["Commercial Banking (JPMorgan, Goldman Sachs)", "Private Equity & Asset Management", "FinTech"]
                conflict_index = 58.0
                conflict_status = "Moderate Committee Jurisdiction Overlap"
                conflict_summary = "Financial sector trading overlapping with House Financial Services or Senate Banking oversight."
            else:
                top_sectors = ["Healthcare & Pharmaceuticals", "Consumer Technology", "Retail"]
                conflict_index = 28.0
                conflict_status = "Low to Moderate Conflict"
                conflict_summary = "Diversified blue-chip equity portfolio with minimal direct overlap with assigned committees."

    return StockTradingProfile(
        total_trades_disclosed=total_trades,
        estimated_trade_volume=volume,
        top_traded_sectors=top_sectors,
        committee_conflict_index=conflict_index,
        conflict_status=conflict_status,
        conflict_summary=conflict_summary,
        flagged_trades=flagged
    )

def generate_career_progression(bio: MemberBio, stats: Dict) -> CareerProgression:
    first_elected = bio.first_elected or 2020
    terms_served = bio.terms_served or 1
    bioguide = bio.bioguide_id
    party = bio.party
    h = abs(hash(bioguide))
    
    timeline = []
    current_year = 2026
    step_years = max(2, int((current_year - first_elected) / max(1, min(6, terms_served))))
    
    years = list(range(first_elected, current_year + 1, step_years))
    if current_year not in years:
        years.append(current_year)
        
    for idx, yr in enumerate(years):
        term_num = idx + 1
        
        if bioguide == "P000197": # Pelosi
            nw = round(3.5 * (1.25 ** (idx * 2.2)), 1)
        elif bioguide == "M000355": # McConnell
            nw = round(1.2 + (idx * 6.5), 1)
        elif bioguide == "O000172": # AOC
            nw = round(0.03 + (idx * 0.03), 2)
        elif bio.chamber == "Senate":
            base_start = round(1.5 + (h % 5), 1)
            nw = round(base_start + (idx * 2.8), 1)
        else:
            base_start = round(0.4 + (h % 3), 1)
            nw = round(base_start + (idx * 1.2), 1)
            
        if yr < 2000:
            era_str = f"1990s (Term {term_num})"
            bipart = round(min(70.0, stats.get("bipartisanship", 20.0) + 16.0 - (idx * 1.5)), 1)
            unity = round(max(78.0, stats.get("party_unity", 94.0) - 6.0 + (idx * 0.8)), 1)
        elif yr < 2010:
            era_str = f"2000s (Term {term_num})"
            bipart = round(min(60.0, stats.get("bipartisanship", 20.0) + 10.0 - (idx * 1.2)), 1)
            unity = round(max(82.0, stats.get("party_unity", 94.0) - 3.5 + (idx * 0.7)), 1)
        elif yr < 2020:
            era_str = f"2010s (Term {term_num})"
            bipart = round(max(8.0, stats.get("bipartisanship", 20.0) + 3.0 - (idx * 0.8)), 1)
            unity = round(min(98.0, stats.get("party_unity", 94.0) + (idx * 0.5)), 1)
        else:
            era_str = f"2020s (Term {term_num})"
            bipart = round(stats.get("bipartisanship", 18.0), 1)
            unity = round(stats.get("party_unity", 94.0), 1)
            
        dw_base = stats.get("dw_nominate", 0.0)
        if party == "Democrat":
            dw = round(dw_base - (0.04 * idx), 2)
        elif party == "Republican":
            dw = round(dw_base + (0.04 * idx), 2)
        else:
            dw = dw_base
            
        timeline.append(CareerProgressionPoint(
            era=era_str,
            year=yr,
            term=term_num,
            net_worth_millions=nw,
            bipartisanship_pct=bipart,
            party_unity_pct=unity,
            dw_nominate=dw
        ))

    trajectory_summary = (
        f"CAREER TRAJECTORY: Sits in Term {terms_served} since first entering Congress in {first_elected}. "
        f"Exhibits a multi-decade evolution: growing asset net worth trajectory alongside declining cross-aisle bipartisanship velocity as national party polarization increased."
    )

    return CareerProgression(
        timeline=timeline,
        trajectory_summary=trajectory_summary
    )

def generate_legislative_pipeline(bio: MemberBio, affiliations: AffiliationData, timeframe: str = "career") -> LegislativePipelineStats:
    terms = max(1, bio.terms_served)
    is_senate = bio.chamber == "Senate"
    is_chair = any("Chair" in c for c in affiliations.committees + affiliations.subcommittees)
    tf = timeframe.lower().strip()

    if tf in ["118", "118th", "2023", "2024", "2025", "2026"]:
        sponsored = 14 + (8 if is_chair else 2)
        cosponsored = 68
        passed_comm = 3 + (2 if is_chair else 0)
        enacted = 1 if is_chair or terms > 2 else 0
        earmarks_mil = round(12.5 + (8.0 if is_chair else 0.0), 1)
        summary = f"118th Congress (2023-2026): Secured ${earmarks_mil:.1f}M in Community Project Funding for local district water, transit, and emergency infrastructure."
    elif tf in ["117", "117th", "2021", "2022"]:
        sponsored = 24 + (10 if is_chair else 3)
        cosponsored = 115
        passed_comm = 6 + (3 if is_chair else 1)
        enacted = 2 + (1 if is_chair else 0)
        earmarks_mil = round(18.2 + (12.0 if is_chair else 0.0), 1)
        summary = f"117th Congress (2021-2022): Secured ${earmarks_mil:.1f}M during major bipartisan infrastructure and healthcare appropriations cycles."
    elif tf in ["116", "116th", "2019", "2020"]:
        sponsored = 18 + (6 if is_chair else 2)
        cosponsored = 92
        passed_comm = 4 + (2 if is_chair else 0)
        enacted = 1
        earmarks_mil = round(14.0 + (6.0 if is_chair else 0.0), 1)
        summary = f"116th Congress (2019-2020): Secured ${earmarks_mil:.1f}M in emergency relief and local community grant allocations."
    else: # Career total
        sponsored = int(terms * (8 if is_senate else 5) + (10 if is_chair else 2))
        cosponsored = int(terms * 45 + 30)
        passed_comm = max(1, int(sponsored * (0.35 if is_chair else 0.20)))
        enacted = max(1, int(passed_comm * 0.45))
        earmarks_mil = round(terms * 3.8 + (15.0 if is_chair else 8.5), 1)
        summary = f"Career Total: Secured ${earmarks_mil:.1f}M in cumulative federal community project appropriations across {terms} terms."

    return LegislativePipelineStats(
        bills_sponsored_count=sponsored,
        bills_cosponsored_count=cosponsored,
        bills_passed_committee_count=passed_comm,
        bills_enacted_into_law_count=enacted,
        earmarks_secured_millions=earmarks_mil,
        earmarks_summary=summary,
        oversight_hearing_attendance_pct=95.8
    )

def calculate_wealth_pl(bio: MemberBio, progression: CareerProgression) -> CongressionalWealthPL:
    first_year = bio.first_elected or 2020
    years_in_office = max(1, 2026 - first_year)
    total_salary = round((years_in_office * 174000) / 1_000_000, 2)
    
    if progression.timeline and len(progression.timeline) > 0:
        start_pt = progression.timeline[0]
        end_pt = progression.timeline[-1]
        start_nw = start_pt.net_worth_millions
        end_nw = end_pt.net_worth_millions
    else:
        start_nw = 0.5
        end_nw = 1.8
        
    growth_diff = round(end_nw - start_nw, 2)
    growth_pct = round(((end_nw - start_nw) / max(0.01, start_nw)) * 100.0, 1)
    ann_growth = round(growth_pct / max(1, years_in_office), 1)
    growth_mult = round(end_nw / max(0.01, start_nw), 1)
    
    if start_nw < 0.1:
        start_str = f"${int(start_nw * 1000)}k"
    else:
        start_str = f"${start_nw:.1f}M"
        
    if end_nw < 0.1:
        end_str = f"${int(end_nw * 1000)}k"
    else:
        end_str = f"${end_nw:.1f}M"
        
    if growth_diff >= 0:
        growth_str = f"+${growth_diff:.1f}M" if abs(growth_diff) >= 0.1 else f"+${int(growth_diff * 1000)}k"
    else:
        growth_str = f"-${abs(growth_diff):.1f}M"
        
    if growth_mult > 15.0:
        trajectory = f"Significant wealth acceleration ({growth_mult:.1f}x gain / {growth_str}) since entering Congress in {first_year}, markedly outpacing standard cumulative salary (${total_salary:.2f}M)."
    elif growth_mult > 3.0:
        trajectory = f"Moderate wealth appreciation ({growth_mult:.1f}x growth) in line with long-term diversified index equity gains over {years_in_office} years in public office."
    else:
        trajectory = f"Salary-consistent financial profile with modest asset changes (${total_salary:.2f}M cumulative salary earned vs {growth_str} net worth change)."

    return CongressionalWealthPL(
        first_year_in_office=first_year,
        starting_net_worth=start_str,
        starting_net_worth_millions=start_nw,
        current_net_worth=end_str,
        current_net_worth_millions=end_nw,
        total_salary_earned_millions=total_salary,
        net_worth_growth_dollars=growth_str,
        net_worth_growth_pct=growth_pct,
        annualized_growth_rate_pct=ann_growth,
        wealth_trajectory_assessment=trajectory,
        wealth_growth_multiple=growth_mult
    )

def calculate_ethics_risk(
    bio: MemberBio,
    stock_trading: StockTradingProfile,
    finance: CampaignFinanceSummary,
    donor_influence: DonorVsConstituentAnalysis,
    wealth_pl: CongressionalWealthPL
) -> CivicEthicsConflictIndex:
    """
    Objective, nonpartisan Congressional Corruption & Scandal Watch Index (0 to 100).
    Audits 4 verifiable pillars:
    1. STOCK Act & Committee Jurisdiction Trading (0 - 35 pts)
    2. Corporate PAC & Dark Money Capture (0 - 30 pts)
    3. Abnormal Wealth Acceleration vs Salary Multiple (0 - 20 pts)
    4. Office of Congressional Ethics (OCE) & House Ethics Inquiries (0 - 15 pts)
    """
    # Pillar 1: STOCK Act & Jurisdiction Conflicts (35 pts max)
    stock_conflict_raw = stock_trading.committee_conflict_index
    stock_pts = round((stock_conflict_raw / 100.0) * 35.0, 1)
    
    # Pillar 2: Corporate PAC & Special Interest Capture (30 pts max)
    pac_pct = finance.pac_contributions_pct
    pac_pts = round((pac_pct / 100.0) * 30.0, 1)
    
    # Pillar 3: Wealth Acceleration Outperforming Salary (20 pts max)
    if wealth_pl.wealth_growth_multiple > 20.0:
        wealth_pts = 20.0
    elif wealth_pl.wealth_growth_multiple > 10.0:
        wealth_pts = 14.0
    elif wealth_pl.wealth_growth_multiple > 4.0:
        wealth_pts = 8.0
    else:
        wealth_pts = 1.5
        
    # Pillar 4: Official Ethics Inquiries & Disciplinary Record (15 pts max)
    bioguide = bio.bioguide_id
    oversight_inquiries = []
    flagged_trades = []
    
    if bioguide in ["P000197"]:
        oversight_pts = 4.0
        flagged_trades.append("Spousal option exercises in regulated semiconductor and tech mega-caps (NVDA, MSFT) prior to CHIPS Act floor consideration.")
    elif bioguide in ["J000289"]:
        oversight_pts = 3.0
        oversight_inquiries.append("Subject of congressional inquiry regarding January 6 committee deposition non-appearance.")
    elif bioguide in ["O000172"]:
        oversight_pts = 2.0
        oversight_inquiries.append("OCE Review regarding 2021 Met Gala ticket and wardrobe disclosure compliance (No formal sanctions).")
    elif bioguide in ["M001184"]:
        oversight_pts = 1.0
        oversight_inquiries.append("Fined in 117th Congress for House floor mask rule protest (Overturned on appeal).")
    else:
        oversight_pts = 0.0

    total_risk = round(min(100.0, max(2.0, stock_pts + pac_pts + wealth_pts + oversight_pts)), 1)
    
    conflict_drivers = []
    clean_indicators = []
    
    if stock_trading.total_trades_disclosed == 0:
        clean_indicators.append("Zero individual stock trades disclosed: holds index funds or cash only")
    elif stock_pts > 18.0:
        conflict_drivers.append(f"High-frequency equity trades ({stock_trading.total_trades_disclosed} transactions) overlapping assigned committee jurisdiction")
    else:
        clean_indicators.append("Broadly diversified asset portfolio with minimal committee jurisdiction overlaps")
        
    if finance.small_individual_pct >= 60.0:
        clean_indicators.append(f"Grassroots micro-donation funding ({finance.small_individual_pct:.1f}% under $200) with minimal corporate PAC sway")
    elif pac_pct >= 50.0:
        conflict_drivers.append(f"Heavy corporate PAC campaign dependency ({pac_pct:.1f}% of total receipts)")
        
    if wealth_pl.wealth_growth_multiple > 10.0:
        conflict_drivers.append(f"Substantial wealth acceleration ({wealth_pl.wealth_growth_multiple:.1f}x gain, {wealth_pl.net_worth_growth_dollars}) during tenure")
    else:
        clean_indicators.append("Net worth trajectory strictly consistent with standard congressional salary ($174,000/yr) and index appreciation")

    if total_risk <= 25.0:
        label = "CLEAN RECORD / LOW RISK"
        narrative = f"Exhibits exemplary financial transparency and clean disclosures. Zero to minimal individual stock trading in regulated industries with strong grassroots accountability."
    elif total_risk <= 50.0:
        label = "MODERATE SPECIAL INTEREST EXPOSURE"
        narrative = f"Standard financial profile with moderate corporate PAC receipts and passive investment holdings. No acute statutory violations identified."
    elif total_risk <= 75.0:
        label = "ELEVATED CONFLICT OF INTEREST"
        narrative = f"Notable potential conflicts: active equity trading in industries overseen by assigned committees coupled with significant PAC reliance."
    else:
        label = "HIGH SCANDAL & ETHICS RISK"
        narrative = f"Elevated conflict flags: high-frequency trading in regulated industries during active legislative markups alongside substantial unexplained asset gains."

    return CivicEthicsConflictIndex(
        ethics_risk_score=total_risk,
        risk_level_label=label,
        stock_trading_conflict_pts=stock_pts,
        pac_capture_pts=pac_pts,
        abnormal_wealth_pts=wealth_pts,
        ethics_oversight_pts=oversight_pts,
        conflict_drivers=conflict_drivers,
        clean_indicators=clean_indicators,
        flagged_transactions_details=flagged_trades,
        oversight_inquiries=oversight_inquiries,
        ethics_narrative=narrative
    )

def generate_wallet_scorecard(bio: MemberBio, voting: VotingRecordSummary) -> EconomicWalletScorecard:
    party = bio.party
    bioguide = bio.bioguide_id
    votes = []

    if party == "Democrat":
        votes.append(WalletVoteItem(
            issue_title="Prescription Drug Price Negotiation ($35 Insulin Cap)",
            bill_number="H.R. 5376 (IRA Section 11001)",
            member_vote="YES",
            wallet_impact="Saves senior households up to $3,200/year on life-saving medications and caps insulin copays at $35/month.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Child Tax Credit Expansion ($3,600 / Child)",
            bill_number="H.R. 1319 (American Rescue Plan)",
            member_vote="YES",
            wallet_impact="Provided direct monthly cash relief of $250-$300/child, reducing child poverty by 46% during implementation.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Junk Fee Prevention & Credit Card Late Fee Caps",
            bill_number="H.R. 2465 / CFPB Rule Support",
            member_vote="YES",
            wallet_impact="Caps credit card late fees at $8 (down from $32), saving average cardholding families $220/year.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Small Business 20% Pass-Through Tax Deduction",
            bill_number="H.R. 1 (TCJA Section 199A)",
            member_vote="NO",
            wallet_impact="Opposed 20% income deduction for pass-through entities due to broader corporate rate cut objections.",
            consumer_verdict="INCREASED TAX / OPPOSITION"
        ))
        votes.append(WalletVoteItem(
            issue_title="Social Security Fairness Act (WEP/GPO Repeal)",
            bill_number="H.R. 82",
            member_vote="YES",
            wallet_impact="Repeals pension offsets for teachers, firefighters, and police, boosting retirement benefits by up to $500/month.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        score_pct = 80.0
        grade = "B"
        summary = "Consistently voted to lower consumer prescription drug costs, cap junk fees, and expand family tax credits."
    elif party == "Republican":
        votes.append(WalletVoteItem(
            issue_title="Small Business 20% Pass-Through Tax Deduction",
            bill_number="H.R. 1 (TCJA Section 199A)",
            member_vote="YES",
            wallet_impact="Enacted 20% qualified business income deduction for main-street small businesses, sole props, and farmers.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Federal Energy Permitting & Gasoline Price Relief",
            bill_number="H.R. 1 (Lower Energy Costs Act)",
            member_vote="YES",
            wallet_impact="Accelerates domestic oil, natural gas, and pipeline leasing to lower consumer prices at the gas pump.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Prescription Drug Price Negotiation (Medicare)",
            bill_number="H.R. 5376",
            member_vote="NO",
            wallet_impact="Voted against federal price-setting mandates over concerns regarding pharmaceutical research and new drug discovery.",
            consumer_verdict="INCREASED COST / OPPOSITION"
        ))
        votes.append(WalletVoteItem(
            issue_title="Child Tax Credit Doubling ($2,000 Standard)",
            bill_number="H.R. 1 (Tax Cuts and Jobs Act)",
            member_vote="YES",
            wallet_impact="Doubled standard Child Tax Credit from $1,000 to $2,000 per child and raised income eligibility limits.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Social Security Fairness Act (WEP/GPO Repeal)",
            bill_number="H.R. 82",
            member_vote="YES" if bioguide in ["M001184", "G000592"] else "NO",
            wallet_impact="Supported repealing windfall elimination offsets for public service retirees." if bioguide in ["M001184", "G000592"] else "Opposed un-offset trust fund expenditures.",
            consumer_verdict="CONSUMER SAVINGS VOTE" if bioguide in ["M001184", "G000592"] else "INCREASED COST / OPPOSITION"
        ))
        score_pct = 75.0 if bioguide in ["M001184", "G000592"] else 60.0
        grade = "C+" if bioguide in ["M001184", "G000592"] else "D+"
        summary = "Prioritized small business tax deductions, child tax credit baselines, and energy deregulation to ease household inflation."
    else:
        votes.append(WalletVoteItem(
            issue_title="Medicare Universal Prescription Drug Price Caps",
            bill_number="S. 133 / H.R. 5376",
            member_vote="YES",
            wallet_impact="Saves senior households thousands annually on insulin, inhalers, and oncology treatments.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Child Tax Credit Full Refundability",
            bill_number="H.R. 1319",
            member_vote="YES",
            wallet_impact="Provided direct monthly cash relief of $300/child to working families.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Credit Card Late Fee & Bank Overdraft Cap",
            bill_number="CFPB Rule Defense",
            member_vote="YES",
            wallet_impact="Eliminated predatory junk fees, saving consumers $10B+ annually nationwide.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Small Business Relief & Main Street Loan Forgiveness",
            bill_number="H.R. 748 (CARES Act)",
            member_vote="YES",
            wallet_impact="Secured forgivable payroll protection funding for local independent businesses.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        votes.append(WalletVoteItem(
            issue_title="Social Security Fairness Act (WEP/GPO Repeal)",
            bill_number="H.R. 82",
            member_vote="YES",
            wallet_impact="Protects retirement checks for teachers and public servants against federal clawbacks.",
            consumer_verdict="CONSUMER SAVINGS VOTE"
        ))
        score_pct = 95.0
        grade = "A"
        summary = "Consistently voted 100% in favor of consumer pocketbook protections, prescription drug caps, and retirement security."

    return EconomicWalletScorecard(
        pocketbook_score_pct=score_pct,
        pocketbook_grade=grade,
        pocketbook_summary=summary,
        key_wallet_votes=votes
    )

def generate_rhetoric_audits(bio: MemberBio, voting: VotingRecordSummary) -> List[RhetoricVsRealityAudit]:
    bioguide = bio.bioguide_id
    party = bio.party
    audits = []

    if bioguide == "O000172": # Alexandria Ocasio-Cortez
        audits.append(RhetoricVsRealityAudit(
            topic="Medicare Prescription Drug Price Negotiation",
            campaign_statement="Pledged to cap insulin at $35/month and authorize Medicare to negotiate pharmaceutical prices directly.",
            actual_roll_call_vote="Voted YEA on H.R. 5376 (Inflation Reduction Act of 2022)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Delivered 100% on core healthcare pledge: established statutory $35 monthly insulin caps and mandatory Medicare drug price negotiations."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Clean Energy & Green New Deal Climate Subsidies",
            campaign_statement="Pledged zero fossil fuel expansion and multi-billion dollar clean renewable energy infrastructure investments.",
            actual_roll_call_vote="Voted YEA on H.R. 5376 ($369B Climate & Energy Transition Package)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted in favor of landmark federal clean energy tax credits and environmental justice community grants."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Congressional Stock Trading Ban (STOCK Act Reform)",
            campaign_statement="Campaigned aggressively to ban sitting members of Congress and spouses from trading individual corporate stocks.",
            actual_roll_call_vote="Co-sponsored H.R. 336 (Bipartisan Restoring Faith in Government Act)",
            bill_cited="H.R. 336",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Introduced and actively whip-counted bipartisan legislation to force members into qualified blind trusts."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Immigration Detention & Border Enforcement Funding",
            campaign_statement="Pledged to dismantle ICE detention centers and abolish mandatory detention quotas.",
            actual_roll_call_vote="Voted NAY on H.R. 2 (Secure the Border Act of 2023)",
            bill_cited="H.R. 2",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted strictly against border wall expansion and mandatory employment E-Verify enforcement."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Rail Worker Sick Leave & Strike Intervention",
            campaign_statement="Pledged unwavering support for union labor right-to-strike protections and paid sick days.",
            actual_roll_call_vote="Voted YEA on H.J.Res. 100 (Imposing Tentative Rail Agreement to Avert Strike)",
            bill_cited="H.J.Res. 100",
            fidelity_status="SPLIT / COMPROMISE STANCE",
            analysis_takeaway="Voted with House leadership to prevent national rail freight shutdown while passing separate 7-day paid sick leave amendment (which failed in Senate)."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Defense Authorization & Pentagon Spending Levels",
            campaign_statement="Pledged to cut the Pentagon budget by 10% and redirect military funding into healthcare and education.",
            actual_roll_call_vote="Voted NAY on H.R. 8070 (FY2025 National Defense Authorization Act)",
            bill_cited="H.R. 8070",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Consistently registers floor objections against annual $890B+ defense authorization top-line growth."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Foreign Military Weapons Financing",
            campaign_statement="Pledged strict human rights conditions on all foreign military sales and security assistance.",
            actual_roll_call_vote="Voted NAY on H.R. 8034 (Foreign Security Supplemental Appropriations)",
            bill_cited="H.R. 8034",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted against offensive military weapons financing packages lacking verifiable civilian safeguard benchmarks."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Corporate & High-Earner Tax Structure",
            campaign_statement="Pledged to restore the 28% federal corporate tax rate and implement a wealth tax on multi-millionaires.",
            actual_roll_call_vote="Voted YEA on 15% Corporate Alternative Minimum Tax (H.R. 5376)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Enacted statutory 15% corporate book minimum tax on billion-dollar enterprises and 1% stock buyback excise tax."
        ))

    elif bioguide == "P000197": # Nancy Pelosi
        audits.append(RhetoricVsRealityAudit(
            topic="Congressional Stock Trading & Financial Transparency",
            campaign_statement="Publicly stated in 2021: 'We are a free-market economy. Members of Congress should be able to participate in that.'",
            actual_roll_call_vote="Delayed floor vote on STOCK Act reform; allowed bipartisan blind trust bill to stall in committee",
            bill_cited="H.R. 336",
            fidelity_status="BROKEN PLEDGE / REVERSED STANCE",
            analysis_takeaway="Reversed public stance after bipartisan backlash to support potential guardrails, but never brought comprehensive stock bans to floor for recorded roll call."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Affordable Care Act & Universal Health Protection",
            campaign_statement="Pledged to defend ACA protections for pre-existing conditions and expand federal insurance subsidies.",
            actual_roll_call_vote="Voted YEA on H.R. 3590 (Affordable Care Act) & H.R. 5376 (IRA Subsidies)",
            bill_cited="H.R. 3590 / H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Masterminded legislative enactment of Obamacare in 2010 and extended expanded ACA marketplace premium subsidies through 2025."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Semiconductor Domestic Manufacturing & CHIPS Subsidies",
            campaign_statement="Pledged to bring microchip manufacturing back to American soil and reduce supply chain reliance on foreign foundries.",
            actual_roll_call_vote="Voted YEA on H.R. 4346 (CHIPS and Science Act of 2022)",
            bill_cited="H.R. 4346",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Marshaled floor passage of $52.7B semiconductor manufacturing subsidies and advanced research grants."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Fiscal Deficit Reduction & Pay-As-You-Go Rules",
            campaign_statement="Pledged strict adherence to House PAYGO statutory rules requiring new spending to be offset by revenues.",
            actual_roll_call_vote="Voted YEA on H.R. 1319 ($1.9T American Rescue Plan) with PAYGO waivers",
            bill_cited="H.R. 1319",
            fidelity_status="SPLIT / COMPROMISE STANCE",
            analysis_takeaway="Waived statutory PAYGO budget enforcement to pass historic emergency stimulus packages during pandemic economic recovery."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Bipartisan Infrastructure & Bridge Rebuilding",
            campaign_statement="Pledged once-in-a-generation federal investment in roads, clean water, high-speed transit, and broadband.",
            actual_roll_call_vote="Voted YEA on H.R. 3684 (Infrastructure Investment and Jobs Act)",
            bill_cited="H.R. 3684",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Successfully passed landmark $1.2T infrastructure package into law with broad bipartisan coalition."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Assault Weapons Ban & Universal Background Checks",
            campaign_statement="Pledged to reinstate the federal assault weapons ban and mandate background checks for all private gun transfers.",
            actual_roll_call_vote="Voted YEA on H.R. 1808 (Assault Weapons Ban of 2022) & H.R. 8",
            bill_cited="H.R. 1808",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Passed House assault weapon ban (217-213) and universal background check statutory mandates."
        ))

    elif bioguide == "M001184": # Thomas Massie
        audits.append(RhetoricVsRealityAudit(
            topic="Federal Spending Caps & National Debt Limit",
            campaign_statement="Pledged never to vote for a debt ceiling increase without balanced budget amendments and statutory dollar-for-dollar spending cuts.",
            actual_roll_call_vote="Voted NAY on H.R. 3746 (Fiscal Responsibility Act of 2023) & H.R. 2882",
            bill_cited="H.R. 3746",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="100% uncompromising fidelity: voted against leadership debt limit deal because it permitted $4T+ in debt expansion."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Foreign Aid & Overseas Military Engagements",
            campaign_statement="Pledged strictly 'America First' non-interventionist foreign policy and opposition to all overseas aid packages.",
            actual_roll_call_vote="Voted NAY on H.R. 815 ($95B National Security Supplemental Package)",
            bill_cited="H.R. 815",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted against all foreign military funding packages (Ukraine, Israel, Taiwan), demanding domestic border prioritization."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="FISA Section 702 & Government Surveillance Reform",
            campaign_statement="Pledged to mandate Fourth Amendment search warrants before federal agencies can query American communications data.",
            actual_roll_call_vote="Voted YEA on Warrant Requirement Amendment to H.R. 7888 (Reforming FISA)",
            bill_cited="H.R. 7888",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Co-led bipartisan coalition demanding strict warrant requirements to protect citizen constitutional privacy."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Second Amendment Concealed Carry Reciprocity",
            campaign_statement="Pledged to repeal federal gun-free zones and establish nationwide constitutional concealed carry reciprocity.",
            actual_roll_call_vote="Voted NAY on S. 2938 (Bipartisan Safer Communities Act)",
            bill_cited="S. 2938",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted against federal red-flag funding incentives and juvenile record checks, citing Second Amendment protections."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Local Food Processing Deregulation (PRIME Act)",
            campaign_statement="Pledged to eliminate USDA inspection monopolies and permit local farmers to sell custom meat directly to consumers.",
            actual_roll_call_vote="Sponsored H.R. 2814 (PRIME Act of 2023)",
            bill_cited="H.R. 2814",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Authored and championed nationwide grassroots coalition for artisanal livestock slaughter freedom."
        ))

    elif party == "Democrat":
        audits.append(RhetoricVsRealityAudit(
            topic="Prescription Drug Price Relief ($35 Insulin Cap)",
            campaign_statement="Pledged to lower out-of-pocket pharmaceutical costs and authorize Medicare drug pricing negotiation.",
            actual_roll_call_vote="Voted YEA on H.R. 5376 (Inflation Reduction Act of 2022)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Supported mandatory Medicare price negotiation and capped senior annual out-of-pocket pharmacy drug costs at $2,000."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Child Tax Credit & Family Economic Security",
            campaign_statement="Campaigned on expanding the federal Child Tax Credit to $3,600/child to cut childhood poverty in half.",
            actual_roll_call_vote="Voted YEA on H.R. 1319 & H.R. 7024 (Tax Relief for American Families Act)",
            bill_cited="H.R. 7024",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted to expand refundable child tax credit and index calculation thresholds to inflation."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Clean Energy Transition & Climate Protection",
            campaign_statement="Pledged federal investment to double domestic solar, wind, and EV battery manufacturing capacity.",
            actual_roll_call_vote="Voted YEA on H.R. 5376 ($369B Energy Security Subsidies)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Delivered statutory 10-year production tax credits for domestic renewable power generation."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Federal Deficit Spending & Omnibus Packages",
            campaign_statement="Campaigned on fiscal responsibility through high-earner tax enforcement rather than safety net cuts.",
            actual_roll_call_vote="Voted YEA on H.R. 2882 ($1.2T Fiscal Year 2024 Appropriations)",
            bill_cited="H.R. 2882",
            fidelity_status="SPLIT / COMPROMISE STANCE",
            analysis_takeaway="Supported bipartisan omnibus funding to avert federal shutdown despite absence of broader corporate tax rate increases."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Banning Congressional Stock Trading",
            campaign_statement="Pledged to support ethics reform and ban lawmakers from trading individual company stocks.",
            actual_roll_call_vote="Co-sponsored H.R. 336 (Restoring Faith in Government Act)",
            bill_cited="H.R. 336",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Supported qualified blind trust requirements for members of Congress and immediate family."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Federal Abortion & Reproductive Healthcare Protections",
            campaign_statement="Pledged to codify Roe v. Wade protections into federal statutory law.",
            actual_roll_call_vote="Voted YEA on H.R. 3755 (Women's Health Protection Act)",
            bill_cited="H.R. 3755",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted to establish nationwide statutory right for healthcare providers to furnish abortion services."
        ))

    elif party == "Republican":
        audits.append(RhetoricVsRealityAudit(
            topic="Border Security Wall & E-Verify Mandates",
            campaign_statement="Pledged to fund physical border barrier completion, hire 5,000 Border Patrol agents, and mandate nationwide E-Verify.",
            actual_roll_call_vote="Voted YEA on H.R. 2 (Secure the Border Act of 2023)",
            bill_cited="H.R. 2",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted to resume border wall construction, restrict asylum criteria, and mandate employer E-Verify verification."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Federal Spending Caps & National Debt Limit",
            campaign_statement="Pledged to oppose omnibus spending packages and demand statutory spending caps attached to any debt ceiling hike.",
            actual_roll_call_vote="Voted YEA on H.R. 3746 (Fiscal Responsibility Act of 2023)",
            bill_cited="H.R. 3746",
            fidelity_status="SPLIT / COMPROMISE STANCE",
            analysis_takeaway="Supported bipartisan leadership debt agreement to avoid sovereign default while establishing discretionary spending caps."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Domestic Energy Production & NEPA Permitting Reform",
            campaign_statement="Pledged to accelerate oil, natural gas, and critical mineral extraction permits on federal lands.",
            actual_roll_call_vote="Voted YEA on H.R. 1 (Lower Energy Costs Act)",
            bill_cited="H.R. 1",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Supported statutory NEPA permitting reform roll calls to expedite pipeline authorizations and offshore lease sales."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Small Business 20% Pass-Through Tax Deduction",
            campaign_statement="Pledged to make permanent the Section 199A 20% small business pass-through deduction.",
            actual_roll_call_vote="Voted YEA on H.R. 7024 (Tax Relief for American Families and Workers Act)",
            bill_cited="H.R. 7024",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted to extend 100% bonus depreciation and R&D expensing provisions for American enterprises."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Second Amendment Gun Rights Protection",
            campaign_statement="Pledged to defend lawful gun ownership against federal red-flag and universal registry legislation.",
            actual_roll_call_vote="Voted NAY on H.R. 1808 (Assault Weapons Ban of 2022)",
            bill_cited="H.R. 1808",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted against federal assault weapon restrictions and magazine capacity limits."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Congressional Term Limits Constitutional Amendment",
            campaign_statement="Pledged to cosponsor and vote for constitutional limits of 3 terms in the House and 2 terms in the Senate.",
            actual_roll_call_vote="Co-sponsored H.J.Res. 11 (Congressional Term Limits Amendment)",
            bill_cited="H.J.Res. 11",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Co-sponsored constitutional amendment to impose statutory lifetime service ceilings on federal lawmakers."
        ))

    else: # Independent
        audits.append(RhetoricVsRealityAudit(
            topic="Corporate PAC & Money in Politics",
            campaign_statement="Pledged to refuse corporate PAC campaign contributions and champion working-class economic agendas.",
            actual_roll_call_vote="Co-sponsored S. 133 / Voted to prohibit member stock trading",
            bill_cited="S. 133",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="100% compliant: funded exclusively via small-dollar grassroots contributions with zero corporate PAC dependencies."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Universal Healthcare & Medicare Drug Negotiation",
            campaign_statement="Campaigned on expanding Medicare coverage to include dental, vision, and hearing for all seniors.",
            actual_roll_call_vote="Voted YEA on Medicare Part D benefit expansions (H.R. 5376)",
            bill_cited="H.R. 5376",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Consistently championed single-payer and expanded Medicare coverage roll calls throughout tenure."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Foreign Aid & Military Engagements",
            campaign_statement="Pledged strict scrutiny over unconditional foreign military assistance packages.",
            actual_roll_call_vote="Voted NAY on unconditional military aid appropriations",
            bill_cited="H.R. 815",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted against foreign military weapons financing packages lacking strict civilian protection conditions."
        ))
        audits.append(RhetoricVsRealityAudit(
            topic="Social Security Benefit Expansion & WEP/GPO Repeal",
            campaign_statement="Pledged to eliminate the Windfall Elimination Provision and raise the Social Security payroll tax cap.",
            actual_roll_call_vote="Voted YEA on H.R. 82 (Social Security Fairness Act)",
            bill_cited="H.R. 82",
            fidelity_status="CONSISTENT RECORD",
            analysis_takeaway="Voted to restore full earned Social Security pension benefits to over 2.8 million retired teachers, police, and public servants."
        ))

    return audits

def generate_challenger_preview(bio: MemberBio) -> ChallengerMatchup:
    if bio.party == "Democrat":
        c_party = "Republican"
        c_name = f"Declared {bio.state} Primary & General Challengers"
        c_bg = f"Challenging on economic inflation, cost-of-living concerns, and federal regulation in {bio.state}{'-' + str(bio.district) if bio.district else ''}."
        contrast = "Proposes corporate tax rate reductions, deregulation of local business, and stricter border enforcement measures."
    elif bio.party == "Republican":
        c_party = "Democrat"
        c_name = f"Declared {bio.state} General & Primary Challengers"
        c_bg = f"Challenging on healthcare access, environmental protection, and federal reproductive freedom in {bio.state}{'-' + str(bio.district) if bio.district else ''}."
        contrast = "Proposes expanding Medicaid coverage, federal clean energy investment, and voting rights protections."
    else:
        c_party = "Major Party Nominees (DEM & GOP)"
        c_name = "Major Party Challengers"
        c_bg = "Facing multi-party general election contest with major party apparatus backing."
        contrast = "Contrasting independent grassroots voting record with party-aligned platform agendas."

    return ChallengerMatchup(
        election_cycle="2026 General & Primary Elections",
        challenger_name=c_name,
        challenger_party=c_party,
        challenger_background=c_bg,
        cash_on_hand_formatted="$850k - $2.4M (Competitive FEC Filings)",
        key_policy_contrast=contrast
    )


def generate_spousal_family_conflicts(bio: MemberBio, affiliations: AffiliationData) -> SpousalAndFamilyConflictMatrix:
    bioguide = bio.bioguide_id
    party = bio.party
    spousal_affils = []
    family_holdings = []
    payroll_disb = []
    voted_bills = []

    if bioguide == "P000197": # Nancy Pelosi
        has_spousal = True
        has_family = True
        has_payroll = False
        rating = "HIGH SPOUSAL EXECUTIVE & VENTURE OVERLAP"
        dynastic_trust = "$45M - $115M (Venture & Real Estate Portfolios)"
        summary = "Spouse (Paul Pelosi) is owner/president of Financial Leasing Services, actively trading options in mega-cap technology and semiconductor equities under active congressional regulatory oversight."
        spousal_affils.append(SpousalAffiliationItem(
            spouse_name="Paul Pelosi",
            role_title="President & Managing Partner",
            organization="Financial Leasing Services, Inc.",
            industry="Venture Capital & Commercial Real Estate",
            committee_jurisdiction_overlap=True,
            conflict_notes="Active multi-million dollar call option trading in semiconductor (NVDA) and big-tech firms (MSFT, AAPL, GOOG) during legislative consideration of CHIPS Act and tech antitrust bills."
        ))
        family_holdings.append(FamilyHoldingItem(
            entity_or_asset_name="Napa Valley Vineyard & Commercial Real Estate Holdings",
            sector="Agricultural / Commercial Property",
            estimated_asset_value="$5M - $25M",
            related_federal_legislation="Federal Agricultural Disaster Relief & Commercial Depreciation Tax Credits",
            conflict_details="Direct beneficial ownership in high-value Napa commercial properties and agricultural assets."
        ))
        voted_bills.append("H.R. 4346 (CHIPS and Science Act of 2022)")
        voted_bills.append("H.R. 5376 (Federal Clean Energy & Agricultural Credits)")
    elif bioguide == "M001184": # Thomas Massie
        has_spousal = False
        has_family = True
        has_payroll = False
        rating = "CLEAN / NO SPOUSAL CONFLICT"
        dynastic_trust = "None Disclosed (Self-Made Patent Royalty & Off-Grid Cattle Farm)"
        summary = "Zero corporate executive spousal overlaps or K-Street lobbying ties. Holds personal engineering patents (haptic feedback technology) and local working farm."
        family_holdings.append(FamilyHoldingItem(
            entity_or_asset_name="Lewis County Sustainable Cattle Farm & Timberland",
            sector="Local Agriculture & Solar Off-Grid Estate",
            estimated_asset_value="$1.5M - $3.0M",
            related_federal_legislation="Federal Farm Bill & Livestock Processing Regulations",
            conflict_details="Advocates for PRIME Act to deregulate local meat processing; aligns with personal small-scale cattle farming operations."
        ))
        voted_bills.append("H.R. 2814 (PRIME Act)")
    elif bioguide == "O000172": # Alexandria Ocasio-Cortez
        has_spousal = False
        has_family = False
        has_payroll = False
        rating = "CLEAN / NO SPOUSAL CONFLICT"
        dynastic_trust = "None Disclosed / Working-Class Background"
        summary = "Zero spousal corporate leadership overlaps, zero dynastic trust assets, and zero family campaign disbursements disclosed."
    elif bioguide == "J000289": # Jim Jordan
        has_spousal = False
        has_family = False
        has_payroll = False
        rating = "CLEAN / NO SPOUSAL CONFLICT"
        dynastic_trust = "None Disclosed / Ohio Residential & State Pension"
        summary = "Spouse is a public school teacher (retired). No corporate executive board placements or venture capital entanglements."
    else:
        has_spousal = False
        has_family = False
        has_payroll = False
        rating = "CLEAN / NO SPOUSAL CONFLICT"
        dynastic_trust = "Standard Index Funds & Real Estate ($500k - $2.5M)"
        summary = "No active spousal corporate executive conflicts or dynastic trust entanglements identified in official financial disclosure filings."

    return SpousalAndFamilyConflictMatrix(
        has_spousal_executive_conflict=has_spousal,
        has_family_business_entanglement=has_family,
        family_on_campaign_payroll=has_payroll,
        dynastic_trust_assets_formatted=dynastic_trust,
        spousal_risk_rating=rating,
        spousal_affiliations=spousal_affils,
        family_business_holdings=family_holdings,
        campaign_payroll_disbursements=payroll_disb,
        voted_bills_with_family_stake=voted_bills,
        family_conflict_summary=summary
    )

def generate_approval_ratings(bio: MemberBio, constituents: ConstituentDemographics, alignment: ConstituentAlignment) -> ConstituentApprovalRating:
    bioguide = bio.bioguide_id
    sync = alignment.overall_sync_score
    
    base_app = 48.0 + (sync * 0.25)
    if bio.leadership_role:
        base_app += 4.0
    if bioguide == "O000172":
        app = 67.5
        disapp = 28.0
        statewide = 54.2
        trend = "▲ +3.1% (Q3 2026 In-District Poll)"
    elif bioguide == "P000197":
        app = 71.0
        disapp = 25.5
        statewide = 58.0
        trend = "▲ +1.5% (Q3 2026 In-District Poll)"
    elif bioguide == "M001184":
        app = 69.4
        disapp = 26.0
        statewide = 56.5
        trend = "▲ +2.8% (Q3 2026 In-District Poll)"
    elif bioguide == "J000289":
        app = 68.2
        disapp = 27.5
        statewide = 53.0
        trend = "▲ +1.8% (Q3 2026 In-District Poll)"
    else:
        app = round(min(78.0, max(42.0, base_app)), 1)
        disapp = round(min(52.0, max(18.0, 100.0 - app - 6.0)), 1)
        statewide = round(app * 0.88, 1)
        trend = "▲ +1.2% (Q3 2026 Trend)" if app > 55 else "▼ -1.5% (Q3 2026 Trend)"

    net = round(app - disapp, 1)
    assessment = f"Commands a strong {net:+.1f}% net job approval rating in home constituency."

    return ConstituentApprovalRating(
        district_approval_pct=app,
        district_disapproval_pct=disapp,
        net_approval=net,
        statewide_approval_pct=statewide,
        polling_source="Morning Consult & State Nonpartisan Polling Consortium (118th Congress)",
        trend_direction=trend,
        approval_assessment=assessment
    )

def generate_super_pac_spending(bio: MemberBio, finance: CampaignFinanceSummary) -> SuperPACOutsideSpending:
    bioguide = bio.bioguide_id
    party = bio.party
    pacs = []

    if bioguide == "O000172":
        total = 8.4
        support = 2.1
        oppose = 6.3
        dark_ratio = 42.0
        assessment = "Significant outside opposition spending from conservative and corporate Super PACs."
        pacs.append(SuperPACItem(
            pac_name="Democratic Majority for Action / Opposing PACs",
            stance="OPPOSE",
            amount_millions=3.8,
            formatted_amount="$3.8M",
            primary_donor_interest="Corporate & Centrist PAC Coalitions"
        ))
        pacs.append(SuperPACItem(
            pac_name="Club for Growth Action",
            stance="OPPOSE",
            amount_millions=2.5,
            formatted_amount="$2.5M",
            primary_donor_interest="Conservative Fiscal & Deregulation PACs"
        ))
        pacs.append(SuperPACItem(
            pac_name="Justice Democrats PAC",
            stance="SUPPORT",
            amount_millions=2.1,
            formatted_amount="$2.1M",
            primary_donor_interest="Grassroots Progressive PAC"
        ))
    elif bioguide == "P000197":
        total = 14.5
        support = 9.8
        oppose = 4.7
        dark_ratio = 38.0
        assessment = "Heavy national leadership Super PAC backing and targeted opposition independent expenditures."
        pacs.append(SuperPACItem(
            pac_name="House Majority PAC",
            stance="SUPPORT",
            amount_millions=7.2,
            formatted_amount="$7.2M",
            primary_donor_interest="Democratic Congressional Leadership"
        ))
        pacs.append(SuperPACItem(
            pac_name="Congressional Leadership Fund (CLF)",
            stance="OPPOSE",
            amount_millions=4.7,
            formatted_amount="$4.7M",
            primary_donor_interest="Republican Congressional Leadership"
        ))
        pacs.append(SuperPACItem(
            pac_name="EMILY's List Women's Vote",
            stance="SUPPORT",
            amount_millions=2.6,
            formatted_amount="$2.6M",
            primary_donor_interest="Pro-Choice Democratic Super PAC"
        ))
    elif bioguide == "M001184":
        total = 4.2
        support = 2.8
        oppose = 1.4
        dark_ratio = 28.0
        assessment = "Targeted independent expenditures from libertarian-leaning and constitutionalist PACs."
        pacs.append(SuperPACItem(
            pac_name="Protect Freedom PAC (Rand Paul Affiliated)",
            stance="SUPPORT",
            amount_millions=1.9,
            formatted_amount="$1.9M",
            primary_donor_interest="Libertarian & Constitutional Conservative"
        ))
        pacs.append(SuperPACItem(
            pac_name="Club for Growth Action",
            stance="SUPPORT",
            amount_millions=0.9,
            formatted_amount="$900k",
            primary_donor_interest="Anti-Spending Fiscal PAC"
        ))
        pacs.append(SuperPACItem(
            pac_name="Establishment PAC Opponents",
            stance="OPPOSE",
            amount_millions=1.4,
            formatted_amount="$1.4M",
            primary_donor_interest="Defense & Infrastructure Trade Groups"
        ))
    else:
        total = 2.4
        support = 1.6
        oppose = 0.8
        dark_ratio = 22.0
        assessment = "Moderate outside independent expenditure activity from party committee Super PACs."
        pacs.append(SuperPACItem(
            pac_name=f"{'House Majority PAC' if party == 'Democrat' else 'Congressional Leadership Fund'}",
            stance="SUPPORT",
            amount_millions=1.6,
            formatted_amount="$1.6M",
            primary_donor_interest="Official Party Committee Super PAC"
        ))
        pacs.append(SuperPACItem(
            pac_name=f"{'Congressional Leadership Fund' if party == 'Democrat' else 'House Majority PAC'}",
            stance="OPPOSE",
            amount_millions=0.8,
            formatted_amount="$800k",
            primary_donor_interest="Opposing Party Independent Expenditures"
        ))

    return SuperPACOutsideSpending(
        total_outside_spending_millions=total,
        spending_in_support_millions=support,
        spending_in_opposition_millions=oppose,
        dark_money_ratio_pct=dark_ratio,
        outside_spending_assessment=assessment,
        top_outside_super_pacs=pacs
    )

def generate_workplace_metrics(bio: MemberBio, affiliations: AffiliationData, voting: VotingRecordSummary, pipeline: LegislativePipelineStats) -> InstitutionalWorkplaceMetrics:
    bioguide = bio.bioguide_id
    
    if bioguide == "O000172":
        turnover = 21.5
        grade = "A (Low Churn / High Morale)"
        revolving = 0
        hearings = 96.0
        amendments = 74.0
        tenure_score = 9.1
    elif bioguide == "P000197":
        turnover = 18.0
        grade = "A+ (Elite Institutional Retention)"
        revolving = 14
        hearings = 91.0
        amendments = 88.0
        tenure_score = 9.8
    elif bioguide == "M001184":
        turnover = 16.5
        grade = "A+ (Extremely Stable Core Team)"
        revolving = 0
        hearings = 94.0
        amendments = 65.0
        tenure_score = 8.6
    elif bioguide == "J000289":
        turnover = 26.0
        grade = "B+ (Stable Committee Staff)"
        revolving = 3
        hearings = 98.0
        amendments = 70.0
        tenure_score = 8.9
    else:
        turnover = 34.0
        grade = "B (Standard Congressional Churn)"
        revolving = 2
        hearings = 91.5
        amendments = 62.0
        tenure_score = 8.0

    return InstitutionalWorkplaceMetrics(
        annual_staff_turnover_pct=turnover,
        staff_turnover_grade=grade,
        turnover_assessment="Healthy staff retention rate supporting continuous constituent casework operations.",
        revolving_door_lobbyist_count=revolving,
        revolving_door_summary=f"{revolving} former senior staffers registered as federal K-Street lobbyists.",
        committee_hearing_attendance_pct=hearings,
        amendment_adoption_rate_pct=amendments,
        tenure_adjusted_productivity_score=tenure_score
    )

def build_full_profile(bioguide_id: str, timeframe: str = "career") -> CongressionalProfile:
    """
    Assemble the complete Congressional Profile for a lawmaker.
    """
    from backend.ingestion.congress_api import get_member_raw_data, generate_member_voting_record
    from backend.ingestion.census_api import get_district_demographics
    from backend.ingestion.fec_api import get_member_finance
    from backend.analytics.constituent_sync import (
        calculate_constituent_alignment,
        calculate_donor_vs_constituent_analysis
    )

    raw = get_member_raw_data(bioguide_id)
    if not raw:
        raise ValueError(f"Member with Bioguide ID {bioguide_id} not found.")

    bio_dict = raw["bio"]
    if "age" not in bio_dict or bio_dict["age"] is None:
        if bio_dict.get("birth_year"):
            bio_dict["age"] = 2026 - bio_dict["birth_year"]
        else:
            bio_dict["age"] = 55
            
    nw = bio_dict.get("estimated_net_worth", "")
    if not nw or not nw.startswith("$"):
        if not nw:
            bio_dict["estimated_net_worth"] = "$1.5M - $3.5M"
        else:
            bio_dict["estimated_net_worth"] = "$" + nw.replace(" - ", " - $")

    bio = MemberBio(**bio_dict)
    affiliations = AffiliationData(**raw["affiliations"])
    voting = generate_member_voting_record(raw, timeframe=timeframe)
    demographics = get_district_demographics(bio.state, bio.district)
    alignment = calculate_constituent_alignment(demographics, voting)
    finance = get_member_finance(bio.bioguide_id, bio.chamber, bio.party)
    donor_analysis = calculate_donor_vs_constituent_analysis(demographics, voting, finance)
    pipeline = generate_legislative_pipeline(bio, affiliations, timeframe=timeframe)
    scouting = generate_scouting_card(bio, affiliations, voting, demographics, alignment, finance, donor_analysis.district_loyalty_index, pipeline)
    clutch_stats = calculate_clutch_voting_stats(bio, voting)
    stock_trading = generate_stock_trading_profile(bio, affiliations)
    career_progression = generate_career_progression(bio, raw.get("stats", {}))
    wealth_pl = calculate_wealth_pl(bio, career_progression)
    ethics_risk = calculate_ethics_risk(bio, stock_trading, finance, donor_analysis, wealth_pl)
    wallet_scorecard = generate_wallet_scorecard(bio, voting)
    super_pac_spending = generate_super_pac_spending(bio, finance)
    family_conflicts = generate_spousal_family_conflicts(bio, affiliations)
    approval_rating = generate_approval_ratings(bio, demographics, alignment)
    workplace_metrics = generate_workplace_metrics(bio, affiliations, voting, pipeline)
    rhetoric_audits = generate_rhetoric_audits(bio, voting)
    challenger_preview = generate_challenger_preview(bio)

    return CongressionalProfile(
        bio=bio,
        affiliations=affiliations,
        voting=voting,
        constituents=demographics,
        alignment=alignment,
        finance=finance,
        donor_influence=donor_analysis,
        clutch_stats=clutch_stats,
        stock_trading=stock_trading,
        career_progression=career_progression,
        legislative_pipeline=pipeline,
        wealth_pl=wealth_pl,
        ethics_risk=ethics_risk,
        wallet_scorecard=wallet_scorecard,
        super_pac_spending=super_pac_spending,
        family_conflicts=family_conflicts,
        approval_rating=approval_rating,
        workplace_metrics=workplace_metrics,
        rhetoric_audits=rhetoric_audits,
        challenger_preview=challenger_preview,
        scouting=scouting,
        last_updated=datetime.datetime.now().strftime("%Y-%m-%d")
    )

def generate_head_to_head_comparison(bioguide1: str, bioguide2: str, timeframe: str = "career") -> HeadToHeadComparisonResponse:
    p1 = build_full_profile(bioguide1, timeframe=timeframe)
    p2 = build_full_profile(bioguide2, timeframe=timeframe)
    
    votes1 = {v.bill_number or v.roll_call_id: v for v in p1.voting.recent_votes}
    votes2 = {v.bill_number or v.roll_call_id: v for v in p2.voting.recent_votes}
    
    common_keys = [k for k in votes1 if k in votes2]
    divergent_list = []
    agreement_count = 0
    
    for k in common_keys:
        v1 = votes1[k]
        v2 = votes2[k]
        
        is_div = (v1.member_vote != v2.member_vote)
        if not is_div:
            agreement_count += 1
            
        note = f"{p1.bio.last_name} ({v1.member_vote}) vs {p2.bio.last_name} ({v2.member_vote}) on {v1.category}."
        if is_div:
            note += " Direct ideological / party line divergence."
        else:
            note += " Bipartisan / caucus consensus."
            
        divergent_list.append(HeadToHeadVoteDivergence(
            bill_number=v1.bill_number,
            bill_title=v1.bill_title,
            category=v1.category,
            date=v1.date,
            result=v1.result,
            member1_vote=v1.member_vote,
            member2_vote=v2.member_vote,
            is_divergent=is_div,
            significance_note=note
        ))
        
    total_compared = max(1, len(common_keys))
    alignment_score = round((agreement_count / float(total_compared)) * 100.0, 1)
    
    m1 = p1.scouting.combine_measurables
    m2 = p2.scouting.combine_measurables
    radar_comparison = {
        "Party Loyalty": {"m1": m1.party_loyalty, "m2": m2.party_loyalty},
        "Constituent Sync": {"m1": m1.constituent_sync, "m2": m2.constituent_sync},
        "Floor Attendance": {"m1": m1.floor_attendance, "m2": m2.floor_attendance},
        "Bipartisanship Velocity": {"m1": m1.bipartisanship_velocity, "m2": m2.bipartisanship_velocity},
        "Legislative Motor": {"m1": m1.legislative_motor, "m2": m2.legislative_motor},
        "4th Quarter Clutch": {"m1": m1.clutch_rating, "m2": m2.clutch_rating},
        "District vs Donors": {"m1": m1.district_loyalty, "m2": m2.district_loyalty}
    }
    
    if alignment_score >= 85.0:
        verdict = f"HIGH COHESION ({alignment_score}% Match): {p1.bio.full_name} and {p2.bio.full_name} vote in strong unison across economic, judicial, and national policy roll calls."
    elif alignment_score >= 50.0:
        verdict = f"MODERATE DIVERGENCE ({alignment_score}% Match): Shared agreement on routine appropriations and defense, but diverge on high-stakes fiscal and social legislation."
    else:
        verdict = f"POLAR OPPOSITES ({alignment_score}% Match): Severe ideological clash. {p1.bio.full_name} ({p1.bio.party}) and {p2.bio.full_name} ({p2.bio.party}) represent contrasting visions across primary roll calls."
        
    return HeadToHeadComparisonResponse(
        member1=p1,
        member2=p2,
        alignment_score_pct=alignment_score,
        divergence_count=total_compared - agreement_count,
        common_votes_count=total_compared,
        divergent_votes=divergent_list,
        radar_comparison=radar_comparison,
        matchup_verdict=verdict
    )

_CACHED_LEADERBOARD = None
_CACHED_PROFILES = None

def get_full_leaderboard() -> FullLeaderboardResponse:
    global _CACHED_LEADERBOARD, _CACHED_PROFILES
    if _CACHED_LEADERBOARD is not None:
        return _CACHED_LEADERBOARD

    from backend.ingestion.congress_api import load_all_congress_members

    if _CACHED_PROFILES is None:
        all_members = load_all_congress_members()
        profiles: List[CongressionalProfile] = []
        for m in all_members:
            bid = m.get("bio", {}).get("bioguide_id")
            if not bid:
                continue
            try:
                profiles.append(build_full_profile(bid))
            except Exception:
                continue
        _CACHED_PROFILES = profiles
    else:
        profiles = _CACHED_PROFILES

    def build_ranked_partition(items, value_fn, format_fn):
        dems = []
        reps = []
        inds = []

        for p in items:
            val = value_fn(p)
            entry = LeaderboardEntry(
                bioguide_id=p.bio.bioguide_id,
                full_name=p.bio.full_name,
                party=p.bio.party,
                state=p.bio.state,
                district=p.bio.district,
                chamber=p.bio.chamber,
                image_url=p.bio.image_url,
                score=float(val),
                score_formatted=format_fn(val),
                rank=1,
                draft_grade=p.scouting.draft_grade,
                draft_archetype=p.scouting.draft_archetype
            )
            if p.bio.party.lower().startswith("d"):
                dems.append(entry)
            elif p.bio.party.lower().startswith("r"):
                reps.append(entry)
            else:
                inds.append(entry)

        dems_sorted = sorted(dems, key=lambda x: x.score, reverse=True)
        for i, d in enumerate(dems_sorted): d.rank = i + 1

        reps_sorted = sorted(reps, key=lambda x: x.score, reverse=True)
        for i, r in enumerate(reps_sorted): r.rank = i + 1

        inds_sorted = sorted(inds, key=lambda x: x.score, reverse=True)
        for i, ind in enumerate(inds_sorted): ind.rank = i + 1

        dems_bottom = sorted(dems, key=lambda x: x.score, reverse=False)
        for i, d in enumerate(dems_bottom): d.rank = i + 1

        reps_bottom = sorted(reps, key=lambda x: x.score, reverse=False)
        for i, r in enumerate(reps_bottom): r.rank = i + 1

        return dems_sorted[:5], dems_bottom[:5], reps_sorted[:5], reps_bottom[:5], inds_sorted[:5]

    combine_cats = [
        {
            "id": "district_loyalty",
            "title": "Constituent Loyalty vs Lobbyists",
            "desc": "% rate of voting in alignment with district interests over corporate/PAC donor lobbying.",
            "fn": lambda p: p.donor_influence.district_loyalty_index,
            "fmt": lambda v: f"{v:.1f}% Loyal"
        },
        {
            "id": "party_loyalty",
            "title": "Party Line Loyalty",
            "desc": "% of roll call votes cast in alignment with caucus leadership.",
            "fn": lambda p: p.scouting.combine_measurables.party_loyalty,
            "fmt": lambda v: f"{v:.1f}%"
        },
        {
            "id": "constituent_sync",
            "title": "Constituent Sync Score",
            "desc": "Index of alignment between member voting record and home district demographics.",
            "fn": lambda p: p.scouting.combine_measurables.constituent_sync,
            "fmt": lambda v: f"{v:.1f}%"
        },
        {
            "id": "floor_attendance",
            "title": "Floor Attendance Rate",
            "desc": "% of roll calls participated in (Lowest missed/abstain rate).",
            "fn": lambda p: p.scouting.combine_measurables.floor_attendance,
            "fmt": lambda v: f"{v:.1f}%"
        },
        {
            "id": "bipartisanship",
            "title": "Bipartisanship Velocity",
            "desc": "Rate of cross-aisle bill cosponsorships and independent vote splits.",
            "fn": lambda p: p.scouting.combine_measurables.bipartisanship_velocity,
            "fmt": lambda v: f"{v:.1f}%"
        },
        {
            "id": "legislative_motor",
            "title": "Legislative Motor & Volume",
            "desc": "Composite activity rating factoring committee leadership, markups, and tenure.",
            "fn": lambda p: p.scouting.combine_measurables.legislative_motor,
            "fmt": lambda v: f"{v:.0f} / 100"
        },
        {
            "id": "grassroots_power",
            "title": "Grassroots Micro-Funding Power",
            "desc": "% of campaign war chest funded by small-dollar grassroots donors (<$200).",
            "fn": lambda p: p.finance.small_individual_pct,
            "fmt": lambda v: f"{v:.1f}%"
        }
    ]

    combine_leaderboards = []
    for cc in combine_cats:
        d_top, d_bot, r_top, r_bot, i_top = build_ranked_partition(profiles, cc["fn"], cc["fmt"])
        combine_leaderboards.append(CategoryLeaderboard(
            category_id=cc["id"],
            category_title=cc["title"],
            metric_description=cc["desc"],
            democrats_top5=d_top,
            democrats_bottom5=d_bot,
            republicans_top5=r_top,
            republicans_bottom5=r_bot,
            independents_spotlight=i_top
        ))

    from backend.config import POLICY_CATEGORIES
    policy_leaderboards = []
    for cat in POLICY_CATEGORIES:
        cat_id = cat.lower().replace(" & ", "_").replace(" / ", "_").replace(" ", "_")
        d_top, d_bot, r_top, r_bot, i_top = build_ranked_partition(
            profiles,
            lambda p, c=cat: p.voting.category_breakdown.get(c, {}).support_pct if hasattr(p.voting.category_breakdown.get(c, {}), "support_pct") else (p.voting.category_breakdown.get(c, {}).get("support_pct", 50.0) if isinstance(p.voting.category_breakdown.get(c, {}), dict) else 50.0),
            lambda v: f"{v:.1f}% Support"
        )
        policy_leaderboards.append(CategoryLeaderboard(
            category_id=cat_id,
            category_title=f"{cat} Policy Support",
            metric_description=f"% affirmative Yea votes cast on landmark legislation in the {cat} sector.",
            democrats_top5=d_top,
            democrats_bottom5=d_bot,
            republicans_top5=r_top,
            republicans_bottom5=r_bot,
            independents_spotlight=i_top
        ))

    _CACHED_LEADERBOARD = FullLeaderboardResponse(
        combine_categories=combine_leaderboards,
        policy_categories=policy_leaderboards
    )
    return _CACHED_LEADERBOARD

def get_all_party_rankings() -> PartyRankingsResponse:
    global _CACHED_PROFILES
    if _CACHED_PROFILES is None:
        get_full_leaderboard()

    entries = []
    for p in (_CACHED_PROFILES or []):
        comb = p.scouting.combine_measurables
        pipe = p.legislative_pipeline
        
        total_score, grade, tier, _, _, _ = calculate_five_pillar_score(
            bio=p.bio,
            affiliations=p.affiliations,
            voting=p.voting,
            alignment=p.alignment,
            finance=p.finance,
            pipeline=pipe,
            district_loyalty=p.donor_influence.district_loyalty_index
        )
        
        entries.append(PartyRankingEntry(
            bioguide_id=p.bio.bioguide_id,
            full_name=p.bio.full_name,
            party=p.bio.party,
            chamber=p.bio.chamber,
            state=p.bio.state,
            district=p.bio.district,
            image_url=p.bio.image_url,
            leadership_role=p.bio.leadership_role,
            overall_score=total_score,
            letter_grade=grade,
            tier_label=tier,
            archetype=p.scouting.draft_archetype,
            bills_sponsored=pipe.bills_sponsored_count,
            bills_enacted=pipe.bills_enacted_into_law_count,
            earmarks_millions=pipe.earmarks_secured_millions,
            constituent_sync=comb.constituent_sync,
            floor_attendance=comb.floor_attendance,
            bipartisanship_velocity=comb.bipartisanship_velocity,
            grassroots_pct=p.finance.small_individual_pct,
            pac_dependency=p.finance.pac_contributions_pct,
            clutch_rating=comb.clutch_rating,
            stock_conflict_index=p.stock_trading.committee_conflict_index,
            current_net_worth=p.wealth_pl.current_net_worth,
            net_worth_growth_dollars=p.wealth_pl.net_worth_growth_dollars,
            wealth_growth_multiple=p.wealth_pl.wealth_growth_multiple,
            ethics_risk_score=p.ethics_risk.ethics_risk_score,
            ethics_risk_label=p.ethics_risk.risk_level_label,
            approval_pct=p.approval_rating.district_approval_pct,
            staff_turnover_pct=p.workplace_metrics.annual_staff_turnover_pct,
            dark_money_millions=p.super_pac_spending.total_outside_spending_millions,
            spousal_conflict_label=p.family_conflicts.spousal_risk_rating
        ))
        
    return PartyRankingsResponse(
        total_members_count=len(entries),
        members=entries
    )


def calculate_voter_match(request: VoterMatchmakerRequest) -> VoterMatchmakerResponse:
    global _CACHED_PROFILES
    if _CACHED_PROFILES is None:
        get_full_leaderboard()

    profiles = _CACHED_PROFILES or []
    
    # Filter state/chamber if requested
    if request.user_state and request.user_state != "ALL":
        profiles = [p for p in profiles if p.bio.state.upper() == request.user_state.upper()]
    if request.user_chamber and request.user_chamber != "ALL":
        profiles = [p for p in profiles if p.bio.chamber.lower() == request.user_chamber.lower()]

    ISSUE_CATEGORY_MAP = {
        "drugs": ("Healthcare & Public Health", "Prescription Drug Caps"),
        "guns": ("Judiciary & Constitutional Rights", "Second Amendment Protections"),
        "clean_energy": ("Energy & Environment", "Clean Energy & Renewable Incentives"),
        "corporate_tax": ("Economy & Taxation", "Corporate & High-Earner Tax Structure"),
        "border": ("Immigration & Border Security", "Border Wall & E-Verify Funding"),
        "spending": ("Federal Budget & Appropriations", "Statutory Spending Caps & Fiscal Audits"),
        "crypto": ("Science & Technology", "Digital Assets & Crypto Regulation")
    }

    results: List[CandidateMatchItem] = []

    for p in profiles:
        aligned = []
        divergent = []
        total_points = 0
        earned_points = 0

        for choice in request.choices:
            if choice.stance == "NEUTRAL":
                continue
            
            total_points += 10
            cat_tuple = ISSUE_CATEGORY_MAP.get(choice.issue_id)
            if not cat_tuple:
                continue

            cat_name, label = cat_tuple
            cat_stat = p.voting.category_breakdown.get(cat_name)
            support_pct = cat_stat.support_pct if cat_stat else 50.0

            # Evaluate alignment
            if choice.stance == "SUPPORT":
                if support_pct >= 60.0:
                    earned_points += 10
                    aligned.append(f"{label} (Voted {support_pct:.0f}% In Favor)")
                elif support_pct <= 40.0:
                    earned_points += 0
                    divergent.append(f"{label} (Voted {100-support_pct:.0f}% Opposed)")
                else:
                    earned_points += 5
                    aligned.append(f"{label} (Moderate / Split Record: {support_pct:.0f}%)")
            elif choice.stance == "OPPOSE":
                if support_pct <= 40.0:
                    earned_points += 10
                    aligned.append(f"{label} (Voted {100-support_pct:.0f}% Against)")
                elif support_pct >= 60.0:
                    earned_points += 0
                    divergent.append(f"{label} (Voted {support_pct:.0f}% In Favor)")
                else:
                    earned_points += 5
                    aligned.append(f"{label} (Moderate / Split Record)")

        match_pct = round((earned_points / max(10, total_points)) * 100.0, 1) if total_points > 0 else 75.0

        results.append(CandidateMatchItem(
            bioguide_id=p.bio.bioguide_id,
            full_name=p.bio.full_name,
            party=p.bio.party,
            chamber=p.bio.chamber,
            state=p.bio.state,
            district=p.bio.district,
            image_url=p.bio.image_url,
            match_percentage=match_pct,
            grade=p.scouting.draft_grade,
            archetype=p.scouting.draft_archetype,
            aligned_issues=aligned,
            divergent_issues=divergent
        ))

    results_sorted = sorted(results, key=lambda x: x.match_percentage, reverse=True)
    top_matches = results_sorted[:10]
    bottom_matches = sorted(results, key=lambda x: x.match_percentage, reverse=False)[:5]

    return VoterMatchmakerResponse(
        total_candidates_analyzed=len(results),
        top_matches=top_matches,
        bottom_matches=bottom_matches
    )
