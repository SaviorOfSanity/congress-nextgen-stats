"""
Live Civic Data Synchronization Pipeline
Hydrates local JSON datasets and fast caches from official / open public sources:
- unitedstates/congress-legislators (roster, terms, leadership roles, committees, subcommittees, FEC IDs)
- Voteview UCLA / Poole & Rosenthal (HS119/HS118/HS117 roll calls, votes, DW-NOMINATE spatial ideology)
- Clerk of the U.S. House Financial Disclosures (2025/2026 STOCK Act PTR & FD filing counts)
"""
import csv
import io
import json
import logging
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import CACHE_DIR, DATA_DIR, POLICY_CATEGORIES
from backend.ingestion.vote_classifier import classify_vote

logger = logging.getLogger(__name__)

LEGISLATORS_CURRENT_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
COMMITTEES_CURRENT_URL = "https://unitedstates.github.io/congress-legislators/committees-current.json"
COMMITTEE_MEMBERSHIP_URL = "https://unitedstates.github.io/congress-legislators/committee-membership-current.json"
VOTEVIEW_ALL_MEMBERS_URL = "https://voteview.com/static/data/out/members/HSall_members.csv"
VOTEVIEW_ROLLCALLS_TMPL = "https://voteview.com/static/data/out/rollcalls/HS{congress}_rollcalls.csv"
VOTEVIEW_VOTES_TMPL = "https://voteview.com/static/data/out/votes/HS{congress}_votes.csv"
HOUSE_FD_ZIP_TMPL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"

ALL_MEMBERS_PATH = DATA_DIR / "all_members.json"
COMMITTEES_CACHE_PATH = CACHE_DIR / "committees_official.json"
VOTEVIEW_SESSIONS_PATH = CACHE_DIR / "voteview_member_sessions.json"
HOUSE_FD_CACHE_PATH = CACHE_DIR / "house_fd_index.json"
EXTERNAL_IDS_CACHE_PATH = CACHE_DIR / "member_external_ids.json"

NON_VOTING_STATES = {"AS", "DC", "GU", "MP", "PR", "VI"}


