"""Read-only collection search checks in temporary app/database copies."""
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class BookSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(__file__).resolve().parents[1]
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(root / 'Library.py', self.app_path)
        self.real_path = self.app_path.with_name('library.db')
        shutil.copyfile(root / 'library.db', self.real_path)
        self.sample_path = self.app_path.with_name('library-sample.db')
        self.rows = [
            ('Café, "読書" 📚\nSecond line\r\nThird line', '0002', ' saved date '),
            ("  Reader's Guide  ", 'B,"3"', '2026-01-01'),
            ('Straße', 'UNICODE', ''),
            ('100%_literal', '+001', '@date'),
            ('', '', ''),
            ('duplicate', '0002', '2026-02-03'),
        ]
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('create table bookRec(BookName Text,BookCode Text,DateAdded Text)')
            conn.execute('create table libTab(CollegeID Text,Course Text,BookCode Text,StudentName Text,DateOfIssue Text,ReturnDate Text)')
            conn.execute('insert into libTab values(?,?,?,?,?,?)',
                         ('PRIVATE-ID', 'Reading', '0002', 'Private Student', '', ''))
            conn.execute('create table sampleInitialization(id integer primary key)')
            conn.execute('insert into sampleInitialization values(1)')
            conn.executemany('insert into bookRec values(?,?,?)', self.rows)
            conn.commit()
        self.menu = patch('streamlit_option_menu.option_menu', return_value='Find Books').start()
        self.addCleanup(patch.stopall)

    def page(self, sample=True):
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        if sample:
            app.session_state['collection'] = 'Sample collection'
        app.run()
        self.assertFalse(app.exception)
        return app

    def search(self, app, query):
        app.text_input[0].set_value(query).run()
        self.assertFalse(app.exception)
        return [tuple(row) for row in app.dataframe[0].value.itertuples(index=False, name=None)] if app.dataframe else []

    def test_empty_query_lists_exact_text_in_order_and_clear_restores_all(self):
        app = self.page()
        self.assertEqual(self.search(app, ''), self.rows)
        self.assertTrue(app.button[0].disabled)
        self.assertEqual(self.search(app, '0002'), [self.rows[0], self.rows[5]])
        self.assertIn('2 of 6 book records', app.caption[0].value)
        app.button[0].click().run()
        self.assertEqual(app.text_input[0].value, '')
        self.assertEqual(self.search(app, ''), self.rows)

    def test_literal_case_insensitive_code_and_title_queries(self):
        app = self.page()
        cases = {
            'cAFÉ': [self.rows[0]], '読書': [self.rows[0]], '📚': [self.rows[0]],
            'second LINE': [self.rows[0]], 'STRASSE': [self.rows[2]],
            "Reader's": [self.rows[1]], '  ': [self.rows[1]],
            'B,"3"': [self.rows[1]], '+001': [self.rows[3]],
            '%_': [self.rows[3]], '0002': [self.rows[0], self.rows[5]],
            "' OR 1=1 --": [], '2026-01-01': [], 'Private Student': [],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.search(app, query), expected)

    def test_no_match_and_empty_collection_have_actionable_messages(self):
        app = self.page()
        self.assertEqual(self.search(app, 'not found'), [])
        self.assertIn('No books match', app.info[0].value)
        self.assertIn('clear the search', app.info[0].value)
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('delete from bookRec')
            conn.commit()
        app.run()
        self.assertFalse(app.dataframe)
        self.assertIn('No books in this collection yet', app.info[0].value)

    def test_switch_resets_query_and_never_reuses_other_collection_results(self):
        app = self.page()
        self.assertEqual(len(self.search(app, '0002')), 2)
        app.sidebar.radio[0].set_value('Existing library').run()
        self.assertEqual(app.text_input[0].value, '')
        self.assertEqual(self.search(app, 'arihant'), [('Arihant Maths', 'ABCXYZ1', '2023-04-10')])
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertEqual(app.text_input[0].value, '')
        self.assertEqual(self.search(app, 'arihant'), [])
        self.assertTrue(any('Sample collection · library-sample.db' in m.value for m in app.markdown))

    def test_search_and_clear_are_read_only_and_open_only_selected_database(self):
        before = {p: p.read_bytes() for p in [self.real_path, self.sample_path]}
        connect = sqlite3.connect
        opened = []

        def tracked(path, *args, **kwargs):
            opened.append(Path(path))
            return connect(path, *args, **kwargs)

        with patch('sqlite3.connect', side_effect=tracked):
            app = self.page()
            self.search(app, 'café')
            self.search(app, 'not found')
            app.button[0].click().run()
        self.assertTrue(opened)
        self.assertEqual(set(opened), {self.sample_path})
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)

    def test_missing_existing_database_is_not_created(self):
        self.real_path.unlink()
        self.search(self.page(), '0002')
        self.assertFalse(self.real_path.exists())

    def test_add_delete_and_import_are_visible_without_stale_results(self):
        app = self.page()
        self.assertEqual(self.search(app, 'NEW-1'), [])
        self.menu.return_value = 'Add Books'
        app.run()
        app.text_input[0].set_value('New title')
        app.text_input[1].set_value('NEW-1')
        app.button[0].click().run()
        self.menu.return_value = 'Find Books'
        app.run()
        self.assertEqual(self.search(app, 'NEW-1')[0][:2], ('New title', 'NEW-1'))
        self.menu.return_value = 'Delete Books'
        app.run()
        app.text_input[0].set_value('New title')
        app.text_input[1].set_value('NEW-1')
        app.button[0].click().run()
        self.menu.return_value = 'Find Books'
        app.run()
        self.assertEqual(self.search(app, 'NEW-1'), [])
        # The import path is separately covered by confirmation/rollback tests.
        with closing(sqlite3.connect(self.sample_path)) as conn:
            conn.execute('insert into bookRec values(?,?,?)', ('Imported title', 'IMPORT-1', 'text date'))
            conn.commit()
        self.assertEqual(self.search(app, 'IMPORT-1'), [('Imported title', 'IMPORT-1', 'text date')])


if __name__ == '__main__':
    unittest.main()
