import requests
import json
from config import TOKEN, CHAT_ID

last_update_id = None


# SEND MESSAGE
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

    if response.status_code != 200:
        print("Error sending message:", response.text)


# SEND MENU
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


#   GET UPDATES  
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

            # skip old updates
            if last_update_id and update["update_id"] <= last_update_id:
                continue

            last_update_id = update["update_id"]

            # normal messages
            if "message" in update:
                messages.append(update["message"].get("text", ""))

            # button clicks
            elif "callback_query" in update:
                messages.append(update["callback_query"]["data"])

                # Acknowledge callback
                cb = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                    data={
                        "callback_query_id": update["callback_query"]["id"]
                    }
                )

                if cb.status_code != 200:
                    print("Error answering callback:", cb.text)

    return messages


#   SKIP OLD UPDATES  
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