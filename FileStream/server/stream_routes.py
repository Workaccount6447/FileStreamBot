import time
import math
import logging
import mimetypes
import traceback
from urllib.parse import quote
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from FileStream.bot import multi_clients, work_loads, FileStream
from FileStream.config import Telegram, Server
from FileStream.server.exceptions import FIleNotFound, InvalidHash
from FileStream import utils, StartTime, __version__
from FileStream.utils.render_template import render_page
from FileStream.utils.custom_dl import CHUNK_SIZE

routes = web.RouteTableDef()
log    = logging.getLogger(__name__)

# One ByteStreamer per Telegram client object
class_cache = {}


@routes.get("/status", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": utils.get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + FileStream.username,
            "connected_bots": len(multi_clients),
            "loads": {
                "bot" + str(c + 1): l
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            },
            "version": __version__,
        }
    )


@routes.get("/watch/{path}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        return web.Response(text=await render_page(path), content_type="text/html")
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass


@routes.get("/dl/{path}", allow_head=True)
async def dl_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        return await media_streamer(request, path)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        log.critical(e, exc_info=True)
        raise web.HTTPInternalServerError(text=str(e))


async def media_streamer(request: web.Request, db_id: str):
    range_header = request.headers.get("Range", "")

    # FIX: work_loads is now properly updated by yield_file, so this
    # correctly picks the least-busy client instead of always picking the same one.
    index         = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if Telegram.MULTI_CLIENT:
        log.info(f"Client {index} serving {request.headers.get('X-Forwarded-For', request.remote)}")

    if faster_client not in class_cache:
        class_cache[faster_client] = utils.ByteStreamer(faster_client)
    tg_connect = class_cache[faster_client]

    file_id   = await tg_connect.get_file_properties(db_id, multi_clients)
    file_size = file_id.file_size

    # ── Range parsing ──────────────────────────────────────────────────────────
    if range_header:
        try:
            raw_range           = range_header.replace("bytes=", "")
            start_str, end_str  = raw_range.split("-", 1)
            from_bytes          = int(start_str)
            until_bytes         = int(end_str) if end_str else file_size - 1
        except ValueError:
            return web.Response(
                status=416,
                body="416: Invalid Range header",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
    else:
        from_bytes  = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    until_bytes = min(until_bytes, file_size - 1)

    if from_bytes < 0 or until_bytes < from_bytes:
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    # ── Chunk geometry ─────────────────────────────────────────────────────────
    chunk_size     = CHUNK_SIZE
    offset         = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut  = until_bytes % chunk_size + 1
    req_length     = until_bytes - from_bytes + 1
    part_count     = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)

    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut,
        part_count, chunk_size, db_id=db_id, multi_clients=multi_clients,
    )

    # ── MIME type ──────────────────────────────────────────────────────────────
    mime_type = file_id.mime_type
    file_name = utils.get_name(file_id)

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    # Inline for media so browsers/players start immediately without downloading
    disposition = "inline" if mime_type.startswith(("video/", "audio/")) else "attachment"

    # FIX: RFC 5987 encoding for non-ASCII filenames (Hindi, Arabic, CJK, etc.)
    # Without this, browsers silently drop or mangle non-ASCII names.
    try:
        file_name.encode("ascii")
        # Pure ASCII — simple form is fine
        cd = f'{disposition}; filename="{file_name}"'
    except UnicodeEncodeError:
        # Has non-ASCII — use RFC 5987 extended parameter
        encoded = quote(file_name, safe=" ()[]{}!#$&'*+,;=@~")
        cd = f"{disposition}; filename*=UTF-8''{encoded}"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type":              mime_type,
            "Content-Range":             f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length":            str(req_length),
            "Content-Disposition":       cd,
            "Accept-Ranges":             "bytes",
            "Cache-Control":             "no-store",
            "Connection":                "keep-alive",
        },
    )
