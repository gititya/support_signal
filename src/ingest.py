import os
import re
import json
from pathlib import Path

import openai
import pandas as pd

from src.llm_client import get_client

FILTER_MODEL = "anthropic/claude-haiku-4.5"
COMPANY = "TRANSUNION INTERMEDIATE HOLDINGS, INC."
DATA_PATH = Path(__file__).parent.parent / "data" / "complaints.csv"
CAP = 2000
SEMANTIC_THRESHOLD = 20  # if keyword match < this, run semantic expansion via Haiku

STOPWORDS = {
    # Articles, conjunctions, prepositions
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "as", "up", "out", "if", "so", "into", "after",
    "before", "than", "then", "there", "through", "between", "during",
    # Verbs / auxiliaries
    "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "get", "got", "want", "wants", "wanted",
    "need", "needs", "using", "used", "use",
    # Pronouns
    "i", "me", "my", "we", "our", "you", "your", "they", "their",
    "it", "its", "he", "she", "him", "her",
    # Common filler
    "that", "this", "these", "those", "what", "when", "how", "who",
    "which", "about", "from", "not", "no", "just", "also", "more",
    "all", "any", "each", "some", "such", "very",
    # Support/complaint context noise — too generic to drive matching
    "customer", "customers", "consumer", "consumers",
    "complain", "complaining", "complained", "complaint", "complaints",
    "company", "companies", "issue", "issues", "problem", "problems",
    "please", "help", "still", "even", "like", "said", "told",
    # Domain noise — present in virtually every TransUnion complaint
    "transunion", "report", "credit", "account",
}


def extract_keywords(text: str) -> list:
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def score_narrative(narrative: str, keywords: list) -> int:
    narrative_lower = narrative.lower()
    return sum(1 for kw in keywords if kw in narrative_lower)


