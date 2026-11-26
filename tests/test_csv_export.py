"""Read-only CSV export checks, using temporary databases only."""
from contextlib import closing
import csv
import io
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest


class CsvExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'Library.py', self.app_path)
        self.real_path = self.app_path.with_name('library.db')
        self.sample_path = self.app_path.with_name('library-sample.db')
        self.real_rows = [('Existing only', '0001', '2026-01-01')]
        self.sample_rows = [
            ('Café, "読書" 📚\nSecond line\r\nThird line', '0002', '2026-02-03'),
            ('  Reader\'s Guide  ', 'B,"3"', ' saved date '),
            ('', '', ''),
            ('=SUM(1,2)', '+001', '@date'),
            ('duplicate', '0002', '2026-02-03'),
        ]
        self.seed(self.real_path, self.real_rows)
        self.seed(self.sample_path, self.sample_rows)
        menu = patch('streamlit_option_menu.option_menu', return_value='Add Books')
        menu.start()
        self.addCleanup(menu.stop)
        self.download = patch('streamlit.download_button', wraps=st.download_button).start()
        self.addCleanup(patch.stopall)

    def seed(self, path, rows):
        with closing(sqlite3.connect(path)) as conn:
            conn.execute('create table bookRec(BookName Text,BookCode Text,DateAdded Text)')
            conn.execute('create table libTab(CollegeID Text,Course Text,BookCode Text,StudentName Text,DateOfIssue Text,ReturnDate Text)')
            conn.execute('insert into libTab values(?,?,?,?,?,?)',
                         ('PRIVATE-ID', 'Course', '0001', 'Private Student', '2026-01-01', '2026-01-08'))
            if path == self.sample_path:
                conn.execute('create table sampleInitialization(id integer primary key)')
                conn.execute('insert into sampleInitialization values(1)')
            conn.executemany('insert into bookRec values(?,?,?)', rows)
            conn.commit()

    def page(self, sample=False):
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        if sample:
            app.session_state['collection'] = 'Sample collection'
        app.run()
        self.assertFalse(app.exception)
        return app

    def downloaded_rows(self):
        data = self.download.call_args.kwargs['data']
        self.assertIsInstance(data, bytes)
        self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
        rows = list(csv.reader(io.StringIO(data.decode('utf-8'), newline='')))
        self.assertEqual(rows.pop(0), ['BookName', 'BookCode', 'DateAdded'])
        return [tuple(row) for row in rows]

    def test_sample_text_round_trip_and_read_only_isolation(self):
        before = {path: path.read_bytes() for path in [self.real_path, self.sample_path]}
        opened = []
        connect = sqlite3.connect

        def tracked(path, *args, **kwargs):
            opened.append(Path(path))
            return connect(path, *args, **kwargs)

        with patch('sqlite3.connect', side_effect=tracked):
            app = self.page(sample=True)
        self.assertEqual(opened, [self.sample_path])
        self.assertEqual(self.downloaded_rows(), self.sample_rows)
        args = self.download.call_args
        self.assertEqual(args.kwargs['file_name'], 'sample-collection-books.csv')
        self.assertEqual(args.kwargs['mime'], 'text/csv; charset=utf-8')
        self.assertEqual(args.kwargs['on_click'], 'ignore')
        self.assertIn('Sample collection', args.args[0])
        self.assertTrue(any('Sample collection · library-sample.db' in m.value for m in app.markdown))
        self.assertNotIn(b'Private Student', args.kwargs['data'])
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_existing_export_and_switch_do_not_reuse_sample_payload(self):
        sample_before = self.sample_path.read_bytes()
        app = self.page()
        self.assertEqual(self.downloaded_rows(), self.real_rows)
        self.assertEqual(self.download.call_args.kwargs['file_name'], 'existing-library-books.csv')
        self.assertEqual(self.sample_path.read_bytes(), sample_before)
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertFalse(app.exception)
        self.assertEqual(self.downloaded_rows(), self.sample_rows)
        app.sidebar.radio[0].set_value('Existing library').run()
        self.assertFalse(app.exception)
        self.assertEqual(self.downloaded_rows(), self.real_rows)

    def test_empty_collections_download_headers(self):
        for sample, path in [(False, self.real_path), (True, self.sample_path)]:
            with self.subTest(sample=sample):
                with closing(sqlite3.connect(path)) as conn:
                    conn.execute('delete from bookRec')
                    conn.commit()
                before = path.read_bytes()
                app = self.page(sample=sample)
                self.assertEqual(self.downloaded_rows(), [])
                self.assertEqual(self.download.call_args.kwargs['data'], b'BookName,BookCode,DateAdded\r\n')
                self.assertIn('0 book records', app.caption[0].value)
                self.assertEqual(path.read_bytes(), before)

    def test_added_and_deleted_books_refresh_payload(self):
        app = self.page(sample=True)
        app.text_input[0].set_value('New book')
        app.text_input[1].set_value('NEW-1')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.downloaded_rows()), len(self.sample_rows) + 1)
        self.assertEqual(self.downloaded_rows()[-1][:2], ('New book', 'NEW-1'))
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('delete from bookRec where BookCode=?', ('NEW-1',))
            conn.commit()
        app.run()
        self.assertEqual(self.downloaded_rows(), self.sample_rows)

    def test_unsupported_null_and_binary_values_are_not_silently_lost(self):
        for value in [None, b'Binary']:
            with self.subTest(value=value):
                with closing(sqlite3.connect(self.sample_path)) as conn:
                    conn.execute('update bookRec set BookName=? where rowid=1', (value,))
                    conn.commit()
                before = self.sample_path.read_bytes()
                self.download.reset_mock()
                app = self.page(sample=True)
                self.download.assert_not_called()
                self.assertIn('not text', app.error[0].value)
                self.assertEqual(self.sample_path.read_bytes(), before)

    def test_sample_export_does_not_create_missing_existing_database(self):
        self.real_path.unlink()
        self.page(sample=True)
        self.assertEqual(self.downloaded_rows(), self.sample_rows)
        self.assertFalse(self.real_path.exists())


if __name__ == '__main__':
    unittest.main()
