"""Hosting entry point: bootstrap dependencies into writable persistent storage."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / '.vendor'


def runtime_ready():
    # Check in a fresh interpreter so a failed import cannot leave partial modules.
    probe = subprocess.run(
        [sys.executable, '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import fastapi, uvicorn', str(VENDOR)],
        cwd=ROOT, capture_output=True, text=True,
    )
    return probe.returncode == 0


def ensure_dependencies():
    if runtime_ready():
        return
    print('[Lingua] Installing Python dependencies into .vendor...', flush=True)
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
            '--no-cache-dir', '--upgrade', '--target', str(VENDOR),
            '-r', str(ROOT / 'backend' / 'requirements.txt'),
        ], cwd=ROOT)
    except subprocess.CalledProcessError:
        raise SystemExit('[Lingua] Dependency installation failed. Check the pip log above and network access to PyPI.')
    if not runtime_ready():
        raise SystemExit('[Lingua] Libraries were installed but could not be imported. Check the Python runtime and dependency files.')
    print('[Lingua] Dependencies ready.', flush=True)


def choose_port(explicit=None):
    value = explicit if explicit is not None else (os.getenv('PORT') or os.getenv('SERVER_PORT') or '8000')
    try:
        port = int(value)
        if not 1 <= port <= 65535:
            raise ValueError()
    except (TypeError, ValueError):
        raise SystemExit('PORT / SERVER_PORT / --port must be a number from 1 to 65535.')
    return port


def main():
    parser = argparse.ArgumentParser(description='Start Lingua on a Python hosting server.')
    parser.add_argument('--port', type=int, help='Override the port assigned through environment variables.')
    args = parser.parse_args()
    port = choose_port(args.port)
    os.chdir(ROOT)
    ensure_dependencies()
    sys.path.insert(0, str(VENDOR))
    import uvicorn
    print(f'[Lingua] Starting on 0.0.0.0:{port}', flush=True)
    uvicorn.run('backend.app:app', host='0.0.0.0', port=port, workers=1)

if __name__ == '__main__':
    main()
