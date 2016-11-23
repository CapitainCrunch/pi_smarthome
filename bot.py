import RPi.GPIO as GPIO
import time
from DHT11 import dht11
from telegram import ReplyKeyboardMarkup, ParseMode, Emoji, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardHide
from telegram.ext import Updater, CommandHandler, RegexHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from config import PI_SMARTHOME, ADMIN_ID
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)



GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# motion
GPIO.setup(25, GPIO.IN)

# temp
instance = dht11.DHT11(pin=14)

socket_pin = 24
GPIO.setup(socket_pin, GPIO.OUT)

lamp_pin = 22
GPIO.setup(lamp_pin, GPIO.OUT)


def get_layout(**kwargs):
    lamp = 'Включить лампу'
    socket = 'Включить розетку'

    if kwargs.get('lamp'):
        lamp = 'Выключить лампу'

    if kwargs.get('socket'):
        socket = 'Выключить розетку'

    keyboard = [['Температура'], [lamp, socket]]
    return keyboard


def motion():
    while True:
        pass
        # i = GPIO.input(25)
        # if i == 0:
        #     print("No intruders", i)
        #     time.sleep(0.1)
        # else:
        #     print("Intruder detected", i)
        #     time.sleep(0.1)


def temperature(bot, update):
    uid = update.message.from_user.id
    msg = ''
    while True:
        result = instance.read()
        if result.is_valid():
            msg += 'Temperature: {} C\n'.format(result.temperature)
            msg += 'Humidity: {} %%'.format(result.humidity)
            if msg:
                bot.sendMessage(uid, msg, reply_markup=ReplyKeyboardMarkup(get_layout()))
                break
        else:
            pass


def lamp(bot, update):
    uid = update.message.from_user.id
    message = update.message.text
    if 'лампу' in message:
        if message.startswith('Включить'):
            GPIO.output(lamp_pin, GPIO.LOW)
            bot.sendMessage(uid, 'Лампу включил', reply_markup=ReplyKeyboardMarkup(get_layout(lamp=True)))
        else:
            GPIO.output(lamp_pin, GPIO.HIGH)
            bot.sendMessage(uid, 'Лампу выключил', reply_markup=ReplyKeyboardMarkup(get_layout(lamp=False)))


def socket(bot, update):
    uid = update.message.from_user.id
    message = update.message.text
    if 'розетку' in message:
        if message.startswith('Включить'):
            GPIO.output(socket_pin, GPIO.LOW)
            bot.sendMessage(uid, 'Розетку включил', reply_markup=ReplyKeyboardMarkup(get_layout(socket=True)))
        else:
            GPIO.output(socket_pin, GPIO.HIGH)
            bot.sendMessage(uid, 'Розетку выключил', reply_markup=ReplyKeyboardMarkup(get_layout(socket=False)))


def start(bot, update):
    print(update)
    bot.sendMessage(update.message.chat_id, text='Hi!', reply_markup=ReplyKeyboardMarkup(get_layout()))



updater = Updater(PI_SMARTHOME)

dp = updater.dispatcher
dp.add_handler(CommandHandler('start', start))
dp.add_handler(RegexHandler('^Температура$', temperature))
dp.add_handler(RegexHandler('^.*лампу$', lamp))
dp.add_handler(RegexHandler('^.*розетку', socket))

updater.start_polling()
updater.idle()

