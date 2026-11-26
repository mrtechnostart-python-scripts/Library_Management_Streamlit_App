"""Fresh-install verification. Standard library only; run with the Python to test."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, env, timeout=300):
    print('+ ' + ' '.join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True, timeout=timeout)


def startup(python, app, cwd, env):
    # Bind briefly to find a free loopback port. Fail on the rare allocation race.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with (cwd / 'startup.log').open('w+', encoding='utf-8') as log:
        process = subprocess.Popen([
            str(python), '-m', 'streamlit', 'run', str(app),
            '--server.headless=true', '--server.address=127.0.0.1',
            f'--server.port={port}', '--browser.gatherUsageStats=false',
            '--server.fileWatcherType=none',
        ], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Streamlit exited before becoming ready')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=2) as response:
                        if response.status == 200 and response.read() == b'ok':
                            break
                except (URLError, TimeoutError):
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError('Streamlit health check timed out after 45 seconds')
            with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                if response.status != 200 or b'<html' not in response.read().lower():
                    raise RuntimeError('Streamlit did not serve its HTML page')
            print('PASS: Streamlit CLI, health endpoint and HTML page', flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            log.seek(0)
            print(log.read(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='Save installed versions as JSON (no records).')
    args = parser.parse_args()
    if sys.version_info[:2] not in [(3, 11), (3, 12), (3, 13)]:
        parser.error('The check matrix targets Python 3.11, 3.12 and 3.13.')
    print(f'Environment: {platform.platform()}, Python {platform.python_version()}', flush=True)
    database = ROOT / 'library.db'
    original = hashlib.sha256(database.read_bytes()).hexdigest()
    try:
        with tempfile.TemporaryDirectory(prefix='library-setup-') as folder:
            work = Path(folder)
            # Run everything from a disposable copy, including the supplied fixture.
            project = work / 'project'
            project.mkdir()
            for name in ['Library.py', 'library.db', 'requirements.txt']:
                shutil.copyfile(ROOT / name, project / name)
            shutil.copytree(ROOT / 'tests', project / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / '.github' / 'ISSUE_TEMPLATE', project / '.github' / 'ISSUE_TEMPLATE')
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
            env['PYTHONUTF8'] = '1'
            env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
            env['PIP_NO_INPUT'] = '1'
            env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
            venv = work / 'venv'
            run([sys.executable, '-m', 'venv', str(venv)], work, env)
            python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            run([str(python), '-m', 'pip', 'install', '-r', 'requirements.txt'], project, env, timeout=600)
            run([str(python), '-m', 'pip', 'check'], project, env)
            # AppTest executes the app; the HTTP health endpoint alone does not.
            run([str(python), '-m', 'unittest', 'discover', '-s', 'tests', '-v'], project, env)
            # Start from outside the app directory, including spaces in both paths.
            smoke = work / 'startup app'
            smoke.mkdir()
            shutil.copyfile(project / 'Library.py', smoke / 'Library.py')
            unrelated = work / 'unrelated working directory'
            unrelated.mkdir()
            run([str(python), '-c', (
                'import sys; from streamlit.testing.v1 import AppTest; '
                'app = AppTest.from_file(sys.argv[1], default_timeout=20).run(); '
                'assert not app.exception, str(app.exception); '
                'assert app.title[0].value == "Library Management Program"; '
                'assert app.subheader[0].value == "Dashboard"'
            ), str(smoke / 'Library.py')], unrelated, env)
            if not (smoke / 'library.db').is_file() or (unrelated / 'library.db').exists():
                raise RuntimeError('App execution did not create its database beside Library.py')
            print('PASS: real app script executed from unrelated directory with a new database', flush=True)
            startup(python, smoke / 'Library.py', unrelated, env)
            if args.report:
                import json
                versions = subprocess.check_output([str(python), '-m', 'pip', 'list', '--format=json'], env=env, timeout=30)
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps({
                    'platform': platform.platform(), 'python': platform.python_version(),
                    'packages': json.loads(versions), 'result': 'passed',
                }, indent=2) + '\n', encoding='utf-8')
    finally:
        if hashlib.sha256(database.read_bytes()).hexdigest() != original:
            raise RuntimeError('The supplied database changed during verification')
    print(f'PASS: fresh install, regressions, startup; supplied database unchanged ({original})', flush=True)


if __name__ == '__main__':
    main()
