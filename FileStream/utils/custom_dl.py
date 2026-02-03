import asyncio
import logging
from typing import Dict, Union
from collections import defaultdict

from pyrogram import Client, utils, raw
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.types import Message

from FileStream.bot import work_loads
from .file_properties import get_file_ids


class ByteStreamer:
    def __init__(self, client: Client):
        self.client = client
        self.clean_timer = 30 * 60
        self.cached_file_ids: Dict[str, FileId] = {}
        self.dc_locks = defaultdict(asyncio.Lock)

        asyncio.create_task(self.clean_cache())

    async def clean_cache(self):
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        if db_id not in self.cached_file_ids:
            self.cached_file_ids[db_id] = await get_file_ids(
                self.client, db_id, multi_clients, Message
            )
        return self.cached_file_ids[db_id]

    async def generate_media_session(self, file_id: FileId) -> Session:
        dc_id = file_id.dc_id

        async with self.dc_locks[dc_id]:
            session = self.client.media_sessions.get(dc_id)

            if session and session.is_connected:
                return session

            if session:
                try:
                    await session.stop()
                except Exception:
                    pass

            if dc_id != await self.client.storage.dc_id():
                auth = await Auth(
                    self.client,
                    dc_id,
                    await self.client.storage.test_mode()
                ).create()

                session = Session(
                    self.client,
                    dc_id,
                    auth,
                    await self.client.storage.test_mode(),
                    is_media=True
                )
                await session.start()

                for _ in range(5):
                    try:
                        exported = await self.client.invoke(
                            raw.functions.auth.ExportAuthorization(dc_id=dc_id)
                        )
                        await session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported.id,
                                bytes=exported.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        await asyncio.sleep(1)
                else:
                    await session.stop()
                    raise AuthBytesInvalid
            else:
                session = Session(
                    self.client,
                    dc_id,
                    await self.client.storage.auth_key(),
                    await self.client.storage.test_mode(),
                    is_media=True
                )
                await session.start()

            self.client.media_sessions[dc_id] = session
            return session

    @staticmethod
    async def get_location(file_id: FileId):
        if file_id.file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )

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
        work_loads[index] += 1
        current_part = 1

        try:
            while current_part <= part_count:
                session = await self.generate_media_session(file_id)
                location = await self.get_location(file_id)

                r = await session.invoke(
                    raw.functions.upload.GetFile(
                        location=location,
                        offset=offset,
                        limit=chunk_size
                    )
                )

                if not isinstance(r, raw.types.upload.File) or not r.bytes:
                    break

                chunk = r.bytes

                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                offset += chunk_size
                current_part += 1

        except Exception:
            logging.exception("Streaming error")

        finally:
            work_loads[index] -= 1