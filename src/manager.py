#!/usr/bin/python3
"""Compact human-facing control panel. It never injects global input."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

HOME = Path.home()
BASE = Path(os.environ.get('DUOOMARCHY_DATA', HOME/'.local/share/duoomarchy'))
CONFIG = Path(os.environ.get('DUOOMARCHY_CONFIG', HOME/'.config/duoomarchy/config.json'))
SERVICE = os.environ.get('DUOOMARCHY_SERVICE', 'duoomarchy.service')
CONTROL = os.environ.get('DUOOMARCHY_COMMAND', str(BASE/'duoomarchy.py'))
RUNTIME_NAME = os.environ.get('DUOOMARCHY_RUNTIME', 'duoomarchy')
SOCKET = BASE/'player2/.duoomarchy-control.sock'
BG, PANEL, FIELD, TEXT, MUTED, ACCENT = '#0f1722', '#172231', '#213247', '#edf5f7', '#9fb0bf', '#5eead4'


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45)
    if result.returncode: raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Comando falhou')
    return result.stdout.strip()


def send(action):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(5); sock.connect(str(SOCKET)); sock.sendall(json.dumps({'action': action}).encode()+b'\n')
        data = b''
        while b'\n' not in data:
            piece = sock.recv(4096)
            if not piece: break
            data += piece
    result = json.loads(data)
    if not result.get('ok'): raise RuntimeError(result.get('message', 'Comando falhou'))
    return result['message']


class Manager:
    def __init__(self, root):
        self.root = root; root.title('DuoOmarchy')
        width, height = 620, 560
        root.geometry(f'{width}x{height}+{max(20,(root.winfo_screenwidth()-width)//2)}+{max(20,(root.winfo_screenheight()-height)//2)}')
        root.minsize(580, 520); root.maxsize(760, 680); root.configure(bg=BG)
        style = ttk.Style(); style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=('sans', 10))
        style.configure('TFrame', background=BG); style.configure('Panel.TFrame', background=PANEL)
        style.configure('TLabel', background=BG, foreground=TEXT); style.configure('Panel.TLabel', background=PANEL, foreground=TEXT)
        style.configure('TButton', padding=(11, 8), background=FIELD, foreground=TEXT, borderwidth=0)
        style.map('TButton', background=[('active', '#2b4660')])
        style.configure('Accent.TButton', padding=(12, 10), background=ACCENT, foreground='#062a27', font=('sans', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#8cf4e4')])
        style.configure('Danger.TButton', background='#3b2630', foreground='#fecdd3')
        style.map('Danger.TButton', background=[('active', '#5a2e3c')])

        main = ttk.Frame(root, padding=(20, 16)); main.pack(fill='both', expand=True)
        header = ttk.Frame(main); header.pack(fill='x')
        ttk.Label(header, text='DuoOmarchy', font=('sans', 22, 'bold'), foreground=ACCENT).pack(side='left')
        self.status = tk.StringVar(value='Verificando…')
        self.status_label = ttk.Label(header, textvariable=self.status, font=('sans', 9, 'bold'), foreground=MUTED)
        self.status_label.pack(side='right', pady=8)

        summary = ttk.Frame(main, style='Panel.TFrame', padding=(14, 11)); summary.pack(fill='x', pady=(10, 10))
        self.person = tk.StringVar(); self.details = tk.StringVar()
        ttk.Label(summary, textvariable=self.person, style='Panel.TLabel', font=('sans', 13, 'bold')).pack(anchor='w')
        ttk.Label(summary, textvariable=self.details, style='Panel.TLabel', foreground=MUTED).pack(anchor='w', pady=(2, 0))

        modes = ttk.Frame(main); modes.pack(fill='x')
        ttk.Button(modes, text='▶  Jogar', style='Accent.TButton', command=lambda: self.job(lambda: run([CONTROL, 'on']))).grid(row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(modes, text='▦  Trabalhar', style='Accent.TButton', command=lambda: self.job(lambda: run([CONTROL, 'work']))).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(modes, text='■  Encerrar', style='Danger.TButton', command=self.stop).grid(row=0, column=2, sticky='ew', padx=(5, 0))
        for col in range(3): modes.columnconfigure(col, weight=1)

        nav = ttk.Frame(main); nav.pack(fill='x', pady=(8, 12))
        ttk.Button(nav, text='Mostrar estação', command=lambda: self.job(lambda: run([CONTROL, 'enter']))).pack(side='left', expand=True, fill='x', padx=(0, 4))
        ttk.Button(nav, text='Configurar tudo', command=self.configure).pack(side='left', expand=True, fill='x', padx=(4, 0))

        actions = ttk.Frame(main, style='Panel.TFrame', padding=(12, 10)); actions.pack(fill='both', expand=True)
        ttk.Label(actions, text='AÇÕES RÁPIDAS', style='Panel.TLabel', foreground=MUTED, font=('sans', 9, 'bold')).pack(anchor='w', pady=(0, 7))
        grid = ttk.Frame(actions, style='Panel.TFrame'); grid.pack(fill='x')
        items = (('Steam', 'steam_open'), ('Overwatch', 'overwatch'), ('Navegador', 'browser_open'), ('Terminal', 'terminal'), ('Arquivos', 'files'), ('Codex', 'codex'), ('Claude', 'claude'))
        for index, (label, action) in enumerate(items):
            ttk.Button(grid, text=label, command=lambda a=action: self.app(a)).grid(row=index//4, column=index%4, sticky='ew', padx=3, pady=3)
        for col in range(4): grid.columnconfigure(col, weight=1)
        ttk.Button(actions, text='Fechar Steam', command=lambda: self.app('steam_close')).pack(fill='x', padx=3, pady=(7, 0))

        self.message = tk.StringVar(value='Os dois kits permanecem separados.')
        ttk.Label(main, textvariable=self.message, foreground=MUTED, wraplength=570).pack(anchor='w', pady=(10, 0))
        self.refresh()

    def job(self, fn):
        self.message.set('Aplicando…')
        def worker():
            try: result = fn() or 'Pronto.'
            except Exception as exc: result = 'Não foi possível: '+str(exc)
            self.root.after(0, lambda: self.message.set(result))
        threading.Thread(target=worker, daemon=True).start()

    def app(self, action):
        if action == 'steam_close' and not messagebox.askyesno('Fechar Steam', 'Fechar a Steam pode encerrar o jogo dela. Continuar?'): return
        if not SOCKET.exists(): self.message.set('Inicie Jogar ou Trabalhar antes de abrir aplicativos.'); return
        self.job(lambda: send(action))

    def stop(self):
        if messagebox.askyesno('Encerrar estação', 'Encerrar os aplicativos dela e liberar o kit?'):
            self.job(lambda: run([CONTROL, 'off']))

    def configure(self):
        if subprocess.run(['systemctl', '--user', 'is-active', '--quiet', SERVICE]).returncode == 0:
            self.message.set('A configuração pode ser consultada agora, mas só é salva com a estação desligada.')
        subprocess.Popen([CONTROL, 'configurar'], env=os.environ.copy())

    def refresh(self):
        try:
            active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', SERVICE]).returncode == 0
            state_path = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))/RUNTIME_NAME/'state.json'
            state = json.loads(state_path.read_text()) if active and state_path.exists() else {}
            mode = {'game': 'JOGO', 'work': 'TRABALHO'}.get(state.get('mode'), '')
            self.status.set(('● ATIVA · '+mode) if active else '○ DESLIGADA')
            self.status_label.configure(foreground=ACCENT if active else MUTED)
            p = json.loads(CONFIG.read_text())['players'][1]; locked = 'fixo' if p.get('workspace_locked', True) else 'livre'
            self.person.set(p.get('name', 'Segunda estação'))
            self.details.set(f"{p.get('monitor','?')}  ·  kit exclusivo  ·  workspaces internos 1–{p.get('internal_workspaces',9)}")
        except Exception:
            self.person.set('Configuração indisponível'); self.details.set('Abra Configurar tudo para revisar os dispositivos.')
        self.root.after(3000, self.refresh)


if __name__ == '__main__':
    window = tk.Tk(); Manager(window); window.mainloop()
