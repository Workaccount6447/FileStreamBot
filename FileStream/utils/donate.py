from pyrogram import Client, filters
from pyrogram.types import LabeledPrice
from datetime import datetime

OWNER_ID = 8420494874  # 🔴 CHANGE THIS


# ⭐ User clicked Donate (about to pay)
@Client.on_callback_query(filters.regex("^donate$"))
async def donate_callback(client, query):
    await query.answer("Opening Telegram Stars payment ⭐")

    # 🔔 Notify owner (payment initiated)
    await client.send_message(
        OWNER_ID,
        f"""
<b>⭐ Donation Initiated</b>

<b>User:</b> {query.from_user.mention}
<b>User ID:</b> <code>{query.from_user.id}</code>

<b>Status:</b> Opened Stars payment screen
"""
    )

    await client.send_invoice(
        chat_id=query.from_user.id,
        title="⭐ Support Royality Bots",
        description="Support development & server costs ❤️",
        payload="donate_stars_basic",
        provider_token="",          # MUST be empty
        currency="XTR",             # Telegram Stars
        prices=[
            LabeledPrice("⭐ Small Support", 25),
            LabeledPrice("⭐⭐ Medium Support", 50),
            LabeledPrice("⭐⭐⭐ Big Support", 100)
        ],
        start_parameter="donate-stars"
    )


# ✅ Payment completed successfully
@Client.on_message(filters.successful_payment)
async def successful_payment_handler(client, message):
    payment = message.successful_payment

    receipt_text = f"""
<b>⭐ Donation Successful!</b>

<b>Amount:</b> {payment.total_amount} Stars
<b>Transaction ID:</b>
<code>{payment.telegram_payment_charge_id}</code>

<b>Date:</b>
{datetime.utcnow().strftime('%d %b %Y | %H:%M UTC')}

<b>Thank you for supporting ❤️</b>
"""

    await message.reply_text(receipt_text)

    # 🔔 Notify owner (payment success)
    await client.send_message(
        OWNER_ID,
        f"""
<b>💰 Donation Received!</b>

<b>User:</b> {message.from_user.mention}
<b>User ID:</b> <code>{message.from_user.id}</code>

<b>Amount:</b> {payment.total_amount} Stars
<b>Currency:</b> {payment.currency}

<b>Transaction ID:</b>
<code>{payment.telegram_payment_charge_id}</code>
"""
    )

    # 🧾 Backend log
    payment_log = {
        "user_id": message.from_user.id,
        "amount": payment.total_amount,
        "currency": payment.currency,
        "transaction_id": payment.telegram_payment_charge_id,
        "payload": payment.invoice_payload,
        "timestamp": datetime.utcnow().isoformat()
    }

    print(payment_log)