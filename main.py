import sqlite3
import requests
import json
import pandas as pd
import numpy as np
from tksheet import Sheet
import tkinter as tk
import tkinter.ttk as ttk
import webbrowser
import os
from hashlib import md5
from urllib.parse import urljoin
from html.parser import HTMLParser
import re


# ローカルの songdata.db パス
SONGDATA_DB_PATH = 'db/songdata.db'

# 難易度表URL
TABLE_LIST = [
    { 'name': 'NEW GENERATION 通常難易度表', 'url': 'https://rattoto10.jounin.jp/table.html' },
    { 'name': 'NEW GENERATION 発狂難易度表', 'url': 'https://rattoto10.jounin.jp/table_insane.html' },
    { 'name': 'Satellite', 'url': 'https://stellabms.xyz/sl/table.html' },
    { 'name': 'LN難易度表', 'url': 'http://flowermaster.web.fc2.com/lrnanido/gla/LN.html' },
]

DEFAULT_TABLE_INDEX = 0


class HtmlBmsTableParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'meta': return

        name = ''
        for key, value in attrs:
            if key.lower() == 'name': name = value.lower()
        
        if name != 'bmstable': return

        self.table_header_url = ''
        for key, value in attrs:
            if key.lower() == 'content': self.table_header_url = value

    def get_table_header_json_url(self):
        return self.table_header_url


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


class MainWindow(tk.Tk):
    FONT_UI = ('MS UI Gothic', 9, 'normal')
    FONT_UI_UNDERLINE = ('MS UI Gothic', 9, 'underline')
    FONT_UI_TITLE = ('MS UI Gothic', 12, 'bold', 'underline')
    HEADERS = ['level', 'title', 'artist', 'found', 'index']

    def __init__(self):
        tk.Tk.__init__(self)

        self.title('bm_sabun_collect_helper')
        self.geometry('800x600')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.sheet = Sheet(self,
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

        self.info_frame = tk.Frame(self)

        self.check_only_notfound = CheckBox(parent=self.info_frame,
                                            text='未所持のみ表示',
                                            command=self._on_check_only_notfound)

        self.label_title = ClickableLabel(parent=self.info_frame, font=self.FONT_UI_TITLE)

        self.label_url = ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.label_urldiff = ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.label_urlpack = ClickableLabel(parent=self.info_frame, font=self.FONT_UI)

        self.search_frame = tk.Frame(self)
        self.search_frame.grid_columnconfigure(0, weight=1)
        self.search_frame.grid_rowconfigure(1, weight=1)

        self.textbox_search = TextBox(parent=self.search_frame, font=self.FONT_UI)
        self.textbox_search.get().bind('<Return>', self._search_songs)

        self.treeview = ttk.Treeview(master=self.search_frame, columns=('diff'), height=5)
        self.treeview.column('#0', width=150)
        self.treeview.column('diff', width=80)
        self.treeview.heading('#0', text='Path/Title')
        self.treeview.heading('diff', text='差分')
        self.treeview.bind('<3>', self._on_treeview_rclick)

        self.sheet.grid(row=0, column=0, sticky='nsew', padx=4, pady=2)
        self.info_frame.grid(row=1, column=0, sticky='ew', padx=4, pady=2)
        self.search_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=4, pady=2)

        self.check_only_notfound.get().grid(row=0, column=0, sticky='w')
        self.label_title.get().grid(row=1, column=0, sticky='w', padx=4, pady=2)
        self.label_url.get().grid(row=2, column=0, sticky='w', padx=4, pady=2)
        self.label_urldiff.get().grid(row=3, column=0, sticky='w', padx=4, pady=2)
        self.label_urlpack.get().grid(row=4, column=0, sticky='w', padx=4, pady=2)

        self.textbox_search.get().grid(row=0, column=0, sticky='ew', padx=4, pady=2, ipadx=2, ipady=2)
        self.treeview.grid(row=1, column=0, sticky=tk.NSEW, padx=4, pady=2)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=self.FONT_UI)
        style.configure("Treeview", font=self.FONT_UI)
        style.configure("TCheckbutton", font=self.FONT_UI)

    def set_song_db(self, df_song_db):
        self.df_song_db = df_song_db

    def set_table(self, table_header, df_table):
        self.table_header = table_header
        self.df_table = df_table
        self.df_table_view = df_table.drop_duplicates(subset='index')

        # シートに曲リストを表示
        self._update_sheet(show_only_notfound=True)

    def _update_sheet(self, show_only_notfound=False):
        self._clear_sheet()

        df = self.df_table_view
        for level, title, artist, found, index in zip(df['level'], df['title'], df['artist'], df['found'], df['index']):
            self.sheet.insert_row(values=(f'{self.table_header["symbol"]}{level}', title, artist, found, index), idx='end')

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
        df_result = self.df_song_db[self.df_song_db['title'].str.contains(search_word, case=False, regex=False)]
        
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

        print(self.treeview.item(iid)['text'])

