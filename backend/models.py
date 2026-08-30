"""
Data models and schemas for Congressional Civic Analytics & Lawmaker Dossiers
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class MemberBio(BaseModel):
    bioguide_id: str
    first_name: str
    last_name: str
    full_name: str
    chamber: str  # "House" or "Senate"
    party: str    # "Democrat", "Republican", "Independent"
    state: str    # "CA", "TX", "NY", etc.
    district: Optional[int] = None # None for Senators
    leadership_role: Optional[str] = None
    first_elected: int # Year first elected
    terms_served: int
    birth_year: Optional[int] = None
    age: Optional[int] = None
    estimated_net_worth: str = "$1M - $5M"
    gender: Optional[str] = None
    image_url: Optional[str] = None
    official_website: Optional[str] = None
    twitter_handle: Optional[str] = None

class AffiliationData(BaseModel):
    committees: List[str] = Field(default_factory=list)
    subcommittees: List[str] = Field(default_factory=list)
    caucuses: List[str] = Field(default_factory=list)
    leadership_pacs: List[str] = Field(default_factory=list)
    prior_organizations: List[str] = Field(default_factory=list)

class CategoryVoteStat(BaseModel):
    category: str
    total_votes: int = 0
    votes_yes: int = 0
    votes_no: int = 0
    votes_abstained: int = 0
    support_pct: float = 0.0 # % voting Yes on this topic

class NotableVote(BaseModel):
    roll_call_id: str
    bill_number: Optional[str] = None
    bill_title: str
    category: str
    member_vote: str # "YES", "NO", "ABSTAIN", "NOT VOTING"
    party_majority_vote: str # "YES" or "NO"
    result: str # "PASSED", "FAILED"
    date: str
    is_party_split: bool = False # Voted against party line
    significance_note: Optional[str] = None

class VotingRecordSummary(BaseModel):
    timeframe: str = "career" # "career", "2026", "2025", "2024", "118th", "117th", "2010s", "2000s", "1990s"
    era_label: str = "Career Total (All-Time)"
    total_votes: int = 0
    total_yes: int = 0
    total_no: int = 0
    total_abstained: int = 0
    abstain_pct: float = 0.0 # Missed / Abstain %
    attendance_pct: float = 100.0
    party_unity_pct: float = 90.0
    bipartisanship_pct: float = 10.0
    dw_nominate_score: float = 0.0 # Ideology dimension 1 (-1.0 liberal to +1.0 conservative)
    category_breakdown: Dict[str, CategoryVoteStat] = Field(default_factory=dict)
    recent_votes: List[NotableVote] = Field(default_factory=list)

# -------------------------------------------------------------
# DETAILED BILL & POLICY CATEGORY DRILL-DOWN SCHEMAS
# -------------------------------------------------------------
class BillDetailRecord(BaseModel):
    bill_number: str # e.g. "H.R. 4366" or "S. 2226"
    bill_title: str
    category: str
    date: str
    result: str # "PASSED (219-210)", "FAILED", "ENACTED"
    member_vote: str # "YES", "NO", "ABSTAIN"
    party_majority_vote: str # "YES" or "NO"
    is_party_split: bool = False
    plain_english_summary: str # 2-3 sentence clear summary of what was inside the bill
    key_provisions: List[str] = Field(default_factory=list) # Bullet points of major clauses
    district_and_sector_impact: str
    significance_level: str = "LANDMARK" # "LANDMARK", "HIGH_IMPACT", "ROUTINE"

class PolicyCategoryDeepDive(BaseModel):
    category_name: str
    member_bioguide_id: str
    member_name: str
    timeframe: str
    total_bills_analyzed: int
    member_support_pct: float
    votes_yes: int
    votes_no: int
    votes_abstained: int
    category_overview: str
    bills: List[BillDetailRecord] = Field(default_factory=list)

# -------------------------------------------------------------
# DISTRICT DEMOGRAPHIC & POLICY CORRELATION SCHEMAS
# -------------------------------------------------------------
class DistrictDemographicMetricDetail(BaseModel):
    metric_name: str # e.g. "SNAP / Food Assistance"
    district_value: str # e.g. "22.4% Households"
    state_avg: str # e.g. "13.2%"
    national_avg: str # e.g. "12.1%"
    variance_status: str # "SIGNIFICANTLY_ABOVE_NATIONAL", "AVERAGE", "BELOW_NATIONAL"
    lawmaker_voting_stance: str # "ACTIVE_PROTECTION", "FISCAL_REDUCTION", "MIXED"
    constituent_impact_analysis: str # How the member's votes directly serve or conflict with this metric
    correlated_roll_calls: List[str] = Field(default_factory=list)

class DistrictDeepDiveDossier(BaseModel):
    district_code: str
    state_name: str
    representative_name: str
    partisan_lean_pvi: str
    population: int
    median_household_income: int
    poverty_rate_pct: float
    snap_assistance_pct: float
    foreign_born_pct: float
    medicaid_enrolled_pct: float
    uninsured_rate_pct: float
    college_educated_pct: float
    urban_pct: float
    rural_pct: float
    veteran_pct: float
    top_employment_sectors: Dict[str, float] = Field(default_factory=dict)
    metric_correlations: List[DistrictDemographicMetricDetail] = Field(default_factory=list)
    overall_district_alignment_verdict: str

class ConstituentDemographics(BaseModel):
    district_code: str # e.g. "CA-12" or "TX-Sen"
    state_name: str
    population: int = 750000
    median_household_income: int = 70000
    poverty_rate_pct: float = 12.0
    snap_assistance_pct: float = 12.5 # % of households receiving SNAP / food stamps
    medicaid_enrolled_pct: float = 19.5 # % of population enrolled in Medicaid / CHIP
    foreign_born_pct: float = 13.9 # % of immigrant / foreign-born residents
    uninsured_rate_pct: float = 8.5 # % uninsured
    disability_pct: float = 13.2 # % with disability
    urban_pct: float = 80.0
    rural_pct: float = 20.0
    college_educated_pct: float = 35.0
    veteran_pct: float = 7.5
    top_employment_sectors: Dict[str, float] = Field(default_factory=dict) # Sector: % of workforce
    partisan_lean_pvi: str = "EVEN" # e.g. "R+8", "D+14", "EVEN"

class ConstituentAlignment(BaseModel):
    overall_sync_score: float = 75.0 # 0 to 100
    category_alignments: Dict[str, float] = Field(default_factory=dict) # Category: 0-100 sync score
    top_alignment_areas: List[str] = Field(default_factory=list)
    top_divergence_areas: List[str] = Field(default_factory=list)
    scouting_takeaway: str = ""

class DonorSector(BaseModel):
    sector_name: str
    amount_usd: float
    pct_of_total: float

class CampaignFinanceSummary(BaseModel):
    total_raised: float = 0.0
    total_spent: float = 0.0
    pac_contributions_pct: float = 0.0
    small_individual_pct: float = 0.0
    large_individual_pct: float = 0.0
    top_donor_sectors: List[DonorSector] = Field(default_factory=list)
    top_donors: List[str] = Field(default_factory=list)

# Donor vs Constituent Tug-of-War Schemas
class SectorTugOfWar(BaseModel):
    sector_name: str
    donor_funding_amount: float
    donor_stake_level: str # "High ($1M+)", "Moderate", "Minimal"
    district_priority_level: str # "High Need", "Neutral", "Conflicted / Adverse"
    member_voting_record: str # e.g. "88% Pro-Industry", "25% Pro-Industry"
    alignment_verdict: str # "Sided with Donors", "Sided with District", "Natural Alignment", "Grassroots Independent"
    conflict_detected: bool
    details: str

class DonorVsConstituentAnalysis(BaseModel):
    district_loyalty_index: float # 0 - 100% (High = aligns with constituents)
    donor_sway_index: float # 0 - 100% (High = influenced by PAC contributions)
    influence_archetype: str # "District-First Sovereign", "Donor-Captive Alignee", "Organic Local Alignment", "Grassroots Uncaptured"
    conflict_sectors: List[SectorTugOfWar] = Field(default_factory=list)
    narrative_verdict: str

# -------------------------------------------------------------
# CIVIC PERFORMANCE INDICATORS & EFFECTIVENESS RATINGS
# -------------------------------------------------------------
class CombineMeasurables(BaseModel):
    party_loyalty: float # 0 - 100
    bipartisanship_velocity: float # 0 - 100
    floor_attendance: float # 0 - 100
    abstain_rate: float # 0 - 100 (Missed / Abstain %)
    pac_dependency: float # 0 - 100
    constituent_sync: float # 0 - 100
    legislative_motor: float # 0 - 100 (bills sponsored / cosponsored volume)
    district_loyalty: float = 80.0 # vs Donors (0 - 100)
    clutch_rating: float = 88.0 # High-Pressure Floor Resilience Index (0 - 100)

class ClutchVotingStats(BaseModel):
    clutch_rating: float # 0 - 100
    nailbiter_votes_analyzed: int
    clutch_party_loyalty_pct: float
    maverick_defection_pct: float
    clutch_archetype: str # "Party Anchor / High Cohesion", "Floor Maverick / Tactical Defector", "District-First Stabilizer"
    clutch_verdict: str

class FlaggedStockTrade(BaseModel):
    ticker: str
    company_name: str
    transaction_type: str # "PURCHASE" or "SALE"
    amount_range: str
    transaction_date: str
    related_committee: str
    conflict_level: str # "HIGH", "MODERATE", "LOW"
    description: str

class StockTradingProfile(BaseModel):
    total_trades_disclosed: int
    estimated_trade_volume: str
    top_traded_sectors: List[str] = Field(default_factory=list)
    committee_conflict_index: float # 0 - 100 (High = trades heavily in sectors regulated by committee)
    conflict_status: str # "Low Conflict", "Moderate Sector Overlap", "High Committee Jurisdiction Overlap"
    conflict_summary: str
    flagged_trades: List[FlaggedStockTrade] = Field(default_factory=list)

class CareerProgressionPoint(BaseModel):
    era: str
    year: int
    term: int
    net_worth_millions: float
    bipartisanship_pct: float
    party_unity_pct: float
    dw_nominate: float

class CareerProgression(BaseModel):
    timeline: List[CareerProgressionPoint] = Field(default_factory=list)
    trajectory_summary: str

# -------------------------------------------------------------
# LEGISLATIVE PIPELINE & EARMARKS OUTPUT SCHEMAS
# -------------------------------------------------------------
class LegislativePipelineStats(BaseModel):
    bills_sponsored_count: int = 14
    bills_cosponsored_count: int = 168
    bills_passed_committee_count: int = 6
    bills_enacted_into_law_count: int = 3
    earmarks_secured_millions: float = 24.5
    earmarks_summary: str = "Secured community project funding for clean water treatment facilities, community healthcare clinics, and STEM education laboratories."
    oversight_hearing_attendance_pct: float = 94.0

class ScoutingCard(BaseModel):
    draft_grade: str # Legislative Effectiveness Rating: "A+", "A", "A-", "B+", "B", "C+", etc.
    draft_archetype: str # Governance Archetype: e.g. "Senior Caucus Leader", "Floor Maverick", "District Pragmatist"
    archetype_description: str
    pro_comparison_name: str # Historical & Policy Alignment Comp
    pro_comparison_desc: str
    combine_measurables: CombineMeasurables
    strengths: List[str] = Field(default_factory=list)
    weaknesses_tendencies: List[str] = Field(default_factory=list)
    film_room_verdict: str

# -------------------------------------------------------------
# CONGRESSIONAL WEALTH P&L AND ETHICS / CONFLICT SCHEMAS
# -------------------------------------------------------------
class CongressionalWealthPL(BaseModel):
    first_year_in_office: int = 2018
    starting_net_worth: str = "$50k"
    starting_net_worth_millions: float = 0.05
    current_net_worth: str = "$125k"
    current_net_worth_millions: float = 0.125
    total_salary_earned_millions: float = 1.39 # Cumulative congressional salary
    net_worth_growth_dollars: str = "+$75k"
    net_worth_growth_pct: float = 150.0
    annualized_growth_rate_pct: float = 12.5
    wealth_trajectory_assessment: str = "Salary-consistent wealth growth with minimal outside asset appreciation."
    wealth_growth_multiple: float = 2.5 # Current NW / Starting NW

class CivicEthicsConflictIndex(BaseModel):
    ethics_risk_score: float = 5.0 # 0 (Clean / Minimum Risk) to 100 (Severe Corruption / Scandal Risk)
    risk_level_label: str = "CLEAN RECORD / LOW RISK" # "CLEAN RECORD / LOW RISK", "MODERATE SPECIAL INTEREST EXPOSURE", "ELEVATED CONFLICT OF INTEREST", "HIGH SCANDAL & ETHICS RISK"
    stock_trading_conflict_pts: float = 0.0 # 0 - 35 pts (Trading equities in committee jurisdiction / late STOCK Act filings)
    pac_capture_pts: float = 2.0 # 0 - 30 pts (Corporate PAC & lobbyist cash dependency)
    abnormal_wealth_pts: float = 3.0 # 0 - 20 pts (Wealth acceleration multiple outpacing salary)
    ethics_oversight_pts: float = 0.0 # 0 - 15 pts (Office of Congressional Ethics inquiries, censures, fines)
    conflict_drivers: List[str] = Field(default_factory=list)
    clean_indicators: List[str] = Field(default_factory=list)
    flagged_transactions_details: List[str] = Field(default_factory=list)
    oversight_inquiries: List[str] = Field(default_factory=list)
    ethics_narrative: str = "Zero individual stock trades disclosed. Fully compliant with STOCK Act standards."

class WalletVoteItem(BaseModel):
    issue_title: str
    bill_number: str
    member_vote: str # "YES", "NO", "ABSTAIN"
    wallet_impact: str
    consumer_verdict: str # "CONSUMER SAVINGS VOTE", "INCREASED COST / OPPOSITION"

class EconomicWalletScorecard(BaseModel):
    pocketbook_score_pct: float = 85.0
    pocketbook_grade: str = "A"
    pocketbook_summary: str = "Strong voting record supporting consumer cost-of-living reductions and drug pricing relief."
    key_wallet_votes: List[WalletVoteItem] = Field(default_factory=list)

class RhetoricVsRealityAudit(BaseModel):
    topic: str
    campaign_statement: str
    actual_roll_call_vote: str
    bill_cited: str
    fidelity_status: str # "CONSISTENT RECORD", "SPLIT / REVERSED STANCE", "EVOLVING RECORD"
    analysis_takeaway: str

class ChallengerMatchup(BaseModel):
    election_cycle: str = "2026 Congressional Elections"
    challenger_name: str
    challenger_party: str
    challenger_background: str
    cash_on_hand_formatted: str
    key_policy_contrast: str

class CongressionalProfile(BaseModel):
    bio: MemberBio
    affiliations: AffiliationData
    voting: VotingRecordSummary
    constituents: ConstituentDemographics
    alignment: ConstituentAlignment
    finance: CampaignFinanceSummary
    donor_influence: DonorVsConstituentAnalysis
    clutch_stats: ClutchVotingStats
    stock_trading: StockTradingProfile
    career_progression: CareerProgression
    legislative_pipeline: LegislativePipelineStats = Field(default_factory=LegislativePipelineStats)
    wealth_pl: CongressionalWealthPL = Field(default_factory=CongressionalWealthPL)
    ethics_risk: CivicEthicsConflictIndex = Field(default_factory=CivicEthicsConflictIndex)
    wallet_scorecard: EconomicWalletScorecard = Field(default_factory=EconomicWalletScorecard)
    rhetoric_audits: List[RhetoricVsRealityAudit] = Field(default_factory=list)
    challenger_preview: Optional[ChallengerMatchup] = None
    scouting: ScoutingCard
    last_updated: str

# -------------------------------------------------------------
# VOTER-CANDIDATE VALUE MATCHMAKER SCHEMAS
# -------------------------------------------------------------
class VoterIssueChoice(BaseModel):
    issue_id: str # "drugs", "guns", "clean_energy", "corporate_tax", "border", "spending", "crypto"
    stance: str # "SUPPORT", "OPPOSE", "NEUTRAL"

class VoterMatchmakerRequest(BaseModel):
    user_state: Optional[str] = "ALL"
    user_chamber: Optional[str] = "ALL"
    choices: List[VoterIssueChoice] = Field(default_factory=list)

class CandidateMatchItem(BaseModel):
    bioguide_id: str
    full_name: str
    party: str
    chamber: str
    state: str
    district: Optional[int] = None
    image_url: Optional[str] = None
    match_percentage: float
    grade: str
    archetype: str
    aligned_issues: List[str] = Field(default_factory=list)
    divergent_issues: List[str] = Field(default_factory=list)

class VoterMatchmakerResponse(BaseModel):
    total_candidates_analyzed: int
    top_matches: List[CandidateMatchItem] = Field(default_factory=list)
    bottom_matches: List[CandidateMatchItem] = Field(default_factory=list)

# Head-to-Head Policy & Voting Matchup Schemas
class HeadToHeadVoteDivergence(BaseModel):
    bill_number: Optional[str]
    bill_title: str
    category: str
    date: str
    result: str
    member1_vote: str # "YES", "NO", "ABSTAIN"
    member2_vote: str
    is_divergent: bool # Did they vote differently?
    significance_note: str

class HeadToHeadComparisonResponse(BaseModel):
    member1: CongressionalProfile
    member2: CongressionalProfile
    alignment_score_pct: float # e.g. 74.5% agreement
    divergence_count: int
    common_votes_count: int
    divergent_votes: List[HeadToHeadVoteDivergence] = Field(default_factory=list)
    radar_comparison: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    matchup_verdict: str

# Leaderboard Schemas (Top 5 and Bottom 5)
class LeaderboardEntry(BaseModel):
    bioguide_id: str
    full_name: str
    party: str
    state: str
    district: Optional[int] = None
    chamber: str
    image_url: Optional[str] = None
    score: float
    score_formatted: str
    rank: int
    draft_grade: str # Legislative Rating
    draft_archetype: str # Governance Archetype

class CategoryLeaderboard(BaseModel):
    category_id: str
    category_title: str
    metric_description: str
    democrats_top5: List[LeaderboardEntry] = Field(default_factory=list)
    democrats_bottom5: List[LeaderboardEntry] = Field(default_factory=list)
    republicans_top5: List[LeaderboardEntry] = Field(default_factory=list)
    republicans_bottom5: List[LeaderboardEntry] = Field(default_factory=list)
    independents_spotlight: List[LeaderboardEntry] = Field(default_factory=list)

class FullLeaderboardResponse(BaseModel):
    combine_categories: List[CategoryLeaderboard] = Field(default_factory=list)
    policy_categories: List[CategoryLeaderboard] = Field(default_factory=list)

# -------------------------------------------------------------
# LEGISLATIVE RATING EXPLANATION & 5-PILLAR BREAKDOWN SCHEMAS
# -------------------------------------------------------------
class RatingScorePillar(BaseModel):
    pillar_id: str # e.g. "output", "district_sync", "floor", "pac_indep", "bipartisanship"
    pillar_title: str
    points_earned: float # e.g. 18.5
    points_max: float # e.g. 25.0
    percentage: float # e.g. 74.0%
    pillar_description: str
    status_label: str # "EXEMPLARY", "STRONG", "AVERAGE", "UNDERPERFORMING"

class RatingBreakdownDossier(BaseModel):
    bioguide_id: str
    full_name: str
    chamber: str
    party: str
    state: str
    district_code: str
    overall_score: float # 0 to 100
    letter_grade: str # A+, A, A-, B+, B, B-, C+, C, C-, D, F
    tier_label: str # "TOP 5% LEGISLATOR", "EFFECTIVE LEGISLATOR", "STANDARD PARTICIPANT", "UNDERPERFORMING", "AT-RISK"
    pillars: List[RatingScorePillar] = Field(default_factory=list)
    positive_drivers: List[str] = Field(default_factory=list)
    deductions_and_growth: List[str] = Field(default_factory=list)
    grade_explanation_narrative: str

# -------------------------------------------------------------
# COMMITTEE & CAUCUS DOSSIER & ROSTER SCHEMAS
# -------------------------------------------------------------
class CommitteeMemberEntry(BaseModel):
    bioguide_id: str
    full_name: str
    party: str
    state: str
    district: Optional[int] = None
    chamber: str
    role: str # "Chair", "Ranking Member", "Vice Chair", "Member"
    image_url: Optional[str] = None
    subcommittees: List[str] = Field(default_factory=list)

class CommitteeSubcommitteeDetail(BaseModel):
    name: str
    chair_name: Optional[str] = None
    ranking_member_name: Optional[str] = None
    focus_area: str

class CommitteeDossier(BaseModel):
    committee_code: str
    committee_name: str
    chamber: str # "House", "Senate", "Joint", "Caucus"
    type: str # "Standing", "Select", "Joint", "Congressional Caucus"
    jurisdiction_overview: str
    key_agencies_supervised: List[str] = Field(default_factory=list)
    subcommittees: List[CommitteeSubcommitteeDetail] = Field(default_factory=list)
    chair: Optional[CommitteeMemberEntry] = None
    ranking_member: Optional[CommitteeMemberEntry] = None
    majority_members: List[CommitteeMemberEntry] = Field(default_factory=list)
    minority_members: List[CommitteeMemberEntry] = Field(default_factory=list)
    active_legislative_priorities: List[str] = Field(default_factory=list)
    total_members_count: int = 0

# -------------------------------------------------------------
# METHODOLOGY & OPEN CIVIC DATA CITATION SCHEMAS
# -------------------------------------------------------------
class MethodologyDataSource(BaseModel):
    name: str
    provider: str
    endpoint_or_source: str
    update_frequency: str
    description: str
    verification_url: str

class MethodologyFormulaDoc(BaseModel):
    metric_name: str
    scale: str
    inputs: List[str]
    formula_text: str
    rationale: str

class MethodologyDocumentationResponse(BaseModel):
    title: str = "Congress Civic Analytics: Open Intelligence & Methodology Specification"
    version: str = "2.4.0 (2026 Edition)"
    mission_statement: str
    data_sources: List[MethodologyDataSource] = Field(default_factory=list)
    scoring_formulas: List[MethodologyFormulaDoc] = Field(default_factory=list)
    bias_mitigation_policy: str
    open_source_audit_link: str

# -------------------------------------------------------------
# PARTY RANKINGS & LEGISLATIVE BENCHMARKING SCHEMAS
# -------------------------------------------------------------
class PartyRankingEntry(BaseModel):
    bioguide_id: str
    full_name: str
    party: str
    chamber: str
    state: str
    district: Optional[int] = None
    image_url: Optional[str] = None
    leadership_role: Optional[str] = None
    overall_score: float # 0 to 100
    letter_grade: str
    tier_label: str
    archetype: str
    bills_sponsored: int
    bills_enacted: int
    earmarks_millions: float
    constituent_sync: float
    floor_attendance: float
    bipartisanship_velocity: float
    grassroots_pct: float
    pac_dependency: float
    clutch_rating: float
    stock_conflict_index: float
    current_net_worth: str = "$1.5M"
    net_worth_growth_dollars: str = "+$800k"
    wealth_growth_multiple: float = 2.5
    ethics_risk_score: float = 12.0
    ethics_risk_label: str = "LOW RISK"

class PartyRankingsResponse(BaseModel):
    total_members_count: int
    members: List[PartyRankingEntry] = Field(default_factory=list)
