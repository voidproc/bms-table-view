# bms-table-view

![screenshot](image/screenshot.png)

未所持の BMS 譜面を導入するための個人用ツール

- 難易度表を読み込んで表示する
- 所持していない曲をリストアップする
- 所持している曲の中からタイトルで検索し、フォルダをエクスプローラで開く

## 動作環境

- Windows 11
- Python 3.11.1

## 使い方

### モジュールのインストール

```
pip install requests numpy pandas tksheet==6.3.5
```

### 設定ファイルを配置

`config.json` に `songdata.db` のパスを書く（`config.example.json` をコピーして編集してください）。

例：
```json
{
    "SONGDATA_DB_PATH": "E:/beatoraja/player/player1/songdata.db"
}
```

### 起動

```
python ./main.py
```
