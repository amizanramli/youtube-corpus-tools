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

from corpus.concordance import collocates, kwic_search, word_frequencies
from corpus.export import XML_META_FIELDS
from corpus.loader import CorpusLoadError, load_table
from corpus.pipeline import run_corpus_export
from corpus.tree import tree_string

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

with st.expander("\U0001F4D6 Tutorial — how to use this app", expanded=True):
    st.markdown(
        """
This app takes comments
you've already gathered from somewhere (a scraper, an export tool, a
manual copy-paste job) and turns them into files ready for corpus or
analysis, plus lets you explore them directly without needing
a separate concordancer.


### Step 1 — Upload comments
Upload a `.csv`, `.xlsx`/`.xls`, or `.json` file. Column names are
matched case-insensitively and a few common aliases are accepted (e.g.
`is_favorited` → `is_favourite`).

**Required columns:** `comment_id`, `video_id`, `is_reply`, `text`,
`timestamp`, `like_count`, `reply_count`, `is_favourite`, `is_pinned`.

**Optional columns** (used only to name output folders/files nicely):
`title` (or `video_title`), `upload_date` (or `date`). Without these,
folders are just named by `video_id`.

### Step 2 — Concordance tools
Once comments are uploaded, explore them right in the app — scoped to
one video or all of them at once:

- **KWIC search** — find a word or phrase and see it in context, with
  adjustable context width, whole-word matching, and case sensitivity.
- **Word frequency** — the most common words, with optional stopword
  removal and a minimum word length.
- **Collocates** — words that co-occur near a word you specify, within
  an adjustable window.

Every tab's results can be downloaded as CSV. This step doesn't require
generating any files first — it works straight off the uploaded data.

### Step 3 — Generate corpus files
Pick an output folder, choose which metadata fields should appear as tags
in the XML-tagged `.txt` files (the `.xlsx` and plain-text output always
include every field regardless of this choice), then click **Generate**.
This writes, for every video in your data:

- `{video}.xlsx` in the output folder's root — all comments, 9 columns.
- `tagged/{video}/{comment_id}.txt` — one XML-tagged file per comment:
  `<comment id="...">`, metadata tags, the comment
  text, `( END )`).
- `plain/{video}/{comment_id}.txt` — the same comment with no markup
  at all.
- `plain/{video}/{video}_combined.txt` — all of that video's comments
  concatenated into one file, one per paragraph.

Re-running Generate for the same video replaces its output
rather than merging with whatever was there before.

### Step 4 — Download
A **Preview folder structure** panel shows the output as a tree so you can
see what you're getting before downloading. Click the download button to
get everything as a single `.zip`.
"""
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

# ── Step 2: concordance tools ──────────────────────────────────────────────────────────
st.header("2\uFE0F\u20E3 Concordance tools")

if st.session_state.df is None:
    st.info("Upload a comments file above first.")
else:
    df = st.session_state.df
    video_options = ["All videos"] + sorted(df["video_id"].astype(str).unique().tolist())
    video_choice = st.selectbox("Video", video_options)
    scoped = df if video_choice == "All videos" else df[df["video_id"].astype(str) == video_choice]
    texts = scoped["text"].tolist()

    tab_kwic, tab_freq, tab_collo = st.tabs(
        ["\U0001F50D KWIC search", "\U0001F4CA Word frequency", "\U0001F517 Collocates"]
    )

    with tab_kwic:
        col1, col2, col3 = st.columns([3, 1, 1])
        query = col1.text_input("Search word or phrase", key="kwic_query")
        context_chars = col2.slider("Context (chars)", 10, 100, 40)
        whole_word = col3.checkbox("Whole word", value=True)
        case_sensitive = st.checkbox("Case sensitive", value=False)

        if query:
            rows = scoped[["comment_id", "video_id", "text"]].to_dict(orient="records")
            kwic_df = kwic_search(rows, query, context_chars=context_chars,
                                   case_sensitive=case_sensitive, whole_word=whole_word)
            if kwic_df.empty:
                st.info(f"No matches for '{query}'.")
            else:
                st.caption(f"{len(kwic_df)} match(es)")
                st.dataframe(kwic_df[["left", "match", "right", "video_id", "comment_id"]],
                             use_container_width=True, height=300)
                st.download_button("\u2B07\uFE0F Download matches (CSV)",
                                    kwic_df.to_csv(index=False), file_name="kwic_results.csv",
                                    mime="text/csv")
        else:
            st.caption("Enter a word or phrase above to see it in context.")

    with tab_freq:
        col1, col2, col3 = st.columns(3)
        remove_sw = col1.checkbox("Remove stopwords", value=True, key="freq_sw")
        min_len = col2.number_input("Min word length", min_value=1, max_value=10, value=2)
        top_n = col3.number_input("Show top N", min_value=5, max_value=500, value=30)

        freq_df = word_frequencies(texts, remove_stopwords=remove_sw,
                                    min_len=min_len, top_n=top_n)
        if freq_df.empty:
            st.info("No words to count yet.")
        else:
            st.bar_chart(freq_df.set_index("word")["count"])
            st.dataframe(freq_df, use_container_width=True, height=300)
            st.download_button("\u2B07\uFE0F Download word list (CSV)",
                                freq_df.to_csv(index=False), file_name="word_frequencies.csv",
                                mime="text/csv")

    with tab_collo:
        col1, col2, col3 = st.columns(3)
        node_word = col1.text_input("Node word", key="collo_node")
        window = col2.slider("Window (words each side)", 1, 10, 5)
        remove_sw_c = col3.checkbox("Remove stopwords", value=True, key="collo_sw")

        if node_word:
            collo_df = collocates(texts, node_word, window=window,
                                   remove_stopwords=remove_sw_c)
            if collo_df.empty:
                st.info(f"No collocates found for '{node_word}'.")
            else:
                st.dataframe(collo_df, use_container_width=True, height=300)
                st.download_button("\u2B07\uFE0F Download collocates (CSV)",
                                    collo_df.to_csv(index=False), file_name="collocates.csv",
                                    mime="text/csv")
        else:
            st.caption("Enter a node word above to see its collocates.")

# ── Step 3: generate corpus files ────────────────────────────────────────────────────
st.header("3\uFE0F\u20E3 Generate corpus files")

output_dir = st.text_input("Output folder", value="corpus_output")

xml_fields = st.multiselect(
    "Metadata fields to include in the XML-tagged .txt files",
    options=XML_META_FIELDS,
    default=XML_META_FIELDS,
    help="Applies to the per-comment <comment_id>.txt files. The .xlsx and "
         "the plain, tag-free .txt always include every field.",
)

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
                    st.session_state.df, output_dir, log=log, progress=progress_cb,
                    xml_meta_fields=xml_fields,
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

# ── Step 4: download ─────────────────────────────────────────────────────────────────
st.header("4\uFE0F\u20E3 Download")

out_path = Path(output_dir)
if out_path.exists() and any(out_path.iterdir()):
    with st.expander("\U0001F4C1 Preview folder structure", expanded=True):
        st.code(tree_string(out_path), language=None)

    # Build the zip once per output (cached in session state so it isn't
    # rebuilt on every rerun) and offer it directly \u2014 no separate "prepare"
    # click. A fresh Generate resets zip_path to None, so it's rebuilt then.
    if not st.session_state.zip_path or not Path(st.session_state.zip_path).exists():
        zip_base = Path(f"{output_dir}_export")
        zip_path = zip_base.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(zip_base), "zip", out_path)
        st.session_state.zip_path = str(zip_path)

    with open(st.session_state.zip_path, "rb") as f:
        st.download_button(
            "\u2B07\uFE0F Download all corpus files (.zip)",
            f, file_name=Path(st.session_state.zip_path).name, mime="application/zip",
        )
else:
    st.info("Nothing generated yet \u2014 run Step 3 first.")
