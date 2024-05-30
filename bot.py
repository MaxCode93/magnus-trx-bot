import json
import datetime
import time
import threading
import requests
import random
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, ConversationHandler, Filters

# Token del bot
TOKEN = "7130462783:AAFghcAReKgo0uReVkBdxwXkMPZoYxXExbQ"
ADMIN_ID = '1244656140'
CHANNEL  = "@magnus_trx"
ADMIN_WALLET = "TBUmsefmBgCfsHmuTGYWwmVGLyv9XvKhr5"
ADMIN_WALLET_KEY = "C37745F2828E3806A09923481F3C4642678E60048C67881F347CE12A19FD41AA"

MAX_WITHDRAW_LIMIT = True

JOIN_MESS = f"✨ Hi! To continue, you must join to:\n {CHANNEL}.\n Then select '✅ Joined' in the menu to proceed."

# Archivos JSON para almacenamiento
USER_DATA_FILE = "users_data.json"
BOT_CONFIG_FILE = "bot_config.json"
TRANSACTIONS_FILE= "transactions.json"

user_temp_data = {}

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as file:
            user_data = json.load(file)
    except FileNotFoundError:
        user_data = {}

    return user_data

def save_user_data(user_data):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(user_data, file)

try:
    with open(USER_DATA_FILE, "r") as file:
        user_data = json.load(file)
except FileNotFoundError:
    user_data = {}
    
def load_bot_config():
    try:
        with open(BOT_CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return bot_config

def save_bot_config(config):
    with open(BOT_CONFIG_FILE, "w") as file:
        json.dump(config, file)

def remove_trailing_zeros(num):
    num_str = "{:.8f}".format(num)
    num_str = num_str.rstrip("0")
    if num_str.endswith("."):
        num_str += "0"
    return num_str
    
# Menus
main_menu = [[KeyboardButton("🔥 Deposit")],
    [KeyboardButton("💸 Withdraw"), KeyboardButton("💳 Account"), KeyboardButton("♻️ Reinvest")],
    [KeyboardButton("👥 Referrals"),KeyboardButton("🎁 Bonus")]
]

account_menu = [
    [KeyboardButton("⚙️ Set Wallet"), KeyboardButton("⚡ Balance"), KeyboardButton("💸 Withdraw History")],
    [KeyboardButton("♻️ Invest History"), KeyboardButton("🏆 Referral Rank"), KeyboardButton("🔙 Back")]
]

referral_menu = [
    [KeyboardButton("🏆 Referral Rank"),KeyboardButton("🔙 Back")]
]

admin_menu = [
    [KeyboardButton("👥 Users"), KeyboardButton("🗣️ Announ"), KeyboardButton("📌 Pin Message")],
    [KeyboardButton("🔙 Back")]
]

joined_menu = [
    [KeyboardButton("✅ Joined")]
]

cancel_set_wallet_menu = [
    [KeyboardButton("✖️ Cancel Action")]
]

cancel_menu = [
    [KeyboardButton("✖️ Cancel")]
]

def is_user_joined_channel(bot, user_id, channel):
    try:
        member = bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'creator', 'administrator']
    except Exception as e:
        print(f"Error al intentar verificar la membresía: {e}")
        return False
        
def start(update: Update, context: CallbackContext) -> None:
    global user_temp_data
    
    user = update.effective_user
    user_id = str(user.id)

    args = context.args[0].split("_") if context.args else [user_id]
    
    if len(args) == 1:
        referral_id = args[0]
        investment_id = 0
    else:
        referral_id, investment_id = args
    
    user_temp_data = {
        "referral_id": referral_id,
        "investment_id": investment_id
    }
    
    user_data = load_user_data()
    
    if user_id in user_data and 'captcha_solved' in user_data[user_id] and user_data[user_id]['captcha_solved']:
        start_main(update, context)
        
        return ConversationHandler.END

    generate_captcha(update, context)
    
    return 'captcha_check'

def captcha_check(update: Update, context: CallbackContext) -> None:
    user_answer = update.message.text.strip()

    if not user_answer.lstrip('-').isdigit():
        update.message.reply_text("⚠️ Please enter a valid number.")
        generate_captcha(update, context)
        return 'captcha_check'
    
    user_answer = int(user_answer)
    expected_result = int(context.user_data.get('expected_result'))
    
    if user_answer == expected_result:
        update.message.reply_text("✅ Captcha verified successfully!")
        start_main(update, context)
        
        del context.user_data['expected_result']
        
        return ConversationHandler.END
    else:
        update.message.reply_text("⚠️ Incorrect captcha. Please try again.")
        generate_captcha(update, context)
    
    return 'captcha_check'

def generate_captcha(update: Update, context: CallbackContext) -> None:
    numero1 = random.randint(1, 10)
    numero2 = random.randint(1, 10)
    operador = random.choice(['+', '-', '*'])
    pregunta = f"What is {numero1} {operador} {numero2}?"
    resultado = eval(f"{numero1} {operador} {numero2}")
    context.user_data['expected_result'] = str(resultado)
    update.message.reply_text(f"✍️ Please answer the following question:\n {pregunta}")

