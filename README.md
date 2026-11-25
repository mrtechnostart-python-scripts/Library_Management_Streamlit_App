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

## Try a separate sample collection

Run `streamlit run Library.py`, then choose **Sample collection** under **Local collection** in the sidebar. On a narrow screen, open the sidebar first. This creates `library-sample.db` beside the app with three sample books. In this mode the app does not open or change `library.db`.

1. Open **Add Books**, enter `My Test Book` and code `TRY-001`, then click **Add Now!**. Click **Display All** to see the three sample books and your new book.
2. Open **Issue Book**. Enter college ID `TEST-001`, course `Reading`, book code `TRY-001`, and student name `Sample Reader`. Click **Submit**, then **Display Records** to see the saved issue.
3. Stop the app with `Ctrl+C` and run `streamlit run Library.py` again. Choose **Sample collection** again. **Add Books → Display All** and **Issue Book → Display Records** show the saved book and issue.
4. To return the book before it is overdue, open **Delete Records**, enter college ID `TEST-001` and book code `TRY-001`, then click **Delete Now!**. The issue disappears; the book stays in the collection.
5. Restart and choose **Sample collection** once more. The book remains in **Display All** and the returned issue is absent from **Display Records**.

Use a different book code and college ID if you repeat the walkthrough; duplicate entries are not prevented. Sample initialization happens only once. Your additions, deletions, and issues survive restarts. To start over, stop the app and remove **only `library-sample.db`**; the next sample selection creates fresh sample records. This file is ignored by Git.

Every new app session starts on **Existing library**, preserving the original default. Choose **Sample collection** before entering test records. The sidebar identifies the active file on every page; switching collections clears unfinished form entries.

The app saves the issue date and a return date seven days later. **Delete Books** removes books by name and code. **Delete Records** removes issue records by college ID and book code when they are not overdue. For overdue records, it displays a fine of 10 INR per day and keeps the record; payment handling is not implemented.

## Export book records to CSV

Choose **Existing library** or **Sample collection** in the sidebar, then open **Add Books → Export book records**. Check the collection name and database filename above the download button. Click **Download … books as CSV** to save `existing-library-books.csv` or `sample-collection-books.csv`.

The download reads all saved books from the selected collection without changing records or opening the other database. An empty collection downloads a header-only file. After adding or deleting books, the next download reflects the saved records. This exports books only—not issue records, student details, or a full database backup.

### Book CSV format (version 1)

This is the format to use for the next import milestone; importing is not implemented yet.

- Encoding: UTF-8 without a byte-order mark (BOM).
- Exact header and column order: `BookName,BookCode,DateAdded`.
- Delimiter: comma. Fields containing commas, quotes or line breaks are enclosed in double quotes; embedded double quotes are doubled. Record separators are CRLF.
- Every row contains the three stored text values, unchanged, including whitespace, Unicode, embedded line breaks, empty strings, leading zeros and duplicates. Rows follow SQLite insertion order (`rowid`); internal IDs are not exported.
- `DateAdded` is exported as stored, without validation or reformatting. The app writes `YYYY-MM-DD` when adding a book.
- SQL NULL and non-text values are not supported by this format. If any are found in these fields, the app shows an error instead of downloading a lossy file. No records are changed.

Read the file as CSV, not by splitting lines or commas. For example, Python can use `csv.DictReader` with `open(path, encoding='utf-8', newline='')`. When opening it in a spreadsheet, explicitly import UTF-8 and treat all columns as text to preserve codes and dates. Spreadsheet programs may interpret values beginning with `=`, `+`, `-` or `@` as formulas. The export preserves those values rather than modifying them; do not enable formula evaluation for untrusted records.

## Your local database

The app opens `library.db` beside `Library.py`, not in an unrelated terminal folder. This repository already includes a database with three book records. Startup keeps those records. If the file is absent, the app creates the two empty tables it needs.

Use **Sample collection** while evaluating. **Existing library** uses the original `library.db` path and updates those records when you submit changes. Keep a copy of any existing data you need before editing it. The original database file is tracked in this repository: do not commit personal records or attach either database to a public issue.

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

The 24 tests use temporary copies of the app and database. They cover the ten original first-run cases, eight sample-collection cases, and six CSV export cases for text preservation, empty collections, refreshed downloads, unsupported values and isolation. Browser checks exercised the real menu, sample selection, an add → issue → restart → return flow, the narrow-screen sidebar, and completed CSV downloads from both collections and an empty collection. See the [first-run test record](docs/first-run-check.md), [sample collection test record](docs/sample-collection-check.md), and [CSV export test record](docs/csv-export-check.md) for scope and limits.
