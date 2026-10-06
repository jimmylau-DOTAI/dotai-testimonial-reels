#!/usr/bin/env python3
"""Entry point: install missing local runtime, then execute the requested stage."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    target=ROOT/'.runtime'
    python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    receipt=target/'install-receipt.json'
    expected=hashlib.sha256((ROOT/'requirements.txt').read_bytes()).hexdigest()
    current=json.loads(receipt.read_text()).get('requirements_sha256') if receipt.is_file() else None
    if current!=expected or not python.is_file() or not (target/'NotoSansTC.ttf').is_file() or not (target/'browsers').is_dir():
        subprocess.run([sys.executable,str(ROOT/'scripts/bootstrap.py')],check=True)
    if len(sys.argv)<2:
        raise SystemExit('Use: python3 scripts/run.py doctor | prepare | sync | validate | render | demo')
    if sys.argv[1]=='demo':
        argv=[str(python),str(ROOT/'scripts/demo.py'),*sys.argv[2:]]
    else:
        argv=[str(python),str(ROOT/'scripts/reels.py'),*sys.argv[1:]]
    raise SystemExit(subprocess.call(argv))

if __name__=='__main__':main()
