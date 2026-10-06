#!/usr/bin/env python3
"""Install an isolated, reusable runtime. Does not upload media or alter other Skills."""
import argparse, hashlib, json, os, subprocess, sys, urllib.request, venv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FONT_COMMIT = '3be1884c48c3e45b52ecc725676a08f87776373e'
FONT_URL = f'https://raw.githubusercontent.com/google/fonts/{FONT_COMMIT}/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf'
FONT_SHA256 = '864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f'
LICENSE_URL = f'https://raw.githubusercontent.com/google/fonts/{FONT_COMMIT}/ofl/notosanstc/OFL.txt'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-asr', action='store_true', help='Render only; use when a transcript already exists')
    ap.add_argument('--runtime', type=Path, default=ROOT / '.runtime')
    args = ap.parse_args()
    if not (3, 9) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit('Python 3.9–3.12 is required for the pinned runtime. Use python3.11 or python3.12 and rerun.')
    target = args.runtime.resolve()
    if not (target / 'pyvenv.cfg').is_file():
        print('Creating isolated Python runtime…', flush=True)
        venv.EnvBuilder(with_pip=True).create(target)
    py = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    deps = [l for l in (ROOT / 'requirements.txt').read_text().splitlines() if l and not (args.no_asr and l.startswith('faster-whisper'))]
    subprocess.run([str(py), '-m', 'pip', 'install', '--disable-pip-version-check', *deps], check=True)
    env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(target / 'browsers'))
    subprocess.run([str(py), '-m', 'playwright', 'install', 'chromium', '--only-shell'], env=env, check=True)
    for name, url in [('NotoSansTC.ttf', FONT_URL), ('NotoSansTC-OFL.txt', LICENSE_URL)]:
        dest = target / name
        if not dest.exists():
            tmp = dest.with_suffix('.download')
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(dest)
    if hashlib.sha256((target/'NotoSansTC.ttf').read_bytes()).hexdigest() != FONT_SHA256:
        raise SystemExit('Font checksum mismatch; remove only the runtime font and rerun setup.')
    # Load the package's FFmpeg binary now so setup failures occur before a job starts.
    result = subprocess.check_output([str(py), '-c', 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'], text=True).strip()
    subprocess.run([result, '-version'], stdout=subprocess.DEVNULL, check=True)
    manifest = {'python': subprocess.check_output([str(py),'--version'],text=True).strip(), 'requirements_sha256': hashlib.sha256((ROOT/'requirements.txt').read_bytes()).hexdigest(), 'dependencies': deps, 'font_commit': FONT_COMMIT,
                'font_sha256': hashlib.sha256((target/'NotoSansTC.ttf').read_bytes()).hexdigest(),
                'browser_path': 'browsers', 'asr_model': 'downloaded only when transcription is requested'}
    (target/'install-receipt.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Runtime ready. Use: "{py}" "{ROOT / "scripts/reels.py"}" doctor', flush=True)

if __name__ == '__main__':
    main()
