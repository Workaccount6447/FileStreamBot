from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY PRE-CHECKOUT HANDLER ---
# This must be present for the 'Pay' button to work. 
# It tells Telegram that the bot is ready to accept the stars.
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)

# --- 2. DONATE BUTTON CLICKED ---
@FileStream.on_callback_query(filters.regex("^donate$"))
async def donate_callback(_, query):
    try:
        await query.answer("Opening Telegram Stars ⭐")

        # Send Invoice for Stars (XTR)
        # Note: provider_token must be None or empty for Stars
        await _.send_invoice(
            chat_id=query.from_user.id,
            title="⭐ Support Royality Bots",
            description="Support development & server costs ❤️",
            payload=f"donate_{query.from_user.id}",
            provider_token=None,    
            currency="XTR",
            prices=[
                LabeledPrice("⭐ Small Support", 50),
                LabeledPrice("⭐⭐ Medium Support", 100),
                LabeledPrice("⭐⭐⭐ Big Support", 250),
            ],
            start_parameter="donate-stars"
        )

        # Notify owner that someone is looking at the donation page
        try:
            await _.send_message(
                OWNER_ID,
                f"<b>⭐ Donation Started</b>\n\n<b>User:</b> {query.from_user.mention}\n<b>ID:</b> <code>{query.from_user.id}</code>"
            )
        except Exception:
            pass

    except Exception as e:
        print("❌ DONATE ERROR:", e)
        traceback.print_exc()
        await query.message.reply_text("❌ Donation failed to initialize. Please try again later.")


# --- 3. PAYMENT SUCCESS HANDLER ---
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

        # Notify owner of successful payment
        await _.send_message(
            OWNER_ID,
            f"""
<b>💰 Donation Received</b>

<b>User:</b> {message.from_user.mention}
<b>Amount:</b> {p.total_amount} Stars
<b>Transaction ID:</b> <code>{p.telegram_payment_charge_id}</code>
"""
        )

    except Exception as e:
        print("❌ PAYMENT ERROR:", e)
        traceback.print_exc()
