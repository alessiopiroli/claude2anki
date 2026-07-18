# claude2anki

A Claude skill that turns a PDF of lecture slides into an Anki `.apkg` deck — one card per content slide (related slides can be merged into a single card), using a custom split-scratchpad template whose back shows only the slide screenshot(s).

## Use

With this skill available, point Claude at a slides PDF and ask for Anki cards. Or run the packager directly:

    pip install genanki
    python scripts/build_deck.py --pdf slides.pdf --cards cards.json --out deck.apkg

Requires `pdftoppm` (poppler-utils) on PATH. See `cards.example.json` for the `cards.json` format.

## Layout

- `SKILL.md` — the instructions Claude follows
- `assets/` — card templates and CSS (edit with care)
- `scripts/build_deck.py` — rasterize + package + validate

Source PDFs, generated slide images, `cards.json`, and `.apkg` files are gitignored and never committed.
