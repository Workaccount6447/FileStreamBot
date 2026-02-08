from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY PRE-CHECKOUT HANDLER ---
# This is a background check; the user doesn't see a message here, 
# but it prevents the "Pay" button from failing.
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)

# --- 2. DYNAMIC DONATION MENU ---
@FileStream.on_callback_query(filters.regex(r"^donate(_(\d+))?$"))
async def donate_menu(_, query):
    data = query.data.split("_")
    current_amount = int(data[2]) if len(data) > 2 else 10
    
    text = f"""
<b>Why should you donate to Royality Bots?</b>
-----------------------------------
Your support helps keep our tools fast, reliable, and free for everyone.

👇 <b>Choose an amount to donate:</b>
"""
    buttons = [
        [
            InlineKeyboardButton("-5", callback_data=f"donate_{max(1, current_amount - 5)}"),
            InlineKeyboardButton(f"⭐ {current_amount}", callback_data="none"),
            InlineKeyboardButton("+5", callback_data=f"donate_{current_amount + 5}")
        ],
        [
            InlineKeyboardButton("+10 ⭐", callback_data=f"donate_{current_amount + 10}"),
            InlineKeyboardButton("+20 ⭐", callback_data=f"donate_{current_amount + 20}")
        ],
        [InlineKeyboardButton("💳 Generate Bill", callback_data=f"bill_{current_amount}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ]
    
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except MessageNotModified:
        pass
    
    await query.answer()

# --- 3. BILL GENERATOR (With User Notification) ---
@FileStream.on_callback_query(filters.regex(r"^bill_(\d+)$"))
async def send_invoice_bill(_, query):
    try:
        amount = int(query.data.split("_")[1])
        
        # This informs the user immediately with a popup alert
        await query.answer(
            f"✅ Generating your bill for {amount} Stars...\nPlease wait for the checkout window.", 
            show_alert=True
        )
        
        # Send the actual Stars Invoice
        await _.send_invoice(
            chat_id=query.from_user.id,
            title="Support Royality Bots",
            description=f"Finalize your contribution of {amount} Stars ❤️",
            payload=f"donate_{amount}",
            currency="XTR",
            prices=[LabeledPrice("Donation", amount)],
            provider_token="" 
        )
    except Exception as e:
        print(f"❌ INVOICE ERROR: {e}")
        await query.message.reply_text(f"❌ Could not generate bill: {e}")

# --- 4. SUCCESS HANDLER ---
@FileStream.on_message(filters.successful_payment)
async def payment_success(_, message):
    p = message.successful_payment
    receipt = f"<b>⭐ Payment Successful!</b>\n\n<b>Amount:</b> {p.total_amount} Stars\n<b>ID:</b> <code>{p.telegram_payment_charge_id}</code>"
    await message.reply_text(receipt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="home")]]))
    await _.send_message(OWNER_ID, f"💰 <b>Donation Received!</b>\n<b>User:</b> {message.from_user.mention}\n<b>Amount:</b> {p.total_amount} Stars")
