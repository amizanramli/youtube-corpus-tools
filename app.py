"""
Corpus Export Tools — Streamlit UI

Takes a table of comments you already have (CSV, Excel, or JSON) and turns
it into corpus-ready files, one folder per video:

  <video>.xlsx            all comments for that video, 9 columns
  <comment_id>.txt         one XML-tagged file per comment
  <video>_plain.txt        all of that video's comments, plain text, no
                            tags at all — for AntConc / other concordancers,
                            which otherwise read XML tags as literal words

Run with:
    streamlit run app.py
"""

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from corpus.loader import CorpusLoadError, load_table
from corpus.pipeline import run_corpus_export

st.set_page_config(page_title="Corpus Export Tools", page_icon="\U0001F4C4", layout="wide")

for key, default in [("df", None), ("logs", []), ("result", None), ("zip_path", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


def log(msg: str):
    st.session_state.logs.append(str(msg))


st.title("\U0001F4C4 Corpus Export Tools")
st.caption(
    "Upload comments you've already collected (CSV / Excel / JSON) and export "
    "them per video as Excel, XML-tagged .txt (one per comment), and a "
    "plain, tag-free .txt for corpus tools like AntConc."
)

# ── Step 1: upload & preview ────────────────────────────────────────────────
st.header("1\uFE0F\u20E3 Upload comments")

st.markdown(
    "Required columns (case-insensitive; a couple of common aliases are "
    "accepted, e.g. `is_favorited` \u2192 `is_favourite`): "
    "`comment_id`, `video_id`, `is_reply`, `text`, `timestamp`, "
    "`like_count`, `reply_count`, `is_favourite`, `is_pinned`.\n\n"
    "Optional columns, used only to name folders/files: `title`, `upload_date`."
)

uploaded = st.file_uploader("Comments file", type=["csv", "xlsx", "xls", "json"])

if uploaded is not None:
    try:
        df = load_table(uploaded, uploaded.name)
        st.session_state.df = df
        st.success(f"Loaded {len(df)} comments across "
                   f"{df['video_id'].nunique()} video(s).")
    except CorpusLoadError as e:
        st.error(str(e))
        st.session_state.df = None
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        st.session_state.df = None

if st.session_state.df is not None:
    st.dataframe(st.session_state.df, use_container_width=True, height=250)

# ── Step 2: generate ─────────────────────────────────────────────────────────
st.header("2\uFE0F\u20E3 Generate corpus files")

output_dir = st.text_input("Output folder", value="corpus_output")

if st.session_state.df is None:
    st.info("Upload a comments file above first.")
else:
    if st.button("Generate", type="primary"):
        st.session_state.logs = []
        progress_bar = st.progress(0.0)
        status = st.empty()

        def progress_cb(i, n):
            progress_bar.progress(i / n if n else 1.0)
            status.text(f"{i}/{n} videos processed")

        with st.spinner("Writing corpus files..."):
            try:
                result = run_corpus_export(
                    st.session_state.df, output_dir, log=log, progress=progress_cb
                )
                st.session_state.result = result
                st.session_state.zip_path = None  # invalidate any previous zip
                st.success(
                    f"Done \u2014 {result['total_comments']} comments written across "
                    f"{len(result['video_results'])} video folder(s)."
                )
            except Exception as e:
                st.error(f"Failed: {e}")

    if st.session_state.result:
        st.dataframe(pd.DataFrame(st.session_state.result["video_results"]),
                     use_container_width=True)

    with st.expander("Log"):
        st.code("\n".join(st.session_state.logs) or "(no logs yet)")

# ── Step 3: download ─────────────────────────────────────────────────────────
st.header("3\uFE0F\u20E3 Download")

out_path = Path(output_dir)
if out_path.exists() and any(out_path.iterdir()):
    if st.button("Prepare zip"):
        zip_base = Path(f"{output_dir}_export")
        zip_path = zip_base.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(zip_base), "zip", out_path)
        st.session_state.zip_path = str(zip_path)

    if st.session_state.zip_path and Path(st.session_state.zip_path).exists():
        with open(st.session_state.zip_path, "rb") as f:
            st.download_button(
                "\u2B07\uFE0F Download all corpus files (.zip)",
                f, file_name=Path(st.session_state.zip_path).name, mime="application/zip",
            )
else:
    st.info("Nothing generated yet \u2014 run Step 2 first.")
