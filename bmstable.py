import os
import json
import numpy as np
import pandas as pd
import requests
from html.parser import HTMLParser
from urllib.parse import urljoin
from hashlib import md5


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


def _files_exist_all(files):
    return all(map(os.path.isfile, files))


def _get_html_text(html_url):
    res = requests.get(html_url)
    return res.text


def _get_json(json_url):
    res = requests.get(json_url)
    text = res.text
    data = json.loads(text)
    return data


class BmsTable():
    CACHE_ROOT_DIR = 'cache/'
    CACHE_FILE_LIST = [
        'table_header.json',
        'df_table.pkl'
    ]

    def __init__(self, table_list, df_songdata):
        self.table_list = table_list
        self.df_songdata = df_songdata
        self.current_table_index = None

    def get_header(self):
        return self.table_header
    
    def get_table(self):
        return self.df_table
    
    def current_index(self):
        return self.current_table_index

    def load(self, table_index):
        if not self._table_cache_exists(table_index):
            print('キャッシュが存在しないので難易度表をダウンロード')
            self._download_table(table_index)
            self._save_table_cache(table_index)
        else:
            print('キャッシュから難易度表を読み込み')
            self._load_table_cache(table_index)

        self.current_table_index = table_index

    def _table_cache_exists(self, table_index):
        cache_dir = self._cache_dir_path(table_index)
        cache_files = [f'{cache_dir}{cache_file}' for cache_file in self.CACHE_FILE_LIST]
        return _files_exist_all(cache_files)

    def _cache_dir_path(self, table_index=None):
        cache_root = self.CACHE_ROOT_DIR

        if table_index == None:
            return cache_root

        table_url_hash = self._table_cache_hash(table_index)
        return f'{cache_root}{table_url_hash}/'

    def _table_cache_hash(self, table_index):
        return md5(self.table_list[table_index]['url'].encode()).hexdigest()

    def _download_table(self, table_index):
        # 難易度表ヘッダを取得
        print('難易度表ヘッダを取得')
        table_header_json_url = self._get_table_header_json_url(table_index)
        table_header = _get_json(table_header_json_url)

        # 難易度表を取得
        print('難易度表を取得')
        table_data_url = urljoin(table_header_json_url, table_header['data_url'])
        table_data = _get_json(table_data_url)
        df_table_orig = pd.DataFrame(table_data)
        df_table_orig['md5'] = df_table_orig['md5'].replace('', np.nan)
        if not 'sha256' in df_table_orig.columns:
            df_table_orig['sha256'] = ''
        df_table_orig.reset_index(inplace=True)
        df_table_orig.to_csv('_debug_csv/df_table_orig.csv')

        # 難易度表とsong.dbから、所持している譜面を取得(1)
        # md5による
        print('マージ(md5)')
        df_merged_md5 = pd.merge(df_table_orig, self.df_songdata, on='md5', how='left', suffixes=(None, '_r'))
        try:
            df_merged_md5.drop(columns=['sha256_r'], inplace=True)
        except:
            print('sha256 property not found.')

        # 難易度表とsong.dbから、所持している譜面を取得(2)
        # sha256による
        print('マージ(sha256)')
        df_merged_sha256 = pd.merge(df_table_orig, self.df_songdata, on='sha256', how='inner', suffixes=(None, '_r'))

        # (1),(2)の結果をマージ
        # これにより df_table の内容は次のようになる：
        # - ベースは難易度表のデータ
        # - 所持していれば path に保存先が格納されている
        # - 重複所持していると、曲が同じで path が異なる行が複数となる
        # - 難易度表の行番号が index に格納されている。リスト表示で曲の重複をしたくない場合は index の重複を削除する
        print('マージ')
        df_table = pd.merge(df_merged_md5, df_merged_sha256[['sha256', 'path']], on='sha256', how='left', suffixes=(None, '_r2'))
        df_table['path'] = df_table['path'].fillna('')
        df_table['path_r2'] = df_table['path_r2'].fillna('')
        df_table['path'] = df_table['path'] + df_table['path_r2']
        df_table['found'] = df_table['path'] != ''
        df_table.to_csv('_debug_csv/df_table.csv')

        self.table_header = table_header
        self.df_table = df_table

    def _get_table_header_json_url(self, table_index):
        table_html_text = _get_html_text(self.table_list[table_index]['url'])
        html_parser = HtmlBmsTableParser()
        html_parser.feed(table_html_text)
        table_header_url = html_parser.get_table_header_json_url()
        return urljoin(self.table_list[table_index]['url'], table_header_url)

    def _save_table_cache(self, table_index):
        cache_root_dir = self._cache_dir_path()
        if not os.path.isdir(cache_root_dir):
            os.mkdir(cache_root_dir)

        cache_dir = self._cache_dir_path(table_index)
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)

        with open(f'{cache_dir}table_header.json', 'wt') as f:
            json.dump(self.table_header, f)
        
        self.df_table.to_pickle(f'{cache_dir}df_table.pkl')

    def _load_table_cache(self, table_index):
        cache_dir = self._cache_dir_path(table_index)

        with open(f'{cache_dir}table_header.json') as f:
            table_header = json.load(f)

        df_table = pd.read_pickle(f'{cache_dir}df_table.pkl')

        self.table_header = table_header
        self.df_table = df_table
