# **Fincho Bot - Health Checker**
ربات تلگرامی برای نظارت بر وضعیت سیستم و سرویس‌ها با قابلیت ارسال هشدار در گروه تلگرام.

---

## **ویژگی‌ها**
✅ **مانیتورینگ سیستم**: نمایش CPU، حافظه، دیسک و اتصالات شبکه  
✅ **بررسی سرویس**: نظارت بر Health Check API  
✅ **هشدارهای هوشمند**: ارسال اعلان فوری برای مشکلات بحرانی  
✅ **گزارش روزانه**: ارسال خودکار وضعیت سیستم هر 24 ساعت  
✅ **بررسی مداوم**: چک کردن سیستم هر 20 ثانیه بدون ارسال پیام اضافی  
✅ **رابط کاربری تعاملی**: دکمه‌های اینلاین برای به‌روزرسانی اطلاعات

---

## **راه‌اندازی سریع**
### **۱. نصب وابستگی‌ها**
```bash
pip install aiogram aiohttp psutil
```

### **۲. تنظیم پیکربندی**
فایل `.env` را ایجاد کنید:
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
🔹 `/help` - نمایش راهنما

---

## **ویژگی‌های جدید**
- **بررسی هوشمند**: چک کردن هر 20 ثانیه با ارسال هشدار فقط برای مشکلات
- **کاهش اعلان‌های تکراری**: ارسال هر هشدار حداکثر یک بار در ساعت
- **گزارش روزانه**: ارسال خودکار وضعیت کلی هر 24 ساعت
- **بهینه‌سازی منابع**: پردازش کمتر برای کاهش مصرف سیستم

برای گزارش مشکلات یا پیشنهادات، لطفاً در گروه پشتیبانی پیام دهید.