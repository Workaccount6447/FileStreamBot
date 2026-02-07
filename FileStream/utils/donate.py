from datetime import datetime

from pyrogram import filters
from pyrogram.types import (
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from FileStream.bot import FileStream
from FileStream.utils.translation import LANG, BUTTON

OWNER_ID = 8420494874  # CHANGE IF NEEDED


# 🔙 Back button
BACK_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🔙 Back", callback_data="home")]]
)


# ⭐ Donate button clicked
@FileStream.on_callback_query(filters.regex("^donate$"))
async def donate_callback(client, query):
    await query.answer("Opening Telegram Stars payment ⭐")

    # Notify owner (payment started)
    await client.send_message(
        OWNER_ID,
        f"""
<b>⭐ Donation Initiated</b>

<b>User:</b> {query.from_user.mention}
<b>User ID:</b> <code>{query.from_user.id}</code>

<b>Status:</b> Opened Stars payment screen
"""
    )

    # Send Stars invoice
    await client.send_invoice(
        chat_id=query.from_user.id,
        title="⭐ Support Royality Bots",
        description="Support development & server costs ❤️",
        payload="donate_stars_basic",
        provider_token="",      # MUST be empty for Stars
        currency="XTR",         # Telegram Stars
        prices=[
            LabeledPrice("⭐ Small Support", 25),
            LabeledPrice("⭐⭐ Medium Support", 50),
            LabeledPrice("⭐⭐⭐ Big Support", 100),
        ],
        start_parameter="donate-stars"
    )


# ✅ Payment successful
@FileStream.on_message(filters.successful_payment)
async def successful_payment_handler(client, message):
    payment = message.successful_payment

    receipt_text = f"""
<b>🧾 Payment Receipt</b>

<b>⭐ Amount:</b> {payment.total_amount} Stars
<b>💳 Currency:</b> {payment.currency}

<b>🆔 Transaction ID:</b>
<code>{payment.telegram_payment_charge_id}</code>

<b>📅 Date:</b>
{datetime.utcnow().strftime('%d %b %Y | %H:%M UTC')}

<b>❤️ Thank you for supporting Royality Bots!</b>
"""

    # Send bill to user
    await message.reply_text(
        receipt_text,
        reply_markup=BACK_BUTTON
    )

    # Notify owner (payment success)
    await client.send_message(
        OWNER_ID,
        f"""
<b>💰 Donation Received!</b>

<b>User:</b> {message.from_user.mention}
<b>User ID:</b> <code>{message.from_user.id}</code>

<b>Amount:</b> {payment.total_amount} Stars
<b>Transaction ID:</b>
<code>{payment.telegram_payment_charge_id}</code>
"""
    )

    # Backend log
    print({
        "user_id": message.from_user.id,
        "amount": payment.total_amount,
        "currency": payment.currency,
        "transaction_id": payment.telegram_payment_charge_id,
        "payload": payment.invoice_payload,
        "timestamp": datetime.utcnow().isoformat()
    })


# 🔙 Back → Home
@FileStream.on_callback_query(filters.regex("^home$"))
async def back_to_home(client, query):
    await query.message.edit_text(
        text=LANG.START_TEXT.format(
            query.from_user.mention,
            FileStream.username
        ),
        reply_markup=BUTTON.START_BUTTONS,
        disable_web_page_preview=True
    )
    await query.answer()