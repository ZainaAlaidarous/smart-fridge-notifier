import os
import json
import pytz
from datetime import datetime
from dateutil import parser

import firebase_admin
from firebase_admin import credentials, firestore

# تحميل بيانات الخدمة من متغير البيئة
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# إعداد الاتصال بقاعدة البيانات
db = firestore.client()
timezone = pytz.timezone('Asia/Riyadh')
now = datetime.now(timezone)  # ✅ سيتم تخزين هذا كتاريخ من نوع Timestamp
today = now.date()

def check_expired_products():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        print(f"🔍 Checking for user: {user_id}")

        # جلب آخر رقم إشعار
        last_notif_number = user_data.get("lastNotificationNumber", 0)

        # الدخول على جميع الأقسام في Categories
        categories_ref = users_ref.document(user_id).collection("Categories")
        categories = categories_ref.stream()

        for category in categories:
            category_id = category.id
            print(f"📁 Category: {category_id}")
            products_ref = categories_ref.document(category_id).collection("Products")
            products = products_ref.stream()

            for product in products:
                product_data = product.to_dict()
                product_name = product_data.get("name", "")
                expiry_str = product_data.get("expiry_date", "")
                try:
                    expiry_date = parser.parse(expiry_str).date()
                except Exception as e:
                    print(f"⚠️ Invalid date for {product_name}: {expiry_str}")
                    continue

                days_left = (expiry_date - today).days
                status = None
                message = None

                if days_left < 0:
                    status = "expired"
                    message = f"Alert: Your item has expired!\n{product_name} expired on [{expiry_date.strftime('%d/%m/%Y')}]"
                elif 0 <= days_left <= 3:
                    status = "expiring"
                    message = f"Reminder: Your item is expiring soon!\n{product_name} expires on [{expiry_date.strftime('%d/%m/%Y')}]"

                if message:
                    last_notif_number += 1
                    notif_id = f"Notifications-{last_notif_number}"
                    notif_data = {
                        "message": message,
                        "status": "unread",
                        "product_name": product_name,
                        "expiry_date": expiry_str,
                        "date": now  # ✅ تخزين التاريخ كـ Timestamp
                    }
                    notif_ref = users_ref.document(user_id).collection("Notifications").document(notif_id)
                    notif_ref.set(notif_data)
                    print(f"✅ Notification created: {notif_id}")

        # تحديث العداد
        users_ref.document(user_id).update({
            "lastNotificationNumber": last_notif_number
        })
        print(f"🔢 Updated lastNotificationNumber: {last_notif_number}")

if __name__ == "__main__":
    check_expired_products()
