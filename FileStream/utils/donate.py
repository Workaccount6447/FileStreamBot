from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID


# ⭐ Donate button clicked
@FileStream.on_callback_query(filters.regex("^donate$"))
async def donate_callback(_, query):
    try:
        await query.answer("Opening Telegram Stars ⭐")

        # Notify owner (payment started)
        await _.send_message(
            OWNER_ID,
            f"""
<b>⭐ Donation Started</b>

<b>User:</b> {query.from_user.mention}
<b>User ID:</b> <code>{query.from_user.id}</code>
"""
        )

        await _.send_invoice(
            chat_id=query.from_user.id,
            title="⭐ Support Royality Bots",
            description="Support development & server costs ❤️",
            payload=f"donate_{query.from_user.id}",
            provider_token="",     # MUST be empty for Stars
            currency="XTR",
            prices=[
                LabeledPrice("⭐ Small Support", 25),
                LabeledPrice("⭐⭐ Medium Support", 50),
                LabeledPrice("⭐⭐⭐ Big Support", 100),
            ],
            start_parameter="donate-stars"
        )

    except Exception as e:
        print("❌ DONATE ERROR:", e)
        traceback.print_exc()
        await query.answer("❌ Donation failed", show_alert=True)


# ✅ Payment success
@FileStream.on_message(filters.successful_payment)
async def payment_success(_, message):
    try:
        p = message.successful_payment

        receipt = f"""
<b>⭐ Payment Successful!</b>

<b>Amount:</b> {p.total_amount} Stars
<b>Transaction ID:</b>
<code>{p.telegram_payment_charge_id}</code>

<b>Date:</b>
{datetime.utcnow().strftime('%d %b %Y | %H:%M UTC')}
"""

        await message.reply_text(
            receipt,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅ Back", callback_data="home")]]
            )
        )

        # Notify owner
        await _.send_message(
            OWNER_ID,
            f"""
<b>💰 Donation Received</b>

<b>User:</b> {message.from_user.mention}
<b>User ID:</b> <code>{message.from_user.id}</code>

<b>Amount:</b> {p.total_amount} Stars
<b>Transaction ID:</b>
<code>{p.telegram_payment_charge_id}</code>
"""
        )

        print({
            "user_id": message.from_user.id,
            "amount": p.total_amount,
            "currency": p.currency,
            "transaction": p.telegram_payment_charge_id
        })

    except Exception as e:
        print("❌ PAYMENT ERROR:", e)
        traceback.print_exc()