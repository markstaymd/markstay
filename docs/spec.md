# markstay specification, version 1.4
<!-- stay:umd0IOWq hash=sha256:f396e1e194e3 -->

Status: **normative, stable.** This is the markstay standard, not a proposal.
Version 1 pins the marker grammar, attachment model, hashing, and recovery
behaviour that a conforming document and a conforming tool agree on. Version 1.1
adds CommonMark-tree attachment (§5.2) as an optional, backward-compatible
refinement of the attachment model: it lets a loose list or a blank-line-containing
fence carry a single stay, and leaves the grammar, identity, hashing, and recovery
rules unchanged. Version 1.4 adds recommended names for the two ways quote
recovery can refuse an attachment, while keeping plain DETACHED conforming. It
also corrects §9.2's prose and reference implementations so permitted sibling
context can distinguish historically duplicate child bodies at CHILD QUOTE. The
reference linter (`linter/`) and the resolver used by the
attachment eval (`eval/attachment/`) implement this document; where this document
and the reference code disagree, this document is authoritative and the code is a
bug.
<!-- stay:DraQ5ZPq hash=sha256:1fbe21748db9 -->

**Version 1.3 adds §5.5 and §9.2**, which let a **direct list item carry its own
stay**, addressed inside its list rather than as a block of its own. It is an
extension in the shape §5.2 established: it defines a behaviour where the earlier
versions had none, adds one reserved key (`subhash`), and changes nothing about a
document that does not use it. It is **less optional than §5.2** in one respect worth
stating up front: segmenting and resolving child blocks is a tool's choice, but two
write-path rules that stop an unaware tool damaging a child-stamped document bind
every version 1.3 writer (§16). §5.1 and §14 are amended to match; table-row
and inline-span identity remain deferred.
<!-- stay:I4mnY6hN hash=sha256:af2ced6ba14d -->

**Version 1.2 changed §5** (see §17 for the full history), in two ways:
<!-- stay:J5JkYEAd hash=sha256:11e4c98bd990 -->

- It **excludes a leading YAML frontmatter block** from segmentation under both
 segmenters (§5.3). Frontmatter is metadata: stamping it mints an id for nothing,
 and hashing it turns a `status:` edit into content drift.
- It **restates the condition under which the two segmenters agree** as the
 agreement subset of §5.4. Version 1.1 gave that condition as "lists tight and
 fences free of internal blank lines", which was too small a rule for the claim it
 supported: an ATX heading followed immediately by a paragraph, a fence or list
 touching a paragraph, and a link reference definition all diverge while sitting
 inside the stated subset. §5.4 now states the condition that actually holds. This
 corrects a claim that was already wrong in v1.1; frontmatter was only the
 instance that got noticed first.
<!-- stay:t1ckK239 hash=sha256:071e08f2366d -->

Only §5 moved in 1.2. The grammar (§4), identity (§2, §7), hashing (§8), and
recovery (§9) were unchanged. It is a normative change rather than an erratum, so it
took a version number, and 1.3 is the same kind of change: §5.5 and §9.2 are new
text, §4 gains one reserved key, and no rule that a 1.2 document relies on is
restated.
<!-- stay:iwDOLDfX hash=sha256:672da6e169f3 -->

**Consequence for documents stamped under 1.1:** a marker written onto frontmatter
by an older tool usually becomes an orphan error, because the block it was bound to
is no longer a block (§5.3 gives the one exception). The repair is to delete that
marker. No migration path is defined; markstay makes no compatibility guarantee
across versions this early.
<!-- stay:yWJ6hDM3 hash=sha256:6d1a44589915 -->

The rationale behind each call, and the prior art it rests on, live in a separate
decision record kept beside this one. This file is the specification; that record is
the reasoning.
<!-- stay:mSgoV8TQ hash=sha256:fe221d34942d -->

## 1. Conformance language
<!-- stay:ivd6cFYg hash=sha256:9e13989af911 -->

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL are to be interpreted as in RFC 2119.
<!-- stay:rfZv0fnk hash=sha256:e795749f165a -->

A **conforming document** is a Markdown document whose markstay markers satisfy
§3, §7. A **conforming tool** is one that parses, validates, or rewrites markstay
markers according to §3, §11.
<!-- stay:7pYcnMZf hash=sha256:891fda7aa5c1 -->

## 2. What markstay is
<!-- stay:pwdXMY99 hash=sha256:8549d542f9c8 -->

Markdown has structure but no stable content addresses. markstay is a
source-level convention that supplies them: it binds a logical block of content a
**stay**, a stable address other tools can point at and keep pointing at across
edits. The address *stays* put while the content around it changes.
<!-- stay:huPtXQsw hash=sha256:f7fdba6cf3eb -->

markstay is the convention; a *stay* is one stable content address bound to one
block. markstay is **not** an annotation system. Annotation, transclusion,
AI-assisted editing, and cross-references are consumers that build on the stay
layer; they are out of scope here (§12).
<!-- stay:mA6Y6udx hash=sha256:3a94135c3671 -->

### 2.1 The core model: identity, then evidence
<!-- stay:2Tzao9J5 hash=sha256:ebaf9bb564fc -->

A stay separates the stable identity of a block from evidence about where that
block currently sits. This split is the one idea the whole spec rests on.
<!-- stay:bxooQzey hash=sha256:24433c90581c -->

| Field | Role | Changes when content changes? |
|-------|------|-------------------------------|
| `id` | stable logical identity (answers *which block*) | no |
| `hash` | drift detection (answers *did the body change*) | yes |
| `quote` + `prefix`/`suffix` | recovery evidence (answers *where did it go* when the marker is lost) | n/a |
<!-- stay:Tnq9iP6L hash=sha256:b8cb99f8026f -->

The `id` is the identity. `hash` and `quote` are **never** identity, only
evidence. A `hash` mismatch with the marker present means "same block, changed
content," not "new block."
<!-- stay:oWXdTy8G hash=sha256:a2ddd56ca21c -->

### 2.2 Same stay or new stay
<!-- stay:SPB1M7vv hash=sha256:42b84ff031a5 -->

A stay is not its location, its content, or a hash of either. It is the stable
logical continuity of a block.
<!-- stay:2ReqtEFz hash=sha256:6cdc3942f4ae -->

The same stay MUST survive:
<!-- stay:hhoHy6WF hash=sha256:110f2a957c2b -->

- wording changes and clarifications,
- formatting changes,
- movement within a document,
- movement between documents.
<!-- stay:GRGGVGrs hash=sha256:43820919afd3 -->

A new stay is warranted only on:
<!-- stay:6eHyJONY hash=sha256:cb5a955d76f1 -->

- a material semantic change (the block now asserts something different),
- replacement of one statement with another.
<!-- stay:vJ7fBxf2 hash=sha256:7b902d9c8b1c -->

Editing a block keeps its stay; replacing its meaning earns a new one.
<!-- stay:M6NVdTtm hash=sha256:71941867e7bc -->

## 3. Marker syntax
<!-- stay:iQqge2g9 hash=sha256:72963fd186c8 -->

A stay is recorded as a **marker** placed after the block it identifies (§5).
<!-- stay:UTfHaa04 hash=sha256:d8c4a2cd1357 -->

### 3.1 Primary form: trailing HTML comment
<!-- stay:5zxecsem hash=sha256:eaf138687cd6 -->

```md
The paragraph being identified.
<!-- stay:8f24 hash=sha256:7a9c -->
```

The HTML-comment form is the primary serialization. It is invisible in
GitHub-rendered Markdown, preserved in the raw `.md` source, needs no Markdown
attribute extension, and degrades to harmless source text on tools that do not
understand it. A conforming `.md` document MUST use this form.
<!-- stay:bubSQOco hash=sha256:52ce4a82f37a -->

