"""Desktop launcher and Windows executable entry point."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from functools import partial
from http.server import ThreadingHTTPServer
from interface.server import Handler, NeuralCore, ROOT


def start_server(port=8765):
    core = NeuralCore(ROOT / 'artifacts/aira-dialogue-v1/run-001/sft-model.pt')
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, core=core))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def open_app(url):
    if sys.platform == 'win32':
        for base in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
            directory = os.environ.get(base)
            if directory:
                edge = Path(directory) / 'Microsoft/Edge/Application/msedge.exe'
                if edge.is_file():
                    subprocess.Popen([str(edge), f'--app={url}'])
                    return
    webbrowser.open(url)


def smoke_test(output):
    """Exercise bundled assets and actual checkpoint without a display."""
    server = start_server(0)
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        health = json.load(urllib.request.urlopen(url + '/api/health', timeout=10))
        for asset in ('/', '/src/app.jsx', '/assets/avatar-ref.png', '/vendor/babel.min.js'):
            with urllib.request.urlopen(url + asset, timeout=10) as response:
                if response.status != 200 or not response.read():
                    raise RuntimeError(f'Asset ausente: {asset}')
        request = urllib.request.Request(url + '/api/chat',
            data=json.dumps({'messages': [{'role': 'user', 'content': 'Olá'}]}).encode(),
            headers={'Content-Type': 'application/json'})
        answer = json.load(urllib.request.urlopen(request, timeout=90))
        if not answer.get('reply', '').strip():
            raise RuntimeError('Resposta vazia no teste do executável.')
        output.write_text(json.dumps({'passed': True, 'frozen': bool(getattr(sys, 'frozen', False)),
            'health': health, 'actual_checkpoint_reply': answer['reply'],
            'quality_claim': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    finally:
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-test', type=Path)
    args = parser.parse_args()
    if args.smoke_test:
        try:
            smoke_test(args.smoke_test)
        except Exception as exc:
            args.smoke_test.write_text(json.dumps({'passed': False, 'error': str(exc)}), encoding='utf-8')
            raise
        return
    import tkinter as tk
    from tkinter import messagebox
    window = tk.Tk()
    window.title('E.L.Y.S.I.A.')
    window.geometry('420x210')
    window.resizable(False, False)
    status = tk.StringVar(value='Iniciando o Neural Core…')
    tk.Label(window, text='E.L.Y.S.I.A.', font=('Segoe UI', 20)).pack(pady=(20, 8))
    tk.Label(window, textvariable=status, wraplength=390).pack(pady=8)
    state = {'server': None, 'error': None, 'done': False, 'closing': False}
    def load():
        try:
            state['server'] = start_server()
        except Exception as exc:
            state['error'] = str(exc)
        finally:
            state['done'] = True
    def close():
        state['closing'] = True
        status.set('Encerrando…')
        check_close()
    def check_close():
        if not state['done']:
            window.after(100, check_close)
            return
        if state['server']:
            state['server'].shutdown()
            state['server'].server_close()
        window.destroy()
    def check_ready():
        if state['closing']:
            return
        if not state['done']:
            window.after(100, check_ready)
            return
        if state['error']:
            status.set('Não foi possível iniciar.')
            messagebox.showerror('Elysia', state['error'] + '\n\nVerifique se outra Elysia está aberta e se o Visual C++ x64 está instalado.')
            return
        status.set('Núcleo local ativo · CPU · modelo experimental')
        button.configure(state='normal')
        open_app('http://127.0.0.1:8765')
    button = tk.Button(window, text='Abrir Elysia', state='disabled',
                       command=lambda: open_app('http://127.0.0.1:8765'))
    button.pack(pady=6)
    tk.Button(window, text='Encerrar Elysia', command=close).pack()
    window.protocol('WM_DELETE_WINDOW', close)
    threading.Thread(target=load, daemon=True).start()
    window.after(100, check_ready)
    window.mainloop()


if __name__ == '__main__':
    main()
