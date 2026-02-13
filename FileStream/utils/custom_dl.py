import asyncio
import logging
import socket
from typing import Dict, Union

from FileStream.bot import work_loads
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.types import Message

socket.setdefaulttimeout(30)


class ByteStreamer:
    def __init__(self, client: Client):
        self.client: Client = client
        self.clean_timer = 30 * 60
        self.cached_file_ids: Dict[str, FileId] = {}

        self.global_semaphore = asyncio.Semaphore(4)
        self.parallel_workers = 3
        self.max_buffer = 6  # prevents RAM overflow

        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        if db_id not in self.cached_file_ids:
            file_id = await get_file_ids(self.client, db_id, multi_clients, Message)
            self.cached_file_ids[db_id] = file_id
        return self.cached_file_ids[db_id]

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        media_session = client.media_sessions.get(file_id.dc_id)

        if media_session:
            return media_session

        if file_id.dc_id != await client.storage.dc_id():
            media_session = Session(
                client,
                file_id.dc_id,
                await Auth(client, file_id.dc_id, await client.storage.test_mode()).create(),
                await client.storage.test_mode(),
                is_media=True,
            )
            await media_session.start()

            for _ in range(6):
                exported_auth = await client.invoke(
                    raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id)
                )
                try:
                    await media_session.invoke(
                        raw.functions.auth.ImportAuthorization(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )
                    break
                except AuthBytesInvalid:
                    await asyncio.sleep(1)
            else:
                await media_session.stop()
                raise AuthBytesInvalid

        else:
            media_session = Session(
                client,
                file_id.dc_id,
                await client.storage.auth_key(),
                await client.storage.test_mode(),
                is_media=True,
            )
            await media_session.start()

        client.media_sessions[file_id.dc_id] = media_session
        return media_session

    async def close_dc(self, dc_id: int):
        session = self.client.media_sessions.pop(dc_id, None)
        if session:
            try:
                await session.stop()
            except:
                pass

    @staticmethod
    async def get_location(file_id: FileId):
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id,
                    access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
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

        elif file_type == FileType.PHOTO:
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

    async def fetch_chunk(self, file_id, offset, chunk_size, db_id, multi_clients):
        retries = 0
        MAX_RETRIES = 6
        BASE_DELAY = 2

        while True:
            try:
                session = await self.generate_media_session(self.client, file_id)
                location = await self.get_location(file_id)

                r = await asyncio.wait_for(
                    session.invoke(
                        raw.functions.upload.GetFile(
                            location=location,
                            offset=offset,
                            limit=chunk_size
                        )
                    ),
                    timeout=30
                )

                if not isinstance(r, raw.types.upload.File):
                    return None

                return r.bytes

            except Exception as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    logging.error(f"Chunk failed permanently: {e}")
                    return None

                wait = BASE_DELAY * (2 ** retries)
                logging.warning(f"Chunk retry {retries}: {e}")

                await self.close_dc(file_id.dc_id)

                if db_id and multi_clients:
                    try:
                        file_id = await self.get_file_properties(db_id, multi_clients)
                    except:
                        pass

                await asyncio.sleep(wait)

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
        db_id=None,
        multi_clients=None
    ):

        async with self.global_semaphore:

            work_loads[index] += 1

            try:
                next_part = 0
                current = 0
                buffer = {}
                lock = asyncio.Lock()
                buffer_sem = asyncio.Semaphore(self.max_buffer)

                async def worker():
                    nonlocal next_part

                    while True:
                        async with lock:
                            part = next_part
                            next_part += 1

                        if part >= part_count:
                            return

                        await buffer_sem.acquire()

                        part_offset = offset + part * chunk_size
                        data = await self.fetch_chunk(
                            file_id,
                            part_offset,
                            chunk_size,
                            db_id,
                            multi_clients
                        )

                        buffer[part] = data

                workers = [
                    asyncio.create_task(worker())
                    for _ in range(self.parallel_workers)
                ]

                while current < part_count:

                    if current not in buffer:
                        await asyncio.sleep(0.0005)
                        continue

                    chunk = buffer.pop(current)
                    buffer_sem.release()

                    if chunk is None:
                        return

                    if part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current == 0:
                        yield chunk[first_part_cut:]
                    elif current == part_count - 1:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

                    current += 1

                await asyncio.gather(*workers)

            finally:
                work_loads[index] -= 1

    async def clean_cache(self):
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("File cache cleared")