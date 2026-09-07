# markstay specification, version 1.6
<!-- stay:umd0IOWq hash=sha256:cfc371d51ead -->

Status: **normative, stable.** This is the markstay standard, not a proposal.
Version 1 pins the marker grammar, attachment model, hashing, and recovery
behaviour that a conforming document and a conforming tool agree on. Version 1.1
adds CommonMark-tree attachment (§5.2) as an optional, backward-compatible
refinement of the attachment model: it lets a loose list or a blank-line-containing
fence carry a single stay, and leaves the grammar, identity, hashing, and recovery
rules unchanged. Version 1.4 adds recommended names for the two ways quote
recovery can refuse an attachment, while keeping plain DETACHED conforming. It
also corrects §9.2's prose and reference implementations so permitted sibling
context can distinguish historically duplicate child bodies at CHILD QUOTE.
Version 1.5 makes text inside a fenced code block content rather than markup
(§3.3), so a marker in an example is an example, for every fence a line scan can
recognise. Version 1.6 lifts the rest of the §5.1 deferral: a table body row may
carry its own stay (§5.6), on the carrier §14 gated it on and with §5.5's identity
model unchanged, and one reader rule now binds every tool rather than only those
implementing child identity (§16). The reference linter (`linter/`) and the resolver
used by the attachment eval (`eval/attachment/`) implement versions through 1.5;
v1.6 row support is the active implementation phase. Where this document and the
reference code disagree, this document is authoritative and the code is a bug.
<!-- stay:DraQ5ZPq hash=sha256:abe99b10b771 -->

**Version 1.3 adds §5.5 and §9.2**, which let a **direct list item carry its own
stay**, addressed inside its list rather than as a block of its own. It is an
extension in the shape §5.2 established: it defines a behaviour where the earlier
versions had none, adds one reserved key (`subhash`), and changes nothing about a
document that does not use it. It is **less optional than §5.2** in one respect worth
stating up front: segmenting and resolving child blocks is a tool's choice, but two
write-path rules that stop an unaware tool damaging a child-stamped document bind
every version 1.3 writer (§16). §5.1 and §14 are amended to match; table-row
identity followed in version 1.6 (§5.6) and inline-span identity remains deferred.
<!-- stay:I4mnY6hN hash=sha256:b3e9441fc699 -->

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

### 3.3 A fenced code block is content (v1.5)

Text inside a fenced code block is **content, not markup**. A conforming tool MUST
NOT read a `stay:` marker there as a marker: it identifies no block, it is not removed
from a body before hashing (§8), and it does not make the block that contains it
stamped (§5).

This is the rule every other Markdown construct already follows. A `#` inside a fence
is not a heading and a row of pipes is not a table, because a fence means *show this,
do not interpret it*. Version 1.4 and earlier made markstay the exception, and the
documents that exception damages are the ones that document markstay: a tutorial, a
README, this specification. All three of the following were observed in this file
before the rule existed. A restamp rewrote the `hash=` values in §3.1's and §3.2's
examples to the digest of the fence around them. The fence carrying an example marker
could not be stamped, because the example already counted as its stay. Two fences
showing the same example id produced a duplicate-id error that no restamp could clear.

**Recognising a fence.** Both segmenters (§5) and every tool apply the same line-based
rule, so for every fence this rule recognises, what counts as a marker does not depend
on which segmenter a tool implements:

0. The scan runs on lines split at LF, after §8's line-ending normalization, so a
 `CRLF` document and its `LF` twin give the same answer.
1. An **opening fence** is a line with at most three leading **spaces**, U+0020, whose
 next characters are a run of three or more backticks or three or more tildes. A
 backtick fence's info string MUST NOT contain a backtick. **A tab is not a space
 here.** CommonMark expands a tab to the next four-column stop, which needs a column
 model this rule deliberately does not have, so a tab-indented fence is not recognised
 and falls in with the other constructs the line rule cannot see (below).
2. It closes at the first later line with at most three leading spaces that is a run
 of **the same character**, **at least as long** as the opener, followed by zero or
 more of **space or tab and nothing else**. A longer run is what lets a fence contain
 a shorter one. The whitespace set is named rather than left to "whitespace", because
 three implementations picking three sets is the way this rule fails quietly.
3. An unclosed fence runs to the end of the document.

The fenced block is the opening line, the closing line, and everything between them.
The fence lines are included deliberately rather than as an edge case: a marker-shaped
string can sit in an opening fence's **info string**, where before this rule it was read
as a marker and bound to whatever block preceded it.

````text
```md <!-- stay:example -->
a listing whose opening fence carries a marker-shaped info string
```
````

**A marker that crosses the boundary.** The grammar (§4) spans lines, so one
marker-shaped string can open outside a fenced block and close inside it, or the
reverse. A tool applying the line rule above MUST judge such a string by the line it
**opens** on. That is the only line a reader sees it begin on, and it is the one line two
tools can agree about without tracking where the span ends. So a marker opening outside
a fence is a marker, and removing it from a body (§8) removes the whole span including
the bytes that fall inside the listing; a marker-shaped string opening inside a fence is
content, even where its closing delimiter falls after the closing fence. Neither shape occurs in a document a
conforming writer produced, because a writer emits a marker on one line. The rule is
here so that two readers handed the same hand-written document agree. A tool with a block
parser has no such ambiguity to resolve, since it reads the bytes from the code node
itself, and §5.4 already scopes where the two answers part company.

