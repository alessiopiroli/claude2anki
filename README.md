# claude2anki

Turn a PDF of lecture slides into an Anki deck you can actually study from.

Claude reads the slides, writes a question for each one, and packages everything into an `.apkg`. The front of a card holds the questions plus a scratchpad you can type LaTeX into while you think. The back is just the slide itself, so the source material stays the answer and nothing gets paraphrased into something subtly wrong.

## How it works

The skill does three things in order. It reads the PDF and decides which slides carry real content, skipping title pages, tables of contents, section dividers and reference lists. It writes a `cards.json` describing each card: a topic title, a few questions, and the slides that card covers. Then `build_deck.py` rasterizes the PDF at 200 DPI, builds the notes, embeds the images and validates the result before handing you the deck.

Related slides can be merged into a single card when they cover one idea, so a 60 page deck does not necessarily become 60 cards.

## Requirements

`genanki` for packaging and `pdftoppm` (from poppler) for rasterizing.

```
pip install genanki
brew install poppler        # macOS
apt install poppler-utils   # Debian or Ubuntu
```

## Usage

Point Claude at a slides PDF and ask for Anki cards. If you already have a `cards.json`, run the packager yourself:

```
python scripts/build_deck.py --pdf slides.pdf --cards cards.json --out deck.apkg
```

`--dpi` and `--workdir` are available if you want sharper images or a different scratch directory. The card spec format is documented in `cards.example.json`.

## Layout

```
SKILL.md               instructions Claude follows
assets/                card templates and CSS
scripts/build_deck.py  rasterize, package, validate
cards.example.json     sample card spec
tests/                 tests and the sample lecture deck
```

The templates in `assets/` are load bearing. A stray character in the HTML or CSS will break how every card renders, so change them deliberately and check a card in Anki afterwards.

## Tests

The tests cover the packaging half of the project: given a PDF and a card spec, does the right `.apkg` come out. They never call a model, so they need no API key and run in about a second.

```
pip install genanki pytest
pytest
```

They run against `tests/fixtures/sample_lecture.pdf`, a six slide lecture on eigenvalues written for this repo. It is the one PDF that lives in the repo, and it is here rather than downloaded so the suite works offline. Regenerate it with `python tests/fixtures/make_sample_pdf.py`, which uses only the standard library.

## What is not committed

Source PDFs, rasterized slide images, generated `cards.json` files and built `.apkg` files are all gitignored. The slides are usually someone else's intellectual property and the artifacts are large, so this repo holds only the machinery that produces them. The sample lecture under `tests/fixtures` is the deliberate exception.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md). You can use, modify and share this freely for any noncommercial purpose, including study, research and teaching. Selling it, or building a paid product on top of it, needs my permission. Copyright stays with me.
