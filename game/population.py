"""
Population stress test for Fifteen Hands.

The tournament assumes a fixed, fairly honest line-up. This asks the more
important question: if k of the 5 players defect, what happens to the
Register, and does defection still pay?

A well-designed commons game should be self-correcting: defection profitable
when rare, self-destroying when common.
"""

import random
from simulate import (PARAMS, play_game, AlwaysCheat, HonestPolice)


def run(n_cheaters, games=3000, confidence=36, entered=6, seed=11):
    p = dict(PARAMS)
    p["confidence_start"] = confidence
    p["entered_payout"] = entered
    rng = random.Random(seed)

    line = [AlwaysCheat] * n_cheaters + [HonestPolice] * (5 - n_cheaters)
    collapses = 0
    cheat_scores, honest_scores = [], []
    cheat_wins = honest_wins = 0

    for _ in range(games):
        players, collapsed = play_game(line, p, rng)
        if collapsed:
            collapses += 1
            continue
        live = [x for x in players if not x.out]
        for pl in players:
            (cheat_scores if pl.s.name == "always-cheat" else honest_scores
             ).append(pl.influence)
        if live:
            best = max(live, key=lambda x: x.influence)
            if best.s.name == "always-cheat":
                cheat_wins += 1
            else:
                honest_wins += 1

    resolved = games - collapses
    cm = sum(cheat_scores) / len(cheat_scores) if cheat_scores else 0
    hm = sum(honest_scores) / len(honest_scores) if honest_scores else 0
    return dict(k=n_cheaters, collapse_pct=100 * collapses / games,
                cheat_mean=cm, honest_mean=hm,
                cheat_win_pct=100 * cheat_wins / resolved if resolved else 0,
                resolved=resolved)


if __name__ == "__main__":
    for conf in (32, 36, 40):
        print(f"\n=== Confidence start {conf}, Entered 6 ===")
        print(f"  {'cheaters':>8} {'collapse':>9} {'cheat avg':>10} "
              f"{'honest avg':>11} {'cheat wins':>11}")
        for k in range(6):
            r = run(k, confidence=conf)
            cw = f"{r['cheat_win_pct']:.0f}%" if k else "n/a"
            print(f"  {k:>8} {r['collapse_pct']:>8.0f}% "
                  f"{r['cheat_mean']:>10.1f} {r['honest_mean']:>11.1f} {cw:>11}")
