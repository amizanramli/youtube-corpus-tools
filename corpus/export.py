"""
Writes, for one video's worth of comments, into the output dir:
  {base_name}.xlsx                             one row per comment, 9
                                                 columns — sits in the
                                                 output dir's root
  tagged/{base_name}/{comment_id}.txt           one XML-tagged file per
                                                 comment (NST-corpus style)
  plain/{base_name}/{comment_id}.txt            one tag-free file per comment
  plain/{base_name}/{base_name}_combined.txt    all of that video's comments
                                                 concatenated into one file

Everything under plain/ has no tags at all — for AntConc or other
concordancers, which otherwise read XML tag names as literal corpus words.
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import pandas as pd

COMMENT_COLS = [
    "comment_id", "video_id", "is_reply", "text", "timestamp",
    "like_count", "reply_count", "is_favourite", "is_pinned",
]

# metadata fields eligible to appear as <tag value="..." /> lines in the
# XML-tagged .txt — i.e. everything except the id (goes in the <comment>
# opening tag) and the text itself (goes in the body)
XML_META_FIELDS = [c for c in COMMENT_COLS if c not in ("comment_id", "text")]


def safe_filename(text: str, max_len: int = 60) -> str:
    """Strip characters that are unsafe in filenames."""
    text = re.sub(r'[\\/:*?"<>|]', "", str(text or ""))
    cleaned = text.strip()[:max_len]
    return cleaned or "untitled"


def comment_to_xml(comment: dict, meta_fields: list = None) -> str:
    """NST-corpus-style tagging: <comment id="..."> + metadata tags + body + ( END ).

    meta_fields: which metadata fields to include as <tag value="..." />
    lines, in order. Defaults to all of them (XML_META_FIELDS).
    """
    meta_cols = XML_META_FIELDS if meta_fields is None else meta_fields
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


def save_video_comments(output_dir: Path, base_name: str, comments: list,
                         xml_meta_fields: list = None):
    """
    comments: list of dicts, each with at least the COMMENT_COLS fields.
    xml_meta_fields: which metadata fields to include in the XML-tagged
    .txt files (see comment_to_xml). Defaults to all of them.

    Writes xlsx into output_dir/ (root); one XML txt per comment into
    output_dir/tagged/{base_name}/; and, into output_dir/plain/{base_name}/,
    one tag-free txt per comment plus one combined txt with all of that
    video's comments.
    Returns (xlsx_path, combined_plain_txt_path).
    """
    tagged_dir = output_dir / "tagged" / base_name
    plain_dir = output_dir / "plain" / base_name
    output_dir.mkdir(parents=True, exist_ok=True)
    tagged_dir.mkdir(parents=True, exist_ok=True)
    plain_dir.mkdir(parents=True, exist_ok=True)

    # ── Excel ──────────────────────────────────────────────────────────────
    df_c = pd.DataFrame(comments)[COMMENT_COLS]
    xlsx_path = output_dir / f"{base_name}.xlsx"
    df_c.to_excel(xlsx_path, index=False, engine="openpyxl")

    # ── XML-tagged txt, one file per comment ──────────────────────────────
    for c in comments:
        fname = f"{safe_filename(c.get('comment_id', ''))}.txt"
        (tagged_dir / fname).write_text(
            comment_to_xml(c, meta_fields=xml_meta_fields), encoding="utf-8"
        )

    # ── Plain-text txt, no tags, one file per comment ──────────────────────
    for c in comments:
        fname = f"{safe_filename(c.get('comment_id', ''))}.txt"
        (plain_dir / fname).write_text(str(c.get("text", "")), encoding="utf-8")

    # ── Plain-text txt, no tags, all comments for this video combined ─────
    plain_text = "\n\n".join(str(c.get("text", "")) for c in comments)
    plain_path = plain_dir / f"{base_name}_combined.txt"
    plain_path.write_text(plain_text, encoding="utf-8")

    return xlsx_path, plain_path


def build_base_name(video_id: str, title: str = "", upload_date: str = "") -> str:
    """'<date>_<title>_<video_id>', dropping any pieces that are missing.

    A blank title is dropped rather than turned into the literal word
    "untitled" — safe_filename's fallback for that is meant for filenames
    that can't be empty (e.g. per-comment files), not for this piece.
    """
    title = str(title).strip()
    title_part = safe_filename(title) if title and title.lower() != "nan" else ""
    parts = [p for p in (str(upload_date).strip(), title_part, str(video_id).strip())
             if p and p.lower() != "nan"]
    return "_".join(parts) if parts else "untitled_video"
