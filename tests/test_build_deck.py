"""Tests for the packaging half of claude2anki.

These never call a model. They feed build_deck.py a fixture PDF and a cards.json
written here, then check the .apkg that comes out. What Claude decides to put on a
card is not tested; what the script does with that decision is.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "build_deck.py")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample_lecture.pdf")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_deck  # noqa: E402


def run_packager(tmp_path, cards, out="deck.apkg", dpi=50):
    """Run build_deck.py end to end against the fixture deck."""
    cards_path = tmp_path / "cards.json"
    cards_path.write_text(json.dumps(cards), encoding="utf-8")
    apkg = tmp_path / out
    proc = subprocess.run(
        [sys.executable, SCRIPT,
         "--pdf", FIXTURE,
         "--cards", str(cards_path),
         "--out", str(apkg),
         "--dpi", str(dpi),
         "--workdir", str(tmp_path / "_slides")],
        capture_output=True, text=True,
    )
    return proc, apkg


def notes_in(apkg, tmp_path):
    """Return (fields, packaged media names) from a built .apkg."""
    z = zipfile.ZipFile(apkg)
    media = set(json.loads(z.read("media")).values())
    d = tmp_path / "unpacked"
    d.mkdir(exist_ok=True)
    z.extract("collection.anki2", d)
    con = sqlite3.connect(d / "collection.anki2")
    rows = [r[0].split("\x1f") for r in con.execute("select flds from notes")]
    con.close()
    return rows, media


# --- the note type -------------------------------------------------------------

def test_model_builds_from_assets():
    """Catches an asset file that was renamed or deleted out from under the script."""
    model = build_deck.build_model()
    assert [f["name"] for f in model.fields] == ["Front", "Back"]


def test_templates_reference_their_fields():
    """A template missing its placeholder renders blank cards and raises no error."""
    front = build_deck.load("front_template.html")
    back = build_deck.load("back_template.html")
    assert "{{Front}}" in front
    assert "{{Back}}" not in front, "the answer must not leak onto the question side"
    assert "{{Front}}" in back and "{{Back}}" in back


def test_deck_id_is_stable():
    """If this drifts, re-imports fork into a duplicate deck instead of updating."""
    assert build_deck.deck_id_from_name("Example Deck") == 4171567930


# --- rasterizing ---------------------------------------------------------------

def test_rasterize_pads_short_decks_to_two_digits(tmp_path):
    """pdftoppm names a 6 page deck slide-1.jpg; cards.json is written expecting
    slide-01.jpg, so rasterize has to normalise."""
    workdir = tmp_path / "_slides"
    build_deck.rasterize(FIXTURE, str(workdir), 50)
    names = sorted(p.name for p in workdir.iterdir())
    assert names == [f"slide-0{n}.jpg" for n in range(1, 7)]


def test_resolve_slide_accepts_either_padding(tmp_path):
    workdir = tmp_path / "_slides"
    build_deck.rasterize(FIXTURE, str(workdir), 50)
    assert build_deck.resolve_slide(str(workdir), "slide-3.jpg") == \
           build_deck.resolve_slide(str(workdir), "slide-03.jpg")
    assert build_deck.resolve_slide(str(workdir), "slide-99.jpg") is None


# --- end to end ----------------------------------------------------------------

def test_builds_importable_deck(tmp_path):
    proc, apkg = run_packager(tmp_path, {
        "deck_name": "Test Deck",
        "cards": [
            {"front": "<b>Definition:</b><br>- What is an eigenvalue?",
             "slides": ["slide-03.jpg"]},
            {"front": "<b>Diagonalisation:</b><br>- Why is A^k cheap?",
             "slides": ["slide-04.jpg", "slide-05.jpg"]},
        ],
    })
    assert proc.returncode == 0, proc.stderr
    rows, media = notes_in(apkg, tmp_path)
    assert len(rows) == 2
    # every image referenced on a back is actually inside the package
    for _front, back in rows:
        for src in re.findall(r'<img src="([^"]+)"', back):
            assert src in media
    # a merged card stacks its slides in the order given
    assert rows[1][1] == '<img src="slide-04.jpg"><br><img src="slide-05.jpg">'


def test_back_holds_only_slides(tmp_path):
    """The back is the slide, never a restatement of the question."""
    front = "<b>Definition:</b><br>- What is an eigenvalue?"
    proc, apkg = run_packager(tmp_path, {
        "deck_name": "Test Deck",
        "cards": [{"front": front, "slides": ["slide-03.jpg"]}],
    })
    assert proc.returncode == 0, proc.stderr
    rows, _media = notes_in(apkg, tmp_path)
    assert rows[0][0] == front
    assert rows[0][1] == '<img src="slide-03.jpg">'


@pytest.mark.parametrize("cards,expected", [
    ([{"front": "q", "slides": ["slide-99.jpg"]}], "missing image"),
    ([{"front": "q", "slides": []}], "no slides"),
])
def test_bad_card_spec_fails_loudly(tmp_path, cards, expected):
    proc, _apkg = run_packager(tmp_path, {"deck_name": "Test Deck", "cards": cards})
    assert proc.returncode != 0
    assert expected in proc.stdout + proc.stderr


def test_example_cards_file_matches_the_documented_schema():
    """cards.example.json is what the skill copies; keep it valid."""
    with open(os.path.join(ROOT, "cards.example.json"), encoding="utf-8") as f:
        spec = json.load(f)
    assert isinstance(spec["deck_name"], str)
    for card in spec["cards"]:
        assert card["front"] and isinstance(card["slides"], list) and card["slides"]
        for s in card["slides"]:
            assert build_deck.SLIDE_RE.match(s), f"{s} is not a slide-NN.jpg name"
