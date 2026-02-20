import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot import event_messages


def test_reminder_and_exact_messages():
    tz = ZoneInfo("Asia/Tashkent")
    events = {
        "suhur_end": datetime(2026, 2, 20, 5, 44, tzinfo=tz),
        "fajr": datetime(2026, 2, 20, 5, 49, tzinfo=tz),
        "iftar": datetime(2026, 2, 20, 18, 15, tzinfo=tz),
    }

    now = datetime(2026, 2, 20, 5, 34, tzinfo=tz)
    msgs = event_messages(now, events, 10, {"suhur_end", "fajr", "iftar"})
    assert any("Сухур" in m for m in msgs)

    now2 = datetime(2026, 2, 20, 18, 15, tzinfo=tz)
    msgs2 = event_messages(now2, events, 10, {"suhur_end", "fajr", "iftar"})
    assert any("ифтара" in m for m in msgs2)
