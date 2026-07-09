import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.modules.setdefault("pyodbc", types.SimpleNamespace(Connection=object, connect=MagicMock()))

import db


class GeneratedEventNumberTests(unittest.TestCase):
    def test_should_generate_for_blank_peace_order(self):
        self.assertTrue(
            db.should_generate_event_number(
                {"Event Number": "  ", "Activity Type": "Peace Order Service"}
            )
        )

    def test_should_generate_for_blank_protective_order_type(self):
        self.assertTrue(
            db.should_generate_event_number(
                {"Event Number": None, "Type": "Protective Order"}
            )
        )

    def test_should_not_generate_when_esri_event_number_exists(self):
        self.assertFalse(
            db.should_generate_event_number(
                {"Event Number": "E123", "Activity Type": "Peace Order"}
            )
        )

    def test_should_not_generate_for_other_activity(self):
        self.assertFalse(
            db.should_generate_event_number(
                {"Event Number": "", "Activity Type": "Civil Paper"}
            )
        )

    def test_prefix_uses_eastern_month_from_epoch_ms(self):
        arrival_ms = int(datetime(2026, 7, 1, 3, 30).timestamp() * 1000)
        self.assertEqual(db.generated_event_number_prefix(arrival_ms), "26-06")

    def test_allocate_generated_event_number_formats_sequence(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (7,)
        self.assertEqual(db.allocate_generated_event_number(cursor, "2026-07-09T12:00:00Z"), "26-07-00007")

    def test_allocate_generated_event_number_rejects_exhausted_sequence(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (100000,)
        with self.assertRaises(RuntimeError):
            db.allocate_generated_event_number(cursor, "2026-07-09T12:00:00Z")

    def test_insert_allocates_only_for_matching_event(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (0,)
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch.object(db, "get_conn", return_value=connection):
            db.insert_esri_event({"Event Number": "", "Activity Type": "Peace Order", "Arrival Time": "2026-07-09T12:00:00Z"})

        insert_params = cursor.execute.call_args_list[-1].args[1]
        self.assertEqual(insert_params[1], "26-07-00000")
        connection.commit.assert_called_once()

    def test_insert_preserves_esri_event_number_without_generating(self):
        cursor = MagicMock()
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch.object(db, "get_conn", return_value=connection):
            db.insert_esri_event({"Event Number": "ESRI-1", "Activity Type": "Protective Order"})

        self.assertEqual(cursor.execute.call_count, 1)
        insert_params = cursor.execute.call_args.args[1]
        self.assertEqual(insert_params[0], "ESRI-1")
        self.assertIsNone(insert_params[1])


class BackfillSqlTests(unittest.TestCase):
    def test_backfill_select_sql_targets_only_missing_order_numbers(self):
        from scripts.backfill_generated_event_numbers import build_backfill_select_sql

        sql = build_backfill_select_sql("dbo.esri_events", "id").lower()

        self.assertIn("generated_event_number is null", sql)
        self.assertIn("event_number is null", sql)
        self.assertIn("%peace order%", sql)
        self.assertIn("%protective order%", sql)

    def test_backfill_update_sql_uses_key_and_rechecks_eligibility(self):
        from scripts.backfill_generated_event_numbers import build_backfill_update_sql

        sql = build_backfill_update_sql("dbo.esri_events", "id").lower()

        self.assertIn("set generated_event_number = ?", sql)
        self.assertIn("where [id] = ?", sql)
        self.assertIn("generated_event_number is null", sql)
        self.assertIn("event_number is null", sql)


if __name__ == "__main__":
    unittest.main()