**Rules for writers.** A tool MUST NOT write a marker on a line inside a fenced code
block, and MUST NOT stamp a block whose span lies inside one. This half of the rule is
not symmetry for its own sake: a dependency-free segmenter (§5) splits a fence that
contains a blank line into ordinary blocks, and a stamper that treats one of those as
stampable appends a marker *into the listing*. This specification shipped that way. Its
§4 grammar block reads

```text
marker      = html-marker / mdx-marker
html-marker = "<!--" *WSP "stay:" id *( 1*WSP attribute ) *WSP "-->"
mdx-marker  = "{/*"  *WSP "stay:" id *( 1*WSP attribute ) *WSP "*/}"
<!-- stay:NdykyfZp hash=sha256:13c245cb8520 -->
```

on the published site, where the last line is a marker a stamping run put inside the
formal grammar. A reader can see it is not ABNF; what they cannot tell from the grammar
is that it is a markstay marker rather than a stray comment. Under §5.2 the fence is
one block and takes its stay after the closing fence in the ordinary way; under the
baseline segmenter the halves of such a fence are simply not stampable, which is where
§5.2 already arrives: a fence with internal blank lines cannot reliably carry one stay
without the block tree.

**Deliberately not covered**, in every case because a dependency-free tool cannot
recognise the construct without the block parser §5.2 exists to avoid:

- **Indented code blocks.** Four spaces is code at the top level and ordinary
 continuation inside a list item, and telling those apart needs list context.
- **A fence the line rule cannot see**, which is one carrying a blockquote marker
 (`> ` ``` `) or indented more than three spaces, as a fence inside a nested list item
 is. Recognising those means knowing the container, which is the same parser. **This is
 the rule's real limit and it is not a small one**: a tutorial that shows its example
 inside a blockquote is exactly the document §3.3 exists to protect, and it is not
 protected. §5.4 records what remains divergent there.
- **Inline code spans.** A marker inside backticks on a prose line stays a marker.
 That is the shape pandoc's native `markdown` writer produces when it mangles a
 trailing marker, and a mangled marker a tool can still see is better than one that
 has silently stopped existing.

**Migration**, in two cases that behave differently, and the second is the one to warn
about:

1. **The block has its own stay and also shows a marker in a fence.** Its body now
 hashes over the marker-shaped string, where before the string was removed. If that
 stay carries a `hash`, it reports drift once and a restamp clears it, correctly
 this time. If it carries none, nothing compares and nothing is reported: the id
 still identifies the block and the upgrade costs nothing. Either way no id moves.
2. **The in-fence marker *was* the block's only stay.** Under version 1.4 a tool read
 it as the block's marker, so the block looked stamped and never received a real one.
 Under this rule the string is content and the block has **no stay at all**. That is
 not drift, nothing compares against a stored hash, and no linter finding fires,
 because an unstamped block is not an error. A restamp does not fix it: the block
 needs a stay **minted**, so it gets a new id rather than a corrected hash. A document
 whose two fences shared an example id lands here twice, and the duplicate error it
 used to report disappears with the stays.

Nothing about the marker grammar (§4), identity (§7), or recovery (§9) changes.
<!-- stay:zvT5cQlG hash=sha256:cb077ed5aa0b -->

## 4. Marker grammar
<!-- stay:p3a9OsnE hash=sha256:eba0ba2af4c9 -->

A marker body begins with the `stay:` namespace, followed by a positional id and
zero or more whitespace-separated attributes.
<!-- stay:eYwKQTdf hash=sha256:e7f882cf6f99 -->

```abnf
marker      = html-marker / mdx-marker
html-marker = "<!--" *WSP "stay:" id *( 1*WSP attribute ) *WSP "-->"
mdx-marker  = "{/*"  *WSP "stay:" id *( 1*WSP attribute ) *WSP "*/}"

id          = 1*( ALPHA / DIGIT / "_" / "-" )      ; required, positional
attribute   = key "=" value
key         = ALPHA *( ALPHA / DIGIT / "_" / "-" )
value       = bare-value / quoted-value
bare-value  = 1*( %x21-7E except WSP and DQUOTE )    ; no spaces, no quotes
quoted-value= DQUOTE *( qchar ) DQUOTE               ; spaces and LF allowed
qchar       = LF / %x20-21 / %x23-5B / %x5D-7E / "\" DQUOTE / "\\"
```
<!-- stay:9zEUvi7Y hash=sha256:6795ad2e3b05 -->

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
 A key being reserved is not permission to interpret it: a tool that does not
 implement §5.5 or §5.6 MUST preserve `subhash` verbatim and MUST NOT interpret it
 as child identity. It MUST still apply §16's mandatory non-attribution and writer
 safety guards; those compare the key without segmenting or resolving a child.
 Without this clause the preservation rule above would cover only future-version
 keys, and a key would lose its protection on the day it was given a meaning.
- **Values** are either a bare token (no whitespace, no double quote) or a
 double-quoted string. A value containing whitespace MUST be double-quoted.
 Inside a quoted value, `\"` and `\\` are the only escapes.
- **Line endings** are normalized from CRLF or CR to LF before applying this
 grammar, as in §8 step 1. LF is valid only inside a quoted value; it is not `WSP`
 between attributes. Recognition uses the normalized copy, while preservation
 remains verbatim. A conforming writer emits a marker on one line (§3.3), so the
 multiline form is reader syntax for hand-written input rather than writer output.
