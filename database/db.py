# ==========================
# Battle Bot v2 - Phase4
# SQLite 接続・初期化
# ==========================

import sqlite3
import os

DB_PATH = "database/tournament.db"


def get_connection():
    """SQLite 接続を返す"""
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """テーブル作成（初回のみ）"""

    conn = get_connection()
    cur = conn.cursor()

    # 大会テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            round INTEGER,
            started INTEGER
        )
    """)

    # プレイヤーテーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER,
            tournament_id INTEGER,
            name TEXT,
            match_points INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            bye INTEGER,
            omw REAL,
            ogw REAL,
            opponents TEXT,
            PRIMARY KEY (id, tournament_id)
        )
    """)

    # 試合テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            round INTEGER,
            table_num INTEGER,
            player1_id INTEGER,
            player2_id INTEGER,
            winner_id INTEGER,
            finished INTEGER
        )
    """)

    conn.commit()
    conn.close()
