# ==========================
# Battle Bot v2 - Phase4
# 大会データ管理（復元対応）
# ==========================

import data.tournament_data as tournament_data
from database.tournament_repo import load_latest_tournament, save_tournament
from database.player_repo import load_players, save_players
from database.match_repo import load_matches, save_matches


current_tournament = None


def reset():
    global current_tournament
    current_tournament = None


# ==========================
# プレイヤー生成（v2仕様）
# ==========================
def create_player(user):
    return {
        "id": user.id,
        "name": user.display_name,
        "match_points": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "bye": False,
        "opponents": [],
        "omw": 0.0,
        "ogw": 0.0
    }


# ==========================
# プレイヤー取得
# ==========================
def get_player(player_id):
    if current_tournament is None:
        return None

    for p in current_tournament["participants"]:
        if p["id"] == player_id:
            return p

    return None


# ==========================
# 試合取得
# ==========================
def get_match(table):
    if current_tournament is None:
        return None

    for m in current_tournament["matches"]:
        if m["table"] == table:
            return m

    return None


# ==========================
# 全試合終了判定
# ==========================
def all_matches_finished():
    if current_tournament is None:
        return False

    for m in current_tournament["matches"]:
        if not m["finished"]:
            return False

    return True


# ==========================
# 順位ソート
# ==========================
def sort_players():
    if current_tournament is None:
        return []

    return sorted(
        current_tournament["participants"],
        key=lambda p: (p["match_points"], p["omw"]),
        reverse=True
    )


# ==========================
# 大会保存（大会 + プレイヤー + 試合）
# ==========================
def save_all():
    if current_tournament is None:
        return

    # 大会保存
    tournament_id = save_tournament(current_tournament)

    # プレイヤー保存
    save_players(tournament_id, current_tournament["participants"])

    # 試合保存
    save_matches(
        tournament_id,
        current_tournament["round"],
        current_tournament["matches"]
    )


# ==========================
# 大会復元
# ==========================
def load_tournament():
    global current_tournament

    t = load_latest_tournament()
    if t is None:
        current_tournament = None
        return None

    tournament_id = t["id"]

    # プレイヤー復元
    players = load_players(tournament_id)
    t["participants"] = players

    # 試合復元
    matches_raw = load_matches(tournament_id, t["round"])
    matches = []

    for m in matches_raw:
        p1 = get_player(m["player1_id"])
        p2 = get_player(m["player2_id"])

        matches.append({
            "table": m["table"],
            "player1": p1,
            "player2": p2,
            "winner": m["winner"],
            "finished": m["finished"]
        })

    t["matches"] = matches

    current_tournament = t
    return t
