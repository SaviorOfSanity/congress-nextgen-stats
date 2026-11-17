"""
Official House Clerk STOCK Act Periodic Transaction Report (PTR) PDF Parser
Downloads public PTR PDFs from disclosures-clerk.house.gov and extracts line-item equity trades,
transaction dates, STOCK Act >45-day late notifications, and committee jurisdiction overlaps.
"""
import io
import json
import logging
import re
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pypdf import PdfReader
from backend.config import CACHE_DIR

logger = logging.getLogger(__name__)

PTR_PDF_URL_TMPL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
PTR_PARSED_CACHE_PATH = CACHE_DIR / "ptr_parsed_cache.json"
_PTR_CACHE: Optional[Dict[str, Any]] = None

_TX_ROW_RE = re.compile(
    r"\b([PSE])\b\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\$[\d,]+(?:\s*-\s*\$[\d,]+|\+)?)"
)
_TICKER_RE = re.compile(r"\(([A-Z]{1,6}(?:\.[A-Z]{1,2})?)\)")

_SECTOR_COMMITTEES = {
    "defense": ("armed", "defense", "intelligence", "appropriations"),
    "energy": ("energy", "natural", "environment", "commerce"),
    "finance": ("financial", "banking", "ways", "budget"),
    "health": ("health", "energy", "ways", "veterans"),
    "tech": ("science", "energy", "oversight", "armed", "judiciary"),
}


def reset_ptr_cache() -> None:
    global _PTR_CACHE
    _PTR_CACHE = None


def _load_ptr_cache() -> Dict[str, Any]:
    global _PTR_CACHE
    if _PTR_CACHE is None:
        if PTR_PARSED_CACHE_PATH.exists():
            try:
                _PTR_CACHE = json.loads(PTR_PARSED_CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                _PTR_CACHE = {}
        else:
            _PTR_CACHE = {}
    return _PTR_CACHE


def _save_ptr_cache() -> None:
    if _PTR_CACHE is not None:
        try:
            PTR_PARSED_CACHE_PATH.write_text(json.dumps(_PTR_CACHE), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Could not persist PTR parsed cache: {e}")


def parse_ptr_pdf_bytes(pdf_bytes: bytes, doc_id: str, year: Any) -> Dict[str, Any]:
    """Parse all transaction rows and STOCK Act reporting delays from one House Clerk PTR PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    transactions: List[Dict[str, Any]] = []
    late_count = 0

    for idx, line in enumerate(lines):
        m = _TX_ROW_RE.search(line)
        if not m:
            continue
        tx_code, tx_date_str, notif_date_str, amount_range = m.groups()
        tx_type = "PURCHASE" if tx_code == "P" else ("SALE" if tx_code == "S" else "EXCHANGE")

        # Asset description & ticker usually sit on the preceding 1-2 lines or before match on same line
        prefix_part = line[:m.start()].strip()
        context_chunk = " ".join(ln for ln in (lines[max(0, idx - 2):idx] + ([prefix_part] if prefix_part else [])))
        # Trim common PDF table header noise
        context_chunk = re.sub(r".*?Amount\s+Cap\.\s*Gains.*?\?\s*", "", context_chunk).strip()
        ticker_match = _TICKER_RE.search(context_chunk)
        ticker = ticker_match.group(1) if ticker_match else "ASSET"
        asset_name = re.sub(r"\[[A-Z]{2}\]", "", context_chunk).strip() or f"{ticker} Security"
        if len(asset_name) > 95:
            asset_name = asset_name[-95:].strip()

        late_days = None
        is_late = False
        try:
            dt_tx = datetime.strptime(tx_date_str, "%m/%d/%Y")
            dt_nt = datetime.strptime(notif_date_str, "%m/%d/%Y")
            late_days = (dt_nt - dt_tx).days
            is_late = late_days > 45
            if is_late:
                late_count += 1
        except Exception:
            pass

        transactions.append({
            "doc_id": doc_id,
            "year": year,
            "ticker": ticker,
            "company_name": asset_name,
            "transaction_type": tx_type,
            "transaction_date": tx_date_str,
            "notification_date": notif_date_str,
            "amount_range": amount_range.replace("  ", " ").strip(),
            "late_days": late_days,
            "is_stock_act_late": is_late,
        })

    return {
        "doc_id": doc_id,
        "year": year,
        "transactions": transactions,
        "late_count": late_count,
        "parsed_utc": datetime.now(timezone.utc).isoformat(),
    }


def fetch_and_parse_member_ptrs(
    bioguide_id: str,
    ptr_docs: List[Dict[str, Any]],
    fetch_live: bool = False,
    max_pdfs: int = 3,
) -> Dict[str, Any]:
    """Return parsed line-item transactions across a member's latest Clerk PTR PDFs (cached by bioguide_id)."""
    cache = _load_ptr_cache()
    if bioguide_id in cache:
        return cache[bioguide_id]
    if not fetch_live or not ptr_docs:
        return {"transactions": [], "late_count": 0, "parsed_doc_ids": []}

    all_txs: List[Dict[str, Any]] = []
    parsed_ids: List[str] = []
    late_total = 0

    for doc in ptr_docs[:max_pdfs]:
        doc_id = str(doc.get("doc_id") or "").strip()
        yr = doc.get("year") or 2025
        if not doc_id:
            continue
        url = PTR_PDF_URL_TMPL.format(year=yr, doc_id=doc_id)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CongressCivicAnalytics/2.6"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                pdf_bytes = resp.read()
            res = parse_ptr_pdf_bytes(pdf_bytes, doc_id=doc_id, year=yr)
            all_txs.extend(res["transactions"])
            late_total += res["late_count"]
            parsed_ids.append(doc_id)
        except Exception as e:
            logger.debug(f"Could not parse PTR PDF {doc_id} ({yr}): {e}")

    summary = {
        "transactions": all_txs,
        "late_count": late_total,
        "parsed_doc_ids": parsed_ids,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    if parsed_ids:
        cache[bioguide_id] = summary
        _save_ptr_cache()
    return summary
