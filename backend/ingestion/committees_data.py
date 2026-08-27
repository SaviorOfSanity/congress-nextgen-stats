"""
Congressional Committees and Caucuses Database & Roster Intelligence
Provides jurisdiction mapping, agency oversight lists, subcommittee structures, and full member rosters.
"""
from typing import Dict, List, Optional, Any
from backend.models import (
    CommitteeDossier,
    CommitteeMemberEntry,
    CommitteeSubcommitteeDetail
)
from backend.ingestion.congress_api import load_all_congress_members

COMMITTEE_DATABASE = {
    "house committee on oversight and accountability": {
        "code": "HSGO",
        "name": "House Committee on Oversight and Accountability",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Chief investigative and government-wide oversight committee of the House of Representatives. Holds broad statutory subpoena power over all federal executive agencies, government efficiency, federal contracts, regulatory enforcement, and presidential administration compliance.",
        "agencies": ["Executive Office of the President", "Department of Justice (DOJ)", "Department of Homeland Security (DHS)", "General Services Administration (GSA)", "Office of Management and Budget (OMB)", "All Federal Inspectors General"],
        "chair_bioguide": "C001108", # James Comer
        "chair_name": "James Comer",
        "ranking_bioguide": "R000606", # Jamie Raskin
        "ranking_name": "Jamie Raskin",
        "subcommittees": [
            {
                "name": "Subcommittee on Cybersecurity, Information Technology, and Government Innovation",
                "focus_area": "Federal IT procurement, artificial intelligence deployment across agencies, and civilian federal cyber defense."
            },
            {
                "name": "Subcommittee on National Security, the Border, and Foreign Affairs",
                "focus_area": "Southern border interdiction operations, defense supply chain accountability, and foreign aid tracking."
            },
            {
                "name": "Subcommittee on Economic Growth, Energy Policy, and Regulatory Affairs",
                "focus_area": "Federal regulatory burden on small businesses, energy permitting reviews, and consumer price oversight."
            },
            {
                "name": "Subcommittee on Health Care and Financial Services",
                "focus_area": "CMS healthcare reimbursements, prescription drug pricing oversight, and financial regulatory enforcement."
            }
        ],
        "active_priorities": [
            "Federal Agency Telework Productivity and Real Estate Utilization Audits",
            "Border Security Operations and Emergency Procurement Oversight",
            "COVID-19 Pandemic Emergency Relief Fraud Clawback Investigations",
            "Executive Branch Ethical Disclosures and Foreign Business Dealings Reviews"
        ]
    },
    "house committee on the judiciary": {
        "code": "HSJU",
        "name": "House Committee on the Judiciary",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Jurisdiction over federal courts, constitutional amendments, civil rights, federal criminal law, antitrust and monopolies, immigration statutes, intellectual property, copyright/patent law, and impeachment proceedings.",
        "agencies": ["Department of Justice (DOJ)", "Federal Bureau of Investigation (FBI)", "Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)", "Drug Enforcement Administration (DEA)", "U.S. Patent and Trademark Office (USPTO)", "Federal Trade Commission (Antitrust)"],
        "chair_bioguide": "J000289", # Jim Jordan
        "chair_name": "Jim Jordan",
        "ranking_bioguide": "N000002", # Jerrold Nadler
        "ranking_name": "Jerrold Nadler",
        "subcommittees": [
            {
                "name": "Subcommittee on the Weaponization of the Federal Government",
                "focus_area": "Investigating alleged federal agency surveillance, political bias, and civil liberties infractions."
            },
            {
                "name": "Subcommittee on Immigration Integrity, Security, and Enforcement",
                "focus_area": "Immigration statutory enforcement, asylum law standards, and deportation proceedings."
            },
            {
                "name": "Subcommittee on the Administrative State, Regulatory Reform, and Antitrust",
                "focus_area": "Big Tech platform competition, merger reviews, and Chevron deference doctrine reforms."
            },
            {
                "name": "Subcommittee on Crime and Federal Government Surveillance",
                "focus_area": "FISA Section 702 reauthorization, FBI oversight, and federal criminal code updates."
            }
        ],
        "active_priorities": [
            "FISA Section 702 Electronic Surveillance Privacy Safeguards",
            "Big Tech Platform Antitrust Enforcement & Digital Market Competition",
            "Federal Judicial Nomination Reviews & Supreme Court Ethics Standards",
            "Civil Asset Forfeiture and Criminal Justice Sentencing Reform"
        ]
    },
    "house committee on financial services": {
        "code": "HSBA",
        "name": "House Committee on Financial Services",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Oversees the entire domestic economy, commercial banking system, Federal Reserve monetary policy, Wall Street securities exchanges, housing and urban development, international monetary organizations, and insurance markets.",
        "agencies": ["Federal Reserve System (Fed)", "Securities and Exchange Commission (SEC)", "Department of the Treasury", "Federal Deposit Insurance Corporation (FDIC)", "Consumer Financial Protection Bureau (CFPB)", "Department of Housing and Urban Development (HUD)"],
        "chair_bioguide": "M001156", # Patrick McHenry
        "chair_name": "Patrick McHenry",
        "ranking_bioguide": "W000187", # Maxine Waters
        "ranking_name": "Maxine Waters",
        "subcommittees": [
            {
                "name": "Subcommittee on Digital Assets, Financial Technology and Inclusion",
                "focus_area": "Cryptocurrency regulatory frameworks, stablecoin statutory rules, and FinTech innovation."
            },
            {
                "name": "Subcommittee on Financial Institutions and Monetary Policy",
                "focus_area": "Federal Reserve interest rate policy, regional banking liquidity, and Basel III capital requirements."
            },
            {
                "name": "Subcommittee on Capital Markets",
                "focus_area": "SEC market structure regulations, private equity disclosures, and IPO access for small companies."
            },
            {
                "name": "Subcommittee on Housing and Insurance",
                "focus_area": "Affordable housing construction supply, Fannie Mae/Freddie Mac, and property insurance availability."
            }
        ],
        "active_priorities": [
            "Comprehensive Digital Asset and Payment Stablecoin Statutory Framework",
            "Regional Bank Liquidity, Uninsured Deposit Protections, and Capital Requirements",
            "National Flood Insurance Program (NFIP) Long-Term Reauthorization",
            "Credit Card Late Fee Caps and Consumer Credit Reporting Protections"
        ]
    },
    "house committee on energy and commerce": {
        "code": "HSIF",
        "name": "House Committee on Energy and Commerce",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Oldest continuous standing committee in the House with broad jurisdiction over consumer protection, food and drug safety, clean air/water environmental policy, public health, interstate telecommunications, cybersecurity, and national energy grids.",
        "agencies": ["Department of Energy (DOE)", "Department of Health and Human Services (HHS)", "Food and Drug Administration (FDA)", "Environmental Protection Agency (EPA)", "Federal Communications Commission (FCC)", "Federal Trade Commission (FTC)"],
        "chair_bioguide": "R000575", # Cathy McMorris Rodgers
        "chair_name": "Cathy McMorris Rodgers",
        "ranking_bioguide": "P000034", # Frank Pallone
        "ranking_name": "Frank Pallone",
        "subcommittees": [
            {
                "name": "Subcommittee on Health",
                "focus_area": "Medicare Part D drug price negotiations, Medicaid funding, and NIH biomedical research grants."
            },
            {
                "name": "Subcommittee on Energy, Climate, and Grid Security",
                "focus_area": "Nuclear reactor permitting, natural gas pipelines, and electrical grid reliability."
            },
            {
                "name": "Subcommittee on Communications and Technology",
                "focus_area": "Spectrum auctions, rural broadband deployment grants, and online minor safety protections."
            },
            {
                "name": "Subcommittee on Innovation, Data, and Commerce",
                "focus_area": "Comprehensive federal consumer data privacy, autonomous vehicles, and supply chain security."
            }
        ],
        "active_priorities": [
            "American Privacy Rights Act (Federal Consumer Data Protection Standard)",
            "Pharmacy Benefit Manager (PBM) Transparency and Drug Price Reform",
            "Advanced Nuclear Energy Siting and Permitting Modernization (ADVANCE Act)",
            "Children and Teens Online Privacy Protection Act (KOSA & COPPA 2.0)"
        ]
    },
    "house committee on armed services": {
        "code": "HSAS",
        "name": "House Committee on Armed Services",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Responsible for funding authorizations and statutory oversight of the Department of Defense (DoD), U.S. Armed Forces, military readiness, defense industrial base procurement, military pay/benefits, and tactical intelligence operations.",
        "agencies": ["Department of Defense (DoD)", "Department of the Army, Navy, and Air Force", "Defense Advanced Research Projects Agency (DARPA)", "Defense Logistics Agency (DLA)", "National Security Agency (Tactical DoD)"],
        "chair_bioguide": "R000575", # Mike Rogers
        "chair_name": "Mike Rogers",
        "ranking_bioguide": "S000510", # Adam Smith
        "ranking_name": "Adam Smith",
        "subcommittees": [
            {
                "name": "Subcommittee on Tactical Air and Land Forces",
                "focus_area": "F-35 fighter jet procurement, armored combat vehicles, and ammunition manufacturing plants."
            },
            {
                "name": "Subcommittee on Seapower and Projection Forces",
                "focus_area": "Navy shipbuilding rates, Virginia-class submarines, and naval shipyard modernization."
            },
            {
                "name": "Subcommittee on Cyber, Information Technologies, and Innovation",
                "focus_area": "Military AI autonomy, quantum computing, DoD cloud networks, and electronic warfare."
            }
        ],
        "active_priorities": [
            "Annual National Defense Authorization Act (NDAA) Statutory Formulation",
            "Indo-Pacific Deterrence Initiative and Taiwan Security Assistance",
            "Junior Enlisted Servicemember Pay Raise (19.5% Increase Proposal)",
            "Domestic Defense Munitions Industrial Base Surge Capacity Expansion"
        ]
    },
    "house committee on rules": {
        "code": "HSRU",
        "name": "House Committee on Rules",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Known as the 'Traffic Cop of the House.' Determines which bills reach the House floor, which amendments may be offered, and the debate terms under structured rule resolutions.",
        "agencies": ["House Floor Procedure", "Joint Committee on the Library", "Joint Committee on Printing"],
        "chair_bioguide": "C001053", # Tom Cole
        "chair_name": "Tom Cole",
        "ranking_bioguide": "M000312", # Jim McGovern
        "ranking_name": "Jim McGovern",
        "subcommittees": [
            {
                "name": "Subcommittee on Legislative and Budget Process",
                "focus_area": "Emergency spending designation rules and parliamentary procedure standards."
            }
        ],
        "active_priorities": [
            "Special Rules Structuring for Annual Appropriations Measures",
            "Emergency Supplemental Security Assistance Floor Gatekeeping",
            "Amendment Germane Rule Adjudication on Major Floor Packages"
        ]
    },
    "house committee on natural resources": {
        "code": "HSII",
        "name": "House Committee on Natural Resources",
        "chamber": "House",
        "type": "Standing Committee",
        "jurisdiction": "Oversees federal public lands, national parks, wildlife refuges, Native American tribal relations, offshore mineral leasing, fisheries, and federal water reclamation projects.",
        "agencies": ["Department of the Interior (DOI)", "Bureau of Land Management (BLM)", "National Park Service (NPS)", "Bureau of Indian Affairs (BIA)", "U.S. Fish and Wildlife Service (USFWS)"],
        "chair_bioguide": "W000821", # Bruce Westerman
        "chair_name": "Bruce Westerman",
        "ranking_bioguide": "G000551", # Raúl Grijalva
        "ranking_name": "Raúl Grijalva",
        "subcommittees": [
            {
                "name": "Subcommittee on Energy and Mineral Resources",
                "focus_area": "Critical mineral processing, geothermal leasing, and offshore wind permitting."
            },
            {
                "name": "Subcommittee on Federal Lands",
                "focus_area": "National park deferred maintenance funding and active forest wildfire management."
            }
        ],
        "active_priorities": [
            "Federal Wildfire Prevention and Categorical Exclusion Forest Management",
            "Critical Mineral Domestic Supply Chain Permitting on Federal Lands",
            "Tribal Water Rights Settlement Compact Confirmations"
        ]
    },
    "senate committee on the judiciary": {
        "code": "SSJU",
        "name": "Senate Committee on the Judiciary",
        "chamber": "Senate",
        "type": "Standing Committee",
        "jurisdiction": "Conducts confirmation hearings for Article III federal judges and Supreme Court Justices. Oversees antitrust, civil rights, federal criminal justice statutes, patents, and Department of Justice administration.",
        "agencies": ["Department of Justice (DOJ)", "Federal Judiciary / Supreme Court", "FBI", "DEA", "ATF", "U.S. Marshals Service"],
        "chair_bioguide": "D000563", # Dick Durbin
        "chair_name": "Dick Durbin",
        "ranking_bioguide": "G000386", # Chuck Grassley
        "ranking_name": "Chuck Grassley",
        "subcommittees": [
            {
                "name": "Subcommittee on Privacy, Technology, and the Law",
                "focus_area": "Frontier AI frontier safety testing, biometric surveillance, and algorithmic accountability."
            },
            {
                "name": "Subcommittee on Competition Policy, Antitrust, and Consumer Rights",
                "focus_area": "Healthcare hospital consolidation, live entertainment ticketing monopolies, and algorithmic price fixing."
            }
        ],
        "active_priorities": [
            "Federal Judicial Nomination Confirmation Hearings & Vetting",
            "Supreme Court Ethics, Financial Disclosure, and Recusal Legislation",
            "Bipartisan Artificial Intelligence Licensing and Liability Framework",
            "Kids Online Safety Act (KOSA) Statutory Passage"
        ]
    },
    "senate committee on appropriations": {
        "code": "SSAP",
        "name": "Senate Committee on Appropriations",
        "chamber": "Senate",
        "type": "Standing Committee",
        "jurisdiction": "Has constitutional responsibility to write the legislation that allocates federal discretionary funds to government agencies, departments, and programs for each fiscal year across all 12 annual spending bills.",
        "agencies": ["All Federal Executive Agencies", "Department of Defense", "Department of Transportation", "HHS", "NASA", "State Department"],
        "chair_bioguide": "M001111", # Patty Murray
        "chair_name": "Patty Murray",
        "ranking_bioguide": "C001035", # Susan Collins
        "ranking_name": "Susan Collins",
        "subcommittees": [
            {
                "name": "Subcommittee on Defense",
                "focus_area": "Allocates over $840 billion in discretionary military procurement and personnel spending."
            },
            {
                "name": "Subcommittee on Labor, Health and Human Services, Education, and Related Agencies",
                "focus_area": "NIH biomedical grants, Title I public school aid, and Head Start early education."
            },
            {
                "name": "Subcommittee on Transportation, Housing and Urban Development, and Related Agencies",
                "focus_area": "Federal highway formula grants, FAA modernization, and Section 8 housing vouchers."
            }
        ],
        "active_priorities": [
            "12 Regular Annual Discretionary Appropriations Bills Formulation",
            "Emergency National Security and Disaster Relief Supplemental Packages",
            "Congressionally Directed Spending (Earmarks) Transparency Disclosures"
        ]
    },
    "congressional progressive caucus": {
        "code": "CPC",
        "name": "Congressional Progressive Caucus",
        "chamber": "House & Senate",
        "type": "Congressional Caucus",
        "jurisdiction": "Largest ideological caucus in the Democratic Party. Advocates for economic justice, universal healthcare (Medicare for All), progressive tax bracket reform, green infrastructure transition, racial equity, and diplomatic foreign policy.",
        "agencies": ["Democratic Caucus Policy Platform", "Caucus Whip Coordination", "Labor Union Alliances"],
        "chair_bioguide": "J000298", # Pramila Jayapal
        "chair_name": "Pramila Jayapal",
        "ranking_bioguide": None,
        "ranking_name": None,
        "subcommittees": [
            {"name": "Labor and Economic Justice Task Force", "focus_area": "$17 Federal Minimum Wage and PRO Act worker unionization protections."},
            {"name": "Climate and Environmental Justice Task Force", "focus_area": "Green New Deal public works and environmental justice block grants."}
        ],
        "active_priorities": [
            "Universal Single-Payer Healthcare (Medicare for All)",
            "Expanding the Child Tax Credit and Universal Childcare Subsidies",
            "Protecting Social Security and Medicare from Benefit Reductions",
            "Federal Wealth Tax on Ultra-High Net Worth Asset Holdings"
        ]
    },
    "house freedom caucus": {
        "code": "HFC",
        "name": "House Freedom Caucus",
        "chamber": "House",
        "type": "Congressional Caucus",
        "jurisdiction": "Influential conservative and libertarian congressional caucus advocating for constitutional originalism, balanced federal budgets, dramatic non-defense spending cuts, strict border security, and procedural decentralized power in the House.",
        "agencies": ["House Floor Leverage Coordination", "Conservative Policy Formulation"],
        "chair_bioguide": "G000565", # Bob Good
        "chair_name": "Bob Good",
        "ranking_bioguide": None,
        "ranking_name": None,
        "subcommittees": [
            {"name": "Budget & Spending Restraint Task Force", "focus_area": "Enforcing pre-2019 discretionary spending caps and single-subject appropriations votes."},
            {"name": "Border Integrity Task Force", "focus_area": "Defunding non-enforcement asylum policies and conditioning funding on wall construction."}
        ],
        "active_priorities": [
            "Balanced Budget Amendment and Strict Statutory Spending Ceilings",
            "Enforcing H.R. 2 Secure the Border Provisions in All Spending Measures",
            "Eliminating Omnibus Spending Bills in Favor of 12 Individual Bills",
            "Rolling Back Unfunded Federal Agency Administrative Regulations"
        ]
    },
    "problem solvers caucus": {
        "code": "PSC",
        "name": "Problem Solvers Caucus",
        "chamber": "House",
        "type": "Congressional Caucus",
        "jurisdiction": "Bipartisan group equally split between Democrats and Republicans committed to finding common-ground solutions on infrastructure, national debt, immigration reform, and healthcare access.",
        "agencies": ["Bipartisan Coalition Building", "House Floor Rule Reform"],
        "chair_bioguide": "F000466", # Brian Fitzpatrick
        "chair_name": "Brian Fitzpatrick & Josh Gottheimer (Co-Chairs)",
        "ranking_bioguide": None,
        "ranking_name": None,
        "subcommittees": [
            {"name": "Bipartisan Infrastructure & Competitiveness Working Group", "focus_area": "Highway trust fund solvency and semiconductor supply chain reshoring."},
            {"name": "Fiscal Stability Working Group", "focus_area": "Bipartisan Fiscal Commission on long-term national debt sustainability."}
        ],
        "active_priorities": [
            "Bipartisan Fiscal Commission Act to Address Long-Term Debt Drivers",
            "Bipartisan Border Security and Farm Labor Legal Status Compromises",
            "Electoral Count Reform and Congressional House Rule Stability",
            "Community Healthcare Center Multi-Year Reauthorization"
        ]
    }
}

