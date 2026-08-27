"""
Constituent Alignment, District Gap, and Donor Influence Analysis Engine
Calculates synchronization index and the "Lobbyist vs. Constituent Tug-of-War" metric.
"""
from typing import Dict, List, Tuple
from backend.models import (
    ConstituentDemographics, 
    VotingRecordSummary, 
    ConstituentAlignment,
    CampaignFinanceSummary,
    SectorTugOfWar,
    DonorVsConstituentAnalysis
)

def calculate_constituent_alignment(
    demographics: ConstituentDemographics, 
    voting: VotingRecordSummary
) -> ConstituentAlignment:
    """
    Calculate policy-by-policy alignment scores and identify top synergy / friction zones.
    """
    category_alignments: Dict[str, float] = {}
    
    # 1. Defense & National Security alignment
    vet_factor = min(1.0, demographics.veteran_pct / 8.0)
    has_defense_ind = any("defense" in k.lower() or "military" in k.lower() or "aerospace" in k.lower() 
                          for k in demographics.top_employment_sectors.keys())
    defense_priority = (vet_factor * 0.5) + (0.5 if has_defense_ind else 0.2)
    def_vote = voting.category_breakdown.get("Defense & National Security")
    def_support = (def_vote.support_pct / 100.0) if def_vote else 0.7
    category_alignments["Defense & National Security"] = round(100.0 - abs(defense_priority - def_support) * 60, 1)

    # 2. Agriculture & Rural Development alignment
    rural_factor = demographics.rural_pct / 100.0
    has_ag_ind = any("agri" in k.lower() or "farm" in k.lower() for k in demographics.top_employment_sectors.keys())
    ag_priority = (rural_factor * 0.6) + (0.4 if has_ag_ind else 0.1)
    ag_vote = voting.category_breakdown.get("Agriculture & Rural Development")
    ag_support = (ag_vote.support_pct / 100.0) if ag_vote else 0.6
    category_alignments["Agriculture & Rural Development"] = round(100.0 - abs(ag_priority - ag_support) * 50, 1)

    # 3. Economy & Taxation (and Social Safety Net / SNAP)
    snap_factor = min(1.5, demographics.snap_assistance_pct / 12.0)
    poverty_ratio = min(1.0, demographics.poverty_rate_pct / 18.0)
    econ_vote = voting.category_breakdown.get("Economy & Taxation")
    econ_support = (econ_vote.support_pct / 100.0) if econ_vote else 0.65
    if snap_factor > 1.2:
        # High assistance district: higher demand for household relief and tax credits
        category_alignments["Economy & Taxation"] = round(85.0 + (12.0 if econ_support > 0.6 else -12.0), 1)
    else:
        category_alignments["Economy & Taxation"] = round(85.0 + (10.0 if econ_support > 0.5 else -10.0), 1)

    # 4. Healthcare & Medicare (and Medicaid Enrollment / Uninsured)
    health_vote = voting.category_breakdown.get("Healthcare & Medicare")
    health_support = (health_vote.support_pct / 100.0) if health_vote else 0.6
    medicaid_factor = min(1.5, demographics.medicaid_enrolled_pct / 20.0)
    uninsured_factor = min(1.5, demographics.uninsured_rate_pct / 8.0)
    health_need = 0.4 + (medicaid_factor * 0.3) + (uninsured_factor * 0.3)
    category_alignments["Healthcare & Medicare"] = round(100.0 - abs(health_need - health_support) * 50, 1)

    # 5. Immigration & Border Security (Factoring Foreign-Born / Immigrant Ratio)
    imm_vote = voting.category_breakdown.get("Immigration & Border Security")
    imm_support = (imm_vote.support_pct / 100.0) if imm_vote else 0.5
    foreign_born_ratio = demographics.foreign_born_pct / 100.0
    if foreign_born_ratio > 0.25:
        # High immigrant population: pro-reform / pathway to legal status alignment
        imm_align = 92.0 if imm_support > 0.6 else 65.0
    elif foreign_born_ratio < 0.06:
        # Low foreign-born / rural border focus: enforcement alignment
        imm_align = 90.0 if imm_support > 0.5 else 72.0
    else:
        imm_align = 82.0
    category_alignments["Immigration & Border Security"] = imm_align

    # 6. Technology & AI / Privacy
    has_tech_ind = any("tech" in k.lower() or "software" in k.lower() or "telecom" in k.lower() 
                       for k in demographics.top_employment_sectors.keys())
    tech_factor = (demographics.college_educated_pct / 100.0 * 0.5) + (0.5 if has_tech_ind else 0.2)
    tech_vote = voting.category_breakdown.get("Technology & AI / Privacy")
    tech_support = (tech_vote.support_pct / 100.0) if tech_vote else 0.75
    category_alignments["Technology & AI / Privacy"] = round(100.0 - abs(tech_factor - tech_support) * 45, 1)

    # 7. Energy & Environment
    has_energy_ind = any("energy" in k.lower() or "oil" in k.lower() or "gas" in k.lower() or "mining" in k.lower() 
                         for k in demographics.top_employment_sectors.keys())
    energy_vote = voting.category_breakdown.get("Energy & Environment")
    energy_support = (energy_vote.support_pct / 100.0) if energy_vote else 0.5
    if has_energy_ind:
        energy_align = 90.0 if energy_support > 0.6 else 62.0
    else:
        energy_align = 84.0 if energy_support > 0.4 else 75.0
    category_alignments["Energy & Environment"] = energy_align

    # 8. Infrastructure & Transportation
    category_alignments["Infrastructure & Transportation"] = round(min(98.0, 75.0 + (demographics.urban_pct * 0.2)), 1)
    
    # 9. Education & Labor
    category_alignments["Education & Labor"] = round(80.0 + (demographics.college_educated_pct * 0.3), 1)

    for k in category_alignments:
        category_alignments[k] = max(45.0, min(99.0, category_alignments[k]))

    overall_sync = round(sum(category_alignments.values()) / len(category_alignments), 1)
    sorted_cats = sorted(category_alignments.items(), key=lambda x: x[1], reverse=True)
    top_alignment = [f"{c[0]} ({c[1]:.0f}% Sync)" for c in sorted_cats[:3]]
    top_divergence = [f"{c[0]} ({c[1]:.0f}% Sync)" for c in sorted_cats[-2:]]

    if overall_sync >= 85.0:
        takeaway = f"Locked-in district synchronizer. Voting profile mirrors the key economic drivers of {demographics.district_code}."
    elif overall_sync >= 72.0:
        takeaway = f"Solid district alignment with selective national party prioritization in {sorted_cats[-1][0]}."
    else:
        takeaway = f"High divergence with local constituent economic markers. National party ideological voting creates tension in {sorted_cats[-1][0]}."

    return ConstituentAlignment(
        overall_sync_score=overall_sync,
        category_alignments=category_alignments,
        top_alignment_areas=top_alignment,
        top_divergence_areas=top_divergence,
        scouting_takeaway=takeaway
    )