- **The host comment owns its close delimiter.** An HTML marker body MUST NOT
 contain either literal sequence `-->` or `--!>`, and an MDX marker body MUST NOT
 contain `*/`. Double quotes do not escape those sequences from the HTML or
 JavaScript comment parser. An HTML reader stops at the earlier of `-->` and `--!>`;
 only `-->` completes the `html-marker` production. An MDX reader stops at the first
 `*/`; only one immediately followed by `}` completes `mdx-marker`. A rejected
 opener does not consume a later opener. If the preceding body is not a complete
 grammar match, it is not a valid marker for attachment, hashing, row-token
 recognition, or preservation evidence. That validity boundary does not cancel the
 required malformed-marker diagnostic above: a comment whose `stay:` namespace is
 followed by a first `key=value` token still has no id and a conforming linter MUST
 report it. A writer MUST NOT emit any forbidden sequence in that marker form.
 Recovery evidence that needs it can use the other marker form where the document
 permits one, or the side index below.
<!-- stay:KLMBH6Ia hash=sha256:ccab39a2cfed -->

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
- **Table**: a marker after the table identifies the table's selected §5 block,
 which is the **whole table** when segmentation isolates it. If adjacent content
 shares that block, the marker identifies the whole selected block. A body row MAY
 also carry a stay of its own, addressed inside that container rather than as a block
 of its own (§5.6, v1.6); a marker with no `subhash` still identifies the container.
- **Blockquote**: a marker after the quote identifies the **whole quote**.
<!-- stay:xUUypf7e hash=sha256:285fdcac82d2 -->

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
boundaries is a separate axis, and **version 1.5 settled the larger half of it**. A
fenced code block the §3.3 line rule recognises is content to every tool, baseline or
tree-based, so it is no longer a divergence axis at all. The premise this section
carried until then, that a baseline tool cannot implement "ignore markers in code"
without the parser it exists to avoid, was true of a *parser* and false of a line
scan: recognising a top-level fence needs neither.

What remains divergent is what the line rule cannot see: a fence carrying a blockquote
marker or indented more than three spaces, an indented code block, and an inline code
span. There the baseline still finds a marker wherever it appears, a tree-based tool
can tell the same bytes are literal code, and the reference mdast adapter declines to
bind them. Both readings stay defensible and this spec still does not force one. Authors
should therefore **keep marker-shaped text out of code spans, indented code, and any
fence that is quoted or deeply indented**, or expect one tool to see a stay there and
another not to. **Table-row recognition is the narrow exception for a tool that
implements table-child identity:** §5.6 requires that tool to treat §4 marker spans as
opaque row-scan tokens outside a §3.3-recognised fence, including inside inline and
indented code, so cell boundaries and row ownership do not inherit this divergence.
The mandatory §16 rule for every reader remains narrower: never attribute a marker
carrying `subhash` to its containing block. It does not require running this scan.

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
own stay.** Every rule below is written so that adding row identity later needs a
carrier rather than a second identity model, and version 1.6 took it up on exactly
that basis (§5.6). Inline spans stay deferred (§14).
<!-- stay:fFwU4hgn hash=sha256:b93f69ae9377 -->

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
**the agreement subset of §5.4 does not extend to the child items of a list**: a
document can sit inside it and still have the two segmenters disagree about whether
its list items are addressable. That is a property of this section rather than of
child identity in general, and §5.6 does not inherit it: both built-in segmenters
recognise candidate table rows with the same parser-free line scan. Each row uses its
selected §5 block as a container. Outside §5.4's agreement subset, ordinary
CommonMark boundaries can make the two built-in segmenters select different
containers around the same rows. A tool MAY use a GFM table extension for rendering
or its own AST, but that extension is not a third §5 segmenter and MUST NOT replace the
selected built-in block with a table node when choosing the §9.2 container. An
author who wants child identity to travel across both built-in segmenters keeps the
list tight and its items single paragraphs. This is the §5.2 split reappearing one
level down, and it is stated rather than closed, for the same reason §5.4 states its
condition rather than changing a segmenter.
<!-- stay:7rUXV7zH hash=sha256:dba136452b4e -->

### 5.6 Child-block identity: table rows (v1.6)
<!-- stay:e0TFIglO hash=sha256:d3595c191d58 -->

Version 1.6 lifts the rest of the §5.1 deferral: **a body row of a GFM table MAY
carry its own stay**, addressed inside its table rather than as a block of its own.
Inline-span identity stays deferred (§14).
<!-- stay:HXlL5EtE hash=sha256:36bdaeedd14c -->

This is §5.5's model with a different carrier and a different body rule, and nothing
else. A row stay's id is an ordinary id, §9.2 resolves it with the ladder it already
has, and every §5.5 rule phrased about `subhash` rather than about lists holds here
unchanged. §5.5's opening paragraph promised that adding rows would need a carrier
rather than a second identity model; this section is that promise being kept.
<!-- stay:wKPQU9KY hash=sha256:048dd3a0d66e -->

A **child block** of a table is one of its **body rows**. The header row and the
delimiter row are the table's schema rather than its content: a conforming tool MUST
NOT mint a stay on either, and a marker carrying `subhash` found on one addresses
nothing (below). A row's **ordinal** is its 1-based position among its table's body
rows; as in §5.5 it is evidence, never identity (§2.1), and §9.2 bars it from the
commit rule.
<!-- stay:gmRtuEWc hash=sha256:bb34ebe37add -->

