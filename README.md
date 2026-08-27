# Congress NextGenStats & Draft Profile Engine 🏈🏛️

An automated data pipeline, scouting report analytics engine, and AI video generation suite that profiles US Congress members like NFL Draft prospects—featuring automated voting categorization, constituent alignment scoring, and high-impact sports-broadcast-style profile videos.

![NextGenStats HUD](output/cards/alexandria_ocasio-cortez_shorts/01_intro.png)

---

## 🌟 Key Features

1. **NFL Draft Scouting Cards & Combine Measurables**:
   - **Draft Archetypes**: *"Grassroots Firebrand"*, *"Committee Workhorse"*, *"Party Field General"*, *"Floor Maverick & Dealmaker"*, *"District Pragmatist"*, *"K-Street Power Broker"*.
   - **Combine Metrics (0-100)**: Party Line Loyalty, Constituent Sync Score, Floor Attendance Rate, Legislative Motor, Bipartisanship Velocity, and PAC Contribution Dependency.
   - **Pro Comparisons**: Algorithmically matched against veteran and historical lawmakers (e.g. Tip O'Neill, Newt Gingrich, Bernie Sanders, Henry Clay).
   - **Composite Draft Grade**: A+, A, A-, B+, B, B-, C+, C.

2. **Constituent Alignment & District Gap Index**:
   - Compares voting history across 12 policy verticals directly against US Census ACS 5-year district demographics, local median income, poverty rate, urban/rural distribution, and top employment sectors (defense, agriculture, tech, energy, healthcare).
   - Identifies **Top District Alignment Areas** vs **Primary Dissonance/Friction Zones**.

3. **Campaign Finance & PAC Profiler**:
   - Ingests FEC receipts and OpenSecrets donor sector mappings.
   - Breaks down Grassroots Micro-donations (<$200) vs Large Individual vs Corporate PAC dependency.
   - Identifies Leadership PACs and top contributing corporate/union donors.

4. **Automated Sports Broadcast Video Generator**:
   - Generates high-definition motion graphics cards (Draft Board, Radar Chart HUD, Voting Tape, District Match-up, Film Room Verdict).
   - Generates an energetic, analytical sports-scout voiceover script.
   - Synthesizes synchronized AI neural broadcast voiceovers (`edge-tts`).
   - Exports high-fps MP4 videos in both **Vertical 9:16 (Shorts/TikTok/Reels)** and **Horizontal 16:9 (YouTube/Broadcast)** formats in seconds!

5. **Interactive Web Dashboard & API**:
   - Real-time search with autocomplete across all 535 voting members of the House and Senate.
   - Interactive radar charts, combine progress meters, and one-click video generator studio.

---

## 🚀 Quick Start Guide

### 1. Launch the Interactive Web Dashboard
Run the following command in your terminal:
```bash
cd C:\Users\SaviorOfSanity\.gemini\antigravity\scratch\congress-nextgen-stats
.\.venv\Scripts\python.exe -m backend.cli serve --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

---

### 2. Command Line Interface (CLI)

#### Search for Lawmakers
```bash
.\.venv\Scripts\python.exe -m backend.cli search "Jordan"
.\.venv\Scripts\python.exe -m backend.cli search "California"
```

#### Generate a Terminal Scouting Report
```bash
.\.venv\Scripts\python.exe -m backend.cli scout --bioguide "J000289"
.\.venv\Scripts\python.exe -m backend.cli scout --bioguide "O000172"
```

#### Generate a Broadcast-Ready MP4 Video
```bash
# Render Vertical 9:16 Shorts / TikTok Video
.\.venv\Scripts\python.exe -m backend.cli generate-video --bioguide "O000172" --format shorts

# Render Horizontal 16:9 Broadcast Video
.\.venv\Scripts\python.exe -m backend.cli generate-video --bioguide "P000197" --format broadcast
```
Rendered videos are saved to `output/videos/`.

---

## 📁 Project Architecture

```
congress-nextgen-stats/
├── backend/
│   ├── config.py                 # System paths, API keys, policy verticals
│   ├── models.py                 # Pydantic schemas for scouting, voting & demographics
│   ├── cli.py                    # Multi-command CLI runner (search, scout, video, serve)
│   ├── server.py                 # FastAPI backend & static file streaming
│   ├── ingestion/
│   │   ├── congress_api.py       # Member bios, caucuses, committees, roll calls
│   │   ├── census_api.py         # ACS district demographic & economic mapper
│   │   ├── fec_api.py            # FEC receipts, PAC vs grassroots funding
│   │   └── vote_classifier.py    # Policy categorization engine (12 verticals)
│   ├── analytics/
│   │   ├── scouting_model.py     # Combine measurables, draft archetypes & pro comps
│   │   └── constituent_sync.py   # District alignment index & friction calculations
│   └── video_engine/
│       ├── graphics_generator.py # Radar charts, HUD cards & visual slides
│       ├── commentator.py        # Sports-style scouting voiceover script generator
│       ├── voice_synth.py        # Neural AI voiceover synthesis
│       └── video_assembler.py    # Native FFmpeg stream muxer & MP4 encoder
├── web/
│   └── index.html                # Interactive NextGenStats web dashboard UI
├── output/
│   ├── cards/                    # High-res PNG slide graphics
│   └── videos/                   # Rendered MP4 videos
└── data/cache/                   # Cached API payloads and assets
```
