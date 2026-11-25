"""Feedback context and URLs must never depend on local records or paths."""
from pathlib import Path
import ast
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(__file__).resolve().parents[1]
        self.app_path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(self.root / 'Library.py', self.app_path)
        shutil.copyfile(self.root / 'library.db', self.app_path.with_name('library.db'))
        self.before = self.app_path.with_name('library.db').read_bytes()
        menu = patch('streamlit_option_menu.option_menu', return_value='Home')
        menu.start()
        self.addCleanup(menu.stop)

    def app(self, mode='Existing library'):
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        app.session_state['collection'] = mode
        return app.run()

    def links(self, app):
        return [element.proto.url for element in app.sidebar.get('link_button')]

    def test_context_and_form_prefill_for_both_modes(self):
        for mode in ('Existing library', 'Sample collection'):
            with self.subTest(mode=mode):
                app = self.app(mode)
                self.assertFalse(app.exception)
                self.assertEqual(app.sidebar.code[0].value,
                                 f'App version: 0.3.0\nCollection mode: {mode}')
                form, fallback = self.links(app)
                self.assertEqual(urlsplit(form).netloc, 'github.com')
                self.assertEqual(urlsplit(form).path,
                                 '/mrtechnostart-python-scripts/Library_Management_Streamlit_App/issues/new')
                self.assertEqual(parse_qs(urlsplit(form).query), {
                    'template': ['app-feedback.yml'],
                    'versions': ['Library Management Streamlit App 0.3.0'],
                    'collection-mode': [mode],
                })
                body = parse_qs(urlsplit(fallback).query)['body'][0]
                for heading in ('What are you reporting?', 'What did you try?',
                                'What did you expect?', 'What actually happened?',
                                'Error messages', 'Operating system'):
                    self.assertIn(heading, body)
                self.assertIn(f'Collection mode: {mode}', body)
                self.assertNotIn('template', parse_qs(urlsplit(fallback).query))

    def test_switching_updates_context_and_both_links(self):
        app = self.app()
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertFalse(app.exception)
        self.assertIn('Sample collection', app.sidebar.code[0].value)
        for link in self.links(app):
            self.assertIn('Sample collection', str(parse_qs(urlsplit(link).query)))
        app.sidebar.radio[0].set_value('Existing library').run()
        self.assertIn('Existing library', app.sidebar.code[0].value)
        self.assertEqual(self.app_path.with_name('library.db').read_bytes(), self.before)

    def test_records_inputs_and_paths_do_not_enter_context(self):
        database = self.app_path.with_name('library.db')
        conn = sqlite3.connect(database)
        conn.execute('insert into bookRec values(?,?,?)', ('PRIVATE-BOOK', 'PRIVATE-CODE', 'PRIVATE-DATE'))
        conn.execute('insert into libTab values(?,?,?,?,?,?)',
                     ('PRIVATE-ID', 'PRIVATE-COURSE', 'PRIVATE-CODE', 'PRIVATE-STUDENT', 'date', 'date'))
        conn.commit()
        conn.close()
        before = database.read_bytes()
        app = AppTest.from_file(str(self.app_path), default_timeout=15)
        app.session_state['form_1'] = 'PRIVATE-DRAFT'
        app.run()
        outputs = app.sidebar.code[0].value + '\n'.join(self.links(app))
        self.assertNotIn('PRIVATE-', outputs)
        self.assertNotIn(self.temp.name, outputs)
        self.assertNotIn('library.db', outputs)
        self.assertEqual(database.read_bytes(), before)

    def test_feedback_available_before_database_startup_failure(self):
        with patch('sqlite3.connect', side_effect=sqlite3.OperationalError('Cannot open database')):
            app = self.app()
        self.assertTrue(app.exception)
        self.assertEqual(len(self.links(app)), 2)
        self.assertIn('Existing library', app.sidebar.code[0].value)

    def test_every_menu_page_has_feedback(self):
        for name in ('Home', 'Find Books', 'Add Books', 'Delete Books', 'Issue Book', 'Delete Records', 'About'):
            with self.subTest(page=name), patch('streamlit_option_menu.option_menu', return_value=name):
                app = self.app()
                self.assertFalse(app.exception)
                self.assertEqual(len(self.links(app)), 2)

    def test_form_ids_match_prefill_keys(self):
        template = (self.root / '.github/ISSUE_TEMPLATE/app-feedback.yml').read_text()
        self.assertIn('id: versions', template)
        self.assertIn('id: collection-mode', template)
        # Extract just the pure helper, without running the app or opening SQLite.
        tree = ast.parse(self.app_path.read_text())
        nodes = [node for node in tree.body if
                 isinstance(node, ast.FunctionDef) and node.name == 'feedback_links'
                 or isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id in ('APP_VERSION', 'FEEDBACK_DESTINATION')
                     for target in node.targets)
                 or isinstance(node, ast.ImportFrom) and node.module == 'urllib.parse']
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<feedback>', 'exec'), namespace)
        with self.assertRaises(ValueError):
            namespace['feedback_links']('/private/path/or/student/name')


if __name__ == '__main__':
    unittest.main()
