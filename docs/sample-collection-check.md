# Sample collection check

## Run it

Install `requirements.txt` in the documented Python environment, then run:

```bash
streamlit run Library.py
```

Choose **Sample collection** in the sidebar before entering test records. Follow the [README walkthrough](../README.md#try-a-separate-sample-collection) to add `TRY-001`, issue it to `TEST-001`, restart, return it through **Delete Records**, and restart again.

A new session defaults to **Existing library**. Sample mode uses only `library-sample.db` beside the app. It seeds three books once, then preserves changes. Stop the app before removing that sample file to start over. Never remove `library.db` to reset the sample.

## Automated checks

Tested on Linux x86_64 with Python 3.13.5 and the pinned dependencies in a fresh virtual environment.

- `python -m pip check`: no broken requirements.
- `python -m unittest discover -s tests -v`: 18 tests pass (ten first-run regressions and eight sample checks).
- `git diff --check`: passes.

All app tests run in temporary folders. The sample tests verify:

- The original default path remains `library.db`; sample selection is explicit.
- Sample startup connects only to `library-sample.db`, with the existing database byte-for-byte unchanged.
- Sample mode does not create a missing `library.db`.
- Repeated initialization does not duplicate sample books or restore deleted seeds, even after all books are deleted.
- An already populated, unmarked sample database is not seeded over.
- Add → issue → new session → return → new session preserves the saved book and removes the returned issue.
- Switching collections clears unfinished form entries.
- Symlinks and hardlinks to the real database are refused before opening a sample connection.

AppTest selects pages by mocking only the third-party menu function. The real menu is covered by the browser check below.

## Actual browser check

Served a temporary copy of the app and included database at `http://localhost:8501`.

- Confirmed the default collection and its visible existing-data message.
- Selected sample mode and used the real Add Books and Issue Book menu pages to save `My Test Book` / `TRY-001` and its issue to `TEST-001`.
- Stopped and restarted the Streamlit server. Reopened the app, confirmed the default was still Existing library, and selected Sample collection again.
- Opened Display Records, then returned the saved issue through Delete Records. The app showed success and an empty updated issue table.
- After shutdown, queried the sample file: four books remained, including `TRY-001`; there were no remaining issue records.
- SHA-256 checks before and after matched for both the temporary existing database and the repository's untouched `library.db`.
- At a 390 × 844 viewport, opened the collapsed sidebar and confirmed both collection choices and the active sample-file message were readable.

## Scope and handoff

No dependencies, database migration, external account, or hosting change is required. The sample initialization marker is created only in the separate sample file. Neither `library.db` nor `BRAINER.md` was changed.

The app's existing limitations remain: duplicate/empty entries and availability are not enforced; overdue returns display a fine and keep their issue record. This walkthrough returns a newly issued, non-overdue book. Windows, macOS, multi-user operation, real patron data, and hosted operation were not tested.

Changes are for founder review through the `brainer/work` pull request. Only the founder merges and deploys.