# Comando start_main
def start_main(update: Update, context: CallbackContext) -> None:
    global user_temp_data
    
    user = update.effective_user
    user_id = str(user.id)
    referral_id = user_temp_data.get('referral_id', user_id)

    user_data = load_user_data()
    
    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        
        return

    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    if user_id != referral_id:
        investment_id = user_temp_data.get('investment_id')
        if investment_id and investment_id != 0:
            for investment in user_data[referral_id]["invest_history"]:
                if investment["investment_id"] == investment_id and investment["status"] == "active":
                    # Acortar la mitad del tiempo en end_date
                    current_datetime = datetime.datetime.now()
                    end_date = datetime.datetime.strptime(investment["end_date"], "%Y-%m-%d %H:%M")
                    new_end_date = current_datetime + (end_date - current_datetime) // 2
                    investment["end_date"] = new_end_date.strftime("%Y-%m-%d %H:%M")
                    investment["boost_times"] += 1
                    context.bot.send_message(chat_id=referral_id, text=f"🎉 Congratulations! User {user_id} has reduced your investment plan {investment_id}. \nSend /boost command to view details.")
                    context.bot.send_message(chat_id=user_id, text="✅ Thank You! With your help, the person who referred you has doubled their investment return speed. Your support made a big difference!💪")
                    break
    
    if user_id not in user_data:
        if referral_id and referral_id != user_id and referral_id in user_data:
            referral_user = user_data[referral_id]
            if "referrals" not in referral_user:
                referral_user["referrals"] = {}
            if user_id not in referral_user["referrals"]:
                referral_user["referrals"][user_id] = {
                    "user_name": user.username
                }
                saldo_actual = round(referral_user["saldo"], 8)
                s_b = saldo_actual + 0.1
                referral_user["saldo"] = s_b
                referral_user["ref_earn"] += 0.1
                referral_user["total_earned"] += 0.1
        
        user_data[user_id] = {
            "id": user_id,
            "user_name": user.username,
            "link": referral_link,
            "user_wallet": "",
            "saldo": 1,
            "ref_earn": 0,
            "total_withdrawn": 0,
            "total_earned": 1,
            "total_deposit": 0,
            "referrals": {},
            "referral_id": referral_id if referral_id and referral_id != user_id else "",
            "withdraw_history": {},
            "invest_history": {}, 
            "deposit_wallet": {},
            "bonus": {
                "last_bonus_time": ""
            },
            "last_withdraw_time": "",
            "user_ban": False,
            "captcha_solved": True
        }
        
        # Guardar los datos de los usuarios en el archivo JSON
        save_user_data(user_data)

        # Notificar al referente sobre el nuevo referido
        if referral_id and referral_id != user_id:
            context.bot.send_message(chat_id=referral_id, text=f"🎉 Congratulations! You have obtained a new referral: {user.username or user.first_name}")
            context.bot.send_message(chat_id=referral_id, text="🎁 You have received a bonus of 0.1 TRX for your new referral!")

        reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        update.message.reply_text(f"🙋‍♂️ Welcome to the bot! 1 TRX has been added to your balance.\n\n🔗 Your referral link is: {referral_link}\n\n🌟 Here's what you can do with me:\n💵 Make Deposits to start your earning journey.\n♻️ Re-invest your earnings to compound your growth.\n💸 Withdraw your profits whenever you wish.\n📈 Track your Investments and watch your portfolio expand.\n👥 Earn more with our referral program, you will receive 15% of the investments made.\n\n~~~~~~~~~~~~~~~~~~~~~~~\n\nINVESTMENT PLAN\n💰 Minimum Deposit: 10 TRX\n💰 Maximum Deposit: Unlimited\n💰 Credited in: 24 hours\n💰 Profit: 135%\n\nReady to grow your digital assets? Let's get started! 🚀", reply_markup=reply_markup)
    else:
        reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        update.message.reply_text(f"🙋‍♂️ Welcome back!\n\n🔗 Your referral link is:\n{referral_link}\n\nHere's what you can do with me:\n💵 Make Deposits to start your earning journey.\n♻️ Re-invest your earnings to compound your growth.\n💸 Withdraw your profits whenever you wish.\n📈 Track your Investments and watch your portfolio expand.\n👥 Earn more with our referral program, you will receive 15% of the investments made.\n\n~~~~~~~~~~~~~~~~~~~~~~~\n\nINVESTMENT PLAN\n💰 Minimum Deposit: 10 TRX\n💰 Maximum Deposit: Unlimited\n💰 Credited in: 24 hours\n💰 Profit: 135%\n\nReady to grow your digital assets? Let's get started! 🚀", reply_markup=reply_markup)

    if 'referral_id' in user_temp_data:
        del user_temp_data['referral_id']

    if 'investment_id' in user_temp_data:
        del user_temp_data['investment_id']

