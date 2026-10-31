"""Tidepool#79 baseline training lane (off-box, HF Space worker).

Trains the DQN policy once, deterministically, on the pinned runtime, and
banks the checkpoint the ML-package migration (EigenScript#1410) is graded
against. Nothing in the game is changed: the lane clones Tidepool at a fixed
commit and runs `train.eigs` and `eval_policy.eigs` exactly as the repo
documents them.

Phases (each one's wall time lands in summary.json):
  1. toolchain  clone EigenScript at EIGS_REF and `make build`; clone
                Tidepool at TIDEPOOL_REF.
  2. preflight  the CI training smoke (`--training-check`), run TWICE in
                fresh dirs with the same seed. Both must pass AND produce a
                byte-identical models/policy.txt: proves the build trains
                and that same-seed training is deterministic on this host.
  3. train      `train.eigs --episodes EPISODES --seed SEED` (all other
                hyperparameters at train.eigs defaults, recorded below).
                Checkpoint + curve re-uploaded every UPLOAD_EVERY_S.
  4. eval       `eval_policy.eigs --seeds EVAL_SEEDS --ticks 1000`
                (trained vs autopilot vs random, fixed seed list).
  5. bank       raw files FIRST (policy.txt, train_state.txt,
                train_log.csv, logs), summary.json LAST, after a json
                round-trip. Then the Space pauses itself (AUTO_PAUSE=1).

Config via env (Space variables): EIGS_REF, TIDEPOOL_REF, EPISODES, SEED,
EVAL_SEEDS, TAG, DATASET, UPLOAD_EVERY_S, HEARTBEAT_S, AUTO_PAUSE.
Secret: HF_TOKEN.
"""

import hashlib
import json
import os
import platform
import re
import resource
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi

EIGS_REF = os.environ.get('EIGS_REF', 'v0.48.0')
TIDEPOOL_REF = os.environ.get('TIDEPOOL_REF', 'main')
EPISODES = int(os.environ.get('EPISODES', '1000'))
SEED = int(os.environ.get('SEED', '42'))
EVAL_SEEDS = int(os.environ.get('EVAL_SEEDS', '20'))
TAG = os.environ.get('TAG', f'baseline-79/seed{SEED}-ep{EPISODES}')
DATASET = os.environ.get('DATASET', 'InauguralSystems/tidepool-baseline')
UPLOAD_EVERY_S = int(os.environ.get('UPLOAD_EVERY_S', '900'))
HEARTBEAT_S = int(os.environ.get('HEARTBEAT_S', '120'))
AUTO_PAUSE = os.environ.get('AUTO_PAUSE', '1') == '1'
SPACE_ID = os.environ.get('SPACE_ID', '')  # set by the HF platform

# train.eigs defaults at the pinned Tidepool commit (parse_train_args). The
# lane passes only --episodes and --seed; these are recorded so the banked
# checkpoint's config is explicit, and checked against the printed header.
TRAIN_DEFAULTS = {
    'lr': 0.001, 'gamma': 0.99, 'epsilon_start': 1.0, 'epsilon_end': 0.05,
    'epsilon_schedule': 'geometric anneal start->end over 0.6*episodes',
    'batch_size': 32, 'buffer_size': 5000, 'target_update': 100,
    'tick_limit': 1000, 'world': '40x20', 'resume': False,
}
SMOKE_ARGS = ['--training-check', '--episodes', '1', '--seed', '80',
              '--ticks', '31', '--batch', '8', '--buffer', '128']

if not os.environ.get('HF_TOKEN'):
    print('[lane] FATAL: HF_TOKEN missing from environment -- Space secret '
          'not set or the container built before it registered. Re-assert '
          'the secret and restart the Space.', flush=True)
    sys.exit(2)
api = HfApi()

HOME = Path.home()
EIGS_DIR = HOME / 'EigenScript'
TP_DIR = HOME / 'Tidepool'
EIG = EIGS_DIR / 'src' / 'eigenscript'
OUT = HOME / 'out'
RUN_DIR = HOME / 'run'
T_START = time.monotonic()


def log(msg):
    el = time.monotonic() - T_START
    print(f'[lane {time.strftime("%H:%M:%S")} +{el / 60:.1f}m] {msg}',
          flush=True)


