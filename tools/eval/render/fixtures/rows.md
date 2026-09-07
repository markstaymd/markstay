# markstay render-survival corpus: the table-row carrier

A GFM table row is one line. A §5.6 writer has one canonical carrier position: inside
the **last cell**, before the closing pipe. A reader accepts a `subhash` marker anywhere
on an accepted body-row source line, but this fixture measures the narrower writer
carrier that discharged §14's former gate on table-row identity. No other fixture here
covers it: `blocks.md` puts the table's marker on its own line *after* the table.

Each data row carries its own marker under the reserved `subhash` key (§5.5's child
carrier), and the table carries an ordinary block stay as a marker-only chunk, so
container and rows are addressed at once. The third row's last cell is the marker and
nothing else, the degenerate placement a formatter is most likely to collapse. In the
spaced form, one space separates that cell's opening delimiter from its marker.

| fruit  | crates | note                                                 |
|--------|--------|------------------------------------------------------|
| apples | 3      | picked early <!-- stay:rs1 subhash=sha256:1a2b -->    |
| pears  | 5      | still ripening <!-- stay:rs2 subhash=sha256:3c4d -->  |
| plums  | 7      | <!-- stay:rs3 subhash=sha256:5e6f -->                 |

<!-- stay:tbls hash=sha256:7a7dd385e703 -->

## The flush placement, which is the one §5.6 specifies

The table above separates the marker from the cell content with a space, which is what
a writer does by reflex. The table below writes it **flush** against the content
instead. Its marker-only carrier begins immediately after the last cell's opening
delimiter, with no cell content available to precede it.

The two tables have identical visible cell text and matching source padding. Their
marker ids remain unique, as the format requires, but each spaced/flush id pair has the
same width and the paired row markers carry the same `subhash`. The table-level ids
differ too, while their equal bodies carry the same `hash`. Those identifier bytes are
the remaining differences; they do not change the visible table shape or the marker
widths that drive formatter wrapping.

Both behave equally here, and that is the point of pairing them: the flush placement
buys nothing on **survival**. The GFM-preserving tools keep both; pandoc's native
writer converts both to a non-pipe table, so §5.6 refuses every output row whether or
not that particular cell wraps. What flush buys is the
container's **hash**, because §8 strips markers and then trailing whitespace *per
line*, and a row marker sits mid-line. Stripping the spaced form leaves a double space
§8 keeps, so minting a row stay drifts its table; stripping the flush form restores the
original bytes exactly. `carrier_hash.py` is that measurement.

| fruit  | crates | note                                                 |
|--------|--------|------------------------------------------------------|
| apples | 3      | picked early<!-- stay:rf1 subhash=sha256:1a2b -->     |
| pears  | 5      | still ripening<!-- stay:rf2 subhash=sha256:3c4d -->   |
| plums  | 7      |<!-- stay:rf3 subhash=sha256:5e6f -->                  |

<!-- stay:tblf hash=sha256:7a7dd385e703 -->

## The compact marked source required by the carrier gate

The first two tables begin aligned, so they test survival and the spaced/flush
comparison without proving that a compact marked input ever reaches the oracle.
This third table is deliberately unpadded before the first formatter run. It uses the
canonical flush carrier and no optional spaces around cell content or closing pipes.
The matrix records whether each path preserves an accepted row carrier and whether it
keeps the source compact, aligns it, or changes the table syntax entirely.

|fruit|crates|note|
|---|---|---|
|apples|3|picked early<!-- stay:rc1 subhash=sha256:1a2b -->|
|pears|5|still ripening<!-- stay:rc2 subhash=sha256:3c4d -->|
|plums|7|<!-- stay:rc3 subhash=sha256:5e6f -->|

<!-- stay:tblc hash=sha256:19f8df0d1796 -->
