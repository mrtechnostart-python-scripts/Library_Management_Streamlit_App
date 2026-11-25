import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
import datetime
from pathlib import Path

def clear_collection_inputs():
    # Do not carry unfinished book/student entries into the other collection.
    for key in list(st.session_state):
        if key.startswith('form_'):
            st.session_state[key] = ''


collection = st.sidebar.radio(
    'Local collection', ['Existing library', 'Sample collection'],
    key='collection', on_change=clear_collection_inputs,
)
sample_mode = collection == 'Sample collection'
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
        options=["Home","Add Books","Delete Books","Issue Book","Delete Records","About"],
        icons=["house", "book", "trash", "journal-arrow-up", "journal-x", "info-circle"],
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
