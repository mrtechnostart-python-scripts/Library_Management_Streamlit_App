# First-run check

## Environment and installation

- Linux x86_64, Python 3.13.5.
- Created a new virtual environment outside the repository with `python3 -m venv`.
- Installed `requirements.txt`: pandas 2.3.3, Streamlit 1.67.0, streamlit-option-menu 0.4.0.
- `python -m pip check` reported no broken requirements.
- The old pins failed a binary-only installation check on Python 3.13 because numpy 1.21.5 has no compatible distribution.

## Automated checks

`python -m unittest discover -s tests -v`: 10 tests pass.

Tests copy `Library.py` into temporary folders. Most begin without any database; one copies the included database and confirms all rows are preserved. They do not modify the repository’s `library.db`.

Covered:

- All six pages render with the required tables available.
- Add, display, and delete a saved book, including apostrophes in names and codes.
- Reject an issue for an unknown book with a warning rather than a missing-table exception.
- Issue a known book, save the seven-day return date, and display the record.
- Warn on missing book and issue records during deletion.
- Delete issue records due today or in the future.
- Display a two-day overdue fine of 20 INR without deleting the record.
- Show an actionable error for an invalid saved return date.
- Keep the included database’s rows on startup.

AppTest cannot interact with the third-party option-menu component. Tests select pages by mocking only that menu function; the real menu was checked separately in the browser.

## Actual browser run

Started `streamlit run Library.py` using the fresh environment, with headless mode and local server options for this test computer. The health endpoint answered, and the browser at `http://localhost:8501` rendered the actual app.

Using a copy of the included database:

- Navigated through Add Books, Issue Book, and Delete Records using the real menu.
- Added a test book and issued it to a test college ID.
- Removed the resulting non-overdue issue record and saw the success message.
- Captured the actual Add Books page at 1280 × 1000 for the README, without personal data.

## Scope

Windows, macOS, other Python versions, hosted operation, real patron data, multi-user use, and payment handling were not tested. The GitHub feedback form is checked locally for structure; its published rendering and submission require the founder to merge the pull request. No test issue was submitted.

The repository’s existing database and `BRAINER.md` remain unchanged. No database migration or external account is required for these changes.
