import requests
import telebot
from telebot import types
import time
import threading
import random
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TOKEN = ""  # Aqui colocas el token generado por bot father
bot = telebot.TeleBot(TOKEN)


running_flags = {}
message_ids = {}
lock = threading.Lock()

frases_libertad = ["Bitcoin es libertad financiera: sin bancos, sin fronteras, sin permiso.",
    "El dinero es poder, y Bitcoin devuelve ese poder a las personas.",
    "No confíes, verifica. Bitcoin es transparencia en un mundo de mentiras.",
    "Con Bitcoin, eres tu propio banco. Nadie puede congelarte la libertad.",
    "La inflación es el impuesto oculto; Bitcoin es la resistencia.",
    "Bitcoin no pide permiso: es dinero sin gobiernos, sin censura.",
    "La clave de tu Bitcoin es la clave de tu soberanía.",
    "En un mundo de control, Bitcoin es el último bastión de libertad.",
    "Bitcoin es el dinero del pueblo, no de los políticos.",
    "Si no posees tus claves, no posees tus bitcoins… ni tu libertad."]


stop_keyboard = types.InlineKeyboardMarkup()
stop_button = types.InlineKeyboardButton("Detener", callback_data="stop_bot")
stop_keyboard.add(stop_button)

def get_btc_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        response.raise_for_status()
        data = response.json()
        return f"$ BTC: ${data['bitcoin']['usd']:,}"
    except Exception as e:
        logger.error(f"Error obteniendo precio BTC: {e}")
def mensaje_libertad():
    return f"⚠️ {random.choice(frases_libertad)}"

def get_mempool_fees():
    try:
        response = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10)
        response.raise_for_status()
        data = response.json()
        return (f"⛏️ Tarifas Mempool:\n"
                f"⚡ Alta: {data['fastestFee']} sat/vB\n"
                f"🕒 Media: {data['halfHourFee']} sat/vB\n"
                f"⏳ Baja: {data['hourFee']} sat/vB")
    except Exception as e:
        logger.error(f"Error obteniendo tarifas mempool: {e}")
        return f"⚠️ {random.choice(frases_libertad)}"

def send_periodic_messages(chat_id):
    while True:
        with lock:
            if not running_flags.get(chat_id, False):
                break

        try:
            btc_price = get_btc_price()
            mempool_fees = get_mempool_fees()

            with lock:
                if not running_flags.get(chat_id, False):
                    break

                msg1 = bot.send_message(chat_id, btc_price)
                msg2 = bot.send_message(chat_id, mempool_fees, reply_markup=stop_keyboard)

                if chat_id not in message_ids:
                    message_ids[chat_id] = []
                message_ids[chat_id].extend([msg1.message_id, msg2.message_id])

        except Exception as e:
            logger.error(f"Error en send_periodic_messages: {e}")

        time.sleep(60)

def clear_chat_history(chat_id):
    while True:
        with lock:
            if not running_flags.get(chat_id, False):
                break

        try:
            with lock:
                if chat_id in message_ids and message_ids[chat_id]:
                    for msg_id in message_ids[chat_id][:]: 
                        try:
                            bot.delete_message(chat_id, msg_id)
                            message_ids[chat_id].remove(msg_id)
                        except Exception as e:
                            if "message to delete not found" not in str(e):
                                logger.error(f"Error borrando mensaje: {e}")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error en clear_chat_history: {e}")
            time.sleep(60)

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    
    with lock:
        running_flags[chat_id] = True
        if chat_id not in message_ids:
            message_ids[chat_id] = []
    
    bot.reply_to(message, "🤖 BOT INICIADO...\n\n⚡Bitcoin minuto a minuto ⚡\n🔥 Precio actual\n🔥Tarifas en tiempo real\n\nToca Detener si no me necesitas 🙁")
    
    
    threading.Thread(target=send_periodic_messages, args=(chat_id,), daemon=True).start()
    threading.Thread(target=clear_chat_history, args=(chat_id,), daemon=True).start()

@bot.callback_query_handler(func=lambda call: call.data == 'stop_bot')
def stop_bot(call):
    chat_id = call.message.chat.id
    
    with lock:
        running_flags[chat_id] = False
        if chat_id in message_ids:
            
            for msg_id in message_ids[chat_id][:]:
                try:
                    bot.delete_message(chat_id, msg_id)
                except Exception as e:
                    if "message to delete not found" not in str(e):
                        logger.error(f"Error borrando mensaje al detener: {e}")
            message_ids[chat_id] = []
     
    try:
        confirmation = bot.send_message(chat_id, "✋ Bot detenido gracias por utilizar el servicio\nEscribe /start para reiniciar")
        time.sleep(5)
        bot.delete_message(chat_id, confirmation.message_id)
    except Exception as e:
        logger.error(f"Error mostrando confirmación: {e}")
    
    bot.answer_callback_query(call.id, "Bot detenido")

if __name__ == '__main__':
    logger.info("Bot iniciado...")
    bot.infinity_polling()
