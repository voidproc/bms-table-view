import tkinter as tk
import tkinter.ttk as ttk
import webbrowser

class ClickableLabel():
    def __init__(self, parent, font):
        self.text = tk.StringVar()
        self.label = tk.Label(parent, textvariable=self.text, cursor='hand1', font=font)

    def get(self):
        return self.label
    
    def set_text(self, text):
        self.text.set('')
        if text:
            self.text.set(text)

    def set_click_event(self, url):
        self.label.unbind('<Button-1>')
        if url:
            self.label.bind('<Button-1>', lambda e: self._link_click(url))

    def _link_click(self, url):
        webbrowser.open_new(url)


class TextBox():
    def __init__(self, parent, font):
        self.text = tk.StringVar()
        self.entry = tk.Entry(parent, textvariable=self.text, font=font, width=100)

        # コンテキストメニュー
        self.menu = tk.Menu(parent, tearoff=0)
        self.menu.add_command(label = 'Cut', command=self._on_cut, font=font)
        self.menu.add_command(label = 'Copy', command=self._on_copy, font=font)
        self.menu.add_command(label = 'Paste', command=self._on_paste, font=font)
        self.menu.add_command(label = 'Delete', command=self._on_delete, font=font)
        self.menu.add_command(label = 'Select all', command=self._on_select_all, font=font)

        self.entry.bind('<Button-3>', self._popup_menu)

    def get(self):
        return self.entry
    
    def set_text(self, text):
        self.text.set(text)

    def get_text(self):
        return self.text.get()

    def _on_cut(self):
        self.entry.event_generate('<<Cut>>')

    def _on_copy(self):
        self.entry.event_generate('<<Copy>>')

    def _on_paste(self):
        self.entry.event_generate('<<Paste>>')

    def _on_delete(self):
        self.entry.delete(self.entry.index('sel.first'), self.entry.index('sel.last'))

    def _on_select_all(self):
        self.entry.select_range(0, 'end')

    def _popup_menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()


class CheckBox():
    def __init__(self, parent, text, command):
        self.value = tk.IntVar(value=1)
        self.check = ttk.Checkbutton(parent, text=text, variable=self.value, command=command)

    def get(self):
        return self.check

    def get_value(self):
        return self.value.get()
    
    def set_value(self, val):
        self.value.set(val)
