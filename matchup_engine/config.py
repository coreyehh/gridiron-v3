from dataclasses import dataclass

@dataclass(frozen=True)
class MatchupConfig:
    min_prior_games: int = 4
    rolling_games: int = 8
    random_state: int = 42
