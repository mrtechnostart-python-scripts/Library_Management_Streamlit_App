import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
import datetime
import csv
import io
import hashlib
from pathlib import Path
from urllib.parse import urlencode

# Bump this version when shipping app behavior changes; works in ZIP downloads too.
APP_VERSION = '0.3.0'
FEEDBACK_DESTINATION = (
    'https://github.com/mrtechnostart-python-scripts/'
    'Library_Management_Streamlit_App/issues/new'
)


def feedback_links(collection_mode):
    """Only explicit, non-personal app context may enter an external URL."""
    if collection_mode not in ('Existing library', 'Sample collection'):
        raise ValueError('Unknown collection mode')
    version = f'Library Management Streamlit App {APP_VERSION}'
    context = f'App version: {APP_VERSION}\nCollection mode: {collection_mode}'
    form = FEEDBACK_DESTINATION + '?' + urlencode({
        'template': 'app-feedback.yml', 'versions': version,
        'collection-mode': collection_mode,
    })
    body = (
        f'{context}\n\n'
        '## What are you reporting?\n'
        '(Setup/startup failure, task problem, or feedback on a task that worked)\n\n'
        '## Operating system, Python and dependency versions\n\n'
        '## What did you try?\n(Use test values, not personal records.)\n\n'
        '## What did you expect?\n\n'
        '## What actually happened?\n\n'
        '## Error messages\n(Remove personal details, secrets and local file paths.)\n\n'
        '## Which database did you use?\n'
        '(Included, new empty, your own existing, or app did not start)\n'
    )
    fallback = FEEDBACK_DESTINATION + '?' + urlencode({
        'title': '[Feedback]: ', 'body': body,
    })
    return context, form, fallback


def show_feedback(collection_mode):
    context, form, fallback = feedback_links(collection_mode)
    with st.sidebar.expander('Report a problem or share feedback'):
        st.write('Report a setup problem or tell us what happened when you tried a task.')
        st.code(context, language=None)
        st.write('The links include only this app version and collection mode. '
                 'No book records, student data or local file paths are attached. '
                 'GitHub issues are public; remove personal details, secrets and paths '
                 'from anything you add. A GitHub account is needed to submit.')
        st.link_button('Open GitHub feedback form', form)
        st.write('If the form is unavailable, it may still be awaiting merge from '
                 'the review branch. Use the plain issue below; it includes the same prompts. '
                 'If GitHub does not fill the context, copy it from above.')
        st.link_button('Open plain GitHub issue instead', fallback)


def clear_book_query():
    st.session_state['book_query'] = ''


def clear_collection_inputs():
    # Do not carry unfinished book/student entries into the other collection.
    for key in list(st.session_state):
        if key.startswith('form_'):
            st.session_state[key] = ''
    clear_book_query()
    # A new uploader identity discards previews, even when switching back.
    st.session_state['import_generation'] = st.session_state.get('import_generation', 0) + 1


collection = st.sidebar.radio(
    'Local collection', ['Existing library', 'Sample collection'],
    key='collection', on_change=clear_collection_inputs,
)
sample_mode = collection == 'Sample collection'
# Render before database access, so database startup problems keep a feedback route.
show_feedback(collection)
# Keep both databases beside the app, even when launched from another directory.
real_path = Path(__file__).resolve().with_name('library.db')
db_path = real_path.with_name('library-sample.db') if sample_mode else real_path
if sample_mode:
    # Refuse an accidentally linked sample file rather than write to real records.
    if db_path.is_symlink() or (db_path.exists() and real_path.exists()
                               and db_path.samefile(real_path)):
        st.error('library-sample.db must be a separate file, not a link to another database. '
                 'Stop the app and move the link before trying the sample collection.')
        st.stop()
    st.sidebar.info('Sample data · library-sample.db\n\n'
                    'Changes stay in this separate local file. library.db is not opened.')
else:
    st.sidebar.info('Existing data · library.db\n\n'
                    'Changes here update your existing library. Choose Sample collection to try the app separately.')

