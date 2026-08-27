"""
High-Impact Sports Broadcast & Draft Card Graphics Generator
Produces NextGenStats HUD cards, radar charts, and film room slides.
"""
import io
import math
import logging
from pathlib import Path
from typing import Tuple, List, Dict
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.config import CARDS_DIR
from backend.models import CongressionalProfile

logger = logging.getLogger(__name__)

# Design System Colors (Sports HUD Broadcast Dark Theme)
BG_COLOR = "#0b0f19"          # Deep cosmic navy/black
CARD_BG = "#131b2e"           # Dark slate card container
ACCENT_CYAN = "#00f0ff"       # Neon cyan for tech/data
ACCENT_GOLD = "#ffb703"       # Draft Gold for grade/highlights
ACCENT_GREEN = "#06d6a0"      # Positive sync / pass
ACCENT_RED = "#ef476f"        # Dissonance / against
TEXT_WHITE = "#f8f9fa"
TEXT_MUTED = "#94a3b8"

def download_member_photo(url: str, bioguide_id: str = "") -> Image.Image:
    """Download member headshot or return default silhouette."""
    import requests
    candidate_urls = []
    if bioguide_id:
        candidate_urls.append(f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/original/{bioguide_id}.jpg")
        candidate_urls.append(f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/225x275/{bioguide_id}.jpg")
    if url:
        # If url was theunitedstates.io, rewrite to raw github
        if "theunitedstates.io/images/congress" in url:
            rewritten = url.replace("https://theunitedstates.io/images/congress", "https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress")
            candidate_urls.append(rewritten)
        candidate_urls.append(url)

    for target_url in candidate_urls:
        try:
            resp = requests.get(target_url, timeout=5, headers={"User-Agent": "CongressNextGen/1.0"})
            if resp.status_code == 200 and len(resp.content) > 100:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                return img
        except Exception:
            continue

    # Generate placeholder silhouette
    img = Image.new("RGBA", (400, 400), (30, 41, 59, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([120, 70, 280, 230], fill=(100, 116, 139, 255))
    draw.ellipse([60, 240, 340, 460], fill=(100, 116, 139, 255))
    return img

def create_radar_chart(profile: CongressionalProfile, size: Tuple[int, int] = (600, 600)) -> Image.Image:
    """
    Generate 6-axis NextGenStats Combine Radar Polygon.
    """
    labels = [
        "Party Loyalty", 
        "Bipartisanship", 
        "Attendance", 
        "Grassroots Power", 
        "Constituent Sync", 
        "Legislative Motor"
    ]
    
    m = profile.scouting.combine_measurables
    grassroots_power = 100.0 - m.pac_dependency
    values = [
        m.party_loyalty,
        m.bipartisanship_velocity,
        m.floor_attendance,
        grassroots_power,
        m.constituent_sync,
        m.legislative_motor
    ]
    
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * math.pi for n in range(num_vars)]
    angles += angles[:1]
    values += values[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True), facecolor=BG_COLOR)
    ax.set_facecolor(CARD_BG)
    
    # Draw polygon
    ax.plot(angles, values, color=ACCENT_CYAN, linewidth=3, linestyle="solid")
    ax.fill(angles, values, color=ACCENT_CYAN, alpha=0.35)
    
    # Fix axis to 0 - 100
    ax.set_ylim(0, 100)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXT_WHITE, fontsize=11, fontweight="bold")
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], color=TEXT_MUTED, fontsize=9)
    ax.grid(color="#334155", linestyle="--", alpha=0.7)
    ax.spines["polar"].set_color("#334155")
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")

