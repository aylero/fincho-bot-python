import asyncio
import platform
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

import aiohttp
import psutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError

# Configuration
API_TOKEN = "7373428920:AAFYXy5o-_S6Cy1BbT6KANJWLHMH8Xf1w1U"
CHAT_ID = "-1002355040050"
THREAD_ID = 771
HEALTH_CHECK_URL = "http://127.0.0.1:3000/health/check"

# Admin configuration - add Telegram usernames of admins to tag (without @ symbol)
ADMIN_USERNAMES = ["alireza10up", "Sajad_mhri", "Grayorc"]

# Monitoring configuration
CHECK_INTERVAL = 86400  # 24 hours (in seconds) for regular status updates
MONITORING_INTERVAL = 10  # Check every 10 seconds
CRITICAL_CPU_THRESHOLD = 90  # CPU usage percentage threshold for alerts
CRITICAL_MEMORY_THRESHOLD = 90  # Memory usage percentage threshold for alerts
CRITICAL_DISK_THRESHOLD = 90  # Disk usage percentage threshold for alerts
ALERT_REPEAT_INTERVAL = 1800  # Repeat alerts every 30 minutes if issue persists
RECOVERY_NOTIFICATION = True  # Send notification when service recovers
STATS_SUMMARY_HOUR = 23  # Hour of the day to send statistics summary (24-hour format)
STATS_SUMMARY_MINUTE = 0  # Minute of the hour to send statistics summary
STATS_FILE = "service_stats.json"  # File to store statistics

# Initialize bot
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # Using HTML instead of Markdown for better reliability
)
dp = Dispatcher()

# Helper function to escape HTML characters
def escape_html(text):
    """Escape HTML special characters to prevent formatting issues"""
    if not isinstance(text, str):
        text = str(text)
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

