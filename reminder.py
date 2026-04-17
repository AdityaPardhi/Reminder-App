import time
import requests
from datetime import datetime
import json

from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHAT_ID in .env")

CHAT_ID = int(CHAT_ID)

user_state = None
temp_task = {}

tasks = []
last_update_id = None
confirm_clear = False

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
        


def send_menu():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Add Task", "callback_data": "add"},
                {"text": "View Tasks", "callback_data": "list"}
            ],
            [
                {"text": "Mark Done", "callback_data": "done"},
                {"text": "Clear Tasks", "callback_data": "clear"}
            ]
        ]
    }

    data = {
        "chat_id": CHAT_ID,
        "text": "Please choose an option",
        "reply_markup": json.dumps(keyboard)
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:
        print("Error sending menu:", response.text)


def save_tasks():
    with open("tasks.json", "w") as f:
        json.dump(tasks, f, indent=4)



# ---------------- SEND MESSAGE ----------------
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    response = requests.post(url, data={"chat_id": CHAT_ID, "text": text})

    if response.status_code != 200:
        print("Error sending message:", response.text)

# ---------------- GET UPDATES ----------------
def get_updates():
    global last_update_id

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=30"

    if last_update_id:
        url += f"&offset={last_update_id + 1}"

    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching updates:", response.text)
        return []

    response = response.json()


    messages = []

    if "result" in response:
        for update in response["result"]:
            if last_update_id and update["update_id"] <= last_update_id:
                continue
            last_update_id = update["update_id"]

            if "message" in update:
                messages.append(update["message"].get("text", ""))

            elif "callback_query" in update:
                messages.append(update["callback_query"]["data"])

                response = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                    data={"callback_query_id": update["callback_query"]["id"]}
                )
                if response.status_code != 200:
                    print("Error answering callback:", response.text)

    return messages


# ---------------- HANDLE COMMANDS ----------------
def handle_command(text):
    global tasks , confirm_clear , user_state, temp_task

    original_text = text.strip()
    text = original_text.lower()


    # 🔥 CLEAR FIRST (ONLY when not in another flow)
    if confirm_clear and user_state is None and text != "confirm clear":
        confirm_clear = False
        send_message("❌ Clear cancelled.")
        send_menu()
        return
    

    # 🔥 CANCEL FLOW
    if text == "cancel":
        user_state = None
        temp_task = {}
        send_message("Cancelled.")
        send_menu()
        return
    
    # COMMAND ESCAPE
    if text.startswith(("list", "clear", "done", "delete")):
        user_state = None
        temp_task = {}

    # STEP 1
    if user_state == "waiting_task_name":
        temp_task["task"] = original_text   # 🔥 FIXED
        user_state = "waiting_time"
        send_message("What time? (HH:MM)")
        return
    
    # 🔥 STEP 2
    elif user_state == "waiting_time":
        try:
            parsed_time = datetime.strptime(text, "%H:%M")
        except:
            send_message("❌ Invalid format. Please enter time like 18:30 or type 'cancel'")
            return

        temp_task["time"] = parsed_time.strftime("%H:%M")

        tasks.append({
            "task": temp_task["task"],
            "time": temp_task["time"],
            "done": False,
            "triggered": False,
            "next_reminder": None
        })

        save_tasks()

        send_message(f"Task added: {temp_task['task']} at {temp_task['time']}")

        user_state = None
        temp_task = {}

        send_menu()
        return



