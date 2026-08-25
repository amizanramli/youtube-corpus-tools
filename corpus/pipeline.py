"""Groups a normalized comments DataFrame by video_id and writes corpus
files for each video."""

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from . import export as ex


def run_corpus_export(df: pd.DataFrame, output_dir: str,
                       log: Callable[[str], None] = print,
                       progress: Optional[Callable[[int, int], None]] = None,
                       xml_meta_fields: Optional[list] = None) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    video_ids = list(dict.fromkeys(df["video_id"].tolist()))  # preserve order, dedupe
    n = len(video_ids)
    results = []

    for i, vid in enumerate(video_ids, start=1):
        sub = df[df["video_id"] == vid]
        title = sub["title"].iloc[0] if "title" in sub.columns else ""
        upload_date = sub["upload_date"].iloc[0] if "upload_date" in sub.columns else ""

        base_name = ex.build_base_name(vid, title, upload_date)

        comments = sub.to_dict(orient="records")
        log(f"[{i}/{n}] {base_name}  ({len(comments)} comments)")

        xlsx_path, plain_path = ex.save_video_comments(
            out, base_name, comments, xml_meta_fields=xml_meta_fields
        )
        results.append({
            "video_id": vid, "title": title, "n_comments": len(comments),
            "tagged_folder": str(xlsx_path.parent),
            "plain_folder": str(plain_path.parent),
        })

        if progress:
            progress(i, n)

    log(f"\nDone \u2014 {len(df)} comments written across {n} video folder(s) in '{out}/'")
    return {"video_results": results, "total_comments": len(df), "output_dir": out}