# Statistics tracking
class StatsTracker:
    def __init__(self, stats_file=STATS_FILE):
        self.stats_file = stats_file
        self.stats = self._load_stats()
        self.current_downtime_start = None

    def _load_stats(self) -> Dict:
        """Load statistics from file or create default structure"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Default stats structure
        return {
            "total_uptime_seconds": 0,
            "total_downtime_seconds": 0,
            "downtime_events": [],
            "daily_stats": {},
            "last_updated": datetime.now().isoformat(),
            "service_started": datetime.now().isoformat()
        }

    def _save_stats(self):
        """Save statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def update_service_status(self, is_online: bool, timestamp: datetime = None):
        """Update statistics based on service status"""
        if timestamp is None:
            timestamp = datetime.now()

        # Format for daily stats
        date_str = timestamp.strftime("%Y-%m-%d")
        if date_str not in self.stats["daily_stats"]:
            self.stats["daily_stats"][date_str] = {
                "uptime_seconds": 0,
                "downtime_seconds": 0,
                "downtime_events": 0,
                "last_status": None
            }

        # Get time since last update
        last_updated = datetime.fromisoformat(self.stats["last_updated"])
        time_diff = (timestamp - last_updated).total_seconds()

        # Handle downtime events
        if not is_online:
            # Service is down
            if self.current_downtime_start is None:
                # This is a new downtime event
                self.current_downtime_start = timestamp
                self.stats["daily_stats"][date_str]["downtime_events"] += 1
            else:
                # Continuing downtime, update counters
                if time_diff > 0:
                    self.stats["total_downtime_seconds"] += time_diff
                    self.stats["daily_stats"][date_str]["downtime_seconds"] += time_diff
        else:
            # Service is up
            if self.current_downtime_start is not None:
                # Service just recovered
                downtime_duration = (timestamp - self.current_downtime_start).total_seconds()
                self.stats["downtime_events"].append({
                    "start": self.current_downtime_start.isoformat(),
                    "end": timestamp.isoformat(),
                    "duration_seconds": downtime_duration
                })
                self.current_downtime_start = None
            else:
                # Continuing uptime, update counters
                if time_diff > 0:
                    self.stats["total_uptime_seconds"] += time_diff
                    self.stats["daily_stats"][date_str]["uptime_seconds"] += time_diff

        # Update last status
        self.stats["daily_stats"][date_str]["last_status"] = is_online
        self.stats["last_updated"] = timestamp.isoformat()
        self._save_stats()

    def get_daily_summary(self, date_str: Optional[str] = None) -> Dict:
        """Get summary statistics for a specific day"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if date_str not in self.stats["daily_stats"]:
            return {
                "date": date_str,
                "uptime_seconds": 0,
                "downtime_seconds": 0,
                "downtime_events": 0,
                "availability_percent": 100.0,
                "status": "No data"
            }

        daily_stats = self.stats["daily_stats"][date_str]
        total_seconds = daily_stats["uptime_seconds"] + daily_stats["downtime_seconds"]
        availability = 100.0
        if total_seconds > 0:
            availability = (daily_stats["uptime_seconds"] / total_seconds) * 100

        return {
            "date": date_str,
            "uptime_seconds": daily_stats["uptime_seconds"],
            "uptime_formatted": self._format_duration(daily_stats["uptime_seconds"]),
            "downtime_seconds": daily_stats["downtime_seconds"],
            "downtime_formatted": self._format_duration(daily_stats["downtime_seconds"]),
            "downtime_events": daily_stats["downtime_events"],
            "availability_percent": round(availability, 2),
            "status": "Online" if daily_stats["last_status"] else "Offline"
        }

    def get_weekly_summary(self) -> Dict:
        """Get summary statistics for the past 7 days"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)

        total_uptime = 0
        total_downtime = 0
        total_events = 0
        days_with_data = 0
        daily_summaries = []

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            summary = self.get_daily_summary(date_str)

            if summary["uptime_seconds"] > 0 or summary["downtime_seconds"] > 0:
                days_with_data += 1
                total_uptime += summary["uptime_seconds"]
                total_downtime += summary["downtime_seconds"]
                total_events += summary["downtime_events"]

            daily_summaries.append(summary)
            current_date += timedelta(days=1)

        total_time = total_uptime + total_downtime
        availability = 100.0
        if total_time > 0:
            availability = (total_uptime / total_time) * 100

        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "days_with_data": days_with_data,
            "total_uptime_seconds": total_uptime,
            "total_uptime_formatted": self._format_duration(total_uptime),
            "total_downtime_seconds": total_downtime,
            "total_downtime_formatted": self._format_duration(total_downtime),
            "total_downtime_events": total_events,
            "availability_percent": round(availability, 2),
            "daily_summaries": daily_summaries
        }

    def get_overall_summary(self) -> Dict:
        """Get overall statistics since tracking began"""
        total_time = self.stats["total_uptime_seconds"] + self.stats["total_downtime_seconds"]
        availability = 100.0
        if total_time > 0:
            availability = (self.stats["total_uptime_seconds"] / total_time) * 100

        return {
            "since": datetime.fromisoformat(self.stats["service_started"]).strftime("%Y-%m-%d %H:%M:%S"),
            "total_uptime_seconds": self.stats["total_uptime_seconds"],
            "total_uptime_formatted": self._format_duration(self.stats["total_uptime_seconds"]),
            "total_downtime_seconds": self.stats["total_downtime_seconds"],
            "total_downtime_formatted": self._format_duration(self.stats["total_downtime_seconds"]),
            "total_downtime_events": len(self.stats["downtime_events"]),
            "availability_percent": round(availability, 2),
            "current_status": "Online" if self.current_downtime_start is None else "Offline"
        }

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into a human-readable duration string"""
        if seconds < 60:
            return f"{int(seconds)} seconds"

        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 and days == 0:  # Only show seconds if less than a day
            parts.append(f"{seconds}s")

        return " ".join(parts)

# Initialize stats tracker
stats_tracker = StatsTracker()

# System metrics collection
class SystemMonitor:
    @staticmethod
    async def get_system_metrics() -> Dict[str, Any]:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        virtual_memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        metrics = {
            "cpu": {
                "usage": cpu_usage,
                "cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False)
            },
            "memory": {
                "total": virtual_memory.total / (1024 ** 3),
                "used": virtual_memory.used / (1024 ** 3),
                "percent": virtual_memory.percent
            },
            "disk": {
                "total": disk.total / (1024 ** 3),
                "used": disk.used / (1024 ** 3),
                "percent": disk.percent
            },
            "system": {
                "platform": platform.system(),
                "version": platform.version(),
                "machine": platform.machine(),
                "hostname": platform.node(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
                "uptime": str(timedelta(seconds=int(time.time() - psutil.boot_time())))
            },
            "network": {
                "connections": len(psutil.net_connections())
            },
            "processes": {
                "count": len(psutil.pids())
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return metrics

# API client
class ServiceClient:
    @staticmethod
    async def check_health() -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(HEALTH_CHECK_URL, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"Status code: {response.status}"}
            except aiohttp.ClientError as e:
                return {"error": f"Connection error: {str(e)}"}
            except asyncio.TimeoutError:
                return {"error": "Request timed out"}

# Message formatter
class MessageFormatter:
    @staticmethod
    def format_status_message(service_data: Dict[str, Any], system_data: Dict[str, Any]) -> str:
        if "error" in service_data:
            service_status = f"⚠️ <b>Service Unavailable</b>: <code>{escape_html(service_data['error'])}</code>"
        else:
            timestamp = escape_html(service_data.get("timestamp", "Unknown"))
            uptime = round(service_data.get("uptime", 0) / 60, 2)
            environment = escape_html(service_data.get("environment", "Unknown"))

            memory = service_data.get("memoryUsage", {})
            rss = escape_html(memory.get("rss", "Unknown"))
            heap_total = escape_html(memory.get("heapTotal", "Unknown"))
            heap_used = escape_html(memory.get("heapUsed", "Unknown"))

            service_status = (
                f"<b>🟢 Service Status</b>\n"
                f"<b>Time</b>: <code>{timestamp}</code>\n"
                f"<b>Uptime</b>: <code>{uptime} minutes</code>\n"
                f"<b>Environment</b>: <code>{environment}</code>\n\n"
                f"<b>Memory Usage</b>:\n"
                f"  - RSS: <code>{rss}</code>\n"
                f"  - Heap Total: <code>{heap_total}</code>\n"
                f"  - Heap Used: <code>{heap_used}</code>\n"
            )

        hostname = escape_html(system_data['system']['hostname'])
        platform_info = escape_html(f"{system_data['system']['platform']} {system_data['system']['machine']}")
        uptime_info = escape_html(system_data['system']['uptime'])

        system_status = (
            f"<b>🖥️ System Status</b> (<code>{hostname}</code>)\n"
            f"<b>Platform</b>: <code>{platform_info}</code>\n"
            f"<b>Uptime</b>: <code>{uptime_info}</code>\n\n"
            f"<b>CPU Usage</b>: <code>{system_data['cpu']['usage']}%</code> ({system_data['cpu']['physical_cores']}/{system_data['cpu']['cores']} cores)\n"
            f"<b>Memory</b>: <code>{system_data['memory']['used']:.2f}GB/{system_data['memory']['total']:.2f}GB</code> ({system_data['memory']['percent']}%)\n"
            f"<b>Disk</b>: <code>{system_data['disk']['used']:.2f}GB/{system_data['disk']['total']:.2f}GB</code> ({system_data['disk']['percent']}%)\n"
            f"<b>Processes</b>: <code>{system_data['processes']['count']}</code>\n"
            f"<b>Network Connections</b>: <code>{system_data['network']['connections']}</code>\n"
            f"<b>Time</b>: <code>{escape_html(system_data['timestamp'])}</code>"
        )

        return f"{service_status}\n\n{system_status}"

    @staticmethod
    def format_admin_tags() -> str:
        """Format admin usernames as tags for notifications"""
        return " ".join([f"@{username}" for username in ADMIN_USERNAMES if username])

    @staticmethod
    def format_daily_stats(daily_stats: Dict) -> str:
        """Format daily statistics for display"""
        status_emoji = "🟢" if daily_stats["status"] == "Online" else "🔴"

        return (
            f"<b>📊 Daily Statistics: {daily_stats['date']}</b>\n\n"
            f"<b>Current Status</b>: {status_emoji} <code>{daily_stats['status']}</code>\n"
            f"<b>Availability</b>: <code>{daily_stats['availability_percent']}%</code>\n"
            f"<b>Uptime</b>: <code>{daily_stats['uptime_formatted']}</code>\n"
            f"<b>Downtime</b>: <code>{daily_stats['downtime_formatted']}</code>\n"
            f"<b>Outages</b>: <code>{daily_stats['downtime_events']} events</code>\n"
        )

    @staticmethod
    def format_weekly_stats(weekly_stats: Dict) -> str:
        """Format weekly statistics for display"""
        return (
            f"<b>📈 Weekly Statistics Summary</b>\n"
            f"<b>Period</b>: <code>{weekly_stats['period']}</code>\n\n"
            f"<b>Overall Availability</b>: <code>{weekly_stats['availability_percent']}%</code>\n"
            f"<b>Total Uptime</b>: <code>{weekly_stats['total_uptime_formatted']}</code>\n"
            f"<b>Total Downtime</b>: <code>{weekly_stats['total_downtime_formatted']}</code>\n"
            f"<b>Total Outages</b>: <code>{weekly_stats['total_downtime_events']} events</code>\n\n"
            f"<b>Daily Breakdown</b>:\n" +
            "\n".join([
                f"- {s['date']}: {s['availability_percent']}% available, {s['downtime_events']} outages"
                for s in weekly_stats['daily_summaries'] if s['uptime_seconds'] > 0 or s['downtime_seconds'] > 0
            ])
        )

    @staticmethod
    def format_overall_stats(overall_stats: Dict) -> str:
        """Format overall statistics for display"""
        status_emoji = "🟢" if overall_stats["current_status"] == "Online" else "🔴"

        return (
            f"<b>📊 Overall Service Statistics</b>\n"
            f"<b>Tracking Since</b>: <code>{overall_stats['since']}</code>\n"
            f"<b>Current Status</b>: {status_emoji} <code>{overall_stats['current_status']}</code>\n\n"
            f"<b>Overall Availability</b>: <code>{overall_stats['availability_percent']}%</code>\n"
            f"<b>Total Uptime</b>: <code>{overall_stats['total_uptime_formatted']}</code>\n"
            f"<b>Total Downtime</b>: <code>{overall_stats['total_downtime_formatted']}</code>\n"
            f"<b>Total Outages</b>: <code>{overall_stats['total_downtime_events']} events</code>\n"
        )

# Command handlers
@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = (
        "🤖 <b>Available Commands</b>:\n\n"
        "🔹 <code>/check</code> - Check server status\n"
        "🔹 <code>/system</code> - System information only\n"
        "🔹 <code>/service</code> - Service information only\n"
        "🔹 <code>/stats</code> - Show service statistics\n"
        "🔹 <code>/daily</code> - Show today's statistics\n"
        "🔹 <code>/weekly</code> - Show weekly statistics\n"
        "🔹 <code>/help</code> - Show this help message\n"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Check Status", callback_data="check_status")
    keyboard.button(text="System Info", callback_data="system_info")
    keyboard.button(text="Statistics", callback_data="show_stats")

    await message.answer(help_text, reply_markup=keyboard.as_markup())

@dp.message(Command("check"))
async def check_command(message: types.Message):
    await message.answer("⏳ Checking status...")

    try:
        system_data = await SystemMonitor.get_system_metrics()
        service_data = await ServiceClient.check_health()

        status_message = MessageFormatter.format_status_message(service_data, system_data)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="refresh_status")

        await message.answer(status_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error checking status: {str(e)}",
            parse_mode=None
        )

@dp.message(Command("system"))
async def system_command(message: types.Message):
    await message.answer("⏳ Collecting system information...")

    try:
        system_data = await SystemMonitor.get_system_metrics()

        hostname = escape_html(system_data['system']['hostname'])
        platform_info = escape_html(f"{system_data['system']['platform']} {system_data['system']['machine']}")
        version_info = escape_html(system_data['system']['version'])
        boot_time = escape_html(system_data['system']['boot_time'])
        uptime_info = escape_html(system_data['system']['uptime'])
        timestamp = escape_html(system_data['timestamp'])

        system_status = (
            f"<b>🖥️ System Status</b> (<code>{hostname}</code>)\n"
            f"<b>Platform</b>: <code>{platform_info}</code>\n"
            f"<b>Version</b>: <code>{version_info}</code>\n"
            f"<b>Boot Time</b>: <code>{boot_time}</code>\n"
            f"<b>Uptime</b>: <code>{uptime_info}</code>\n\n"
            f"<b>CPU Usage</b>: <code>{system_data['cpu']['usage']}%</code> ({system_data['cpu']['physical_cores']}/{system_data['cpu']['cores']} cores)\n"
            f"<b>Memory</b>: <code>{system_data['memory']['used']:.2f}GB/{system_data['memory']['total']:.2f}GB</code> ({system_data['memory']['percent']}%)\n"
            f"<b>Disk</b>: <code>{system_data['disk']['used']:.2f}GB/{system_data['disk']['total']:.2f}GB</code> ({system_data['disk']['percent']}%)\n"
            f"<b>Processes</b>: <code>{system_data['processes']['count']}</code>\n"
            f"<b>Network Connections</b>: <code>{system_data['network']['connections']}</code>\n"
            f"<b>Time</b>: <code>{timestamp}</code>"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh System Info", callback_data="refresh_system")

        await message.answer(system_status, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error collecting system information: {str(e)}",
            parse_mode=None
        )

@dp.message(Command("service"))
async def service_command(message: types.Message):
    await message.answer("⏳ Checking service status...")

    try:
        service_data = await ServiceClient.check_health()

        if "error" in service_data:
            service_status = f"⚠️ <b>Service Unavailable</b>: <code>{escape_html(service_data['error'])}</code>"
        else:
            timestamp = escape_html(service_data.get("timestamp", "Unknown"))
            uptime = round(service_data.get("uptime", 0) / 60, 2)
            environment = escape_html(service_data.get("environment", "Unknown"))

            memory = service_data.get("memoryUsage", {})
            rss = escape_html(memory.get("rss", "Unknown"))
            heap_total = escape_html(memory.get("heapTotal", "Unknown"))
            heap_used = escape_html(memory.get("heapUsed", "Unknown"))

            service_status = (
                f"<b>🟢 Service Status</b>\n"
                f"<b>Time</b>: <code>{timestamp}</code>\n"
                f"<b>Uptime</b>: <code>{uptime} minutes</code>\n"
                f"<b>Environment</b>: <code>{environment}</code>\n\n"
                f"<b>Memory Usage</b>:\n"
                f"  - RSS: <code>{rss}</code>\n"
                f"  - Heap Total: <code>{heap_total}</code>\n"
                f"  - Heap Used: <code>{heap_used}</code>\n"
            )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh Service", callback_data="refresh_service")

        await message.answer(service_status, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error checking service status: {str(e)}",
            parse_mode=None
        )

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await message.answer("⏳ Generating statistics...")

    try:
        overall_stats = stats_tracker.get_overall_summary()
        stats_message = MessageFormatter.format_overall_stats(overall_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Daily Stats", callback_data="daily_stats")
        keyboard.button(text="Weekly Stats", callback_data="weekly_stats")

        await message.answer(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error generating statistics: {str(e)}",
            parse_mode=None
        )

@dp.message(Command("daily"))
async def daily_stats_command(message: types.Message):
    await message.answer("⏳ Generating daily statistics...")

    try:
        daily_stats = stats_tracker.get_daily_summary()
        stats_message = MessageFormatter.format_daily_stats(daily_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="daily_stats")
        keyboard.button(text="Weekly Stats", callback_data="weekly_stats")

        await message.answer(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error generating daily statistics: {str(e)}",
            parse_mode=None
        )

@dp.message(Command("weekly"))
async def weekly_stats_command(message: types.Message):
    await message.answer("⏳ Generating weekly statistics...")

    try:
        weekly_stats = stats_tracker.get_weekly_summary()
        stats_message = MessageFormatter.format_weekly_stats(weekly_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="weekly_stats")
        keyboard.button(text="Daily Stats", callback_data="daily_stats")

        await message.answer(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await message.answer(
            f"⚠️ Error generating weekly statistics: {str(e)}",
            parse_mode=None
        )

# Callback query handlers
@dp.callback_query(F.data == "check_status")
async def check_status_callback(callback: types.CallbackQuery):
    await callback.answer("Checking status...")

    try:
        system_data = await SystemMonitor.get_system_metrics()
        service_data = await ServiceClient.check_health()

        status_message = MessageFormatter.format_status_message(service_data, system_data)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="refresh_status")

        await callback.message.edit_text(status_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error checking status: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "refresh_status")
async def refresh_status_callback(callback: types.CallbackQuery):
    await callback.answer("Refreshing status...")

    try:
        system_data = await SystemMonitor.get_system_metrics()
        service_data = await ServiceClient.check_health()

        status_message = MessageFormatter.format_status_message(service_data, system_data)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="refresh_status")

        await callback.message.edit_text(status_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error refreshing status: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "system_info")
async def system_info_callback(callback: types.CallbackQuery):
    await callback.answer("Getting system info...")

    try:
        system_data = await SystemMonitor.get_system_metrics()

        hostname = escape_html(system_data['system']['hostname'])
        platform_info = escape_html(f"{system_data['system']['platform']} {system_data['system']['machine']}")
        version_info = escape_html(system_data['system']['version'])
        boot_time = escape_html(system_data['system']['boot_time'])
        uptime_info = escape_html(system_data['system']['uptime'])
        timestamp = escape_html(system_data['timestamp'])

        system_status = (
            f"<b>🖥️ System Status</b> (<code>{hostname}</code>)\n"
            f"<b>Platform</b>: <code>{platform_info}</code>\n"
            f"<b>Version</b>: <code>{version_info}</code>\n"
            f"<b>Boot Time</b>: <code>{boot_time}</code>\n"
            f"<b>Uptime</b>: <code>{uptime_info}</code>\n\n"
            f"<b>CPU Usage</b>: <code>{system_data['cpu']['usage']}%</code> ({system_data['cpu']['physical_cores']}/{system_data['cpu']['cores']} cores)\n"
            f"<b>Memory</b>: <code>{system_data['memory']['used']:.2f}GB/{system_data['memory']['total']:.2f}GB</code> ({system_data['memory']['percent']}%)\n"
            f"<b>Disk</b>: <code>{system_data['disk']['used']:.2f}GB/{system_data['disk']['total']:.2f}GB</code> ({system_data['disk']['percent']}%)\n"
            f"<b>Processes</b>: <code>{system_data['processes']['count']}</code>\n"
            f"<b>Network Connections</b>: <code>{system_data['network']['connections']}</code>\n"
            f"<b>Time</b>: <code>{timestamp}</code>"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh System Info", callback_data="refresh_system")

        await callback.message.edit_text(system_status, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error getting system info: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "refresh_system")
async def refresh_system_callback(callback: types.CallbackQuery):
    await callback.answer("Refreshing system info...")

    try:
        system_data = await SystemMonitor.get_system_metrics()

        hostname = escape_html(system_data['system']['hostname'])
        platform_info = escape_html(f"{system_data['system']['platform']} {system_data['system']['machine']}")
        version_info = escape_html(system_data['system']['version'])
        boot_time = escape_html(system_data['system']['boot_time'])
        uptime_info = escape_html(system_data['system']['uptime'])
        timestamp = escape_html(system_data['timestamp'])

        system_status = (
            f"<b>🖥️ System Status</b> (<code>{hostname}</code>)\n"
            f"<b>Platform</b>: <code>{platform_info}</code>\n"
            f"<b>Version</b>: <code>{version_info}</code>\n"
            f"<b>Boot Time</b>: <code>{boot_time}</code>\n"
            f"<b>Uptime</b>: <code>{uptime_info}</code>\n\n"
            f"<b>CPU Usage</b>: <code>{system_data['cpu']['usage']}%</code> ({system_data['cpu']['physical_cores']}/{system_data['cpu']['cores']} cores)\n"
            f"<b>Memory</b>: <code>{system_data['memory']['used']:.2f}GB/{system_data['memory']['total']:.2f}GB</code> ({system_data['memory']['percent']}%)\n"
            f"<b>Disk</b>: <code>{system_data['disk']['used']:.2f}GB/{system_data['disk']['total']:.2f}GB</code> ({system_data['disk']['percent']}%)\n"
            f"<b>Processes</b>: <code>{system_data['processes']['count']}</code>\n"
            f"<b>Network Connections</b>: <code>{system_data['network']['connections']}</code>\n"
            f"<b>Time</b>: <code>{timestamp}</code>"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh System Info", callback_data="refresh_system")

        await callback.message.edit_text(system_status, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error refreshing system info: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "refresh_service")
async def refresh_service_callback(callback: types.CallbackQuery):
    await callback.answer("Refreshing service status...")

    try:
        service_data = await ServiceClient.check_health()

        if "error" in service_data:
            service_status = f"⚠️ <b>Service Unavailable</b>: <code>{escape_html(service_data['error'])}</code>"
        else:
            timestamp = escape_html(service_data.get("timestamp", "Unknown"))
            uptime = round(service_data.get("uptime", 0) / 60, 2)
            environment = escape_html(service_data.get("environment", "Unknown"))

            memory = service_data.get("memoryUsage", {})
            rss = escape_html(memory.get("rss", "Unknown"))
            heap_total = escape_html(memory.get("heapTotal", "Unknown"))
            heap_used = escape_html(memory.get("heapUsed", "Unknown"))

            service_status = (
                f"<b>🟢 Service Status</b>\n"
                f"<b>Time</b>: <code>{timestamp}</code>\n"
                f"<b>Uptime</b>: <code>{uptime} minutes</code>\n"
                f"<b>Environment</b>: <code>{environment}</code>\n\n"
                f"<b>Memory Usage</b>:\n"
                f"  - RSS: <code>{rss}</code>\n"
                f"  - Heap Total: <code>{heap_total}</code>\n"
                f"  - Heap Used: <code>{heap_used}</code>\n"
            )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh Service", callback_data="refresh_service")

        await callback.message.edit_text(service_status, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error refreshing service status: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: types.CallbackQuery):
    await callback.answer("Loading statistics...")

    try:
        overall_stats = stats_tracker.get_overall_summary()
        stats_message = MessageFormatter.format_overall_stats(overall_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Daily Stats", callback_data="daily_stats")
        keyboard.button(text="Weekly Stats", callback_data="weekly_stats")

        await callback.message.edit_text(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error loading statistics: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "daily_stats")
async def daily_stats_callback(callback: types.CallbackQuery):
    await callback.answer("Loading daily statistics...")

    try:
        daily_stats = stats_tracker.get_daily_summary()
        stats_message = MessageFormatter.format_daily_stats(daily_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="daily_stats")
        keyboard.button(text="Weekly Stats", callback_data="weekly_stats")
        keyboard.button(text="Overall Stats", callback_data="show_stats")

        await callback.message.edit_text(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error loading daily statistics: {str(e)}",
            parse_mode=None
        )

@dp.callback_query(F.data == "weekly_stats")
async def weekly_stats_callback(callback: types.CallbackQuery):
    await callback.answer("Loading weekly statistics...")

    try:
        weekly_stats = stats_tracker.get_weekly_summary()
        stats_message = MessageFormatter.format_weekly_stats(weekly_stats)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Refresh", callback_data="weekly_stats")
        keyboard.button(text="Daily Stats", callback_data="daily_stats")
        keyboard.button(text="Overall Stats", callback_data="show_stats")

        await callback.message.edit_text(stats_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Send error without any parsing mode to avoid formatting issues
        await callback.message.reply(
            f"⚠️ Error loading weekly statistics: {str(e)}",
            parse_mode=None
        )

# Track the last time we sent a status update
last_status_update = datetime.now() - timedelta(minutes=10)  # Initialize to ensure first update runs
last_alert_time = {}  # Dictionary to track when each type of alert was last sent
service_status_history = {"is_online": None}  # Track service status for recovery notifications
last_stats_summary = datetime.now().replace(hour=0, minute=0, second=0)  # Last time we sent stats summary

# Automated monitoring
async def scheduled_check():
    global last_status_update
    global last_alert_time
    global service_status_history
    global last_stats_summary

    while True:
        try:
            current_time = datetime.now()
            system_data = await SystemMonitor.get_system_metrics()
            service_data = await ServiceClient.check_health()

            # Update service status in statistics tracker
            current_service_online = "error" not in service_data
            stats_tracker.update_service_status(current_service_online, current_time)

            # Check if there are critical issues to report
            critical_issues = []

            # CPU check - use average of multiple readings to avoid false alarms on spikes
            cpu_readings = []
            for _ in range(3):  # Take 3 readings
                cpu_readings.append(psutil.cpu_percent(interval=0.5))

            avg_cpu = sum(cpu_readings) / len(cpu_readings)
            if avg_cpu > CRITICAL_CPU_THRESHOLD:
                critical_issues.append(f"⚠️ <b>High CPU Usage</b>: {avg_cpu:.1f}%")

            # Memory check
            if system_data['memory']['percent'] > CRITICAL_MEMORY_THRESHOLD:
                critical_issues.append(f"⚠️ <b>High Memory Usage</b>: {system_data['memory']['percent']}%")

            # Disk check
            if system_data['disk']['percent'] > CRITICAL_DISK_THRESHOLD:
                critical_issues.append(f"⚠️ <b>Low Disk Space</b>: {system_data['disk']['percent']}%")

            # Handle service status change (offline to online)
            if service_status_history["is_online"] is False and current_service_online and RECOVERY_NOTIFICATION:
                recovery_message = (
                    f"✅ <b>SERVICE RECOVERED</b>\n\n"
                    f"The service is now back online! {MessageFormatter.format_admin_tags()}\n\n"
                    f"<b>Time</b>: <code>{escape_html(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</code>\n"
                    f"<b>Environment</b>: <code>{escape_html(service_data.get('environment', 'Unknown'))}</code>\n"
                    f"<b>Uptime</b>: <code>{round(service_data.get('uptime', 0) / 60, 2)} minutes</code>"
                )
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=recovery_message, message_thread_id=THREAD_ID)
                except TelegramAPIError as e:
                    print(f"Error sending recovery notification: {e}")

            # Update service status history
            service_status_history["is_online"] = current_service_online

            # Add service issue if offline
            if not current_service_online:
                critical_issues.append(f"⚠️ <b>Service Down</b>: {escape_html(service_data.get('error', 'Unknown error'))}")

            # Format the status message only if we need to send it
            status_message = None

            # If there are critical issues, send an alert
            if critical_issues:
                # Create a unique key for this set of issues
                issue_key = "|".join(sorted(critical_issues))

                # Send alert if we haven't sent one for these issues recently
                if issue_key not in last_alert_time or (current_time - last_alert_time[issue_key]).total_seconds() > ALERT_REPEAT_INTERVAL:
                    if status_message is None:
                        status_message = MessageFormatter.format_status_message(service_data, system_data)

                    # Add admin tags to the message
                    admin_tags = MessageFormatter.format_admin_tags()

                    alert_message = f"🚨 <b>SYSTEM ALERT</b> {admin_tags}\n\n" + "\n".join(critical_issues) + f"\n\n{status_message}"

                    try:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=alert_message,
                            message_thread_id=THREAD_ID
                        )
                        # Update the last alert time for this issue
                        last_alert_time[issue_key] = current_time
                    except TelegramAPIError as e:
                        print(f"Error sending alert: {e}")

            # Send regular status updates every CHECK_INTERVAL seconds (e.g., once per day)
            if (current_time - last_status_update).total_seconds() >= CHECK_INTERVAL:
                if status_message is None:
                    status_message = MessageFormatter.format_status_message(service_data, system_data)

                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="🔄 Refresh", callback_data="refresh_status")

                try:
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"📊 <b>Daily Status Update</b>\n\n{status_message}",
                        reply_markup=keyboard.as_markup(),
                        message_thread_id=THREAD_ID
                    )
                    last_status_update = current_time  # Update the timestamp
                except TelegramAPIError as e:
                    print(f"Error sending daily status update: {e}")

            # Send daily statistics summary at configured time
            if (current_time.hour == STATS_SUMMARY_HOUR and
                current_time.minute == STATS_SUMMARY_MINUTE and
                (current_time - last_stats_summary).total_seconds() > 3600):  # Ensure at least 1 hour since last summary

                # Get daily stats
                daily_stats = stats_tracker.get_daily_summary()
                stats_message = MessageFormatter.format_daily_stats(daily_stats)

                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="Weekly Stats", callback_data="weekly_stats")
                keyboard.button(text="Overall Stats", callback_data="show_stats")

                try:
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"📈 <b>Daily Statistics Summary</b>\n\n{stats_message}",
                        reply_markup=keyboard.as_markup(),
                        message_thread_id=THREAD_ID
                    )
                    last_stats_summary = current_time
                except TelegramAPIError as e:
                    print(f"Error sending daily statistics summary: {e}")

        except Exception as e:
            try:
                # Use plain text for error messages to avoid parsing issues
                error_message = f"⚠️ Monitoring Error: {str(e)}"
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=error_message,
                    message_thread_id=THREAD_ID,
                    parse_mode=None  # Explicitly disable parsing mode for error messages
                )
            except TelegramAPIError as telegram_error:
                # Log the error locally since we can't send to Telegram
                print(f"Failed to send error message: {telegram_error}")

        # Check more frequently (every MONITORING_INTERVAL seconds)
        await asyncio.sleep(MONITORING_INTERVAL)

# Legacy command handler (for backward compatibility)
@dp.message(Command("checkFincho"))
async def legacy_check_command(message: types.Message):
    await message.answer("ℹ️ This command has been renamed. Please use <code>/check</code> instead.")
    await check_command(message)

# Main function
async def main():
    # Start the monitoring task
    asyncio.create_task(scheduled_check())
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())