def calculate_donor_vs_constituent_analysis(
    demographics: ConstituentDemographics,
    voting: VotingRecordSummary,
    finance: CampaignFinanceSummary
) -> DonorVsConstituentAnalysis:
    """
    Evaluates whether a lawmaker votes in alignment with corporate/lobbyist donors
    or home district constituents when their interests pull in opposing directions.
    """
    conflict_sectors: List[SectorTugOfWar] = []
    donor_sectors_map = {s.sector_name.lower(): s for s in finance.top_donor_sectors}
    
    # Check if purely grassroots funded
    is_grassroots = finance.pac_contributions_pct < 8.0 and finance.small_individual_pct > 65.0

    # 1. Sector: Oil & Gas / Energy
    energy_donor = next((s for k, s in donor_sectors_map.items() if "energy" in k or "oil" in k), None)
    energy_donor_amt = energy_donor.amount_usd if energy_donor else 0.0
    has_energy_ind = any("energy" in k.lower() or "oil" in k.lower() or "coal" in k.lower() 
                         for k in demographics.top_employment_sectors.keys())
    energy_vote = voting.category_breakdown.get("Energy & Environment")
    energy_supp = energy_vote.support_pct if energy_vote else 50.0

    if energy_donor_amt > 1000000.0:
        donor_stake = f"High (${energy_donor_amt/1000000:.1f}M+ PAC)"
        if has_energy_ind:
            dist_prio = "High Pro-Energy Demand (Local Economy)"
            verdict = "Natural Alignment (Donors & District Agree)"
            conf = False
            dtl = f"Local economy is energy-dependent ({list(demographics.top_employment_sectors.keys())[0]}), coinciding with PAC funding."
        else:
            dist_prio = "Adverse / Climate Vulnerable"
            conf = True
            if energy_supp > 65.0:
                verdict = "Sided with Donors (High Conflict)"
                dtl = f"Voted {energy_supp:.0f}% for fossil fuel subsidies despite district non-energy profile."
            else:
                verdict = "Sided with District (Resisted Donors)"
                dtl = f"Voted with district priorities despite ${energy_donor_amt/1000000:.1f}M from energy PACs."
    else:
        donor_stake = "Minimal / No Oil PACs"
        dist_prio = "Clean Energy / Climate Priority" if not has_energy_ind else "Pro-Energy"
        verdict = "Sided with District" if not has_energy_ind else "Natural Alignment"
        conf = False
        dtl = "Negligible energy PAC funding; voting reflects constituent stance."

    conflict_sectors.append(SectorTugOfWar(
        sector_name="Energy & Oil / Gas",
        donor_funding_amount=energy_donor_amt,
        donor_stake_level=donor_stake,
        district_priority_level=dist_prio,
        member_voting_record=f"{energy_supp:.0f}% Pro-Industry Support",
        alignment_verdict=verdict,
        conflict_detected=conf,
        details=dtl
    ))

    # 2. Sector: Pharmaceuticals & Healthcare
    pharma_donor = next((s for k, s in donor_sectors_map.items() if "health" in k or "pharma" in k), None)
    pharma_donor_amt = pharma_donor.amount_usd if pharma_donor else 0.0
    poverty_high = demographics.poverty_rate_pct > 13.0
    health_vote = voting.category_breakdown.get("Healthcare & Medicare")
    health_supp = health_vote.support_pct if health_vote else 60.0

    if pharma_donor_amt > 1200000.0:
        donor_stake = f"High (${pharma_donor_amt/1000000:.1f}M+ PAC)"
        if poverty_high:
            dist_prio = "Urgent Need for Drug Price Caps & Medicaid"
            conf = True
            if health_supp < 50.0:
                verdict = "Sided with Donors (High Conflict)"
                dtl = "Voted against prescription price caps coinciding with major pharmaceutical contributions."
            else:
                verdict = "Sided with District (Resisted Donors)"
                dtl = f"Backed healthcare expansion and price caps despite ${pharma_donor_amt/1000000:.1f}M in industry donations."
        else:
            dist_prio = "Moderate Need"
            conf = False
            verdict = "Balanced / Moderate"
            dtl = "District healthcare needs balanced with bio-pharma research funding."
    else:
        donor_stake = "Low / Grassroots Funded"
        dist_prio = "High Public Healthcare Need" if poverty_high else "Moderate"
        conf = False
        verdict = "Sided with District"
        dtl = "Minimal pharmaceutical PAC leverage; voting aligns with district cost-of-living priorities."

    conflict_sectors.append(SectorTugOfWar(
        sector_name="Big Pharma & Healthcare",
        donor_funding_amount=pharma_donor_amt,
        donor_stake_level=donor_stake,
        district_priority_level=dist_prio,
        member_voting_record=f"{health_supp:.0f}% Healthcare Support",
        alignment_verdict=verdict,
        conflict_detected=conf,
        details=dtl
    ))

    # 3. Sector: Defense & Aerospace
    def_donor = next((s for k, s in donor_sectors_map.items() if "defense" in k or "military" in k), None)
    def_donor_amt = def_donor.amount_usd if def_donor else 0.0
    has_def_base = demographics.veteran_pct > 7.0 or any("defense" in k.lower() for k in demographics.top_employment_sectors)
    def_vote = voting.category_breakdown.get("Defense & National Security")
    def_supp = def_vote.support_pct if def_vote else 70.0

    if def_donor_amt > 1500000.0:
        donor_stake = f"High (${def_donor_amt/1000000:.1f}M+ PAC)"
        if has_def_base:
            dist_prio = "Pro-Defense (Major Military/Veteran District)"
            conf = False
            verdict = "Natural Alignment (Donors & District Agree)"
            dtl = f"High veteran presence ({demographics.veteran_pct:.1f}%) directly aligns with defense appropriations."
        else:
            dist_prio = "Domestic Spending Priority"
            conf = True
            verdict = "Sided with Donors (High Conflict)" if def_supp > 85.0 else "Balanced"
            dtl = f"Backed major foreign/military packages with ${def_donor_amt/1000000:.1f}M from defense PACs."
    else:
        donor_stake = "Minimal Defense PACs"
        dist_prio = "Pro-Defense" if has_def_base else "Domestic Focused"
        conf = False
        verdict = "Sided with District"
        dtl = "Voting guided by constituent demographics rather than military contractor funding."

    conflict_sectors.append(SectorTugOfWar(
        sector_name="Defense & Aerospace",
        donor_funding_amount=def_donor_amt,
        donor_stake_level=donor_stake,
        district_priority_level=dist_prio,
        member_voting_record=f"{def_supp:.0f}% Defense Support",
        alignment_verdict=verdict,
        conflict_detected=conf,
        details=dtl
    ))

    # 4. Sector: Wall Street & Banking / Finance
    fin_donor = next((s for k, s in donor_sectors_map.items() if "finance" in k or "securities" in k or "bank" in k), None)
    fin_donor_amt = fin_donor.amount_usd if fin_donor else 0.0
    is_fin_hub = any("finance" in k.lower() or "banking" in k.lower() for k in demographics.top_employment_sectors)
    econ_vote = voting.category_breakdown.get("Economy & Taxation")
    econ_supp = econ_vote.support_pct if econ_vote else 65.0

    if fin_donor_amt > 2000000.0:
        donor_stake = f"High (${fin_donor_amt/1000000:.1f}M+ PAC)"
        if is_fin_hub:
            dist_prio = "Financial District Employment"
            conf = False
            verdict = "Natural Alignment"
            dtl = "District is a regional financial center matching donor contributions."
        else:
            dist_prio = "Consumer Protection & Fair Tax"
            conf = True
            verdict = "Sided with Donors" if econ_supp > 80.0 else "Balanced"
            dtl = f"Financial PACs contributed ${fin_donor_amt/1000000:.1f}M; voting tracks commercial deregulation."
    else:
        donor_stake = "Low / Grassroots"
        dist_prio = "Working Class Tax Relief"
        conf = False
        verdict = "Sided with District"
        dtl = "Minimal banking PAC influence; voting prioritizes local household economic relief."

    conflict_sectors.append(SectorTugOfWar(
        sector_name="Wall Street & Banking",
        donor_funding_amount=fin_donor_amt,
        donor_stake_level=donor_stake,
        district_priority_level=dist_prio,
        member_voting_record=f"{econ_supp:.0f}% Economic Support",
        alignment_verdict=verdict,
        conflict_detected=conf,
        details=dtl
    ))

    # Calculate overall scores
    conflicts_sided_with_donors = sum(1 for c in conflict_sectors if "with Donors" in c.alignment_verdict)
    conflicts_sided_with_dist = sum(1 for c in conflict_sectors if "with District" in c.alignment_verdict or "Natural" in c.alignment_verdict)
    
    if is_grassroots:
        district_loyalty = 96.5
        donor_sway = 3.5
        archetype = "Grassroots Sovereign (Uncaptured)"
        narrative = "Operates with near-zero corporate PAC dependency. Voting tape strictly follows constituent and party base mandates with zero detected lobbyist distortion."
    elif conflicts_sided_with_donors >= 2:
        district_loyalty = 58.0
        donor_sway = 42.0
        archetype = "Donor-Captive Alignee"
        narrative = "Elevated lobbyist pull detected. On contested energy, financial, and healthcare roll calls, voting record consistently sides with major corporate PAC contributors over home district economic indicators."
    elif any("Natural" in c.alignment_verdict for c in conflict_sectors):
        district_loyalty = 88.0
        donor_sway = 18.0
        archetype = "Organic District/Donor Alignment"
        narrative = "Home district economic profile naturally mirrors top donor sectors (e.g. industrial energy, maritime, or defense base), creating low friction between PAC contributions and constituent priorities."
    else:
        district_loyalty = 82.0
        donor_sway = 18.0
        archetype = "District-First Sovereign"
        narrative = "Demonstrates solid constituent fidelity, routinely voting in favor of district demographics even when opposing major PAC lobbying positions."

    return DonorVsConstituentAnalysis(
        district_loyalty_index=district_loyalty,
        donor_sway_index=donor_sway,
        influence_archetype=archetype,
        conflict_sectors=conflict_sectors,
        narrative_verdict=narrative
    )
