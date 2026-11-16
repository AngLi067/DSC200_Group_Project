import unittest

import numpy as np
from scipy.sparse import csr_matrix

from prepare_data import asof_indices
from recommendation_models import evaluate, filter_known_unavailable, popularity_ranking


class AvailabilityTests(unittest.TestCase):
    def test_asof_join_uses_only_state_at_or_before_query_time(self):
        multiplier = 1_000
        property_items = np.array([10, 10, 20], dtype=np.int32)
        property_timestamps = np.array([100, 300, 200], dtype=np.int64)
        property_keys = property_items.astype(np.int64) * multiplier + property_timestamps
        property_keys.sort()

        result = asof_indices(
            property_keys,
            property_items,
            np.array([10, 10, 20, 30], dtype=np.int32),
            np.array([99, 200, 250, 250], dtype=np.int64),
            multiplier,
        )

        np.testing.assert_array_equal(result, [-1, 0, 2, -1])

    def test_filter_excludes_known_unavailable_and_keeps_unknown(self):
        availability = np.array([0, 1, -1, 1], dtype=np.int8)
        candidates = np.array([[0, 2]], dtype=np.int32)
        popular = np.array([0, 1, 2, 3], dtype=np.int32)

        result = filter_known_unavailable(candidates, availability, popular, 3)

        np.testing.assert_array_equal(result, [[2, 1, 3]])

    def test_metrics_report_unavailable_and_unknown_exposure(self):
        targets = csr_matrix(([1.0, 1.0], ([0, 0], [1, 3])), shape=(1, 4))
        recommendations = np.array([[0, 2]], dtype=np.int32)
        availability = np.array([0, 1, -1, 0], dtype=np.int8)

        result = evaluate(recommendations, np.array([0]), targets, availability, 2)

        self.assertEqual(result["recall@2"], 0.0)
        self.assertEqual(result["unavailable_recommendation_rate"], 0.5)
        self.assertEqual(result["unknown_availability_recommendation_rate"], 0.5)

    def test_filter_deduplicates_and_pads_when_eligible_catalog_is_small(self):
        result = filter_known_unavailable(
            np.array([[1, 1, 2, -1]]), np.array([0, 1, -1]), np.array([0, 1, 2]), 4
        )
        np.testing.assert_array_equal(result, [[1, 2, -1, -1]])

    def test_all_unavailable_items_leave_empty_slots(self):
        result = filter_known_unavailable(
            np.array([[0, 1]]), np.array([0, 0]), np.array([0, 1]), 2
        )
        np.testing.assert_array_equal(result, [[-1, -1]])

    def test_metrics_use_original_rank_and_known_relevance(self):
        targets = csr_matrix(([1.0, 1.0], ([0, 0], [1, 3])), shape=(1, 4))
        result = evaluate(np.array([[1, 0, 3]]), np.array([0]), targets, np.ones(4), 3)
        self.assertEqual(result["recall@3"], 1.0)
        self.assertAlmostEqual(result["ndcg@3"], 1.5 / (1 + 1 / np.log2(3)))
        padded = evaluate(np.array([[-1, 1]]), np.array([0]), targets, np.ones(4), 2)
        self.assertEqual(padded["recall@2"], 0.5)
        self.assertAlmostEqual(padded["ndcg@2"], (1 / np.log2(3)) / (1 + 1 / np.log2(3)))
        self.assertEqual(padded["recommendation_slots_filled"], 1)

    def test_popularity_excludes_future_only_items_and_breaks_ties_by_id(self):
        train = csr_matrix([[2.0, 2.0, 0.0, 4.0]])
        np.testing.assert_array_equal(popularity_ranking(train), [3, 0, 1])


if __name__ == "__main__":
    unittest.main()
