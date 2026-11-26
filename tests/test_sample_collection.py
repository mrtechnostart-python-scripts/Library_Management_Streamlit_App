"""Sample mode checks in temporary folders, with no writes to real records."""
from contextlib import closing
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class SampleCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(__file__).resolve().parents[1]
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(root / 'Library.py', self.app_path)
        self.real_path = self.app_path.with_name('library.db')
        shutil.copyfile(root / 'library.db', self.real_path)
        self.real_before = self.real_path.read_bytes()
        self.sample_path = self.app_path.with_name('library-sample.db')

    def page(self, name='Home', sample=True):
        menu = patch('streamlit_option_menu.option_menu', return_value=name)
        menu.start()
        self.addCleanup(menu.stop)
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        # Start in sample mode before any database is opened.
        if sample:
            app.session_state['collection'] = 'Sample collection'
        app.run()
        self.assertFalse(app.exception)
        return app

    def rows(self, table):
        with closing(sqlite3.connect(self.sample_path)) as conn:
            return conn.execute('select * from ' + table).fetchall()

    def assert_isolated(self):
        self.assertEqual(self.real_path.read_bytes(), self.real_before)

    def test_default_path_and_explicit_sample_selection(self):
        app = self.page(sample=False)
        self.assertEqual(app.sidebar.radio[0].value, 'Existing library')
        self.assertFalse(self.sample_path.exists())
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertFalse(app.exception)
        self.assertIn('library-sample.db', app.sidebar.info[0].value)
        self.assertEqual(len(self.rows('bookRec')), 3)
        self.assert_isolated()

    def test_sample_never_connects_to_real_database(self):
        connect = sqlite3.connect
        opened = []

        def record_connection(path, *args, **kwargs):
            opened.append(Path(path))
            return connect(path, *args, **kwargs)

        with patch('sqlite3.connect', side_effect=record_connection):
            self.page()
        self.assertEqual(opened, [self.sample_path])
        self.assert_isolated()

    def test_repeated_initialization_and_deleted_seeds_stay_deleted(self):
        self.page()
        original = self.rows('bookRec')
        for _ in range(3):
            self.page()
        self.assertEqual(self.rows('bookRec'), original)
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('delete from bookRec')
            conn.commit()
        self.page()
        self.assertEqual(self.rows('bookRec'), [])
        self.assert_isolated()

    def test_populated_unmarked_sample_is_not_reseeded(self):
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('create table bookRec(BookName Text,BookCode Text,DateAdded Text)')
            conn.execute('insert into bookRec values(?,?,?)', ('My existing sample', 'OWN-1', '2026-01-01'))
            conn.commit()
        self.page()
        self.assertEqual(self.rows('bookRec'), [('My existing sample', 'OWN-1', '2026-01-01')])
        self.assert_isolated()

    def test_add_issue_return_and_new_session_persistence(self):
        app = self.page('Add Books')
        app.text_input[0].set_value('My Test Book')
        app.text_input[1].set_value('TRY-001')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.success), 1)
        issue = self.page('Issue Book')
        for widget, value in zip(issue.text_input, ['TEST-001', 'Reading', 'TRY-001', 'Sample Reader']):
            widget.set_value(value)
        issue.button[0].click().run()
        self.assertFalse(issue.exception)
        self.assertEqual(len(issue.success), 1)
        restarted = self.page('Issue Book')
        restarted.button[1].click().run()
        self.assertEqual(restarted.dataframe[0].value.iloc[0]['BookCode'], 'TRY-001')
        returned = self.page('Delete Records')
        returned.text_input[0].set_value('TEST-001')
        returned.text_input[1].set_value('TRY-001')
        returned.button[0].click().run()
        self.assertFalse(returned.exception)
        self.assertEqual(len(returned.success), 1)
        restarted = self.page('Issue Book')
        restarted.button[1].click().run()
        self.assertEqual(len(restarted.dataframe[0].value), 0)
        books = self.page('Add Books')
        books.button[1].click().run()
        self.assertIn('TRY-001', books.dataframe[0].value['BookCode'].tolist())
        self.assertEqual(len(self.rows('bookRec')), 4)
        self.assert_isolated()

    def test_switching_collections_clears_unfinished_inputs(self):
        app = self.page('Add Books')
        app.text_input[0].set_value('Sample draft').run()
        app.sidebar.radio[0].set_value('Existing library').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, '')
        self.assertIn('library.db', app.sidebar.info[0].value)
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, '')
        self.assert_isolated()

    def test_missing_real_database_is_not_created_in_sample_mode(self):
        self.real_path.unlink()
        self.page()
        self.assertFalse(self.real_path.exists())
        self.assertEqual(len(self.rows('bookRec')), 3)

    def test_symlinked_sample_is_refused(self):
        try:
            self.sample_path.symlink_to(self.real_path)
        except OSError as error:
            # Windows can require Developer Mode or elevated symlink privileges.
            # Do not hide other filesystem errors or skip the hardlink check.
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable (winerror 1314)')
            raise
        app = self.page()
        self.assertIn('separate file', app.error[0].value)
        self.assert_isolated()

    def test_hardlinked_sample_is_refused(self):
        os.link(self.real_path, self.sample_path)
        app = self.page()
        self.assertIn('separate file', app.error[0].value)
        self.assert_isolated()


if __name__ == '__main__':
    unittest.main()