### 3.2 MDX profile: comment-expression form
<!-- stay:fV4l5X4i hash=sha256:ceac644d263c -->

HTML comments are invalid in MDX v2. Where the target is MDX, the same marker
takes the JSX comment form:
<!-- stay:FefPEX9W hash=sha256:81105865f4ed -->

```mdx
The paragraph being identified.
{/* stay:8f24 hash=sha256:7a9c */}
```

One data model, two serializations. A conforming tool that targets MDX MUST use
this form; a conforming tool MUST recognise both forms on input.
<!-- stay:BVGaybIK hash=sha256:17d57643716d -->

## 4. Marker grammar
<!-- stay:p3a9OsnE hash=sha256:eba0ba2af4c9 -->

A marker body begins with the `stay:` namespace, followed by a positional id and
zero or more whitespace-separated attributes.
<!-- stay:eYwKQTdf hash=sha256:e7f882cf6f99 -->

```abnf
marker      = html-marker / mdx-marker
html-marker = "<!--" *WSP "stay:" id *( 1*WSP attribute ) *WSP "-->"
mdx-marker  = "{/*"  *WSP "stay:" id *( 1*WSP attribute ) *WSP "*/}"
<!-- stay:NdykyfZp hash=sha256:13c245cb8520 -->

id          = 1*( ALPHA / DIGIT / "_" / "-" )      ; required, positional
attribute   = key "=" value
key         = ALPHA *( ALPHA / DIGIT / "_" / "-" )
value       = bare-value / quoted-value
bare-value  = 1*( %x21-7E except WSP and DQUOTE )    ; no spaces, no quotes
quoted-value= DQUOTE *( qchar ) DQUOTE               ; spaces allowed
qchar       = %x20-21 / %x23-5B / %x5D-7E / "\" DQUOTE / "\\"
```
<!-- stay:9zEUvi7Y hash=sha256:c7b547a5e838 -->

Rules:
<!-- stay:GIjJJe34 hash=sha256:09e09762d2d1 -->

- **`id` is REQUIRED and positional**: the first whitespace-delimited token after
 `stay:`. A first token containing `=` (a bare `key=value` with no id) is
 **malformed**; the marker has no id and a conforming linter MUST report it.
- **Attribute order is free.** A conforming tool MUST NOT depend on the order of
 attributes.
- **Reserved (core) keys** defined by this spec: `hash`, `quote`, `prefix`,
 `suffix`, and `subhash` (v1.3). Their meanings are fixed by §8, §9 and §5.5.
- **Extension keys MUST be namespaced** with an `x-` prefix (e.g.
 `x-acme-author="…"`). Keys that are neither reserved nor `x-`-prefixed are
 reserved for future versions; a conforming tool MUST preserve any key it does
 not understand verbatim and MUST NOT act on it.
- **The same holds for a reserved key from a section a tool does not implement.**
 A key being reserved is not permission to act on it: a tool that does not
 implement §5.5 MUST preserve `subhash` verbatim and MUST NOT act on it, exactly
 as if it were unrecognised. Without this clause the preservation rule above would
 cover only future-version keys, and a key would lose its protection on the day it
 was given a meaning.
- **Values** are either a bare token (no whitespace, no double quote) or a
 double-quoted string. A value containing whitespace MUST be double-quoted.
 Inside a quoted value, `\"` and `\\` are the only escapes.
<!-- stay:KLMBH6Ia hash=sha256:4b1a51fd43e6 -->

A marker MUST carry an `id`. It SHOULD carry a `hash` (§8). It MAY carry
`quote`/`prefix`/`suffix` recovery evidence inline (§9); equivalently a tool MAY
keep that evidence in a side index instead of inline. Inline is normative when
present; the side-index option exists so dense coverage need not bloat the source.
<!-- stay:ki0tGHt6 hash=sha256:1291bc664ab3 -->

## 5. Attachment model
<!-- stay:rkzV5vdY hash=sha256:0822c8b4cdc0 -->

Attachment binds each marker to the block it follows. A conforming tool segments
a document into blocks one of two ways, which draw the same block boundaries on
every document in the **agreement subset** (§5.4):
<!-- stay:MhJttcKe hash=sha256:59756c69823a -->

- **Blank-line segmentation** is the baseline and the reference default. It needs
 no Markdown parser, which keeps the reference implementation dependency-free. A
 **block** is a maximal run of non-blank lines bounded by blank lines or the
 document edges.
- **CommonMark-tree segmentation** (§5.2) is the version 1.1 refinement. A
 **block** is a node of the CommonMark block tree, so a loose list, a fence with
 internal blank lines, or a blockquote with internal blank lines is one block. It
 needs a CommonMark parser and is an optional extra.
<!-- stay:EdpAyM55 hash=sha256:b714230bdeca -->

The rest of this section holds under both segmenters:
<!-- stay:gH12FOq9 hash=sha256:7593fbc28f40 -->

- A **blank line** is a line that is empty or contains only ASCII whitespace.
- A **leading YAML frontmatter block** (§5.3) is document metadata, not content. It
 is excluded from the document before segmentation, so it is never a block: it
 carries no stay, is never hashed, and is not a host a marker can bind to.
- A marker binds to the block **immediately preceding** it. A marker MAY sit on
 the block's last line, or on its own line(s) after the block as a *marker-only
 chunk*; a marker-only chunk binds to the preceding content block.
- A marker (or marker-only chunk) with **no preceding content block** is an
 **orphan**; a conforming linter MUST report it.
- More than one marker MAY bind to one block.
<!-- stay:eKrPsCWQ hash=sha256:e219286e6a11 -->

### 5.1 Block granularity
<!-- stay:len8ImGa hash=sha256:d53a94813cd2 -->

Every stay identifies a whole block:
<!-- stay:13MAmutm hash=sha256:0d8a4944f9ba -->

- **Paragraph**: the paragraph.
- **List**: a marker after the list identifies the **whole list**. A list item MAY
 also carry a stay of its own, addressed inside the list rather than as a block of
 its own (§5.5, v1.3); a marker with no `subhash` still identifies the whole list.
- **Code fence**: a marker after the closing fence identifies the **whole fence**.
- **Table**: a marker after the table identifies the **whole table**; row-level
 identity is deferred.
- **Blockquote**: a marker after the quote identifies the **whole quote**.
<!-- stay:xUUypf7e hash=sha256:48921e617e92 -->

### 5.2 CommonMark-tree attachment (v1.1)
<!-- stay:RPoNeLUp hash=sha256:d3e87ce83401 -->

Blank-line segmentation (§5) splits two constructs that legitimately contain
blank lines into multiple blocks, so under the baseline:
<!-- stay:LcA30cBE hash=sha256:9628a955514d -->

- a **loose list** (blank lines between items) parses as one block per item, and
 a trailing marker binds the last item, not the whole list;
- a **fenced code block with internal blank lines** parses as multiple blocks, so
 a fence cannot reliably carry one stay.
<!-- stay:g7P7V9pw hash=sha256:dbc94ed21f58 -->

CommonMark-tree segmentation lifts both. Parsing the CommonMark block tree makes a
list, a fence, or a blockquote a single node regardless of the blank lines inside
it, so the whole-block granularity of §5.1 holds for them too: a marker after a
loose list binds the whole list, a marker after a blank-line fence binds the whole
fence, and a nested list or blockquote resolves to its outermost block.
<!-- stay:CgOl8Wt6 hash=sha256:4400655d05e5 -->

This refinement changes only **what counts as one block**. The marker grammar
(§4), the identity model (§2, §7), hash normalization (§8), and the quote/margin
commit rule (§9) are unchanged.
<!-- stay:pmZ29xqb hash=sha256:a58026a6eea0 -->

