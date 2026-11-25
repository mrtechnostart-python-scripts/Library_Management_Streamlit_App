# Library Management Streamlit App

A simple local Python app built with Streamlit and SQLite. Run it to explore adding books, viewing saved books, issuing a book, and viewing issue records.

![The app’s Add Books page](docs/images/app-add-books.png)

## Run locally

Use **Python 3.13** with `pip` and `venv`. The setup below was tested on Linux with Python 3.13.5 in a fresh virtual environment. Other Python versions and operating systems have not been verified.

Clone the repository, or download and extract its ZIP. Open a terminal in the project folder:

```bash
git clone https://github.com/mrtechnostart-python-scripts/Library_Management_Streamlit_App.git
cd Library_Management_Streamlit_App
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
streamlit run Library.py
```

Open the **Local URL** printed in the terminal (normally `http://localhost:8501`). You should see **Library Management Program**, **Dashboard**, and the six-page menu. Select **Add Books** to see the page pictured above. Stop the app with `Ctrl+C`.

On Windows, the equivalent environment commands are `py -3.13 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell. Then use the same `python -m pip …` and `streamlit run Library.py` commands. Windows setup has not been tested.

SQLite comes with Python; there is no separate database installation or hosted account to create.

## Try a book record

1. Open **Add Books**, enter a book name and a code, then click **Add Now!**.
2. Click **Display All** to view saved books.
3. Open **Issue Book** and enter a college ID, course, the same book code, and a student name. Click **Submit**, then **Display Records**.

The app saves the issue date and a return date seven days later. **Delete Books** removes books by name and code. **Delete Records** removes issue records by college ID and book code when they are not overdue. For overdue records, it displays a fine of 10 INR per day and keeps the record; payment handling is not implemented.

## Your local database

The app opens `library.db` beside `Library.py`, not in an unrelated terminal folder. This repository already includes a database with three book records. Startup keeps those records. If the file is absent, the app creates the two empty tables it needs.

Use test records while evaluating. Copy the project to a separate folder before experimenting with an existing database, and keep a copy of any data you need. The database file is tracked in this repository: do not commit personal records or attach your database to a public issue.

This is a lightweight local project, not a full institutional library system. Empty or duplicate entries are not prevented, book availability is not enforced, and the About page is a placeholder. The current checks do not establish suitability for real patron data or multi-user operation.

## Setup help

- **`streamlit` is not found:** activate `.venv` in this terminal and run `python -m pip install -r requirements.txt` again. You can also launch with `python -m streamlit run Library.py`.
- **Installation fails:** check `python --version`. Use Python 3.13 and a new virtual environment rather than the old 2022 dependencies or an existing shared environment.
- **Port 8501 is occupied:** run `streamlit run Library.py --server.port 8502` and open the URL printed in the terminal.
- **The database is read-only:** move your evaluation copy into a folder your user can write to. SQLite needs to write beside `Library.py`.

[Report a setup failure or share feedback on a task](https://github.com/mrtechnostart-python-scripts/Library_Management_Streamlit_App/issues/new?template=app-feedback.yml). The GitHub form asks for your environment, steps, expected result, actual result, and relevant error messages. A GitHub account is needed to submit it. Leave out personal records and secrets.

## Checks for contributors

With the virtual environment activated:

```bash
python -m pip check
python -m unittest discover -s tests -v
```

The ten regression tests use temporary copies of the app and database. They cover empty-database startup on all pages, book addition/display/deletion, issue creation/display, missing records, due-date handling, invalid saved dates, and preservation of the included database. Browser checks also exercised the real menu and an add → issue → delete-issue flow. See [the first-run test record](docs/first-run-check.md) for scope and limits.
