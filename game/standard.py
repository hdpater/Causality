"""
Does the Standard do any work?

Tests the club-with-a-door proposal: members may call one extra assay each
round against another member, over and above the single table-wide assay.

The question is whether staying outside is the dominant play. If it is, the
club never forms. If it is dominated, everyone joins and the mechanic is
inert. We want it close, and sensitive to how many others have joined.
"""

import random
from simulate import PARAMS, Player

TURN_TRUST = 20
CATCH_COST = 6
ASSAY_REWARD = 3
STANDARD_REWARD = 4
MIN_MEMBERS = 3


class Base:
    member = False
    def cheat(self, v): raise NotImplementedError
    def challenge(self, v): return v["last_total"] is not None and v["last_total"] >= 4


class LoyalMember(Base):
    """Signs and keeps to it."""
    name = "member-honest"; member = True
    def cheat(self, v): return False


class CheatingMember(Base):
    """Signs for the cover, clips anyway."""
    name = "member-clips"; member = True
    def cheat(self, v): return True


class OutsideHonest(Base):
    """Stays out, strikes sound anyway."""
    name = "outsider-honest"
    def cheat(self, v): return False


class FreeRider(Base):
    """Stays out and clips: the strategy the club must not reward."""
    name = "outsider-clips"
    def cheat(self, v): return True


def play(line, trust0, rng, club_assay=True):
    ps = [Player(sc, i) for i, sc in enumerate(line)]
    for p in ps:
        p.member = p.s.member
    trust = trust0; last = None

    for _ in range(12):
        alive = [x for x in ps if not x.out]
        if trust <= 0 or len(alive) <= 1: break
        members = [x for x in alive if x.member]
        club_live = len(members) >= MIN_MEMBERS

        v = {"confidence": trust, "last_total": last}; ch = 0
        for pl in alive:
            pl.played_true = not pl.s.cheat(v)
            pl.influence += 0 if pl.played_true else 1
            if not pl.played_true: ch += 1

        total = ch + sum(1 for _ in alive if rng.random() < 0.20)
        va = {"confidence": trust, "last_total": total}

        def do_assay(challenger, pool):
            if not pool: return
            marked = [x for x in pool if x.discredits > 0]
            t = rng.choice(marked) if marked else rng.choice(pool)
            if not t.played_true:
                challenger.influence += ASSAY_REWARD
                t.influence -= CATCH_COST
                t.discredits += 1
                if t.member:
                    t.warnings = getattr(t, "warnings", 0) + 1
                    if t.warnings >= 2: t.member = False      # expelled
                if t.discredits >= 3: t.out = True
            else:
                challenger.discredits += 1
                if challenger.discredits >= 3: challenger.out = True

        # the ordinary table-wide assay (open season after the Turn)
        limit = 1 if trust >= TURN_TRUST else 99
        order = [x for x in alive if x.played_true]; rng.shuffle(order); done = 0
        for c in order:
            if done >= limit or c.out: break
            if not c.s.challenge(va): continue
            do_assay(c, [x for x in alive if x is not c and not x.out])
            done += 1

        # the club's own scales: members police members
        if club_assay and club_live:
            mem = [x for x in alive if x.member and x.played_true and not x.out]
            rng.shuffle(mem)
            for c in mem[:1]:
                if not c.s.challenge(va): continue
                do_assay(c, [x for x in alive if x.member and x is not c and not x.out])

        trust -= total; last = total

    # settle
    members_left = [x for x in ps if x.member and not x.out]
    club_ok = len(members_left) >= MIN_MEMBERS
    for p in ps:
        if p.out: p.influence = 0
        elif p.member and club_ok: p.influence += STANDARD_REWARD
    return ps, trust <= 0


def run(line, trust0=34, games=4000, club_assay=True, seed=11):
    rng = random.Random(seed)
    col = 0; scores = {}
    for _ in range(games):
        pl, c = play([type(x) for x in line], trust0, rng, club_assay)
        if c: col += 1; continue
        for p in pl: scores.setdefault(p.s.name, []).append(p.influence)
    return 100*col/games, {k: sum(v)/len(v) for k, v in scores.items()}


def show(title, line, **kw):
    c, m = run(line, **kw)
    print(f"\n{title}   collapse {c:.0f}%")
    for k in sorted(m, key=lambda x: -m[x]):
        print(f"    {k:<18} {m[k]:6.2f}")


if __name__ == "__main__":
    L, C, O, F = LoyalMember(), CheatingMember(), OutsideHonest(), FreeRider()

    print("=== 5 Houses, Trust 34, club has its own scales ===")
    show("4 loyal members + 1 free rider outside", [L, L, L, L, F])
    show("3 loyal members + 1 clipping member + 1 free rider", [L, L, L, C, F])
    show("3 loyal members + 2 free riders", [L, L, L, F, F])
    show("2 loyal + 3 outside (club below minimum)", [L, L, O, F, F])

    print("\n=== same, but WITHOUT the club's extra assay ===")
    show("4 loyal members + 1 free rider outside", [L, L, L, L, F], club_assay=False)
    show("3 loyal members + 1 clipping member + 1 free rider", [L, L, L, C, F], club_assay=False)
