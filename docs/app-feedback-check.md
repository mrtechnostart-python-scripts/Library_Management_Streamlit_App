# In-app feedback check

## Scope

Tested on Linux with Python 3.13.5 and the pinned requirements. App version: `0.2.0`. All app and browser tests ran in temporary copies; the repository database was not changed.

## Automated checks

`python -m pip check` passed. `python -m unittest discover -s tests -v` passed all 44 tests (38 existing plus 6 feedback tests).

New tests cover:

- Visible version and collection mode, exact repository destination and form query keys for both collections.
- Mode switches update the context and both links.
- Book/student records, unfinished input, and absolute local paths do not enter either URL or displayed context; feedback does not change the database.
- Feedback renders before database startup failure.
- Feedback is available on all six menu pages.
- Form field IDs match the prefill keys; the URL helper rejects unrecognized modes.

## Browser interaction

Started the actual app with `streamlit run Library.py` in a temporary copy. Opened the sidebar feedback panel, confirmed version and Existing library context, and clicked the structured-form link. GitHub opened its sign-in page with the repository issue URL as the return destination.

Selected Sample collection; the panel changed to that mode. Inspected the plain-issue URL: it includes only version, mode and static reporting prompts. Clicked it and confirmed the GitHub sign-in destination. Nothing was submitted. At 390 × 844, opened the narrow-screen sidebar and confirmed readable text and accessible links.

## Destination and review limitation

The repository remote is `mrtechnostart-python-scripts/Library_Management_Streamlit_App`; its default branch is `master`. At check time, `git ls-tree origin/master .github/ISSUE_TEMPLATE/app-feedback.yml` showed no template, and its raw default-branch URL returned HTTP 404. The structured form is present on `brainer/work` only. GitHub reads issue forms from the default branch; this change does not claim that a review-branch template is already publicly usable.

The app explains the limitation and provides a plain-issue fallback with the same reporting prompts. The visible context can be copied if GitHub does not prefill it. Both links require a GitHub account to submit. Signed-in form rendering, field prefill and submission were not verified; recheck the structured link after founder merge. No public test issue was created.

## Maintenance

`APP_VERSION` in `Library.py` identifies the shipped app behavior, including ZIP downloads without Git. Bump it for subsequent app behavior changes and update the corresponding documentation/tests. It is not a runtime Git commit detector and does not imply a GitHub release exists. Testers may add their commit or download date and dependency versions themselves. No automatic environment, diagnostics, uploads, database contents or filesystem paths are collected.

No new dependencies, migrations, environment keys, hosting or deployment steps are required. Founder review and merge are pending; the founder deploys the app themselves if needed.