**A child block is not a block, and a table candidate does not create one.** Every
line from the candidate's header through its last body row MUST lie inside one block
under the tool's selected §5 segmenter; otherwise the candidate has no child blocks.
That existing §5 block is the rows' **container** for §9.2. A marker with no `subhash`
binds to it, and its `hash` is computed over that whole block. Inside §5.4's agreement
subset both built-in segmenters select the same block, but that block can include
adjacent prose as well as the table-shaped lines. Outside the subset, an ordinary
CommonMark boundary such as a touching heading can make the built-in segmenters choose
different containers around the same rows. A GFM table node does not change this
choice: §5 defines exactly two segmenters, and an extension AST MUST map the candidate
back to the block selected by the tool's chosen §5 profile. Nothing about segmentation
or a document without row markers changes under either profile.
<!-- stay:9wuNMD1z hash=sha256:a79fe4ea0cd8 -->

After the complete scan, an accepted candidate has child blocks only when it is the
**only accepted candidate in its selected §5 container**. If two or more candidates
share one container, none of their rows is a child block. A `subhash` marker on any of
those rows addresses nothing and the linter report required below applies. This is the
same fail-closed reason as rule 4: §9.2 records the container and the row ordinal, not a
second table discriminator, so two ordinal-1 rows inside one container cannot be
recovered unambiguously. This filter is applied after recognition and does not change
the parser-free scan or its candidate boundaries.
<!-- stay:single-row-table-per-container hash=sha256:2a66c5889afb -->

**Recognising a table** is a parser-free line scan, and every tool that implements
table-child segmentation applies the same one. The rule uses a conceptual **marker
token** while it scans: every part of a marker span
on a line is one opaque token that is not ASCII whitespace, `\\`, or `|`, and that
breaks a run of backslashes. Bytes inside the token are never inspected as table
syntax. The token is deleted only after cell boundaries have been fixed. This is
what lets a marker value contain `|` without letting marker removal turn a closing
pipe into an escaped one.
<!-- stay:cFmVUxy5 hash=sha256:8ffa547059ae -->

Two marker spans that share any source byte, or one marker span that crosses an LF,
make every line they touch ineligible as a row line and as a marker-only terminator.
Tools detect both conditions over the complete frontmatter-excluded document before
scanning individual lines. If such a line lies in a started candidate body, rule 4
refuses the candidate. This fail-closed rule is about table recognition only: the scan
does not merge, discard, or choose a semantic owner between §4 grammar matches.
Whatever markers §4 recognises remain preserved ordinary markers, and a `subhash`
marker among them addresses no row because the candidate is refused.
<!-- stay:overlapping-row-markers hash=sha256:9b6f -->

0. The scan runs after §5.3 has excluded a recognised leading YAML frontmatter block,
 on lines split at LF after §8's line-ending normalization. Frontmatter lines never
 start or belong to a candidate. A line §3.3 masks as fenced code is ineligible as a
 row line; if one occurs inside a candidate body, rule 4 refuses that candidate rather
 than bridging across the code. On every other eligible line, §4 marker spans are
 replaced by the opaque tokens above before any delimiter is sought. **For this row
 scan and for row ownership, that token rule also applies inside inline code spans,
 indented code, and any other literal-code form §5.4 otherwise permits a tree reader
 to ignore.** This local rule overrides that latitude: outside a §3.3-recognised fence,
 a parsed marker carrying `subhash` on an accepted body row addresses that row.
1. A line has a **working slice** only when it starts with zero to three **spaces**,
 U+0020, followed by a non-space. Remove those initial spaces, then remove trailing
 ASCII whitespace (space, tab, form feed, vertical tab). A tab is not a leading
 space here, for §3.3's reason: expanding one needs a column model this rule
 deliberately does not have. A **row line** is one whose working slice contains at
 least two distinct unescaped `|` delimiters, begins with the first, and ends with the
 last.
2. At each line, the scan tests a possible **header** row line followed immediately
 by a possible **delimiter** row line whose cell count equals the header's. Fix the
 cell boundaries first. The delimiter source line MUST contain no marker token, form
 feed, or vertical tab; these checks use the LF-split source line before rule 1 removes
 trailing whitespace. Each delimiter cell, trimmed of spaces and tabs only, MUST then
 be an optional `:`, one or more `-`, an optional `:`, and nothing else. A candidate
 starts only when that whole pair passes. When it fails, no candidate owns or reserves
 either line; advance one line and test again.
3. Starting after the delimiter, the **candidate body** continues to the first blank
 line (§5), the first **marker-only line**, or the end of the document. A marker-only
 line is a nonblank LF-split line that, after deleting one or more complete marker
 spans, contains only ASCII whitespace. Those are the only successful terminators and
 are not part of the body. A line §3.3 masks as fenced code never terminates a
 candidate, even if its source has that shape. Every other line in the candidate body
 MUST be a row line. If all are, the candidate is a table and they are its body rows.
4. A started candidate with any non-row line in its candidate body has **no child
 blocks at all**, including the row lines before the refusal. That is per table
 rather than per row, and the reason is ordinals: §9.2 tier 2 maps markerless
 children by position, so two tools that disagree about whether one line is a row
 disagree about the ordinal of every row after it. Refusing the whole table is the
 only failure that keeps them in step.
5. The scan is left-to-right and candidates do not nest. Once a pair passes rule 2
 and starts a candidate, the lines through its successful terminator belong to that
 candidate for this scan whether it succeeds or is refused. A later pair inside that
 extent MUST NOT start a second candidate table.
<!-- stay:5zNzAzaz hash=sha256:6fdda5703e41 -->

