"""
Fifteen Hands: strategy simulation.

Tests whether the intended equilibrium holds: an honest player who polices
should narrowly beat a defector, while a passive honest player should lose.

Usage:
    python3 simulate.py                 # default tournament
    python3 simulate.py --sweep entered # sweep the Entered payout
    python3 simulate.py --sweep discredits
"""

import random
import argparse
from collections import defaultdict
from itertools import product

# ---------------------------------------------------------------- parameters

PARAMS = dict(
    players=5,
    confidence_start=36,
    discredit_limit=3,
    true_payout=2,
    entered_payout=6,
    challenge_reward=3,
    margin_value=10,
    margin_band=2,          # total <= this awards a Margin token
    compact_bonus=1,
    compact_minimum=3,
    tariff=1,
    max_rounds=12,   # fixed game length; survive it to score
)

# Confidence tiers: (floor, true_payout, entered_payout)
TIERS = [
    (31, 2, 5),
    (21, 2, 4),
    (11, 1, 3),
    (1,  1, 2),
]


def tier_payouts(confidence, p):
    for floor, tp, ep in TIERS:
        if confidence >= floor:
            # scale by configured payouts (keeps sweeps meaningful)
            scale_t = p["true_payout"] / 2.0
            scale_e = p["entered_payout"] / 5.0
            return tp * scale_t, ep * scale_e
    return 0.0, 0.0


# ---------------------------------------------------------------- strategies

class Strategy:
    """Base. Subclasses decide whether to cheat and whether to challenge."""
    name = "base"

    def cheat(self, view):
        raise NotImplementedError

    def challenge(self, view):
        """Return True if this player wants to claim the round's challenge."""
        return False


class AlwaysCheat(Strategy):
    name = "always-cheat"

    def cheat(self, view):
        return True


class AlwaysHonest(Strategy):
    """Honest but passive: never challenges. Should lose."""
    name = "honest-passive"

    def cheat(self, view):
        return False


class HonestPolice(Strategy):
    """Honest and polices. The intended winner."""
    name = "honest-police"

    def cheat(self, view):
        return False

    def challenge(self, view):
        # Challenge when the posterior clears the break-even point.
        return view["last_total"] is not None and view["last_total"] >= 4


class Opportunist(Strategy):
    """Cheats only when the Register looks healthy; polices when honest."""
    name = "opportunist"

    def cheat(self, view):
        return view["confidence"] > 25

    def challenge(self, view):
        return view["last_total"] is not None and view["last_total"] >= 4


class TitForTat(Strategy):
    """Honest while the last round was clean; cheats after a bad one."""
    name = "tit-for-tat"

    def cheat(self, view):
        if view["last_total"] is None:
            return False
        return view["last_total"] >= 4

    def challenge(self, view):
        return view["last_total"] is not None and view["last_total"] >= 4


STRATEGIES = [AlwaysCheat, AlwaysHonest, HonestPolice, Opportunist, TitForTat]


# ---------------------------------------------------------------- game engine

class Player:
    def __init__(self, strategy, pid):
        self.s = strategy()
        self.pid = pid
        self.influence = 0.0
        self.discredits = 0
        self.out = False
        self.in_compact = False
        self.played_true = False


