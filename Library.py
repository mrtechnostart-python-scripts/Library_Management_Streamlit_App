import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
import datetime
from pathlib import Path

# Keep the database beside the app, even when launched from another directory.
conn = sqlite3.connect(Path(__file__).resolve().with_name('library.db'))
c = conn.cursor()
c.execute("create table if not exists libTab(CollegeID varchar(20),Course varchar(20),BookCode varchar(20),StudentName varchar(20),DateOfIssue varchar(20),ReturnDate varchar(20))")
c.execute('create table if not exists bookRec(BookName Text,BookCode Text,DateAdded Text)')
conn.commit()


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
    BookName = st.text_input("Book Name Here")
    BookCode = st.text_input("Book Code Here")
    if st.button("Add Now!"):
        c.execute('Insert into bookRec(BookName,BookCode,DateAdded) values(?,?,?)',(BookName,BookCode,str(datetime.date.today())))
        conn.commit()
        st.success("Book Added Successfully! ")
    if st.button("Display All"):
        c.execute('Select * from bookRec')
        data = pd.DataFrame(c.fetchall(),columns=["BookName","BookCode","DateAdded"])
        st.dataframe(data)
def deleteBooks():
    bookName = st.text_input("Enter Book Name Here: ")
    bookCode = st.text_input("Enter BookCode Here")
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
    CollegeID = st.text_input("College ID Here: ")
    Course = st.text_input("Enter Course")
    BookCode = st.text_input("Book Code")
    StudentName = st.text_input("Student Name Here: ")
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
    CollegeID = st.text_input("Enter College ID Here: ")
    bookCode = st.text_input("Enter BookCode Here")
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
