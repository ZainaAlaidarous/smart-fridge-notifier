import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
import google.auth.transport.requests

# تحميل بيانات الخدمة
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# إعداد Firestore
db = firestore.client()

# إعداد FCM V1
def send_fcm_notification_v1(token, title, body):
    credentials_obj = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    request = google.auth.transport.requests.Request()
    credentials_obj.refresh(request)
    access_token = credentials_obj.token

    project_id = service_account_info["project_id"]
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": {
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("📲 Notification sent successfully!")
    else:
        print(f"❌ Failed to send notification: {response.status_code}, {response.text}")

# إرسال الإشعارات غير المقروءة والغير مرسلة
def send_unread_notifications():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        token = user_data.get("fcm_token")

        if not token:
            print(f"⚠️ No FCM token for user: {user_id}")
            continue

        notif_ref = users_ref.document(user_id).collection("Notifications")
        # ✅ تعديل الشرط ليشمل فقط الإشعارات غير المقروءة والتي لم تُرسل
        unread_notifs = notif_ref.where("status", "==", "unread").where("sent", "==", False).stream()

        for notif in unread_notifs:
            notif_data = notif.to_dict()
            message = notif_data.get("message")
            notif_id = notif.id

            send_fcm_notification_v1(token, "Smart Fridge Alert", message)

            # ✅ تحديث حقل 'sent' بعد الإرسال
            notif_ref.document(notif_id).update({
                "sent": True
            })
            print(f"📤 Notification sent and marked as sent: {notif_id}")

if __name__ == "__main__":
    send_unread_notifications()
