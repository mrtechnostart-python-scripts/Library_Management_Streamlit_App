# Book CSV export check

Tested on Linux with Python 3.13.5 and the pinned `requirements.txt` dependencies.

## Automated checks

`python -m pip check` passed. `python -m unittest discover -s tests -v` passed all 24 tests: 18 existing regressions plus six CSV export cases.

The CSV cases use temporary app copies and databases. They verify:

- Exact `BookName,BookCode,DateAdded` headers and UTF-8 bytes without a BOM.
- Unicode, emoji, commas, doubled quotes, LF and CRLF within fields, whitespace, empty strings, leading-zero codes, duplicate codes and formula-like text survive a CSV reader round trip.
- Both empty collections produce exactly the header with CRLF.
- Collection switching replaces the download content and filename, and saved additions/deletions refresh it.
- Sample export opens only the sample database; a missing existing database is not created. Both initialized database files remain byte-for-byte unchanged when exporting.
- Issue/student records are excluded. SQL NULL and binary values show an actionable error and suppress the download rather than losing information.

## Browser checks

Ran an unmodified temporary copy of the app at `http://localhost:8501`, with separate temporary existing and sample databases. No repository database was used for browser edits.

Used the real third-party menu to open Add Books. Clicked the existing collection download, switched to Sample collection, and clicked its download. Chromium's download history showed completed downloads for both. Read the download URLs from that history and verified the served attachment bytes with Python's CSV reader against the seeded records. The attachment headers specified the correct collection-specific filename and `text/csv; charset=utf-8`. Both database SHA-256 hashes were unchanged after these exports.

Emptied the temporary sample table, reran via Display All, and clicked the sample download again. The app showed zero records; Chromium recorded a completed download and its content was exactly `BookName,BookCode,DateAdded\r\n`.

Checked 390, 768 and 1280 px viewport widths: no page-level horizontal overflow. At 390 px the collection identity, scope description, empty-state text and download button remained legible and usable.

The browser harness assigns random filenames to downloads in its history; HTTP attachment filenames were verified separately. Spreadsheet applications and other operating systems were not tested. The README documents importing all CSV columns as text and avoiding formula evaluation for untrusted values.

## Scope

This is a read-only export of three book text fields, not a full database backup. Startup retains the existing first-run/sample initialization behavior. The CSV format and unsupported-value policy are documented in the README for the next import milestone; import is not implemented here.
