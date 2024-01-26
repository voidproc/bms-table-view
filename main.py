import os
import re
import json
import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
from tksheet import Sheet
import subprocess

import tkwidgets
import songdata
import bmstable


# 難易度表URL
TABLE_LIST = [
    { 'name': 'NEW GENERATION 通常難易度表', 'url': 'https://rattoto10.jounin.jp/table.html' },
    { 'name': 'NEW GENERATION 発狂難易度表', 'url': 'https://rattoto10.jounin.jp/table_insane.html' },
    { 'name': 'Satellite', 'url': 'https://stellabms.xyz/sl/table.html' },
    { 'name': 'LN難易度表', 'url': 'http://flowermaster.web.fc2.com/lrnanido/gla/LN.html' },
]

DEFAULT_TABLE_INDEX = 0


class MainWindow(tk.Tk):
    FONT_UI = ('MS UI Gothic', 9, 'normal')
    FONT_UI_UNDERLINE = ('MS UI Gothic', 9, 'underline')
    FONT_UI_TITLE = ('MS UI Gothic', 12, 'bold', 'underline')
    HEADERS = ['level', 'title', 'artist', 'found', 'index']

    def __init__(self):
        tk.Tk.__init__(self)

        self.title('bms-table-view')
        self.geometry('800x600')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.table_frame = tk.Frame(self)
        self.table_frame.grid_columnconfigure(0, weight=1)

        self.table_combobox = ttk.Combobox(self.table_frame,
                                           state='readonly',
                                           font=self.FONT_UI,
                                           values=[t.get('name') for t in TABLE_LIST])
        self.table_combobox.current(DEFAULT_TABLE_INDEX)
        self.table_combobox.bind('<<ComboboxSelected>>', self._on_table_combobox_selected)

        self.sheet = Sheet(self.table_frame,
                           headers=self.HEADERS,
                           font=self.FONT_UI,
                           header_font=self.FONT_UI,
                           index_font=self.FONT_UI,
                           outline_thickness=1,
                           outline_color='gray')
        self.sheet.enable_bindings()
        self.sheet.extra_bindings([('all_select_events', self._sheet_select_event)])
        self.sheet.readonly_columns(list(range(len(self.HEADERS))))
        self.sheet.readonly_header(list(range(len(self.HEADERS))))
        self.sheet.hide_columns(columns=[4])

        self.check_only_notfound = tkwidgets.CheckBox(parent=self.table_frame,
                                            text='未所持のみ表示',
                                            command=self._on_check_only_notfound)

        self.info_frame = tk.Frame(self, bd=1, relief=tk.SOLID)

        self.label_title = tkwidgets.ClickableLabel(parent=self.info_frame, font=self.FONT_UI_TITLE)

        self.label_url = tkwidgets.ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.label_urldiff = tkwidgets.ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.label_urlpack = tkwidgets.ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.search_frame = tk.Frame(self)
        self.search_frame.grid_columnconfigure(0, weight=1)
        self.search_frame.grid_rowconfigure(1, weight=1)

        self.textbox_search = tkwidgets.TextBox(parent=self.search_frame, font=self.FONT_UI)
        self.textbox_search.get().bind('<Return>', self._search_songs)

        self.treeview = ttk.Treeview(master=self.search_frame, columns=('diff'), height=5)
        self.treeview.column('#0', width=150)
        self.treeview.column('diff', width=80)
        self.treeview.heading('#0', text='Path/Title')
        self.treeview.heading('diff', text='差分')
        self.treeview.bind('<3>', self._on_treeview_rclick)

        # レイアウト

        # フレーム
        self.table_frame.grid(row=0, column=0, sticky='ew', padx=4, pady=2)
        self.info_frame.grid(row=1, column=0, sticky='ew', padx=4, pady=2)
        self.search_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=4, pady=2)

        # フレーム内 (1)
        self.table_combobox.grid(row=0, column=0, sticky='ew', padx=4, pady=2)
        self.sheet.grid(row=1, column=0, sticky='ew', padx=4, pady=2)
        self.check_only_notfound.get().grid(row=2, column=0, sticky='w')

        # フレーム内 (2)
        self.label_title.get().grid(row=1, column=0, sticky='w', padx=4, pady=2)
        self.label_url.get().grid(row=2, column=0, sticky='w', padx=4, pady=2)
        self.label_urldiff.get().grid(row=3, column=0, sticky='w', padx=4, pady=2)
        self.label_urlpack.get().grid(row=4, column=0, sticky='w', padx=4, pady=2)

        # フレーム内 (3)
        self.textbox_search.get().grid(row=0, column=0, sticky='ew', padx=4, pady=2, ipadx=2, ipady=2)
        self.treeview.grid(row=1, column=0, sticky=tk.NSEW, padx=4, pady=2)

        # ttkウィジェットのスタイル（フォント）指定
        style = ttk.Style()
        style.configure("Treeview.Heading", font=self.FONT_UI)
        style.configure("Treeview", font=self.FONT_UI)
        style.configure("TCheckbutton", font=self.FONT_UI)

    def set_songdata(self, df_songdata):
        self.df_songdata = df_songdata

    def set_table(self, table):
        self.table = table
        self.df_table_view = self.table.get_table().drop_duplicates(subset='index')

        # シートに曲リストを表示
        self._update_sheet(show_only_notfound=True)

    def _on_table_combobox_selected(self, event):
        index = self.table_combobox.current()
        self.table.load(index)
        self.df_table_view = self.table.get_table().drop_duplicates(subset='index')
        self._update_sheet(show_only_notfound=self.check_only_notfound.get_value())

    def _update_sheet(self, show_only_notfound=False):
        self._clear_sheet()

        df = self.df_table_view
        for level, title, artist, found, index in zip(df['level'], df['title'], df['artist'], df['found'], df['index']):
            self.sheet.insert_row(values=(f'{self.table.get_header()["symbol"]}{level}', title, artist, found, index), idx='end')

        not_found_rows = [index for found, index in zip(df['found'], df['index']) if not found]
        self.sheet.highlight_rows(not_found_rows, fg='blue')

        if show_only_notfound:
            self.sheet.display_rows(not_found_rows, all_rows_displayed=False)

        self.sheet.select_row(0)
        self.sheet.see(row=0)

    def _clear_sheet(self):
        self.sheet.display_rows(None, all_rows_displayed=True)
        self.sheet.set_sheet_data([])
        self.sheet.column_width(column=0, width=50)
        self.sheet.column_width(column=1, width=400)

    def _on_check_only_notfound(self):
        self._update_sheet(show_only_notfound=self.check_only_notfound.get_value())

    def _sheet_select_event(self, event=None):
        if event[0] == 'select_cell':
            # セルがクリックされた → 行全体を選択する
            row_idx = event[1]
            self.sheet.select_row(row_idx)

        elif event[0] == 'select_row':
            # 行が選択された
            row_idx = event[1]
            # 表示されている行の番号から元データの行番号を得る（非表示の行がある場合を考慮）
            disp_row_idx = self.sheet.displayed_row_to_data(row_idx)

            # 曲データを取得
            row = self.df_table_view.iloc[disp_row_idx].replace(np.nan, '')
            title = row['title']
            md5 = row['md5']
            ir_url = f'http://www.dream-pro.info/~lavalse/LR2IR/search.cgi?mode=ranking&bmsmd5={md5}' if md5 else ''
            url = row['url'] if row['url'] else ''
            url_diff = row['url_diff'] if row['url_diff'] else ''
            name_diff = f'- {row["name_diff"]}' if 'name_diff' in row.keys() and row['name_diff'] else ''

            if 'url_pack' in self.df_table_view.columns:
                url_pack = row['url_pack'] if 'url_pack' in row.keys() else ''
                name_pack = f'- {row["name_pack"]}' if 'name_pack' in row.keys() and row['name_pack'] else ''
            else:
                url_pack, name_pack = '', ''

            # 曲データをUIに反映
            self.label_title.set_text(title)
            self.label_title.set_click_event(ir_url)

            self.label_url.set_text(url)
            self.label_url.set_click_event(url)

            self.label_urldiff.set_text(f'{url_diff} {name_diff}')
            self.label_urldiff.set_click_event(url_diff)

            if url_pack:
                self.label_urlpack.set_text(f'{url_pack} {name_pack}')
                self.label_urlpack.set_click_event(url_pack)
            else:
                self.label_urlpack.set_text('')

            self.textbox_search.set_text(re.sub(r'\s*\[.[^\[]+\]$', '', title))

    def _search_songs(self, event):
        # テキストボックスの内容で曲を検索
        search_word = self.textbox_search.get_text()
        df_result = self.df_songdata[self.df_songdata['title'].str.contains(search_word, case=False, regex=False)]
        
        # 検索結果：譜面格納フォルダのパスと、含まれる差分の一覧
        dirlist = {}
        for title, path in zip(df_result['title'], df_result['path']):
            path_dir = os.path.dirname(path)
            path_base = os.path.basename(path)
            diff_data = { 'title':title, 'diff':path_base }

            if path_dir in dirlist.keys():
                dirlist[path_dir].append(diff_data)
            else:
                dirlist[path_dir] = [diff_data]
        
        # ツリービューに譜面格納フォルダのパス・差分一覧を表示
        self.treeview.delete(*self.treeview.get_children())
        for path, diff_list in dirlist.items():
            iid = self.treeview.insert(parent='', index='end', text=path, open=True)
            for diff in diff_list:
                self.treeview.insert(parent=iid, index='end', text=diff['title'], values=[diff['diff']])

    def _on_treeview_rclick(self, event):
        iid = self.treeview.identify_row(y=event.y)
        if self.treeview.parent(iid) != '':
            iid = self.treeview.parent(iid)

        dir_path = self.treeview.item(iid)['text']
        if os.path.isdir(dir_path):
            subprocess.Popen(['explorer', dir_path], shell=True)


def main():
    # songdata.db のパスを読み込み
    config = json.load(open('config.json', 'r'))

    # songdata.db 読み込み
    df_songdata = songdata.read_songdata(config['SONGDATA_DB_PATH'])

    # 難易度表読み込み
    # キャッシュがなければダウンロードする
    table = bmstable.BmsTable(TABLE_LIST, df_songdata)
    table.load(DEFAULT_TABLE_INDEX)

    # GUI表示
    main_window = MainWindow()
    main_window.set_songdata(df_songdata)
    main_window.set_table(table)
    main_window.mainloop()


if __name__ == '__main__':
    main()
