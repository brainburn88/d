import discord
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

TOKEN           = os.environ.get("DISCORD_TOKEN", "")
CUSTOM_STATUS   = os.environ.get("STATUS_TEXT",   "still here, somehow")
RPC_APP_NAME    = os.environ.get("RPC_APP_NAME",  "3am thoughts")
RPC_DETAILS     = os.environ.get("RPC_DETAILS",   "nothing's wrong")
RPC_STATE       = os.environ.get("RPC_STATE",     "nothing's right either — {elapsed}")
RPC_LARGE_IMAGE = os.environ.get("RPC_LARGE_IMAGE", "")
RPC_LARGE_TEXT  = os.environ.get("RPC_LARGE_TEXT",  "")
STATUS_PAGE_URL = os.environ.get("STATUS_PAGE_URL", "https://why-chi-rust.vercel.app/")
ONLINE_STATUS   = os.environ.get("ONLINE_STATUS", "online")
TZ_OFFSET       = int(os.environ.get("TZ_OFFSET", "3"))

if not TOKEN:
    print("❌ DISCORD_TOKEN not set!")
    exit(1)

start_time = datetime.now(timezone.utc)

def get_elapsed():
    delta = datetime.now(timezone.utc) - start_time
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    if h > 0: return f"{h}h {m}m"
    if m > 0: return f"{m}m {s}s"
    return f"{s}s"

def get_time():
    tz = timezone(timedelta(hours=TZ_OFFSET))
    return datetime.now(tz).strftime("%H:%M")

# tiny HTTP server for Render free tier
class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

threading.Thread(
    target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), _H).serve_forever(),
    daemon=True
).start()
print("🌐 HTTP server started")

class MyClient(discord.Client):
    async def setup_hook(self):
        print("🔧 setup_hook called — starting update loop")
        self.loop.create_task(self.update_loop())

    async def on_ready(self):
        print(f"✅ on_ready — logged in as {self.user}")

    async def on_connect(self):
        print("🔗 on_connect fired")

    async def update_loop(self):
        # wait a bit for connection to stabilize
        await asyncio.sleep(5)
        print("▶️  update_loop started")
        while True:
            try:
                await self.set_presence()
            except Exception as e:
                print(f"⚠️  Presence error: {e}")
            await asyncio.sleep(60)

    async def set_presence(self):
        t       = get_time()
        elapsed = get_elapsed()
        status_map = {
            "online": discord.Status.online,
            "idle":   discord.Status.idle,
            "dnd":    discord.Status.dnd,
        }
        status = status_map.get(ONLINE_STATUS, discord.Status.online)

        kwargs = dict(
            type       = discord.ActivityType.playing,
            name       = RPC_APP_NAME.format(time=t, elapsed=elapsed),
            details    = RPC_DETAILS.format(time=t, elapsed=elapsed),
            state      = RPC_STATE.format(time=t, elapsed=elapsed),
            timestamps = {"start": int(start_time.timestamp() * 1000)},
            buttons    = [{"label": "моё состояние", "url": STATUS_PAGE_URL}],
        )
        if RPC_LARGE_IMAGE: kwargs["large_image"] = RPC_LARGE_IMAGE
        if RPC_LARGE_TEXT:  kwargs["large_text"]  = RPC_LARGE_TEXT

        activity        = discord.Activity(**kwargs)
        custom_activity = discord.CustomActivity(
            name=CUSTOM_STATUS.format(time=t, elapsed=elapsed)
        )
        await self.change_presence(status=status, activities=[custom_activity, activity])
        print(f"🔄 [{t} MSK] Status updated — uptime {elapsed}")

client = MyClient()
client.run(TOKEN)