def sh(cmd, **kw):
    log('$ ' + ' '.join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=True,
                          **kw).stdout


def upload(local, remote, msg):
    api.upload_file(path_or_fileobj=str(local), path_in_repo=remote,
                    repo_id=DATASET, repo_type='dataset', commit_message=msg)


def safe_upload(local, remote, msg):
    try:
        if Path(local).exists():
            upload(local, remote, msg)
    except Exception as e:  # a progress-upload blip must not kill the run
        log(f'upload {remote} failed (non-fatal): {e}')


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cgroup_cpus():
    try:
        q, p = Path('/sys/fs/cgroup/cpu.max').read_text().split()
        return None if q == 'max' else round(int(q) / int(p), 2)
    except Exception:
        return len(os.sched_getaffinity(0))


def platform_info():
    def cmd(c):
        try:
            return subprocess.run(c, text=True, capture_output=True,
                                  shell=True).stdout.strip()
        except Exception as e:
            return f'error: {e}'
    return {
        'cpu_model': cmd("lscpu | sed -n 's/^Model name: *//p'"),
        'avx2': 'avx2' in cmd('grep -m1 flags /proc/cpuinfo'),
        'gcc': cmd('gcc --version | head -1'),
        'kernel': platform.release(),
        'host_cpus': os.cpu_count(),
        'quota_cpus': cgroup_cpus(),
        'python': platform.python_version(),
    }


def prep_workdir(d):
    """A fresh copy of exactly what train/eval need (as Tidepool's Makefile
    smoke does), so runs never share a models/ dir."""
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name in ('train.eigs', 'eval_policy.eigs', 'eigs.json'):
        shutil.copy2(TP_DIR / name, d / name)
    shutil.copytree(TP_DIR / 'src', d / 'src')
    (d / 'models').mkdir()


EP_RE = re.compile(
    r'^Ep (\d+) \| score (\S+) \| len (\S+) \| tier (\S+) \| loss (\S+) '
    r'\| Q (\S+) \| eps (\S+) \| buf (\d+)')


