# ==========================
# Battle Bot v2 - Phase4
# プレイヤーデータ 永続化
# ==========================

import json
from database.db import get_connection


def save_players(tournament_id, players):
    """プレイヤー一覧を保存"""

    conn = get_connection()
    cur = conn.cursor()

    for p in players:
        opponents_json = json.dumps(p["opponents"])

        cur.execute("""
            INSERT OR REPLACE INTO players (
                id, tournament_id, name,
                match_points, wins, draws, losses,
                bye, omw, ogw, opponents
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], tournament_id, p["name"],
            p["match_points"], p["wins"], p["draws"], p["losses"],
            int(p["bye"]), p["omw"], p["ogw"], opponents_json
        ))

    conn.commit()
    conn.close()


def load_players(tournament_id):
    """大会IDからプレイヤー一覧を読み込む"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, match_points, wins, draws, losses,
               bye, omw, ogw, opponents
        FROM players
        WHERE tournament_id = ?
    """, (tournament_id,))

    rows = cur.fetchall()
    conn.close()

    players = []

    for r in rows:
        players.append({
            "id": r[0],
            "name": r[1],
            "match_points": r[2],
            "wins": r[3],
            "draws": r[4],
            "losses": r[5],
            "bye": bool(r[6]),
            "omw": r[7],
            "ogw": r[8],
            "opponents": json.loads(r[9])
        })

    return players
