import asyncio
import logging
from typing import Dict, Optional
from .file_properties import get_file_ids

from pyrogram import Client, raw, utils
from pyrogram.errors import AuthBytesInvalid, FloodWait
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.session import Session
from pyrogram.session.auth import Auth
from pyrogram.types import Message

log = logging.getLogger(__name__)

# ─── Tuning constants ─────────────────────────────────────────────────────────
CHUNK_SIZE      = 1024 * 1024   # 1 MB — Telegram's maximum per GetFile request
PARALLEL_CHUNKS = 6             # concurrent Telegram requests per stream
BUFFER_AHEAD    = 8             # max chunks buffered ahead of consumer
GLOBAL_LIMIT    = 8             # max simultaneous streams across all clients
# ──────────────────────────────────────────────────────────────────────────────


class ByteStreamer:
    def __init__(self, client: Client):
        self.client = client

        # file-id cache  {db_id -> FileId}
        self.cached_file_ids: Dict[str, FileId] = {}
        # per-db_id lock to prevent double-fetch on concurrent first requests
        self._cache_locks: Dict[str, asyncio.Lock] = {}

        # per-DC session locks
        self._dc_locks: Dict[int, asyncio.Lock] = {}

        # cap total concurrent streams
        self._global_sem = asyncio.Semaphore(GLOBAL_LIMIT)

        # FIX: use get_running_loop() — safe inside async context, no DeprecationWarning
        asyncio.get_running_loop().create_task(self._cache_janitor())

    # ── cache maintenance ──────────────────────────────────────────────────────

    async def _cache_janitor(self):
        while True:
            await asyncio.sleep(30 * 60)
            self.cached_file_ids.clear()
            log.debug("File-id cache cleared")

    # ── file properties (race-safe) ────────────────────────────────────────────

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        # FIX: per-db_id lock prevents two concurrent requests both missing the
        # cache and making duplicate DB/Telegram calls for the same file.
        lock = self._cache_locks.setdefault(db_id, asyncio.Lock())
        async with lock:
            if db_id not in self.cached_file_ids:
                file_id = await get_file_ids(self.client, db_id, multi_clients, Message)
                self.cached_file_ids[db_id] = file_id
            return self.cached_file_ids[db_id]

    # ── Telegram media session ─────────────────────────────────────────────────

    async def _get_media_session(self, client: Client, file_id: FileId) -> Session:
        dc_id = file_id.dc_id
        lock  = self._dc_locks.setdefault(dc_id, asyncio.Lock())

        async with lock:
            session = client.media_sessions.get(dc_id)
            if session:
                return session

            home_dc = await client.storage.dc_id()

            if dc_id != home_dc:
                auth_key = await Auth(
                    client, dc_id, await client.storage.test_mode()
                ).create()
                session = Session(
                    client, dc_id, auth_key,
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await session.start()

                for attempt in range(6):
                    try:
                        exported = await client.invoke(
                            raw.functions.auth.ExportAuthorization(dc_id=dc_id)
                        )
                        await session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported.id, bytes=exported.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        if attempt == 5:
                            await session.stop()
                            raise
                        await asyncio.sleep(1)
            else:
                session = Session(
                    client, dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await session.start()

            client.media_sessions[dc_id] = session
            return session

    async def _drop_dc_session(self, client: Client, dc_id: int):
        session = client.media_sessions.pop(dc_id, None)
        if session:
            try:
                await session.stop()
            except Exception:
                pass

    # ── location builder ───────────────────────────────────────────────────────

    @staticmethod
    def _build_location(file_id: FileId):
        if file_id.file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id,
                    access_hash=file_id.chat_access_hash,
                )
            elif file_id.chat_access_hash == 0:
                peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
            else:
                peer = raw.types.InputPeerChannel(
                    channel_id=utils.get_channel_id(file_id.chat_id),
                    access_hash=file_id.chat_access_hash,
                )
            return raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_id.file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            return raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )

    # ── single chunk fetch ─────────────────────────────────────────────────────

    async def _fetch_chunk(
        self,
        client: Client,
        file_id: FileId,
        offset: int,
        chunk_size: int,
        db_id: Optional[str],
        multi_clients,
    ) -> Optional[bytes]:
        for attempt in range(6):
            try:
                session  = await self._get_media_session(client, file_id)
                location = self._build_location(file_id)

                # FIX: shield the invoke so a CancelledError from wait_for
                # doesn't leave the pyrogram session in a corrupted state.
                # The inner coroutine completes (or times out) cleanly.
                result = await asyncio.wait_for(
                    asyncio.shield(
                        session.invoke(
                            raw.functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=chunk_size,
                            )
                        )
                    ),
                    timeout=30,
                )

                if isinstance(result, raw.types.upload.File):
                    return result.bytes

                return None

            except asyncio.TimeoutError:
                # Timeout (not external cancel) — retry with backoff
                log.warning(f"Chunk timeout offset={offset} attempt={attempt+1}")
                await self._drop_dc_session(client, file_id.dc_id)
                await asyncio.sleep(2 ** attempt)

            except FloodWait as e:
                wait = e.value + 1
                log.warning(f"FloodWait {wait}s offset={offset}")
                await asyncio.sleep(wait)

            except asyncio.CancelledError:
                # External cancel (client disconnected) — propagate immediately
                raise

            except Exception as exc:
                if attempt >= 5:
                    log.error(f"Chunk permanently failed offset={offset}: {exc}")
                    return None

                backoff = 2 ** attempt
                log.warning(f"Chunk retry {attempt+1}/5 offset={offset}: {exc} (wait {backoff}s)")
                await self._drop_dc_session(client, file_id.dc_id)

                if db_id and multi_clients:
                    try:
                        file_id = await self.get_file_properties(db_id, multi_clients)
                    except Exception:
                        pass

                await asyncio.sleep(backoff)

        return None

    # ── streaming generator ────────────────────────────────────────────────────

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
        db_id: Optional[str] = None,
        multi_clients=None,
    ):
        """
        Async generator delivering file bytes to the HTTP response.

        Workers race ahead fetching chunks from Telegram in parallel.
        asyncio.Event per slot eliminates busy-spinning.
        The finally block always cancels + awaits every worker — this is what
        eliminates "Task was destroyed but it is pending!" entirely.
        """
        if part_count == 0:
            return

        client = multi_clients[index] if multi_clients else self.client

        # Track workload for load balancing
        if multi_clients and index in multi_clients:
            from FileStream.bot import work_loads
            work_loads[index] = work_loads.get(index, 0) + 1

        async with self._global_sem:
            workers:       list                      = []
            buffer:        Dict[int, Optional[bytes]] = {}
            ready_events:  Dict[int, asyncio.Event]   = {}
            next_part  = 0
            part_lock  = asyncio.Lock()
            # FIX: BoundedSemaphore raises ValueError on over-release,
            # making accidental over-releases visible instead of silently
            # inflating the counter.
            buffer_sem = asyncio.BoundedSemaphore(BUFFER_AHEAD)

            async def worker():
                nonlocal next_part
                while True:
                    async with part_lock:
                        part = next_part
                        next_part += 1

                    if part >= part_count:
                        return

                    await buffer_sem.acquire()

                    part_offset = offset + part * chunk_size
                    try:
                        data = await self._fetch_chunk(
                            client, file_id, part_offset, chunk_size,
                            db_id, multi_clients,
                        )
                    except asyncio.CancelledError:
                        # FIX: release the slot we acquired before being cancelled
                        # so the finally block's semaphore state stays consistent.
                        buffer_sem.release()
                        raise

                    buffer[part] = data
                    ready_events[part].set()

            try:
                # Create events lazily as we go to save memory on large files
                # FIX: don't pre-create all 3000+ events for a 3 GB file.
                # Instead create only BUFFER_AHEAD worth at a time.
                for p in range(min(BUFFER_AHEAD + PARALLEL_CHUNKS, part_count)):
                    ready_events[p] = asyncio.Event()
                # Remaining events created on-demand below

                workers = [
                    asyncio.create_task(worker())
                    for _ in range(min(PARALLEL_CHUNKS, part_count))
                ]

                for current in range(part_count):
                    # Ensure the event for this slot exists
                    if current not in ready_events:
                        ready_events[current] = asyncio.Event()

                    # Pre-create the event for a future slot too
                    future = current + BUFFER_AHEAD + PARALLEL_CHUNKS
                    if future < part_count and future not in ready_events:
                        ready_events[future] = asyncio.Event()

                    await ready_events[current].wait()
                    ready_events.pop(current)   # free memory as we go

                    chunk = buffer.pop(current, None)
                    buffer_sem.release()

                    if chunk is None:
                        log.error(f"Chunk {current} fetch failed — aborting stream")
                        return

                    if part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current == 0:
                        yield chunk[first_part_cut:]
                    elif current == part_count - 1:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

            except asyncio.CancelledError:
                log.debug("Stream cancelled — client disconnected")
                raise

            finally:
                # ── CRITICAL: cancel every worker then await all of them ──────
                # This is what prevents "Task was destroyed but it is pending!"
                for w in workers:
                    if not w.done():
                        w.cancel()
                if workers:
                    await asyncio.gather(*workers, return_exceptions=True)

                # Decrement workload counter
                if multi_clients and index in multi_clients:
                    from FileStream.bot import work_loads
                    work_loads[index] = max(0, work_loads.get(index, 1) - 1)