def _semantic_expand(pattern: str, narrative_df: pd.DataFrame, client: openai.OpenAI) -> pd.DataFrame:
    """
    When keyword match returns < SEMANTIC_THRESHOLD results, ask Haiku which
    narratives from the full company set are relevant to the pattern.
    Samples up to 500 to keep token usage bounded.
    """
    sample = narrative_df.sample(min(500, len(narrative_df)), random_state=42).reset_index(drop=True)
    indexed = [
        {"idx": i, "text": str(row["Consumer complaint narrative"])[:300]}
        for i, row in sample.iterrows()
    ]
    prompt = (
        f"You are filtering consumer complaints for relevance to a support pattern.\n\n"
        f"Pattern: \"{pattern}\"\n\n"
        f"Return a JSON array of index numbers (from the 'idx' field) for complaints "
        f"that are relevant to this pattern. Include any complaint that relates to the "
        f"same product area, issue type, or user problem — even if the wording differs.\n\n"
        f"Complaints:\n{json.dumps(indexed, indent=2)}\n\n"
        f"Return ONLY a JSON array of integers, e.g. [0, 3, 7, ...]"
    )
    response = client.chat.completions.create(
        model=FILTER_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    match = re.search(r'\[[\d,\s]*\]', raw)
    if not match:
        return pd.DataFrame()
    indices = json.loads(match.group())
    valid = [i for i in indices if 0 <= i < len(sample)]
    return sample.iloc[valid]


def load_and_filter(pattern: str, data_path: Path = None) -> tuple:
    """
    Load complaints CSV, filter for the target company and non-empty narratives,
    apply keyword matching against the user's pattern, enforce 2,000-row cap.

    Returns (filtered_df, metadata_dict).
    Raises FileNotFoundError, EnvironmentError, or ValueError on bad state.
    """
    path = data_path or DATA_PATH

    if not path.exists():
        raise FileNotFoundError(f"Complaints CSV not found at: {path}")

    print(f"  Loading {path.name}...")
    df = pd.read_csv(path, low_memory=False)

    # Step 1 — filter for target company
    company_df = df[df["Company"] == COMPANY].copy()
    total_company = len(company_df)
    print(f"  [{total_company:,}] total {COMPANY} complaints in dataset")

    # Step 2 — filter for non-empty narratives
    narrative_df = company_df[
        company_df["Consumer complaint narrative"].notna() &
        (company_df["Consumer complaint narrative"].str.strip() != "")
    ].copy()
    after_narrative = len(narrative_df)
    print(f"  [{after_narrative:,}] after removing complaints with no narrative")

    # Step 3 — keyword matching
    keywords = extract_keywords(pattern)
    if not keywords:
        raise ValueError(
            f"Could not extract any meaningful keywords from: \"{pattern}\"\n"
            "Please describe the support pattern using more specific terms."
        )
    print(f"  Keywords extracted: {keywords}")

    # Require at least 2 keyword matches when the query has 2+ keywords,
    # so a single generic word (e.g. "fees") can't flood results with off-topic complaints.
    min_score = 2 if len(keywords) >= 2 else 1

    narrative_df = narrative_df.copy()
    narrative_df["_score"] = narrative_df["Consumer complaint narrative"].apply(
        lambda x: score_narrative(str(x), keywords)
    )
    keyword_df = narrative_df[narrative_df["_score"] >= min_score].copy()
    after_keyword = len(keyword_df)
    print(f"  [{after_keyword:,}] after keyword filtering")

    # Step 4 — semantic expansion if keyword match is thin
    if after_keyword < SEMANTIC_THRESHOLD:
        print(
            f"  Keyword match returned {after_keyword} results (< {SEMANTIC_THRESHOLD}). "
            f"Running semantic expansion via {FILTER_MODEL}..."
        )
        if not os.environ.get("OPENROUTER_API_KEY"):
            raise EnvironmentError("OPENROUTER_API_KEY environment variable not set.")
        try:
            client = get_client()
            expanded = _semantic_expand(pattern, narrative_df, client)
            if len(expanded) > 0:
                keyword_df = (
                    pd.concat([keyword_df, expanded])
                    .drop_duplicates(subset=["Complaint ID"])
                    .copy()
                )
                after_keyword = len(keyword_df)
                print(f"  [{after_keyword:,}] after semantic expansion")
        except openai.AuthenticationError:
            raise EnvironmentError(
                "OPENROUTER_API_KEY is set but invalid. "
                "Check that the key is correct and active."
            )
        except Exception as e:
            print(f"  Semantic expansion failed ({type(e).__name__}: {e}). Continuing with keyword results only.")

    if after_keyword == 0:
        raise ValueError(
            f"No complaints found matching: \"{pattern}\"\n"
            f"No matching narratives in {after_narrative:,} {COMPANY} complaints. "
            "Try broader or different terms."
        )

    # Step 5 — parse dates, sort descending, cap at 2,000
    keyword_df["Date received"] = pd.to_datetime(
        keyword_df["Date received"], format="mixed", errors="coerce"
    )
    keyword_df = keyword_df.sort_values("Date received", ascending=False)

    filtered_out_by_cap = max(0, after_keyword - CAP)
    if after_keyword > CAP:
        keyword_df = keyword_df.head(CAP)
        print(
            f"  [{CAP:,}] used in analysis "
            f"(capped from {after_keyword:,} — {filtered_out_by_cap:,} older complaints excluded)"
        )
    else:
        print(f"  [{after_keyword:,}] used in analysis (no cap needed)")

    keyword_df = keyword_df.drop(columns=["_score"], errors="ignore").reset_index(drop=True)

    # Date range for brief metadata
    valid_dates = keyword_df["Date received"].dropna()
    date_start = valid_dates.min().strftime("%Y-%m-%d") if len(valid_dates) else "unknown"
    date_end = valid_dates.max().strftime("%Y-%m-%d") if len(valid_dates) else "unknown"

    metadata = {
        "total_company_complaints": total_company,
        "after_narrative_filter": after_narrative,
        "after_keyword_filter": after_keyword,
        "used_in_analysis": len(keyword_df),
        "filtered_out_by_cap": filtered_out_by_cap,
        "keywords": keywords,
        "company": COMPANY,
        "pattern": pattern,
        "date_start": date_start,
        "date_end": date_end,
    }

    return keyword_df, metadata
