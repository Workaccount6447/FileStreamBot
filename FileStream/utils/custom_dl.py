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
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: Dict[str, FileId] = {}
        self.session_locks: Dict[int, asyncio.Lock] = {}
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
        if file_id.dc_id not in self.session_locks:
            self.session_locks[file_id.dc_id] = asyncio.Lock()

        async with self.session_locks[file_id.dc_id]:
            media_session = client.media_sessions.get(file_id.dc_id)

            # FIXED: Check if session exists without calling .is_connected
            if media_session is None:
                if file_id.dc_id != await client.get_dc_id():
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

                client.media_sessions[file_id.dc_id] = media_session
            return media_session

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
        location = await self.get_location(file_id)

        current_part = 1
        max_retries = 10 
        retry_delay = 1

        try:
            while current_part <= part_count:
                retries = 0
                while retries < max_retries:
                    try:
                        media_session = await self.generate_media_session(client, file_id)
                        r = await media_session.invoke(
                            raw.functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=chunk_size
                            )
                        )
                        
                        if isinstance(r, raw.types.upload.File):
                            chunk = r.bytes
                            if not chunk: break
                            
                            if part_count == 1:
                                yield chunk[first_part_cut:last_part_cut]
                            elif current_part == 1:
                                yield chunk[first_part_cut:]
                            elif current_part == part_count:
                                yield chunk[:last_part_cut]
                            else:
                                yield chunk
                                
                            current_part += 1
                            offset += chunk_size
                            break 
                        else:
                            raise ConnectionError("Empty Telegram Response")
                            
                    except (OSError, RuntimeError, Exception) as e:
                        retries += 1
                        logging.warning(f"TCP Fail (Retry {retries}): {e}")
                        # Force drop broken session
                        if file_id.dc_id in client.media_sessions:
                            old_session = client.media_sessions.pop(file_id.dc_id)
                            try:
                                await old_session.stop()
                            except:
                                pass
                        await asyncio.sleep(retry_delay)
                else:
                    break
        finally:
            work_loads[index] -= 1

    @staticmethod
    async def get_location(file_id: FileId):
        file_type = file_id.file_type
        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(user_id=file_id.chat_id, access_hash=file_id.chat_access_hash)
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(channel_id=utils.get_channel_id(file_id.chat_id), access_hash=file_id.chat_access_hash)
            location = raw.types.InputPeerPhotoFileLocation(peer=peer, volume_id=file_id.volume_id, local_id=file_id.local_id, big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG)
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(id=file_id.media_id, access_hash=file_id.access_hash, file_reference=file_id.file_reference, thumb_size=file_id.thumbnail_size)
        else:
            location = raw.types.InputDocumentFileLocation(id=file_id.media_id, access_hash=file_id.access_hash, file_reference=file_id.file_reference, thumb_size=file_id.thumbnail_size)
        return location

    async def clean_cache(self) -> None:
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
