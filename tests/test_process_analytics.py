
import unittest
import pandas as pd

from src.waiting_time_analysis import calculate_waiting_time_metrics


class TestProcessAnalytics(unittest.TestCase):

    def setUp(self):
        self.events = pd.DataFrame({
            "event_id": ["E1", "E2", "E3", "E4", "E5"],
            "case_id": ["C1", "C1", "C1", "C2", "C2"],
            "activity": [
                "Registration", "Triage", "Consultation",
                "Registration", "Triage"
            ],
            "timestamp": [
                "2026-01-01 09:00:00",
                "2026-01-01 09:10:00",
                "2026-01-01 09:40:00",
                "2026-01-01 10:00:00",
                "2026-01-01 10:05:00"
            ]
        })

    def test_elapsed_times_are_calculated_correctly(self):
        intervals, _, _ = calculate_waiting_time_metrics(self.events)

        self.assertEqual(
            intervals["elapsed_minutes"].tolist(),
            [10.0, 30.0, 5.0]
        )

    def test_cases_are_not_mixed(self):
        intervals, _, _ = calculate_waiting_time_metrics(self.events)

        self.assertEqual(len(intervals), 3)
        self.assertEqual(
            intervals["previous_activity"].tolist(),
            ["Registration", "Triage", "Registration"]
        )

    def test_transition_summary_counts(self):
        _, summary, _ = calculate_waiting_time_metrics(self.events)

        self.assertEqual(summary["transition_count"].sum(), 3)
        self.assertEqual(len(summary), 2)

    def test_invalid_timestamps_are_excluded(self):
        events = self.events.copy()
        events.loc[1, "timestamp"] = "invalid timestamp"

        intervals, _, _ = calculate_waiting_time_metrics(events)

        self.assertTrue(intervals["elapsed_minutes"].notna().all())
        self.assertEqual(len(intervals), 2)

    def test_missing_required_column_raises_error(self):
        events = self.events.drop(columns=["activity"])

        with self.assertRaisesRegex(ValueError, "activity"):
            calculate_waiting_time_metrics(events)

    def test_single_event_case_has_no_transition(self):
        events = pd.DataFrame({
            "case_id": ["C1"],
            "activity": ["Registration"],
            "timestamp": ["2026-01-01 09:00:00"],
        })

        intervals, summary, _ = calculate_waiting_time_metrics(events)

        self.assertEqual(len(intervals), 0)
        self.assertEqual(len(summary), 0)

    def test_transition_summary_statistics(self):
        events = pd.DataFrame({
            "case_id": ["C1", "C1", "C1"],
            "activity": ["Registration", "Triage", "Triage"],
            "timestamp": [
                "2026-01-01 09:00:00",
                "2026-01-01 09:10:00",
                "2026-01-01 09:30:00",
            ],
        })

        _, summary, _ = calculate_waiting_time_metrics(events)

        transition = summary[
            (summary["previous_activity"] == "Triage")
            & (summary["activity"] == "Triage")
        ].iloc[0]

        self.assertEqual(transition["transition_count"], 1)
        self.assertEqual(transition["median_elapsed_minutes"], 20)
        self.assertEqual(transition["max_elapsed_minutes"], 20)


if __name__ == "__main__":
    unittest.main()
