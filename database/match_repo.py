# ==========================
# Battle Bot v2 - Phase4
# 試合データ 永続化
# ==========================

from database.db import get_connection


def save_matches(tournament_id, round_num, matches):
    """試合一覧を保存"""

    conn = get_connection()
    cur = conn.cursor()

    for m in matches:
        cur.execute("""
            INSERT OR REPLACE INTO matches (
                id, tournament_id, round, table_num,
                player1_id, player2_id, winner_id, finished
            )
            VALUES (
                COALESCE(
                    (SELECT id FROM matches
                     WHERE tournament_id = ? AND round = ? AND table_num = ?),
                    NULL
                ),
                ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            tournament_id, round_num, m["table"],
            tournament_id, round_num, m["table"],
            m["player1"]["id"], m["player2"]["id"],
            m["winner"], int(m["finished"])
        ))

    conn.commit()
    conn.close()


def load_matches(tournament_id, round_num):
    """大会IDとラウンドから試合一覧を読み込む"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT table_num, player1_id, player2_id, winner_id, finished
        FROM matches
        WHERE tournament_id = ? AND round = ?
        ORDER BY table_num ASC
    """, (tournament_id, round_num))

    rows = cur.fetchall()
    conn.close()

    matches = []

    for r in rows:
        matches.append({
            "table": r[0],
            "player1_id": r[1],
            "player2_id": r[2],
            "winner": r[3],
            "finished": bool(r[4])
        })

    return matches
