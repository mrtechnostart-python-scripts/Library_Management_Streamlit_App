# Book search verification

## Environment and scope

Tested on Linux with Python 3.13.5 and the pinned requirements. App version: `0.3.0`. All testing used temporary app/database copies, never edits to the tracked `library.db`. Changes are review-ready on `brainer/work`; the founder must merge and manage any deployment.

## Automated checks

`python -m pip check`, `python -m unittest discover -s tests -v`, `python -m compileall -q Library.py tests`, and `git diff --check` passed. The full suite has 51 tests (44 existing plus seven search tests).

Search checks cover:

- Empty query and Clear search restore all saved text fields in insertion order, including blank fields and duplicate codes.
- Partial code/title matching, leading zeros, quotes, literal `%` and `_`, whitespace, Unicode, emoji, and substrings of multiline titles.
- Unicode case folding, including `STRASSE` matching `Straße`.
- SQL-shaped query text is treated literally. Dates and student/issue data are not search fields.
- Distinct no-match and empty-collection messages.
- Collection switching resets the query and results. Sample search opens only the sample database; a missing existing database stays absent.
- Search and clearing leave both prepared database files byte-identical.
- Add/delete changes through the app and newly saved book records are visible without cached results.
- Feedback is present on the new menu page and reports the updated app version.

The pre-existing startup, sample persistence/return, export, import confirmation/rollback and feedback privacy tests also pass.

## Actual browser checks

Started Streamlit from a temporary copy at `http://localhost:8501` and used its real option-menu component.

- Existing collection: `aRIHANT` found the saved Arihant Maths record; `123` matched two code substrings. A missing query showed the no-match guidance, then Clear search restored all three books.
- Sample collection: `sample-002` matched one seeded book. Switching to Existing library and back cleared the query and showed only the active collection.
- Uploaded an actual UTF-8 CSV with title `Straße Café, "読書" 📚` followed by a line break and `Second line`, code `0007`, and a text date. Confirmed the import into Sample collection, then searched successfully by `STRASSE`, `0007`, and `読書`. Four books were visible after clearing.
- Sample database bytes before and after the final search/clear sequence were identical. Both the repository database and the temporary existing database retained their original SHA-256: `e723e9f6e21e55dbcb810ec442d636288cd432dae50f1465809a0803eb429445`.
- Cleared only the temporary sample book table to test an empty collection. The browser showed the dedicated empty-collection guidance, with no stale table.
- Checked widths 390, 768 and 1280 px: no document-level horizontal overflow. At phone width, cleared the query, opened the sidebar, switched collections, searched an existing title, and visually verified its row. Wide table content scrolls within the table.

## Limits

Search filters the selected book table locally, using literal Unicode case-folded substrings. It does not normalize accents or whitespace, rank results, search issue/student records, or change book data. No schema migration or new dependency is needed. Large-collection performance and other operating systems were not tested. Existing startup behavior can initialize a missing database or seed a sample collection on first use; search itself only reads books.