def create_slide_1_intro(profile: CongressionalProfile, is_vertical: bool = True) -> Image.Image:
    """Slide 1: Draft Board Prospect Card."""
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Top Header Banner
    draw.rectangle([0, 0, width, 140 if is_vertical else 100], fill="#070a12")
    draw.line([0, 140 if is_vertical else 100, width, 140 if is_vertical else 100], fill=ACCENT_CYAN, width=3)
    
    # Title Text
    draw.text((width // 2, 40 if is_vertical else 25), "CONGRESSIONAL NEXTGEN STATS", fill=ACCENT_CYAN, anchor="mm", font_size=32)
    draw.text((width // 2, 85 if is_vertical else 65), "OFFICIAL SCOUTING REPORT & DRAFT PROFILE", fill=TEXT_MUTED, anchor="mm", font_size=20)
    
    # Photo Container
    photo_size = 400 if is_vertical else 340
    photo = download_member_photo(profile.bio.image_url, profile.bio.bioguide_id)
    photo = photo.resize((photo_size, photo_size), Image.Resampling.LANCZOS)
    
    px = (width - photo_size) // 2 if is_vertical else 160
    py = 220 if is_vertical else 200
    
    # Draw glowing photo frame
    draw.rounded_rectangle([px - 8, py - 8, px + photo_size + 8, py + photo_size + 8], radius=24, fill="#1e293b", outline=ACCENT_CYAN, width=3)
    img.paste(photo, (px, py), photo)
    
    # Member Identity Details
    bio = profile.bio
    info_x = width // 2 if is_vertical else 620
    info_y = (py + photo_size + 60) if is_vertical else 200
    anchor = "mm" if is_vertical else "lm"
    
    # Chamber / State Badge
    badge_text = f"{bio.party.upper()} • {bio.state.upper()} ({bio.chamber.upper()})"
    if bio.district is not None:
        badge_text = f"{bio.party.upper()} • {bio.state.upper()}-{bio.district:02d} ({bio.chamber.upper()})"
    
    draw.text((info_x, info_y), badge_text, fill=ACCENT_GOLD, anchor=anchor, font_size=28)
    draw.text((info_x, info_y + 60), bio.full_name, fill=TEXT_WHITE, anchor=anchor, font_size=56)
    
    if bio.leadership_role:
        draw.text((info_x, info_y + 125), f"★ {bio.leadership_role} ★", fill=ACCENT_CYAN, anchor=anchor, font_size=26)
    
    # Draft Grade Big Badge
    card_y = (info_y + 200) if is_vertical else 580
    card_x = (width - 800) // 2 if is_vertical else 160
    card_w = 800 if is_vertical else 1600
    
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + 240], radius=20, fill=CARD_BG, outline="#334155", width=2)
    
    # Grade Circle
    draw.ellipse([card_x + 30, card_y + 30, card_x + 210, card_y + 210], fill="#1e293b", outline=ACCENT_GOLD, width=4)
    draw.text((card_x + 120, card_y + 90), "GRADE", fill=TEXT_MUTED, anchor="mm", font_size=18)
    draw.text((card_x + 120, card_y + 145), profile.scouting.draft_grade, fill=ACCENT_GOLD, anchor="mm", font_size=52)
    
    # Archetype & Pro Comp Info
    tx = card_x + 250
    draw.text((tx, card_y + 45), f"ARCHETYPE: {profile.scouting.draft_archetype.upper()}", fill=ACCENT_CYAN, font_size=28)
    draw.text((tx, card_y + 90), profile.scouting.archetype_description, fill=TEXT_WHITE, font_size=20)
    draw.text((tx, card_y + 145), f"PRO COMPARISON: {profile.scouting.pro_comparison_name}", fill=ACCENT_GOLD, font_size=24)
    draw.text((tx, card_y + 185), profile.scouting.pro_comparison_desc[:70] + "...", fill=TEXT_MUTED, font_size=18)

    # Lower Third Scouting Ticker
    if is_vertical:
        t_y = card_y + 320
        draw.rounded_rectangle([card_x, t_y, card_x + card_w, t_y + 260], radius=16, fill="#0f172a", outline="#1e293b", width=2)
        draw.text((card_x + 30, t_y + 30), "KEY AFFILIATIONS & COMMITTEES", fill=ACCENT_CYAN, font_size=22)
        affs = profile.affiliations.committees[:2] + profile.affiliations.caucuses[:2]
        for i, aff in enumerate(affs[:4]):
            draw.text((card_x + 30, t_y + 70 + (i * 42)), f"▶ {aff}", fill=TEXT_WHITE, font_size=19)

    return img

def create_slide_2_measurables(profile: CongressionalProfile, is_vertical: bool = True) -> Image.Image:
    """Slide 2: NextGenStats Combine Measurables & Radar HUD."""
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Top Header
    draw.rectangle([0, 0, width, 120], fill="#070a12")
    draw.line([0, 120, width, 120], fill=ACCENT_CYAN, width=3)
    draw.text((width // 2, 60), f"COMBINE MEASURABLES: {profile.bio.full_name.upper()}", fill=TEXT_WHITE, anchor="mm", font_size=32)
    
    # Embed Radar Chart
    radar_img = create_radar_chart(profile, (550, 550) if is_vertical else (480, 480))
    rx = (width - radar_img.width) // 2 if is_vertical else 100
    ry = 160 if is_vertical else 180
    img.paste(radar_img, (rx, ry), radar_img)
    
    # Draw Measurable Stat Bars
    bars_x = 80 if is_vertical else 720
    bars_y = (ry + radar_img.height + 40) if is_vertical else 180
    bar_w = width - 160 if is_vertical else 1080
    
    m = profile.scouting.combine_measurables
    stats_list = [
        ("PARTY LINE LOYALTY", m.party_loyalty, ACCENT_CYAN),
        ("CONSTITUENT SYNC SCORE", m.constituent_sync, ACCENT_GREEN),
        ("FLOOR ATTENDANCE RATE", m.floor_attendance, ACCENT_GOLD),
        ("LEGISLATIVE MOTOR", m.legislative_motor, ACCENT_CYAN),
        ("BIPARTISANSHIP VELOCITY", m.bipartisanship_velocity, "#38bdf8"),
        ("PAC CONTRIBUTION RELIANCE", m.pac_dependency, ACCENT_RED if m.pac_dependency > 30 else ACCENT_GREEN)
    ]
    
    for i, (label, val, col) in enumerate(stats_list):
        sy = bars_y + (i * (110 if is_vertical else 85))
        draw.text((bars_x, sy), label, fill=TEXT_WHITE, font_size=20)
        draw.text((bars_x + bar_w, sy), f"{val:.1f}%", fill=col, anchor="ra", font_size=22)
        
        # Background bar
        by = sy + 32
        draw.rounded_rectangle([bars_x, by, bars_x + bar_w, by + 20], radius=8, fill="#1e293b")
        # Filled bar
        fill_w = int((val / 100.0) * bar_w)
        if fill_w > 0:
            draw.rounded_rectangle([bars_x, by, bars_x + fill_w, by + 20], radius=8, fill=col)
            
    return img

def create_slide_3_voting(profile: CongressionalProfile, is_vertical: bool = True) -> Image.Image:
    """Slide 3: Voting Policy Breakdown & Stance Analysis."""
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Top Header
    draw.rectangle([0, 0, width, 120], fill="#070a12")
    draw.line([0, 120, width, 120], fill=ACCENT_CYAN, width=3)
    draw.text((width // 2, 60), f"VOTING TAPE BY POLICY SECTOR", fill=TEXT_WHITE, anchor="mm", font_size=32)
    
    # Policy Breakdown Bars
    start_y = 160
    cats = list(profile.voting.category_breakdown.items())[:8 if is_vertical else 6]
    box_w = width - 120 if is_vertical else 860
    
    for i, (cat_name, stat) in enumerate(cats):
        col_x = 60 if is_vertical else (60 if i % 2 == 0 else 980)
        row_y = start_y + (i * 180) if is_vertical else (start_y + (i // 2) * 220)
        
        draw.rounded_rectangle([col_x, row_y, col_x + box_w, row_y + 150], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
        draw.text((col_x + 24, row_y + 20), cat_name.upper(), fill=ACCENT_CYAN, font_size=22)
        draw.text((col_x + box_w - 24, row_y + 20), f"{stat.support_pct:.0f}% SUPPORT", fill=TEXT_WHITE, anchor="ra", font_size=20)
        
        # Dual Bar (YES vs NO)
        b_y = row_y + 60
        b_w = box_w - 48
        draw.rounded_rectangle([col_x + 24, b_y, col_x + 24 + b_w, b_y + 22], radius=6, fill="#1e293b")
        
        yes_w = int((stat.votes_yes / max(1, stat.total_votes)) * b_w)
        if yes_w > 0:
            draw.rounded_rectangle([col_x + 24, b_y, col_x + 24 + yes_w, b_y + 22], radius=6, fill=ACCENT_GREEN)
            
        draw.text((col_x + 24, row_y + 100), f"✔ {stat.votes_yes} Yea Votes", fill=ACCENT_GREEN, font_size=18)
        draw.text((col_x + 240, row_y + 100), f"✖ {stat.votes_no} Nay Votes", fill=ACCENT_RED, font_size=18)
        draw.text((col_x + box_w - 24, row_y + 100), f"Total: {stat.total_votes} Analyzed", fill=TEXT_MUTED, anchor="ra", font_size=18)

    return img

def create_slide_4_constituents(profile: CongressionalProfile, is_vertical: bool = True) -> Image.Image:
    """Slide 4: District Impact & Constituent Gap Index."""
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Top Header
    draw.rectangle([0, 0, width, 120], fill="#070a12")
    draw.line([0, 120, width, 120], fill=ACCENT_CYAN, width=3)
    draw.text((width // 2, 60), f"CONSTITUENT SYNC & DISTRICT PROFILE", fill=TEXT_WHITE, anchor="mm", font_size=32)
    
    # Overall Sync Banner
    sy = 160
    draw.rounded_rectangle([60, sy, width - 60, sy + 180], radius=20, fill="#0f172a", outline=ACCENT_GREEN if profile.alignment.overall_sync_score >= 80 else ACCENT_GOLD, width=3)
    draw.text((width // 2, sy + 40), f"OVERALL DISTRICT SYNC SCORE: {profile.alignment.overall_sync_score:.1f}%", fill=ACCENT_GREEN if profile.alignment.overall_sync_score >= 80 else ACCENT_GOLD, anchor="mm", font_size=32)
    draw.text((width // 2, sy + 100), profile.alignment.scouting_takeaway, fill=TEXT_WHITE, anchor="mm", font_size=20)
    
    # District Demographics Grid
    c = profile.constituents
    dy = sy + 220
    draw.rounded_rectangle([60, dy, width - 60, dy + 320], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
    draw.text((90, dy + 25), f"HOME DISTRICT METRICS ({c.district_code})", fill=ACCENT_CYAN, font_size=24)
    
    demo_metrics = [
        f"• Median Income: ${c.median_household_income:,}",
        f"• Poverty Rate: {c.poverty_rate_pct:.1f}%",
        f"• Urban / Rural Split: {c.urban_pct:.0f}% / {c.rural_pct:.0f}%",
        f"• College Degree Rate: {c.college_educated_pct:.1f}%",
        f"• Veteran Population: {c.veteran_pct:.1f}%",
        f"• Partisan Lean: {c.partisan_lean_pvi}"
    ]
    for idx, dm in enumerate(demo_metrics):
        col = idx % 2
        row = idx // 2
        draw.text((90 + (col * (width // 2 - 60)), dy + 80 + (row * 65)), dm, fill=TEXT_WHITE, font_size=22)
        
    # Top Alignments & Friction Zones
    fy = dy + 360
    draw.rounded_rectangle([60, fy, width - 60, fy + 480], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
    draw.text((90, fy + 30), "TOP DISTRICT ALIGNMENT AREAS", fill=ACCENT_GREEN, font_size=24)
    for i, al in enumerate(profile.alignment.top_alignment_areas):
        draw.text((90, fy + 80 + (i * 45)), f"✔ {al}", fill=TEXT_WHITE, font_size=20)
        
    draw.text((90, fy + 240), "PRIMARY FRICTION & DIVERGENCE AREAS", fill=ACCENT_RED, font_size=24)
    for i, div in enumerate(profile.alignment.top_divergence_areas):
        draw.text((90, fy + 290 + (i * 45)), f"✖ {div}", fill=TEXT_WHITE, font_size=20)

    return img

def create_slide_5_film_room(profile: CongressionalProfile, is_vertical: bool = True) -> Image.Image:
    """Slide 5: Film Room Scouting Verdict & Top Donors."""
    width, height = (1080, 1920) if is_vertical else (1920, 1080)
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Top Header
    draw.rectangle([0, 0, width, 120], fill="#070a12")
    draw.line([0, 120, width, 120], fill=ACCENT_CYAN, width=3)
    draw.text((width // 2, 60), f"FILM ROOM VERDICT & DONOR BACKING", fill=TEXT_WHITE, anchor="mm", font_size=32)
    
    # Strengths Box
    sy = 160
    draw.rounded_rectangle([60, sy, width - 60, sy + 320], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
    draw.text((90, sy + 25), "SCOUTING STRENGTHS", fill=ACCENT_GREEN, font_size=24)
    for i, s in enumerate(profile.scouting.strengths):
        draw.text((90, sy + 80 + (i * 65)), f"★ {s}", fill=TEXT_WHITE, font_size=21)
        
    # Weaknesses Box
    wy = sy + 360
    draw.rounded_rectangle([60, wy, width - 60, wy + 260], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
    draw.text((90, wy + 25), "TENDENCIES & CAUTIONS", fill=ACCENT_GOLD, font_size=24)
    for i, w in enumerate(profile.scouting.weaknesses_tendencies):
        draw.text((90, wy + 80 + (i * 60)), f"⚠ {w}", fill=TEXT_WHITE, font_size=21)
        
    # Top Funding Sectors
    fy = wy + 300
    draw.rounded_rectangle([60, fy, width - 60, fy + 380], radius=16, fill=CARD_BG, outline="#1e293b", width=2)
    draw.text((90, fy + 25), "TOP DONOR & INDUSTRY SECTORS", fill=ACCENT_CYAN, font_size=24)
    for i, sec in enumerate(profile.finance.top_donor_sectors[:4]):
        draw.text((90, fy + 80 + (i * 65)), f"• {sec.sector_name}: ${sec.amount_usd:,.0f} ({sec.pct_of_total:.1f}%)", fill=TEXT_WHITE, font_size=20)

    # Final Grade Sign-off
    gy = fy + 420
    draw.rounded_rectangle([60, gy, width - 60, gy + 160], radius=20, fill="#070a12", outline=ACCENT_GOLD, width=3)
    draw.text((width // 2, gy + 50), f"FINAL DRAFT GRADE: {profile.scouting.draft_grade}", fill=ACCENT_GOLD, anchor="mm", font_size=36)
    draw.text((width // 2, gy + 110), f"NEXTGEN STATS CONGRESSIONAL PROFILE • VERIFIED DATA", fill=TEXT_MUTED, anchor="mm", font_size=18)

    return img

def generate_all_slides(profile: CongressionalProfile, is_vertical: bool = True) -> List[Path]:
    """Generate and save all 5 slides for video assembly."""
    member_slug = profile.bio.full_name.lower().replace(" ", "_")
    orientation = "shorts" if is_vertical else "broadcast"
    dest_dir = CARDS_DIR / f"{member_slug}_{orientation}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    slide_generators = [
        ("01_intro", create_slide_1_intro),
        ("02_measurables", create_slide_2_measurables),
        ("03_voting", create_slide_3_voting),
        ("04_constituents", create_slide_4_constituents),
        ("05_film_room", create_slide_5_film_room)
    ]
    
    saved_paths: List[Path] = []
    for name, gen_fn in slide_generators:
        img = gen_fn(profile, is_vertical=is_vertical)
        out_path = dest_dir / f"{name}.png"
        img.save(out_path, format="PNG")
        saved_paths.append(out_path)
        
    return saved_paths
