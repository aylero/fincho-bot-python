# **Fincho Bot - Health Checker**

ربات تلگرامی برای نظارت بر وضعیت سیستم و سرویس‌ها با قابلیت ارسال هشدار و آمارگیری دقیق.

---

## **ویژگی‌ها**
✅ **مانیتورینگ سیستم**: نمایش CPU، حافظه، دیسک و اتصالات شبکه  
✅ **بررسی سرویس**: نظارت بر Health Check API  
✅ **هشدارهای هوشمند**: ارسال اعلان فوری برای مشکلات بحرانی  
✅ **تگ کردن مدیران**: اطلاع‌رسانی خودکار به مدیران در مواقع بحرانی  
✅ **اطلاع‌رسانی بازیابی**: اعلان خودکار هنگام برگشت سرویس به حالت آنلاین  
✅ **آمارگیری دقیق**: ثبت زمان‌های دقیق آپتایم و دان‌تایم سرویس  
✅ **گزارش روزانه و هفتگی**: آمار دقیق از وضعیت سرویس در بازه‌های مختلف  
✅ **ذخیره‌سازی داده‌ها**: حفظ آمار حتی پس از راه‌اندازی مجدد ربات

---

## **راه‌اندازی سریع**
### **۱. نصب وابستگی‌ها**
```bash
pip install aiogram aiohttp psutil
```

### **۲. تنظیم پیکربندی**
فایل `.env` را ایجاد کنید یا مقادیر را مستقیماً در کد تنظیم نمایید:
```env
API_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_TELEGRAM_CHAT_ID
THREAD_ID=YOUR_THREAD_ID
HEALTH_CHECK_URL=http://127.0.0.1:3000/health/check
```

### **۳. اجرای ربات**
```bash
python bot.py
```

---

## **اجرا به‌عنوان سرویس**
```bash
sudo nano /etc/systemd/system/fincho-health-checker.service
```

محتوای فایل سرویس:
```ini
[Unit]
Description=Fincho Health Check Bot
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 /path/to/bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

فعال‌سازی سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fincho-health-checker.service
sudo systemctl start fincho-health-checker.service
```

---

## **دستورات ربات**
🔹 `/check` - بررسی کامل سیستم و سرویس  
🔹 `/system` - نمایش اطلاعات سیستم  
🔹 `/service` - نمایش وضعیت سرویس  
🔹 `/stats` - نمایش آمار کلی سرویس  
🔹 `/daily` - نمایش آمار امروز  
🔹 `/weekly` - نمایش آمار هفتگی  
🔹 `/help` - نمایش راهنما

---

## **تنظیمات پیشرفته**

ربات دارای تنظیمات پیشرفته‌ای است که می‌توانید با تغییر مقادیر ثابت در ابتدای کد، رفتار آن را تنظیم کنید:

```python
# تنظیمات مانیتورینگ
CHECK_INTERVAL = 86400  # زمان بین گزارش‌های روزانه (ثانیه)
MONITORING_INTERVAL = 20  # فاصله زمانی بررسی سیستم (ثانیه)
CRITICAL_CPU_THRESHOLD = 90  # آستانه هشدار برای CPU (درصد)
CRITICAL_MEMORY_THRESHOLD = 90  # آستانه هشدار برای حافظه (درصد)
CRITICAL_DISK_THRESHOLD = 90  # آستانه هشدار برای دیسک (درصد)
ALERT_REPEAT_INTERVAL = 1800  # فاصله تکرار هشدارها (ثانیه)
RECOVERY_NOTIFICATION = True  # اعلان بازیابی سرویس
STATS_SUMMARY_HOUR = 23  # ساعت ارسال گزارش آماری روزانه
STATS_SUMMARY_MINUTE = 0  # دقیقه ارسال گزارش آماری روزانه
```

---

## **ویژگی‌های آماری**

### **۱. آمار روزانه**
- درصد دسترس‌پذیری سرویس
- مدت زمان آپتایم و دان‌تایم
- تعداد قطعی‌های سرویس
- وضعیت فعلی سرویس

### **۲. آمار هفتگی**
- خلاصه عملکرد ۷ روز گذشته
- میانگین دسترس‌پذیری
- نمودار روزانه وضعیت سرویس

### **۳. آمار کلی**
- زمان کل آپتایم و دان‌تایم
- تعداد کل قطعی‌ها
- درصد دسترس‌پذیری کلی از زمان شروع مانیتورینگ

---

## **تگ کردن مدیران**

برای تنظیم لیست مدیرانی که باید در مواقع بحرانی تگ شوند، مقدار `ADMIN_USERNAMES` را در ابتدای کد تغییر دهید:

```python
# تنظیمات مدیران
ADMIN_USERNAMES = ["username1", "username2", "username3"]  # نام‌های کاربری تلگرام بدون @ 
```

---

## **ذخیره‌سازی داده‌ها**

آمار سرویس در فایل `service_stats.json` ذخیره می‌شود و پس از راه‌اندازی مجدد ربات، داده‌ها حفظ می‌شوند. این فایل شامل:

- تاریخچه دان‌تایم‌ها با زمان دقیق شروع و پایان
- آمار روزانه دسترس‌پذیری
- زمان کل آپتایم و دان‌تایم

---

## **نکات پیشرفته**

### **۱. تنظیم آستانه‌های هشدار**
آستانه‌های هشدار برای CPU، حافظه و دیسک را می‌توانید با توجه به نیازهای خود تنظیم کنید.

### **۲. کنترل فاصله زمانی هشدارها**
برای جلوگیری از ارسال هشدارهای مکرر، مقدار `ALERT_REPEAT_INTERVAL` را تنظیم کنید.

### **۳. گزارش آماری خودکار**
ربات به صورت خودکار در ساعت مشخص شده، گزارش آماری روزانه را ارسال می‌کند.

---

## **عیب‌یابی**

### **۱. مشکل اتصال به API**
اگر ربات نمی‌تواند به سرویس متصل شود، آدرس `HEALTH_CHECK_URL` را بررسی کنید.

### **۲. مشکل ارسال پیام**
اطمینان حاصل کنید که ربات در گروه مورد نظر عضو است و دسترسی ارسال پیام دارد.

### **۳. خطای دسترسی به فایل**
مطمئن شوید کاربری که ربات را اجرا می‌کند، دسترسی نوشتن در پوشه ربات را دارد.

---

ربات **Fincho Health Checker** ابزاری قدرتمند برای نظارت بر سرویس‌هاست که با ارائه آمار دقیق و هشدارهای به‌موقع، به شما کمک می‌کند تا همواره از وضعیت سیستم‌های خود آگاه باشید.