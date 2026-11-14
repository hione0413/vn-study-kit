# -*- coding: utf-8 -*-
import threading, time, tkinter as tk
from tkinter import font as tkfont

BG, FG, MUT, ACC, LINE = '#16181c', '#e8e8e8', '#9aa0a6', '#8ab4e8', '#2c3036'
from i18n import T


class App:
    def __init__(self, lines, follower=None):
        self.lines = lines; self.i = 0; self.auto = follower is not None; self.follower = follower
        self.status = ''
        r = self.root = tk.Tk()
        r.title(T('title')); r.configure(bg=BG); r.geometry('380x560+40+40')
        r.attributes('-topmost', True); r.attributes('-alpha', 0.93)
        self.f_w = tkfont.Font(family='Yu Gothic UI', size=17)
        self.f_r = tkfont.Font(family='Yu Gothic UI', size=11)
        self.f_m = tkfont.Font(family=T('font'), size=11)
        self.f_s = tkfont.Font(family=T('font'), size=9)
        top = tk.Frame(r, bg=BG); top.pack(fill='x', padx=8, pady=(6, 2))

        def btn(text, cmd):
            b = tk.Button(top, text=text, command=cmd, bg=LINE, fg=FG, activebackground=ACC, relief='flat', bd=0, padx=8, pady=2, font=self.f_s)
            b.pack(side='left', padx=2); return b
        btn(T('prev_ch'), lambda: self.chapter(-1)); btn('◀', lambda: self.step(-1)); btn('▶', lambda: self.step(1)); btn(T('next_ch'), lambda: self.chapter(1))
        self.b_auto = btn('', self.toggle)
        self.head = tk.Label(r, bg=BG, fg=MUT, font=self.f_s, anchor='w'); self.head.pack(fill='x', padx=10)
        tk.Frame(r, bg=LINE, height=1).pack(fill='x', padx=8, pady=4)
        self.body = tk.Text(r, bg=BG, fg=FG, bd=0, highlightthickness=0, wrap='word', cursor='arrow', padx=10, pady=2, spacing3=7)
        self.body.pack(fill='both', expand=True)
        self.body.tag_configure('w', font=self.f_w, foreground=FG)
        self.body.tag_configure('wb', font=self.f_w, foreground=MUT)
        self.body.tag_configure('r', font=self.f_r, foreground=ACC)
        self.body.tag_configure('m', font=self.f_m, foreground=FG, lmargin1=14, lmargin2=14)
        self.body.tag_configure('mb', font=self.f_m, foreground=MUT, lmargin1=14, lmargin2=14)
        self.body.tag_configure('none', font=self.f_m, foreground=MUT)
        r.bind('<Right>', lambda e: self.step(1)); r.bind('<Left>', lambda e: self.step(-1))
        self.show()
        if follower:
            threading.Thread(target=self._poll, daemon=True).start()

    def toggle(self):
        if self.follower:
            self.auto = not self.auto
        self.show()

    def step(self, d):
        self.auto = False
        self.i = max(0, min(len(self.lines) - 1, self.i + d)); self.show()

    def chapter(self, d):
        self.auto = False
        ch = max(1, min(7, self.lines[self.i]['ch'] + d))
        self.i = next(k for k, l in enumerate(self.lines) if l['ch'] == ch); self.show()

    def show(self):
        l = self.lines[self.i]
        mode = T('auto') if self.auto else T('manual')
        self.b_auto.configure(text=mode, fg=ACC if self.auto else FG)
        v = ' · ' + T('voice') if l['voice'] else ''
        self.head.configure(text='%s  ·  %s%s   %s' % (T('head', ch=l['ch'], n=l['n'] + 1, total=l['total']), T('kind_' + l['kind']), v, T(self.status) if self.status else ''))
        t = self.body
        t.configure(state='normal'); t.delete('1.0', 'end')
        if not l['words']:
            t.insert('end', T('no_words'), 'none')
        for w, rd, ko, basic in l['words']:
            t.insert('end', w, 'wb' if basic else 'w')
            if rd:
                t.insert('end', '  ' + rd, 'r')
            t.insert('end', chr(10) + ko + chr(10), 'mb' if basic else 'm')
        t.configure(state='disabled'); t.yview_moveto(0)

    def _poll(self):
        while True:
            try:
                idx, status = self.follower.current()
            except Exception as e:  # keep the window alive whatever the reader does
                idx, status = None, 'read_error'
            def apply(idx=idx, status=status):
                changed = status != self.status
                self.status = status
                if self.auto and idx is not None and idx != self.i:
                    self.i = idx; changed = True
                if changed:
                    self.show()
            self.root.after(0, apply)
            time.sleep(0.25)


def run(lines, follower=None):
    App(lines, follower).root.mainloop()
