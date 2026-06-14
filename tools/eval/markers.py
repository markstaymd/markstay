"""Candidate markstay marker syntaxes and block-marking utilities.

A "marker" is one candidate syntax for attaching a stable id to a Markdown block.
The eval inserts each candidate after every block of a base document, runs the
document through an LLM perturbation, and checks how many markers survive.

Two survival metrics:
- marker_intact: the full marker syntax with that id is present in the output
  (the id survived in *usable* form).
- id_present: the bare id token appears anywhere in the output (looser; the id
  survived as text even if the marker wrapper was mangled).
"""

import hashlib
import re

ID_PREFIX = "blk"


def _h(s: str, n: int = 4) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]


def block_id(index: int, block_text: str) -> str:
    """Deterministic, distinct, greppable id per block, e.g. 'br0a1b2'."""
    return f"{ID_PREFIX}{index}{_h(block_text)}"


def split_blocks(md: str):
    """Split a Markdown doc into blocks on blank lines.

    Fixture docs are authored so this yields clean blocks (no blank lines inside
    code fences or tables)."""
    blocks, cur = [], []
    for line in md.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


class Marker:
    inline = True  # placed after each block (vs frontmatter, placed once at top)

    def __init__(self, name, render, pattern):
        self.name = name
        self._render = render          # (id, content_hash) -> str
        self._pattern = pattern        # (id) -> regex string matching the intact marker

    def render(self, mid, content_hash):
        return self._render(mid, content_hash)

    def intact(self, mid, output):
        return re.search(self._pattern(mid), output) is not None

    def annotate(self, base_md):
        """Return (annotated_md, [ids]) with this marker after every block."""
        out, ids = [], []
        for i, block in enumerate(split_blocks(base_md)):
            mid = block_id(i, block)
            ids.append(mid)
            out.append(block)
            out.append(self.render(mid, _h(block, 4)))
        return "\n\n".join(out) + "\n", ids


class FrontmatterMarker(Marker):
    """Out-of-band variant: ids live in a YAML frontmatter map, body is clean.

    Tests whether keeping identity out of the prose survives perturbation better.
    For this variant marker_intact == id_present (no inline wrapper to preserve).
    """
    inline = False

    def __init__(self):
        super().__init__("frontmatter_map", None, None)

    def annotate(self, base_md):
        blocks = split_blocks(base_md)
        ids, lines = [], ["---", "stay:"]
        for i, block in enumerate(blocks):
            mid = block_id(i, block)
            ids.append(mid)
            snippet = " ".join(block.split())[:40].replace('"', "'")
            lines.append(f'  {mid}: "{snippet}"')
        lines.append("---")
        return "\n".join(lines) + "\n\n" + base_md.strip() + "\n", ids

    def intact(self, mid, output):
        return mid in output


MARKERS = {
    "html_comment": Marker(
        "html_comment",
        lambda mid, h: f"<!-- stay:{mid} -->",
        lambda mid: rf"<!--\s*stay:{re.escape(mid)}\b[^>]*-->",
    ),
    "html_comment_hash": Marker(
        "html_comment_hash",
        lambda mid, h: f"<!-- stay:{mid} hash=sha256:{h} -->",
        lambda mid: rf"<!--\s*stay:{re.escape(mid)}\b[^>]*-->",
    ),
    "pandoc_attr": Marker(
        "pandoc_attr",
        lambda mid, h: f"{{#{mid}}}",
        lambda mid: rf"\{{#{re.escape(mid)}\b[^}}]*\}}",
    ),
    "kramdown_ial": Marker(
        "kramdown_ial",
        lambda mid, h: f"{{: #{mid}}}",
        lambda mid: rf"\{{:\s*#{re.escape(mid)}\b[^}}]*\}}",
    ),
    "obsidian_caret": Marker(
        "obsidian_caret",
        lambda mid, h: f"^{mid}",
        lambda mid: rf"\^{re.escape(mid)}\b",
    ),
    "visible_tag": Marker(
        "visible_tag",
        lambda mid, h: f"[{mid}]",
        lambda mid: rf"\[{re.escape(mid)}\]",
    ),
    "mdx_comment": Marker(
        "mdx_comment",
        lambda mid, h: f"{{/* stay:{mid} */}}",
        lambda mid: rf"\{{/\*\s*stay:{re.escape(mid)}\b.*?\*/\}}",
    ),
    "frontmatter_map": FrontmatterMarker(),
}


def id_present(mid, output):
    return re.search(rf"\b{re.escape(mid)}\b", output) is not None