# ---- BUTTON HANDLING (INLINE) ----
    if text == "add":
        user_state = "waiting_task_name"
        temp_task = {}

        send_message("What is the task name?")
        return

    # elif text == "list":
    #     pass   # will go to your list logic below

    elif text == "done":
        send_message("Send like: Done task_name")
        return

    # elif text == "clear":
    #     pass   # will go to your clear logic below


    # ---- LIST TASKS ----
    elif text == "list":
        if not tasks:
            send_message("No tasks.")
            send_menu()
        else:
            msg = ""
            for i, t in enumerate(tasks, start=1):
                status = "✅" if t["done"] else "❌"
                msg += f"{i}. {status} {t['task']} at {t['time']}\n"
            send_message(msg)
            send_menu()
        return

    # ---- MARK DONE ----
    elif text.startswith("done"):
        parts = text.split()

        if len(parts) < 2:
            send_message("Usage: done TaskName")
            send_menu()
            return

        task_name = " ".join(parts[1:])

        for t in tasks:
            if t["task"].lower() == task_name.lower():
                t["done"] = True
                t["triggered"] = True
                t["next_reminder"] = None 
                save_tasks()
                send_message(f"✅ Marked '{task_name}' as done")

                # 🔥 SHOW ONLY REMAINING TASKS
                remaining = [t for t in tasks if not t["done"]]
                remaining = sorted(remaining, key=lambda x: x["time"])

                if remaining:
                    msg = "📌 Remaining Tasks:\n\n"
                    for i, t in enumerate(remaining, start=1):
                        msg += f"{i}. {t['task']} at {t['time']}\n"
                else:
                    msg = "🎉 All tasks completed!"

                send_message(msg)

                send_menu()
                return

        send_message("Task not found")
        send_menu()
        return

    # ---- CLEAR TASKS ----
    elif text == "clear":

        if not tasks:
            send_message("No tasks to clear.")
            send_menu()
            return

        if not confirm_clear:
            msg = "⚠️ Confirm clear by typing: confirm clear\n\n"

            for i, t in enumerate(tasks, start=1):
                msg += f"{i}. {t['task']} at {t['time']}\n"

            send_message(msg)
            confirm_clear = True
            return
        
        send_message("Already waiting for confirmation. Type 'confirm clear'")
        send_menu()
        return
        


    elif text == "confirm clear":

        if confirm_clear:
            tasks.clear()
            save_tasks()
            send_message("All tasks cleared.")
            confirm_clear = False
            send_menu()
        else:
            send_message("Nothing to confirm.")
            send_menu()
        return
    
    
    
    elif text.startswith("delete"):
        parts = text.split()

        if len(parts) < 2:
            send_message("Usage: delete <number>")
            send_menu()
            return

        try:
            index = int(parts[1]) - 1
        except:
            send_message("Invalid number")
            send_menu()
            return

        if index < 0 or index >= len(tasks):
            send_message("Out of range")
            send_menu()
            return

        removed = tasks.pop(index)
        save_tasks()

        send_message(f"Deleted: {removed['task']}")
        send_menu()
        return

    # ---- UNKNOWN ----
    else:
        send_message("Unknown command")
        send_menu()

# ---------------- CHECK TASKS ----------------
def check_tasks():
    now = datetime.now()

    for t in tasks:
        task_time = datetime.strptime(t["time"], "%H:%M").replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        # 🔥 FIRST TRIGGER
        if not t["done"] and not t.get("triggered", False) and now >= task_time:
            send_message(f"⏰ Do this now: {t['task']}")
            
            t["triggered"] = True
            t["next_reminder"] = (now.timestamp() + 60)  # next in 60 sec
            save_tasks()

        # 🔥 FOLLOW-UP REMINDERS
        elif not t["done"] and t["triggered"]:
            if t["next_reminder"] and now.timestamp() >= t["next_reminder"]:
                send_message(f"⚠️ Still pending: {t['task']}")

                # schedule next reminder
                t["next_reminder"] = (now.timestamp() + 60)
                save_tasks()



def skip_old_updates():
    global last_update_id

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error skipping updates:", response.text)
        return

    response = response.json()
    if "result" in response and response["result"]:
        last_update_id = response["result"][-1]["update_id"]


# ---------------- MAIN LOOP ----------------
load_tasks()
skip_old_updates()

print("Bot started...")
send_menu()


while True:
    texts = get_updates()

    for text in texts:
        handle_command(text)

    check_tasks()

    time.sleep(0.1)

