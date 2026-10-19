from __future__ import annotations

import itertools
import math
import random

from study_a_plus import (
    aurc_direct,
    aurc_weighted,
    one_label_influence,
    paired_influence,
)


def test_bruteforce_direct_equals_weighted() -> None:
    for n in range(1, 9):
        for errors in itertools.product((0, 1), repeat=n):
            assert math.isclose(
                aurc_direct(errors), aurc_weighted(errors), rel_tol=0, abs_tol=3e-16
            )


def test_bruteforce_one_label_influence() -> None:
    for n in range(1, 9):
        for errors in itertools.product((0, 1), repeat=n):
            baseline = aurc_direct(errors)
            for rank in range(1, n + 1):
                changed = list(errors)
                changed[rank - 1] = 1 - changed[rank - 1]
                delta_error = changed[rank - 1] - errors[rank - 1]
                observed = aurc_direct(changed) - baseline
                expected = one_label_influence(n, rank, delta_error)
                assert math.isclose(observed, expected, rel_tol=0, abs_tol=3e-16)


def test_bruteforce_paired_influence() -> None:
    for n in range(1, 7):
        identity = tuple(range(n))
        for permutation in itertools.permutations(range(n)):
            for errors in itertools.product((0, 1), repeat=n):
                baseline = aurc_direct(errors[i] for i in permutation) - aurc_direct(
                    errors[i] for i in identity
                )
                for claim in range(n):
                    changed = list(errors)
                    changed[claim] = 1 - changed[claim]
                    observed = (
                        aurc_direct(changed[i] for i in permutation)
                        - aurc_direct(changed[i] for i in identity)
                        - baseline
                    )
                    delta_error = changed[claim] - errors[claim]
                    expected = paired_influence(
                        n, identity.index(claim) + 1, permutation.index(claim) + 1, delta_error
                    )
                    assert math.isclose(observed, expected, rel_tol=0, abs_tol=4e-16)


def test_randomized_properties() -> None:
    rng = random.Random(20261019)
    for _ in range(10_000):
        n = rng.randint(1, 200)
        errors = [rng.randrange(2) for _ in range(n)]
        b1_order = list(range(n))
        ears_order = list(range(n))
        rng.shuffle(b1_order)
        rng.shuffle(ears_order)
        assert math.isclose(
            aurc_direct(errors[i] for i in b1_order),
            aurc_weighted(errors[i] for i in b1_order),
            rel_tol=0,
            abs_tol=5e-16,
        )
        claim = rng.randrange(n)
        changed = list(errors)
        changed[claim] = 1 - changed[claim]
        delta_error = changed[claim] - errors[claim]
        before = aurc_direct(errors[i] for i in ears_order) - aurc_direct(
            errors[i] for i in b1_order
        )
        after = aurc_direct(changed[i] for i in ears_order) - aurc_direct(
            changed[i] for i in b1_order
        )
        expected = paired_influence(
            n, b1_order.index(claim) + 1, ears_order.index(claim) + 1, delta_error
        )
        assert math.isclose(after - before, expected, rel_tol=0, abs_tol=7e-16)