def clean_committee_query(q: str) -> str:
    s = q.lower().strip()
    # Strip prefixes/suffixes like "house ", "senate ", "committee on ", "(honorary)"
    s = s.replace("(honorary)", "").replace("standing committee", "").strip()
    return s

def get_committee_dossier(committee_query: str) -> CommitteeDossier:
    """
    Retrieve or build a comprehensive Committee Dossier with full member rosters.
    """
    q = clean_committee_query(committee_query)
    
    # Try exact match or substring match
    matched_key = None
    for k in COMMITTEE_DATABASE:
        if k in q or q in k:
            matched_key = k
            break
            
    if not matched_key:
        # Check partial keyword match (e.g. "oversight", "judiciary", "financial services", "progressive", "freedom")
        for k in COMMITTEE_DATABASE:
            words = [w for w in q.split() if len(w) > 3 and w not in ["house", "senate", "committee", "caucus"]]
            if any(w in k for w in words):
                matched_key = k
                break
                
    if not matched_key:
        # Fallback generic standing committee structure
        title = committee_query.strip()
        if not title.startswith("House") and not title.startswith("Senate") and not "Caucus" in title:
            title = f"House Committee on {title}"
            
        data = {
            "code": "HSXX",
            "name": title,
            "chamber": "Senate" if "Senate" in title else "House",
            "type": "Standing Committee" if "Caucus" not in title else "Congressional Caucus",
            "jurisdiction": f"Conducts legislative formulation, oversight hearings, and statutory authorization markups related to {title.replace('House Committee on', '').replace('Senate Committee on', '').strip()} policy initiatives.",
            "agencies": ["Relevant Federal Executive Departments", "Subordinate Bureau Agencies"],
            "chair_bioguide": None,
            "chair_name": "Committee Leadership Chair",
            "ranking_bioguide": None,
            "ranking_name": "Ranking Member",
            "subcommittees": [
                {"name": "Subcommittee on General Oversight and Operations", "focus_area": "Statutory execution reviews and federal budget efficiency."},
                {"name": "Subcommittee on Policy Strategy and Innovation", "focus_area": "Emerging legislative priorities and stakeholder hearings."}
            ],
            "active_priorities": [
                "Annual Budget Authorization and Agency Oversight Review",
                "Stakeholder Industry Expert and Inspector General Testimony Hearings",
                "Statutory Language Markups for Pending House/Senate Measures"
            ]
        }
    else:
        data = COMMITTEE_DATABASE[matched_key]

    # Build member roster from all preloaded members
    all_members = load_all_congress_members()
    majority_members = []
    minority_members = []
    
    chair_entry = None
    ranking_entry = None
    
    for m in all_members:
        bio = m.get("bio", {})
        affs = m.get("affiliations", {})
        all_aff_strings = [a.lower() for a in affs.get("committees", []) + affs.get("caucuses", []) + affs.get("subcommittees", [])]
        
        # Check if member belongs to this committee/caucus
        is_member = False
        target_name_lower = data["name"].lower()
        if any(target_name_lower in a or a in target_name_lower for a in all_aff_strings):
            is_member = True
        else:
            # Check key word
            keywords = [w for w in data["name"].lower().split() if len(w) > 4 and w not in ["house", "senate", "committee", "caucus"]]
            if any(all(kw in a for kw in keywords[:2]) for a in all_aff_strings):
                is_member = True
                
        # Also include specific known key members for high-profile committees
        bid = bio.get("bioguide_id")
        if bid == data.get("chair_bioguide") or bid == data.get("ranking_bioguide"):
            is_member = True
            
        if is_member:
            role = "Member"
            if bid == data.get("chair_bioguide"):
                role = "Chair"
            elif bid == data.get("ranking_bioguide"):
                role = "Ranking Member"
            elif "Vice" in (bio.get("leadership_role") or ""):
                role = bio.get("leadership_role") or "Vice Chair"
                
            entry = CommitteeMemberEntry(
                bioguide_id=bio.get("bioguide_id"),
                full_name=bio.get("full_name"),
                party=bio.get("party"),
                state=bio.get("state"),
                district=bio.get("district"),
                chamber=bio.get("chamber"),
                role=role,
                image_url=bio.get("image_url"),
                subcommittees=affs.get("subcommittees", [])[:2]
            )
            
            if role == "Chair":
                chair_entry = entry
            elif role == "Ranking Member":
                ranking_entry = entry
                
            if bio.get("party") == "Republican":
                majority_members.append(entry)
            else:
                minority_members.append(entry)

    # Ensure chair and ranking member exist if not populated from current subset
    if not chair_entry and data.get("chair_name"):
        chair_entry = CommitteeMemberEntry(
            bioguide_id=data.get("chair_bioguide") or "LEAD01",
            full_name=data["chair_name"],
            party="Republican" if data["chamber"] == "House" else "Democrat",
            state="US",
            district=None,
            chamber=data["chamber"],
            role="Chair",
            image_url=f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/original/{data.get('chair_bioguide', 'O000172')}.jpg"
        )
        if chair_entry.party == "Republican" and not any(m.full_name == chair_entry.full_name for m in majority_members):
            majority_members.insert(0, chair_entry)
            
    if not ranking_entry and data.get("ranking_name"):
        ranking_entry = CommitteeMemberEntry(
            bioguide_id=data.get("ranking_bioguide") or "LEAD02",
            full_name=data["ranking_name"],
            party="Democrat" if data["chamber"] == "House" else "Republican",
            state="US",
            district=None,
            chamber=data["chamber"],
            role="Ranking Member",
            image_url=f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/original/{data.get('ranking_bioguide', 'J000289')}.jpg"
        )
        if ranking_entry.party == "Democrat" and not any(m.full_name == ranking_entry.full_name for m in minority_members):
            minority_members.insert(0, ranking_entry)

    subcomms = [
        CommitteeSubcommitteeDetail(
            name=s["name"],
            chair_name=s.get("chair_name"),
            ranking_member_name=s.get("ranking_member_name"),
            focus_area=s["focus_area"]
        ) for s in data.get("subcommittees", [])
    ]

    total_count = len(majority_members) + len(minority_members)

    return CommitteeDossier(
        committee_code=data["code"],
        committee_name=data["name"],
        chamber=data["chamber"],
        type=data["type"],
        jurisdiction_overview=data["jurisdiction"],
        key_agencies_supervised=data["agencies"],
        subcommittees=subcomms,
        chair=chair_entry,
        ranking_member=ranking_entry,
        majority_members=majority_members,
        minority_members=minority_members,
        active_legislative_priorities=data["active_priorities"],
        total_members_count=total_count
    )
