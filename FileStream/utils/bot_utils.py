import asyncio
import logging
from typing import Dict, Union
from FileStream.bot import work_loads
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.types import Message


class ByteStreamer:
    def __init__(self, client: Client):
        self.client = client
        self.clean_timer = 30 * 60
        self.cached_file_ids: Dict[str, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        if db_id not in self.cached_file_ids:
            await self.generate_file_properties(db_id, multi_clients)
        return self.cached_file_ids[db_id]

    async def generate_file_properties(self, db_id: str, multi_clients) -> FileId:
        file_id = await get_file_ids(self.client, db_id, multi_clients, Message)
        self.cached_file_ids[db_id] = file_id
        return file_id

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        media_session = client.media_sessions.get(file_id.dc_id)

        if not media_session:
            if file_id.dc_id != await client.storage.dc_id():
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await Auth(client, file_id.dc_id, await client.storage.test_mode()).create(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()

                # FAST CONNECTION MODE
                media_session.connection.retries = 1
                media_session.connection.timeout = 10

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
                        continue
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

                media_session.connection.retries = 1
                media_session.connection.timeout = 10

            client.media_sessions[file_id.dc_id] = media_session

        return media_session

    @staticmethod
    async def get_location(file_id: FileId) -> Union[
        raw.types.InputPhotoFileLocation,
        raw.types.InputDocumentFileLocation,
        raw.types.InputPeerPhotoFileLocation,
    ]:

        if file_id.file_type == FileType.CHAT_PHOTO:
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

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ):

        client = self.client
        work_loads[index] += 1

        media_session = await self.generate_media_session(client, file_id)
        location = await self.get_location(file_id)

        max_retries = 4
        retry_delay = 1

        try:
            # MAX SAFE PARALLELISM
            workers = min(16, part_count)
            semaphore = asyncio.Semaphore(workers)

            async def fetch(part_index):
                part_offset = offset + (part_index * chunk_size)

                async with semaphore:
                    retries = 0
                    while retries < max_retries:
                        try:
                            r = await media_session.invoke(
                                raw.functions.upload.GetFile(
                                    location=location,
                                    offset=part_offset,
                                    limit=chunk_size
                                )
                            )

                            if isinstance(r, raw.types.upload.File):
                                return part_index, r.bytes
                            return part_index, b""

                        except OSError:
                            retries += 1
                            await asyncio.sleep(retry_delay)

                    return part_index, b""

            # START ALL TASKS INSTANTLY
            tasks = [asyncio.create_task(fetch(i)) for i in range(part_count)]

            # STREAM AS THEY ARRIVE (NO WAITING)
            results = [await t for t in asyncio.as_completed(tasks)]
            results.sort(key=lambda x: x[0])

            for part_index, chunk in results:

                if not chunk:
                    continue

                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]

                elif part_index == 0:
                    yield chunk[first_part_cut:]

                elif part_index == part_count - 1:
                    yield chunk[:last_part_cut]

                else:
                    yield chunk

        finally:
            work_loads[index] -= 1

    async def clean_cache(self):
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()