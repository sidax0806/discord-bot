# ==========================
# Battle Bot v2 - 最終版
# 大会データ管理（OGW% + 永続化 + 復元）
# ==========================

from database.tournament_repo import (
    save_tournament,
    load_latest_tournament,
    load_tournament_by_id as repo_load_by_id
)
from database.player_repo import save_players, load_players
from database.match_repo import save_matches, load_matches

current_tournament = None


# ==========================
# 大会リセット
# ==========================
def reset():
    global current_tournament
    current_tournament = None


# ==========================
# プレイヤー生成（OGW%対応）
# ==========================
def create_player(user):
    return {
        "id": user.id,
        "name": user.display_name,

        # マッチ結果
        "match_points": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,

        # ゲーム結果（OGW%用）
        "game_wins": 0,
        "game_losses": 0,

        # BYE
        "bye": False,

        # 対戦履歴
        "opponents": [],

        # スイスドロー用
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
# OMW% 更新
# ==========================
def update_omw(t):
    for player in t["participants"]:
        opponents = player["opponents"]

        if len(opponents) == 0:
            player["omw"] = 0.0
            continue

        total = 0

        for oid in opponents:
            opp = get_player(oid)
            if opp is None:
                continue

            games = opp["wins"] + opp["losses"] + opp["draws"]
            win_rate = opp["wins"] / games if games > 0 else 0

            total += win_rate

        player["omw"] = round(total / len(opponents), 3)


# ==========================
# OGW% 更新
# ==========================
def update_ogw(t):
    for player in t["participants"]:
        opponents = player["opponents"]

        if len(opponents) == 0:
            player["ogw"] = 0.0
            continue

        total = 0

        for oid in opponents:
            opp = get_player(oid)
            if opp is None:
                continue

            games = opp["game_wins"] + opp["game_losses"]
            gw_rate = opp["game_wins"] / games if games > 0 else 0

            total += gw_rate

        player["ogw"] = round(total / len(opponents), 3)


# ==========================
# 順位ソート（match → OMW → OGW）
# ==========================
def sort_players():
    if current_tournament is None:
        return []

    return sorted(
        current_tournament["participants"],
        key=lambda p: (
            p["match_points"],
            p["omw"],
            p["ogw"]
        ),
        reverse=True
    )


# ==========================
# 大会保存（大会 + プレイヤー + 試合）
# ==========================
def save_all():
    if current_tournament is None:
        return

    tournament_id = save_tournament(current_tournament)
    save_players(tournament_id, current_tournament["participants"])
    save_matches(
        tournament_id,
        current_tournament["round"],
        current_tournament["matches"]
    )


# ==========================
# 最新大会の復元
# ==========================
def load_tournament():
    global current_tournament

    t = load_latest_tournament()
    if t is None:
        current_tournament = None
        return None

    tournament_id = t["id"]

    players = load_players(tournament_id)
    t["participants"] = players

    matches_raw = load_matches(tournament_id, t["round"])
    matches = []

    for m in matches_raw:
        p1 = next(p for p in players if p["id"] == m["player1_id"])
        p2 = next(p for p in players if p["id"] == m["player2_id"])

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


# ==========================
# 大会ID指定で復元
# ==========================
def load_tournament_by_id(tournament_id):
    global current_tournament

    t = repo_load_by_id(tournament_id)
    if t is None:
        return None

    players = load_players(tournament_id)
    t["participants"] = players

    matches_raw = load_matches(tournament_id, t["round"])
    matches = []

    for m in matches_raw:
        p1 = next(p for p in players if p["id"] == m["player1_id"])
        p2 = next(p for p in players if p["id"] == m["player2_id"])

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