def play_game(strategy_classes, p, rng):
    players = [Player(sc, i) for i, sc in enumerate(strategy_classes)]
    confidence = p["confidence_start"]
    last_total = None

    # Compact: honest-leaning strategies join at setup.
    joiners = [pl for pl in players
               if pl.s.name in ("honest-passive", "honest-police", "tit-for-tat")]
    compact_live = len(joiners) >= p["compact_minimum"]
    for pl in joiners:
        pl.in_compact = compact_live

    for _ in range(p["max_rounds"]):
        alive = [pl for pl in players if not pl.out]
        if confidence <= 0 or len(alive) <= 1:
            break

        tp, ep = tier_payouts(confidence, p)
        view = {"confidence": confidence, "last_total": last_total}

        # --- 1. simultaneous claims
        cheats = 0
        for pl in alive:
            pl.played_true = not pl.s.cheat(view)
            if pl.played_true:
                bonus = p["compact_bonus"] if pl.in_compact and compact_live else 0
                pl.influence += tp + bonus
            else:
                pl.influence += ep
                cheats += 1

        # --- 2. City noise, then reveal total only
        city = rng.choice([0, 1, 2])
        total = cheats + city
        view_after = {"confidence": confidence, "last_total": total}

        # --- 3. one challenge, table-wide, honest players only
        order = list(alive)
        rng.shuffle(order)
        for challenger in order:
            if not challenger.played_true:
                continue
            if not challenger.s.challenge(view_after):
                continue
            targets = [t for t in alive if t is not challenger]
            if not targets:
                break
            target = rng.choice(targets)
            if not target.played_true:                 # caught
                challenger.influence += p["challenge_reward"]
                target.influence -= ep
                target.discredits += 1
                if target.discredits >= p["discredit_limit"]:
                    target.out = True
            else:                                       # wrong
                challenger.discredits += 1
                if challenger.discredits >= p["discredit_limit"]:
                    challenger.out = True
            break

        # --- 4. margin token
        if total <= p["margin_band"]:
            honest = [pl for pl in alive if pl.played_true and not pl.out]
            if honest:
                rng.choice(honest).influence += p["margin_value"]

        # --- 5. erosion
        confidence -= total
        last_total = total

        # compact may collapse
        if compact_live:
            remaining = [pl for pl in joiners if not pl.out]
            if len(remaining) < p["compact_minimum"]:
                compact_live = False

    collapsed = confidence <= 0
    return players, collapsed


def tournament(p, games=4000, seed=7):
    """Every strategy plays every game; rotate seats to remove positional bias."""
    rng = random.Random(seed)
    scores = defaultdict(list)
    wins = defaultdict(int)
    collapses = 0
    eliminated = defaultdict(int)

    for _ in range(games):
        line = list(STRATEGIES)
        rng.shuffle(line)
        players, collapsed = play_game(line, p, rng)
        for pl in players:
            scores[pl.s.name].append(pl.influence)
            if pl.out:
                eliminated[pl.s.name] += 1
        if collapsed:
            collapses += 1
            continue                      # everyone loses; no winner recorded
        live = [pl for pl in players if not pl.out]
        if live:
            best = max(live, key=lambda x: x.influence)
            wins[best.s.name] += 1

    return scores, wins, collapses, eliminated, games


def report(p, games=4000):
    scores, wins, collapses, elim, n = tournament(p, games)
    survived = n - collapses
    print(f"  games {n} | register collapsed {collapses} "
          f"({100*collapses/n:.0f}%) | resolved {survived}")
    print(f"  {'strategy':<16} {'mean infl':>10} {'wins':>7} {'win %':>7} {'elim %':>7}")
    rows = []
    for s in STRATEGIES:
        nm = s.name
        m = sum(scores[nm]) / len(scores[nm]) if scores[nm] else 0.0
        w = wins[nm]
        wp = 100 * w / survived if survived else 0
        ep = 100 * elim[nm] / n
        rows.append((m, nm, w, wp, ep))
    for m, nm, w, wp, ep in sorted(rows, reverse=True):
        print(f"  {nm:<16} {m:>10.1f} {w:>7} {wp:>6.1f}% {ep:>6.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", choices=["entered", "discredits", "margin", "confidence"])
    ap.add_argument("--games", type=int, default=4000)
    a = ap.parse_args()

    if not a.sweep:
        print("\n=== baseline (Entered 5, Discredit limit 3, Margin 10) ===")
        report(dict(PARAMS), a.games)
        return

    if a.sweep == "entered":
        for v in [3, 4, 5, 6, 7]:
            p = dict(PARAMS); p["entered_payout"] = v
            print(f"\n=== Entered payout = {v} ===")
            report(p, a.games)
    elif a.sweep == "discredits":
        for v in [2, 3, 4, 5]:
            p = dict(PARAMS); p["discredit_limit"] = v
            print(f"\n=== Discredit limit = {v} ===")
            report(p, a.games)
    elif a.sweep == "confidence":
        for v in [24, 28, 32, 36, 40]:
            p = dict(PARAMS); p["confidence_start"] = v
            print(f"\n=== Confidence start = {v} ===")
            report(p, a.games)
    elif a.sweep == "margin":
        for v in [0, 5, 10, 15, 20]:
            p = dict(PARAMS); p["margin_value"] = v
            print(f"\n=== Margin token = {v} ===")
            report(p, a.games)


if __name__ == "__main__":
    main()
