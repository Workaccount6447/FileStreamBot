from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY PRE-CHECKOUT HANDLER ---
# Without this, the 'Pay' button will fail. You must answer within 10 seconds.
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)


# --- 2. DYNAMIC DONATION MENU ---
# Handles the selection and increment/decrement logic (-5, +5, etc.)
@FileStream.on_callback_query(filters.regex(r"^donate(_(\d+))?$"))
async def donate_menu(_, query):
    # Parse current amount from callback data, default to 10 Stars
    data = query.data.split("_")
    current_amount = int(data[2]) if len(data) > 2 else 10
    
    text = f"""
<b>Why should you donate to Royality Bots?</b>
-----------------------------------
Your support helps keep our tools fast, reliable, and free for everyone. Even a small <b>Donation</b> makes a big difference! 💖

👇 <b>Choose an amount to donate:</b>
"""
    # Button layout as requested: [ -5 ] [ ⭐ current ] [ +5 ]
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
    
    # Edit existing message to prevent spamming the chat
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


# --- 3. BILL GENERATOR (The Invoice) ---
@FileStream.on_callback_query(filters.regex(r"^bill_(\d+)$"))
async def send_invoice_bill(_, query):
    try:
        amount = int(query.data.split("_")[1])
        await query.answer(f"✅ Invoice for {amount} Stars generated!")
        
        # FIX: provider_token MUST be omitted or empty for Stars
        # FIX: prices MUST contain exactly ONE item for XTR
        await _.send_invoice(
            chat_id=query.from_user.id,
            title="Support Royality Bots",
            description=f"Contribute {amount} Stars to support ongoing development!",
            payload=f"donate_{amount}",
            currency="XTR",
            prices=[LabeledPrice("Donation", amount)],
            # Some Pyrogram versions crash if provider_token is passed as "" or None
            # If your error persists, remove this line entirely.
            provider_token="" 
        )
    except Exception as e:
        print(f"❌ INVOICE ERROR: {e}")
        await query.message.reply_text(f"❌ Error: {e}\nPlease ensure your Telegram app is updated.")


# --- 4. SUCCESSFUL PAYMENT HANDLER ---
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
        await message.reply_text(receipt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="home")]]))

        # Notify owner of actual funds received
        await _.send_message(
            OWNER_ID, 
            f"💰 <b>Donation Received!</b>\n\n<b>User:</b> {message.from_user.mention}\n<b>Amount:</b> {p.total_amount} Stars"
        )
    except Exception as e:
        print(f"❌ SUCCESS HANDLER ERROR: {e}")
