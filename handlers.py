from datetime import datetime
from telegram_api import send_message, send_menu
from task_manager import tasks, save_tasks

# STATE VARIABLES
user_state = None
temp_task = {}
confirm_clear = False


#   HANDLE COMMAND  
def handle_command(text):
    global user_state, temp_task, confirm_clear

    original_text = text.strip()
    text = original_text.lower()

    #   CLEAR CANCEL  
    if confirm_clear and user_state is None and text != "confirm clear":
        confirm_clear = False
        send_message("❌ Clear cancelled.")
        send_menu()
        return

    #   CANCEL FLOW  
    if text == "cancel":
        user_state = None
        temp_task = {}
        send_message("Cancelled.")
        send_menu()
        return

    #   COMMAND ESCAPE  
    if text.startswith(("list", "clear", "done", "delete")):
        user_state = None
        temp_task = {}

    #   STEP 1: TASK NAME  
    if user_state == "waiting_task_name":
        temp_task["task"] = original_text
        user_state = "waiting_time"
        send_message("What time? (HH:MM)")
        return

    #   STEP 2: TIME  
    elif user_state == "waiting_time":
        try:
            parsed_time = datetime.strptime(text, "%H:%M")
        except:
            send_message("❌ Invalid format. Enter time like 18:30 or type 'cancel'")
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

    #   BUTTON HANDLING  
    if text == "add":
        user_state = "waiting_task_name"
        temp_task = {}
        send_message("What is the task name?")
        return

    elif text == "done":
        send_message("Send like: done TaskName")
        return

    #   LIST TASKS  
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

    #   MARK DONE  
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

                # show remaining tasks
                remaining = [x for x in tasks if not x["done"]]
                remaining = sorted(remaining, key=lambda x: x["time"])

                if remaining:
                    msg = "📌 Remaining Tasks:\n\n"
                    for i, x in enumerate(remaining, start=1):
                        msg += f"{i}. {x['task']} at {x['time']}\n"
                else:
                    msg = "🎉 All tasks completed!"

                send_message(msg)
                send_menu()
                return

        send_message("Task not found")
        send_menu()
        return

    #   CLEAR TASKS  
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

    #   DELETE TASK  
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

    #   UNKNOWN  
    else:
        send_message("Unknown command")
        send_menu()