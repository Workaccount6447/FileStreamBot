from datetime import datetime
from pyrogram import filters
from pyrogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from FileStream.bot import FileStream
from FileStream.config import Telegram
import traceback

OWNER_ID = Telegram.OWNER_ID

# --- 1. MANDATORY PRE-CHECKOUT HANDLER ---
@FileStream.on_pre_checkout_query()
async def pre_checkout_handler(_, query):
    await query.answer(ok=True)

# --- 2. DYNAMIC DONATION MENU ---
@FileStream.on_callback_query(filters.regex(r"^donate"))
async def donate_menu(_, query):
    data = query.data.split("_")
    current_amount = int(data[1]) if len(data) > 1 else 10
    
    text = "<b>Why should you donate to Royality Bots?\n\n

• It helps to cover the cost of the servers.\n
• It motivate us to make an update or create a new bot.\n
• Help me to buy a cup of tea from starbucks (does starbucks provides tea ?)<\b>\n-----------------------------------\n👇 <b>Choose an amount to donate:</b>"
    
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

# --- 3. PART 1: USER GO TO PAY ---
@FileStream.on_callback_query(filters.regex(r"^bill_(\d+)$"))
async def send_invoice_bill(_, query):
    try:
        amount = int(query.data.split("_")[1])
        user = query.from_user
        
        await query.answer(f"✅ Generating bill for {amount} Stars...", show_alert=True)
        
        # Notify Owner: Status - Go to pay
        await _.send_message(
            OWNER_ID,
            f"<b>🔔 Donation Initiative</b>\n\n"
            f"<b>Name :</b> {user.first_name}\n"
            f"<b>Username :</b> @{user.username if user.username else 'N/A'}\n"
            f"<b>Id :</b> <code>{user.id}</code>\n"
            f"<b>Ammount :</b> {amount} Stars\n"
            f"<b>Status :</b> Go to pay"
        )

        # Send Invoice (provider_token removed to fix error)
        await _.send_invoice(
            chat_id=user.id,
            title="Donate and made a difference. ",
            description=f"Contribute {amount} Stars ❤️",
            payload=f"donate_{amount}",
            currency="XTR",
            prices=[LabeledPrice("Donation", amount)],
            start_parameter="donate-stars"
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

# --- 4. PART 2: USER PAID ---
@FileStream.on_message(filters.successful_payment)
async def payment_success(_, message):
    try:
        p = message.successful_payment
        user = message.from_user
        
        # Notify User
        await message.reply_text(
            f"<b>⭐ Payment Successful!</b>\n\n<b>Amount:</b> {p.total_amount} Stars\n<b>ID:</b> <code>{p.telegram_payment_charge_id}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="home")]])
        )

        # Notify Owner: Status - Paid
        await _.send_message(
            OWNER_ID,
            f"<b>💰 Donation Received</b>\n\n"
            f"<b>Name :</b> {user.first_name}\n"
            f"<b>Username :</b> @{user.username if user.username else 'N/A'}\n"
            f"<b>Id :</b> <code>{user.id}</code>\n"
            f"<b>Ammount :</b> {p.total_amount} Stars\n"
            f"<b>Status :</b> Paid"
        )
    except Exception as e:
        print(f"❌ Error: {e}")