It is a **conservative extension**, not a breaking change: it changes what a
CommonMark-mode tool counts as one block and changes nothing at all for a baseline
tool. On the agreement subset (§5.4) the two segmenters draw the same block
boundaries, so a document in the subset segments identically under either. Outside
that subset they can differ, and always could, which is why §5.4 states the subset
as a condition on the document rather than assuming it. CommonMark-tree segmentation only *adds* a defined
single-stay attachment for loose lists and blank-line fences, which version 1 left
out of scope (§14).
<!-- stay:scAPAyB6 hash=sha256:b231269500e0 -->

CommonMark-tree segmentation needs a CommonMark parser, which the dependency-free
baseline does not. A conforming tool MAY implement either or both; when it offers
both, the baseline SHOULD remain the default so the zero-dependency path always
exists. For a document that must resolve identically under any conforming tool,
keep it in the agreement subset (§5.4).
<!-- stay:qa7MGPWW hash=sha256:b689a37b36aa -->

### 5.3 Document metadata: leading YAML frontmatter (v1.2)
<!-- stay:C9Cr398S hash=sha256:53260c0d2fab -->

A **leading YAML frontmatter block** is document metadata, not content. A
conforming tool MUST exclude it from the document before segmentation, under both
segmenters of §5. It is never a block: it carries no stay and is never hashed.
<!-- stay:9hQjXrqr hash=sha256:30d0b71b8992 -->

Once the span is gone, everything else follows from §5 unchanged. In particular a
marker written onto the frontmatter by an older tool now has nothing before it, so
it is an orphan and a conforming linter MUST report it (§5). The one shape that is
not an orphan is a marker on the line immediately before following content with no
blank line between them, which blank-line segmentation reads as one run and binds
to that content. That document is outside the agreement subset (§5.4), and this is
one of the reasons the subset exists.
<!-- stay:xHsSWkGF hash=sha256:2bbf9963a7fb -->

Excluding it MUST NOT change the blocks, the block order, or the line numbers of
the rest of the document. (The reference implementations replace each excluded line
with an empty line rather than deleting it, which gives all three properties for
free.)
<!-- stay:r8CoYM7p hash=sha256:cd7f360fa72f -->

**Recognition.** After line endings are normalized to LF (§8, step 1), the document
has a leading frontmatter span iff all four of these hold. The span is then lines 1
to *n* inclusive, where line *n* is the closing line found in condition 2.
<!-- stay:xDBqyP4Z hash=sha256:85fbcd496b31 -->

1. **Line 1 is exactly `---`**, with only spaces or tabs allowed after it. Exactly
 three hyphens: `----` neither opens nor closes a span.
2. **Some later line is exactly `---` or `...`**, again with only spaces or tabs
 after it. The **first** such line closes the span. With no such line there is no
 frontmatter, and line 1 is an ordinary thematic break.
3. **The payload** (the lines strictly between the two fence lines) is **non-empty**
 and contains **no blank line** (§5: empty or only ASCII whitespace).
4. **At least one payload line reads as YAML rather than as prose**, which means,
 after any leading spaces or tabs, either:
 - a **sequence item**: `-`, then one or more spaces or tabs, then a character
   outside `\x00-\x20` and not `\x7f`; or
 - a **mapping key**: a first character outside `\x00-\x20`, not `\x7f`, and
   neither `:` nor `#`; then zero or more characters that are not `:`; then `:`;
   then a space, a tab, or end of line.
<!-- stay:7QwcW4qd hash=sha256:16becee8b769 -->

 A YAML **comment** (`# …`) does NOT satisfy this, because it is byte-identical to
 an ATX heading.
<!-- stay:8UvXTXCX hash=sha256:afb85f408d2e -->

The closing line is fixed by condition 2 alone. If the span it fixes then fails
condition 3 or 4, **the document has no frontmatter**; a conforming tool MUST NOT
go looking for a later `---` or `...` that would satisfy them. Rescanning would let
`---` / `Title` / `---` / `title: t` / `---` swallow the whole document, which is
the failure this rule exists to prevent.
<!-- stay:gh50VZLp hash=sha256:8a4b051e6e94 -->

Conditions 3 and 4 are load-bearing, because `---` is also a thematic break and a
setext underline, so a looser rule destroys content. Condition 3 is what stops
`---` / blank / `Intro.` / blank / `---` (two thematic breaks around a paragraph)
from reading as frontmatter that swallows the paragraph. Condition 4 is what stops
`---` / `Title` / `---` (a thematic break plus a setext heading) from doing the
same.
<!-- stay:6fzA2UNw hash=sha256:17f66ad0f2a0 -->

**Recognition is a heuristic over a genuinely ambiguous construct, and the spec
says so rather than pretending otherwise.** A document that opens with a thematic
break, carries one blank-free run of content, and closes with another thematic
break has two legitimate readings, and no rule can separate them from the bytes:
<!-- stay:Zlfe9vqQ hash=sha256:7275a75b3f74 -->

```md
---
- Keep this content
---
```
<!-- stay:VCNu0cnB hash=sha256:3513070a4284 -->

That is a list between two thematic breaks *and* a YAML sequence, and conditions
1 to 4 accept it, so the content is excluded. **Frontmatter wins**, which is the
same call every mainstream Markdown site generator makes on the same bytes. What
conditions 3 and 4 buy is not the absence of false positives, it is that the
ambiguity is confined to documents of exactly this shape: an opening thematic
break, no blank line before the closer, and a payload line that reads as YAML.
Everything else fails towards ordinary Markdown, where the worst case is a
spurious block and a stray drift warning.
<!-- stay:zBULIRwq hash=sha256:20c7afebd569 -->

The whitespace sets above are **ASCII**, spelled out as character ranges rather than
delegated to a language's "whitespace" or "non-whitespace" class, for the same
reason as in §8 and §9: Python, ECMAScript, and Rust each classify a different set
of characters (U+001C, U+0085, U+00A0, U+FEFF each differ between at least two of
them). A rule that **removes** a span from the document cannot afford that
divergence, because implementations would then delete different spans.
<!-- stay:ieqBkTss hash=sha256:c00b0cd6860f -->

**The exclusion is a source span, not a block**, and a tool that segments a parsed
tree MUST honour it as one. `...` is a legal YAML end marker but not a setext
underline, so in `---` / `title: t` / `...` / `Body.` a CommonMark parser produces
a single paragraph node that begins inside the metadata and ends outside it. Such a
node MUST be trimmed to the part after the excluded span; dropping the whole node
would destroy `Body.`
<!-- stay:7h7exWXG hash=sha256:6b0eed1e077f -->

**Out of scope, deliberately:**
<!-- stay:NyRmt9oH hash=sha256:c44ab9f6f2a0 -->

- **TOML (`+++`) and JSON frontmatter are not recognised.** Only the `---` form.
- **A `---` fence anywhere but line 1 is not frontmatter**, and is segmented as
 whatever CommonMark says it is.
- **Whether the metadata itself should be addressable** (a stay for the
 frontmatter) is unresolved rather than refused. Nothing needs it today, and
 adding it later is additive.
<!-- stay:2Vrhk8L9 hash=sha256:2c1e7a81ee38 -->

### 5.4 The agreement subset (v1.2)
<!-- stay:DcwbiImh hash=sha256:8b5425374326 -->

A document is in the **agreement subset** when, after the leading frontmatter span
(§5.3) is excluded, its **maximal runs of non-blank lines and its top-level
CommonMark block nodes cover the same spans of lines**: every run is covered by
exactly one node, and every node covers exactly one whole run. Top-level means
outermost: a list item inside a list, or a paragraph inside a blockquote, is not
counted separately.
<!-- stay:JNurIEEM hash=sha256:7203595dd2fc -->

