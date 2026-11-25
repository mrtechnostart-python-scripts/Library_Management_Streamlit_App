"""Regression checks using temporary app copies, never the repository database."""
import datetime
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'Library.py', self.app_path)
        self.db_path = self.app_path.with_name('library.db')

    def page(self, name):
        # AppTest cannot click third-party component menus; browser checks cover that.
        menu = patch('streamlit_option_menu.option_menu', return_value=name)
        menu.start()
        self.addCleanup(menu.stop)
        app = AppTest.from_file(str(self.app_path), default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def rows(self, table):
        with closing(sqlite3.connect(self.db_path)) as conn:
            return conn.execute('select * from ' + table).fetchall()

    def seed_issue(self, due):
        self.page('Home')
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('insert into libTab values(?,?,?,?,?,?)',
                         ('TEST-1', 'Test', 'BOOK-1', 'Tester', '2026-01-01', due))
            conn.commit()

    def delete_issue(self):
        app = self.page('Delete Records')
        app.text_input[0].set_value('TEST-1')
        app.text_input[1].set_value('BOOK-1')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        return app

    def test_all_pages_open_without_a_database(self):
        for name in ['Home', 'Add Books', 'Delete Books', 'Issue Book', 'Delete Records', 'About']:
            with self.subTest(page=name):
                self.db_path.unlink(missing_ok=True)
                self.page(name)
                self.assertEqual(self.rows('bookRec'), [])
                self.assertEqual(self.rows('libTab'), [])

    def test_add_display_and_delete_book_with_apostrophe(self):
        app = self.page('Add Books')
        app.text_input[0].set_value("Reader's Guide")
        app.text_input[1].set_value("B'1")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.success), 1)
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value.iloc[0]['BookName'], "Reader's Guide")
        # A new run uses the saved database.
        delete = self.page('Delete Books')
        delete.text_input[0].set_value("Reader's Guide")
        delete.text_input[1].set_value("B'1")
        delete.button[0].click().run()
        self.assertFalse(delete.exception)
        self.assertEqual(self.rows('bookRec'), [])

    def test_unknown_book_issue_is_a_warning(self):
        app = self.page('Issue Book')
        app.text_input[2].set_value('UNKNOWN')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.warning), 1)
        self.assertEqual(self.rows('libTab'), [])

    def test_issue_book_and_display_saved_record(self):
        self.page('Home')
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('insert into bookRec values(?,?,?)', ('Test book', 'BOOK-1', '2026-01-01'))
            conn.commit()
        app = self.page('Issue Book')
        for widget, value in zip(app.text_input, ['TEST-1', 'Test', 'BOOK-1', 'Tester']):
            widget.set_value(value)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.success), 1)
        saved = self.rows('libTab')[0]
        self.assertEqual(saved[-1], str(datetime.date.today() + datetime.timedelta(days=7)))
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 1)

    def test_missing_issue_and_book_deletion_are_warnings(self):
        app = self.delete_issue()
        self.assertEqual(len(app.warning), 1)
        app = self.page('Delete Books')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.warning), 1)

    def test_issue_due_today_can_be_deleted(self):
        self.seed_issue(str(datetime.date.today()))
        app = self.delete_issue()
        self.assertEqual(len(app.success), 1)
        self.assertEqual(self.rows('libTab'), [])

    def test_future_issue_can_be_deleted(self):
        self.seed_issue(str(datetime.date.today() + datetime.timedelta(days=7)))
        app = self.delete_issue()
        self.assertEqual(len(app.success), 1)
        self.assertEqual(self.rows('libTab'), [])

    def test_overdue_issue_displays_fine_and_keeps_record(self):
        self.seed_issue(str(datetime.date.today() - datetime.timedelta(days=2)))
        app = self.delete_issue()
        self.assertIn('20 INR', app.markdown[0].value)
        self.assertEqual(len(self.rows('libTab')), 1)

    def test_invalid_saved_return_date_does_not_crash(self):
        self.seed_issue('invalid date')
        app = self.delete_issue()
        self.assertEqual(len(app.error), 1)
        self.assertEqual(len(self.rows('libTab')), 1)

    def test_existing_database_is_preserved(self):
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'library.db', self.db_path)
        before_books = self.rows('bookRec')
        before_issues = self.rows('libTab')
        self.page('Home')
        self.assertEqual(self.rows('bookRec'), before_books)
        self.assertEqual(self.rows('libTab'), before_issues)


if __name__ == '__main__':
    unittest.main()
