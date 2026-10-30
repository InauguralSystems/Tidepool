"""Gradio wrapper for the Tidepool#79 baseline training lane.

job.py runs in a SUBPROCESS, not a thread: an in-process job starves the
gradio health endpoint and the platform restarts the container mid-run
(hf-space-compute-pool skill, ym pool 2026-07-27). The UI is only a window
onto the job's log file; /status is the API the monitor polls.
"""

import subprocess
import sys
import threading

import gradio as gr

LOG_PATH = 'job.log'
STATE = {'status': 'starting'}


def run():
    STATE['status'] = 'running'
    with open(LOG_PATH, 'w', buffering=1) as f:
        p = subprocess.Popen([sys.executable, '-u', 'job.py'],
                             stdout=f, stderr=subprocess.STDOUT)
        rc = p.wait()
    STATE['status'] = 'DONE' if rc == 0 else f'FAILED rc={rc}'


threading.Thread(target=run, daemon=True).start()


def status():
    try:
        with open(LOG_PATH) as f:
            log = f.read()[-6000:]
    except OSError:
        log = ''
    return STATE['status'], log


with gr.Blocks(title='tidepool-79-baseline') as demo:
    gr.Markdown('# Tidepool#79 baseline DQN training lane')
    st = gr.Textbox(label='status')
    lg = gr.Textbox(label='log tail', lines=30)
    btn = gr.Button('refresh')
    btn.click(status, outputs=[st, lg], api_name='status')
    demo.load(status, outputs=[st, lg])

demo.launch(server_name='0.0.0.0', server_port=7860)
