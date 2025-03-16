# **Fincho Bot - Health Checker**
یک **ربات تلگرام** برای نظارت بر وضعیت **سیستم** و **سرویس‌ها** که اطلاعات مانیتورینگ را در گروه تلگرام ارسال می‌کند. این ربات از **Aiogram** استفاده می‌کند و قابلیت‌های متعددی مانند بررسی مصرف منابع سرور، وضعیت سرویس‌ها، اعلان‌های خودکار، و منوهای تعاملی دارد.

---

## **ویژگی‌ها**
✅ **بررسی وضعیت سیستم**: دریافت اطلاعاتی از جمله **CPU، حافظه، فضای دیسک، پردازش‌ها و اتصالات شبکه**  
✅ **بررسی وضعیت سرویس**: مانیتورینگ **Health Check API** و نمایش وضعیت سرویس  
✅ **اعلان‌های خودکار**: ارسال هشدار در صورت **مصرف بالای منابع** یا **داون شدن سرویس**  
✅ **دستورات تعاملی**: دارای **منوی اینلاین** و **دستورات متنی** برای مشاهده وضعیت  
✅ **دستور `/help`** برای نمایش راهنمای ربات  
✅ **پشتیبانی از آپدیت خودکار داده‌ها**

---

## **پیش‌نیازها**
### **۱. نصب وابستگی‌ها**
ابتدا **Python 3.8+** و **pip** را نصب کنید.

سپس، وابستگی‌های لازم را با اجرای دستور زیر نصب کنید:
```bash
pip install -r requirements.txt
```

### **۲. تنظیم مقادیر محیطی (`.env`)**
فایل `.env` را در دایرکتوری پروژه ایجاد کنید و مقادیر زیر را اضافه کنید:
```env
API_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_TELEGRAM_CHAT_ID
THREAD_ID=YOUR_THREAD_ID
HEALTH_CHECK_URL=http://127.0.0.1:3000/health/check
CHECK_INTERVAL=300  # زمان بررسی وضعیت (ثانیه)
```
**نکته:** برای دریافت `API_TOKEN`، یک ربات جدید در **BotFather** تلگرام ایجاد کنید.

---

## **نحوه اجرای ربات**
### **۱. اجرای مستقیم در ترمینال**
می‌توانید ربات را مستقیماً اجرا کنید:
```bash
python bot.py
```

### **۲. اجرای به عنوان سرویس (`systemd`)**
اگر می‌خواهید ربات به‌صورت **سرویس دائمی** اجرا شود، یک فایل **Systemd Service** بسازید.

۱️⃣ ابتدا یک فایل جدید در `/etc/systemd/system/fincho-health-checker.service` ایجاد کنید:
```bash
sudo nano /etc/systemd/system/fincho-health-checker.service
```

۲️⃣ محتوای زیر را داخل آن قرار دهید:
```ini
[Unit]
Description=Fincho Health Check Bot
After=network.target

[Service]
User=fincho
WorkingDirectory=/home/fincho/fincho-bot-health-checker
ExecStart=/usr/bin/python3 /home/fincho/fincho-bot-health-checker/bot.py
Restart=always
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

۳️⃣ ذخیره و خروج (`CTRL + X` سپس `Y` و `Enter`)

۴️⃣ فعال‌سازی و اجرای سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fincho-health-checker.service
sudo systemctl start fincho-health-checker.service
```

۵️⃣ بررسی وضعیت سرویس:
```bash
sudo systemctl status fincho-health-checker.service
```

۶️⃣ راه‌اندازی مجدد سرویس:
```bash
sudo systemctl restart fincho-health-checker.service
```

۷️⃣ توقف سرویس:
```bash
sudo systemctl stop fincho-health-checker.service
```

---

## **دستورات ربات**
🔹 `/check` ➜ بررسی وضعیت **سرویس و سیستم**  
🔹 `/system` ➜ نمایش اطلاعات **سیستم (CPU، حافظه، دیسک و...)**  
🔹 `/service` ➜ نمایش اطلاعات **سرویس (Health Check API)**  
🔹 `/help` ➜ نمایش لیست دستورات  
🔹 **دکمه‌ی `🔄 Refresh`** ➜ به‌روزرسانی وضعیت به‌صورت دستی  

---

## **گزارش مشکلات و پیشنهادات**
🔹 اگر با مشکلی مواجه شدید یا پیشنهادی برای بهبود ربات دارید، لطفاً **یک Issue در GitHub باز کنید** یا در گروه پشتیبانی پیام بفرستید.

🚀 **Fincho Bot - Health Checker** به شما کمک می‌کند که همیشه وضعیت سرور و سرویس‌های خود را در کنترل داشته باشید!