conn = sqlite3.connect(db_path)
c = conn.cursor()
with conn:
    c.execute("create table if not exists libTab(CollegeID varchar(20),Course varchar(20),BookCode varchar(20),StudentName varchar(20),DateOfIssue varchar(20),ReturnDate varchar(20))")
    c.execute('create table if not exists bookRec(BookName Text,BookCode Text,DateAdded Text)')
    if sample_mode:
        # A saved marker prevents reruns/restarts from restoring deleted sample books.
        c.execute('create table if not exists sampleInitialization(id integer primary key)')
        if not c.execute('select 1 from sampleInitialization where id=1').fetchone():
            # Never add seeds to an already populated sample file.
            if (not c.execute('select 1 from bookRec limit 1').fetchone()
                    and not c.execute('select 1 from libTab limit 1').fetchone()):
                c.executemany('insert into bookRec values(?,?,?)', [
                    ('A Guide to Python', 'SAMPLE-001', str(datetime.date.today())),
                    ('Community Gardening', 'SAMPLE-002', str(datetime.date.today())),
                    ('Short Stories', 'SAMPLE-003', str(datetime.date.today())),
                ])
            c.execute('insert into sampleInitialization values(1)')


# Checks if the book exist in record
def inBookRec(BookCode):
    c.execute('select * from bookRec')
    data = c.fetchall()
    for i in data:
        if i[1] == BookCode:
            return True
    return False

# Check if late and takes 10 rupee fine per day
def isLate(ExpectedDate):
    return fineCalc(ExpectedDate)[0] > 0

BOOK_CSV_COLUMNS = ('BookName', 'BookCode', 'DateAdded')


def book_records_csv(connection):
    # Explicit fields and row order keep this format stable for a future importer.
    rows = connection.execute(
        'select BookName, BookCode, DateAdded from bookRec order by rowid'
    ).fetchall()
    if any(not isinstance(value, str) for row in rows for value in row):
        raise ValueError('Some book fields are not text (for example, NULL or binary data). '
                         'Check BookName, BookCode and DateAdded in the selected database '
                         'before exporting. No records were changed.')
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(BOOK_CSV_COLUMNS)
    writer.writerows(rows)
    return output.getvalue().encode('utf-8'), len(rows)


def find_book_records(connection, query):
    """Literal, Unicode case-insensitive search; keep stored values and row order."""
    rows = connection.execute(
        'select BookName, BookCode, DateAdded from bookRec order by rowid'
    ).fetchall()
    needle = query.casefold()
    matches = [row for row in rows if not needle or any(
        isinstance(value, str) and needle in value.casefold() for value in row[:2]
    )]
    return matches, len(rows)


def findBooks():
    st.subheader('Find books')
    st.write(f'Searching: {collection} · {db_path.name}')
    st.write('Search any part of a book code or title, ignoring upper and lower case. '
             'Spaces and punctuation match literally. Leave the query empty to see all books.')
    query = st.text_input('Book code or title', key='book_query')
    st.button('Clear search', on_click=clear_book_query, disabled=query == '')
    try:
        rows, total = find_book_records(conn, query)
    except sqlite3.Error:
        st.error('Could not read this collection. Check the database file and try again.')
        return
    if not total:
        st.info('No books in this collection yet. Add a book or import a book CSV in Add Books.')
    elif not rows:
        st.info('No books match this query in the selected collection. '
                'Try another code or title, or clear the search to see all books.')
    else:
        st.caption(f'{len(rows)} of {total} book records · ' +
                   ('Matching books' if query else 'All books'))
        st.dataframe(pd.DataFrame(rows, columns=BOOK_CSV_COLUMNS), hide_index=True)


def exportBooks():
    st.subheader('Export book records')
    st.write(f'Exporting: {collection} · {db_path.name}')
    st.write('This CSV contains book names, codes and dates added. '
             'It does not include issue or student records and is not a full database backup.')
    try:
        data, count = book_records_csv(conn)
    except ValueError as error:
        st.error(str(error))
        return
    st.caption(f'{count} book record' + ('. ' if count == 1 else 's. ') +
               ('The empty collection downloads column names only.' if count == 0 else
                'All saved books in this collection are included.'))
    st.download_button(
        f'Download {collection} books as CSV', data=data,
        file_name='sample-collection-books.csv' if sample_mode else 'existing-library-books.csv',
        mime='text/csv; charset=utf-8', key=f'book_export_{sample_mode}',
        on_click='ignore',
    )


