#!/usr/bin/python3
"""Compact, data-driven editor for DuoOmarchy station profiles."""
from copy import deepcopy
import tkinter as tk
from tkinter import messagebox, ttk


COLORS = {
    'bg': '#0f1722', 'panel': '#172231', 'field': '#213247', 'line': '#2c4056',
    'text': '#edf5f7', 'muted': '#9fb0bf', 'accent': '#5eead4', 'danger': '#fb7185',
}


def _display(mapping, value):
    return next((label for label, stored in mapping.items() if stored == value), next(iter(mapping), ''))


def launch(config, inventory, session_active, save_config):
    """Open the editor. save_config receives the complete edited configuration."""
    root = tk.Tk()
    root.title('DuoOmarchy — Configurar estações')
    width = min(920, max(760, root.winfo_screenwidth() - 120))
    height = min(680, max(600, root.winfo_screenheight() - 120))
    root.geometry(f'{width}x{height}+{max(20, (root.winfo_screenwidth()-width)//2)}+{max(20, (root.winfo_screenheight()-height)//2)}')
    root.minsize(760, 600)
    root.configure(bg=COLORS['bg'])

    style = ttk.Style(); style.theme_use('clam')
    style.configure('.', background=COLORS['bg'], foreground=COLORS['text'], font=('sans', 10))
    style.configure('TFrame', background=COLORS['bg'])
    style.configure('Panel.TFrame', background=COLORS['panel'])
    style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'])
    style.configure('Panel.TLabel', background=COLORS['panel'], foreground=COLORS['text'])
    style.configure('Muted.TLabel', background=COLORS['bg'], foreground=COLORS['muted'])
    style.configure('TLabelframe', background=COLORS['panel'], bordercolor=COLORS['line'], relief='solid')
    style.configure('TLabelframe.Label', background=COLORS['panel'], foreground=COLORS['accent'], font=('sans', 11, 'bold'))
    style.configure('TEntry', fieldbackground=COLORS['field'], foreground=COLORS['text'], insertcolor=COLORS['text'], bordercolor=COLORS['line'])
    style.configure('TCombobox', fieldbackground=COLORS['field'], foreground=COLORS['text'], arrowcolor=COLORS['accent'])
    style.map('TCombobox', fieldbackground=[('readonly', COLORS['field'])], foreground=[('readonly', COLORS['text'])])
    style.configure('TSpinbox', fieldbackground=COLORS['field'], foreground=COLORS['text'], arrowcolor=COLORS['accent'])
    style.configure('TCheckbutton', background=COLORS['panel'], foreground=COLORS['text'])
    style.map('TCheckbutton', background=[('active', COLORS['panel'])])
    style.configure('TNotebook', background=COLORS['bg'], borderwidth=0)
    style.configure('TNotebook.Tab', padding=(16, 8), background=COLORS['panel'], foreground=COLORS['muted'])
    style.map('TNotebook.Tab', background=[('selected', COLORS['field'])], foreground=[('selected', COLORS['accent'])])
    style.configure('TButton', padding=(12, 8), background=COLORS['field'], foreground=COLORS['text'], borderwidth=0)
    style.map('TButton', background=[('active', '#2b4660')])
    style.configure('Accent.TButton', background=COLORS['accent'], foreground='#062a27', font=('sans', 10, 'bold'))
    style.map('Accent.TButton', background=[('active', '#8cf4e4')])

    edited = deepcopy(config)
    players = edited['players']
    devices = inventory['devices']
    monitors = inventory['monitors']

    choices = {
        'monitor': {f"{m.get('description', m['name'])}  ·  {m['name']}": m['name'] for m in monitors},
        'workspace': {f'Workspace {n}': n for n in range(1, 6)},
        'keyboard': {f"{d['name']}  ·  {d['path'].split('/')[-1]}": d['path'] for d in devices if d['kind'] == 'keyboard'},
        'mouse': {f"{d['name']}  ·  {d['path'].split('/')[-1]}": d['path'] for d in devices if d['kind'] == 'mouse'},
        'gamepad': {'Nenhum controle': ''} | {f"{d['name']}  ·  {d['path'].split('/')[-1]}": d['path'] for d in devices if d['kind'] == 'gamepad'},
        'sink': {'Padrão do sistema': ''} | {f"{d.get('description', d['name'])}  ·  {d['name']}": d['name'] for d in inventory['sinks']},
        'source': {'Padrão do sistema': ''} | {f"{d.get('description', d['name'])}  ·  {d['name']}": d['name'] for d in inventory['sources']},
        'resolution': {'Nativa do monitor': 'native', '3440 × 1440': '3440x1440', '2560 × 1440': '2560x1440', '1920 × 1080': '1920x1080', '1600 × 900': '1600x900', '1280 × 720': '1280x720'},
        'scaler': {'Ajustar sem cortar': 'fit', 'Preencher a tela': 'fill', 'Esticar': 'stretch', 'Escala inteira': 'integer', 'Automático': 'auto'},
        'filter': {'Linear': 'linear', 'FSR': 'fsr', 'NIS': 'nis', 'Mais nítido': 'nearest', 'Pixel': 'pixel'},
        'backend': {'Wayland (recomendado)': 'wayland', 'SDL': 'sdl'},
        'gpu': {'Automática': ''} | {g['label']: g['id'] for g in inventory['gpus']},
        'startup': {'Abrir menu': 'menu', 'Abrir terminal': 'terminal', 'Abrir navegador': 'browser', 'Não abrir nada': 'none'},
    }

    outer = ttk.Frame(root, padding=(22, 16)); outer.pack(fill='both', expand=True)
    heading = ttk.Frame(outer); heading.pack(fill='x')
    ttk.Label(heading, text='Configurar estações', font=('sans', 22, 'bold'), foreground=COLORS['accent']).pack(side='left')
    badge_text = 'SESSÃO ATIVA · SOMENTE LEITURA' if session_active else 'PRONTO PARA EDITAR'
    ttk.Label(heading, text=badge_text, font=('sans', 9, 'bold'), foreground=COLORS['danger'] if session_active else COLORS['accent']).pack(side='right', pady=8)
    ttk.Label(outer, text='Compare os dois perfis. Cada alteração é salva como um conjunto coerente.', style='Muted.TLabel').pack(anchor='w', pady=(2, 12))

    notebook = ttk.Notebook(outer); notebook.pack(fill='both', expand=True)
    variables = [{}, {}]
    extra_lists = [None, None]

    def tab(title):
        page = ttk.Frame(notebook, padding=10); notebook.add(page, text=title)
        page.columnconfigure(0, weight=1, uniform='profiles'); page.columnconfigure(1, weight=1, uniform='profiles')
        return page

    def card(page, index):
        p = players[index]
        frame = ttk.LabelFrame(page, text=p.get('name') or f'Pessoa {index+1}', padding=12)
        frame.grid(row=0, column=index, sticky='nsew', padx=(0, 5) if index == 0 else (5, 0), pady=2)
        frame.columnconfigure(1, weight=1)
        return frame

    def entry(frame, index, row, key, label):
        ttk.Label(frame, text=label, style='Panel.TLabel').grid(row=row, column=0, sticky='w', padx=(0, 10), pady=6)
        var = tk.StringVar(value=str(players[index].get(key, ''))); variables[index][key] = var
        ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky='ew', pady=6)

    def combo(frame, index, row, key, label):
        ttk.Label(frame, text=label, style='Panel.TLabel').grid(row=row, column=0, sticky='w', padx=(0, 10), pady=6)
        mapping = choices[key]; var = tk.StringVar(value=_display(mapping, players[index].get(key, ''))); variables[index][key] = var
        ttk.Combobox(frame, textvariable=var, values=list(mapping), state='readonly').grid(row=row, column=1, sticky='ew', pady=6)

    def spin(frame, index, row, key, label, low, high, step=1):
        ttk.Label(frame, text=label, style='Panel.TLabel').grid(row=row, column=0, sticky='w', padx=(0, 10), pady=6)
        var = tk.StringVar(value=str(players[index].get(key, low))); variables[index][key] = var
        ttk.Spinbox(frame, from_=low, to=high, increment=step, textvariable=var, width=9).grid(row=row, column=1, sticky='w', pady=6)

    general = tab('Pessoas e telas')
    for i in range(2):
        frame = card(general, i)
        entry(frame, i, 0, 'name', 'Nome')
        combo(frame, i, 1, 'monitor', 'Monitor')
        combo(frame, i, 2, 'workspace', 'Workspace externo')
        var = tk.BooleanVar(value=bool(players[i].get('workspace_locked', i == 1))); variables[i]['workspace_locked'] = var
        ttk.Checkbutton(frame, text='Reservar e manter neste workspace', variable=var).grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 4))
        note = 'Seu Omarchy continua normal.' if i == 0 else 'A estação volta silenciosamente para cá se for movida.'
        ttk.Label(frame, text=note, style='Panel.TLabel', foreground=COLORS['muted'], wraplength=310).grid(row=4, column=0, columnspan=2, sticky='w', pady=(3, 0))

    input_page = tab('Periféricos')
    extras = [d for d in devices if d.get('usable')]
    for i in range(2):
        frame = card(input_page, i)
        combo(frame, i, 0, 'keyboard', 'Teclado')
        combo(frame, i, 1, 'mouse', 'Mouse')
        combo(frame, i, 2, 'gamepad', 'Controle')
        spin(frame, i, 3, 'mouse_native_dpi', 'DPI físico atual', 100, 42000, 100)
        spin(frame, i, 4, 'mouse_dpi', 'DPI desejado', 100, 42000, 100)
        ttk.Label(frame, text='Entradas extras', style='Panel.TLabel').grid(row=5, column=0, columnspan=2, sticky='w', pady=(10, 4))
        box = tk.Listbox(frame, selectmode='multiple', height=5, exportselection=False, bg=COLORS['field'], fg=COLORS['text'], selectbackground='#285b62', highlightthickness=1, highlightbackground=COLORS['line'], relief='flat')
        box.grid(row=6, column=0, columnspan=2, sticky='ew')
        selected = set(players[i].get('extra_devices', []))
        for pos, device in enumerate(extras):
            box.insert('end', f"{device['name']} · {device['kind']}")
            if device['path'] in selected: box.selection_set(pos)
        extra_lists[i] = box
        dpi_note = 'A razão entre os dois DPIs é aplicada em Jogo e Trabalho.' if i == 1 else 'O perfil principal registra o DPI; o Omarchy continua usando o ajuste físico.'
        ttk.Label(frame, text=dpi_note, style='Panel.TLabel', foreground=COLORS['muted'], wraplength=310).grid(row=7, column=0, columnspan=2, sticky='w', pady=(6, 0))

    audio = tab('Som e microfone')
    for i in range(2):
        frame = card(audio, i)
        combo(frame, i, 0, 'sink', 'Saída de áudio')
        spin(frame, i, 1, 'sink_volume', 'Volume inicial (%)', 0, 150, 5)
        combo(frame, i, 2, 'source', 'Microfone')
        spin(frame, i, 3, 'source_volume', 'Ganho inicial (%)', 0, 150, 5)
        ttk.Label(frame, text='O volume inicial só é aplicado quando um dispositivo específico foi escolhido.', style='Panel.TLabel', foreground=COLORS['muted'], wraplength=310).grid(row=4, column=0, columnspan=2, sticky='w', pady=(8, 0))

    advanced = tab('Desempenho e trabalho')
    for i in range(2):
        frame = card(advanced, i)
        spin(frame, i, 0, 'fps', 'FPS alvo', 30, 240, 5)
        combo(frame, i, 1, 'resolution', 'Resolução interna')
        combo(frame, i, 2, 'scaler', 'Encaixe')
        combo(frame, i, 3, 'filter', 'Filtro')
        combo(frame, i, 4, 'gpu', 'GPU')
        combo(frame, i, 5, 'backend', 'Backend')
        if i == 1:
            spin(frame, i, 6, 'internal_workspaces', 'Workspaces internos', 1, 9)
            combo(frame, i, 7, 'startup', 'Ao abrir Trabalho')
        else:
            ttk.Label(frame, text='As opções de trabalho pertencem à segunda estação.', style='Panel.TLabel', foreground=COLORS['muted'], wraplength=310).grid(row=6, column=0, columnspan=2, sticky='w', pady=(10, 0))

    footer = ttk.Frame(outer); footer.pack(fill='x', pady=(12, 0))
    info = tk.StringVar(value='A sessão atual continuará intacta.' if session_active else 'As mudanças entram na próxima sessão.')
    ttk.Label(footer, textvariable=info, style='Muted.TLabel').pack(side='left')

    def save():
        try:
            if session_active: raise ValueError('Encerre a sessão antes de salvar uma nova distribuição.')
            for i, p in enumerate(players):
                for key, var in variables[i].items():
                    if key in choices: p[key] = choices[key][var.get()]
                    elif key in ('fps', 'sink_volume', 'source_volume', 'internal_workspaces', 'mouse_native_dpi', 'mouse_dpi'): p[key] = int(var.get())
                    elif key == 'workspace_locked': p[key] = bool(var.get())
                    else: p[key] = var.get().strip()
                p['extra_devices'] = [extras[pos]['path'] for pos in extra_lists[i].curselection()]
            save_config(edited)
            messagebox.showinfo('Configuração salva', 'Perfis, reserva de workspace e dispositivos foram salvos.')
            root.destroy()
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Confira a configuração', str(exc))

    ttk.Button(footer, text='Cancelar', command=root.destroy).pack(side='right')
    save_button = ttk.Button(footer, text='Salvar configuração', style='Accent.TButton', command=save)
    save_button.pack(side='right', padx=(0, 8))
    if session_active: save_button.state(['disabled'])
    root.bind('<Escape>', lambda _event: root.destroy())
    root.mainloop()
