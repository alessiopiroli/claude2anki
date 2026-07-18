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
        "Let A be an n x n matrix. A scalar L is an eigenvalue of A",
        "if there is a nonzero vector v with",
        "",
        "        A v = L v",
        "",
        "Such a v is called an eigenvector of A for L.",
        "The set of all such v, together with 0, is the eigenspace.",
    ]),
    ("The characteristic polynomial", [
        "A v = L v holds for some nonzero v exactly when",
        "",
        "        det(A - L I) = 0",
        "",
        "The left hand side is a degree n polynomial in L,",
        "called the characteristic polynomial of A.",
        "Its roots are precisely the eigenvalues of A.",
    ]),
    ("Diagonalisation", [
        "If A has n linearly independent eigenvectors, collect them",
        "as the columns of P. Then",
        "",
        "        P^-1 A P = D",
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


def content_stream(title, body):
    """Lay out one slide as a PDF content stream."""
    out = ["BT", "/F1 30 Tf", f"1 1 1 rg", f"60 {H - 90} Td", f"({esc(title)}) Tj", "ET"]
    # rule under the title
    out += ["1 1 1 RG", "2 w", f"60 {H - 110} m {W - 60} {H - 110} l S"]
    y = H - 170
    for line in body:
        if line:
            out += ["BT", "/F2 18 Tf", "1 1 1 rg", f"60 {y} Td", f"({esc(line)}) Tj", "ET"]
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

    page_ids = []
    for title, body in SLIDES:
        stream = content_stream(title, body)
        # dark background drawn first, then the text
        bg = f"0.12 0.12 0.12 rg 0 0 {W} {H} re f\n".encode("latin-1")
        stream = bg + stream
        sid = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        pid = add(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
            % (W, H, font_bold, font_reg, sid)
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
