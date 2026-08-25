"""
Concordance tools over comment text: KWIC search, word frequency lists, and
collocates — the analyses AntConc would otherwise be used for, available
directly in the app without a separate export step.
"""

import re
from collections import Counter
from typing import Optional

import pandas as pd

TOKEN_RE = re.compile(r"[A-Za-z']+")

# Common English function words — enough to clean up a YouTube-comment
# frequency list without pulling in an NLP dependency.
STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll he's
her here here's hers herself him himself his how how's i i'd i'll i'm i've
if in into is isn't it it's its itself let's me more most mustn't my myself
no nor not of off on once only or other ought our ours ourselves out over
own same shan't she she'd she'll she's should shouldn't so some such than
that that's the their theirs them themselves then there there's these they
they'd they'll they're they've this those through to too under until up
very was wasn't we we'd we'll we're we've were weren't what what's when
when's where where's which while who who's whom why why's with won't would
wouldn't you you'd you'll you're you've your yours yourself yourselves
""".split())


def tokenize(text: str) -> list:
    return TOKEN_RE.findall(str(text or ""))


def kwic_search(rows, query: str, context_chars: int = 40,
                 case_sensitive: bool = False, whole_word: bool = True) -> pd.DataFrame:
    """
    rows: iterable of dicts with at least a 'text' key; any other keys
    (video_id, comment_id, ...) are carried through into the result.
    Returns one row per match: left context, match, right context, plus the
    row's other fields. Empty query returns an empty frame.
    """
    if not query:
        return pd.DataFrame(columns=["left", "match", "right"])

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(query)
    if whole_word:
        pattern = rf"\b{pattern}\b"
    regex = re.compile(pattern, flags)

    results = []
    for row in rows:
        text = str(row.get("text", ""))
        for m in regex.finditer(text):
            left = text[max(0, m.start() - context_chars):m.start()]
            right = text[m.end():m.end() + context_chars]
            entry = {k: v for k, v in row.items() if k != "text"}
            entry.update({"left": left.strip(), "match": m.group(0), "right": right.strip()})
            results.append(entry)
    return pd.DataFrame(results)


def word_frequencies(texts, remove_stopwords: bool = True, min_len: int = 1,
                      top_n: Optional[int] = None) -> pd.DataFrame:
    """Word frequency list across all given texts, most common first."""
    counts = Counter()
    for text in texts:
        for tok in tokenize(text):
            w = tok.lower()
            if len(w) < min_len:
                continue
            if remove_stopwords and w in STOPWORDS:
                continue
            counts[w] += 1
    return pd.DataFrame(counts.most_common(top_n), columns=["word", "count"])


def collocates(texts, node_word: str, window: int = 5,
               remove_stopwords: bool = True, top_n: Optional[int] = 30) -> pd.DataFrame:
    """Words co-occurring with node_word within `window` tokens either side."""
    node = node_word.lower().strip()
    counts = Counter()
    for text in texts:
        toks = [t.lower() for t in tokenize(text)]
        for i, t in enumerate(toks):
            if t != node:
                continue
            lo, hi = max(0, i - window), min(len(toks), i + window + 1)
            for j in range(lo, hi):
                if j == i:
                    continue
                w = toks[j]
                if remove_stopwords and w in STOPWORDS:
                    continue
                counts[w] += 1
    return pd.DataFrame(counts.most_common(top_n), columns=["word", "count"])