Read that as an equality of line spans, **not** as "each run parses to one node on
its own". Parsing a run in isolation asks a different question and gives the wrong
answer: `- a` / blank / `- b` is a one-item list twice when each run is parsed
alone, and a single loose list when the document is parsed whole.
<!-- stay:Kqw3w5Xh hash=sha256:9804ef1ea70d -->

On this subset the two segmenters of §5 draw the same block boundaries, so a
document in it segments identically under any conforming tool. The condition is
stated in this form because a shorter one cannot be complete: blank-line
segmentation can see nothing but blank lines, so the two can only agree where
CommonMark's block boundaries and the document's blank lines are the same
boundaries.
<!-- stay:qgouQT8D hash=sha256:843b19cd094d -->

Three ways a document leaves the subset, all of them common:
<!-- stay:QD7DIna3 hash=sha256:2806f95bc8b6 -->

1. **A block boundary with no blank line at it.** CommonMark starts a new node at
 an ATX heading, a fence, a blockquote, a list, or a thematic break whether or not
 a blank line precedes it; blank-line segmentation does not. `# Heading` /
 `Body.` is one block under the baseline and two under CommonMark. So is `Para.`
 followed immediately by a fence, a list, or a `>` quote.
2. **A blank line inside one node.** A loose list, a fence with an internal blank
 line, an indented code block, or an HTML block spanning a blank line (`<pre>` …
 `</pre>`) is one node but several runs. Two constructs of the same kind also
 **merge across** the blank line meant to separate them: `- a` / blank / `- b` is
 a single loose list, and two indented code chunks are a single code block. This
 is the case §5.2 was written for.
3. **A run that no single node covers.** A CommonMark parser consumes **link
 reference definitions** (`[label]: /url`) and emits no node for them, so a run of
 definitions is a block to the baseline and nothing at all to the tree segmenter,
 even with blank lines on both sides. A definition glued to the paragraph below it
 gives the partial version of the same thing: one run, one node, and the node
 covers only part of the run.
<!-- stay:bPRXA3Qs hash=sha256:bf4e02aee092 -->

**For authors**, the practical version: put a blank line between block-level
constructs; keep lists tight; use fenced code rather than indented code, and keep
fences and HTML blocks free of internal blank lines; do not place two lists of the
same kind back to back, since they merge; keep link reference definitions out of a
document whose blocks carry stays; and keep marker-shaped text out of code (see
below). A document written that way is in the subset. The definition above is what
a tool checks when it needs certainty, and checking it needs a CommonMark parser,
which is the honest cost of the guarantee.
<!-- stay:lpxsDMdG hash=sha256:973edf875167 -->

The condition is **necessary as well as sufficient** for block boundaries, and it
is necessary by construction: a document outside it has a run whose lines are not
one node's lines, which is a boundary the two segmenters draw differently. What can
still coincide is the *result* of a lint or a stamp, because a marker-only chunk
folds into the block above it (§5) and so can hide a boundary difference in the
final block list. Do not read that coincidence as agreement.
<!-- stay:JpuKawU2 hash=sha256:90c391b2c3b2 -->

**One thing the subset does not cover: marker-shaped text inside literal code.**
The boundaries agree; what each tool recognises as a *marker* inside those
boundaries is a separate axis. The dependency-free baseline scans source text
(§3), so it finds `<!-- stay:x -->` wherever it appears, including inside a fenced
code block or a code span. A tree-based tool can tell that the same bytes are
literal code, and the reference mdast adapter deliberately declines to bind them.
Both readings are defensible and this spec does not force one: a baseline tool
cannot implement "ignore markers in code" without the parser it exists to avoid.
Authors should therefore **keep marker-shaped text out of code spans and fenced
blocks**, or expect one tool to see a stay there and another not to.

**What version 1.2 changed here.** Version 1.1 stated this condition as "lists
tight and fences free of internal blank lines", which is case 2 alone. Cases 1 and
3 were missing, so documents that plainly diverge, `# Heading` / `Body.` first
among them, were inside the stated subset while being outside the real one. That
was already false in v1.1, before frontmatter was involved; frontmatter was simply
the instance that got noticed, because a stayed document with YAML at the top hits
it on the first run. Version 1.2 does **not** change either segmenter to close
cases 1 to 3; it states the condition correctly and leaves the constraint with the
author, which is what §5.2 was already doing for case 2.
<!-- stay:SLqUtALj hash=sha256:608e071e24ed -->

### 5.5 Child-block identity: list items (v1.3)
<!-- stay:BIvjZW2q hash=sha256:18ca5fad8733 -->

Version 1.3 lifts the §5.1 deferral for one construct: **a list item MAY carry its
own stay.** Nothing else in that deferral moves. Table rows and inline spans stay
deferred (§14), and every rule below is written so that adding row identity later
needs a carrier rather than a second identity model.
<!-- stay:fFwU4hgn hash=sha256:f66a27ba2b90 -->

A **child block** is a **direct** list item of a block that is a list. Direct is the
whole depth rule: only the items at the top level of the container are child blocks.
A list nested inside an item is part of **that item's body**, and its items are not
child blocks in version 1.3. A conforming tool MUST NOT address an item more than one
level below the container block.
<!-- stay:LQvA7978 hash=sha256:985fefe6a1e8 -->

**A child block is not a block.** Segmentation (§5) is unchanged: the list is still
the block, it is what a marker without `subhash` binds to, and its `hash` is still
computed over the whole list. A child block is addressed *inside* its container, and
only through the carrier below. Nothing about a document without child markers
changes, in either segmenter.
<!-- stay:KroLEKrJ hash=sha256:92c226f49f7a -->

A child stay's id is an ordinary id. §4 (grammar), §6 (generation), §7 (identity,
duplicates, move and copy) and §12 (`doc.md#stay-id`) apply to it verbatim. There is
no compound id, no second namespace, and no third kind of thing to resolve.
<!-- stay:uU7em9ml hash=sha256:cb230bad05b1 -->

**Body and hash.** The **child body** is the item's source slice with, in order:
<!-- stay:eqXhxY6k hash=sha256:d4e393e1ec87 -->

1. every marker removed (§3);
2. the first line's leading indentation, its list marker, and the whitespace gap
 after it removed (`- `, `* `, `  1. `, `3) `);
3. from each following line, the same indentation width removed where the line
 carries it, counting a tab as advancing to the next 4-column stop.
<!-- stay:smQCrE6F hash=sha256:67fb8630a3e0 -->

Everything that remains, **including any nested content**, is then normalized and
hashed exactly as §8 specifies, and written under the key defined below. Two
consequences, both intended: changing a bullet glyph is not drift, and renumbering
an ordered list is not drift.
<!-- stay:mMCAL03X hash=sha256:2d4752b839db -->

The child's **ordinal** is its 1-based position among its container's child blocks.
It is evidence, never identity (§2.1), and §9.2 bars it from the commit rule.
<!-- stay:3QoH8ITo hash=sha256:ca08823d2098 -->

**What a resolver has to have recorded.** §9.2 reads five things about a child stay,
and a resolver that recorded fewer cannot run the whole ladder, so they are named here
rather than left to a tool's side-index design (§4):
<!-- stay:BuLLLk3m hash=sha256:f47020064916 -->

1. the child's **id**;
2. its **child body hash** (`subhash`);
3. the **container's** id and hash;
4. the child's **ordinal** at the time the stay was recorded;
5. whether that hash identified **exactly one** child among its siblings, and exactly
 one in the whole document, at that same time.
<!-- stay:kDeKylMA hash=sha256:270af4d344f6 -->

Items 4 and 5 are recomputable from the document as it stood, so nothing new goes in
the marker; they are stated because a resolver that skips them silently loses tiers.
A resolver missing item 4 cannot run tier 2 and one missing item 5 must not run tiers
3 or 4, and either would answer differently from a complete one on the same pair of
documents, which §13 counts as a failure rather than an implementation choice.
<!-- stay:bnBXHOSX hash=sha256:281c8dafc1d4 -->

