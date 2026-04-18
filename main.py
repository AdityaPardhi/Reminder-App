import time
from telegram_api import get_updates, skip_old_updates, send_menu
from handlers import handle_command
from task_manager import load_tasks, check_tasks


# STARTUP
load_tasks()
skip_old_updates()

print("Bot started...")
send_menu()


# MAIN LOOP
while True:
    texts = get_updates()

    for text in texts:
        handle_command(text)

    check_tasks()

    time.sleep(0.1)


