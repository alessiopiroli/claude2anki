---
name: claude2anki
description: "Use when the user wants to generate Anki flashcards (.apkg) from a PDF of lecture slides. Produces one card per content slide (merging several related slides into one card when appropriate), using a fixed custom template with a split-scratchpad front and a back that shows only the slide screenshot(s). Triggers: 'Anki cards from these slides', 'make flashcards from this lecture PDF', 'build an .apkg from slides', or any request pairing slide decks with genanki/Anki."
---

# claude2anki

Turn a PDF of lecture slides into an importable Anki `.apkg`, one card per content slide.

## Workflow

1. Read the PDF and understand each slide's content (render pages if needed).
2. Decide the card set using the Style and Skip rules below. Default to one card per content slide, but merge several slides into a single card whenever they cover the same topic — there is no limit of two.
3. Write `cards.json`:
   `{"deck_name": "...", "cards": [{"front": "<b>Title:</b><br>- Q1<br>- Q2", "slides": ["slide-03.jpg"]}, ...]}`
   - `slides` is a list; page N maps to `slide-NN.jpg` (zero-padded to 2 digits, so page 3 is `slide-03.jpg`). A merged card lists every slide it covers, in order. The packager normalizes the rasterized filenames to this form and accepts either padding, so write `slide-03.jpg` regardless of how long the deck is.
4. Run the packager:
   `python scripts/build_deck.py --pdf <slides.pdf> --cards cards.json --out <deck>.apkg`
   It rasterizes at 200 DPI, builds each card with the fixed model, and validates.
5. Give the user the `.apkg`. Never commit the PDF, the slide images, `.apkg` files, or `cards.json` (all gitignored).

## Front style (match exactly)
- A bold topic title, then sub-questions as `<br>- ...` bullet lines.
- Questions should test understanding of the slide content.
- Use `\(...\)` for inline LaTeX math.

## Back (auto-generated — never hand-write)
The back is ONLY the slide screenshot(s): `<img src="slide-XX.jpg">`, one per slide the card covers, stacked in order. The questions are NOT repeated on the back. `build_deck.py` builds this from each card's `slides` list.

## Skip these slides
Title pages, tables of contents, section/transition dividers, reference lists, and any slide with no meaningful exam content.

## Notes
- Templates and CSS live in `assets/`; do not edit casually — a single stray character breaks card rendering.
- The packager validates note count and that every referenced image is embedded. If it errors, fix `cards.json` and re-run.
- Requires `genanki` (`pip install genanki`) and `pdftoppm` (poppler-utils) on PATH.