# Función balance
def balance(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if user_id in user_data:
        user_info = user_data[user_id]
        saldo = user_info.get("saldo", 0)
        refer_earn = user_info.get("ref_earn", 0)
        total_withdrawn = user_info.get("total_withdrawn", 0)
        ganancia_total = user_info.get("total_earned", 0)

        saldo_str = remove_trailing_zeros(round(saldo, 8))
        refer_earn_str = remove_trailing_zeros(round(refer_earn, 8))
        total_withdrawn_str = remove_trailing_zeros(round(total_withdrawn, 8))
        ganancia_total_str = remove_trailing_zeros(round(ganancia_total, 8))

        message = f"🚀Account Information🚀\n\n💰 Available Balance: {saldo_str} TRX\n"
        message += f"👥 Earnings from referrals: {refer_earn_str} TRX\n"
        message += f"💸 Total Withdrawn: {total_withdrawn_str} TRX\n"
        message += f"⚖️ Total Earnings: {ganancia_total_str} TRX\n"

        wallet = user_info.get("user_wallet")
        if wallet:
            message += f"💳 Withdrawal Wallet: {wallet}\n\n"
        else:
            message += "💳 Withdrawal Wallet: Not Set\n\n"

        referral_link = user_info.get("link")
        message += f"🔗 Your referral link is: {referral_link}\n"

        message += "\nContinue sharing your referral link and you will achieve great accomplishments! 💪🚀"

        reply_markup = ReplyKeyboardMarkup(account_menu, resize_keyboard=True)
        update.message.reply_text(message, reply_markup=reply_markup)
    else:
        update.message.reply_text("⚠️ You don't have a balance yet! Please use /start")

    return ConversationHandler.END

#Comando info
def info(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    user_data = load_user_data()

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    user_count = len(user_data)

    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    update.message.reply_text(f"ℹ️ Bot info\n\n🚦Status: 🟢 Online\n💸 Withdrawal Status: ✅ Automatic\n\n👥 Total Users\n{user_count} registered users\n\nMagnus Pool TRX Bot 🤖 - Invest and see your investments grow\n\n🤖 Bot Powered by Maxwell(@Karlitin)", reply_markup=reply_markup)

def admin(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    
    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    user_id = str(update.effective_user.id)
    
    if user_id == ADMIN_ID:
        reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
        update.message.reply_text("🙋‍♂️Hi Admin!", reply_markup=reply_markup)
    else:
        update.message.reply_text("❌ I'm sorry, you don't have permission to use this command.")

def request_announcement(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if user_id == ADMIN_ID:
        context.user_data['is_announcing'] = True
        reply_markup = ReplyKeyboardMarkup(cancel_menu, resize_keyboard=True)
        update.message.reply_text("✍️ Please enter the announcement you want to send to all users:", reply_markup=reply_markup)

def announce_to_users(update: Update, context: CallbackContext, announcement: str) -> None:
    user_data = load_user_data()
    announcement_message = f"📢 [Admin MSG]:\n\n{announcement}"
    for user_id in user_data.keys():
        if user_id != ADMIN_ID:
            context.bot.send_message(chat_id=user_id, text=announcement_message)
    context.user_data['is_announcing'] = False
    update.message.reply_text("✅ Announcement sent to all users.")

    reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
    update.message.reply_text("🙋‍♂️Hi Admin!", reply_markup=reply_markup)
    
# Comando get_users
def get_users(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()
    
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ I'm sorry, you don't have permission to use this command.")
        return

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if not user_data:
        message = "😔 There are no registered users in the bot."
        reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
        update.message.reply_text(message, reply_markup=reply_markup)
        return

    message = "👥 Users:\n"
    for user_id, user_info in user_data.items():
        user_name = user_info.get("user_name")
        user_id = user_info.get("id")
        user_saldo = user_info.get("saldo")
        user_saldo_str = remove_trailing_zeros(round(user_saldo, 8))
        if user_name:
            user_name_with_at = "@" + user_name
            message += f"- {user_name_with_at}\n🆔: {user_id}\n💰: {user_saldo_str} TRX\n\n"

    reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
    update.message.reply_text(message, reply_markup=reply_markup)

PIN_MESSAGE = 1

def pin_message(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)

    if user_id != ADMIN_ID:
        update.message.reply_text("❌ I'm sorry, you don't have permission to use this command.")
        return ConversationHandler.END

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return ConversationHandler.END
        
    keyboard = [['❌ Back']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("✍️ Send my the message:", reply_markup=reply_markup)
    return PIN_MESSAGE

def handle_pin_message(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)

    if user_id != ADMIN_ID:
        update.message.reply_text("❌ I'm sorry, you don't have permission to use this command.")
        return ConversationHandler.END

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return ConversationHandler.END

    pin_message = update.message.text
    user_data = load_user_data()
    pin_chat_message(context, pin_message)

    return ConversationHandler.END

def pin_chat_message(context, message):
    if message == "❌ Back":
        reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
        context.bot.send_message(chat_id=ADMIN_ID, text="🙋‍♂️Hi Admin!", reply_markup=reply_markup)
        return ConversationHandler.END

    user_data = load_user_data()
    for user_id in user_data:
        sent_message = context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.HTML)
        context.bot.pin_chat_message(chat_id=user_id, message_id=sent_message.message_id)

    reply_markup = ReplyKeyboardMarkup(admin_menu, resize_keyboard=True)
    context.bot.send_message(chat_id=ADMIN_ID, text="✅ Pinned message.", reply_markup=reply_markup)

# Función show_referrals
def show_referrals(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if user_id in user_data:
        referrals = user_data[user_id]["referrals"]
        referral_count = len(referrals)

        if referral_count > 0:
            message = "👤 Referrals:\n"

            for referral_id, referral in referrals.items():
                referral_name = "@" + referral["user_name"]
                message += f"- {referral_name}\n"
        else:
            message = "😔 You don't have any referrals yet.\n"

        message += "\nKeep sharing your referral link! 💪🚀"
    else:
        message = "😔 You don't have any referrals yet.\n"

        message += "\nShare your referral link with your friends! 📣💫"

    referral_link = user_data[user_id]["link"]
    message_final = f"{message}\n🔗 {referral_link}"
    reply_markup = ReplyKeyboardMarkup(referral_menu, resize_keyboard=True)
    update.message.reply_text(message_final, reply_markup=reply_markup)

SET_WALLET = 1

# Comando set_wallet
def set_wallet(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if user_id in user_data:
        if user_data[user_id]["user_wallet"]:
            reply_markup = ReplyKeyboardMarkup(cancel_set_wallet_menu, resize_keyboard=True)
            current_wallet = user_data[user_id]["user_wallet"]
            update.message.reply_text(f"💳 Current Wallet:\n{current_wallet}\n\n🚨 Remember that we are not responsible for sending payments to incorrect wallets.\n\n👇 Please send me your wallet address for future payments:", reply_markup=reply_markup)
        else:
            reply_markup = ReplyKeyboardMarkup(cancel_set_wallet_menu, resize_keyboard=True)
            update.message.reply_text("🚨 Remember that we are not responsible for sending payments to incorrect wallets.\n\n👇 Please send me your wallet address for future payments:", reply_markup=reply_markup)
        return SET_WALLET
    else:
        update.message.reply_text("😔 You don't have an account in the bot yet. Please use the command /start to create an account.")
        return ConversationHandler.END

# capture wallet
def capture_wallet(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text
    user_data = load_user_data()

    if text.startswith('/') or text == "✖️ Cancel Action" or text == "💳 Account":
        update.message.reply_text("⚠️ Action canceled.", reply_markup=ReplyKeyboardMarkup(account_menu, resize_keyboard=True))
        return ConversationHandler.END

    if user_id in user_data:
        wallet = update.message.text

        for user_info in user_data.values():
            if user_info["user_wallet"] == wallet:
                update.message.reply_text("⚠️ The entered wallet is already in use. Please use a different wallet.", reply_markup=ReplyKeyboardMarkup(account_menu, resize_keyboard=True))
                return ConversationHandler.END

        user_data[user_id]["user_wallet"] = wallet
        save_user_data(user_data)

        update.message.reply_text("✅ Wallet saved successfully.", reply_markup=ReplyKeyboardMarkup(account_menu, resize_keyboard=True))
    else:
        update.message.reply_text("😔 You don't have an account in the bot yet. Please use the command /start to create an account.", reply_markup=ReplyKeyboardMarkup(account_menu, resize_keyboard=True))

    return ConversationHandler.END

# show_withdraw_history
def show_withdraw_history(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()

    if user_id in user_data:
        withdraw_history = user_data[user_id]["withdraw_history"]

        if withdraw_history:
            message = "💸 Withdraw History:\nLast 20 payments:\n\n"
            last_20_withdraws = withdraw_history[-20:]
            for withdraw in last_20_withdraws:
                withdraw_date = withdraw["date"]
                withdraw_amount = withdraw["amount"]
                withdraw_status = withdraw["status"]
                message += f"📅 Date: {withdraw_date}\n💰 Amount: {withdraw_amount}\n🟢 Status: {withdraw_status}\n\n"

            update.message.reply_text(message)
        else:
            update.message.reply_text("⚠️ You don't have any withdrawal history.")
    else:
        update.message.reply_text("😔 You don't have an account in the bot yet. Please use the command /start to create an account.")

REINVEST_AMOUNT, REINVEST_CONFIRMATION = range(2)

def cancel(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("⚠️ Operation canceled.")
    return ConversationHandler.END

def reinvest_start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()

    if user_id in user_data:
        saldo_actual = round(user_data[user_id]["saldo"],8)
        user_wallet = user_data[user_id]["user_wallet"]

        if saldo_actual < 1:
            update.message.reply_text(f"🔥 Remember that our plans return 135% every 24 hours. Stake your assets and watch your rewards grow, maintaining flexibility to trade and borrow.\n\n💸 Available Balance: {saldo_actual} TRX\n\n⚡Your current balance is insufficient.\n\nThe minimum balance for reinvestment is 1 TRX.")
            return ConversationHandler.END

        min_reinvest = 1
        max_reinvest = round(saldo_actual, 8)
        max_reinvest_str = remove_trailing_zeros(max_reinvest)
        if saldo_actual == 1:
        	keyboard = [[KeyboardButton(str(min_reinvest))], [KeyboardButton("Cancel")]]
        else:
        	keyboard = [[KeyboardButton(str(min_reinvest)), KeyboardButton(str(max_reinvest))], [KeyboardButton("Cancel")]]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        update.message.reply_text(f"♻️ Balance Reinvestment ♻️\n\n🔥 Remember that our plans return 135% every 24 hours. Stake your assets and watch your rewards grow, maintaining flexibility to trade and borrow.\n\n💸 Available Balance: {max_reinvest_str}\n\n⚠️ Please enter the amount you want to reinvest or select one of the suggested options:", reply_markup=reply_markup)

        return REINVEST_AMOUNT

    else:
        update.message.reply_text("😔 You don't have an account in the bot yet. Please use the command /start to create an account.")
        return ConversationHandler.END

def handle_reinvest_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    text = update.message.text
    user_data = load_user_data()
    
    if user_id in user_data:
        try:
            reinvest_amount = float(text)
            min_reinvest = 1.0
            max_reinvest = round(user_data[user_id]["saldo"], 8)

            if reinvest_amount < min_reinvest or reinvest_amount > max_reinvest:
                update.message.reply_text(f"⚠️ Please select a valid amount between 1 and {max_reinvest}.")
                return REINVEST_AMOUNT

            context.user_data["reinvest_amount"] = reinvest_amount

            #hide_markup = ReplyKeyboardRemove()
            keyboard = [['✅ Yes', '❌ No']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            update.message.reply_text(f"♻️ You have selected to reinvest {reinvest_amount} TRX. \nAre you sure?", reply_markup=reply_markup)
            return REINVEST_CONFIRMATION

        except ValueError:
            pass
     
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    update.message.reply_text("⚠️ Operation canceled.", reply_markup=reply_markup)
    return ConversationHandler.END
    
def reinvest_confirmation(update: Update, context: CallbackContext) -> int:
    bot = Bot(TOKEN)
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()
    user_data = load_user_data()
    user_link = user_data[user_id].get("link")

    if user_id in user_data:
        reinvest_amount = context.user_data.get("reinvest_amount")

        if text == "✅ yes":
            fecha_inicio = datetime.datetime.now().replace(second=0, microsecond=0)
            fecha_final = fecha_inicio + datetime.timedelta(hours=24)

            ganancia = reinvest_amount * 1.35
            ganancia_esperada = remove_trailing_zeros(round(ganancia, 8))
            user_data[user_id]["saldo"] -= reinvest_amount

            if "invest_history" not in user_data[user_id] or not isinstance(user_data[user_id]["invest_history"], list):
                user_data[user_id]["invest_history"] = []

            if user_data[user_id]["invest_history"]:
                last_investment = user_data[user_id]["invest_history"][-1]
                last_investment_id = last_investment["investment_id"]
                new_investment_id = str(int(last_investment_id) + 1)
            else:
                new_investment_id = "1000000"
            
            boost_link = user_link + "_" + new_investment_id
            user_data[user_id]["invest_history"].append({
                "investment_id": new_investment_id,
                "amount": reinvest_amount,
                "profit": ganancia_esperada,
                "status": "active",
                "type": "Reinvestment",
                "start_date": fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "end_date": fecha_final.strftime("%Y-%m-%d %H:%M"),
                "boost_link": boost_link,
                "boost_times": 0
            })

            save_user_data(user_data)
            
            mensaje = f"🎉 Reinvestment Started 🎉 \n\n🥳 Congratulations on starting your investment journey with us!\n\n📝 Reinvestment details:\n📆 Duration: 24 hours (total return 135%)\n💰 Amount {reinvest_amount} TRX.\n📈 Profit: {ganancia_esperada} TRX.\n⏳Start Date: {fecha_inicio}.\n⌛End Date: {fecha_final}.\n\n🚀 Thank you for depositing your trust in us. Stay tuned for regular updates. 🚀\n\n💫 Want to boost your investment returns by 2x the speed? Send /boost command to learn how!"

            reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            bot.send_message(chat_id=user_id, text=mensaje, reply_markup=reply_markup)
            
            # API para obtener el precio actual de Tron
            api_url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd"
            trx_response = requests.get(api_url)
            price = trx_response.json()
            tron_price = price.get("tron", {}).get("usd", 0)
            tron_decimal = float(tron_price)
            monto_to_price = reinvest_amount * tron_decimal
            amount_to_price = remove_trailing_zeros(monto_to_price)
            user_link_formatted = user_link.replace("_", "\_")
            mensaje = f"♻️ NEW REINVEST ♻️\n\n👤 USER ID: {user_id}\n💰 AMOUNT: {reinvest_amount} TRX\n💲 USD($): {amount_to_price} USD\n💰 EXPECTED PROFIT: {ganancia_esperada} TRX\n\n🤖 Bot: {user_link_formatted}"
            bot.send_message(chat_id=CHANNEL, text=mensaje, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            update.message.reply_text("⚠️ Reinvestment canceled.", reply_markup=reply_markup)

    return ConversationHandler.END
 
def invest_history(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_data = load_user_data()

    if user_id in user_data:
        invest_history = user_data[user_id].get("invest_history", [])

        if invest_history:
            active_investments = []
            completed_investments = []

            for invest in invest_history:
                if invest["status"] == "completed":
                    completed_investments.append(invest)
                else:
                    active_investments.append(invest)

            active_investments = sorted(active_investments, key=lambda inv: inv["start_date"])
            completed_investments = sorted(completed_investments, key=lambda inv: inv["start_date"])

            mensaje = "📊 Here is your investment history:\n\n✅ Active investments:\n\n"

            for invest in active_investments[-20:]:
                start_date = datetime.datetime.strptime(invest["start_date"], "%Y-%m-%d %H:%M")
                remaining_time = datetime.datetime.strptime(invest["end_date"], "%Y-%m-%d %H:%M") - datetime.datetime.now()

                if remaining_time.total_seconds() >= 3600:
                    remaining_hours = int(remaining_time.total_seconds() // 3600)
                    monto = round(float(invest['amount']), 8)
                    monto_str = remove_trailing_zeros(monto)
                    ganancia = round(float(invest['profit']), 8)
                    ganancia_str = remove_trailing_zeros(ganancia)
                    mensaje += (f"⏳ Start Date: {invest['start_date']}\n💰 Amount: {monto_str} TRX\n💰 Expected Profit: {ganancia_str} TRX\n⚡ Type: {invest['type']}\n⌛ Remaining Time: {remaining_hours} hours\n\n")
                elif remaining_time.total_seconds() >= 60:
                    remaining_minutes = int(remaining_time.total_seconds() // 60)
                    monto = round(float(invest['amount']), 8)
                    monto_str = remove_trailing_zeros(monto)
                    ganancia = round(float(invest['profit']), 8)
                    ganancia_str = remove_trailing_zeros(ganancia)
                    mensaje += (f"⏳ Start Date: {invest['start_date']}\n💰 Amount: {monto_str} TRX\n💰 Expected Profit: {ganancia_str} TRX\n⚡ Type: {invest['type']}\n⌛ Remaining Time: {remaining_minutes} minutes\n\n")
                else:
                    remaining_seconds = int(remaining_time.total_seconds())
                    if remaining_seconds <= 0:
                        remaining_seconds = "Some Seconds"
                    else:
                        remaining_seconds = f"{remaining_seconds} seconds"
                    monto = round(float(invest['amount']), 8)
                    monto_str = remove_trailing_zeros(monto)
                    ganancia = round(float(invest['profit']), 8)
                    ganancia_str = remove_trailing_zeros(ganancia)
                    mensaje += (f"⏳ Start Date: {invest['start_date']}\n💰 Amount: {monto_str} TRX\n💰 Expected Profit: {ganancia_str} TRX\n⚡ Type: {invest['type']}\n⌛ Remaining Time: {remaining_seconds}\n\n")

            update.message.reply_text(mensaje)
            
            if completed_investments:
                mensaje1 = "☑️ Last 20 completed:\n\n"
                last_20_completed = completed_investments[-20:]
                for invest in last_20_completed:
                    start_date = datetime.datetime.strptime(invest["start_date"], "%Y-%m-%d %H:%M")
                    monto = round(float(invest['amount']), 8)
                    monto_str = remove_trailing_zeros(monto)
                    ganancia = round(float(invest['profit']), 8)
                    ganancia_str = remove_trailing_zeros(ganancia)
                    mensaje1 += (f"⏳ Date: {invest['end_date']}\n💰 Amount: {monto_str} TRX\n💰 Profit: {ganancia_str} TRX\n⚡ Type: {invest['type']}\n\n")

                update.message.reply_text(mensaje1)
        else:
            update.message.reply_text("⚠️ You have no investment history.\n\n💫 What are you waiting for, start now! /invest")
    else:
        update.message.reply_text("⚠️ User information not found.")

    return ConversationHandler.END

def check_reinvestment_completion():
    bot = Bot(TOKEN)
    while True:
        user_data = load_user_data()

        for user_id, user_info in user_data.items():
            invest_history = user_info.get("invest_history", [])

            for invest in invest_history:
                if invest["status"] == "completed":
                    continue

                end_date = datetime.datetime.strptime(invest["end_date"], "%Y-%m-%d %H:%M")

                if datetime.datetime.now() >= end_date:
                    ganancia = invest["amount"] * 1.35

                    ganancia = round(ganancia, 8)
                    ganancia_str = remove_trailing_zeros(ganancia)

                    user_info["saldo"] += ganancia
                    user_info["total_earned"] += ganancia
                    invest["status"] = "completed"

                    save_user_data(user_data)

                    mensaje = f"💫 Your investment has ended! 💫\n\n{ganancia_str} TRX has been added to your balance.\n\n✅ Check your balance with /balance\n\nLooking to increase your earnings even more? Use the /reinvest command and watch your investment grow even further!\n\n⚡ Quick Commands\n/balance - Check your account balance.\n/invest - Explore our plans and start a new investment.\n/reinvest - Initiate a quick reinvestment of your earnings."

                    bot.send_message(chat_id=user_id, text=mensaje)

        time.sleep(2)

def start_check_reinvestment():
    thread = threading.Thread(target=check_reinvestment_completion)
    thread.start()
    print("Check_Reinvestment_Completion task started successfully.")

start_check_reinvestment()

def create_wallet(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_user_data()
    chat_id = update.message.chat_id

    if not is_user_joined_channel(context.bot, user_id, CHANNEL):
        reply_markup = ReplyKeyboardMarkup(joined_menu, resize_keyboard=True)
        update.message.reply_text(JOIN_MESS, reply_markup=reply_markup)
        return

    if user_id in user_data and "deposit_wallet" in user_data[user_id] and "wallet" in user_data[user_id]["deposit_wallet"]:
        wallet_address = user_data[user_id]["deposit_wallet"]["wallet"]
        update.message.reply_text("Magnus Pool TRX Bot 🤖\nMagnus Staking 135% in 24 hours\n\n▫ Minimum Deposit: 10 TRX\n▫ Maximum Deposit: Unlimited\n▫ 135% returns \n▫ Earnings paid in 24 hours")
        update.message.reply_text("🥳 Please only send TRX to this address. The minimum amount to send is 10 TRX. Smaller deposits will be ignored. The bot will automatically recognize the deposit, transactions usually take between 3~30 minutes, in special cases it may take up to 24 hours, please be patient. 🙏")
        update.message.reply_text(f"Your unique deposit address is:\n {wallet_address}")
        return

    response = requests.get('https://api-tronprojects.vercel.app')
    update.message.reply_text("Magnus Pool TRX Bot 🤖\nMagnus Staking 135% in 24 hours\n\n▫ Minimum Deposit: 10 TRX\n▫ Maximum Deposit: Unlimited\n▫ 135% returns \n▫ Earnings paid in 24 hours")
    update.message.reply_text(f"⏳ Generating a unique deposit address for you...")
    try:
        data = response.json()
        address = data["address"]["base58"]
        privateKey = data["privateKey"]

        if user_id in user_data:
            user_data[user_id]["deposit_wallet"] = {
                "wallet": address,
                "private_key": privateKey
            }

            save_user_data(user_data)

            update.message.reply_text("🥳 Unique deposit address created. Please only send TRX to this address. The minimum amount to send is 10 TRX. Smaller deposits will be ignored. The bot will automatically recognize the deposit, transactions usually take between 3~30 minutes, in special cases it may take up to 24 hours. Please be patient. 🙏")

            update.message.reply_text(f"💫 Your unique deposit address is:\n {address}")
        else:
            update.message.reply_text("⚠️ No user information found..")
    except:
        update.message.reply_text("⚠️ There was an error creating the wallet. Please try again later...")

def max_bonus(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_data = load_user_data()

    if user_id in user_data and "bonus" in user_data[user_id] and "last_bonus_time" in user_data[user_id]["bonus"]:
        last_bonus_time_str = user_data[user_id]["bonus"]["last_bonus_time"]
        
        if last_bonus_time_str:
            last_bonus_time = datetime.datetime.fromisoformat(last_bonus_time_str)
            current_time = datetime.datetime.now()

            if (current_time - last_bonus_time).days < 1:
                time_diff = current_time - last_bonus_time
                time_remaining = datetime.timedelta(days=1) - time_diff

                hours = time_remaining.seconds // 3600
                minutes = (time_remaining.seconds // 60) % 60
                seconds = time_remaining.seconds % 60

                time_remaining_str = ""
                if hours > 0:
                    time_remaining_str += f"{hours} hours "
                if minutes > 0:
                    time_remaining_str += f"{minutes} minutes "
                if seconds > 0:
                    time_remaining_str += f"{seconds} seconds"

                update.message.reply_text(f"⚠️ You have already received the daily bonus. Come back in {time_remaining_str} to receive another one.")               
                return

    bono_amount = round(random.uniform(0.01, 0.001), 8)

    current_time = datetime.datetime.now()
    current_time_str = current_time.isoformat()
    user_data[user_id].setdefault("bonus", {})["last_bonus_time"] = current_time_str

    if user_id in user_data and "saldo" in user_data[user_id]:
        user_data[user_id]["saldo"] += bono_amount
        user_data[user_id]["total_earned"] += bono_amount

        save_user_data(user_data)

        update.message.reply_text(f"🎉 You have received a bonus of {bono_amount} TRX")
    else:
        update.message.reply_text("⚠️ No user information found.")

WITHDRAW_AMOUNT, WITHDRAW_CONFIRMATION = range(2)

def retiro(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    saldo = user_data[user_id].get("saldo")
    saldo_str = remove_trailing_zeros(round(saldo, 8))
    user_wallet = user_data[user_id].get("user_wallet")
    user_total_deposit = user_data[user_id].get("total_deposit")
    u_t_dep_str = remove_trailing_zeros(round(user_total_deposit, 8))
    
    if saldo < 10:
        update.message.reply_text(f"⚠️ Your balance is insufficient to make a withdrawal.\n\n💰 Available Balance: {saldo_str} TRX\n💰 Minimum Balance: 10 TRX\n\n🆒 Recommended commands:\n /deposit \n /reinvest")
        return ConversationHandler.END
        
    if user_total_deposit < 10:
        update.message.reply_text(f"⚠️ You need to deposit at least 10 TRX to be able to make withdrawals\n\n💰 Total Deposited: {u_t_dep_str} TRX\n\n🆒 Recommended command:\n /deposit")
        return ConversationHandler.END
     
    if not user_wallet:
        update.message.reply_text("⚠️ You cannot make a withdrawal because you have not registered a withdrawal wallet. Please add a withdrawal wallet.")
        return ConversationHandler.END

    referral_link = user_data[user_id].get("link")
    referrals_count = len(user_data[user_id].get("referrals", []))
    if referrals_count < 3:
        update.message.reply_text(f"⚠️ You do not have the required number of referrals to make withdrawals.\n\n👥 Referrals: {referrals_count} / 3\n\n🔗 Your referral link is: {referral_link}\n\n🚀Keep sharing your referral link and you will achieve great results! 💪")
        return ConversationHandler.END

    last_withdraw_time = user_data[user_id].get("last_withdraw_time")
    if last_withdraw_time:
        last_withdraw_date = datetime.datetime.fromisoformat(last_withdraw_time).strftime("%Y-%m-%d %H:%M:%S")
        time_difference = datetime.datetime.now() - datetime.datetime.fromisoformat(last_withdraw_time)
        if time_difference.total_seconds() < 24 * 60 * 60:
            tiempo_restante = datetime.timedelta(seconds=(24 * 60 * 60 - time_difference.total_seconds()))

            tiempo_str = ""
            if tiempo_restante.seconds >= 3600:
                horas = tiempo_restante.seconds // 3600
                tiempo_str += f"{horas} hours "
                tiempo_restante -= datetime.timedelta(hours=horas)
            if tiempo_restante.seconds >= 60:
                minutos = tiempo_restante.seconds // 60
                tiempo_str += f"{minutos} minutes "
                tiempo_restante -= datetime.timedelta(minutes=minutos)
            segundos = tiempo_restante.seconds
            tiempo_str += f"{segundos} seconds"

            update.message.reply_text(f"⚠️ You cannot make a withdrawal because you have already made one in the last 24 hours.\n\nLast withdrawal made on: {last_withdraw_date}\n⏳ Time remaining until the next withdrawal: {tiempo_str}\n\n🆒 Recommended command:\n /reinvest")
            return ConversationHandler.END

    keyboard = [['❌ Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(f"🔰 Balance withdrawal request🔰\n\n💵 Available Balance: {saldo_str} TRX\n\n👇 Please enter the amount you wish to withdraw:", reply_markup=reply_markup)
    return WITHDRAW_AMOUNT

def monto(update: Update, context: CallbackContext) -> None:
    monto = update.message.text
    user_data = load_user_data()
    user_id = str(update.effective_user.id)
    saldo = user_data[user_id].get("saldo")
    user_total_deposit = user_data[user_id].get("total_deposit")

    if isinstance(saldo, (int, float)):
        try:
            monto = float(monto)
            if monto < 10 or monto > saldo:
                update.message.reply_text(f"⚠️ The entered amount is not valid. Please try again.")
                return WITHDRAW_AMOUNT

            if MAX_WITHDRAW_LIMIT:
                diferencia = monto - user_total_deposit
                if diferencia < 10:
                    diferencia += 10

                if monto > user_total_deposit:
                    update.message.reply_text(f"⚠️ You have exceeded the maximum withdrawal amount. To withdraw {monto} TRX, you need to deposit an additional {diferencia} TRX.")
                    return WITHDRAW_AMOUNT

            context.user_data['saldo'] = monto

            keyboard = [['✅ Yes', '❌ No']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            update.message.reply_text(f"💰 Withdrawal Confirmation 💰\n\n🌐 Network Fee: 5%\n🏧 Withdrawal Fee: 3 TRX\n\n⚡ Are you sure you want to withdraw {monto} TRX?", reply_markup=reply_markup)
            return WITHDRAW_CONFIRMATION
        except ValueError:
            reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            update.message.reply_text("⚠️ Canceled...", reply_markup=reply_markup)
            return ConversationHandler.END
    else:
        update.message.reply_text(f"⚠️ You do not have enough balance to make the withdrawal.")
        return WITHDRAW_CONFIRMATION

def confirm_monto(update: Update, context: CallbackContext) -> None:
    bot = Bot(TOKEN)
    respuesta = update.message.text.lower()
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    user_wallet = user_data[user_id].get("user_wallet")
    user_link = user_data[user_id].get("link")
    admin_wallet_key = ADMIN_WALLET_KEY
  
    if respuesta == '✅ yes':
        monto = context.user_data['saldo']
        monto_descontado = monto * 0.05
        monto_desc = monto - monto_descontado
        monto_reduc = monto_desc - 3
        amount_sun = monto_reduc * 10**6
        
        update.message.reply_text(f"🌟 Withdrawal Success 🌟\n\n✅ Your withdrawal is being processed automatically right now! Most transfers are usually instantaneous. Please be patient. 🙏\n\n📝 Withdrawal Details:\n💰 Amount: {monto_reduc} TRX\n💳 Wallet: {user_wallet} \n\n📉 Check Withdrawal Status 👇\n🚀 {CHANNEL}")
        
        # API to get price
        api_url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd"
        trx_response = requests.get(api_url)
        price = trx_response.json()
        tron_price = price["tron"]["usd"]
        monto_to_price = monto_reduc * tron_price
        
        # API to send payments
        url = f"https://verceltron.vercel.app/sent/{user_wallet}/{amount_sun}/{admin_wallet_key}"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            txid = data['response']['txid']
            user_data[user_id]['saldo'] -= monto
            user_data[user_id]['total_withdrawn'] += monto
         
            # Agregar retiro al historial de retiros
            if "withdraw_history" not in user_data[user_id] or not isinstance(user_data[user_id]["withdraw_history"], list):
                user_data[user_id]["withdraw_history"] = []

            user_data[user_id]["withdraw_history"].append({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "amount": monto_reduc,
                "status": "done"
            })

            save_user_data(user_data)
            
            update.message.reply_text(f"🎉 Withdrawal Successful 🎉\n\nYour Withdrawal of {monto_reduc} TRX has been payed to your wallet {user_wallet} \n\n🆔 TXID: {txid}")

            user_link_formatted = user_link.replace("_", "\_")
            mensaje = f"✅ WITHDRAWAL SUCCESS ✅\n\n👤 USER ID: {user_id}\n💰 AMOUNT: {monto_reduc} TRX\n💲USD($): {monto_to_price} USD\n🆔 TXID: [{txid}](https://tx.botdev.me/TRX/{txid})\n\n🤖 Bot: {user_link_formatted}"
            context.bot.send_message(chat_id=CHANNEL, text=mensaje, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            update.message.reply_text(f"❌ Error processing withdrawal!\n⚠️ Error: Server congestion\n\nPlease try again later.\n\n♻️ Refunded Balance: {monto} TRX", reply_markup=reply_markup)
            return ConversationHandler.END
    else:
        reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        update.message.reply_text("❌ Withdrawal canceled.", reply_markup=reply_markup)

    return ConversationHandler.END

def exit_retiro(update: Update, context: CallbackContext) -> None:
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    update.message.reply_text("❌ Withdrawal canceled.", reply_markup=reply_markup)
    return ConversationHandler.END
    
def exit_all(update: Update, context: CallbackContext) -> None:
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    update.message.reply_text("❌ Operation canceled.", reply_markup=reply_markup)
    return ConversationHandler.END
    
def obtener_todas_transacciones(user_wallet):
    url = f"https://api.trongrid.io/v1/accounts/{user_wallet}/transactions?only_to=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            transactions = data.get("data")
            if transactions:
                transacciones = []
                for transaction in transactions:
                    txID = transaction["txID"]
                    balance = transaction["raw_data"]["contract"][0]["parameter"]["value"]["amount"]
                    transacciones.append({"txID": txID, "balance": balance})
                return transacciones
    return []

def verificar_billeteras_de_deposito():
    while True:
        bot = Bot(TOKEN)
        user_data = load_user_data()
        transacciones_procesadas = cargar_transacciones_procesadas()
        for user_id, user_info in user_data.items():
            user_id = user_info.get("id")
            user_name = user_info.get("user_name")
            user_link = user_info.get("link")
            user_wallet_key = user_info.get("deposit_wallet", {}).get("private_key")
            user_wallet = user_info.get("deposit_wallet", {}).get("wallet")
            if user_wallet:
                transacciones = obtener_todas_transacciones(user_wallet)
                for transaction in transacciones:
                    txID = transaction["txID"]
                    balance = transaction["balance"]
                    if txID in transacciones_procesadas:
                        continue
                        
                    if balance < 10000000:
                        transacciones_procesadas.add(txID)
                        guardar_transacciones_procesadas(transacciones_procesadas)
                        # Send balance to admin wallet
                        adm_wallet = ADMIN_WALLET
                        url = f"https://verceltron.vercel.app/sent/{adm_wallet}/{balance}/{user_wallet_key}"
                        response = requests.get(url)
                        amount_sun = balance / 10**6
                        amount_formatted = remove_trailing_zeros(amount_sun)
                        final_amount = float(amount_formatted)
                        mensaje = f"📌 New deposit received below the established amount, it has been sent to the main wallet. 📝 Details:\n\n💰 Deposit value: {final_amount} TRX\n👤 User: {user_name}\n🆔 {user_id}"
                        bot.send_message(chat_id=ADMIN_ID, text=mensaje)
                        continue

                    fecha_inicio = datetime.datetime.now().replace(second=0, microsecond=0)
                    fecha_final = fecha_inicio + datetime.timedelta(hours=24)
                    amount_sun = balance / 10**6
                    amount_formatted = remove_trailing_zeros(amount_sun)
                    amount_decimal = float(amount_formatted)
                    ganancia = amount_decimal * 1.35
                    if "invest_history" not in user_info or not isinstance(user_info["invest_history"], list):
                        user_info["invest_history"] = []
                    
                    if user_data[user_id]["invest_history"]:
                        last_investment = user_data[user_id]["invest_history"][-1]
                        last_investment_id = last_investment["investment_id"]
                        new_investment_id = str(int(last_investment_id) + 1)
                    else:
                        new_investment_id = "1000000"
                    
                    boost_link = user_link + "_" + new_investment_id

                    user_info["invest_history"].append({
                        "investment_id": new_investment_id,
                        "amount": amount_decimal,
                        "profit": ganancia,
                        "status": "active",
                        "type": "Deposit",
                        "start_date": fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                        "end_date": fecha_final.strftime("%Y-%m-%d %H:%M"),
                        "boost_link": boost_link,
                        "boost_times": 0
                    })
                    
                    user_info["total_deposit"] += amount_decimal
                    
                    referral_id = user_info.get("referral_id")
                    if referral_id and referral_id != user_id and referral_id in user_data:
                        referral_user = user_data[referral_id]
                        referral_amount = amount_decimal * 0.15
                        referral_amount_str = remove_trailing_zeros(round(referral_amount, 8))
                        referral_user["saldo"] += referral_amount
                        referral_user["ref_earn"] += referral_amount
                        referral_user["total_earned"] += referral_amount
                        mensaje_referente = f"🎉 Congratulations! Your referral {user_name} has made a deposit of {amount_decimal} TRX, and you have received {referral_amount_str} TRX. Keep sharing your link to earn more rewards like this.\n\n🔗 Your referral link: {user_link}"
                        bot.send_message(chat_id=referral_id, text=mensaje_referente)

                    save_user_data(user_data)
                    
                    # Send TRX to adm wallet 
                    adm_wallet = ADMIN_WALLET
                    url = f"https://verceltron.vercel.app/sent/{adm_wallet}/{balance}/{user_wallet_key}"
                    response = requests.get(url)
                    
                    api_url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd"
                    trx_response = requests.get(api_url)
                    price = trx_response.json()
                    tron_price = price.get("tron", {}).get("usd", 0)
                    tron_decimal = float(tron_price)
                    monto_to_price = amount_decimal * tron_decimal
                    amount_to_price = remove_trailing_zeros(monto_to_price)
                    ganancia_esperada = remove_trailing_zeros(round(ganancia, 8))

                    mensaje = f"✅ New Deposit Received ✅\n\n🔰 Deposit Details 🔰\n\n💰 Amount: {amount_formatted} TRX.\n💵 Spected Profit: {ganancia_esperada} TRX.\n⏳ Start Date: {fecha_inicio}.\n⌛ End Date: {fecha_final}.\n\n🚀 Thank you for depositing your trust in us! 🚀\n\n💫 Want to boost your deposit returns by 2x the speed? Send /boost command to learn how!"
                    bot.send_message(chat_id=user_id, text=mensaje)
                    user_link_formatted = user_link.replace("_", "\_")
                    mensaje = f"☑️ NEW DEPOSIT RECEIVED ☑️\n\n👤 USER ID: {user_id}\n💰 AMOUNT: {amount_formatted} TRX\n💲 USD($): {amount_to_price} USD\n🆔 TXID: [{txID}](https://tx.botdev.me/TRX/{txID})\n\n🤖 Bot: {user_link_formatted}"
                    bot.send_message(chat_id=CHANNEL, text=mensaje, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

                    transacciones_procesadas.add(txID)
                    guardar_transacciones_procesadas(transacciones_procesadas)

        time.sleep(2)
        
def cargar_transacciones_procesadas():
    try:
        with open(TRANSACTIONS_FILE, "r") as file:
            transacciones_procesadas = set(json.load(file))
    except FileNotFoundError:
        transacciones_procesadas = set()
    return transacciones_procesadas

def guardar_transacciones_procesadas(transacciones_procesadas):
    with open(TRANSACTIONS_FILE, "w") as file:
        json.dump(list(transacciones_procesadas), file)

def start_verificar_billeteras_de_deposito():
    thread = threading.Thread(target=verificar_billeteras_de_deposito)
    thread.start()
    print("Verificar_Billeteras_de_Deposito task started successfully.")

start_verificar_billeteras_de_deposito()

def show_referral_rank(update: Update, context: CallbackContext) -> None:
    user_data = load_user_data()
    bot_config = load_bot_config()

    top_users = sorted(user_data.values(), key=lambda x: len(x.get("referrals", {})), reverse=True)
    top_users = [user_info for user_info in top_users if len(user_info.get("referrals", {})) > 0][:10]

    message = "🏆 Top 10 Users🏆\n\n"

    # Calcular el tiempo restante para el próximo bono
    last_bonus_time_str = bot_config.get("last_bonus_time")
    if last_bonus_time_str:
        last_bonus_time = datetime.datetime.fromisoformat(last_bonus_time_str)
        next_bonus_time = last_bonus_time + datetime.timedelta(hours=24)
        remaining_time = next_bonus_time - datetime.datetime.now()

        remaining_hours = int(remaining_time.total_seconds() // 3600)
        remaining_minutes = int((remaining_time.total_seconds() % 3600) // 60)
        remaining_seconds = int(remaining_time.total_seconds() % 60)

        if remaining_hours < 0:
            remaining_hours = 0
        if remaining_minutes < 0:
            remaining_minutes = 0
        if remaining_seconds < 0:
            remaining_seconds = 0

        message += f"⏳ Remaining Time: {remaining_hours} hours {remaining_minutes} minutes {remaining_seconds} seconds\n\n"

    for i, user_info in enumerate(top_users, 1):
        user_id = user_info["id"]
        username = user_info.get("user_name")
        if not username:
            username = str(user_id)
        referrals = len(user_info.get("referrals", {}))
        earned = user_info.get("ref_earn", 0)
        earned_str = remove_trailing_zeros(round(earned, 8))
        message += f"{i}. {username}:  {referrals} ~~~ ➕ {earned_str} TRX\n"

    user_id = str(update.effective_user.id)
    user_info = user_data.get(user_id)
    if user_info:
        user_link = user_info.get("link")
        if user_link:
            message += f"\n🔗 Your referral link: {user_link}"

    message += "\n\nKeep inviting your friends and earn even more with your referral link! 🚀💸"

    update.message.reply_text(message)

def referral_rank_bonus():
    while True:
        bot = Bot(TOKEN)
        user_data = load_user_data()
        bot_config = load_bot_config()

        top_users = sorted(user_data.values(), key=lambda x: len(x.get("referrals", {})), reverse=True)[:5]
        top_users = [user_info for user_info in top_users if len(user_info.get("referrals", {})) >= 1]

        bonuses = [0.1, 0.01, 0.001, 0.0001, 0.00001]

        current_time = datetime.datetime.now()
        last_bonus_time_str = bot_config.get("last_bonus_time")
        last_bonus_time = datetime.datetime.fromisoformat(last_bonus_time_str) if last_bonus_time_str else None

        if not last_bonus_time or (current_time - last_bonus_time).total_seconds() >= 86400:
            for i, user_info in enumerate(top_users):
                user_id = user_info["id"]
                user_link = user_info["link"]
                bonus = bonuses[i]

                user_info["saldo"] += bonus
                user_info["ref_earn"] += bonus
                user_info["total_earned"] += bonus

                save_user_data(user_data)
                
                message = f"🎉 Congratulations! You have reached the {i+1} position in the referral ranking. You have received a bonus of {bonus} TRX. Keep up the good work!\n\n🔗 Your referral link is: {user_link}\n\nKeep inviting your friends and earn even more 🚀💸"
                bot.send_message(chat_id=user_id, text=message)

            bot_config["last_bonus_time"] = current_time.isoformat()
            save_bot_config(bot_config)

        time.sleep(1)

def start_referral_rank_bonus():
    thread = threading.Thread(target=referral_rank_bonus)
    thread.start()
    print("Referral_Rank_Bonus task started successfully.")

start_referral_rank_bonus()

def boost(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id in user_data:
        invest_history = user_data[user_id].get("invest_history", [])
        
        if invest_history:
            message = "🚀 Boost your investments by 2x the speed!\nInvite a friend now and slice your wait time for investment returns right down by half! Rally your friends to join in and watch how quickly you all move forward.\n\n✅ Active Investments:\n\n"
            
            for investment in invest_history:
                if investment["status"] == "active":
                    amount = investment["amount"]
                    boost_link = investment["boost_link"]
                    investment_id = investment["investment_id"]
                    boost_times = investment["boost_times"]
                    
                    message += f"🆔 ID: {investment_id}(Boosted {boost_times} times)\n💰 Amount: {amount} TRX\n🚀 Boost Link: {boost_link}\n\n"
            
            update.message.reply_text(message)
        else:
            update.message.reply_text("⚠️ You don't have any active investments.")
    else:
        update.message.reply_text("⚠️ User data not found.")

def handle_text(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.text:
        text = update.message.text
        if text == "🚀 Start":
            return start(update, context)
        elif text == "ℹ️ Info":
            return info(update, context)
        elif text == "🔙 Back":
            return start(update, context)
        elif text == "✅ Joined":
            return start_main(update, context)
        elif text == "✖️ Cancel":
            return admin(update, context)
        elif text == "❌ Cancel":
            return exit_all(update, context)
        elif text == "✖️ Cancel Action":
            return balance(update, context)
        elif text == "👥 Referrals":
            return show_referrals(update, context)
        elif text == "👥 Users":
            return get_users(update, context)
        elif text == "💳 Account":
            return balance(update, context)
        elif text == "⚡ Balance":
            return balance(update, context)
        elif text == "⚙️ Set Wallet":
            return set_wallet(update, context)
        elif text == "🔥 Deposit":
            return create_wallet(update, context)
        elif text == "♻️ Reinvest":
            return reinvest_start(update, context)
        elif text == "🎁 Bonus":
            return max_bonus(update, context)
        elif text == "🗣️ Announ":
            return request_announcement(update, context)
        elif text == "💸 Withdraw History":
            return show_withdraw_history(update, context)
        elif text == "♻️ Invest History":
            return invest_history(update, context)
        elif text == "🏆 Referral Rank":
            return show_referral_rank(update, context)
        elif context.user_data.get('is_announcing'):
            announce_to_users(update, context, text)

#updater
updater = Updater(token=TOKEN, use_context=True)

dp = updater.dispatcher

dp.add_handler(ConversationHandler(
    entry_points=[CommandHandler('set_wallet', set_wallet), MessageHandler(Filters.regex('^⚙️ Set Wallet$'), set_wallet)],
    states={
        SET_WALLET: [MessageHandler(Filters.text, capture_wallet)]
    },
    fallbacks=[]
))

dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('reinvest', reinvest_start), MessageHandler(Filters.regex('^♻️ Reinvest$'), reinvest_start)],
        states={
            REINVEST_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_reinvest_amount)],
            REINVEST_CONFIRMATION: [MessageHandler(Filters.regex('^(✅ Yes|❌ No)$'), reinvest_confirmation)]
        },
        fallbacks=[CommandHandler('cancel', cancel),MessageHandler(Filters.regex('^❌ Cancel$'), exit_all)]
    ))
    
dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('withdraw', retiro), MessageHandler(Filters.regex('^💸 Withdraw$'), retiro)],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(Filters.text, monto)],
            WITHDRAW_CONFIRMATION: [MessageHandler(Filters.regex('^(✅ Yes|❌ No)$'), confirm_monto)]
        },
        fallbacks=[MessageHandler(Filters.regex('^❌ Cancel$'), exit_all)]
    ))
    
dp.add_handler(ConversationHandler(
    entry_points=[CommandHandler("pin", pin_message), MessageHandler(Filters.regex('^📌 Pin Message$'), pin_message)],
    states={
        PIN_MESSAGE: [MessageHandler(Filters.text, handle_pin_message)]
    },
    fallbacks=[MessageHandler(Filters.regex('^❌ Back$'), exit_all)]
))

dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            'captcha_check': [MessageHandler(Filters.text, captcha_check)]
        },
        fallbacks=[]
    ))

dp.add_handler(CommandHandler('start', start))
dp.add_handler(CommandHandler('deposit', create_wallet))
dp.add_handler(CommandHandler('invest', create_wallet))
dp.add_handler(CommandHandler('boost', boost))
dp.add_handler(CommandHandler('bonus', max_bonus))
dp.add_handler(CommandHandler('info', info))
dp.add_handler(CommandHandler('admin', admin))
dp.add_handler(CommandHandler('show_referrals', show_referrals))
dp.add_handler(CommandHandler('balance', balance))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# Iniciar el bot
updater.start_polling()
print("Bot running and listening for changes.")
updater.idle()
