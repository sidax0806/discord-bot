# ==========================
# Battle Bot v2 - Phase3
# スイスドロー ペアリングロジック
# ==========================

import random
import data.tournament_data as tournament_data


def swiss_pairing(t):
    """
    スイスドローのペアリングを生成する
    - 勝点 → OMW% → ランダム の順で並べる
    - 再戦防止
    - BYE 最適化
    """

    players = t["participants"]

    # ==========================
    # ソート（勝点 → OMW% → ランダム）
    # ==========================
    sorted_players = sorted(
        players,
        key=lambda p: (p["match_points"], p["omw"], random.random()),
        reverse=True
    )

    # ==========================
    # BYE 対象者の決定
    # ==========================
    bye_player = None

    if len(sorted_players) % 2 == 1:
        # BYE をまだ受けていない人の中で勝点が最も低い人
        candidates = [
            p for p in sorted_players
            if not p["bye"]
        ]

        if len(candidates) == 0:
            # 全員がBYE済みなら最後の人
            bye_player = sorted_players[-1]
        else:
            bye_player = sorted(
                candidates,
                key=lambda p: p["match_points"]
            )[0]

        bye_player["bye"] = True
        bye_player["match_points"] += 3

        # BYE をリストから除外
        sorted_players.remove(bye_player)

    # ==========================
    # 再戦防止ペアリング
    # ==========================
    matches = []
    used = set()

    for i, p in enumerate(sorted_players):
        if p["id"] in used:
            continue

        # 対戦相手を探す
        opponent = None

        for q in sorted_players[i + 1:]:
            if q["id"] in used:
                continue

            # 再戦防止
            if q["id"] not in p["opponents"]:
                opponent = q
                break

        # 見つからない場合 → 仕方なく次の人
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
