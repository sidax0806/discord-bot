# ==========================
# Battle Bot v2 - 最終仕上げ
# 大会データ 永続化（拡張）
# ==========================

from database.db import get_connection


def save_tournament(t):
    """大会データを保存（新規 or 更新）"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM tournaments WHERE name = ?", (t["name"],))
    row = cur.fetchone()

    if row:
        cur.execute("""
            UPDATE tournaments
            SET round = ?, started = ?
            WHERE id = ?
        """, (t["round"], int(t["started"]), row[0]))
        tournament_id = row[0]
    else:
        cur.execute("""
            INSERT INTO tournaments (name, round, started)
            VALUES (?, ?, ?)
        """, (t["name"], t["round"], int(t["started"])))
        tournament_id = cur.lastrowid

    conn.commit()
    conn.close()
    return tournament_id


def load_latest_tournament():
    """最新の大会を読み込む"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, round, started
        FROM tournaments
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "round": row[2],
        "started": bool(row[3]),
        "participants": [],
        "matches": []
    }


def load_tournament_by_id(tournament_id):
    """大会IDを指定して読み込む"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, round, started
        FROM tournaments
        WHERE id = ?
    """, (tournament_id,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "round": row[2],
        "started": bool(row[3]),
        "participants": [],
        "matches": []
    }


def list_tournaments():
    """大会一覧を取得"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, round, started
        FROM tournaments
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "round": r[2],
            "started": bool(r[3])
        }
        for r in rows
    ]


def delete_tournament(tournament_id):
    """大会削除"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
    cur.execute("DELETE FROM players WHERE tournament_id = ?", (tournament_id,))
    cur.execute("DELETE FROM matches WHERE tournament_id = ?", (tournament_id,))

    conn.commit()
    conn.close()