A `|` is **escaped** where an odd number of consecutive `\` immediately precedes it
in the tokenized working slice, and is a cell delimiter otherwise. A marker token
breaks that consecutive run. **Cells** are what the unescaped delimiters separate,
discarding the empty field before the first and after the last. After those boundaries
are fixed, marker tokens are deleted from the cells. A cell keeps every other escape
verbatim: a tool that turned `\|` back into `|` would give `| a\|b |` and `| a | b |`
the same row body.
<!-- stay:sw6uqdt4 hash=sha256:4b55ff565b0b -->

**This rule is narrower than GFM's, in the direction of refusing rather than
guessing**, and the differences were checked rather than assumed. GFM recognises rows
without outer pipes, treats an ordinary non-blank line as a one-cell body row, and can
end a table at a block-level construct. This parser-free rule refuses the first two and
accepts only a blank line, a marker-only line, or EOF as the end: a heading or other
block construct touching the table therefore refuses child addressability unless a
blank line separates it. It is also narrower than a GFM **parser's** view of a row it
does accept: a parser pads or truncates a row to the header's cell count and this rule
does neither, so a tool implementing §5.6 MUST take a row's cells from the rule above
rather than from a parser's cell list even where it has one. Two tools that read the
same ragged row through those two routes hash it differently. The delimiter-line
marker rule preserves that refusal-only relation: a marker is not deleted to
manufacture delimiter syntax. Form feed and vertical tab are a separate deliberate
narrowing. `cmark-gfm` accepts them where the pinned MarkdownIt table rule refuses
them, so §5.6 rejects both rather than making child addressability depend on the parser
an implementation happened to test against.
<!-- stay:NJuv6zuU hash=sha256:499a473f0ef5 -->

**Body and hash.** The **row body** is the row line with, in order:
<!-- stay:TOHH9OVO hash=sha256:974c4bcf4347 -->

1. its tokenized working slice split into cells as above;
2. every marker token deleted from its cell (§3);
3. each cell's leading and trailing ASCII whitespace (space, tab, form feed,
 vertical tab) removed;
4. inside each cell, every `\` replaced with `\\`, then every `|` replaced with
 `\|`, in that order;
5. the encoded cells joined with a single unescaped `|`.
<!-- stay:AYBz6TkN hash=sha256:8243bacba0e6 -->

What remains is normalized and hashed exactly as §8 specifies, and written under
`subhash`, the reserved key §5.5 defines.
<!-- stay:ykGYB0DP hash=sha256:8f1992d93a64 -->

**Trimmed rather than source-sliced, and that is the whole difference from §5.5's body
rule.** Every table formatter re-pads cells, and §8 strips trailing whitespace per line
but never collapses interior whitespace, so a row body taken from the source slice
would drift on a format run that changed no content at all. Trimming each cell makes
cell padding and column alignment non-drift, which is the consequence §5.5 gets from
stripping the list marker: a bullet glyph is not drift there, a column width is not
drift here.
<!-- stay:Tvlt3ksC hash=sha256:3e183592f335 -->

The encoding makes the join reversible. `\\` represents a literal backslash, `\|`
represents a pipe that belonged to a cell, and only an unescaped `|` separates cells.
Escaping both characters matters: without it, the two cells in `| a\ | b |` and the
one cell in `| a\|b |` would both produce `a\|b`. The separator is `|` rather than a
newline or a space so an empty cell survives; joining with LF would put a blank line at
one end of the body for §8 step 3 to drop and hash `| | a |` the same as `| a |`.
<!-- stay:FzFrVCd4 hash=sha256:0c5f2e5395b5 -->

**Carrier.** A row marker sits **inside the row's last cell, flush against that cell's
content**: no whitespace at all between the cell's last character and the marker's
opening delimiter.
<!-- stay:pM6UX7pY hash=sha256:5a86474bcc78 -->

```md
| fruit  | crates | note                                              |
|--------|--------|---------------------------------------------------|
| apples | 3      | picked early<!-- stay:r1 subhash=sha256:fb1c -->   |
| pears  | 5      | still ripening<!-- stay:r2 subhash=sha256:4879 --> |

