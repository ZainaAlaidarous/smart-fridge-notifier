import firebase_admin
from firebase_admin import credentials, firestore, messaging
import os
import json

# تهيئة Firebase (مرة واحدة فقط)
if not firebase_admin._apps:
    service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def send_unread_notifications():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_id = user.id
        user_data = user.to_dict()
        fcm_token = user_data.get("fcmToken")

        if not fcm_token:
            print(f"🚫 No FCM token for {user_id}")
            continue

        notif_ref = users_ref.document(user_id).collection("Notifications")
        unread_notifs = notif_ref.where("status", "==", "unread").stream()

        for notif in unread_notifs:
            notif_data = notif.to_dict()
            message = notif_data.get("message", "")
            if not message:
                continue

            try:
                response = messaging.send(
                    messaging.Message(
                        notification=messaging.Notification(
                            title="Smart Fridge Alert 🧊",
                            body=message,
                        ),
                        token=fcm_token
                    )
                )
                print(f"✅ Notification sent to {user_id}: {response}")
            except Exception as e:
                print(f"⚠️ Failed to send to {user_id}: {e}")

if __name__ == "__main__":
    send_unread_notifications()
