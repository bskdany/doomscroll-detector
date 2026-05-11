from exponent_server_sdk import (
    PushClient,
    PushMessage,
)
TOKEN = "YOUR_EXPO_PUSH_TOKEN"

def send_push_message(message, extra=None):
        response = PushClient().publish(
            PushMessage(to=TOKEN,
                        body=message,
                        data=extra, sound="default"))

if __name__ == '__main__':
    send_push_message('Stop Doomscrolling!')