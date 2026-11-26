# Book CSV import check

## Environment and scope

Tested on Linux, Python 3.13.5, with the pinned dependencies in `requirements.txt`. All checks used temporary app copies and evaluation databases. The repository's tracked `library.db` was not edited. No hosting or deployment was performed.

Commands:

```bash
python -m pip check
python -m unittest discover -s tests -v
```

Result: no broken requirements; **38 tests passed**, including all 24 earlier regression tests and 14 new import tests.

## Automated coverage

- Export → import into an empty destination → export reproduces identical UTF-8 CSV bytes. SQLite text values and insertion order survive reopening the database.
- Leading-zero codes, Unicode, commas, quotes, LF/CRLF inside fields, surrounding spaces, empty strings, formula-like text and dates as stored are preserved without coercion. Optional UTF-8 BOM accepted.
- Empty files, BOM-only files and header-only files produce errors and add no books.
- Wrong header order, extra headers, wrong case, invalid UTF-8, missing/extra fields, blank rows, unterminated quotes, quotes in unquoted fields, text after closing quotes, and a malformed last row are rejected without database changes.
- Duplicate codes within a file (including empty codes) identify the duplicate record. Codes already in the destination block all inserts and retain the existing rows.
- Trigger failure after earlier inserts rolls back every imported book. Simulated commit failure also rolls back. A locked destination does not write. An unrelated pending transaction is not committed or rolled back by import.
- Streamlit AppTest checks that preview writes nothing, identifies the destination and displays text values; explicit confirmation writes the books; the upload is consumed on a later rerun.
- Collection switching invalidates the upload, even when switching back. A conflict introduced after preview is caught before import.
- UI validation and write failures show actionable errors without uncaught exceptions.
- Round trips and UI import retain issue rows and leave the other collection unchanged.

The pure helper tests load only the CSV functions from the app's syntax tree to avoid executing its page. AppTest's uploader is stubbed because these tests do not drive a native file picker; the real uploader was separately verified in the browser.

## Actual browser checks

Started the unchanged app entry point from `/tmp/library-import-browser/Library.py` on `http://localhost:8501`, using fresh local evaluation files.

1. Used the real Add Books menu and file picker to upload a CSV created with the app's export helper. It contained two books with leading-zero codes, Unicode, quoted commas, an embedded newline, and surrounding whitespace.
2. The preview identified `Existing library · library.db`, reported two validated books and offered an explicit confirmation. A separate SQLite read confirmed zero books before confirmation.
3. Switched to Sample collection: the upload and confirmation disappeared. Switching back did not restore them.
4. Uploaded again and confirmed into the empty Existing library evaluation database. The success message reported two added books; a SQLite read matched the source text exactly.
5. Uploaded the same file again. The browser identified the existing code `0007`, offered correction guidance, and showed no confirmation.
6. Uploaded a file with a malformed final row. The browser identified CSV record 4 / line 5 and the two-field error. No confirmation was offered.
7. At 390 × 844, opened the sidebar, selected Sample collection, uploaded the valid CSV and confirmed. The preview fit the narrow main content area and named the sample destination. Both imported books were added alongside the three sample seeds.
8. Read both saved files: Existing library held exactly the two imported rows; Sample collection retained its seeds plus the two rows. Restarted the Streamlit server and opened a new browser session; Existing library still reported two saved books, with a fresh empty uploader.

## Limits

This format transfers books only; it is not a full backup and does not restore students or issue records. Manual Add Now! still permits duplicate/empty entries; import alone enforces distinct codes. Dates remain stored text rather than being calendar-validated. Large-file performance, Windows setup and general multi-user operation were not established by these checks. The existing Streamlit upload limit and Python CSV field-length limit still apply.
