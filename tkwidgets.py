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

    def get(self):
        return self.entry
    
    def set_text(self, text):
        self.text.set(text)

    def get_text(self):
        return self.text.get()


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
