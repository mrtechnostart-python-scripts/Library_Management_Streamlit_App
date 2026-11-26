"""Optional guided trial checks, using disposable collections only."""
from contextlib import closing
from pathlib import Path
import ast
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest


class GuidedTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(__file__).resolve().parents[1]
        self.path = Path(self.temp.name) / 'Library.py'
        shutil.copyfile(root / 'Library.py', self.path)
        self.real = self.path.with_name('library.db')
        shutil.copyfile(root / 'library.db', self.real)
        self.before = self.real.read_bytes()
        self.sample = self.path.with_name('library-sample.db')
        self.menu = patch('streamlit_option_menu.option_menu', return_value='Home').start()
        self.addCleanup(patch.stopall)

    def app(self, sample=True):
        app = AppTest.from_file(str(self.path), default_timeout=15)
        if sample:
            app.session_state['collection'] = 'Sample collection'
        app.run()
        self.assertFalse(app.exception)
        return app

    def click(self, app, label):
        next(b for b in app.button if b.label == label).click().run()
        self.assertFalse(app.exception)

    def start(self):
        app = self.app()
        self.click(app, 'Start guided sample trial')
        return app

    def test_opt_in_is_read_only_and_default_navigation_is_unchanged(self):
        app = self.app(sample=False)
        self.assertEqual(app.sidebar.radio[0].value, 'Existing library')
        self.assertFalse(self.sample.exists())
        self.assertFalse(any(b.label == 'Start guided sample trial' for b in app.button))
        app.sidebar.radio[0].set_value('Sample collection').run()
        before = self.sample.read_bytes()
        self.click(app, 'Start guided sample trial')
        self.assertEqual(app.session_state['trial_code'], 'TRY-001')
        self.assertEqual(self.sample.read_bytes(), before)
        self.assertEqual(self.real.read_bytes(), self.before)
        self.assertTrue(any('No saved trial book' in i.value for i in app.info))

    def test_add_find_saved_result_and_restart(self):
        app = self.start()
        self.menu.return_value = 'Add Books'
        app.run()
        app.text_input[0].set_value('My Trial Book')
        app.text_input[1].set_value('TRY-001')
        self.click(app, 'Add Now!')
        self.assertTrue(any('Saved result confirmed' in s.value for s in app.success))
        self.assertEqual(tuple(app.dataframe[0].value.iloc[0])[:2], ('My Trial Book', 'TRY-001'))
        self.menu.return_value = 'Find Books'
        app.run()
        app.text_input[0].set_value('TRY-001').run()
        self.assertEqual(len(app.dataframe), 2)  # guide confirmation and normal search
        self.assertEqual(tuple(app.dataframe[1].value.iloc[0])[:2], ('My Trial Book', 'TRY-001'))
        restarted = self.app(sample=False)
        restarted.sidebar.radio[0].set_value('Sample collection').run()
        restarted.text_input[0].set_value('TRY-001').run()
        self.assertEqual(tuple(restarted.dataframe[0].value.iloc[0])[:2], ('My Trial Book', 'TRY-001'))
        self.assertEqual(self.real.read_bytes(), self.before)

    def test_repeated_trial_uses_free_code_and_never_counts_old_book_as_success(self):
        self.app()
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.executemany('insert into bookRec values(?,?,?)', [
                ('My Trial Book', 'TRY-001', 'saved'),
                ('Other saved book', 'TRY-002', 'saved'),
            ])
            conn.commit()
        before = self.sample.read_bytes()
        app = self.start()
        self.assertEqual(app.session_state['trial_code'], 'TRY-003')
        self.assertFalse(app.success)
        self.assertEqual(self.sample.read_bytes(), before)
        self.click(app, 'End guided trial')
        self.assertEqual(self.sample.read_bytes(), before)
        self.assertTrue(any(b.label == 'Start guided sample trial' for b in app.button))

    def test_wrong_inputs_do_not_confirm_saved_trial_and_deletion_is_visible(self):
        app = self.start()
        self.menu.return_value = 'Add Books'
        app.run()
        app.text_input[0].set_value('Different title')
        app.text_input[1].set_value('TRY-001')
        self.click(app, 'Add Now!')
        self.assertFalse(any('Saved result confirmed' in s.value for s in app.success))
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute("update bookRec set BookName='My Trial Book' where BookCode='TRY-001'")
            conn.commit()
        app.run()
        self.assertTrue(any('Saved result confirmed' in s.value for s in app.success))
        with closing(sqlite3.connect(self.sample)) as conn:
            conn.execute("delete from bookRec where BookCode='TRY-001'")
            conn.commit()
        app.run()
        self.assertFalse(any('Saved result confirmed' in s.value for s in app.success))

    def test_switching_collections_ends_guide_and_removes_task_context(self):
        app = self.start()
        app.sidebar.radio[0].set_value('Existing library').run()
        self.assertFalse(any('Guided sample trial' in h.value for h in app.subheader))
        self.assertNotIn('Attempted task', app.sidebar.code[0].value)
        self.assertEqual(self.real.read_bytes(), self.before)
        app.sidebar.radio[0].set_value('Sample collection').run()
        self.assertTrue(any(b.label == 'Start guided sample trial' for b in app.button))

    def test_guide_stays_available_on_all_pages_with_private_data_free_feedback(self):
        app = self.start()
        for page in ('Home', 'Find Books', 'Add Books', 'Delete Books', 'Issue Book', 'Delete Records', 'About'):
            with self.subTest(page=page):
                self.menu.return_value = page
                app.run()
                self.assertFalse(app.exception)
                links = [e.proto.url for e in app.get('link_button')]
                self.assertEqual(len(links), 4)
                self.assertIn('Attempted task: Guided sample trial', app.sidebar.code[0].value)
                for link in links:
                    params = parse_qs(urlsplit(link).query)
                    if 'template' in params:
                        self.assertIn('add a book in Add Books', params['steps'][0])
                    else:
                        self.assertIn('Attempted task: Guided sample trial', params['body'][0])
                    for private in ('TRY-001', 'My Trial Book', self.temp.name, 'library-sample.db'):
                        self.assertNotIn(private, str(params))
        app.session_state['form_1'] = 'PRIVATE-DRAFT'
        app.run()
        self.assertNotIn('PRIVATE-DRAFT', str([e.proto.url for e in app.get('link_button')]))

    def test_feedback_rejects_untrusted_task_values(self):
        tree = ast.parse(self.path.read_text())
        nodes = [n for n in tree.body if
                 isinstance(n, ast.FunctionDef) and n.name == 'feedback_links'
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                     ('APP_VERSION', 'FEEDBACK_DESTINATION', 'GUIDED_TASK') for t in n.targets)
                 or isinstance(n, ast.ImportFrom) and n.module == 'urllib.parse']
        ns = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<feedback>', 'exec'), ns)
        with self.assertRaises(ValueError):
            ns['feedback_links']('Sample collection', 'PRIVATE-RECORD')
        with self.assertRaises(ValueError):
            ns['feedback_links']('Existing library', 'guided-book')
        context, form, _ = ns['feedback_links']('Sample collection', 'guided-book')
        self.assertIn('Attempted task', context)
        self.assertIn('steps', parse_qs(urlsplit(form).query))


if __name__ == '__main__':
    unittest.main()
