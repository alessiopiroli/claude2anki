#!/usr/bin/env python3
"""Package an Anki .apkg from lecture-slide images + a cards.json spec.

Usage:
    python scripts/build_deck.py --pdf slides.pdf --cards cards.json --out deck.apkg
                                 [--dpi 200] [--workdir _slides]

cards.json format:
    {
      "deck_name": "My Deck",
      "cards": [
        {"front": "<b>Title:</b><br>- Q1<br>- Q2", "slides": ["slide-03.jpg"]},
        {"front": "<b>Combined topic:</b><br>- Q", "slides": ["slide-05.jpg", "slide-06.jpg"]}
      ]
    }

Each card's `slides` is a list of one or more rasterized page images. The Back of a
card is ONLY the slide image(s) (stacked, in order) — the questions are not repeated.
Rasterizes the PDF to <workdir>/slide-XX.jpg at the given DPI, builds notes with the
fixed custom model (templates + CSS from assets/), writes the package, then validates.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

import genanki

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
MODEL_ID = 1607392319  # fixed so re-imports update the same note type


def load(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
        return f.read()


def build_model():
    return genanki.Model(
        MODEL_ID,
        "claude2anki (Split Scratchpad)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{
            "name": "Card 1",
            "qfmt": load("front_template.html"),
            "afmt": load("back_template.html"),
        }],
        css=load("cards.css"),
    )


def deck_id_from_name(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) | 0x10000000


def rasterize(pdf, workdir, dpi):
    os.makedirs(workdir, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(dpi), pdf, os.path.join(workdir, "slide")],
        check=True,
    )


def validate(apkg, n_expected):
    z = zipfile.ZipFile(apkg)
    present = set(json.loads(z.read("media")).values())
    d = tempfile.mkdtemp()
    z.extract("collection.anki2", d)
    con = sqlite3.connect(os.path.join(d, "collection.anki2"))
    n = con.execute("select count(*) from notes").fetchone()[0]
    assert n == n_expected, f"note count {n} != expected {n_expected}"
    imgs = set()
    for (flds,) in con.execute("select flds from notes"):
        imgs.update(re.findall(r'<img src="([^"]+)"', flds))
    con.close()
    missing = imgs - present
    assert not missing, f"images referenced but not packaged: {missing}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--workdir", default="_slides")
    args = ap.parse_args()

    with open(args.cards, encoding="utf-8") as f:
        spec = json.load(f)
    deck_name = spec.get("deck_name", "Slides")
    cards = spec["cards"]

    rasterize(args.pdf, args.workdir, args.dpi)

    model = build_model()
    deck = genanki.Deck(deck_id_from_name(deck_name), deck_name)
    media = []
    for c in cards:
        front = c["front"]
        slides = c["slides"]
        if not slides:
            sys.exit(f"ERROR: a card has no slides: {front[:60]!r}")
        for s in slides:
            p = os.path.join(args.workdir, s)
            if not os.path.exists(p):
                sys.exit(f"ERROR: card references missing image {p}")
            media.append(p)
        back = "<br>".join(f'<img src="{s}">' for s in slides)
        deck.add_note(genanki.Note(model=model, fields=[front, back]))

    pkg = genanki.Package(deck)
    pkg.media_files = list(dict.fromkeys(media))  # de-dup, keep order
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    pkg.write_to_file(args.out)

    validate(args.out, len(cards))
    print(f"OK: wrote {len(cards)} cards -> {args.out}")


if __name__ == "__main__":
    main()
