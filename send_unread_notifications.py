import os  # Access environment variables
import json # Parse JSON data
import requests  # Send HTTP requests
import firebase_admin  # Initialize Firebase Admin SDK
from firebase_admin import credentials, firestore # Handle Firebase credentials and Firestore
from google.oauth2 import service_account  # Handle OAuth2 service account credentials
import google.auth.transport.requests # Refresh and transport Google authentication requests

# Load service account info from environment variable
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()

# Function to send a push notification using FCM v1 API
def send_fcm_notification_v1(token, title, body):
    # Create credentials object with messaging scope
    credentials_obj = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    # Refresh token to get access token
    request = google.auth.transport.requests.Request()
    credentials_obj.refresh(request)
    access_token = credentials_obj.token
    
    # Build FCM v1 API URL
    project_id = service_account_info["project_id"]
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
   
    # Set request headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }


    # Build notification payload
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
    # Send POST request to FCM API
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("📲 Notification sent successfully!")
    else:
        print(f"❌ Failed to send notification: {response.status_code}, {response.text}")

# Function to send unread and unsent notifications
def send_unread_notifications():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        token = user_data.get("fcm_token")
       
        # Skip user if no FCM token available
        if not token:
            print(f"⚠️ No FCM token for user: {user_id}")
            continue

        notif_ref = users_ref.document(user_id).collection("Notifications")
        # Fetch notifications that are unread and not yet sent
        unread_notifs = notif_ref.where("status", "==", "unread").where("sent", "==", False).stream()

        for notif in unread_notifs:
            notif_data = notif.to_dict()
            message = notif_data.get("message")
            notif_id = notif.id
            
            # Send notification to the user's device
            send_fcm_notification_v1(token, "Smart Fridge Alert", message)

            # Update notification as sent
            notif_ref.document(notif_id).update({
                "sent": True
            })
            print(f"📤 Notification sent and marked as sent: {notif_id}")

if __name__ == "__main__":
    send_unread_notifications()
