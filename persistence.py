import json
import os
from models import BigGame, SmallRound

DATA_FILE = "games.json"


def _to_dict(games: list[BigGame]) -> list[dict]:
    return [
        {
            "name": g.name,
            "players": g.players,
            "status": g.status,
            "created_at": g.created_at,
            "scores": g.scores,
            "rounds": [
                {
                    "seq": r.seq,
                    "landlord": r.landlord,
                    "fanshu": r.fanshu,
                    "winner": r.winner,
                    "score_changes": r.score_changes,
                    "scores_after": r.scores_after,
                }
                for r in g.rounds
            ],
        }
        for g in games
    ]


def _from_dict(data: list[dict]) -> list[BigGame]:
    return [
        BigGame(
            name=d["name"],
            players=d["players"],
            status=d["status"],
            created_at=d["created_at"],
            rounds=[SmallRound(**r) for r in d.get("rounds", [])],
            scores=d.get("scores", [0, 0, 0]),
        )
        for d in data
    ]


def save_games(games: list[BigGame]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_to_dict(games), f, ensure_ascii=False, indent=2)


def load_games() -> list[BigGame]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _from_dict(data)


def get_active_game(games: list[BigGame]) -> BigGame | None:
    for g in games:
        if g.status == "进行中":
            return g
    return None


def finish_all_active(games: list[BigGame]) -> None:
    for g in games:
        if g.status == "进行中":
            g.status = "已结束"


def finish_game(games: list[BigGame], name: str) -> None:
    for g in games:
        if g.name == name:
            g.status = "已结束"
            break
    save_games(games)


def resume_game(games: list[BigGame], name: str) -> None:
    finish_all_active(games)
    for g in games:
        if g.name == name:
            g.status = "进行中"
            break
    save_games(games)


def delete_game(games: list[BigGame], name: str) -> None:
    games[:] = [g for g in games if g.name != name]
    save_games(games)
