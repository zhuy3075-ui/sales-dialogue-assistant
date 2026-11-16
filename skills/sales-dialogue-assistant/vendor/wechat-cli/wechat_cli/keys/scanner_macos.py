"""Sales patch: explicit key extraction; never re-sign WeChat or print keys."""
import json
import os
import platform
from pathlib import Path
import subprocess
from .common import collect_db_files, cross_verify_keys, save_results, verify_enc_key


def extract_keys(db_dir, output_path, pid=None):
    machine = platform.machine().lower()
    if machine not in ('arm64', 'x86_64'):
        raise RuntimeError(f'Unsupported macOS architecture: {machine}')
    binary = Path(__file__).resolve().parents[1] / 'bin' / f'find_all_keys_macos.{machine}'
    if not binary.is_file():
        raise RuntimeError('Missing native scanner; run the skill installer first')
    target = Path(output_path).resolve()
    if target.exists():
        raise RuntimeError('Key file exists; preserve it and select a new account profile')
    processes = subprocess.run(['pgrep','-x','WeChat'],capture_output=True,text=True)
    candidates = [int(p) for p in processes.stdout.split() if p.isdigit()]
    if pid is None and len(candidates) != 1:
        raise RuntimeError('Specify --pid for one running WeChat process')
    pid = pid if pid is not None else candidates[0]
    if pid not in candidates: raise RuntimeError('Selected PID is not WeChat')
    env = dict(os.environ, WECHAT_CLI_KEYS_OUTPUT=str(target), WECHAT_CLI_DB_DIR=str(Path(db_dir).resolve()))
    command = [str(binary),str(pid)]
    result = subprocess.run(command, cwd=str(Path(db_dir).resolve().parent), env=env,
                            capture_output=True, text=True, timeout=120)
    log = (result.stdout or '') + (result.stderr or '')
    if 'task_for_pid' in log or result.returncode != 0:
        raise RuntimeError('macOS denied process access. No signature or permission changed. Use an existing key/export or request explicit OS authorization separately.')
    if not target.exists():
        raise RuntimeError('Scanner produced no key file; raw scanner output withheld')
    target.chmod(0o600)
    keys = json.loads(target.read_text(encoding='utf-8'))
    db_files, salt_to_dbs = collect_db_files(db_dir)
    matched = {}
    for rel, path, size, salt, first_page in db_files:
        value = keys.get(rel.replace('\\','/'), {})
        key = value.get('enc_key', '')
        if key and verify_enc_key(bytes.fromhex(key), first_page): matched[salt] = key
    if not matched:
        raise RuntimeError('No verified database keys')
    cross_verify_keys(db_files, salt_to_dbs, matched, lambda *a: None)
    return save_results(db_files, salt_to_dbs, matched, str(target), lambda *a: None)