**Carrier.** A child marker stores its drift evidence under the reserved key
`subhash=sha256:<hex>`, which follows §8's truncation and comparison rules exactly as
`hash` does:
<!-- stay:HdGCH0No hash=sha256:e901afb13be2 -->

```md
- Ship the linter <!-- stay:c4LD1 subhash=sha256:9d2f -->
- Ship the hook <!-- stay:c4LD2 subhash=sha256:41ac -->
<!-- stay:c4LDp hash=sha256:1122 -->
```

**`subhash` is a write-path requirement, not a naming preference.** A tool that does
not implement this section computes a block's hash over the whole list. If a child
stored its evidence under `hash`, that tool's restamp would overwrite it with the
container's digest, and the child's real hash would be gone with nothing left to
detect the loss. Under `subhash` the same tool leaves the key alone, because §4
already requires an unrecognised key to be preserved verbatim and not acted on.
<!-- stay:GfRwNZkB hash=sha256:516e0fc113d6 -->

Rules for readers:
<!-- stay:UetpPA03 hash=sha256:d3d6e88e6c6c -->

- A marker carrying `subhash` addresses the direct item whose source span contains
 it, **wherever in that span it sits, except inside a nested item** (next rule), and
 MUST NOT be treated as binding to the container block. Where a writer may put one is
 narrower (below): reading loosely costs nothing, since a marker in an item's own
 lines is not addressing anything else, and writing loosely is what produces a
 document two tools disagree about.
