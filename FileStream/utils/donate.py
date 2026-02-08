from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY: PRE-CHECKOUT HANDLER ---
# Telegram requires the bot to confirm it can fulfill the order.
# Without this 'ok=True' answer, the payment window will fail.
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)


# --- 2. DONATE BUTTON LOGIC ---
@FileStream.on_callback_query(filters.regex("^donate$"))
async def donate_callback(_, query):
    try:
        await query.answer("Opening Telegram Stars ⭐")

        # Notify owner that someone clicked the button
        try:
            await _.send_message(
                OWNER_ID,
                f"<b>⭐ Donation Started</b>\n\n<b>User:</b> {query.from_user.mention}\n<b>ID:</b> <code>{query.from_user.id}</code>"
            )
        except Exception:
            pass

        # send_invoice for Stars (XTR)
        # We OMIT 'provider_token' entirely for Stars payments.
        await _.send_invoice(
            chat_id=query.from_user.id,
            title="⭐ Support Royality Bots",
            description="Support development & server costs ❤️",
            payload=f"donate_{query.from_user.id}",
            currency="XTR",
            prices=[
                # Telegram Stars prices are integers (e.g., 50 = 50 Stars)
                LabeledPrice("⭐ Small Support", 50),
                LabeledPrice("⭐⭐ Medium Support", 100),
                LabeledPrice("⭐⭐⭐ Big Support", 250),
            ],
            start_parameter="donate-stars"
        )

    except Exception as e:
        print("❌ DONATE ERROR:", e)
        traceback.print_exc()
        await query.message.reply_text("❌ Donation failed to initialize. Please ensure your Telegram app is updated.")


# --- 3. SUCCESSFUL PAYMENT HANDLER ---
@FileStream.on_message(filters.successful_payment)
async def payment_success(_, message):
    try:
        p = message.successful_payment

        receipt = f"""
<b>⭐ Payment Successful!</b>

<b>Amount:</b> {p.total_amount} Stars
<b>Transaction ID:</b> <code>{p.telegram_payment_charge_id}</code>

<b>Date:</b> {datetime.utcnow().strftime('%d %b %Y | %H:%M UTC')}
"""
        await message.reply_text(
            receipt,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅ Back", callback_data="home")]]
            )
        )

        # Notify owner of actual money received
        await _.send_message(
            OWNER_ID,
            f"<b>💰 Donation Received!</b>\n\n<b>Amount:</b> {p.total_amount} Stars\n<b>From:</b> {message.from_user.mention}"
        )

    except Exception as e:
        print("❌ PAYMENT ERROR:", e)
        traceback.print_exc()
