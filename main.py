import os  # Access environment variables
import json # Parse JSON data
import pytz # Handle timezones
from datetime import datetime # Work with dates and times
from dateutil import parser  # Parse date strings
import firebase_admin  # Initialize Firebase Admin SDK
from firebase_admin import credentials, firestore # Credentials for auth, Firestore for database access

# Load service account credentials from environment variable
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# Initialize Firestore client and set timezone
db = firestore.client()
timezone = pytz.timezone('Asia/Riyadh')
now = datetime.now(timezone)
today = now.date()

def check_expired_products():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        print(f"🔍 Checking for user: {user_id}")
        
        # Access user's notifications collection
        notif_ref = users_ref.document(user_id).collection("Notifications")
        all_notifs = notif_ref.stream()
        notif_list = list(all_notifs)

        # Delete all notifications if they reach 35 or more
        if len(notif_list) >= 35:
            print("🧹 Deleting all notifications (limit reached)...")
            for notif in notif_list:
                notif.reference.delete()
                
            # Reset the lastNotificationNumber to 0 after deletion
            users_ref.document(user_id).update({
                "lastNotificationNumber": 0
            })
            print("✅ Reset lastNotificationNumber to 0")
            last_notif_number = 0
        else:
            # Retrieve the last notification number
            last_notif_number = user_data.get("lastNotificationNumber", 0)

        # Access user's categories
        categories_ref = users_ref.document(user_id).collection("Categories")
        categories = categories_ref.stream()

        for category in categories:
            category_id = category.id
            products_ref = categories_ref.document(category_id).collection("Products")
            products = products_ref.stream()

            for product in products:
                product_data = product.to_dict()
                product_name = product_data.get("name", "")
                expiry_str = product_data.get("expiry_date", "")

                try:
                    # Parse expiry date
                    expiry_date = parser.parse(expiry_str).date()
                except Exception:
                    print(f"⚠️ Invalid date for {product_name}: {expiry_str}")
                    continue
                    
                # Calculate days left until expiry
                days_left = (expiry_date - today).days
                message = None
                
                # Generate appropriate message based on expiry status
                if days_left < 0:
                    message = f"Alert: Your item has expired!\n{product_name} expired on [{expiry_date.strftime('%d/%m/%Y')}]"
                elif 0 <= days_left <= 3:
                    message = f"Reminder: Your item is expiring soon!\n{product_name} expires on [{expiry_date.strftime('%d/%m/%Y')}]"

                if message:
                    # Create and save a new notification
                    last_notif_number += 1
                    notif_id = f"Notifications-{last_notif_number}"
                    notif_data = {
                        "message": message,
                        "status": "unread",
                        "product_name": product_name,
                        "expiry_date": expiry_str,
                        "date": now,
                        "sent": False 
                    }
                    notif_ref.document(notif_id).set(notif_data)
                    print(f"✅ Notification created: {notif_id}")
                    
        # Update the last notification number for the user
        users_ref.document(user_id).update({
            "lastNotificationNumber": last_notif_number
        })
        print(f"🔢 Updated lastNotificationNumber: {last_notif_number}")

if __name__ == "__main__":
    check_expired_products()