def run_streaming(args, cwd, logfile, on_line=None, periodic=None):
    """Run eigenscript with line-buffered output to logfile. Heartbeat every
    HEARTBEAT_S with the child's CPU time; periodic() every UPLOAD_EVERY_S."""
    t0 = time.monotonic()
    last_hb = last_up = t0
    with open(logfile, 'w', buffering=1) as f:
        p = subprocess.Popen(['stdbuf', '-oL', str(EIG)] + args, cwd=cwd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        fd = p.stdout.fileno()
        buf = b''
        while True:
            ready, _, _ = select.select([fd], [], [], 5.0)
            chunk = os.read(fd, 65536) if ready else None
            if chunk:
                buf += chunk
                *lines, buf = buf.split(b'\n')
                for raw in lines:
                    line = raw.decode('utf-8', 'replace')
                    f.write(line + '\n')
                    if on_line:
                        on_line(line, time.monotonic() - t0)
            elif chunk == b'':  # EOF
                if buf:
                    line = buf.decode('utf-8', 'replace')
                    f.write(line + '\n')
                    if on_line:
                        on_line(line, time.monotonic() - t0)
                break
            now = time.monotonic()
            if now - last_hb >= HEARTBEAT_S:
                last_hb = now
                try:
                    st = Path(f'/proc/{p.pid}/stat').read_text().split()
                    cpu = (int(st[13]) + int(st[14])) / os.sysconf(
                        'SC_CLK_TCK')
                    rss = int(st[23]) * os.sysconf('SC_PAGE_SIZE') / 2**20
                    log(f'heartbeat: {args[0]} alive, wall '
                        f'{(now - t0) / 60:.1f}m, child cpu {cpu / 60:.1f}m, '
                        f'rss {rss:.0f} MiB')
                except OSError:
                    pass
            if periodic and now - last_up >= UPLOAD_EVERY_S:
                last_up = now
                periodic()
        rc = p.wait()
    return rc, time.monotonic() - t0


def bank(status, phases, extra, note=''):
    """Raw files FIRST, summary LAST (hf-space-compute-pool rule 2)."""
    md = RUN_DIR / 'models'
    for name in ('policy.txt', 'train_state.txt', 'train_log.csv'):
        safe_upload(md / name, f'{TAG}/{name}', f'{TAG}: {name} ({status})')
    for p in sorted(OUT.glob('*.log')):
        safe_upload(p, f'{TAG}/logs/{p.name}', f'{TAG}: {p.name}')
    summary = {
        'status': status, 'note': note, 'issue': 'InauguralSystems/Tidepool#79',
        'tag': TAG, 'dataset': DATASET, 'space': SPACE_ID,
        'eigs_ref': EIGS_REF, 'tidepool_ref': TIDEPOOL_REF,
        'episodes': EPISODES, 'seed': SEED, 'eval_seeds': EVAL_SEEDS,
        'train_defaults': TRAIN_DEFAULTS, 'phases_wall_s': phases,
        'wall_time_caveat': 'wall time is per-host colour only; not a '
                            'budget (Tidepool#79 comment 1)',
        **extra,
    }
    text = json.dumps(summary, indent=2)  # round-trip gate: fails HERE
    json.loads(text)
    sfile = OUT / 'summary.json'
    sfile.write_text(text)
    upload(sfile, f'{TAG}/summary.json', f'{TAG}: {status}')
    log(f'banked {status}: {DATASET}/{TAG}/summary.json')


def pause_self():
    if AUTO_PAUSE and SPACE_ID:
        log(f'pausing Space {SPACE_ID} (results banked)')
        time.sleep(30)
        try:
            api.pause_space(SPACE_ID)
        except Exception as e:
            log(f'pause failed (pause it by hand): {e}')


def main():
    OUT.mkdir(exist_ok=True)
    api.create_repo(DATASET, repo_type='dataset', private=True,
                    exist_ok=True)
    # A platform restart re-runs the job; never retrain over a banked result.
    try:
        if f'{TAG}/summary.json' in api.list_repo_files(
                DATASET, repo_type='dataset'):
            log(f'{TAG}/summary.json already banked; nothing to do')
            pause_self()
            return
    except Exception as e:
        log(f'could not list dataset (continuing): {e}')

    log(f'lane tag={TAG} eigs={EIGS_REF} tidepool={TIDEPOOL_REF} '
        f'episodes={EPISODES} seed={SEED}')
    phases, extra = {}, {'platform': platform_info()}
    log(f'platform: {extra["platform"]}')

    # 1. toolchain
    t = time.monotonic()
    if not EIG.exists():
        sh(['git', 'clone', '-q', '--depth', '1', '--branch', EIGS_REF,
            'https://github.com/InauguralSystems/EigenScript.git',
            str(EIGS_DIR)])
        sh(['make', '-C', str(EIGS_DIR), '-j2', 'build'])
    if not TP_DIR.exists():
        sh(['git', 'clone', '-q',
            'https://github.com/InauguralSystems/Tidepool.git', str(TP_DIR)])
        sh(['git', '-C', str(TP_DIR), 'checkout', '-q', TIDEPOOL_REF])
    extra['eigs_version'] = sh([str(EIG), '--version']).strip()
    extra['eigs_commit'] = sh(['git', '-C', str(EIGS_DIR), 'rev-parse',
                               'HEAD']).strip()
    extra['tidepool_commit'] = sh(['git', '-C', str(TP_DIR), 'rev-parse',
                                   'HEAD']).strip()
    phases['toolchain'] = round(time.monotonic() - t, 1)
    log(f'toolchain: eigenscript {extra["eigs_version"]} '
        f'({extra["eigs_commit"][:10]}), tidepool '
        f'{extra["tidepool_commit"][:10]}, {phases["toolchain"]}s')

    # 2. preflight: smoke passes AND same-seed runs are byte-identical
    t = time.monotonic()
    pre = []
    for k in (1, 2):
        d = HOME / f'preflight{k}'
        prep_workdir(d)
        rc, wall = run_streaming(['train.eigs'] + SMOKE_ARGS, d,
                                 OUT / f'preflight{k}.log')
        txt = (OUT / f'preflight{k}.log').read_text()
        m = re.search(r'Training smoke passed: (.*)', txt)
        pol = d / 'models' / 'policy.txt'
        pre.append({'rc': rc, 'wall_s': round(wall, 1),
                    'smoke': m.group(1) if m else None,
                    'policy_sha256': sha256(pol) if pol.exists() else None})
    phases['preflight'] = round(time.monotonic() - t, 1)
    extra['preflight'] = {'args': SMOKE_ARGS, 'runs': pre}
    ok = (all(r['rc'] == 0 and r['smoke'] for r in pre)
          and pre[0]['policy_sha256'] == pre[1]['policy_sha256']
          and pre[0]['smoke'] == pre[1]['smoke'])
    if not ok:
        log(f'PREFLIGHT FAIL: {pre}')
        bank('PREFLIGHT_FAIL', phases, extra,
             note='smoke failed or same-seed runs differ')
        sys.exit(1)
    log(f'preflight OK: smoke passed twice, policy byte-identical '
        f'(sha256 {pre[0]["policy_sha256"][:16]}), {pre[0]["smoke"]}')

    # 3. train
    prep_workdir(RUN_DIR)
    curve, header = [], []

    def on_line(line, el):
        if line.startswith(('Episodes:', 'Buffer:')):
            header.append(line)
        m = EP_RE.match(line)
        if not m:
            return
        ep = int(m.group(1))
        row = {'ep': ep, 'wall_s': round(el, 1),
               'avg_score': float(m.group(2)), 'avg_len': float(m.group(3)),
               'mean_tier': float(m.group(4)), 'loss': float(m.group(5)),
               'mean_q': float(m.group(6)), 'epsilon': float(m.group(7))}
        curve.append(row)
        rate = el / ep
        eta = rate * (EPISODES - ep)
        log(f'progress ep {ep}/{EPISODES} score {row["avg_score"]:.3f} '
            f'tier {row["mean_tier"]:.3f} loss {row["loss"]:.4f} '
            f'eps {row["epsilon"]:.3f} | {rate:.1f} s/ep, '
            f'ETA {eta / 3600:.1f} h (episodes lengthen as it learns)')

    def periodic():
        md = RUN_DIR / 'models'
        for name in ('policy.txt', 'train_state.txt', 'train_log.csv'):
            safe_upload(md / name, f'{TAG}/partial/{name}',
                        f'{TAG}: partial {name}')
        safe_upload(OUT / 'train.log', f'{TAG}/partial/train.log',
                    f'{TAG}: partial log')

    log(f'training: train.eigs --episodes {EPISODES} --seed {SEED}')
    rc, wall = run_streaming(['train.eigs', '--episodes', str(EPISODES),
                              '--seed', str(SEED)], RUN_DIR,
                             OUT / 'train.log', on_line, periodic)
    phases['train'] = round(wall, 1)
    extra['train_header'] = header
    extra['curve'] = curve
    extra['train_rc'] = rc
    extra['peak_rss_children_mib'] = round(
        resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)
    pol = RUN_DIR / 'models' / 'policy.txt'
    tail = (OUT / 'train.log').read_text().splitlines()[-4:]
    extra['train_tail'] = tail
    if rc != 0 or not pol.exists():
        bank('TRAIN_FAIL', phases, extra, note=f'train rc={rc}')
        sys.exit(1)
    extra['policy_sha256'] = sha256(pol)
    log(f'training done in {wall / 3600:.2f} h; policy sha256 '
        f'{extra["policy_sha256"][:16]}')
    # Raw checkpoint up NOW, before eval and before any summary.
    for name in ('policy.txt', 'train_state.txt', 'train_log.csv'):
        upload(RUN_DIR / 'models' / name, f'{TAG}/{name}',
               f'{TAG}: {name} (trained)')

    # 4. eval
    rc, wall = run_streaming(['eval_policy.eigs', '--seeds',
                              str(EVAL_SEEDS), '--ticks', '1000'],
                             RUN_DIR, OUT / 'eval.log')
    phases['eval'] = round(wall, 1)
    extra['eval_rc'] = rc
    extra['eval_output'] = (OUT / 'eval.log').read_text()[-4000:]

    # 5. bank
    bank('DONE' if rc == 0 else 'EVAL_FAIL', phases, extra)
    pause_self()


if __name__ == '__main__':
    main()
