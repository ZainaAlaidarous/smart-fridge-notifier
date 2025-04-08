import os
import json
import pytz
import requests
from datetime import datetime
from dateutil import parser
import firebase_admin
from firebase_admin import credentials, firestore
from google.auth.transport.requests import Request  # 🔁 للحصول على access token
from google.oauth2 import service_account           # 🔐 لمصادقة Admin SDK

# ✅ تحميل بيانات حساب الخدمة من GitHub Secrets (تم حفظها كسلسلة JSON في متغير البيئة)
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_KEY"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# ✅ إنشاء عميل Firestore وتحديد المنطقة الزمنية
db = firestore.client()
timezone = pytz.timezone('Asia/Riyadh')
now = datetime.now(timezone)
today = now.date()

# ✅ دالة لإرسال إشعار Push باستخدام FCM API V1 (بدون legacy token)
def send_fcm_notification_v1(user_id, message_body):
    # تحديد صلاحيات الوصول
    SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
    
    # تهيئة credentials من ملف الخدمة
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    credentials.refresh(Request())  # 🔁 تجديد access token

    access_token = credentials.token
    project_id = service_account_info['project_id']

    # عنوان طلب FCM API V1
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; UTF-8',
    }

    # محتوى الرسالة التي سترسل إلى topic باسم user_id
    message = {
        "message": {
            "topic": user_id,
            "notification": {
                "title": "Smart Fridge Alert",
                "body": message_body
            },
            "data": {
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            }
        }
    }

    # تنفيذ الإرسال عبر FCM
    response = requests.post(url, headers=headers, json=message)
    print(f"📤 Sent FCM to {user_id}: {response.status_code} - {response.text}")

# ✅ الدالة الأساسية التي تتحقق من المنتجات وتُنشئ إشعارات للمستخدمين
def check_expired_products():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        print(f"🔍 Checking for user: {user_id}")

        notif_ref = users_ref.document(user_id).collection("Notifications")

        # ✅ إذا كان عدد الإشعارات 35 أو أكثر → نحذفها كلها ونصفر العداد
        all_notifs = notif_ref.stream()
        notif_list = list(all_notifs)

        if len(notif_list) >= 35:
            print("🧹 Deleting all notifications (limit reached)...")
            for notif in notif_list:
                notif.reference.delete()

            users_ref.document(user_id).update({
                "lastNotificationNumber": 0
            })
            print("✅ Reset lastNotificationNumber to 0")
            continue  # ننتقل للمستخدم التالي

        # ✅ جلب رقم آخر إشعار محفوظ
        last_notif_number = user_data.get("lastNotificationNumber", 0)

        # ✅ التحقق من كل منتج داخل الأقسام
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

                # ✅ محاولة تحويل تاريخ الانتهاء إلى كائن تاريخ
                try:
                    expiry_date = parser.parse(expiry_str).date()
                except Exception:
                    print(f"⚠️ Invalid date for {product_name}: {expiry_str}")
                    continue

                days_left = (expiry_date - today).days
                message = None

                # ✅ تحديد نوع الإشعار بناءً على التاريخ
                if days_left < 0:
                    message = f"Alert: Your item has expired!\n{product_name} expired on [{expiry_date.strftime('%d/%m/%Y')}]"
                elif 0 <= days_left <= 3:
                    message = f"Reminder: Your item is expiring soon!\n{product_name} expires on [{expiry_date.strftime('%d/%m/%Y')}]"

                if message:
                    # ✅ إنشاء إشعار جديد وتحديث الرقم
                    last_notif_number += 1
                    notif_id = f"Notifications-{last_notif_number}"
                    notif_data = {
                        "message": message,
                        "status": "unread",
                        "product_name": product_name,
                        "expiry_date": expiry_str,
                        "date": now
                    }
                    notif_ref.document(notif_id).set(notif_data)
                    print(f"✅ Notification created: {notif_id}")

                    # ✅ إرسال إشعار Push باستخدام FCM API V1
                    send_fcm_notification_v1(user_id, message)

        # ✅ تحديث رقم آخر إشعار للمستخدم
        users_ref.document(user_id).update({
            "lastNotificationNumber": last_notif_number
        })
        print(f"🔢 Updated lastNotificationNumber: {last_notif_number}")

# ✅ تنفيذ الدالة عند تشغيل السكربت
if __name__ == "__main__":
    check_expired_products()
