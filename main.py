import discord
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Custom status (shown under nickname)
CUSTOM_STATUS_TEXT = os.environ.get("STATUS_TEXT", "still here, somehow")

# RPC — shown as "Playing in..."
RPC_APP_NAME    = os.environ.get("RPC_APP_NAME",  "3am thoughts")
RPC_DETAILS     = os.environ.get("RPC_DETAILS",   "nothing's wrong")
RPC_STATE       = os.environ.get("RPC_STATE",     "nothing's right either — {elapsed}")

# Icon — set these after uploading an image to your Discord Application assets
# Go to discord.com/developers → your app → Rich Presence → Art Assets → upload image
# Then put the asset name (e.g. "moon") into RPC_LARGE_IMAGE
RPC_LARGE_IMAGE = os.environ.get("RPC_LARGE_IMAGE", "")   # asset name from Discord Dev Portal
RPC_LARGE_TEXT  = os.environ.get("RPC_LARGE_TEXT",  "")   # tooltip on hover (optional)
RPC_SMALL_IMAGE = os.environ.get("RPC_SMALL_IMAGE", "")   # small corner icon (optional)

# Discord Application ID (needed for icons to show)
# Create app at discord.com/developers/applications → copy Application ID
APP_ID          = os.environ.get("APP_ID", "")

# Button in RPC — links to your status page
STATUS_PAGE_URL = os.environ.get("STATUS_PAGE_URL", "https://why-chi-rust.vercel.app/")

# Online status: "online" / "idle" / "dnd" / "invisible"
ONLINE_STATUS   = os.environ.get("ONLINE_STATUS", "online")

# Timezone offset from UTC (3 = Moscow MSK)
TIMEZONE_OFFSET = int(os.environ.get("TZ_OFFSET", "3"))
# ─────────────────────────────────────────

start_time = datetime.now(timezone.utc)

def get_elapsed() -> str:
    """Сколько времени прошло с запуска"""
    delta = datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}ч {minutes}м"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"

def get_time() -> str:
    """Текущее время в нужном часовом поясе"""
    from datetime import timedelta
    tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
    return datetime.now(tz).strftime("%H:%M")


class SelfBot(discord.Client):
    def __init__(self):
        super().__init__(self_bot=True)
        self._update_task = None

    async def on_ready(self):
        print(f"✅ Залогинился как {self.user} (id: {self.user.id})")
        print(f"🕐 Старт: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self._update_task = self.loop.create_task(self.update_loop())

    async def update_loop(self):
        """Обновляем статус каждые 60 секунд"""
        while True:
            try:
                await self.update_presence()
            except Exception as e:
                print(f"⚠️  Ошибка обновления статуса: {e}")
            await asyncio.sleep(60)

    async def update_presence(self):
        current_time = get_time()
        elapsed = get_elapsed()

        custom_text = CUSTOM_STATUS_TEXT.format(time=current_time, elapsed=elapsed)
        rpc_state   = RPC_STATE.format(time=current_time, elapsed=elapsed)
        rpc_details = RPC_DETAILS.format(time=current_time, elapsed=elapsed)

        activity_kwargs = dict(
            type=discord.ActivityType.playing,
            name=RPC_APP_NAME.format(time=current_time, elapsed=elapsed),
            state=rpc_state,
            details=rpc_details,
            timestamps={"start": int(start_time.timestamp() * 1000)},
            buttons=[{"label": "моё состояние", "url": STATUS_PAGE_URL}] if STATUS_PAGE_URL else [],
        )

        # Add icons if configured
        if RPC_LARGE_IMAGE:
            activity_kwargs["large_image"] = RPC_LARGE_IMAGE
        if RPC_LARGE_TEXT:
            activity_kwargs["large_text"] = RPC_LARGE_TEXT
        if RPC_SMALL_IMAGE:
            activity_kwargs["small_image"] = RPC_SMALL_IMAGE

        activity = discord.Activity(**activity_kwargs)

        custom_activity = discord.CustomActivity(
            name=custom_text,
        )

        status_map = {
            "online":    discord.Status.online,
            "idle":      discord.Status.idle,
            "dnd":       discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        status = status_map.get(ONLINE_STATUS, discord.Status.online)

        await self.change_presence(
            status=status,
            activities=[custom_activity, activity],
        )
        print(f"🔄 [{current_time}] Статус обновлён — онлайн {elapsed}")


# Tiny HTTP server so Render Web Service stays happy (free tier)
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *args): pass

def _start_http():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()

threading.Thread(target=_start_http, daemon=True).start()

client = SelfBot()

if not TOKEN:
    print("❌ DISCORD_TOKEN не задан! Укажи его в переменных окружения Render.")
    exit(1)

client.run(TOKEN)
