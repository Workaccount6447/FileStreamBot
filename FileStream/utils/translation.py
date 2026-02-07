from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.config import Telegram


class LANG(object):

    START_TEXT = """
<b>👋 Hᴇʏ, </b>{}\n 
<b>I'ᴍ ᴛᴇʟᴇɢʀᴀᴍ ғɪʟᴇs sᴛʀᴇᴀᴍɪɴɢ ʙᴏᴛ ᴀs ᴡᴇʟʟ ᴅɪʀᴇᴄᴛ ʟɪɴᴋs ɢᴇɴᴇʀᴀᴛᴏʀ</b>\n
<b>ᴡᴏʀᴋɪɴɢ ᴏɴ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ</b>
<blockquote><b>‣ 💥Fᴀsᴛ ᴀs ᴀ ʀᴏᴄᴋᴇᴛ🚀 ᴀɴᴅ ғᴇᴇʟɪɴɢ ᴀs ᴀ ᴋɪɴɢ👑 sᴜᴄʜ ᴛʜᴀᴛ ᴍᴀᴅᴇ ʙʏ 
<a href='https://telegram.me/RoyalityBots'>ʀᴏʏᴀʟɪᴛʏ ʙᴏᴛꜱ👑</a></b></blockquote>
"""

    HELP_TEXT = """
<b>- ᴀᴅᴅ ᴍᴇ ᴀs ᴀɴ ᴀᴅᴍɪɴ ᴏɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ</b>
<b>- sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴅᴏᴄᴜᴍᴇɴᴛ ᴏʀ ᴍᴇᴅɪᴀ</b>
<b>- ɪ'ʟʟ ᴘʀᴏᴠɪᴅᴇ sᴛʀᴇᴀᴍᴀʙʟᴇ ʟɪɴᴋ</b>\n
<b>🔞 ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ sᴛʀɪᴄᴛʟʏ ᴘʀᴏʜɪʙɪᴛᴇᴅ.</b>\n
<i><b> ʀᴇᴘᴏʀᴛ ʙᴜɢs ᴛᴏ <a href='https://telegram.me/RoyalityBots'>ᴅᴇᴠᴇʟᴏᴘᴇʀ</a></b></i>
"""

    ABOUT_TEXT = """
<b>⚜ ᴍʏ ɴᴀᴍᴇ : {}</b>\n
<b>✦ ᴠᴇʀsɪᴏɴ : {}</b>
<b>✦ ᴜᴘᴅᴀᴛᴇᴅ ᴏɴ : 06-January-2026</b>
<b>✦ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href='https://telegram.me/RoyalityBots'>Royality Bots</a></b>\n
"""

    DONATE_TEXT = """
<b>⭐ Support This Project</b>\n\n
<b>Help me to motivate and buy me a glass of tea ( I don't drink coffee)</b>\n\n
• Helps me to design a new Advanced bot\n
• Helps me to be motivated\n
• Helps me to maintain server\n\n
Your small amount can motivate me a lot.\n\n
Thanks\n\n
<i>Click ⭐ Donate to proceed</i>
"""

    STREAM_TEXT = """
<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n
<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <b>{}</b>\n
<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n
<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n
<b>🖥 Wᴀᴛᴄʜ :</b> <code>{}</code>\n
<b>🔗 Sʜᴀʀᴇ :</b> <code>{}</code>\n\n
Oᴘᴇɴ ᴛʜɪs ʟɪɴᴋ ᴏɴ Bʀᴏᴡsᴇʀ 🌐 ᴛᴏ ᴀᴠᴏɪᴅ ɪssᴜᴇs.
"""

    STREAM_TEXT_X = """
<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n
<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <b>{}</b>\n
<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n
<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n
<b>🔗 Sʜᴀʀᴇ :</b> <code>{}</code>\n\n
Oᴘᴇɴ ᴛʜɪs ʟɪɴᴋ ᴏɴ Bʀᴏᴡsᴇʀ 🌐 ᴛᴏ ᴀᴠᴏɪᴅ ɪssᴜᴇs.
"""

    BAN_TEXT = "__Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ ᴛᴏ ᴜsᴇ ᴍᴇ.__\n\n**[Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ](tg://user?id={}) Tʜᴇʏ Wɪʟʟ Hᴇʟᴘ Yᴏᴜ**"


class BUTTON(object):
    START_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('⭐ ᴅᴏɴᴀᴛᴇ', callback_data='donate'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close')
        ],
        [
            InlineKeyboardButton(
                "📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ",
                url=f'https://t.me/RoyalityBots'
            )
        ]]
    )

    HELP_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close'),
        ],
        [
            InlineKeyboardButton(
                "📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ",
                url=f'https://t.me/RoyalityBots'
            )
        ]]
    )

    ABOUT_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close'),
        ],
        [
            InlineKeyboardButton(
                "📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ",
                url=f'https://t.me/RoyalityBots'
            )
        ]]
    )