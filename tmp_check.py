import asyncio
import data.tournament_data as tournament_data
import cogs.tournament as tmod

class FakeUser:
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name

    async def send(self, message):
        print(f"DM to {self.name}: {message}")

class FakeClient:
    def __init__(self, users):
        self.users = users

    async def fetch_user(self, user_id):
        return self.users[user_id]

class FakeFollowup:
    async def send(self, *args, **kwargs):
        print("followup sent")
        return None

class FakeInteraction:
    def __init__(self, client):
        self.client = client
        self.followup = FakeFollowup()

    async def response(self):
        return None

async def main():
    tournament_data.current_tournament = {
        'name': 'テスト大会',
        'participants': [
            {'id': 1, 'name': 'Alice', 'match_points': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'game_wins': 0, 'game_losses': 0, 'bye': False, 'opponents': [], 'omw': 0.0, 'ogw': 0.0},
            {'id': 2, 'name': 'Bob', 'match_points': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'game_wins': 0, 'game_losses': 0, 'bye': False, 'opponents': [], 'omw': 0.0, 'ogw': 0.0},
        ],
        'started': False,
        'round': 0,
        'matches': [],
        'bo': 'BO1',
        'creator_id': 99,
    }
    users = {
        1: FakeUser(1, 'Alice'),
        2: FakeUser(2, 'Bob'),
    }
    interaction = FakeInteraction(FakeClient(users))

    async def fake_disable(interaction):
        return None

    async def fake_ranking(interaction):
        return None

    tmod.disable_buttons = fake_disable
    tmod.send_ranking_summary = fake_ranking

    await tmod.start_tournament_internal(interaction)

asyncio.run(main())
