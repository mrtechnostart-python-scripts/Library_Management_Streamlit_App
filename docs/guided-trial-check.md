# Guided sample trial check

Checked on Linux x86_64 with Python 3.13.5 and the pinned dependencies. App version: 0.4.0. All app and browser tests used disposable copies; the supplied database was not edited.

## Behavior

- Home offers an optional guide after Sample collection is selected. Existing library remains the default and cannot start the guide.
- Starting chooses an unused TRY-nnn code without writing records. The evaluator manually adds My Trial Book through Add Books and searches through Find Books.
- The guide remains above every existing menu page. Its confirmation queries the sample database for the exact title and code after page actions commit; it shows the saved date, not merely a completion checkbox.
- End guided trial, collection switching or a new session ends the guide without removing books. Restart instructions let the evaluator find the saved code again.
- Feedback on every page and in the guide includes only version, collection mode and an allowlisted task description. No code, title, records, entered values or paths enter the links. Both structured and plain issue links identify the attempted task, including before a successful save. No result is automatically claimed in the issue.
- No migrations, additional dependencies or navigation replacements were needed.

## Automated checks

`python -m unittest discover -s tests -v`: **59 tests passed**, including seven new guided-trial tests. New coverage includes opt-in/read-only start, add/search/restart, occupied codes, incorrect inputs and deleted results, collection switching, all menu pages, and privacy-safe allowlisted feedback. Existing sample, CSV, search, startup and feedback checks also passed.

## Browser checks

Disposable app at `http://localhost:8501`:

1. Verified Existing library default and sample selection.
2. Started the guide, entered the supplied test title/code in Add Books and clicked Add Now! once. Saved confirmation and row appeared immediately.
3. Opened Find Books through the actual menu and searched TRY-001. One matching book appeared.
4. Opened the feedback destination. GitHub required sign-in; the return URL contained the fixed attempted task and no records or paths. Rendering/prefill of the actual issue form after sign-in is not verified; it still depends on founder merge into the default branch.
5. Restarted the server and opened a new browser session. Existing library was again the default. Selected Sample collection and searched TRY-001; one saved book remained.
6. Checked 390, 768 and 1280 pixel widths: no document-level horizontal overflow. The existing menu and sidebar remain available. The guide can require vertical scrolling on small screens.
7. SHA-256 of both the repository library.db and the disposable existing database stayed `e723e9f6e21e55dbcb810ec442d636288cd432dae50f1465809a0803eb429445` before and after browser tests.

## Limits

The guide is session-only; it does not persist progress metadata. Normal book entry still allows duplicate records; the guide instructs a single add and avoids already-used codes at trial start. Simultaneous evaluators sharing one sample file can select the same code; separate local copies remain the intended evaluation setup. Other operating systems were not checked for this change. Availability requires founder review/merge and any deployment they manage.
