"""
Loads a comments table from CSV, Excel, or JSON and normalizes it to the
9 required fields (plus optional video-title/date columns used only for
naming output folders).

Required fields (case-insensitive, a few common aliases accepted):
    comment_id, video_id, is_reply, text, timestamp,
    like_count, reply_count, is_favourite (or is_favorited), is_pinned

Optional fields, used only to build nicer folder/file names:
    title / video_title
    upload_date / date
"""

import json
from io import BytesIO
from pathlib import Path
from typing import Union

import pandas as pd

REQUIRED_COLS = [
    "comment_id", "video_id", "is_reply", "text", "timestamp",
    "like_count", "reply_count", "is_favourite", "is_pinned",
]

# alternate spellings/casings we'll accept and rename to the canonical name
ALIASES = {
    "is_favorited": "is_favourite",
    "commentid": "comment_id",
    "videoid": "video_id",
    "isreply": "is_reply",
    "likecount": "like_count",
    "replycount": "reply_count",
    "isfavourite": "is_favourite",
    "isfavorited": "is_favourite",
    "ispinned": "is_pinned",
}

TITLE_ALIASES = ["title", "video_title", "videotitle"]
DATE_ALIASES = ["upload_date", "date", "uploaddate", "published_at", "publishedat"]


class CorpusLoadError(ValueError):
    pass


def _normalize_colname(c: str) -> str:
    return c.strip().lower().replace(" ", "_").replace("-", "_")


def load_table(file, filename: str) -> pd.DataFrame:
    """
    file: a file-like object (e.g. Streamlit UploadedFile) or a path.
    filename: original filename, used to pick the parser by extension.
    """
    ext = Path(filename).suffix.lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file, dtype=str, engine="openpyxl" if ext == ".xlsx" else None)
    elif ext == ".csv":
        df = pd.read_csv(file, dtype=str)
    elif ext == ".json":
        raw = file.read() if hasattr(file, "read") else Path(file).read_bytes()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        # accept either a flat list of comment dicts, or {"videos": [...]}-style
        # wrappers containing a nested comments list per video.
        if isinstance(data, dict) and "comments" in data:
            data = data["comments"]
        elif isinstance(data, dict) and "videos" in data:
            rows = []
            for v in data["videos"]:
                for c in v.get("comments", []):
                    rows.append(c)
            data = rows
        df = pd.DataFrame(data)
    else:
        raise CorpusLoadError(f"Unsupported file type: {ext or '(no extension)'}")

    return normalize_table(df)


def normalize_table(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names and validate required fields exist."""
    rename_map = {}
    for c in df.columns:
        key = _normalize_colname(c)
        if key in ALIASES:
            rename_map[c] = ALIASES[key]
        elif key in REQUIRED_COLS:
            rename_map[c] = key
        elif key in TITLE_ALIASES:
            rename_map[c] = "title"
        elif key in DATE_ALIASES:
            rename_map[c] = "upload_date"
    df = df.rename(columns=rename_map)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise CorpusLoadError(
            "Missing required column(s): " + ", ".join(missing) +
            ". Found columns: " + ", ".join(map(str, df.columns))
        )

    # keep required + optional naming columns, drop everything else
    keep = REQUIRED_COLS + [c for c in ("title", "upload_date") if c in df.columns]
    df = df[keep].copy()

    # normalize booleans that may have arrived as strings ("True"/"False"/"1"/"0")
    for col in ("is_reply", "is_favourite", "is_pinned"):
        df[col] = df[col].apply(_to_bool)

    return df


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y")
