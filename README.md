# Corpus Export Tools

A Streamlit app that takes comments you've **already collected** (from
wherever) and formats them for corpus/linguistic analysis — no scraping
involved.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Try it immediately with the included
sample file: `sample_data/sample_comments.csv`.

## Input format

Upload a CSV, Excel (`.xlsx`/`.xls`), or JSON file containing your comments.
Required columns (case-insensitive; a couple of common aliases are accepted,
e.g. `is_favorited` → `is_favourite`):

- `comment_id`
- `video_id`
- `is_reply`
- `text`
- `timestamp`
- `like_count`
- `reply_count`
- `is_favourite`
- `is_pinned`

Optional columns, used only to name output folders/files nicely:

- `title` (or `video_title`)
- `upload_date` (or `date`)

If `title`/`upload_date` are missing, folders are just named by `video_id`.

JSON input can be either a flat list of comment objects, or an object with
a top-level `"comments"` list, or an object with a `"videos"` list where
each video has its own nested `"comments"` list (matches common scraper
export shapes).

## Output

For **each video** in the uploaded data, a folder is created:

```
corpus_output/
└── 20260103_My Video One_AAA111/
    ├── 20260103_My Video One_AAA111.xlsx        ← all comments, 9 columns
    ├── 20260103_My Video One_AAA111_plain.txt   ← all comments, plain text, no tags
    ├── Ugz1abc.txt                               ← one comment, XML-tagged
    └── Ugz2def.txt
```

**XML-tagged comment format** (`<comment_id>.txt`):

```xml
<comment id="Ugz1abc">
	<video_id value="AAA111" />
	<is_reply value="False" />
	<timestamp value="1700000000" />
	<like_count value="12" />
	<reply_count value="1" />
	<is_favourite value="False" />
	<is_pinned value="True" />

Great video! Thanks &amp; keep it up &lt;3

( END )

</comment>
```

**Plain-text format** (`<video>_plain.txt`) — just the raw comment text for
that video, one comment per paragraph, blank line between each, no markup
at all. This is the one to load into AntConc or any other concordancer,
since those tools otherwise read XML tag names and attributes as if they
were corpus words.

## Project layout

```
corpus-tools/
├── app.py                 # Streamlit UI
├── corpus/
│   ├── loader.py            # reads + normalizes CSV/Excel/JSON input
│   ├── export.py            # writes xlsx / XML-txt / plain-txt per video
│   └── pipeline.py          # groups by video, calls export for each
├── sample_data/
│   └── sample_comments.csv  # try the app immediately with this
├── requirements.txt
└── corpus_output/           # created at runtime, gitignored
```
