# markstay render-survival corpus: the table-row carrier

A GFM table row is one line, so a row marker has exactly one position available to
it: inside the **last cell**, before the closing pipe. Every other placement puts the
marker outside the row it addresses. This fixture is that placement, the one
`SPEC.md` §14 names as the gate on table-row identity ("stay deferred until that
carrier is shown to survive real renderers"), and the one no other fixture here
covers: `blocks.md` puts the table's marker on its own line *after* the table.

Each data row carries its own marker under the reserved `subhash` key (§5.5's child
carrier), and the table carries an ordinary block stay as a marker-only chunk, so
container and rows are addressed at once. The third row's last cell is the marker and
nothing else, the degenerate placement a formatter is most likely to collapse.

| fruit  | crates | note                                                 |
|--------|--------|------------------------------------------------------|
| apples | 3      | picked early <!-- stay:rw1 subhash=sha256:1a2b -->    |
| pears  | 5      | still ripening <!-- stay:rw2 subhash=sha256:3c4d -->  |
| plums  | 7      | <!-- stay:rw3 subhash=sha256:5e6f -->                 |

<!-- stay:tbl1 hash=sha256:7a7dd385e703 -->
