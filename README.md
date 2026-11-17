# Congress Civic Analytics: Legislative Performance & Lawmaker Dossiers 🏛️📊

An open, automated data pipeline, nonpartisan legislative intelligence engine, and interactive civic analytics platform profiling all 539 voting members and delegates of the 119th United States Congress—featuring live Voteview roll calls and DW-NOMINATE spatial ideology, official 119th committees and subcommittees, U.S. Census Geocoder street-level district lookup, OpenFEC campaign filings, House Clerk STOCK Act disclosure indexing, and plain-English bill breakdowns.

---

## 🌟 Key Features

1. **5-Pillar Legislative Effectiveness Rating**:
   - **Nonpartisan 100-Point Benchmark**: Evaluates lawmakers across **Legislative Output & Enactments (25 pts)**, **Constituent & District Fidelity (25 pts)**, **Floor Attendance & Reliability (20 pts)**, **Special Interest & PAC Independence (15 pts)**, and **Bipartisanship & Coalition Building (15 pts)**.
   - **Interactive Score Math Modal**: Detailed breakdown of exact points earned, positive drivers, and deductions for every lawmaker.
   - **Realistic Distribution**: Eliminates grade inflation with an authentic distribution across A, B, C, D, and F ratings.

2. **Interactive Committee & Caucus Dossiers**:
   - Comprehensive statutory jurisdiction, agency oversight lists, and subpoena mandates across House/Senate standing committees and major caucuses.
   - Full member rosters partitioned into **Majority** and **Minority** members with one-click navigation to load each member's profile.
   - Subcommittees and active legislative priorities before each committee.

3. **District Demographics Deep-Dive & Roll Call Correlation**:
   - Compares voting history directly against U.S. Census Bureau ACS 5-Year district socioeconomic metrics (median household income, poverty rate, SNAP food assistance %, foreign-born population %, and Medicaid enrollment %).
   - Evaluates whether lawmakers vote in alignment with local constituent needs or national party talking points.

4. **12 Policy Verticals & Landmark Bill Archive**:
   - Interactive drill-down into Economy & Taxation, Healthcare, Tech & AI Privacy, Energy, Border Security, Defense, Judiciary, and more.
   - Includes **plain-English bill summaries**, **key statutory provisions**, roll call outcomes, and district/sector impacts.

5. **Campaign Finance, Geography & Special Interest Profiler**:
   - Ingests OpenFEC filings (`candidate/totals`, `schedule_a/by_state/by_candidate`, and `schedule_e`) for Grassroots Micro-Donations (<$200), In-State vs. Out-of-State fundraising splits, and Super PAC outside spending.
   - **Constituent Fidelity vs. Earmark-Donor Crosswalk**: Highlights donor sector alignment vs. local district priorities and maps appropriations earmark categories against top contributing industries and committee oversight.
   - **Line-Item House Clerk PTR PDF Parser & STOCK Act Timing Audit**: Parses public House Clerk Periodic Transaction Report (PTR) PDFs via `pypdf`, detects late disclosures (>45-day statutory window), and cross-references equities against assigned committee jurisdictions (Senate eFD remains linked via its interactive portal).
   - **Contested vs. Routine Absence & Floor Amendment Checks**: Splits missed Voteview roll calls into party-divided floor votes vs. routine motions and tracks Congress.gov v3 bill sponsorships alongside Voteview amendment participation.

6. **Automated Weekly Updates & Real-Time Sync**:
   - Background daemon automatically updates roll calls, committee rosters, and Census tables every **Saturday at 02:00 AM UTC**.
   - On-demand manual sync button for instant database refreshes.

7. **Open Civic Methodology & Verification**:
   - 100% public data sourced directly from Congress.gov, House/Senate Clerks, U.S. Census Bureau, FEC, House/Senate Ethics Committees, and Voteview UCLA DW-NOMINATE.
   - Published mathematical formulas and open collaboration guidelines for bias mitigation.

---

## 🚀 Quick Start Guide

### Option A: Run via Docker (Recommended for Servers & Proxmox)

