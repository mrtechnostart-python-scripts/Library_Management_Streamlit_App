# Fresh-install and startup check

## Executed environments

All three rows below ran on Linux x86_64 with glibc 2.41. Each check created a new standard-library virtual environment and installed from `requirements.txt` with pip. No app packages were inherited from the parent environment.

| Python | Fresh install / pip check | Regressions | App execution / CLI startup |
| --- | --- | --- | --- |
| 3.11.18 | Passed | 52 passed, no skips | Passed |
| 3.12.16 | Passed | 52 passed, no skips | Passed |
| 3.13.5 | Passed | 52 passed, no skips | Passed |

The exact installed packages and OS identifiers are saved in [3.11 evidence](setup-results/linux-python-3.11.json), [3.12 evidence](setup-results/linux-python-3.12.json) and [3.13 evidence](setup-results/linux-python-3.13.json). These are observations, not dependency lockfiles. The direct pins remain pandas 2.3.3, Streamlit 1.67.0 and streamlit-option-menu 0.4.0. Transitive dependencies can resolve differently on later installs or another OS; rerun the check and save a new report when evaluating those environments.

Streamlit 1.67.0 declares `Requires-Python >=3.11`; pandas 2.3.3 declares `>=3.9`. Python 3.11 is therefore the minimum for the current pins, not Python 3.9 or 3.10. The project's checked Linux range is 3.11–3.13. Python 3.14, macOS, other architectures and other Linux distributions have not been verified by this run.

## Repeat the check

From the repository folder:

```bash
python3.13 scripts/check_setup.py --report setup-result.json
```

On Windows PowerShell:

```powershell
py -3.13 scripts/check_setup.py --report setup-result.json
```

Substitute 3.11 or 3.12 to test that interpreter. The script is standard-library-only and creates its own temporary environment. The optional JSON report contains OS, Python and package versions, not collection records. Full output and failures are printed to the terminal. Exit code zero means the complete check passed; a subprocess failure or timeout returns nonzero. Installation has a ten-minute limit, regression execution five minutes, and server readiness 45 seconds. The server is terminated and temporary data removed on ordinary success or failure.

The check:

1. Copies only the app, supplied database fixture, requirements, tests and feedback issue template into a temporary project.
2. Creates a fresh venv, installs dependencies and runs `pip check`.
3. Runs all regression tests against temporary data. AppTest selects pages by mocking the third-party menu where needed; it executes the app, not a substitute implementation.
4. Runs the real Home script with AppTest without mocking the menu, initially without a database. It checks the title and Dashboard, and verifies that the new database is beside the app, not in the working directory. Both paths include spaces.
5. Starts `python -m streamlit run` from that unrelated working directory, checks `/_stcore/health` and the HTML page on a temporary loopback port, then stops it. HTTP readiness alone does not execute a Streamlit session; the preceding AppTest steps provide app-execution coverage.
6. Checks that the repository's supplied database hash is unchanged, including when a step fails.

The supplied `library.db` SHA-256 before and after all local checks was:

```text
e723e9f6e21e55dbcb810ec442d636288cd432dae50f1465809a0803eb429445
```

The script never launches the repository's own `Library.py` or opens its database with SQLite. Both the regression fixtures and startup database are disposable. Test data, server logs and environments are removed when each check exits.

## Windows and hosted CI status

**Windows has not been executed in this workspace.** The prepared template [`docs/ci/setup-check.yml`](ci/setup-check.yml) runs six independent jobs when installed: `ubuntu-latest` and `windows-latest`, each with Python 3.11, 3.12 and 3.13. It uses the same fresh-install command, read-only repository permissions, a 15-minute job timeout, and successful-run package reports retained for 14 days. It does not deploy or need application secrets.

GitHub rejected the initial push containing an active workflow: Brainer's GitHub App does not have `workflows` permission. The complete YAML is therefore delivered as a template outside `.github/workflows`, not silently presented as active CI. Hosted results remain pending. The founder must review the existing pull request, copy `docs/ci/setup-check.yml` to `.github/workflows/setup-check.yml` using their own GitHub permissions, and enable Actions or approve the run if required. The team does not change repository settings, merge the pull request or deploy. A manual `workflow_dispatch` trigger is included for runs after the installed workflow is available on the default branch. Do not describe a Windows or hosted runner as verified until its actual job passes.

The symbolic-link regression now skips only Windows error 1314 (missing symlink privilege), with an explicit reason. Other filesystem failures still fail the test. The hard-link refusal is a separate test and always runs, even when the symlink check must skip. Local Linux execution ran both checks without skips. The missing-database page check now includes Find Books as well as the original six pages.

## Browser confirmation

Using another fresh Linux/Python 3.13.5 pip environment, started the documented `python -m streamlit run` path with a temporary app copy containing spaces in its path, from an unrelated directory. The copy initially had no database.

At `http://localhost:8501`, the actual browser rendered Library Management Program, Dashboard and all seven real option-menu links. Selected Sample collection, opened Add Books, saved `Fresh setup check` with code `SETUP-001`, then opened Find Books and searched that code. The app reported one matching book out of four. This exercised the actual third-party menu and browser session, which the HTTP-only startup probe cannot cover. The browser and server were closed afterward; the supplied repository database was unchanged.

This check does not establish hosted operation, suitability for personal patron data, multi-user use or performance at library scale.
