from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# -----------------------------
# Global variables (files)
# -----------------------------

candidate_outcome: str = "candidate_outcomes.json"
transformed_output: str = "transformed_outputs.json"

# -----------------------------
# Matching configuration
# -----------------------------

STOPWORDS: Set[str] = {
    # common filler
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "at", "by", "with",
    "will", "would", "does", "do", "did", "is", "are", "was", "were", "be", "been", "being",
    # market phrasing
    "win", "wins", "won", "winner", "winning",
    # common sports/market words that often do not help identify the entity
    "scored", "score", "goals", "goal", "points", "point",
    # optional suffixes
    "fc", "cf", "sc", "bc", "ac", "afc",
}

# Optional: drop extremely short tokens that are usually not identifying
# (keeps things like "aj" if you want; set to 3 if you want to ignore "aj")
MIN_TOKEN_LEN = 2


def _normalize_text(s: str) -> str:
    """
    Lowercase, remove most punctuation, collapse whitespace.

    Option A: keep '.' characters.
    Keeps letters a-z, digits 0-9, whitespace, and '.'.
    """
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s\.]+", " ", s)  # keep dots
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize_set(s: str) -> Set[str]:
    """
    Tokenize by spaces after normalization, remove stopwords, apply MIN_TOKEN_LEN.
    """
    s = _normalize_text(s)
    if not s:
        return set()
    toks = s.split(" ")
    out: Set[str] = set()
    for t in toks:
        if not t:
            continue
        if t in STOPWORDS:
            continue
        if len(t) < MIN_TOKEN_LEN:
            continue
        out.add(t)
    return out


def _matches_subtitle(subtitle: str, outcome: str) -> bool:
    """
    Returns True if outcome matches subtitle using:
    1) phrase match (normalized outcome phrase contained in normalized subtitle)
    2) token overlap match (any meaningful outcome token appears in subtitle tokens)
    """
    subtitle_n = _normalize_text(subtitle)
    outcome_n = _normalize_text(outcome)

    if not subtitle_n or not outcome_n:
        return False

    # 1) phrase match
    if outcome_n in subtitle_n:
        return True

    # 2) token overlap match
    subtitle_tokens = _tokenize_set(subtitle)
    outcome_tokens = _tokenize_set(outcome)

    if not subtitle_tokens or not outcome_tokens:
        return False

    return len(subtitle_tokens.intersection(outcome_tokens)) > 0


def _try_map_one(item: Dict[str, Any]) -> Tuple[bool, Dict[str, str] | None]:
    outcomes = item.get("polymarket_outcomes") or []
    token_ids = item.get("polymarket_clobTokenIds") or []

    if len(outcomes) != 2 or len(token_ids) != 2:
        return False, None

    o0, o1 = str(outcomes[0]), str(outcomes[1])
    t0, t1 = str(token_ids[0]), str(token_ids[1])

    # Case 1: explicit Yes/No mapping (case-insensitive)
    o0_l = o0.strip().lower()
    o1_l = o1.strip().lower()
    if o0_l == "yes" and o1_l == "no":
        yes_token, no_token = t0, t1
    elif o0_l == "no" and o1_l == "yes":
        yes_token, no_token = t1, t0
    else:
        # Case 2: use matching against kalshi_yes_sub_title
        subtitle = str(item.get("kalshi_yes_sub_title") or "")

        m0 = _matches_subtitle(subtitle, o0)
        m1 = _matches_subtitle(subtitle, o1)

        # Only guard rail: must be unique
        if m0 and not m1:
            yes_token, no_token = t0, t1
        elif m1 and not m0:
            yes_token, no_token = t1, t0
        else:
            return False, None

    mapped = {
        "kalshi_ticker": str(item.get("kalshi_ticker") or ""),
        "poly_yes_token": yes_token,
        "poly_no_token": no_token,
    }
    return True, mapped


def transform(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in data:
        ok, mapped = _try_map_one(item)
        if ok and mapped is not None:
            out.append(mapped)
        else:
            kt = str(item.get("kalshi_ticker") or "")
            print(f"AMBIGUOUS: {kt}")
    return out


def _read_json(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input JSON file not found: {p.resolve()}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main() -> None:
    raw = _read_json(candidate_outcome)
    if not isinstance(raw, list):
        raise ValueError("candidate_outcome JSON must be a list of objects.")
    out = transform(raw)
    _write_json(transformed_output, out)


if __name__ == "__main__":
    main()