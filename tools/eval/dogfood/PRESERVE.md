This Markdown document uses markstay markers: HTML comments of the form
`<!-- stay:ID ... -->` (or, in MDX, `{/* stay:ID ... */}`) placed on or just after
the block they identify. Each marker is a stable address that other tools rely on,
so it must survive your edit.

When you edit this document you MUST:

- preserve every existing `stay:` marker exactly as written, including its id and
  any `hash=` / `quote=` attributes; do not remove, reword, renumber, or relocate it;
- keep each marker attached to the same logical block it was on before, even when
  you move, reword, or reformat that block;
- mint a fresh id (any new short token) only for content that is genuinely new;
- never reuse an existing id for different content;
- if you must drop a marker, report it explicitly in your reply, never drop one
  silently;
- never introduce a duplicate id (the same id on two blocks).

Return the edited Markdown with every original marker still present and in place.
