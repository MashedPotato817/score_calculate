from dataclasses import dataclass, field


@dataclass
class SmallRound:
    seq: int
    landlord: str
    fanshu: int
    winner: str  # "地主" or "农民"
    score_changes: dict[str, int]
    scores_after: dict[str, int]


@dataclass
class BigGame:
    name: str
    players: list[str]
    status: str  # "进行中" or "已结束"
    rounds: list[SmallRound]
    created_at: str
    scores: list[int] = field(default_factory=lambda: [0, 0, 0])