def parse_book_csv(data):
    """Validate the entire export-shaped file without coercing any text."""
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('Save the file as UTF-8 CSV and upload it again. No books were added.') from error
    # csv.reader accepts quotes inside unquoted fields; reject that malformed syntax.
    state = 'start'
    line = 1
    for char in text:
        if state == 'quoted':
            if char == '"':
                state = 'closed'
        elif state == 'closed':
            if char == '"':
                state = 'quoted'
            elif char in ',\r\n':
                state = 'start'
            else:
                raise ValueError(f'CSV line {line}: unexpected text after a closing quote. Check quoting.')
        elif char == '"':
            if state != 'start':
                raise ValueError(f'CSV line {line}: quote inside an unquoted field. Check quoting.')
            state = 'quoted'
        elif char in ',\r\n':
            state = 'start'
        else:
            state = 'unquoted'
        if char == '\n':
            line += 1
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    try:
        header = next(reader, None)
        if header != list(BOOK_CSV_COLUMNS):
            raise ValueError('The first row must be exactly BookName,BookCode,DateAdded in that order. '
                             'Use the app’s book export and upload it again.')
        rows = []
        codes = {}
        for number, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise ValueError(f'CSV record {number} (ending on line {reader.line_num}): '
                                 f'expected 3 fields, found {len(row)}. Check commas and quoting.')
            if row[1] in codes:
                raise ValueError(f'CSV record {number}: duplicate BookCode {row[1]!r}; '
                                 f'also in record {codes[row[1]]}. Give each book a distinct code.')
            codes[row[1]] = number
            rows.append(tuple(row))
    except csv.Error as error:
        raise ValueError(f'CSV line {reader.line_num}: {error}. Check quoting and field length.') from error
    if not rows:
        raise ValueError('This file contains column names only. Export a collection with books to import.')
    return rows


def validate_book_destination(connection, rows):
    existing = {row[0] for row in connection.execute('select BookCode from bookRec')}
    for number, row in enumerate(rows, start=2):
        if row[1] in existing:
            raise ValueError(f'CSV record {number}: BookCode {row[1]!r} already exists in this collection. '
                             'Remove that row or use a distinct code. No books were added.')


def import_book_csv(connection, data):
    rows = parse_book_csv(data)
    # Lock before checking destination codes: another writer cannot slip in a duplicate.
    # The app supplies an idle connection; do not commit an unrelated pending write.
    if connection.in_transaction:
        raise sqlite3.OperationalError('Import requires an idle connection')
    try:
        connection.execute('BEGIN IMMEDIATE')
        validate_book_destination(connection, rows)
        connection.executemany(
            'insert into bookRec(BookName,BookCode,DateAdded) values(?,?,?)', rows)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return len(rows)


def importBooks():
    st.subheader('Import book records')
    st.write(f'Destination: {collection} · {db_path.name}')
    st.write('Upload a book CSV exported by the app. Import adds books only; existing records are never replaced. '
             'Names, codes and dates stay as text. Every book code must be distinct.')
    generation = st.session_state.get('import_generation', 0)
    upload = st.file_uploader('Choose a book CSV', type=['csv'], key=f'book_upload_{generation}')
    if upload is None:
        return
    data = upload.getvalue()
    identity = f'{generation}_{hashlib.sha256(data).hexdigest()}'
    try:
        rows = parse_book_csv(data)
        validate_book_destination(conn, rows)
    except ValueError as error:
        st.error(str(error))
        return
    except sqlite3.Error:
        st.error('Could not check this collection. Check the database file and try again. No books were added.')
        return
    st.write(f'Validation passed: {len(rows)} books to add to {collection} · {db_path.name}.')
    st.caption('Preview of the first 20 books. The entire file has been checked. Nothing is added until you confirm.')
    st.dataframe(pd.DataFrame(rows[:20], columns=BOOK_CSV_COLUMNS), hide_index=True)
    if st.button(f'Confirm import into {collection}', key=f'book_confirm_{identity}', type='primary'):
        try:
            count = import_book_csv(conn, data)
        except ValueError as error:
            st.error(str(error))
        except sqlite3.Error:
            st.error('Import could not be saved. No books were added. Check that the database is writable '
                     'and not busy, then upload the file again.')
        else:
            st.success(f'Added {count} books to {collection} · {db_path.name}. Existing records were kept.')
            # Consume this upload; a later click cannot import it twice.
            st.session_state['import_generation'] = generation + 1


# It add book

def addBooks():
    c.execute('create table if not exists bookRec(BookName Text,BookCode Text,DateAdded Text)')
    BookName = st.text_input("Book Name Here", key='form_1')
    BookCode = st.text_input("Book Code Here", key='form_2')
    if st.button("Add Now!"):
        c.execute('Insert into bookRec(BookName,BookCode,DateAdded) values(?,?,?)',(BookName,BookCode,str(datetime.date.today())))
        conn.commit()
        st.success("Book Added Successfully! ")
    if st.button("Display All"):
        c.execute('Select * from bookRec')
        data = pd.DataFrame(c.fetchall(),columns=["BookName","BookCode","DateAdded"])
        st.dataframe(data)
    exportBooks()
    importBooks()