```bash
# Clone the repository
git clone https://github.com/SaviorOfSanity/congress-nextgen-stats.git
cd congress-nextgen-stats

# Launch with Docker Compose
docker-compose up -d --build
```
Open **[http://localhost:8000](http://localhost:8000)** (or your server's IP at port `8000`) in your browser!

---

### Option B: Run Locally with Python

```bash
# Clone the repository
git clone https://github.com/SaviorOfSanity/congress-nextgen-stats.git
cd congress-nextgen-stats

# Install dependencies
pip install -r requirements.txt

# Start the web server
python -m backend.cli serve --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

### 💻 Command Line Interface (CLI)

#### Search for Lawmakers
```bash
python -m backend.cli search "Jordan"
python -m backend.cli search "California"
```

#### Generate a Terminal Lawmaker Dossier
```bash
python -m backend.cli scout --bioguide "J000289"
python -m backend.cli scout --bioguide "O000172"
```

---

## 📁 Project Architecture

```
congress-civic-analytics/
├── backend/
│   ├── config.py                 # System paths, API keys, policy verticals
│   ├── models.py                 # Pydantic schemas for ratings, voting, and demographics
│   ├── scheduler.py              # Automated weekly Saturday sync daemon & manual triggers
│   ├── cli.py                    # Multi-command CLI runner (search, scout, serve)
│   ├── server.py                 # FastAPI backend & REST API endpoints
│   ├── ingestion/
│   │   ├── congress_api.py       # Member bios, 12-category bill archive, roll calls
│   │   ├── committees_data.py    # Committee jurisdictions, leadership, and rosters
│   │   ├── census_api.py         # U.S. Census ACS district demographic mapper
│   │   ├── fec_api.py            # FEC receipts, Schedule A geography & PACs
│   │   ├── ptr_parser.py         # House Clerk PTR PDF parser & 45-day timing check
│   │   ├── live_sync.py          # Voteview, committee & House FD weekly cache sync
│   │   └── vote_classifier.py    # Policy categorization engine (12 verticals)
│   ├── analytics/
│   │   ├── scouting_model.py     # 5-pillar rating engine, score breakdowns & comps
│   │   └── constituent_sync.py   # District alignment index & friction calculations
│   └── video_engine/
│       ├── graphics_generator.py # Radar charts & visual slides
│       ├── commentator.py        # Analytical voiceover script generator
│       ├── voice_synth.py        # Neural AI voiceover synthesis
│       └── video_assembler.py    # FFmpeg MP4 stream encoder
├── web/
│   └── index.html                # Interactive civic analytics web dashboard UI
├── output/
│   ├── cards/                    # High-resolution lawmaker infographic graphics
│   └── videos/                   # Rendered MP4 analytical videos
├── docker-compose.yml            # Container orchestration config
├── Dockerfile                    # Container build recipe
└── requirements.txt              # Python library dependencies
```

---

## 📜 Nonpartisan Data Sources & Citations

- **Official Legislative & Roll Call Records**: [Voteview / Poole & Rosenthal DW-NOMINATE](https://voteview.com), [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators), & [Congress.gov API](https://api.congress.gov).
- **District Geocoding & Socioeconomic Demographics**: [U.S. Census Bureau Geocoder](https://geocoding.geo.census.gov) & [American Community Survey (ACS 5-Year Data)](https://www.census.gov/programs-surveys/acs).
- **Campaign Finance & Super PAC Contributions**: [Federal Election Commission (OpenFEC)](https://www.fec.gov/data).
- **Financial & STOCK Act Disclosures**: [Office of the Clerk, U.S. House](https://disclosures-clerk.house.gov) & [Senate Ethics](https://efdsearch.senate.gov).

---

## 🔒 Environment Variables & Public Deployment (Cloudflare Tunnel)

Copy `.env.example` to `.env` before deploying externally:

```bash
cp .env.example .env
```

- Set `ADMIN_API_KEY` to a strong secret so `POST /api/admin/sync` and `POST /api/video/generate` require `X-Admin-Key` when accessed over a tunnel/proxy (or put those routes behind Cloudflare Zero Trust Access).
- Set `ALLOWED_ORIGINS` to your public hostname (for example `https://congress.yourdomain.com`).
- Optional keys (`CONGRESS_API_KEY`, `FEC_API_KEY`, `CENSUS_API_KEY`) unlock higher-rate live Congress.gov bill sponsorship, OpenFEC cycle totals, and district-level Census ACS queries.

---

## 🤝 Open Collaboration & Auditing

All analytical models apply identical mathematical formulas and thresholds equally across Democrats, Republicans, and Independents. We welcome public scrutiny, academic peer review, and community contributions to continuously refine our scoring models.