<!-- stay:tb1 hash=sha256:9c04 -->
```

A last cell that is the marker and nothing else is permitted. In that case **flush**
means that the marker's opening delimiter immediately follows the last cell's opening
unescaped `|`; any padding that was already between the empty cell and its closing pipe
stays after the marker. It is the degenerate case of the same placement and it survives
the same tools.
<!-- stay:48HhqNh6 hash=sha256:3f2caaf6cb5b -->

**Flush is a MUST, and the reason is §8 rather than taste.** §8 removes markers and then
strips trailing whitespace **per line**. A list-item marker sits at the end of its line,
so removing it leaves whitespace §8 strips, and stamping an item leaves its list's hash
byte-identical for free. A row marker sits mid-line, so a space written in front of it
survives that removal as interior whitespace §8 keeps, and stamping a row would drift
its own table for nothing. Written flush, the removal restores the row's bytes exactly.
This is the one place where the two forms of child identity do not behave alike, and
writing the marker flush is what hides the difference.
<!-- stay:AAdenEdx hash=sha256:7ab5ad4ee7cb -->

**Rules for readers.** §5.5's reader rules are phrased about `subhash` and apply here
unamended. Two are worth restating in the table's terms:
<!-- stay:bPrvTru8 hash=sha256:e2003e6f2ca5 -->

- A marker carrying `subhash` on a body row of the **sole accepted candidate in its
 selected §5 container** addresses **that row** and MUST NOT be treated as binding to
 the selected container. Wherever in that accepted row's source line it sits, it is
 addressing that row and nothing else.
- A marker carrying `subhash` anywhere else in a table, on the header line, on the
 delimiter line, or anywhere in a table the rule above refused, addresses no child
 block. It is nobody's stay: a conforming tool MUST NOT resolve it, MUST NOT treat it
 as identifying the selected §5 container either, and MUST preserve it verbatim (§4).
 A linter SHOULD report it, and §5.5's requirement on that report holds here too, that
 a refused table and an unaddressed marker are told apart rather than merged into one
 silence.
<!-- stay:GS9ytnPY hash=sha256:71bab0ff4ad8 -->

**Rules for writers.**
<!-- stay:jAdLcTTL hash=sha256:160a99efe65e -->

- A bare selected-container marker written before v1.6 MAY legally follow the last
 row's closing pipe under §5. A row-stamping writer MUST NOT let that legacy carrier make the table
 impossible to upgrade. If the ordinary scan plus the post-scan selected-container
 filter does not place the requested row in an addressable candidate, the writer MUST
 test one **migration probe** when the selected §5 block's last content line has this
 exact suffix after its final unescaped delimiter in the tokenized line: only ASCII
 whitespace and one or more complete marker spans, all without `subhash`. The probe
 relocates those spans verbatim and in order to a marker-only line after the
 prospective candidate body, leaving every non-marker byte unchanged. It then reruns
 the selected §5 segmenter over the complete in-memory proposed document, performs the
 complete ordinary scan and the post-scan selected-container filter, and succeeds only
 when the suffix-bearing line becomes the candidate's last body row and the requested
 row belongs to the sole accepted candidate in that selected container. The probe
 itself MUST NOT write. If it fails, the source stays byte-identical. Readers never use
 this probe.
- A tool that mints a row stay MUST write the marker in the row's last cell, flush
 as the Carrier rule defines (against its content, or its opening delimiter when the
 cell has none), and MUST NOT write one on a header or delimiter row.
- A tool that mints a row stay MUST put the selected §5 container's own stay on a
 marker-only line after the candidate body, moving the container block's existing stay
 there if necessary or minting one there if the container has none. The marker-only
 line MAY be the candidate's terminator or MAY follow a blank-line terminator. The tool
 MUST NOT put that marker after a body row's closing pipe: the opaque marker token would
 follow the last delimiter, rule 1 would reject the line, and the write would make its
 new row stays unaddressable. This is §5.5's container-stay rule with the surviving
 table-adjacent carrier made explicit.
- Moving an existing container marker, whether found by the migration probe or by the
 ordinary scan, is provisional until the selected §5 segmenter has run over the
 complete proposed document, the complete ordinary scan and post-scan
 selected-container filter have run again, and the requested row remains a child block
 of the sole accepted candidate in its container. A marker carrying `subhash` is never
 eligible to move as a container marker. A writer MUST commit the relocation and row
 write atomically, or leave the source byte-identical.
- **A tool whose write changes the selected §5 container's normalized body MUST refresh
 every stored `hash` that binds to that container in the same pass.** Minting alone
 does not change the container body, because the carrier is flush; a pass that also
 reflows or re-pads the table can. Before writing, the tool MUST compare every such
 stored hash with the complete pre-write container body, including any adjacent prose
 in that block. If one is already drifted, the tool MUST report that fact and MAY abort
 without changing the source. If it proceeds, it MUST refresh the hash from the complete
 post-write container body. This container rule does not exempt the tool from refreshing
 a row's `subhash` when it changes that row's body. The two forbidden outcomes are
 preserving a hash made stale by the tool's own write, and clearing pre-existing drift
 without first reporting it.
- §5.5's hash-filling rules apply unchanged: a tool that fills in missing hashes MUST
 write `subhash` for a row marker, and MUST NOT add a `hash` to any marker that
 already carries `subhash`.
<!-- stay:ABOUzu6d hash=sha256:56fd5ce6c8ea -->

**One row scan, with the existing §5 container split.** Neither built-in segmenter
parses GFM tables: blank-line segmentation sees a run of lines, and the CommonMark
segmenter of §5.2 reads the table source as a paragraph. Both apply the same
parser-free scan to find candidate rows, and every candidate row uses its selected
§5 block as the §9.2 container. Outside §5.4's agreement subset those selected blocks
can differ even though the rows do not. A parser with a GFM table extension may also
hold a narrower table node, but that node is not a third §5 profile and does not
replace the selected container. Neither built-in profile has a second row-recognition
rule.
<!-- stay:W84ejxWc hash=sha256:e72c68c4fe64 -->

That buys the thing §5.5 could not offer: **a document using row identity can sit
inside the agreement subset of §5.4.** A table with a blank line on each side is one run
and one node, and its rows are addressable identically under both segmenters, where
§5.4 has to warn that the subset does not extend to child list items. Outside that
subset, ordinary built-in boundaries can change the **container** rather than the row:
for example, a touching heading can make the blank-line and CommonMark segmenters
select different blocks. A GFM extension can represent the table separately for its
own purposes, but conforming attachment still uses the block chosen by one of those
two profiles. The candidate row lines do not change. Authors who need the same
container across both profiles should blank-separate adjacent constructs from the
table.
<!-- stay:lxYwDhFE hash=sha256:65132407a9e7 -->

**What the carrier cannot buy, stated rather than claimed away.** A formatter that
aligns a table's columns pads every cell to its column's width, so a row marker widens
its column and the **next** format run re-pads the whole table. The table's hash drifts
with no content change, and no placement can prevent it: the marker is inside the cell
and the padding is outside it. Both measured tools that actually format tables align
columns and lose the table's hash under the flush carrier. The two holds came from
tools that treated the source as paragraph text, not from table formatting. The
consequence belongs to §9.2: tier 2 is gated on the container's hash matching, so it is
**weaker for rows than for list items** on any document a column-aligning formatter
maintains, and tiers 3 and 4 carry the load there.
A hash rule that knew what a table was could close this, which is exactly the coupling
§8 has never had and does not acquire here.
<!-- stay:jtxAgFVL hash=sha256:fc1cb405d9c0 -->

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
this order. A marker-shaped string inside a fenced code block is not a marker (§3.3),
so it stays in the body and is hashed with the rest of it:
<!-- stay:kRGUAMQN hash=sha256:09856ff76283 -->

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

A child stay (§5.5, §5.6) resolves on the same discipline as §9.1, strongest evidence
first, with one addition: a child is resolved **inside its container**, so its rivals
are its siblings rather than the whole document. That containment is what answers
§5.1's stated reason for deferring item identity, which was near-duplicate items:
`Done` competes only with the other items of its own list. Every tier below is written
about child blocks and containers rather than about lists, which is why version 1.6's
table rows resolve on it unchanged: §5.6 makes an addressable candidate the only table
candidate in its container, so a row's container siblings are exactly that table's
other body rows.
<!-- stay:7mqLi8iw hash=sha256:92df494a3a6f -->

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
2. **CONTAINER HASH**, the container's stored hash matches → the container is unchanged
 modulo §8 normalization, so the remaining markerless children map by ordinal.
 This tier is narrower than it looks: a container's body keeps its `- ` and `1. `
 prefixes, so a bullet-glyph change or a renumber breaks the container hash even
 though §5.5 makes both non-drift for every child. Those edits fall through to
 tier 3, where the child hashes correctly see no drift. **A table's cell padding is
 the same shape and bites harder**, because a formatter re-pads columns without being
 asked and a row marker is what makes it re-pad: §5.6 makes padding non-drift for a
 row, and the table's own hash breaks on it anyway, so this tier is weaker for rows
 than for list items on any document a column-aligning formatter maintains.
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
<!-- stay:BHNQSFUx hash=sha256:dc1980a0e5d2 -->

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
| **A document about markstay damaged by markstay** (an example marker in a fence read as a real stay, so a restamp rewrites the example, the fence cannot be stamped, and two examples sharing an id are a duplicate nothing can clear) | text inside a fenced code block is content, not markup (§3.3). |
| **Scope creep into an annotation product** | core stays at identity + resolution; annotation is a separate, layered spec (§14). |
<!-- stay:K6J3h42A hash=sha256:bbd47062a532 -->

## 14. Non-goals
<!-- stay:x3XFUhd4 hash=sha256:2f59dc50d4cf -->

- Annotation, comment storage, threads.
- Transclusion / embedding.
- Inline-span identity.
- Recognising **indented** code blocks or **inline** code spans as content the way
 §3.3 recognises a fenced block. Both need context a dependency-free tool does not
 have, and §3.3 states why each is left out.
- Provenance tracking and knowledge-graph construction.
- A backend, accounts, a hosted registry, or any global / cross-repo stay
 namespace.
<!-- stay:Itv36Vd3 hash=sha256:1f55f9d4341a -->

(Loose-list and blank-line-fence single-stay attachment was a v1 non-goal; it is
resolved by CommonMark-tree attachment in v1.1, §5.2. List-item identity was a v1
non-goal; it is resolved for direct list items in v1.3, §5.5. Table rows were the
same idea with a different carrier, a marker inside the last cell of a one-line row,
deferred until that carrier was shown to survive real renderers; it was, and they are
resolved in v1.6, §5.6.)
<!-- stay:umfBvzuc hash=sha256:cfa156aee6a3 -->

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

Every conforming tool, whichever segmenter it implements and whether or not it
implements §5.5, MUST apply §3.3: a marker-shaped string inside a fenced code block is
content. It is not recognised as a marker on the read path, not removed from a body
before hashing, and not treated as its block's stay on the write path. A tool that
skips this damages the documents most likely to contain marker examples, which are the
documents that explain markstay to a new adopter.

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

Child-block identity (§5.5 for list items, §5.6 for table rows) splits into an optional
half and a mandatory one, and the split is not the same as §5.2's. **Segmenting and
resolving child blocks is optional**: a tool that never sees a list item or a table row
is conforming. **Recognising `subhash` on the write path is not**, and every conforming
writer MUST:
<!-- stay:gY4kwGJH hash=sha256:f217a5e2ae9f -->

- not add a `hash` to a marker that already carries a `subhash`, and
- not treat a block as stamped on the strength of a marker that carries one.
<!-- stay:GbIyKsIr hash=sha256:c2c16e103d57 -->

Those two are a compatibility shim rather than a feature, and they are mandatory
because §4's preserve-unknown-keys rule does not reach them: a writer that adds a key
of its own, or that reads a child marker as evidence the block is done, is not acting
on a key it does not understand, it is acting on its own idea of the document. A tool
without the shim damages a document that uses §5.5, in both of the ways named above and
both measured rather than predicted, so "ignore the section entirely" is conforming for
a reader, subject to the one rule below, and never for a writer. Both rules are phrased
about `subhash` rather than about lists, so they already cover a row-stamped document;
that was checked against every published write path rather than inferred from the
wording.
<!-- stay:Ap9TiTxs hash=sha256:4136380c47da -->

**Version 1.6 adds a third rule, and this one binds every reader:** a tool MUST NOT
report a marker carrying `subhash` as the stay of the block that contains it. Ignoring
the marker is conforming, and so is ignoring §5.5 and §5.6 entirely; attributing it to
the container is not. This promotes §5.5's first reader rule out of the optional half,
and it is cheap enough to belong there: one key comparison, no segmentation and no
parser. What it prevents is silent. A reader without it hands a consumer a real id
bound to the wrong block, and nothing in the output says so. Version 1.6 makes this an
error rather than an omission because rows widen the exposure: a row marker sits
mid-block rather than on a line of its own, so a whole table's rows can be reported as
one block's stays.

A tool that does implement child identity MUST apply the §9.2 ladder for child stays,
and MUST emit no child blocks at all, rather than guess a boundary, for a list that
falls outside its segmenter's profile or for a table its §5.6 recognition rule
refuses.
<!-- stay:3dCNYT0A hash=sha256:7c3233f424e0 -->

Any conforming tool that segments a document, whichever segmenter it implements,
MUST exclude a leading YAML frontmatter span (§5.3) before segmenting, and MUST
NOT stamp, hash, or attach a marker to it.
<!-- stay:RW4LozSB hash=sha256:3eae6ace5b03 -->

## 17. Version history
<!-- stay:lUqH9hHD hash=sha256:9fe14861072a -->

| Version | What it changed |
|---------|-----------------|
| **1.6** | Adds child-block identity for GFM table body rows (§5.6), on the same reserved `subhash` key and the same §9.2 ladder as list items: a different carrier and a different body rule, not a second identity model. The carrier is a marker inside the row's last cell, written flush against the cell's content, or against the cell's opening delimiter when the cell has none, so stamping a row leaves its table's hash byte-identical; the row body is the row's cells trimmed, reversibly escaped, and joined, so cell padding is not drift and cell boundaries cannot collide. Row recognition is one parser-free line scan shared by both segmenters, so unlike a child-stamped list a row-stamped table can sit inside §5.4's agreement subset. Lifts the remaining half of the §5.1 deferral and the §14 non-goal; inline spans stay deferred. Adds one rule binding every reader (§16): a marker carrying `subhash` MUST NOT be reported as the stay of the block that contains it. Reconciles §4 with §3.3 and the host comment syntaxes: normalized LF is valid inside quoted marker values, while `-->` in an HTML body and `*/` in an MDX body are forbidden and never hidden by quotes. |
| **1.5** | Text inside a fenced code block is content, not markup (§3.3): a `stay:` marker there identifies no block, is not removed from a body before hashing (§8), and does not make its block stamped (§5). Fence recognition is line-based, so for every fence it recognises, what counts as a marker does not depend on which segmenter a tool implements, and §5.4's divergence axis narrows to what the line rule cannot see. Indented code blocks, inline code spans, and a fence that is quoted or indented more than three spaces are deliberately not covered. A block whose body contains a marker-shaped string inside a fence hashes over that string now and reports drift once; nothing else changes. |
| **1.4** | Recommends reporting `unmatched` when quote recovery has no above-threshold candidate and `ambiguous` when a candidate reaches the threshold but fails the margin (§10), while keeping plain DETACHED conforming. A machine-readable reason, when exposed, uses those names and meanings; candidate and evidence schemas remain non-normative (§16). Also corrects §9.2's version 1.3 note and both Python references: the historical-uniqueness gate belongs to CHILD HASH tiers 3 and 4, while CHILD QUOTE may use permitted sibling context to distinguish duplicate child bodies. The commit rule, document syntax, and DETACHED outcome are unchanged. |
| **1.3** | Adds child-block identity for direct list items (§5.5) and their resolution ladder (§9.2), carried by the new reserved key `subhash` (§4) so that a tool which does not implement the section cannot overwrite a child's evidence. Lifts the list-item half of the §5.1 deferral and the §14 non-goal; table rows and inline spans stay deferred. Segmenting and resolving child blocks is optional; two write-path rules that keep an unaware tool from damaging a child-stamped document are not (§16). A document with no child markers is unaffected under either segmenter. |
| **1.2** | Excludes leading YAML frontmatter from segmentation under both segmenters (§5, §5.3), and restates the two segmenters' agreement condition as the agreement subset (§5.4), which v1.1 stated too narrowly. Normative change to §5; grammar, identity, hashing, and recovery unchanged. A marker already stamped onto frontmatter usually becomes an orphan error. |
| **1.1** | Adds CommonMark-tree attachment (§5.2) as an optional segmenter, so a loose list, a blank-line fence, or a blockquote with an internal blank line can carry a single stay. Adds no requirement to a baseline tool and changes no marker's meaning; its statement of when the two segmenters agree was corrected in 1.2. |
| **1.0** | The marker grammar (§3, §4), the identity model (§2, §7), blank-line attachment (§5), hash normalization (§8), quote recovery and the commit rule (§9), the detached state (§10), and the AI editing contract (§11). |
<!-- stay:wpHe8SeN hash=sha256:0fc918fe51fa -->

markstay does **not** offer a compatibility guarantee across versions at this
stage. Where a version corrects a defect, it corrects it rather than carrying the
defect forward behind a flag; §17 exists so the change is legible, not so it can be
avoided.
<!-- stay:Dqoh2DIU hash=sha256:16977c266dfc -->
