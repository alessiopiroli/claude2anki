#!/usr/bin/env python3
# Copyright (C) 2026 Alessio Piroli
# SPDX-License-Identifier: GPL-3.0-only
"""Generate tests/fixtures/sample_lecture.pdf, the deck used by the tests and README.

This writes a tiny six page slide deck with no dependencies beyond the standard
library, so the fixture can always be regenerated from source:

    python tests/fixtures/make_sample_pdf.py

The content is deliberately generic and written for this repo, so the fixture
carries no third party rights. It also exercises the skill's skip rules: the deck
opens with a title slide, has a table of contents and closes with references, none
of which should become cards.
"""
import os

W, H = 720, 540  # 4:3 landscape, the usual slide shape

# A body line is either a plain string set in Helvetica, or a list of (font, text)
# runs. The Symbol font is the only way to reach Greek letters from the standard
# 14 PDF fonts, so lambda is emitted as a run of its own. Prose lines are worded to
# keep Greek out of running text, where mixing fonts would need real metrics.
LAMBDA = ("sym", "l")  # lowercase lambda in the Symbol encoding

SLIDES = [
    # (title, [body lines]) — an empty body means a bare title slide
    ("Linear Algebra, Lecture 4", [
        "Eigenvalues and Eigenvectors",
        "",
        "Autumn term",
    ]),
    ("Outline", [
        "1. Definitions",
        "2. The characteristic polynomial",
        "3. Diagonalisation",
        "4. References",
    ]),
    ("Definition", [
        "Let A be an n x n matrix. An eigenvalue of A is a scalar",
        "for which the equation",
        "",
        [("reg", "A v = "), LAMBDA, ("reg", " v")],
        "",
        "has a nonzero solution v. Such a v is an eigenvector of A,",
        "and the set of all of them, together with 0, is the eigenspace.",
    ]),
    ("The characteristic polynomial", [
        "The eigenvalues of A are exactly the scalars satisfying",
        "",
        [("reg", "det(A - "), LAMBDA, ("reg", " I) = 0")],
        "",
        "The left hand side is a polynomial of degree n, called the",
        "characteristic polynomial of A. Finding eigenvalues therefore",
        "means finding the roots of a polynomial.",
    ]),
    ("Diagonalisation", [
        "If A has n linearly independent eigenvectors, collect them",
        "as the columns of P. Then",
        "",
        [("reg", "P^-1 A P = D")],
        "",
        "where D is diagonal and holds the eigenvalues.",
        "Powers become cheap: A^k = P D^k P^-1.",
    ]),
    ("References", [
        "Strang, Introduction to Linear Algebra",
        "Axler, Linear Algebra Done Right",
    ]),
]


def esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


FONT_KEY = {"reg": "/F2", "sym": "/F3"}
BODY_SIZE = 18
INDENT = 100  # display lines sit in from the body margin
# Rough Helvetica advances, enough to butt two runs together on a short display
# line without pulling in a full metrics table. Spaces are much narrower than
# glyphs, so they get their own number or the gap before a run is visible.
W_SPACE, W_GLYPH = 0.28, 0.55


def advance(s, size):
    return sum(W_SPACE if c == " " else W_GLYPH for c in s) * size


def text_run(x, y, font, size, s):
    return ["BT", f"{font} {size} Tf", "1 1 1 rg", f"{x:.1f} {y} Td", f"({esc(s)}) Tj", "ET"]


def content_stream(title, body):
    """Lay out one slide as a PDF content stream."""
    out = ["BT", "/F1 30 Tf", "1 1 1 rg", f"60 {H - 90} Td", f"({esc(title)}) Tj", "ET"]
    # rule under the title
    out += ["1 1 1 RG", "2 w", f"60 {H - 110} m {W - 60} {H - 110} l S"]
    y = H - 170
    for line in body:
        if isinstance(line, list):
            x = float(INDENT)
            for font, s in line:
                out += text_run(x, y, FONT_KEY[font], BODY_SIZE, s)
                x += advance(s, BODY_SIZE)
        elif line:
            out += text_run(60, y, "/F2", BODY_SIZE, line)
        y -= 32
    return "\n".join(out).encode("latin-1")


def build_pdf():
    objects = []  # 1-indexed on write

    def add(body):
        objects.append(body)
        return len(objects)

    # Reserve 1 and 2 for the catalog and page tree, whose contents need the page ids.
    objects.append(b"")
    objects.append(b"")
    font_bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    font_reg = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_sym = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Symbol >>")

    page_ids = []
    for title, body in SLIDES:
        stream = content_stream(title, body)
        # dark background drawn first, then the text
        bg = f"0.12 0.12 0.12 rg 0 0 {W} {H} re f\n".encode("latin-1")
        stream = bg + stream
        sid = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        pid = add(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >> "
            b"/Contents %d 0 R >>"
            % (W, H, font_bold, font_reg, font_sym, sid)
        )
        page_ids.append(pid)

    kids = b" ".join(b"%d 0 R" % p for p in page_ids)
    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"

    buf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_at = len(buf)
    buf += b"xref\n0 %d\n" % (len(objects) + 1)
    buf += b"0000000000 65535 f \n"
    for off in offsets:
        buf += b"%010d 00000 n \n" % off
    buf += (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref_at)
    )
    return bytes(buf)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_lecture.pdf")
    with open(out, "wb") as f:
        f.write(build_pdf())
    print(f"wrote {out} ({len(SLIDES)} slides)")
