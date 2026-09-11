#!/usr/bin/env python3
"""Does a write change what a reader sees? (the property behind the proposed §3.4)

The oracle behind §3.4's measured claims. It renders a document before and after a
write and compares the element structure and the words, which is the property §3.4
states, rather than the visible text, which is weaker and misses a construct
reflowed into another construct with the same words.

Getting this right took six attempts and each one moved a published number, so the
sanity cases in test_oracle.py are part of the instrument rather than a nicety: a
layout artefact reads exactly like a defect.
"""
import re

import markstay as M  # noqa: E402
from markdown_it import MarkdownIt  # noqa: E402
from html.parser import HTMLParser  # noqa: E402

RENDER = MarkdownIt("commonmark", {"html": True})
# The same renderer with GFM tables on. §5.6 is about a GFM table, and a CommonMark
# renderer shows one as a paragraph, where `*` and backticks in different cells pair
# with each other. That difference is not hypothetical: it is the whole of the row
# arm's one corpus failure (`figures/readme.md`), which this renderer preserves.
RENDER_TABLES = MarkdownIt("commonmark", {"html": True}).enable("table")
COMMENT = re.compile(r"<!--.*?-->", re.S)
TAG = re.compile(r"<[^>]*>", re.S)


def visible(md):
    """Visible text only. Weaker than the property, kept for continuity."""
    return " ".join(TAG.sub(" ", COMMENT.sub("", RENDER.render(md))).split())


def rendered(md, tables=False):
    """The property the draft stated: the rendered document, not its layout.

    ``tables`` turns on the GFM table rule, which is the renderer §5.6's row carrier
    is written for. Off by default, because §5 defines the CommonMark profile.

    Three regex normalisations were tried and each hid a different layout
    artefact behind the fix for the last one: whitespace left where a comment was
    removed from a raw HTML block, whitespace introduced between two tags, and
    whitespace introduced between text and a closing tag. None is a difference a
    reader sees. So parse the rendered HTML instead and compare the element
    structure and the words: start tags with their attributes, end tags, and
    non-blank text runs. Comments are dropped, because a marker is a comment.
    """
    parser = _Structure()
    parser.feed((RENDER_TABLES if tables else RENDER).render(md))
    parser.close()
    return parser.out


class _Structure(HTMLParser):
    """Element structure plus words, with markers removed as a reader sees them.

    Text is buffered across comments and flushed at a tag boundary. Without that,
    dropping a marker splits one text node into two and every row-stamped table
    reads as a change when nothing about it moved.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self._buf = []

    def _flush(self):
        text = " ".join("".join(self._buf).split())
        self._buf.clear()
        if text:
            self.out.append(("t", text))

    def handle_starttag(self, tag, attrs):
        self._flush()
        self.out.append(("s", tag, tuple(sorted(attrs))))

    def handle_startendtag(self, tag, attrs):
        self._flush()
        self.out.append(("se", tag, tuple(sorted(attrs))))

    def handle_endtag(self, tag):
        self._flush()
        self.out.append(("e", tag))

    def handle_data(self, data):
        self._buf.append(data)

    def handle_comment(self, data):
        pass

    def close(self):
        super().close()
        self._flush()
