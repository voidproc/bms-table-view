import sqlite3
import pandas as pd

def read_songdata(songdata_db_path):
    connection = sqlite3.connect(songdata_db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    df = pd.read_sql_query(sql='SELECT md5,sha256,title,artist,path FROM song', con=connection)
    cursor.close()
    connection.close()
    return df