def deleteBooks():
    bookName = st.text_input("Enter Book Name Here: ", key='form_3')
    bookCode = st.text_input("Enter BookCode Here", key='form_4')
    btn = st.button("Delete Now!")
    if btn:
        c.execute('delete from bookRec where BookName=? and BookCode=?', (bookName, bookCode))
        conn.commit()
        if c.rowcount:
            st.success("Records Deleted Successfully")
        else:
            st.warning("No matching book found.")


# It calculate fine
def fineCalc(ExpectedDate):
    date_object = datetime.date.fromisoformat(str(ExpectedDate))
    days = max(0, (datetime.date.today() - date_object).days)
    return [days, days * 10]


# It display All Records

def displayRec():
    c.execute("Select * from libTab")
    data = pd.DataFrame(c.fetchall(),columns=["CollegeID","Course","BookCode","StudentName","DateOfIssue","ReturnDate"])
    return data

# issueBook here
def issueBook():
    CollegeID = st.text_input("College ID Here: ", key='form_5')
    Course = st.text_input("Enter Course", key='form_6')
    BookCode = st.text_input("Book Code", key='form_7')
    StudentName = st.text_input("Student Name Here: ", key='form_8')
    DateOfIssue = str(datetime.date.today())
    btn = st.button("Submit")
    btn1 = st.button("Display Records")
    if btn1:
        st.dataframe(displayRec())
    if btn:
        if inBookRec(BookCode):
            c.execute('insert into libTab(CollegeID,Course,BookCode,StudentName,DateOfIssue,ReturnDate) values(?,?,?,?,?,?)',(CollegeID,Course,BookCode,StudentName,DateOfIssue,str(datetime.date.today()+datetime.timedelta(days=7))))
            conn.commit()
            st.success("Records Added Successfully!")
        else:
            st.warning("Book Not In Database!")

# It delete record
def deleteRecords():
    CollegeID = st.text_input("Enter College ID Here: ", key='form_9')
    bookCode = st.text_input("Enter BookCode Here", key='form_10')
    btn = st.button("Delete Now!")
    if btn:
        c.execute('Select ReturnDate from libTab where CollegeID=? and BookCode=?', (CollegeID, bookCode))
        data = c.fetchall()
        if not data:
            st.warning("No matching issue record found.")
            return
        expectedReturn = data[0][0]
        try:
            late = isLate(expectedReturn)
        except (TypeError, ValueError):
            st.error("The saved return date must use YYYY-MM-DD. Check the record before deleting it.")
            return
        if late:
            days, fine = fineCalc(expectedReturn)
            st.write("## You pay fine {} INR as You are {} days late".format(fine, days))
        else:
            c.execute('delete from libTab where CollegeID=? and BookCode=?', (CollegeID, bookCode))
            conn.commit()
            st.success("Records Deleted Successfully")
            st.write("Updated Records")
            st.dataframe(displayRec())
def letter():
    st.title("Library Management Program")
    st.subheader("Dashboard")
    selected = option_menu(
        menu_title="Main Menu",
        options=["Home","Find Books","Add Books","Delete Books","Issue Book","Delete Records","About"],
        icons=["house", "search", "book", "trash", "journal-arrow-up", "journal-x", "info-circle"],
        menu_icon="cast",
        orientation="horizontal"
        )
    if selected=="Home":
        st.markdown('Library Management By Krishna Yadav')
        if sample_mode:
            st.subheader('Try the sample collection')
            st.write('Add a book with code TRY-001 in Add Books. In Issue Book, use that code '
                     'with college ID TEST-001, course Reading, and student name Sample Reader. '
                     'Use Delete Records with TEST-001 and TRY-001 to return it before it is overdue.')
            st.write('Stop and restart the app, then choose Sample collection again. '
                     'Display All shows your saved book; Display Records shows any remaining issues. '
                     'Sample books are added only on first use, not on every restart.')
    if selected == "Find Books":
        findBooks()
    if selected=="Issue Book":
        issueBook()
    if selected == "Delete Books":
        deleteBooks()
    if selected=="Delete Records":
        deleteRecords()
    if selected=="Add Books":
        addBooks()
    if selected == "About":
        st.write(" About Here! ")

try:
    letter()
finally:
    conn.close()
