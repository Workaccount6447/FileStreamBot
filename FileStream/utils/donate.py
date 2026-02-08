from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY PRE-CHECKOUT HANDLER ---
# Without this 'ok=True' response, the 'Pay' button will fail.
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)


# --- 2. DONATION MENU (Choose amount) ---
@FileStream.on_callback_query(filters.regex("^donate$"))
async def donate_menu(_, query):
    text = "<b>⭐ Support This Project</b>\n\nSelect an amount to donate via Telegram Stars:"
    buttons = [
        [InlineKeyboardButton("⭐ 5 Stars", callback_data="pay_5")],
        [
            InlineKeyboardButton("+5 ⭐", callback_data="pay_10"),
            InlineKeyboardButton("+10 ⭐", callback_data="pay_15"),
            InlineKeyboardButton("+15 ⭐", callback_data="pay_20")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# --- 3. INVOICE GENERATOR (The Bill) ---
# Triggers after the user selects an amount from the menu above
@FileStream.on_callback_query(filters.regex(r"^pay_(\d+)$"))
async def send_donation_invoice(_, query):
    try:
        # Extract the amount from callback_data (e.g., pay_5 -> 5)
        amount = int(query.data.split("_")[1])
        await query.answer(f"Opening Star Invoice for {amount} ⭐")

        # FIX: We OMIT provider_token entirely for XTR
        # FIX: prices contains exactly ONE item for Stars
        await _.send_invoice(
            chat_id=query.from_user.id,
            title=f"⭐ Support ({amount} Stars)",
            description="Support development & server costs ❤️",
            payload=f"donate_{query.from_user.id}_{amount}",
            currency="XTR",
            prices=[LabeledPrice("Donation", amount)],
            start_parameter="donate-stars"
        )

    except Exception as e:
        print(f"❌ INVOICE ERROR: {e}")
        traceback.print_exc()
        await query.answer("❌ Error creating invoice. Update your app.", show_alert=True)


# --- 4. SUCCESSFUL PAYMENT HANDLER ---
@FileStream.on_message(filters.successful_payment)
async def payment_success(_, message):
    try:
        p = message.successful_payment
        receipt = f"<b>⭐ Payment Successful!</b>\n\n<b>Amount:</b> {p.total_amount} Stars\n<b>ID:</b> <code>{p.telegram_payment_charge_id}</code>"
        
        await message.reply_text(receipt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="home")]]))

        # Notify owner
        await _.send_message(OWNER_ID, f"<b>💰 Donation Received!</b>\n<b>User:</b> {message.from_user.mention}\n<b>Amount:</b> {p.total_amount} Stars")
    except Exception as e:
        print(f"❌ SUCCESS HANDLER ERROR: {e}")
