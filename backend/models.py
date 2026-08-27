"""
Data models and schemas for Congressional NextGenStats & Draft Profiles
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

class CombineMeasurables(BaseModel):
    party_loyalty: float # 0 - 100
    bipartisanship_velocity: float # 0 - 100
    floor_attendance: float # 0 - 100
    abstain_rate: float # 0 - 100 (Missed / Abstain %)
    pac_dependency: float # 0 - 100
    constituent_sync: float # 0 - 100
    legislative_motor: float # 0 - 100 (bills sponsored / cosponsored volume)
    district_loyalty: float = 80.0 # vs Donors (0 - 100)
    clutch_rating: float = 88.0 # 4th Quarter Clutch Index (0 - 100)

class ClutchVotingStats(BaseModel):
    clutch_rating: float # 0 - 100
    nailbiter_votes_analyzed: int
    clutch_party_loyalty_pct: float
    maverick_defection_pct: float
    clutch_archetype: str # "Party Anchor / Ice in the Veins", "Floor Maverick / Pressure Defector", "District-First Stabilizer"
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

class ScoutingCard(BaseModel):
    draft_grade: str # "A+", "A", "A-", "B+", "B", "C+", etc.
    draft_archetype: str # e.g. "Partisan Playmaker", "Floor Maverick", "District Pragmatist"
    archetype_description: str
    pro_comparison_name: str # e.g. "Joe Manchin (Legacy Comp)"
    pro_comparison_desc: str
    combine_measurables: CombineMeasurables
    strengths: List[str] = Field(default_factory=list)
    weaknesses_tendencies: List[str] = Field(default_factory=list)
    film_room_verdict: str

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
    scouting: ScoutingCard
    last_updated: str

# Head-to-Head Tale of the Tape Schema
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
    draft_grade: str
    draft_archetype: str

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