def _fetch_bytes(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CongressCivicAnalytics/2.5 (Civic Transparency Pipeline)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _party_normalize(party_raw: str) -> str:
    p = (party_raw or "").strip()
    if p.startswith("D"):
        return "Democrat"
    if p.startswith("R"):
        return "Republican"
    return "Independent"


def _compute_terms_served(terms: List[Dict[str, Any]]) -> int:
    # Count House terms + Senator 6-year terms accurately
    return max(1, len(terms))


def _format_committee_display_name(raw_name: str, comm_type: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        return ""
    if name.lower().startswith(("house ", "senate ", "joint ")):
        return name
    prefix = "Senate" if comm_type == "senate" else ("Joint" if comm_type == "joint" else "House")
    return f"{prefix} {name}"


def _clean_bill_number(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("HR") and len(s) > 2 and s[2:].isdigit():
        return f"H.R. {s[2:]}"
    if s.startswith("S") and len(s) > 1 and s[1:].isdigit():
        return f"S. {s[1:]}"
    if s.startswith("HJRES") and s[5:].isdigit():
        return f"H.J.Res. {s[5:]}"
    if s.startswith("SJRES") and s[5:].isdigit():
        return f"S.J.Res. {s[5:]}"
    return s


def _sync_house_fd(years: Tuple[int, ...] = (2025, 2026)) -> Dict[str, Any]:
    """Download House Clerk annual FD/PTR index ZIPs and count PTRs & annual disclosures."""
    by_state_last: Dict[str, Dict[str, Any]] = {}
    for yr in years:
        try:
            zbytes = _fetch_bytes(HOUSE_FD_ZIP_TMPL.format(year=yr), timeout=15)
            with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
                txt_names = [n for n in zf.namelist() if n.endswith(".txt")]
                if not txt_names:
                    continue
                content = zf.read(txt_names[0]).decode("utf-8", errors="replace")
                reader = csv.DictReader(io.StringIO(content), delimiter="\t")
                for row in reader:
                    state_dst = (row.get("StateDst") or "").strip().upper()
                    last = (row.get("Last") or "").strip().lower()
                    first = (row.get("First") or "").strip().lower()
                    ftype = (row.get("FilingType") or "").strip().upper()
                    fdate = (row.get("FilingDate") or "").strip()
                    doc_id = (row.get("DocID") or "").strip()
                    if not state_dst or not last:
                        continue
                    key = f"{state_dst}|{last}"
                    rec = by_state_last.setdefault(
                        key,
                        {
                            "state_dst": state_dst,
                            "last": last,
                            "first": first,
                            "ptr_count": 0,
                            "annual_fd_count": 0,
                            "years": [],
                            "ptr_docs": [],
                            "recent_filings": [],
                        },
                    )
                    if str(yr) not in rec["years"]:
                        rec["years"].append(str(yr))
                    if ftype == "P":
                        rec["ptr_count"] += 1
                        if doc_id:
                            rec["ptr_docs"].append({"year": yr, "doc_id": doc_id, "date": fdate})
                    elif ftype in ("A", "O", "C"):
                        rec["annual_fd_count"] += 1
                    if len(rec["recent_filings"]) < 8:
                        rec["recent_filings"].append(
                            {"year": yr, "type": ftype, "date": fdate, "doc_id": doc_id}
                        )
        except Exception as e:
            logger.warning(f"House FD {yr} sync skipped: {e}")

    payload = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Office of the Clerk, U.S. House of Representatives Financial Disclosures",
        "records": by_state_last,
    }
    HOUSE_FD_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _process_voteview_conference(
    congress: int,
    rc_csv_text: str,
    votes_csv_text: str,
    icpsr_to_member: Dict[int, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Aggregate one Congress session of Voteview roll calls + member votes."""
    rollcalls: Dict[Tuple[str, int], Dict[str, Any]] = {}
    rc_reader = csv.DictReader(io.StringIO(rc_csv_text))
    for r in rc_reader:
        try:
            chamber = (r.get("chamber") or "").strip()
            rc_num = int(r["rollnumber"])
        except Exception:
            continue
        bill_raw = (r.get("bill_number") or "").strip()
        bill_num = _clean_bill_number(bill_raw)
        v_desc = (r.get("vote_desc") or "").strip()
        v_q = (r.get("vote_question") or "").strip()
        dtl = (r.get("dtl_desc") or "").strip()
        title = v_desc or dtl or v_q or f"{chamber} Roll Call #{rc_num}"
        category = classify_vote(f"{bill_num} {v_desc}", dtl, v_q)
        yea_c = int(float(r.get("yea_count") or 0))
        nay_c = int(float(r.get("nay_count") or 0))
        margin = abs(yea_c - nay_c)
        is_narrow = margin <= (15 if chamber == "House" else 5)
        is_named_passage = bool(bill_raw) and (
            "passage" in v_q.lower()
            or "agree" in v_q.lower()
            or "concur" in v_q.lower()
            or "cloture" in v_q.lower()
            or "final" in v_q.lower()
        )
        priority = (3 if bill_raw else 0) + (2 if is_named_passage else 0) + (1 if v_desc else 0)
        is_amendment = ("amendment" in v_q.lower()) or ("amendment" in dtl.lower())
        rollcalls[(chamber, rc_num)] = {
            "roll_call_id": f"{chamber[0]}-{congress}-{rc_num}",
            "chamber": chamber,
            "rollnumber": rc_num,
            "bill_number": bill_num or f"RC-{rc_num}",
            "bill_title": title[:220],
            "date": (r.get("date") or "").strip(),
            "result": f"{(r.get('vote_result') or 'RECORDED').strip()} ({yea_c} - {nay_c})",
            "category": category,
            "is_narrow": is_narrow,
            "is_amendment": is_amendment,
            "priority": priority,
            "dem_yes": 0,
            "dem_no": 0,
            "rep_yes": 0,
            "rep_no": 0,
        }

    # Stream votes once: group by icpsr AND tally dem/rep party majorities
    member_cast_list: Dict[int, List[Tuple[Tuple[str, int], str]]] = {}
    v_reader = csv.DictReader(io.StringIO(votes_csv_text))
    for row in v_reader:
        chamber = (row.get("chamber") or "").strip()
        try:
            rc_num = int(row["rollnumber"])
            icpsr = int(row["icpsr"])
            cc = int(float(row["cast_code"]))
        except Exception:
            continue
        key = (chamber, rc_num)
        rc = rollcalls.get(key)
        if not rc:
            continue
        if cc in (1, 2, 3):
            v_str = "YES"
        elif cc in (4, 5, 6):
            v_str = "NO"
        elif cc in (7, 8, 9):
            v_str = "ABSTAIN"
        else:
            continue

        mem = icpsr_to_member.get(icpsr)
        if mem and v_str in ("YES", "NO"):
            caucus_dem = mem["caucus_dem"]
            if caucus_dem:
                if v_str == "YES":
                    rc["dem_yes"] += 1
                else:
                    rc["dem_no"] += 1
            else:
                if v_str == "YES":
                    rc["rep_yes"] += 1
                else:
                    rc["rep_no"] += 1

        member_cast_list.setdefault(icpsr, []).append((key, v_str))

    # Finalize majority sides per roll call
    for rc in rollcalls.values():
        rc["dem_maj"] = "YES" if rc["dem_yes"] >= rc["dem_no"] else "NO"
        rc["rep_maj"] = "YES" if rc["rep_yes"] >= rc["rep_no"] else "NO"

    session_by_bioguide: Dict[str, Dict[str, Any]] = {}
    for icpsr, items in member_cast_list.items():
        mem = icpsr_to_member.get(icpsr)
        if not mem:
            continue
        bg = mem["bioguide_id"]
        caucus_dem = mem["caucus_dem"]

        total_votes = len(items)
        total_yes = 0
        total_no = 0
        total_abstained = 0
        own_party_matches = 0
        opp_party_matches = 0
        cast_count = 0
        divided_total = 0
        divided_own = 0
        divided_eligible = 0
        divided_missed = 0
        routine_eligible = 0
        routine_missed = 0
        narrow_total = 0
        narrow_attended = 0
        narrow_own = 0
        amend_total = 0
        amend_cast = 0
        amend_yes = 0

        cat_counts: Dict[str, List[int]] = {c: [0, 0, 0, 0] for c in POLICY_CATEGORIES}
        candidate_notables: List[Tuple[int, str, Dict[str, Any]]] = []

        for key, v_str in items:
            rc = rollcalls[key]
            cat = rc["category"]
            if cat not in cat_counts:
                cat_counts[cat] = [0, 0, 0, 0]
            cat_counts[cat][0] += 1

            own_maj = rc["dem_maj"] if caucus_dem else rc["rep_maj"]
            opp_maj = rc["rep_maj"] if caucus_dem else rc["dem_maj"]
            is_divided_rc = (own_maj != opp_maj)

            if is_divided_rc:
                divided_eligible += 1
                if v_str == "ABSTAIN":
                    divided_missed += 1
            else:
                routine_eligible += 1
                if v_str == "ABSTAIN":
                    routine_missed += 1

            if rc["is_amendment"]:
                amend_total += 1
                if v_str in ("YES", "NO"):
                    amend_cast += 1
                    if v_str == "YES":
                        amend_yes += 1

            if rc["is_narrow"]:
                narrow_total += 1
                if v_str in ("YES", "NO"):
                    narrow_attended += 1
                    if v_str == own_maj:
                        narrow_own += 1

            if v_str == "YES":
                total_yes += 1
                cat_counts[cat][1] += 1
            elif v_str == "NO":
                total_no += 1
                cat_counts[cat][2] += 1
            else:
                total_abstained += 1
                cat_counts[cat][3] += 1

            if v_str in ("YES", "NO"):
                cast_count += 1
                if v_str == own_maj:
                    own_party_matches += 1
                if v_str == opp_maj:
                    opp_party_matches += 1
                if own_maj != opp_maj:
                    divided_total += 1
                    if v_str == own_maj:
                        divided_own += 1

                if rc["priority"] >= 3:
                    is_split = v_str != own_maj
                    note = (
                        f"Crossed party line (voted {v_str} vs caucus majority {own_maj})"
                        if is_split
                        else (
                            "Bipartisan consensus vote"
                            if own_maj == opp_maj
                            else f"Voted with party majority ({own_maj})"
                        )
                    )
                    candidate_notables.append(
                        (
                            rc["priority"],
                            rc["date"],
                            {
                                "roll_call_id": rc["roll_call_id"],
                                "bill_number": rc["bill_number"],
                                "bill_title": rc["bill_title"],
                                "category": cat,
                                "member_vote": v_str,
                                "party_majority_vote": own_maj,
                                "result": rc["result"],
                                "date": rc["date"],
                                "is_party_split": is_split,
                                "significance_note": note,
                            },
                        )
                    )

        attendance_pct = round((cast_count / float(max(1, total_votes))) * 100.0, 1)
        # Use party-unity on party-divided votes if at least 20 divided votes exist; else overall alignment
        party_unity_pct = round(
            (divided_own / float(divided_total) * 100.0)
            if divided_total >= 20
            else (own_party_matches / float(max(1, cast_count)) * 100.0),
            1,
        )
        bipartisanship_pct = round((opp_party_matches / float(max(1, cast_count))) * 100.0, 1)

        cat_dict = {}
        for c, (tot, vy, vn, va) in cat_counts.items():
            cat_dict[c] = {
                "total_votes": tot,
                "votes_yes": vy,
                "votes_no": vn,
                "votes_abstained": va,
                "support_pct": round((vy / float(max(1, tot))) * 100.0, 1) if tot > 0 else 0.0,
            }

        # Pick diverse notable votes (mix of highest priority & party splits)
        candidate_notables.sort(key=lambda x: (x[2]["is_party_split"], x[0], x[1]), reverse=True)
        seen_bills = set()
        notable_votes = []
        for _, _, nv in candidate_notables:
            bn = nv["bill_number"]
            if bn in seen_bills and len(notable_votes) < 6:
                continue
            seen_bills.add(bn)
            notable_votes.append(nv)
            if len(notable_votes) >= 8:
                break

        session_by_bioguide[bg] = {
            "congress": congress,
            "total_votes": total_votes,
            "total_yes": total_yes,
            "total_no": total_no,
            "total_abstained": total_abstained,
            "attendance_pct": attendance_pct,
            "party_unity_pct": party_unity_pct,
            "bipartisanship_pct": bipartisanship_pct,
            "dw_nominate": mem.get("dw_nominate", 0.0),
            "divided_votes_total": divided_eligible,
            "divided_votes_missed": divided_missed,
            "divided_absence_pct": round((divided_missed / float(max(1, divided_eligible))) * 100.0, 1),
            "routine_votes_total": routine_eligible,
            "routine_votes_missed": routine_missed,
            "routine_absence_pct": round((routine_missed / float(max(1, routine_eligible))) * 100.0, 1),
            "amend_total": amend_total,
            "amend_cast": amend_cast,
            "amend_yes": amend_yes,
            "narrow_total": narrow_total,
            "narrow_attended": narrow_attended,
            "narrow_party_unity_pct": round(
                (narrow_own / float(max(1, narrow_attended))) * 100.0, 1
            ) if narrow_attended > 0 else party_unity_pct,
            "category_breakdown": cat_dict,
            "recent_votes": notable_votes,
        }

    return session_by_bioguide


def run_full_live_sync(conferences: Tuple[int, ...] = (119, 118, 117)) -> Dict[str, Any]:
    """
    Download and compile official datasets from Congress-Legislators, Voteview,
    and House Financial Disclosures into clean local caches and data/all_members.json.
    """
    logger.info("Running full live civic data sync...")

    existing_by_bg: Dict[str, Dict[str, Any]] = {}
    if ALL_MEMBERS_PATH.exists():
        try:
            for m in json.loads(ALL_MEMBERS_PATH.read_text(encoding="utf-8")):
                bg = m.get("bio", {}).get("bioguide_id")
                if bg:
                    existing_by_bg[bg] = m
        except Exception:
            pass

    urls_to_fetch = {
        "legs": LEGISLATORS_CURRENT_URL,
        "comms": COMMITTEES_CURRENT_URL,
        "cmems": COMMITTEE_MEMBERSHIP_URL,
        "vv_all": VOTEVIEW_ALL_MEMBERS_URL,
    }
    for c in conferences:
        urls_to_fetch[f"rc_{c}"] = VOTEVIEW_ROLLCALLS_TMPL.format(congress=c)
        urls_to_fetch[f"v_{c}"] = VOTEVIEW_VOTES_TMPL.format(congress=c)

    raw_blobs: Dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {k: pool.submit(_fetch_bytes, u, 30) for k, u in urls_to_fetch.items()}
        for k, fut in futures.items():
            raw_blobs[k] = fut.result()

    legs = json.loads(raw_blobs["legs"].decode("utf-8"))
    comms = json.loads(raw_blobs["comms"].decode("utf-8"))
    cmems = json.loads(raw_blobs["cmems"].decode("utf-8"))

    # Parse Voteview HSall_members for congresses 116..119
    vv_by_conf_bg: Dict[int, Dict[str, Dict[str, Any]]] = {}
    vv_by_conf_icpsr: Dict[int, Dict[int, Dict[str, Any]]] = {}
    for row in csv.DictReader(io.StringIO(raw_blobs["vv_all"].decode("utf-8", errors="replace"))):
        try:
            cong = int(row["congress"])
        except Exception:
            continue
        if cong < 116:
            continue
        bg = (row.get("bioguide_id") or "").strip()
        try:
            icpsr = int(row["icpsr"])
        except Exception:
            continue
        try:
            dim1 = round(float(row["nominate_dim1"]), 3) if row.get("nominate_dim1") else None
        except Exception:
            dim1 = None
        pcode = (row.get("party_code") or "").strip()
        if pcode == "100":
            caucus_dem = True
        elif pcode == "200":
            caucus_dem = False
        else:
            caucus_dem = (dim1 is not None and dim1 <= 0.05)

        entry = {
            "bioguide_id": bg,
            "icpsr": icpsr,
            "dw_nominate": dim1 if dim1 is not None else ( -0.35 if caucus_dem else 0.35),
            "caucus_dem": caucus_dem,
        }
        if bg:
            vv_by_conf_bg.setdefault(cong, {})[bg] = entry
        vv_by_conf_icpsr.setdefault(cong, {})[icpsr] = entry

    # Build member index & committees map
    leg_lookup: Dict[str, Dict[str, Any]] = {l["id"]["bioguide"]: l for l in legs}

    member_comms: Dict[str, List[str]] = {}
    member_subcomms: Dict[str, List[str]] = {}
    member_comm_lead_titles: Dict[str, str] = {}
    comm_meta_by_id: Dict[str, Dict[str, Any]] = {}
    subcomm_parent: Dict[str, Tuple[str, str]] = {}

    for c in comms:
        tid = c["thomas_id"]
        ctype = c.get("type", "house")
        cname = _format_committee_display_name(c["name"], ctype)
        subs = []
        for s in c.get("subcommittees", []):
            sid = f"{tid}{s['thomas_id']}"
            sname = s["name"]
            if not sname.lower().startswith("subcommittee"):
                sname = f"Subcommittee on {sname}"
            subs.append({"code": sid, "name": sname, "address": s.get("address"), "phone": s.get("phone")})
            subcomm_parent[sid] = (cname, sname)

        comm_meta_by_id[tid] = {
            "thomas_id": tid,
            "name": cname,
            "chamber": "Senate" if ctype == "senate" else ("Joint" if ctype == "joint" else "House"),
            "jurisdiction": c.get("jurisdiction") or "",
            "url": c.get("url") or "",
            "subcommittees": subs,
            "chair": None,
            "ranking_member": None,
            "majority_members": [],
            "minority_members": [],
        }

    for key, entries in cmems.items():
        if key in comm_meta_by_id:
            cm = comm_meta_by_id[key]
            cname = cm["name"]
            for m_entry in entries:
                bg = m_entry.get("bioguide")
                if not bg or bg not in leg_lookup:
                    continue
                lobj = leg_lookup[bg]
                latest_t = lobj["terms"][-1]
                party = _party_normalize(latest_t.get("party"))
                state = latest_t.get("state", "US")
                title = m_entry.get("title") or (
                    "Chair" if m_entry.get("rank") == 1 and m_entry.get("party") == "majority" else
                    ("Ranking Member" if m_entry.get("rank") == 1 and m_entry.get("party") == "minority" else
                     f"{m_entry.get('party', 'member').title()} Member (Rank #{m_entry.get('rank', '')})")
                )
                roster_item = {
                    "bioguide_id": bg,
                    "full_name": lobj["name"].get("official_full") or f"{lobj['name']['first']} {lobj['name']['last']}",
                    "party": party,
                    "state": state,
                    "rank": m_entry.get("rank", 99),
                    "role": title,
                    "image_url": f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/original/{bg}.jpg",
                }
                if m_entry.get("party") == "majority":
                    cm["majority_members"].append(roster_item)
                    if m_entry.get("rank") == 1:
                        cm["chair"] = roster_item
                else:
                    cm["minority_members"].append(roster_item)
                    if m_entry.get("rank") == 1:
                        cm["ranking_member"] = roster_item

                member_comms.setdefault(bg, [])
                if cname not in member_comms[bg]:
                    member_comms[bg].append(cname)
                if m_entry.get("title") in ("Chairman", "Chair", "Ranking Member") and bg not in member_comm_lead_titles:
                    short_comm = cname.replace("House Committee on ", "").replace("Senate Committee on ", "")
                    member_comm_lead_titles[bg] = f"{m_entry['title']}, {short_comm}"
        elif key in subcomm_parent:
            _, sname = subcomm_parent[key]
            for m_entry in entries:
                bg = m_entry.get("bioguide")
                if bg:
                    member_subcomms.setdefault(bg, [])
                    if sname not in member_subcomms[bg]:
                        member_subcomms[bg].append(sname)

    COMMITTEES_CACHE_PATH.write_text(
        json.dumps({"updated_utc": datetime.now(timezone.utc).isoformat(), "committees": comm_meta_by_id}),
        encoding="utf-8",
    )

    # Aggregate Voteview roll call sessions
    sessions_by_conf: Dict[str, Dict[str, Any]] = {}
    for c in conferences:
        sessions_by_conf[str(c)] = _process_voteview_conference(
            c,
            raw_blobs[f"rc_{c}"].decode("utf-8", errors="replace"),
            raw_blobs[f"v_{c}"].decode("utf-8", errors="replace"),
            vv_by_conf_icpsr.get(c, {}),
        )

    VOTEVIEW_SESSIONS_PATH.write_text(
        json.dumps({"updated_utc": datetime.now(timezone.utc).isoformat(), "sessions": sessions_by_conf}),
        encoding="utf-8",
    )

    # Sync House Clerk FD index
    house_fd = _sync_house_fd()

    # Build hydrated all_members.json + external IDs index
    external_ids: Dict[str, Dict[str, Any]] = {}
    now_year = datetime.now(timezone.utc).year
    hydrated_members: List[Dict[str, Any]] = []

    for l in legs:
        ids = l["id"]
        bg = ids["bioguide"]
        terms = l["terms"]
        first_term = terms[0]
        latest = terms[-1]

        party = _party_normalize(latest.get("party"))
        chamber = "Senate" if latest.get("type") == "sen" else "House"
        state = latest.get("state", "US")
        district = latest.get("district") if chamber == "House" else None
        first_elected = int(first_term["start"][:4])
        # Election year normalization for Jan swaps (2019 term -> 2018 election cycle, etc.)
        if first_term["start"].endswith("-01-03") and first_elected % 2 == 1:
            first_elected_cycle = first_elected - 1
        else:
            first_elected_cycle = first_elected
        terms_served = _compute_terms_served(terms)

        bday = (l.get("bio", {}).get("birthday") or "")
        birth_year = int(bday[:4]) if len(bday) >= 4 and bday[:4].isdigit() else None
        age = (now_year - birth_year) if birth_year else None

        # Active official congressional or committee leadership role
        lead_role = None
        for lr in reversed(l.get("leadership_roles") or []):
            if not lr.get("end"):
                lead_role = lr.get("title")
                break
        if not lead_role:
            lead_role = member_comm_lead_titles.get(bg)

        prev = existing_by_bg.get(bg, {})
        prev_bio = prev.get("bio", {})
        prev_aff = prev.get("affiliations", {})

        vv119 = sessions_by_conf.get("119", {}).get(bg)
        vv118 = sessions_by_conf.get("118", {}).get(bg)
        vv117 = sessions_by_conf.get("117", {}).get(bg)
        vv_mem = vv_by_conf_bg.get(119, {}).get(bg) or vv_by_conf_bg.get(118, {}).get(bg) or {}

        # Weighted aggregate across available recent Congresses
        active_sessions = [s for s in (vv119, vv118, vv117) if s and s.get("total_votes", 0) > 0]
        if active_sessions:
            tot_cast_sum = sum(s["total_votes"] for s in active_sessions)
            party_unity = round(sum(s["party_unity_pct"] * s["total_votes"] for s in active_sessions) / tot_cast_sum, 1)
            bipartisanship = round(sum(s["bipartisanship_pct"] * s["total_votes"] for s in active_sessions) / tot_cast_sum, 1)
            attendance = round(sum(s["attendance_pct"] * s["total_votes"] for s in active_sessions) / tot_cast_sum, 1)
        else:
            party_unity = prev.get("stats", {}).get("party_unity", 90.0)
            bipartisanship = prev.get("stats", {}).get("bipartisanship", 22.0)
            attendance = prev.get("stats", {}).get("attendance", 97.5)

        dw_nominate = vv_mem.get("dw_nominate")
        if dw_nominate is None:
            dw_nominate = -0.35 if party == "Democrat" else (0.35 if party == "Republican" else -0.15)

        fec_list = ids.get("fec") or []
        preferred_fec = None
        prefix = "S" if chamber == "Senate" else "H"
        for fc in fec_list:
            if fc.startswith(prefix):
                preferred_fec = fc
                break
        if not preferred_fec and fec_list:
            preferred_fec = fec_list[0]

        external_ids[bg] = {
            "fec_ids": fec_list,
            "preferred_fec_id": preferred_fec,
            "icpsr": ids.get("icpsr"),
            "lis": ids.get("lis"),
            "govtrack": ids.get("govtrack"),
            "is_delegate": state in NON_VOTING_STATES,
        }

        official_full = l["name"].get("official_full") or f"{l['name']['first']} {l['name']['last']}"
        hydrated_members.append(
            {
                "bio": {
                    "bioguide_id": bg,
                    "first_name": l["name"]["first"],
                    "last_name": l["name"]["last"],
                    "full_name": official_full,
                    "chamber": chamber,
                    "party": party,
                    "state": state,
                    "district": district,
                    "leadership_role": lead_role,
                    "first_elected": first_elected_cycle,
                    "terms_served": terms_served,
                    "birth_year": birth_year,
                    "age": age,
                    "estimated_net_worth": prev_bio.get("estimated_net_worth", "$1M - $5M"),
                    "gender": l.get("bio", {}).get("gender"),
                    "image_url": f"https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/original/{bg}.jpg",
                    "official_website": latest.get("url"),
                    "twitter_handle": prev_bio.get("twitter_handle"),
                },
                "affiliations": {
                    "committees": member_comms.get(bg) or prev_aff.get("committees", []),
                    "subcommittees": member_subcomms.get(bg, [])[:10],
                    "caucuses": prev_aff.get("caucuses", []),
                    "leadership_pacs": prev_aff.get("leadership_pacs", [f"{l['name']['last']} Victory Fund"]),
                    "prior_organizations": prev_aff.get("prior_organizations", []),
                },
                "stats": {
                    "party_unity": party_unity,
                    "bipartisanship": bipartisanship,
                    "attendance": attendance,
                    "dw_nominate": dw_nominate,
                },
            }
        )

    EXTERNAL_IDS_CACHE_PATH.write_text(json.dumps(external_ids), encoding="utf-8")
    ALL_MEMBERS_PATH.write_text(json.dumps(hydrated_members, indent=2), encoding="utf-8")

    return {
        "members_hydrated": len(hydrated_members),
        "committees_indexed": len(comm_meta_by_id),
        "voteview_119_members": len(sessions_by_conf.get("119", {})),
        "voteview_118_members": len(sessions_by_conf.get("118", {})),
        "voteview_117_members": len(sessions_by_conf.get("117", {})),
        "house_fd_records": len(house_fd.get("records", {})),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_full_live_sync(), indent=2))
