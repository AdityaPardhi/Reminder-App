import json
from datetime import datetime
from telegram_api import send_message

tasks = []


# LOAD TASKS
def load_tasks():
    global tasks

    try:
        with open("tasks.json", "r") as f:
            tasks = json.load(f)
    except:
        tasks = []

    for t in tasks:
        if "triggered" not in t:
            t["triggered"] = False
        if "next_reminder" not in t:
            t["next_reminder"] = None


# SAVE TASKS
def save_tasks():
    with open("tasks.json", "w") as f:
        json.dump(tasks, f, indent=4)


# CHECK TASKS 
def check_tasks():
    now = datetime.now()

    for t in tasks:
        task_time = datetime.strptime(t["time"], "%H:%M").replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        # FIRST TRIGGER
        if not t["done"] and not t.get("triggered", False) and now >= task_time:
            send_message(f"⏰ Do this now: {t['task']}")

            t["triggered"] = True
            t["next_reminder"] = now.timestamp() + 60
            save_tasks()

        # FOLLOW-UP REMINDERS
        elif not t["done"] and t["triggered"]:
            if t["next_reminder"] and now.timestamp() >= t["next_reminder"]:
                send_message(f"⚠️ Still pending: {t['task']}")

                t["next_reminder"] = now.timestamp() + 60
                save_tasks()