import streamlit as st
import numpy as np
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
import datetime
conn = sqlite3.connect('library.db')
c=conn.cursor()
c.execute("create table if not exists libTab(CollegeID varchar(20),Course varchar(20),BookCode varchar(20),StudentName varchar(20),DateOfIssue varchar(20),ReturnDate varchar(20))")
# c.execute(")
# conn.commit()


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
    a = datetime.date.today()
    date_object = datetime.datetime.strptime("{}".format(ExpectedDate), '%Y-%m-%d').date()
    data = str(a-date_object)
    newStr=""
    for i in range(len(data)-15,-1,-1):
        newStr+=data[i]
    days = int(newStr[::-1])
    if days < 0:
        return True
    return False

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
    bookName = st.text_input("Enter Book Code Here: ")
    bookCode = st.text_input("Enter BookCode Here")
    btn = st.button("Delete Now!")
    if btn:
        Query="delete from bookRec where BookName='{}' and BookCode='{}'".format(bookName,bookCode)
        c.execute(Query)
        conn.commit()
        st.success("Records Deleted Successfully")
        st.write("Updated Records")


# It calculate fine
def fineCalc(ExpectedDate):
    a = datetime.date.today()
    date_object = datetime.datetime.strptime("{}".format(ExpectedDate), '%Y-%m-%d').date()
    data = str(a-date_object)
    newStr=""
    for i in range(len(data)-15,-1,-1):
        newStr+=data[i]
    days = int(newStr[::-1])
    return [days,days*10]


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
        c.execute("Select ReturnDate from libTab where CollegeID='{}' and BookCode='{}'".format(CollegeID,bookCode))
        data = c.fetchall()
        expectedReturn = data[0][0]
        if isLate(expectedReturn):
            Query="delete from libTab where CollegeID='{}' and BookCode='{}'".format(CollegeID,bookCode)
            c.execute(Query)
            conn.commit()
            st.success("Records Deleted Successfully")
            st.write("Updated Records")
            st.dataframe(displayRec())
        else:
            st.write("## You pay fine {} INR as You are {} days late".format(fineCalc(expectedReturn)[1],fineCalc(expectedReturn)[0]))
def letter():
    st.title("Library Management Program")
    st.subheader("Dashboard")
    selected = option_menu(
        menu_title="Main Menu",
        options=["Home","Add Books","Delete Books","Issue Book","Delete Records","About"],
        icons=["house","book","envelop","contact"],
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
letter()
