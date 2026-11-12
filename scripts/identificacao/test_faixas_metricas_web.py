"""Confere a otimização com enumeração independente de todas as partições."""
from itertools import combinations
import unittest

import numpy as np

from preparar_faixas_metricas_web import weighted_breaks


def loss(values, weights, edges):
    groups = np.searchsorted(edges, values, side='left')
    total = 0
    for group in np.unique(groups):
        selected = groups == group
        mean = np.average(values[selected], weights=weights[selected])
        total += np.sum(weights[selected]*(values[selected]-mean)**2)
    return total


class BreaksTest(unittest.TestCase):
    def test_global_optimum(self):
        rng = np.random.default_rng(77)
        for _ in range(12):
            values = rng.integers(1, 80, 9).astype(float)
            weights = rng.integers(1, 100, 9).astype(float)
            unique = np.unique(values)
            for k in [2, 3, 4]:
                expected = min(loss(values, weights, edges) for edges in combinations(unique[:-1], k-1))
                actual = loss(values, weights, weighted_breaks(values, weights, k))
                self.assertAlmostEqual(actual, expected, places=7)

    def test_duplicates_and_constant(self):
        self.assertEqual(weighted_breaks([2, 2, 2], [1, 10, 100]), [])
        self.assertEqual(weighted_breaks([1, 1, 4, 4, 9], [1, 2, 3, 4, 5]), [1, 4])

    def test_invariance(self):
        values = np.array([1, 2, 8, 10, 25, 30, 80, 100.])
        weights = np.array([5, 2, 3, 7, 4, 2, 6, 1.])
        expected = np.array(weighted_breaks(values, weights))
        np.testing.assert_allclose(weighted_breaks(values*100+17, weights*3), expected*100+17)
        self.assertEqual(weighted_breaks(values[::-1], weights[::-1]), expected.tolist())

    def test_invalid_input(self):
        for values, weights in [([], []), ([1], [0]), ([1, np.nan], [1, 2]), ([1, 2], [1]), ([1], [np.inf])]:
            with self.assertRaises(ValueError):
                weighted_breaks(values, weights)


if __name__ == '__main__':
    unittest.main()
