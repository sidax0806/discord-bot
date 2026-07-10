# ==========================
# Battle Bot v2 - Phase3
# スイスドロー ペアリングロジック
# ==========================

import random
import data.tournament_data as tournament_data


def swiss_pairing(t):
    players = t["participants"]

    sorted_players = sorted(
        players,
        key=lambda p: (p["match_points"], p["omw"], random.random()),
        reverse=True
    )

    bye_player = None

    if len(sorted_players) % 2 == 1:
        candidates = [p for p in sorted_players if not p["bye"]]

        if len(candidates) == 0:
            bye_player = sorted_players[-1]
        else:
            bye_player = sorted(candidates, key=lambda p: p["match_points"])[0]

        bye_player["bye"] = True

        # ★ BYE は加点なし
        bye_player["match_points"] += 0

        # ★ 対戦履歴を全員に追加（総当たり判定のため）
        for p in sorted_players:
            if p["id"] != bye_player["id"]:
                bye_player["opponents"].append(p["id"])

        sorted_players.remove(bye_player)

    matches = []
    used = set()

    for i, p in enumerate(sorted_players):
        if p["id"] in used:
            continue

        opponent = None

        for q in sorted_players[i + 1:]:
            if q["id"] in used:
                continue
            if q["id"] not in p["opponents"]:
                opponent = q
                break

        if opponent is None:
            for q in sorted_players[i + 1:]:
                if q["id"] not in used:
                    opponent = q
                    break

        if opponent is None:
            continue

        used.add(p["id"])
        used.add(opponent["id"])

        matches.append({
            "player1": p,
            "player2": opponent
        })

    return matches, bye_player

