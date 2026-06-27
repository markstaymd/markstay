# markstay render-survival corpus: the MDX (SPEC.md 3.2) profile

HTML comments are invalid in MDX v2, so an MDX target uses the comment-expression
form `{/* ... */}` instead of the `<!-- ... -->` HTML comment. This fixture is the
§3.2 serialization. It exercises two things the HTML-comment fixtures cannot:

- an MDX-aware round-trip (remark-mdx parse + stringify) must preserve the
  comment-expression marker;
- an MDX compile (@mdx-js/mdx) drops the JSX comment from the output (invisible),
  the same good outcome the HTML comment gets in a plain Markdown renderer.

(Nothing in this prose is a real marker: only the two lines below are, so the
parser sees exactly two ids, x1 and x2.)

A paragraph identified with the MDX comment-expression marker.

{/* stay:x1 */}

* alpha
* beta

{/* stay:x2 */}
