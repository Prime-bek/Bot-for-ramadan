import asyncio
import csv
import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

KNOWN_EVENTS = {
    "suhur_end": "Сухур",
    "fajr": "Фаджр",
    "dhuhr": "Зухр",
    "asr": "Аср",
    "maghrib": "Магриб",
    "isha": "Иша",
    "iftar": "Ифтар",
}


def combine_dt(d: date, hh_mm: str, tz: ZoneInfo) -> datetime:
    t = datetime.strptime(hh_mm, "%H:%M").time()
    return datetime.combine(d, t, tz)


def load_schedule(schedule_file: str, tz: ZoneInfo) -> dict[date, dict[str, datetime]]:
    schedule: dict[date, dict[str, datetime]] = {}

    with open(schedule_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "date" not in reader.fieldnames:
            raise ValueError("CSV must contain the 'date' column (YYYY-MM-DD).")

        time_columns = [c for c in reader.fieldnames if c != "date"]
        if not time_columns:
            raise ValueError("CSV should have at least one event time column.")

        for row in reader:
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            events: dict[str, datetime] = {}
            for col in time_columns:
                value = (row.get(col) or "").strip()
                if value:
                    events[col] = combine_dt(d, value, tz)
            schedule[d] = events

    return schedule


def label_for_event(event_key: str) -> str:
    return KNOWN_EVENTS.get(event_key, event_key.replace("_", " ").title())


def is_exact_minute(now: datetime, target: datetime) -> bool:
    return now.strftime("%Y-%m-%d %H:%M") == target.strftime("%Y-%m-%d %H:%M")


def event_messages(
    now: datetime,
    events: dict[str, datetime],
    reminder_minutes: int,
    reminder_events: set[str],
) -> list[str]:
    messages: list[str] = []

    for event_key, event_time in events.items():
        event_label = label_for_event(event_key)

        if event_key in reminder_events:
            reminder_time = event_time - timedelta(minutes=reminder_minutes)
            if is_exact_minute(now, reminder_time):
                messages.append(
                    f"⏳ До времени «{event_label}» осталось {reminder_minutes} минут."
                )

        if is_exact_minute(now, event_time):
            if event_key == "suhur_end":
                messages.append("🛑 Время сухура завершилось. Держим пост.")
            elif event_key == "iftar":
                messages.append("🌙 Время ифтара наступило. Можно открыть уразу.")
            else:
                messages.append(f"🕌 Наступило время намаза: {event_label}.")

    return messages


async def run_bot() -> None:
    from dotenv import load_dotenv
    from telegram import Bot

    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent")
    schedule_file = os.getenv("SCHEDULE_FILE", "schedule.csv")
    reminder_minutes = int(os.getenv("REMINDER_MINUTES", "10"))
    check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
    reminder_events = {
        x.strip()
        for x in os.getenv("REMINDER_EVENTS", "suhur_end,fajr,iftar").split(",")
        if x.strip()
    }

    if not token or not chat_id:
        raise ValueError("BOT_TOKEN and CHAT_ID are required in .env")

    tz = ZoneInfo(timezone)
    schedule = load_schedule(schedule_file, tz)
    bot = Bot(token=token)

    logging.info("Bot started. Interval=%s sec; reminder=%s min", check_interval, reminder_minutes)
    sent_keys: set[tuple[str, str]] = set()

    while True:
        now = datetime.now(tz).replace(second=0, microsecond=0)
        day_events = schedule.get(now.date())

        if day_events:
            for text in event_messages(now, day_events, reminder_minutes, reminder_events):
                message_key = (now.isoformat(), text)
                if message_key in sent_keys:
                    continue
                await bot.send_message(chat_id=chat_id, text=text)
                logging.info("Sent: %s", text)
                sent_keys.add(message_key)
        else:
            logging.warning("No schedule found for %s", now.date())

        await asyncio.sleep(check_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_bot())
