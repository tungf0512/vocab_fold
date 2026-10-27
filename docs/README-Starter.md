# FoldLex — IELTS Vocabulary Notebook

**A working, offline-first two-column vocabulary website.** Built to mimic a folded sheet of paper: `Words | Explanation`.

## Start in 10 seconds

1. Open `index.html` in Chrome, Edge, Firefox or Safari.
2. Choose **Morning Reading** to see both columns.
3. Choose **Folded Recall** to hide all explanations. Try to remember; click *Tap to reveal meaning* only when needed.
4. Click **Got it** or **Again** to record a review and schedule the next one.

Nothing needs to be installed and no account is necessary. All CSS, JavaScript and starter vocabulary are embedded in `index.html`; the website works offline. Speech playback relies on your browser/device voices. Optional dictionary lookup requires the internet.

## What's included

- **514 original starter entries** with English explanations (some entries are multiword expressions).
- Six **unofficial study groups:** 4.0 (68), 5.0 (87), 6.0 (100), 7.0 (116), 8.0 (92), 9.0 (51).
- Topic and band filters, instant word/definition search, daily selection and shuffle.
- Morning Reading / Folded Recall, optional single-card focus view.
- Bookmarks, a **Needs practice** collection, pronunciation via browser speech synthesis.
- **Spaced repetition:** successful reviews are due in approximately 1, 3, 7, 14, 30 and 60 days; *Again* marks the word as due today. This is a simple heuristic, not a validated memory model.
- Streak and weekly review statistics.
- Add personal words and fetch suggested definitions from Free Dictionary API if online.
- Import vocabulary from CSV/TSV; export all vocabulary in CSV; save/restore personal words and study progress in JSON.
- Responsive layout for desktop and mobile.

## Import your own words

In the website, click the **import/export** icon above your paper sheet or the **Import / Export** footer link. Import a `.csv` file in this format:

```csv
Word,Explanation,Band,Topic
foster,"To encourage the development of something.",7,Education
alleviate,"To make pain or difficulties less severe.",7,Health
"renewable energy","Power from sources that replenish naturally.",6,Environment
```

`Definition` also works as the heading instead of `Explanation`, and `Explaination` (a common misspelling) is accepted. A single import handles up to 20,000 rows / 16 MB. Larger personal corpora should be broken into files, but the browser's local storage still imposes an overall capacity limit (often around 5 MB). **This is not a million-word database.** Do not assume it can store one million records.

**Tip:** Keep occasional JSON backups. Progress is saved to *this browser/device* using localStorage; it does not sync between devices or in private browsing.

## Important note on IELTS bands

IELTS does **not** publish an official per-word band grading system. The band numbers in this application are **approximate educational groupings** based on usefulness and lexical sophistication, not certified CEFR classifications or guarantees of an IELTS score. Knowing individual complex words is not enough for high scores: precision, collocations, grammatical fit and natural context also matter.

Official context:
- British Council: https://takeielts.britishcouncil.org/blog/vocabulary-for-ielts
- IELTS writing lexical resource: https://ielts.org/take-a-test/preparation-resources/writing-test-resources/

All 514 explanations were written for this starter collection. A single explanation does not cover all meanings, collocations or pronunciations.

## Host it online

Because this is a static website, upload `index.html` to any static web host (for example GitHub Pages, Netlify, Vercel or Cloudflare Pages). No build step or API key is required. The website stores progress locally even when hosted online. It will not sync across browsers/devices without an added backend.

You can also run a simple local server if your browser restricts storage on `file://` pages:

```bash
cd folder-containing-index
python -m http.server 8000
# Open http://localhost:8000
```

If you switch from a `file://` URL to a `localhost` or hosted URL, those are different browser storage origins; use JSON export/import to transfer your progress.
