import logging
import sqlite3

import RPi.GPIO as GPIO
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

import dht11
from config import PI_SMARTHOME

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


translations = {'living_room': 'Гостиная',
                'bathroom': 'Ванная',
                'sleeping_room': 'Спальня'}

PI_PATH = '/home/pi/Desktop/smarthome/smarthome_data.db'
PATH = 'smarthome_data.db'

state_menu = dict()

class SQL(object):
    def do(self, query):
        self.connection = sqlite3.connect(PI_PATH, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute(query)
        self.connection.commit()
        self.connection.close()

    def execute(self, query):
        self.connection = sqlite3.connect(PI_PATH, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute(query)
        res = self.cursor.fetchall()
        self.connection.close()
        return res

sql = SQL()

tables = {'bathroom': 'CREATE TABLE bathroom (thing TEXT, is_on INTEGER)',
          'sleeping_room': 'CREATE TABLE sleeping_room (thing TEXT, is_on INTEGER)',
          'living_room': 'CREATE TABLE living_room (thing TEXT, is_on INTEGER)'}

try:
    for t in tables.values():
        sql.do(t)
except Exception as e:
    print(e)

def get_keyboard(menu=None):
    if menu is not None:
        keyboard_room = []
        if menu == 'sleeping_room':
            keyboard_room += [[InlineKeyboardButton('Температура', callback_data='get_temp')]]
        states = sql.execute('select thing, is_on from {}'.format(menu))
        if states:
            for thing, state in states:
                if bool(state) is True:
                    keyboard_room.append([InlineKeyboardButton('Выключить '+thing, callback_data='off_'+thing)])
                else:
                    keyboard_room.append([InlineKeyboardButton('Включить '+thing, callback_data='on_'+thing)])
            keyboard_room += [[InlineKeyboardButton('Назад', callback_data='back')]]
            return keyboard_room

    living_room = InlineKeyboardButton('Гостиная', callback_data='living_room')
    bathroom = InlineKeyboardButton('Ванная', callback_data='bathroom')
    sleeping_room = InlineKeyboardButton('Спальня', callback_data='sleeping_room')
    keyboard = [[living_room], [bathroom, sleeping_room]]
    return keyboard


def start(bot, update):
    print(update)
    uid = update.message.from_user.id
    msg = 'Привет! Я помогу контролировать твой дом!'
    bot.sendMessage(uid, msg, reply_markup=InlineKeyboardMarkup(get_keyboard()))


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


def temperature():
    temp = ''
    while True:
        result = instance.read()
        if result.is_valid():
            temp += '<b>Temperature:</b> {} C\n'.format(result.temperature)
            temp += '<b>Humidity:</b> {} %%'.format(result.humidity)
            if temp:
                break
        else:
            pass
    return temp


def on(thing):
    if 'lamp' in thing:
        GPIO.output(lamp_pin, GPIO.LOW)
        sql.do('update living_room set is_on=1 where thing="lamp"')
    elif 'socket' in thing:
        GPIO.output(socket_pin, GPIO.LOW)
        sql.do('update living_room set is_on=1 where thing="socket"')
    return thing + ' Включил'


def off(thing):
    if 'lamp' in thing:
        GPIO.output(lamp_pin, GPIO.HIGH)
        sql.do('update living_room set is_on=0 where thing="lamp"')
    elif 'socket' in thing:
        GPIO.output(socket_pin, GPIO.HIGH)
        sql.do('update living_room set is_on=0 where thing="socket"')
    return thing + ' Включил'


def procces_value(bot, update):
    query = update.callback_query
    uid = query.from_user.id
    text = query.data
    bot.answerCallbackQuery(query.id, text='Обрабатываю!')
    if text.endswith('room'):
        state_menu[uid] = text
        bot.editMessageText(chat_id=uid,
                            message_id=query.message.message_id,
                            text='<b>{}</b>'.format(translations[text]),
                            reply_markup=InlineKeyboardMarkup(get_keyboard(menu=text)),
                            parse_mode=ParseMode.HTML)

    elif text.startswith('on'):
        res = on(text)
        bot.editMessageText(chat_id=uid, message_id=query.message.message_id, text=res,
                            reply_markup=InlineKeyboardMarkup(get_keyboard(state_menu[uid])))

    elif text.startswith('off'):
        res = off(text)
        bot.editMessageText(chat_id=uid, message_id=query.message.message_id, text=res,
                            reply_markup=InlineKeyboardMarkup(get_keyboard(state_menu[uid])))
    elif text == 'get_temp':
        bot.editMessageText(chat_id=uid, message_id=query.message.message_id,
                            text=temperature(), reply_markup=InlineKeyboardMarkup(get_keyboard(state_menu[uid])),
                            parse_mode=ParseMode.HTML)
    elif text == 'back':
        bot.editMessageText(chat_id=uid, message_id=query.message.message_id,
                            text='Выбери комнату',
                            reply_markup=InlineKeyboardMarkup(get_keyboard()))


updater = Updater(PI_SMARTHOME)

dp = updater.dispatcher
dp.add_handler(CommandHandler('start', start))
dp.add_handler(CallbackQueryHandler(procces_value))


updater.start_polling()
updater.idle()