- A marker carrying `subhash` inside an item **nested inside another list item**
 addresses no child block in version 1.3. A conforming tool MUST NOT resolve it as
 a child stay, MUST NOT treat it as identifying the container block either (it is
 nobody's stay), and MUST preserve it verbatim (§4). A linter SHOULD report it: the
 marker addresses nothing, and silence there is indistinguishable from a marker that
 resolved. The same report is owed for the other way a `subhash` marker can address
 nothing: a tool whose segmenter emitted no child blocks for that list at all, which
 is the fail-closed profile below rather than a defect in the document, and a report
 that does not tell those two apart is not much better than silence.
- A marker carrying no `subhash` binds to a block under §5 wherever it sits,
 including inside a list.
- A child stay SHOULD sit in a container that carries its own stay. Where it does
 not, a conforming linter SHOULD report it (the reference emits `ORPHAN_CHILD` at
 warn level); resolution still proceeds, through §9.2 tier 4, on weaker evidence.
<!-- stay:CPtgZcDd hash=sha256:fd5494cfbb80 -->

Rules for writers:
<!-- stay:P2uOvh60 hash=sha256:6ad2d26e3736 -->

- A tool that mints a child stay MUST write the marker at the **end of the item's
 last paragraph**. An item with no paragraph to carry one, an item that is only a
 fenced code block, only a nested list, or only a blockquote, MUST NOT be given a
 child stay in version 1.3: no position for the marker survives every renderer and
 formatter while staying inside that item. The container still receives its own
 stay, so such an item is **readable but not stampable**.
- A tool that stamps MUST treat a block as already stamped only when a marker binds
 **the block itself**. A list whose items carry child markers is not a stamped
 block, and a tool that mints a child stay MUST mint the container's stay in the
 same pass if it has none.
- A tool that fills in missing hashes MUST write `subhash` for a child marker, and
 MUST NOT add a `hash` to any marker that already carries a `subhash`. That holds
 whether or not the tool recognised a child block on this run: a tool segmenting a
 loose list without a CommonMark parser sees no children at all (below), and that
 is exactly the run that would otherwise write the container's digest onto every
 item of a child-stamped list.
- A marker carrying `subhash` **and** a `hash` equal to its container's digest is
 the signature of an older tool having added the second key. A conforming repair
 MAY remove that `hash`; it MUST NOT remove the `subhash`.
<!-- stay:KfbF3dLR hash=sha256:4229d04447ed -->

**Segmenter profiles, which do not agree here.** Under CommonMark-tree segmentation
(§5.2) the child blocks of a list are its `listItem` nodes. Under blank-line
segmentation they are recognised only in a restricted profile: a **tight** list
whose items are single paragraphs, whose continuation lines carry the item's exact
content indentation. Outside that profile, a dependency-free tool MUST emit **no**
child blocks for the whole list rather than guess a boundary, and the list attaches
as an ordinary block.
<!-- stay:UmwMU3qe hash=sha256:43202b759054 -->

So a loose list can carry child stays under §5.2 and cannot under the baseline, and
**the agreement subset of §5.4 does not extend to child blocks**: a document can sit
inside it and still have the two segmenters disagree about whether its list items are
addressable. An author who wants child identity to travel across both segmenters
keeps the list tight and its items single paragraphs. This is the §5.2 split
reappearing one level down, and it is stated rather than closed, for the same reason
§5.4 states its condition rather than changing a segmenter.
<!-- stay:7rUXV7zH hash=sha256:2352a0cc5bce -->

## 6. IDs
<!-- stay:HxEBSxMP hash=sha256:c80e52bb8b4f -->

- **Default: a short opaque generated id**, not derived from the block text, so
 it survives arbitrary edits to that text. Generated ids give a rewriting model
 nothing to "improve."
- **Human-readable ids are allowed** for authored landmarks (`stay:install-step`).
- **The id character set is** `[A-Za-z0-9_-]+`.
- **UUIDs are permitted but never required** (too token-heavy for dense coverage).
- **Duplicate ids within a document are invalid** (§7).
<!-- stay:lkTZYDRp hash=sha256:bcc1158e0137 -->

## 7. Identity rules
<!-- stay:nEIboLyb hash=sha256:08280ff9e170 -->

- **No duplicate stays.** Two blocks in one document MUST NOT share a stay id. A
 duplicate id is a well-formedness error a conforming linter MUST report.
- **Move preserves the stay.** A block moved within or between documents keeps its
 id (same logical block, new position).
- **Copy mints a new stay.** Copying a block produces a duplicate, which is
 invalid, so a copied block MUST receive a fresh id. *How* a tool repairs a
 duplicate (mint on paste, mint on next lint, prompt the user) is tool behaviour,
 not protocol; this spec states the invariant and leaves the repair strategy to
 the tool.
<!-- stay:bdnFkn4c hash=sha256:0e076771bef6 -->

## 8. Hash normalization
<!-- stay:dCfLAjWz hash=sha256:9f6b33e8e84e -->

`hash` detects whether a block's body changed since the hash was written. It is
**not** identity (§2.1) and it is **lossy by design**: it detects semantic drift,
not byte-exact change.
<!-- stay:XZ1C6RVN hash=sha256:e11f95608f88 -->

The hash input is the block's body with all markers removed (§3), normalized in
this order:
<!-- stay:kRGUAMQN hash=sha256:37374b0af2ac -->

1. **Line endings → LF.** `CRLF` and lone `CR` become `LF`.
2. **Strip trailing ASCII whitespace** (space, tab, form feed, vertical tab) from
 every line.
3. **Drop leading and trailing blank lines** (a blank line is empty or only ASCII
 whitespace, §5).
<!-- stay:aH0LRmdi hash=sha256:706021423264 -->

The whitespace set in steps 2 and 3 is **ASCII**, not a language's Unicode
whitespace definition, so two conforming implementations compute the same hash
without sharing a Unicode whitespace table.
<!-- stay:LPX2vW4e hash=sha256:e04fd4f21752 -->

The hash is the **SHA-256** of the UTF-8 encoding of the normalized body.
<!-- stay:EKpoCiB2 hash=sha256:dd5416c9796f -->

It is written `hash=sha256:<hex>`, lowercase hex. The hex MAY be **truncated** to
a prefix (the examples use 4 hex digits). A conforming tool MUST compare at the
precision stored in the marker (prefix comparison) and MUST NOT report drift
merely because a freshly computed full hash is longer than a stored short one.
Hex comparison is case-insensitive.
<!-- stay:0t01ViYl hash=sha256:b6a3d6083606 -->

Consequence of normalization: trailing-whitespace-only and line-ending-only edits
do **not** register as drift, including inside code fences. This is intentional,
such edits do not change meaning.
<!-- stay:5QhL3TAZ hash=sha256:3919e79cc08e -->

## 9. Quote / selector recovery
<!-- stay:LbtPE2jX hash=sha256:0bee0ac139c9 -->

When a marker is lost (the AI-regeneration failure mode: an agent rewrites the
document and drops the comment), the id is re-found from evidence about the text,
using a W3C `TextQuoteSelector`-style triple:
<!-- stay:yCefQdFM hash=sha256:72df0e180110 -->

- `quote`, the block's own body text (the exact selector),
- `prefix`, trailing context of the preceding block,
- `suffix`, leading context of the following block.
<!-- stay:iKwGyoJF hash=sha256:46586ff50917 -->

Normative parameters of the reference recovery model:
<!-- stay:T6PV9nm7 hash=sha256:5f3616d79b34 -->

- **Context length**: `prefix`/`suffix` carry up to **48 characters** of the
 neighbour on each side.
- **Normalization for matching**: lowercase ASCII letters (A, Z), collapse runs of
 ASCII whitespace to a single space, then trim. Capitalization and reflowed line
 breaks (common after an LLM edit) MUST NOT register as differences. The fold and
 the whitespace set are **ASCII**, so every implementation reproduces them exactly
 without a Unicode case-folding or whitespace table; non-ASCII characters are
 compared unchanged. This is sufficient because matching is recovery *evidence*,
 not identity (§2.1): a coarser fold can only weaken a recovery hint, never
 corrupt a stay. A richer Unicode fold MAY be defined by a later version.
- **Body score**: similarity of the stored `quote` to a candidate block body in
 `[0, 1]`, with a containment floor so a surviving half of a split block does not
 score arbitrarily low. The metric is the **Ratcliff/Obershelp
 longest-matching-block ratio**: `2·M / T`, where `T` is the combined length of
 the two strings and `M` the total size of the recursively-found longest matching
 blocks. It is computed over **Unicode code points** (not UTF-16 code units), with
 the **earliest-match tie-break** (on equal run length, the lowest
 `(a-index, b-index)`) and **no junk or popularity heuristic**. This is exactly
 the algorithm Python's `difflib.SequenceMatcher(autojunk=False)` implements;
 naming it directly, rather than by reference to one language's standard library,
 is what lets an independent implementation agree bit-for-bit (the published
 `conformance/` corpus checks this, including the non-BMP code-point cases).
- **Context bonus**: `prefix`/`suffix` contribute only a small additive
 tiebreaker (≤ 0.05 each); they break near-ties between structurally identical
 blocks, they are not a primary key.
- **Commit rule (resolves "surface, don't guess")**: a recovery is committed only
 when the best candidate's score is **≥ 0.5** AND beats the runner-up by a
 **margin ≥ 0.05**. Otherwise the marker MUST be reported **detached**, never
 reattached.
<!-- stay:Dr9XpGtH hash=sha256:bbc1c5ffef6d -->

Quote recovery is **best-effort evidence, never authority.** The trustworthy
signals are the surviving id (kept via §11) and the exact `hash` (§8); the
attachment eval measures the hash tier alone recovering 81% of moved-but-unchanged
blocks with zero false attachment, while quote recovery on near-duplicate blocks
false-attaches even with the margin guard. A quote match without a clear margin
MUST surface as detached (§10) rather than reattach.
<!-- stay:eHJeQ3ox hash=sha256:0e5bd26a7797 -->

### 9.1 The resolution ladder
<!-- stay:z1CpxJom hash=sha256:39dff40e20b0 -->

A conforming resolver applies the evidence strongest-first:
<!-- stay:asV4mUlu hash=sha256:32c55b033016 -->

1. **MARKER**, the id's marker is still present → trust it.
2. **HASH**, no marker, but exactly one block's normalized-body hash equals the
 stored hash → the content survived verbatim, just lost its marker.
3. **QUOTE**, no marker and no unique hash hit → fuzzy-recover via §9, committing
 only on a clear winner; otherwise **DETACHED**.
<!-- stay:h0XizihD hash=sha256:6936087ab677 -->

### 9.2 The child resolution ladder (v1.3)
<!-- stay:wsG5Ieyn hash=sha256:3d9f10bf89f0 -->

A child stay (§5.5) resolves on the same discipline as §9.1, strongest evidence
first, with one addition: a child is resolved **inside its container**, so its rivals
are its siblings rather than the whole document. That containment is what answers
§5.1's stated reason for deferring item identity, which was near-duplicate items:
`Done` competes only with the other items of its own list.
<!-- stay:7mqLi8iw hash=sha256:9c0afea0a147 -->

0. **Resolve the container** by §9.1, applied **exclusively**: containers are
 resolved tier by tier across the document, and a block claimed by a stronger tier
 leaves the candidate pool for the weaker ones. Resolving each container in
 isolation would let a deleted list quote-match onto a surviving near-duplicate
 sibling at a wide margin, because the rival that would have contested the match is
 the one the edit removed. A container that resolves to DETACHED detaches its
 children, **except** those whose own marker survived (tier 1 outranks this gate: a
 failed inference about the container MUST NOT discard stored identity).
1. **CHILD MARKER**, the child's marker is still present → trust it. This runs
 **first**, ahead of any structural inference. A container's hash is computed with
 markers removed (§8), so two child markers can be swapped while the container's
 hash still matches; a ladder that tried ordinals first would silently override the
 surviving ids, which contradicts §9.1.
2. **CONTAINER HASH**, the container's stored hash matches → the list is unchanged
 modulo §8 normalization, so the remaining markerless children map by ordinal.
 This tier is narrower than it looks: a container's body keeps its `- ` and `1. `
 prefixes, so a bullet-glyph change or a renumber breaks the container hash even
 though §5.5 makes both non-drift for every child. Those edits fall through to
 tier 3, where the child hashes correctly see no drift.
 **Ordinal decides *which* child, never *whether* a match is good enough**, and that
 split collapses easily in either direction, so read it here once: at this tier, with
 the container hash matched, position is the whole mapping and item *n* is item *n*,
 while at tier 5 it contributes to neither the score nor the margin. Generalizing
 tier 5's bar into "ordinal never matters" loses this mapping and leaves identical
 siblings indistinguishable; generalizing this tier into "position is evidence" hands
 tier 5 the margin its commit rule exists to demand from the text.
3. **CHILD HASH, sibling-scoped**, the stored `subhash` equals exactly one sibling's
 child-body hash → attach. Uniqueness is required on **both** sides: the hash must
 identify exactly one sibling now *and* have identified exactly one when the stay was
 recorded (§5.5, item 5). A tie on either side falls through, which is the honest
 handling of a list with two identical items, and checking only the after side would
 attach a stay whose evidence was already ambiguous when it was written.
4. **CHILD HASH, document-scoped**, exactly one child block anywhere in the document
 matches → attach, under the same both-sides rule as tier 3. This tier keeps §7's move guarantee true for children: an item
 dragged into another list would otherwise detach despite unambiguous evidence. It
 is restricted to the **exact hash**; quote recovery is deliberately not offered at
 document scope, because on short near-duplicate items that is precisely the
 false-attachment case §9 warns about.
<!-- stay:BHNQSFUx hash=sha256:2956b717227e -->

 **Its known exposure, stated rather than claimed away:** uniqueness in the edited
 document is weaker evidence than provenance. If an item's text was *copied*
 elsewhere without its marker and the original is then edited, the copy becomes the
 sole hash match and this tier attaches to it, when §7 says a copy is a new stay and
 §10 would rather detach. This is the same trade §9.1's document-wide hash tier
 already makes for whole blocks, where the attachment eval measured 81% recovery at
 0% false attachment, and it is **sharper for children**, because short items repeat
 far more often than whole blocks do and no equivalent measurement has been run on
 them. A tool MAY offer this tier as a reported, reversible attachment rather than a
 silent one. A later version should either measure it or fence it with provenance.
5. **CHILD QUOTE**, §9 scoring over **siblings only**, where `prefix`/`suffix` are
 the adjacent siblings. The commit rule is unchanged: score ≥ 0.5 AND margin ≥ 0.05.
 **Ordinal distance contributes nothing to the score and nothing to the margin.** It
 MAY order candidates for presentation. Letting it contribute even the tiebreaker
 §9 allows for context would let position manufacture the exact margin the commit
 rule demands, which is location acting as identity under another name, and it would
 fire hardest on the repeated-item case where it is least trustworthy.
6. Otherwise **DETACHED** (§10, unchanged: surface, don't guess). When tier 5
 itself refuses the attachment, §10's `unmatched` and `ambiguous` reasons apply.
 A resolver MAY expose more specific child diagnostics for a failed container
 gate, an unaddressed marker, or a same-tier contest, but version 1.4 standardizes
 neither their names nor their precedence. The outcome remains DETACHED.
<!-- stay:S18ZgaHG hash=sha256:295d47a09719 -->

**Assignment is exclusive at every tier, and a contested item goes to neither stay.**
A child block is a candidate for at most one stay: once a tier attaches a stay to an
item, that item leaves the candidate pool for every weaker tier and every other stay.
Where two stays reach the same item **at the same tier**, that item MUST be given to
neither of them; both continue to the weaker tiers, and detach if nothing else fits.
A tier therefore MUST be evaluated for every stay before any of its attachments is
committed, because committing as each stay is visited hands a contested item to
whichever one the tool enumerated first. Tier 0 already says this for containers;
without it here, two implementations that agree about every hash still disagree about
the document, which is the §13 failure this ladder exists to avoid.
<!-- stay:fqq8ptfJ hash=sha256:bbe6ed6bfac0 -->

**Byte-identical sibling bodies are not automatically detached.** When the
container's hash still matches, the list is unchanged and item *n* is item *n*, so
tier 2 maps identical siblings by position without guessing. When it does not match,
tiers 3 and 4 still require historical and current uniqueness, but tier 5 MAY attach
when the permitted sibling prefix or suffix creates the required margin. Repeated
items detach only when the allowed quote and context evidence remains
indistinguishable, or when exclusive assignment leaves the target contested. The
version 1.3 note said a container edit always detached identical bodies; that
contradicted tier 5 and caused both Python references to skip a permitted recovery.
<!-- stay:Jz7C6uiP hash=sha256:65b6f9d3dd95 -->

## 10. Detached and stale markers
<!-- stay:DmG1dtHO hash=sha256:1536ce8c4e52 -->

When a marker cannot be confidently mapped to a block, a conforming tool MUST mark
it **outdated** (detached) rather than guess a nearby block. Silent reattachment
to the wrong block is worse than an explicit stale state. (Precedent: GitHub
review comments mark a comment outdated rather than silently re-anchoring it.) When
DETACHED is reached because the QUOTE tier in §9.1 or §9.2 refuses an attachment,
a conforming resolver SHOULD report `unmatched` if there is no candidate or the
best score is below `0.5`, and `ambiguous` if the best score reaches `0.5` but its
margin over the runner-up is below `0.05`. A resolver MAY report plain DETACHED. If
it exposes a machine-readable reason for either refusal, it MUST use those names and
meanings. The reason MUST NOT authorize an attachment or weaken §9's commit rule.
Candidate lists, evidence labels, provenance, ordering, presentation, and transport
schema are outside this specification.
<!-- stay:f61ICvwp hash=sha256:98e6b095ebb6 -->

DETACHED is a correct outcome, not a failure: a marker whose block was genuinely
deleted MUST resolve to detached.
<!-- stay:AA1q85HU hash=sha256:f876adf139a2 -->

## 11. AI editing contract
<!-- stay:5QmPEhKi hash=sha256:b7d757551967 -->

Markdown is routinely edited by machines, and that is exactly when stays are lost:
a naive full-document rewrite strips nearly every marker, an instructed one keeps
them all (`eval/FINDINGS.md`). The contract an editing agent honours is therefore
part of the spec, not an implementation note.
<!-- stay:8a639fKv hash=sha256:7ab0f78ca5d8 -->

An agent editing a markstay document MUST:
<!-- stay:y3xtU7es hash=sha256:cb465afc2094 -->

- **preserve** every existing stay,
- **keep** each stay attached to the same logical content it had before,
- **mint** a new stay for newly-addressed content,
- **never reuse** a stay id for semantically different content,
- **report** any stay it drops,
- **report** any duplicate stay it introduces.
<!-- stay:jjEjAD1z hash=sha256:60ffa11a69f0 -->

The contract is **measurable, not aspirational**: the reference linter's
regeneration diff (`linter/`) detects dropped, duplicated, and relocated stays
across a before/after edit and exits non-zero, so a post-edit lint step turns
silent stay loss into a caught error. The durable deliverable for the AI use case
is this contract (the preservation instruction plus the post-edit linter), not the
choice of marker syntax, which measurement found barely affects survival
(`eval/FINDINGS.md`).
<!-- stay:EImE9iNp hash=sha256:44f1f9c28781 -->

## 12. Address scope
<!-- stay:2fRaiRj3 hash=sha256:279a77f011d9 -->

A stay is unique within a **single document** (§7). There is no repository-wide or
global stay; resolving a stay always happens relative to one document.
<!-- stay:A0KqOGRG hash=sha256:0c2c50139973 -->

The canonical address of a block is its document address plus its stay id, reusing
the URL-fragment convention so a stay address is already shaped like a link:
<!-- stay:LYEzvI6K hash=sha256:af1ae1dd8806 -->

```
document-address#stay-id
```
<!-- stay:vPIPTe5K hash=sha256:c568ff6f46f6 -->

Examples:
<!-- stay:KQqQkviv hash=sha256:1889f03338b7 -->

```
auth.md#oauth-summary
docs/architecture.md#a1f0
```
<!-- stay:uN7qsPF4 hash=sha256:7fd82ca85409 -->

Cross-document reference resolution is a consumer's concern. This spec defines the
in-document stay and its address form, not a resolver for addresses that span
documents.
<!-- stay:cVXlwtsC hash=sha256:442eedc2945c -->

## 13. Failure modes and how the spec answers them
<!-- stay:i0jGpoFd hash=sha256:79fa009c9ac1 -->

| Failure mode | Answer |
|--------------|--------|
| **Marker detachment** (edit splits/merges/moves a block) | hash-drift check (§8) + quote recovery (§9) + explicit stale state (§10). On distinct prose the marker→hash→quote ladder re-attaches 98% of ids with zero false attachment; near-duplicate blocks are the residual risk, so a quote match without a clear margin surfaces as detached. |
| **Sanitizer stripping** (a pipeline removes HTML comments) | the MDX/attribute profiles (§3.2), and consumers that detect a missing expected marker. |
| **AI regeneration churn** (an agent drops or reassigns markers) | the AI editing contract (§11): a preservation instruction restores survival to 100% in the eval; a post-edit linter catches silent loss; generated non-semantic ids (§6) give a model nothing to "improve." |
| **Copy-paste duplication** | copy mints a new id (§7); tools detect and repair duplicates. |
| **Granularity disagreement** | granularity pinned to whole blocks (§5.1); loose lists and blank-line fences are handled by CommonMark-tree attachment (§5.2). |
| **Metadata read as content** (a `status:` flip drifts a hash; the two segmenters disagree about what frontmatter even is) | leading YAML frontmatter is excluded from segmentation under both segmenters (§5.3), so it is never stamped and never hashed. |
| **Scope creep into an annotation product** | core stays at identity + resolution; annotation is a separate, layered spec (§14). |
<!-- stay:K6J3h42A hash=sha256:1b48fcd497d0 -->

## 14. Non-goals
<!-- stay:x3XFUhd4 hash=sha256:2f59dc50d4cf -->

- Annotation, comment storage, threads.
- Transclusion / embedding.
- Row-level table identity, inline-span identity.
- Provenance tracking and knowledge-graph construction.
- A backend, accounts, a hosted registry, or any global / cross-repo stay
 namespace.
<!-- stay:Itv36Vd3 hash=sha256:27d3544028db -->

(Loose-list and blank-line-fence single-stay attachment was a v1 non-goal; it is
resolved by CommonMark-tree attachment in v1.1, §5.2. List-item identity was a v1
non-goal; it is resolved for direct list items in v1.3, §5.5. Table rows are the same
idea with a different carrier, a marker inside the last cell of a one-line row, and
stay deferred until that carrier is shown to survive real renderers.)
<!-- stay:umfBvzuc hash=sha256:3ad402cfc62f -->

## 15. Closest existing standards
<!-- stay:FqGyVOjF hash=sha256:a5cda24dd2fa -->

- Recovery anchoring: W3C Web Annotation Data Model selectors (`TextQuoteSelector`,
 `TextPositionSelector`).
- Markdown syntax lineage: Pandoc / PHP Markdown Extra / kramdown `{#id}` attribute
 lists.
- Markdown product precedent: Obsidian block references (`^block-id`).
- Block-database precedent: Notion comments parented by block id; Logseq / Roam
 block references.
- Editor block-identity precedent (storage-anchored): AFFiNE / BlockSuite, where
 every doc and block is a node with a stable id persisted in a YJS CRDT store. It
 is the closest production neighbour and proves the demand; it anchors identity in
 the store, where markstay anchors it in the source text.
- Revision / stale-state precedent: GitHub review comments (commit + path + line,
 with an outdated state).
<!-- stay:LqV4Hdw9 hash=sha256:01667873988a -->

See `research/` (and the site's prior-art page) for the full survey and sources.
<!-- stay:zLdRNoDL hash=sha256:2aae1677c95c -->

## 16. Conformance summary
<!-- stay:f6YC7K0X hash=sha256:d995f806087a -->

A conforming linter MUST, for a single document, report: malformed markers (no id,
§4), orphan markers (§5), duplicate ids (§7), and hash drift (§8). For a
before/after pair it MUST report dropped, duplicated, and relocated ids (§11). It
MUST exit non-zero on any error-level finding so it can gate a commit hook or an
agent's post-edit step. The reference linter in `linter/` is such a tool.
<!-- stay:xr9pdYQe hash=sha256:7607d19b3e6d -->

A conforming resolver MUST apply the §9.1 ladder and MUST resolve to detached
rather than reattach when no tier yields a confident result. It SHOULD distinguish
the `unmatched` and `ambiguous` quote-refusal cases defined by §10; if it exposes a
machine-readable reason for either, it MUST use those names and meanings. Plain
DETACHED remains conforming, and candidate or evidence detail is not a conformance
requirement. The resolver used by `eval/attachment/` is such a tool.
<!-- stay:tpIZKKBm hash=sha256:df90dced5eba -->

Child-block identity (§5.5) splits into an optional half and a mandatory one, and the
split is not the same as §5.2's. **Segmenting and resolving child blocks is optional**:
a tool that never sees a list item is conforming. **Recognising `subhash` on the write
path is not**, and every conforming version 1.3 writer MUST:
<!-- stay:gY4kwGJH hash=sha256:0b91dea134cc -->

- not add a `hash` to a marker that already carries a `subhash`, and
- not treat a block as stamped on the strength of a marker that carries one.
<!-- stay:GbIyKsIr hash=sha256:c2c16e103d57 -->

Those two are a compatibility shim rather than a feature, and they are mandatory
because §4's preserve-unknown-keys rule does not reach them: a writer that adds a key
of its own, or that reads a child marker as evidence the block is done, is not acting
on a key it does not understand, it is acting on its own idea of the document. A tool
without the shim damages a document that uses §5.5, in both of the ways named above and
both measured rather than predicted, so "ignore the section entirely" is conforming only
for a reader.
<!-- stay:Ap9TiTxs hash=sha256:25552b2b7dc7 -->

A tool that does implement the section MUST apply the §9.2 ladder for child stays, and
MUST emit no child blocks at all for a list that falls outside its segmenter's profile
rather than guess an item boundary.
<!-- stay:3dCNYT0A hash=sha256:32c15853bd94 -->

Any conforming tool that segments a document, whichever segmenter it implements,
MUST exclude a leading YAML frontmatter span (§5.3) before segmenting, and MUST
NOT stamp, hash, or attach a marker to it.
<!-- stay:RW4LozSB hash=sha256:3eae6ace5b03 -->

## 17. Version history
<!-- stay:lUqH9hHD hash=sha256:9fe14861072a -->

| Version | What it changed |
|---------|-----------------|
| **1.4** | Recommends reporting `unmatched` when quote recovery has no above-threshold candidate and `ambiguous` when a candidate reaches the threshold but fails the margin (§10), while keeping plain DETACHED conforming. A machine-readable reason, when exposed, uses those names and meanings; candidate and evidence schemas remain non-normative (§16). Also corrects §9.2's version 1.3 note and both Python references: the historical-uniqueness gate belongs to CHILD HASH tiers 3 and 4, while CHILD QUOTE may use permitted sibling context to distinguish duplicate child bodies. The commit rule, document syntax, and DETACHED outcome are unchanged. |
| **1.3** | Adds child-block identity for direct list items (§5.5) and their resolution ladder (§9.2), carried by the new reserved key `subhash` (§4) so that a tool which does not implement the section cannot overwrite a child's evidence. Lifts the list-item half of the §5.1 deferral and the §14 non-goal; table rows and inline spans stay deferred. Segmenting and resolving child blocks is optional; two write-path rules that keep an unaware tool from damaging a child-stamped document are not (§16). A document with no child markers is unaffected under either segmenter. |
| **1.2** | Excludes leading YAML frontmatter from segmentation under both segmenters (§5, §5.3), and restates the two segmenters' agreement condition as the agreement subset (§5.4), which v1.1 stated too narrowly. Normative change to §5; grammar, identity, hashing, and recovery unchanged. A marker already stamped onto frontmatter usually becomes an orphan error. |
| **1.1** | Adds CommonMark-tree attachment (§5.2) as an optional segmenter, so a loose list, a blank-line fence, or a blockquote with an internal blank line can carry a single stay. Adds no requirement to a baseline tool and changes no marker's meaning; its statement of when the two segmenters agree was corrected in 1.2. |
| **1.0** | The marker grammar (§3, §4), the identity model (§2, §7), blank-line attachment (§5), hash normalization (§8), quote recovery and the commit rule (§9), the detached state (§10), and the AI editing contract (§11). |
<!-- stay:wpHe8SeN hash=sha256:6b3f9969296d -->

markstay does **not** offer a compatibility guarantee across versions at this
stage. Where a version corrects a defect, it corrects it rather than carrying the
defect forward behind a flag; §17 exists so the change is legible, not so it can be
avoided.
<!-- stay:Dqoh2DIU hash=sha256:16977c266dfc -->
