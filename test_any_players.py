"""Test the partnership algorithm with different player counts.
Uses a backtracking solver to find valid templates, then verifies them."""
import random
from itertools import combinations

def analyze_constraints(num_players, num_rounds=9):
    """Print and return mathematical analysis of what's possible."""
    total_partnerships = num_players * (num_players - 1) // 2
    partnerships_needed = num_rounds * 2
    num_sitting = num_players - 4

    unique_ok = partnerships_needed <= total_partnerships
    # No-consec requires sitter sets in adjacent rounds to be disjoint:
    # 2 * num_sitting <= num_players
    no_consec_ok = (2 * num_sitting <= num_players)

    print(f"  {num_players} players | {num_sitting} sit/round")
    print(f"  Unique partnerships : need {partnerships_needed}, have {total_partnerships} → {'✓' if unique_ok else '✗ IMPOSSIBLE'}")
    print(f"  No consec. sit-outs : {'✓ possible' if no_consec_ok else '✗ IMPOSSIBLE (2×'+str(num_sitting)+'>'+str(num_players)+')'}")
    return unique_ok, no_consec_ok


def solve_template(num_players, num_rounds=9, max_attempts=2000):
    """Backtracking solver: find a schedule with unique partnerships.
    Tries to avoid consecutive sit-outs; if unavoidable, minimises them.
    Returns list of {teams, sitting} dicts or None."""
    num_sitting = num_players - 4
    players = list(range(num_players))

    def find_pairs(playing, used_ps):
        """Find 2 non-overlapping unique pairs from playing list."""
        valid = [(a, b) for a, b in combinations(playing, 2)
                 if tuple(sorted([a, b])) not in used_ps]
        def bt(pairs, selected, used):
            if len(selected) == 2:
                return selected
            for i, p in enumerate(pairs):
                if p[0] not in used and p[1] not in used:
                    r = bt(pairs[i+1:], selected + [p], used | set(p))
                    if r:
                        return r
            return None
        random.shuffle(valid)
        return bt(valid, [], set())

    def backtrack(round_idx, last_sitting, used_ps, schedule):
        if round_idx == num_rounds:
            return True

        must_play = set(last_sitting)          # sat last round → must play
        can_sit   = [p for p in players if p not in must_play]

        # Build candidate sit-combos: prefer those that avoid consecutive,
        # but always add combos with consecutive as fallback.
        sit_combos_no_consec = []
        sit_combos_with_consec = []
        all_players = list(range(num_players))

        if len(can_sit) >= num_sitting:
            sit_combos_no_consec = list(combinations(can_sit, num_sitting))
            random.shuffle(sit_combos_no_consec)

        # Also generate combos that include some from last_sitting (consecutive allowed)
        for extra_count in range(1, len(must_play) + 1):
            for extra in combinations(sorted(must_play), extra_count):
                remaining_can_sit = [p for p in can_sit if True]  # all can_sit
                needed = num_sitting - extra_count
                if needed < 0:
                    continue
                for rest in combinations(remaining_can_sit, needed):
                    sit_combos_with_consec.append(tuple(extra) + rest)

        sit_combos = sit_combos_no_consec + sit_combos_with_consec

        for sit_combo in sit_combos:
            sitting = set(sit_combo)
            playing = [p for p in players if p not in sitting]
            if len(playing) < 4:
                continue
            teams = find_pairs(playing[:4], used_ps)
            if not teams:
                continue
            # Commit
            new_ps = used_ps | {tuple(sorted(t)) for t in teams}
            schedule.append({'teams': [list(teams[0]), list(teams[1])],
                             'sitting': sorted(sitting)})
            if backtrack(round_idx + 1, sitting, new_ps, schedule):
                return True
            schedule.pop()

        return False

    for attempt in range(max_attempts):
        random.seed(attempt)
        schedule = []
        if backtrack(0, set(), set(), schedule):
            return schedule
    return None

def verify_template(template, num_players, label=""):
    """Verify a template for unique partnerships and consecutive sit-out violations."""
    used = set()
    duplicates = []
    consec_violations = []
    last_sitting = set()

    for i, rnd in enumerate(template):
        t = rnd['teams']
        sitting = set(rnd['sitting'])
        p1 = tuple(sorted(t[0]))
        p2 = tuple(sorted(t[1]))
        for pair in [p1, p2]:
            if pair in used:
                duplicates.append((i+1, pair))
            used.add(pair)
        overlap = sitting & last_sitting
        for p in overlap:
            consec_violations.append((p, i, i+1))  # 0-indexed rounds
        last_sitting = sitting

    print(f"\n  {'Template' if not label else label}: {num_players} players")
    if duplicates:
        print(f"  ❌ {len(duplicates)} repeat partnership(s): {duplicates[:3]}")
    else:
        print(f"  ✅ All {len(used)} partnerships unique")
    if consec_violations:
        print(f"  ⚠️  {len(consec_violations)} consecutive sit-out(s): {consec_violations[:3]}")
    else:
        print(f"  ✅ No consecutive sit-outs")
    return len(duplicates) == 0, len(consec_violations) == 0


def test_player_count(num_players, num_rounds=9):
    print(f"\n{'='*60}")
    print(f"  {num_players} PLAYERS  ({num_rounds} rounds)")
    print(f"{'='*60}")
    unique_ok, no_consec_ok = analyze_constraints(num_players, num_rounds)

    if num_players < 4:
        print("  ⚠️  Skipping – need at least 4 players")
        return None
    if not unique_ok:
        print("  ⚠️  Skipping – unique partnerships mathematically impossible")
        return None

    print(f"\n  Solving...")
    template = solve_template(num_players, num_rounds)
    if template is None:
        print(f"  ❌ Solver could not find a valid template")
        return False

    print(f"  Found template in solver.")
    # Print the schedule
    for i, rnd in enumerate(template):
        t = rnd['teams']
        s = rnd['sitting']
        print(f"  R{i+1}: ({t[0][0]+1},{t[0][1]+1}) vs ({t[1][0]+1},{t[1][1]+1}) | sit: {[x+1 for x in s]}")

    unique_pass, no_consec_pass = verify_template(template, num_players)

    if not no_consec_ok:
        print(f"  ℹ️  Note: no-consecutive is mathematically impossible for {num_players} players")

    # Print template as Python code for copy-pasting into the main app
    print(f"\n  # ---- Python template (0-indexed) for {num_players} players ----")
    print(f"  self.templates[{num_players}] = [")
    for rnd in template:
        print(f"      {{'teams': {rnd['teams']}, 'sitting': {rnd['sitting']}}},")
    print(f"  ]")

    return unique_pass


# ── Main ──────────────────────────────────────────────────────────────────────
print("SOLVING PARTNERSHIP TEMPLATES FOR VARIOUS PLAYER COUNTS")
print("="*60)

results = {}
for n in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
    results[n] = test_player_count(n)

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for n, r in results.items():
    if r is None:
        print(f"  {n} players: ⚠️  impossible (not enough partnerships)")
    elif r:
        print(f"  {n} players: ✅ PASS")
    else:
        print(f"  {n} players: ❌ FAIL")
