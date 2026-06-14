# Backup Strategy

Personal data is backed up on two independent paths so that a single failure never loses everything. One path targets a remote git repository for configuration, the other targets a physical USB drive for bulk data.

Configuration files, environment templates, and editor settings go to git because they are small, text shaped, and benefit from history. Bulk data such as photos and archives goes to the USB drive because it is large and does not need per-line history.

The checklist before any backup run is short:

- Confirm there is no uncommitted work in the tracked repositories.
- Confirm the USB drive is mounted and has free space.
- Confirm the most recent run finished without errors.

If any check fails the run stops rather than producing a partial backup that looks complete but is not.

```bash
rsync -a --delete ~/data /mnt/usb/data
```

Restore is tested quarterly by pulling a random file from each path and comparing it against the live copy.

| Path | Contents | Frequency |
|------|----------|-----------|
| git | configs | on change |
| usb | bulk data | weekly |

The goal is not maximum coverage but confidence that the data you care about can actually be recovered when you need it.
