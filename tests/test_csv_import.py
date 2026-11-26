"""Atomic additive book import checks; all databases and app copies are temporary."""
import ast
from contextlib import closing
import csv
import io
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


SOURCE = Path(__file__).resolve().parents[1] / 'Library.py'
# Load only pure CSV helpers, without executing the Streamlit page.
module = ast.parse(SOURCE.read_text())
names = {'book_records_csv', 'parse_book_csv', 'validate_book_destination', 'import_book_csv'}
helpers = ast.Module(body=[node for node in module.body
                          if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
namespace = dict(csv=csv, io=io, sqlite3=sqlite3,
                 BOOK_CSV_COLUMNS=('BookName', 'BookCode', 'DateAdded'))
exec(compile(helpers, str(SOURCE), 'exec'), namespace)
parse = namespace['parse_book_csv']
import_csv = namespace['import_book_csv']
export_csv = namespace['book_records_csv']


def encoded(rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(['BookName', 'BookCode', 'DateAdded'])
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


class CsvImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(SOURCE, self.app_path)
        self.real = self.app_path.with_name('library.db')
        self.sample = self.app_path.with_name('library-sample.db')
        self.rows = [('Café, "読書" 📚\nLine 2\r\nLine 3', '0002', '2026-02-03'),
                     ('  Reader\'s Guide  ', 'B,"3"', ' saved date '),
                     ('', '', ''), ('=SUM(1,2)', '+001', '@date')]
        for path in [self.real, self.sample]:
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('create table bookRec(BookName Text,BookCode Text,DateAdded Text)')
                conn.execute('create table libTab(CollegeID Text,Course Text,BookCode Text,StudentName Text,DateOfIssue Text,ReturnDate Text)')
                conn.execute('insert into libTab values(?,?,?,?,?,?)', ('ID', 'Course', 'X', 'Student', 'date', 'date'))
                if path == self.sample:
                    conn.execute('create table sampleInitialization(id integer primary key)')
                    conn.execute('insert into sampleInitialization values(1)')
                conn.commit()
        self.data = encoded(self.rows)

    def saved(self, path=None):
        with closing(sqlite3.connect(path or self.sample)) as conn:
            return conn.execute('select * from bookRec order by rowid').fetchall()

    def test_export_import_round_trip_persistence_and_isolation(self):
        with closing(sqlite3.connect(self.real)) as source:
            source.executemany('insert into bookRec values(?,?,?)', self.rows)
            source.commit()
            data, count = export_csv(source)
        before = self.real.read_bytes()
        with closing(sqlite3.connect(self.sample)) as dest:
            issues = dest.execute('select * from libTab').fetchall()
            self.assertEqual(import_csv(dest, data), count)
            self.assertEqual(dest.execute('select * from libTab').fetchall(), issues)
            self.assertEqual(export_csv(dest)[0], data)
        self.assertEqual(self.saved(), self.rows)
        self.assertEqual(self.real.read_bytes(), before)

    def test_empty_files_and_header_only_are_actionable(self):
        for data in [b'', b'\xef\xbb\xbf', b'BookName,BookCode,DateAdded\r\n']:
            with self.subTest(data=data), closing(sqlite3.connect(self.sample)) as conn:
                with self.assertRaises(ValueError):
                    import_csv(conn, data)
                self.assertEqual(self.saved(), [])

    def test_malformed_headers_encoding_and_rows_leave_file_unchanged(self):
        invalid = [b'BookCode,BookName,DateAdded\nA,B,C',
                   b'BookName,BookCode,DateAdded,Extra\nA,B,C,D',
                   b'bookname,BookCode,DateAdded\nA,B,C',
                   b'BookName,BookCode,DateAdded\n\xff,B,C',
                   b'BookName,BookCode,DateAdded\nA,B',
                   b'BookName,BookCode,DateAdded\nA,B,C,D',
                   b'BookName,BookCode,DateAdded\n\n',
                   b'BookName,BookCode,DateAdded\n"A,B,C',
                   b'BookName,BookCode,DateAdded\nA"X,B,C',
                   b'BookName,BookCode,DateAdded\n"A"X,B,C',
                   self.data + b'late,bad\r\n']
        before = self.sample.read_bytes()
        for data in invalid:
            with self.subTest(data=data), closing(sqlite3.connect(self.sample)) as conn:
                with self.assertRaises(ValueError):
                    import_csv(conn, data)
                self.assertFalse(conn.in_transaction)
                self.assertEqual(self.sample.read_bytes(), before)

    def test_duplicates_within_file_include_record_and_code(self):
        for code in ['0002', '']:
            with self.subTest(code=code), closing(sqlite3.connect(self.sample)) as conn:
                with self.assertRaisesRegex(ValueError, 'record 3: duplicate BookCode'):
                    import_csv(conn, encoded([('one', code, ''), ('two', code, '')]))
                self.assertEqual(self.saved(), [])

    def test_existing_duplicate_keeps_all_existing_records(self):
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute('insert into bookRec values(?,?,?)', ('Keep me', '+001', 'old date'))
            conn.commit()
            before = self.sample.read_bytes()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                import_csv(conn, self.data)
            self.assertEqual(self.sample.read_bytes(), before)
            self.assertFalse(conn.in_transaction)

    def test_write_failure_after_first_insert_rolls_back_every_row(self):
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute("create trigger fail_insert before insert on bookRec when NEW.BookCode = '+001' begin select raise(ABORT, 'test failure'); end")
            conn.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                import_csv(conn, self.data)
            self.assertEqual(self.saved(), [])
            self.assertFalse(conn.in_transaction)

    def test_commit_failure_rolls_back(self):
        class FailedCommit(sqlite3.Connection):
            def commit(self):
                raise sqlite3.OperationalError('test commit failure')
        with closing(sqlite3.connect(self.sample, factory=FailedCommit)) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                import_csv(conn, self.data)
            self.assertFalse(conn.in_transaction)
        self.assertEqual(self.saved(), [])

    def test_busy_database_and_pending_transaction_do_not_write(self):
        with closing(sqlite3.connect(self.sample)) as blocker:
            blocker.execute('BEGIN IMMEDIATE')
            with closing(sqlite3.connect(self.sample, timeout=0.01)) as conn:
                with self.assertRaises(sqlite3.OperationalError):
                    import_csv(conn, self.data)
                self.assertFalse(conn.in_transaction)
            blocker.rollback()
            blocker.execute('insert into bookRec values(?,?,?)', ('Pending', 'pending', ''))
            with self.assertRaises(sqlite3.OperationalError):
                import_csv(blocker, self.data)
            self.assertTrue(blocker.in_transaction)
            blocker.rollback()
        self.assertEqual(self.saved(), [])

    def test_bom_supported_without_changing_field_text(self):
        self.assertEqual(parse(b'\xef\xbb\xbf' + self.data), self.rows)

    def page(self, data=None):
        self.current_upload = data
        self.upload_key = None

        def uploader(*args, **kwargs):
            if self.upload_key is None:
                self.upload_key = kwargs['key']
            return io.BytesIO(self.current_upload) if self.current_upload is not None and kwargs['key'] == self.upload_key else None

        menu = patch('streamlit_option_menu.option_menu', return_value='Add Books')
        upload = patch('streamlit.file_uploader', side_effect=uploader)
        menu.start()
        upload.start()
        self.addCleanup(menu.stop)
        self.addCleanup(upload.stop)
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        app.session_state['collection'] = 'Sample collection'
        app.run()
        self.assertFalse(app.exception)
        return app

    def confirm(self, app):
        return next(button for button in app.button if button.label.startswith('Confirm import'))

    def test_preview_requires_confirmation_consumes_upload_and_persists(self):
        before = self.real.read_bytes()
        app = self.page(self.data)
        self.assertEqual(self.saved(), [])
        self.assertEqual(list(app.dataframe[0].value.itertuples(index=False, name=None)), self.rows)
        self.assertTrue(any('Destination: Sample collection · library-sample.db' in m.value for m in app.markdown))
        self.confirm(app).click().run()
        self.assertFalse(app.exception)
        self.assertIn('Added 4 books', app.success[0].value)
        self.assertEqual(self.saved(), self.rows)
        app.run()
        self.assertFalse(any(b.label.startswith('Confirm import') for b in app.button))
        self.assertEqual(self.real.read_bytes(), before)

    def test_switching_collections_discards_preview_even_when_switching_back(self):
        app = self.page(self.data)
        self.confirm(app)
        for collection in ['Existing library', 'Sample collection']:
            app.sidebar.radio[0].set_value(collection).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(b.label.startswith('Confirm import') for b in app.button))
        self.assertEqual(self.saved(self.real), [])
        self.assertEqual(self.saved(), [])

    def test_conflict_added_after_preview_is_rechecked(self):
        app = self.page(self.data)
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute('insert into bookRec values(?,?,?)', ('Other writer', '0002', ''))
            conn.commit()
        self.confirm(app).click().run()
        self.assertFalse(app.exception)
        self.assertIn('already exists', app.error[0].value)
        self.assertEqual(self.saved(), [('Other writer', '0002', '')])

    def test_invalid_ui_file_has_error_and_no_confirmation(self):
        app = self.page(self.data + b'bad,row\r\n')
        self.assertIn('expected 3 fields', app.error[0].value)
        self.assertFalse(any(b.label.startswith('Confirm import') for b in app.button))
        self.assertEqual(self.saved(), [])

    def test_ui_write_failure_shows_retry_advice(self):
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute("create trigger fail_insert before insert on bookRec when NEW.BookCode = '+001' begin select raise(ABORT, 'test failure'); end")
            conn.commit()
        app = self.page(self.data)
        self.confirm(app).click().run()
        self.assertFalse(app.exception)
        self.assertIn('No books were added', app.error[0].value)
        self.assertIn('writable', app.error[0].value)
        self.assertEqual(self.saved(), [])


if __name__ == '__main__':
    unittest.main()
