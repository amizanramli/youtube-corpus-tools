"""
Writes, for one video's worth of comments, into a per-video folder:
  - {base_name}.xlsx        one row per comment, 9 columns
  - {comment_id}.txt        one XML-tagged file per comment (NST-corpus style)
  - {base_name}_plain.txt   all comment text concatenated, no tags at all
                             (for AntConc / other concordancers, which
                             otherwise read XML tags as literal words)
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import pandas as pd

COMMENT_COLS = [
    "comment_id", "video_id", "is_reply", "text", "timestamp",
    "like_count", "reply_count", "is_favourite", "is_pinned",
]


def safe_filename(text: str, max_len: int = 60) -> str:
    """Strip characters that are unsafe in filenames."""
    text = re.sub(r'[\\/:*?"<>|]', "", str(text or ""))
    cleaned = text.strip()[:max_len]
    return cleaned or "untitled"


def comment_to_xml(comment: dict) -> str:
    """NST-corpus-style tagging: <comment id="..."> + metadata tags + body + ( END )."""
    meta_cols = [c for c in COMMENT_COLS if c not in ("comment_id", "text")]
    lines = [f"<comment id={quoteattr(str(comment.get('comment_id', '')))}>"]
    for col in meta_cols:
        lines.append(f"\t<{col} value={quoteattr(str(comment.get(col, '')))} />")
    lines.append("")
    lines.append(escape(str(comment.get("text", ""))))
    lines.append("")
    lines.append("( END )")
    lines.append("")
    lines.append("</comment>")
    return "\n".join(lines)


def save_video_comments(video_dir: Path, base_name: str, comments: list):
    """
    comments: list of dicts, each with at least the COMMENT_COLS fields.
    Writes xlsx + one XML txt per comment + one plain txt for the whole video.
    Returns (xlsx_path, plain_txt_path).
    """
    video_dir.mkdir(parents=True, exist_ok=True)

    # ── Excel ──────────────────────────────────────────────────────────────
    df_c = pd.DataFrame(comments)[COMMENT_COLS]
    xlsx_path = video_dir / f"{base_name}.xlsx"
    df_c.to_excel(xlsx_path, index=False, engine="openpyxl")

    # ── XML-tagged txt, one file per comment ──────────────────────────────
    for c in comments:
        fname = f"{safe_filename(c.get('comment_id', ''))}.txt"
        (video_dir / fname).write_text(comment_to_xml(c), encoding="utf-8")

    # ── Plain-text txt, no tags, all comments for this video in one file ──
    plain_text = "\n\n".join(str(c.get("text", "")) for c in comments)
    plain_path = video_dir / f"{base_name}_plain.txt"
    plain_path.write_text(plain_text, encoding="utf-8")

    return xlsx_path, plain_path


def build_base_name(video_id: str, title: str = "", upload_date: str = "") -> str:
    """'<date>_<title>_<video_id>', dropping any pieces that are missing."""
    parts = [p for p in (str(upload_date).strip(), safe_filename(title), str(video_id).strip())
             if p and p.lower() != "nan"]
    return "_".join(parts) if parts else "untitled_video"
