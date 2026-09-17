#!/usr/bin/python3
"""Human-facing manager. No global input, focus automation or admin privileges."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

HOME=Path.home()
BASE=Path(os.environ.get('DUOOMARCHY_DATA',HOME/'.local/share/duoomarchy'))
CONFIG=Path(os.environ.get('DUOOMARCHY_CONFIG',HOME/'.config/duoomarchy/config.json'))
SERVICE=os.environ.get('DUOOMARCHY_SERVICE','duoomarchy.service')
CONTROL=os.environ.get('DUOOMARCHY_COMMAND',str(BASE/'duoomarchy.py'))
SOCKET=BASE/'player2/.duoomarchy-control.sock'

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=45)
    if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Comando falhou')
    return result.stdout

def send(action):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(5);sock.connect(str(SOCKET))
        sock.sendall(json.dumps({'action':action}).encode()+b'\n')
        data=b''
        while b'\n' not in data:
            piece=sock.recv(4096)
            if not piece:break
            data+=piece
        result=json.loads(data)
    if not result.get('ok'):raise RuntimeError(result.get('message','Comando falhou'))
    return result['message']

class Manager:
    def __init__(self,root):
        self.root=root;root.title('DuoOmarchy — Gerenciador');root.geometry(f'700x590+{max(0,(root.winfo_screenwidth()-700)//2)}+{max(0,(root.winfo_screenheight()-590)//2)}');root.minsize(650,570)
        style=ttk.Style();style.theme_use('clam')
        style.configure('.',background='#151b25',foreground='#e6edf3',font=('sans',11))
        style.configure('TFrame',background='#151b25');style.configure('TLabel',background='#151b25')
        style.configure('TButton',padding=12,background='#243344',borderwidth=0,relief='flat');style.map('TButton',background=[('active','#35516d')])
        style.configure('Accent.TButton',background='#46dec2',foreground='#10221f',font=('sans',11,'bold'))
        style.map('Accent.TButton',background=[('active','#70efd8')])
        style.configure('TSeparator',background='#2c3949')
        root.configure(bg='#151b25')
        frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='DuoOmarchy',font=('sans',28,'bold'),foreground='#63e6cb').pack(anchor='w')
        ttk.Label(frame,text='Dois jogadores. Você no controle da segunda estação.',wraplength=590).pack(anchor='w',pady=(4,18))
        self.status=tk.StringVar(value='Verificando sessão…');self.status_label=ttk.Label(frame,textvariable=self.status,font=('sans',13,'bold'),foreground='#63e6cb');self.status_label.pack(anchor='w')
        self.details=tk.StringVar();ttk.Label(frame,textvariable=self.details,wraplength=580).pack(anchor='w',pady=(4,16))
        row=ttk.Frame(frame);row.pack(fill='x')
        ttk.Button(row,text='Ligar sessão',style='Accent.TButton',command=lambda:self.job(lambda:run([CONTROL,'on']))).pack(side='left',expand=True,fill='x',padx=(0,6))
        ttk.Button(row,text='Encerrar sessão',command=self.stop).pack(side='left',expand=True,fill='x')
        ttk.Separator(frame).pack(fill='x',pady=18)
        ttk.Label(frame,text='APLICATIVOS NA TELA DELA',font=('sans',10,'bold')).pack(anchor='w',pady=(0,8))
        apps=ttk.Frame(frame);apps.pack(fill='x')
        for i,(label,action) in enumerate((('Abrir Steam','steam_open'),('Fechar Steam','steam_close'),('Abrir Overwatch','overwatch'),('Abrir navegador','browser_open'))):
            ttk.Button(apps,text=label,command=lambda a=action:self.app(a)).grid(row=i//2,column=i%2,sticky='ew',padx=3,pady=3)
        apps.columnconfigure(0,weight=1);apps.columnconfigure(1,weight=1)
        ttk.Separator(frame).pack(fill='x',pady=18)
        ttk.Label(frame,text='Escolha saída, microfone e volume por aplicativo no Sonora.',wraplength=580).pack(anchor='w')
        self.message=tk.StringVar(value='Fechar a Steam não encerra mais a sessão.');ttk.Label(frame,textvariable=self.message,wraplength=580).pack(anchor='w',pady=10)
        self.refresh()

    def job(self,fn):
        self.message.set('Aplicando…')
        def worker():
            try:text=fn() or 'Pronto.'
            except Exception as e:text='Não foi possível: '+str(e)
            self.root.after(0,lambda:self.message.set(text))
        threading.Thread(target=worker,daemon=True).start()

    def app(self,action):
        if action=='steam_close' and not messagebox.askyesno('Fechar Steam','Fechar a Steam pode encerrar o jogo dela. Continuar?'):return
        if not SOCKET.exists():
            self.message.set('Ligue a sessão antes de abrir os aplicativos.');return
        self.job(lambda:send(action))

    def stop(self):
        if messagebox.askyesno('Encerrar sessão','Encerrar os aplicativos dela e liberar o kit? Seu jogo permanece aberto.'):
            self.job(lambda:run([CONTROL,'off']))

    def refresh(self):
        try:
            active=subprocess.run(['systemctl','--user','is-active','--quiet',SERVICE]).returncode==0
            self.status.set('● Sessão ativa' if active else '○ Sessão desligada')
            cfg=json.loads(CONFIG.read_text());p=cfg['players'][1]
            self.details.set(f"{p['name']} · Monitor {p['monitor']} · alvo {p['fps']} FPS")
        except Exception:self.details.set('Não foi possível consultar a sessão. Verifique a configuração.')
        self.root.after(4000,self.refresh)

if __name__=='__main__':
    root=tk.Tk();Manager(root);root.mainloop()
