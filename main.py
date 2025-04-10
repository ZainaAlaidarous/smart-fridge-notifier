def check_expired_products():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        print(f"🔍 Checking for user: {user_id}")

        notif_ref = users_ref.document(user_id).collection("Notifications")
        all_notifs = notif_ref.stream()
        notif_list = list(all_notifs)

        # ✅ حذف الإشعارات القديمة إذا وصل العدد إلى 35 أو أكثر
        if len(notif_list) >= 35:
            print("🧹 Deleting all notifications (limit reached)...")
            for notif in notif_list:
                notif.reference.delete()

            users_ref.document(user_id).update({
                "lastNotificationNumber": 0
            })
            print("✅ Reset lastNotificationNumber to 0")

            # إعادة تعيين العداد في الذاكرة المحلية أيضًا
            last_notif_number = 0
        else:
            last_notif_number = user_data.get("lastNotificationNumber", 0)

        # الأقسام
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
                    expiry_date = parser.parse(expiry_str).date()
                except Exception:
                    print(f"⚠️ Invalid date for {product_name}: {expiry_str}")
                    continue

                days_left = (expiry_date - today).days
                message = None

                if days_left < 0:
                    message = f"Alert: Your item has expired!\n{product_name} expired on [{expiry_date.strftime('%d/%m/%Y')}]"
                elif 0 <= days_left <= 3:
                    message = f"Reminder: Your item is expiring soon!\n{product_name} expires on [{expiry_date.strftime('%d/%m/%Y')}]"

                if message:
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

        # تحديث العداد بعد الإضافة
        users_ref.document(user_id).update({
            "lastNotificationNumber": last_notif_number
        })
        print(f"🔢 Updated lastNotificationNumber: {last_notif_number}")