def read_songdata_db(songdata_db_path):
    connection = sqlite3.connect(songdata_db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    df = pd.read_sql_query(sql='SELECT md5,sha256,title,artist,path FROM song', con=connection)
    cursor.close()
    connection.close()
    return df


def get_html_text(html_url):
    res = requests.get(html_url)
    return res.text


def get_json(json_url):
    res = requests.get(json_url)
    text = res.text
    data = json.loads(text)
    return data


def get_table_header_json_url(table_index):
    table_html_text = get_html_text(TABLE_LIST[table_index]['url'])
    html_parser = HtmlBmsTableParser()
    html_parser.feed(table_html_text)
    table_header_url = html_parser.get_table_header_json_url()
    return urljoin(TABLE_LIST[table_index]['url'], table_header_url)


def files_exist_all(files):
    return all(map(os.path.isfile, files))


def table_cache_hash(table_index):
    return md5(TABLE_LIST[table_index]['url'].encode()).hexdigest()


def table_cache_exists(table_index):
    table_url_hash = table_cache_hash(table_index)

    cache_files = [
        f'cache/{table_url_hash}/table_header.json',
        f'cache/{table_url_hash}/df_table.pkl',
    ]

    return files_exist_all(cache_files)


def save_table_cache(table_index, table_header, df_table):
    table_url_hash = table_cache_hash(table_index)

    if not os.path.isdir('cache'):
        os.mkdir('cache')
    if not os.path.isdir(f'cache/{table_url_hash}'):
        os.mkdir(f'cache/{table_url_hash}')

    with open(f'cache/{table_url_hash}/table_header.json', 'wt') as f:
        json.dump(table_header, f)
    
    df_table.to_pickle(f'cache/{table_url_hash}/df_table.pkl')


def load_table_cache(table_index):
    table_url_hash = table_cache_hash(table_index)

    with open(f'cache/{table_url_hash}/table_header.json') as f:
        table_header = json.load(f)

    df_table = pd.read_pickle(f'cache/{table_url_hash}/df_table.pkl')

    return table_header, df_table


def download_table(table_index, df_song_db):
    # 難易度表ヘッダを取得
    print('難易度表ヘッダを取得')
    table_header_json_url = get_table_header_json_url(table_index)
    table_header = get_json(table_header_json_url)

    # 難易度表を取得
    print('難易度表を取得')
    table_data_url = urljoin(table_header_json_url, table_header['data_url'])
    table_data = get_json(table_data_url)
    df_table_orig = pd.DataFrame(table_data)
    df_table_orig['md5'].replace('', np.nan, inplace=True)
    if not 'sha256' in df_table_orig.columns:
        df_table_orig['sha256'] = ''
    df_table_orig.reset_index(inplace=True)
    df_table_orig.to_csv('_debug_csv/df_table_orig.csv')

    # 難易度表とsong.dbから、所持している譜面を取得(1)
    # md5による
    print('マージ(md5)')
    df_merged_md5 = pd.merge(df_table_orig, df_song_db, on='md5', how='left', suffixes=(None, '_r'))
    try:
        df_merged_md5.drop(columns=['sha256_r'], inplace=True)
    except:
        print('sha256 property not found.')

    # 難易度表とsong.dbから、所持している譜面を取得(2)
    # sha256による
    print('マージ(sha256)')
    df_merged_sha256 = pd.merge(df_table_orig, df_song_db, on='sha256', how='inner', suffixes=(None, '_r'))

    # (1),(2)の結果をマージ
    # これにより df_table の内容は次のようになる：
    # - ベースは難易度表のデータ
    # - 所持していれば path に保存先が格納されている
    # - 重複所持していると、曲が同じで path が異なる行が複数となる
    # - 難易度表の行番号が index に格納されている。リスト表示で曲の重複をしたくない場合は index の重複を削除する
    print('マージ')
    df_table = pd.merge(df_merged_md5, df_merged_sha256[['sha256', 'path']], on='sha256', how='left', suffixes=(None, '_r2'))
    df_table['path'].fillna('', inplace=True)
    df_table['path_r2'].fillna('', inplace=True)
    df_table['path'] = df_table['path'] + df_table['path_r2']
    df_table['found'] = df_table['path'] != ''
    df_table.to_csv('_debug_csv/df_table.csv')

    return table_header, df_table


def load_table(table_index, df_song_db):
    """難易度表を読み込む。ローカルにキャッシュがなければダウンロードする
    """
    if not table_cache_exists(table_index):
        print('キャッシュが存在しないので難易度表をダウンロード')
        table_header, df_table = download_table(table_index, df_song_db)
        save_table_cache(table_index, table_header, df_table)
    else:
        print('キャッシュから難易度表を読み込み')
        table_header, df_table = load_table_cache(table_index)

    return table_header, df_table


def main():
    # song.db 読み込み
    df_song_db = read_songdata_db(SONGDATA_DB_PATH)

    # 難易度表読み込み
    # キャッシュがなければダウンロードする
    table_header, df_table = load_table(DEFAULT_TABLE_INDEX, df_song_db)

    # GUI表示
    main_window = MainWindow()
    main_window.set_song_db(df_song_db)
    main_window.set_table(table_header, df_table)
    main_window.mainloop()


if __name__ == '__main__':
    main()
