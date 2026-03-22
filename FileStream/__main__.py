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

# ── uvloop (optional, ~30-40% throughput boost) ────────────────────────────────
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logging.info("uvloop active")
except ImportError:
    logging.info("uvloop not found — using default asyncio (pip install uvloop for better speed)")


async def start_services():
    mode = "Secondary" if Telegram.SECONDARY else "Primary"
    print(f"\n{'─'*18} Starting as {mode} Server {'─'*18}\n")

    print("Initializing Telegram Bot…")
    await FileStream.start()
    bot_info = await FileStream.get_me()
    FileStream.id       = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname    = bot_info.first_name
    print("  ✓ Bot ready")

    print("Initializing clients…")
    await initialize_clients()
    print("  ✓ Clients ready")

    print("Starting web server…")
    app    = web_server()
    runner = web.AppRunner(
        app,
        access_log=None,
        tcp_keepalive=True,
        keepalive_timeout=75,
    )
    await runner.setup()
    site = web.TCPSite(
        runner,
        Server.BIND_ADDRESS,
        Server.PORT,
        reuse_address=True,
        reuse_port=True,    # SO_REUSEPORT — better multi-core distribution (Linux only)
    )
    await site.start()
    print("  ✓ Web server ready")
    print(f"\n  Bot : {bot_info.first_name}")
    if bot_info.dc_id:
        print(f"  DC  : {bot_info.dc_id}")
    print(f"  URL : {Server.URL}\n")

    await idle()

    # Graceful shutdown
    await runner.cleanup()
    await FileStream.stop()


if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error(traceback.format_exc())
    finally:
        print("Services stopped.")
