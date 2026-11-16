import tempfile
import unittest
from pathlib import Path

from prepare_data import load_events


class EventLoadingTests(unittest.TestCase):
    def load_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            path.write_text(text, encoding="utf-8")
            return load_events(path)

    def test_last_event_without_newline_is_loaded(self):
        events, counts = self.load_text(
            "timestamp,visitorid,event,itemid,transactionid\n100,1,view,10,"
        )
        self.assertEqual(events.size, 1)
        self.assertEqual(events[0]["timestamp"], 100)
        self.assertEqual(counts, {"view": 1})

    def test_blank_lines_do_not_create_uninitialized_events(self):
        events, counts = self.load_text(
            "timestamp,visitorid,event,itemid,transactionid\n\n100,1,view,10,\n\n"
        )
        self.assertEqual(events.size, 1)
        self.assertEqual(events[0]["item"], 10)
        self.assertEqual(sum(counts.values()), events.size)

    def test_empty_events_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "no usable events"):
            self.load_text("timestamp,visitorid,event,itemid,transactionid\n")

    def test_unknown_event_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown event type"):
            self.load_text("timestamp,visitorid,event,itemid,transactionid\n100,1,click,10,\n")


if __name__ == "__main__":
    unittest.main()
