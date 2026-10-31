"""Deploy (or redeploy) the Tidepool#79 baseline lane as a private HF Space.

    python3 tools/hf_lane/deploy.py            # create/update + restart
    python3 tools/hf_lane/deploy.py --status   # stage + log tail + dataset files

Auth: the local HF login (huggingface_hub.get_token()); the token is never
printed. Hardware: cpu-basic (free). A restart re-runs the job from scratch
(same seed, deterministic) unless the TAG's summary.json is already banked.
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token

SPACE = 'InauguralSystems/tidepool-79-baseline'
HERE = Path(__file__).resolve().parent


def config():
    cfg = {}
    for line in (HERE / 'lane.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            k, v = line.split('=', 1)
            cfg[k] = v
    return cfg


def job_status(token):
    """Call the Space's /status endpoint over gradio's HTTP API (no
    gradio_client dependency): POST starts the call, GET streams SSE."""
    import json
    import requests
    base = 'https://' + SPACE.lower().replace('/', '-') + '.hf.space'
    hdr = {'Authorization': f'Bearer {token}'}
    r = requests.post(f'{base}/gradio_api/call/status', json={'data': []},
                      headers=hdr, timeout=60)
    r.raise_for_status()
    eid = r.json()['event_id']
    r = requests.get(f'{base}/gradio_api/call/status/{eid}', headers=hdr,
                     timeout=60, stream=True)
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith('data:'):
            data = json.loads(line[5:])
            if isinstance(data, list) and len(data) == 2:
                return data[0], data[1]
    raise RuntimeError('no data in /status response')


def status(api, token):
    cfg = config()
    rt = api.space_info(SPACE).runtime
    print(f'stage: {rt.stage}  hardware: {rt.hardware}')
    try:
        st, tail = job_status(token)
        lines = tail.splitlines()[1:]  # head line is clipped mid-token
        print(f'job: {st}')
        print('\n'.join(lines[-25:]))
    except Exception as e:
        print(f'(log unavailable: {e})')
    try:
        fs = [f for f in api.list_repo_files(cfg['DATASET'],
                                             repo_type='dataset')
              if f.startswith(cfg['TAG'])]
        print('dataset:', fs)
    except Exception as e:
        print(f'(dataset unavailable: {e})')


def deploy(api, token):
    cfg = config()
    api.create_repo(SPACE, repo_type='space', space_sdk='gradio',
                    private=True, exist_ok=True)
    api.create_repo(cfg['DATASET'], repo_type='dataset', private=True,
                    exist_ok=True)
    for f in ('app.py', 'job.py', 'requirements.txt', 'packages.txt'):
        api.upload_file(path_or_fileobj=str(HERE / f), path_in_repo=f,
                        repo_id=SPACE, repo_type='space')
    api.upload_file(path_or_fileobj=str(HERE / 'SPACE_README.md'),
                    path_in_repo='README.md', repo_id=SPACE,
                    repo_type='space')
    for k, v in cfg.items():
        api.add_space_variable(SPACE, k, v)
    api.add_space_secret(SPACE, 'HF_TOKEN', token)
    api.restart_space(SPACE)
    print(f'deployed https://huggingface.co/spaces/{SPACE} with {cfg}')


if __name__ == '__main__':
    api, token = HfApi(), get_token()
    if not token:
        sys.exit('no HF login: run `hf auth login`')
    (status if '--status' in sys.argv else deploy)(api, token)
