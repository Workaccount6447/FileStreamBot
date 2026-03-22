import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers

from FileStream.config import Telegram, Server
from aiohttp import web
from pyrogram import idle

from FileStream.bot import FileStream
from FileStream.server import web_server
from FileStream.bot.clients import initialize_clients
import FileStream.utils.donate  # loads donate handlers

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        handlers.RotatingFileHandler(
            "streambot.log", mode="a",
            maxBytes=100 * 1024 * 1024,
            backupCount=2, encoding="utf-8",
        ),
    ],
)

for _noisy in ("aiohttp", "aiohttp.web", "pyrogram", "pyrogram.session.session"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

# ── uvloop (optional) ──────────────────────────────────────────────────────────
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logging.info("uvloop active")
except ImportError:
    logging.info("uvloop not found — using default asyncio")

# ── Create event loop explicitly — works with both uvloop and default asyncio ──
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

server = web.AppRunner(
    web_server(),
    access_log=None,
    tcp_keepalive=True,
    keepalive_timeout=75,
)


async def start_services():
    mode = "Secondary" if Telegram.SECONDARY else "Primary"
    print(f"\n--- Starting as {mode} Server ---\n")

    print("Initializing Telegram Bot...")
    await FileStream.start()
    bot_info = await FileStream.get_me()
    FileStream.id       = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname    = bot_info.first_name
    print("  Bot ready")

    print("Initializing clients...")
    await initialize_clients()
    print("  Clients ready")

    print("Starting web server...")
    await server.setup()
    await web.TCPSite(
        server,
        Server.BIND_ADDRESS,
        Server.PORT,
        reuse_address=True,
        # reuse_port removed — causes OSError on Koyeb if port not fully released
    ).start()
    print("  Web server ready")
    print(f"\n  Bot : {bot_info.first_name}")
    if bot_info.dc_id:
        print(f"  DC  : {bot_info.dc_id}")
    print(f"  URL : {Server.URL}\n")

    await idle()


async def cleanup():
    await server.cleanup()
    await FileStream.stop()


if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error(traceback.format_exc())
    finally:
        loop.run_until_complete(cleanup())
        loop.stop()
        print("Services stopped.")
