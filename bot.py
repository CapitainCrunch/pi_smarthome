# import RPi.GPIO as GPIO
import time
import logging
import requests
import transmissionrpc
import os
import sys
import threading
from datetime import datetime as dt
# from DHT11 import dht11
from telegram import ReplyKeyboardMarkup, ParseMode, Emoji, \
    ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardHide, MessageEntity, Bot
from telegram.ext import Updater, CommandHandler, RegexHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram.ext.dispatcher import run_async
from config import PI_SMARTHOME, ADMIN_ID, ALLTESTS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

#
# GPIO.setwarnings(False)
# GPIO.setmode(GPIO.BCM)
#
# # motion
# GPIO.setup(25, GPIO.IN)
#
# # temp
# instance = dht11.DHT11(pin=14)
#
# socket_pin = 24
# GPIO.setup(socket_pin, GPIO.OUT)
#
# lamp_pin = 22
# GPIO.setup(lamp_pin, GPIO.OUT)
#
#
# def get_layout(**kwargs):
#     lamp = 'Включить лампу'
#     socket = 'Включить розетку'
#
#     if kwargs.get('lamp'):
#         lamp = 'Выключить лампу'
#
#     if kwargs.get('socket'):
#         socket = 'Выключить розетку'
#
#     keyboard = [['Температура'], [lamp, socket]]
#     return keyboard
#
#
# def motion():
#     while True:
#         pass
#         # i = GPIO.input(25)
#         # if i == 0:
#         #     print("No intruders", i)
#         #     time.sleep(0.1)
#         # else:
#         #     print("Intruder detected", i)
#         #     time.sleep(0.1)
#
#
# def temperature(bot, update):
#     uid = update.message.from_user.id
#     msg = ''
#     while True:
#         result = instance.read()
#         if result.is_valid():
#             msg += 'Temperature: {} C\n'.format(result.temperature)
#             msg += 'Humidity: {} %%'.format(result.humidity)
#             if msg:
#                 bot.sendMessage(uid, msg, reply_markup=ReplyKeyboardMarkup(get_layout()))
#                 break
#         else:
#             pass
#
#
# def lamp(bot, update):
#     uid = update.message.from_user.id
#     message = update.message.text
#     if 'лампу' in message:
#         if message.startswith('Включить'):
#             GPIO.output(lamp_pin, GPIO.LOW)
#             bot.sendMessage(uid, 'Лампу включил', reply_markup=ReplyKeyboardMarkup(get_layout(lamp=True)))
#         else:
#             GPIO.output(lamp_pin, GPIO.HIGH)
#             bot.sendMessage(uid, 'Лампу выключил', reply_markup=ReplyKeyboardMarkup(get_layout(lamp=False)))
#
#
# def socket(bot, update):
#     uid = update.message.from_user.id
#     message = update.message.text
#     if 'розетку' in message:
#         if message.startswith('Включить'):
#             GPIO.output(socket_pin, GPIO.LOW)
#             bot.sendMessage(uid, 'Розетку включил', reply_markup=ReplyKeyboardMarkup(get_layout(socket=True)))
#         else:
#             GPIO.output(socket_pin, GPIO.HIGH)
#             bot.sendMessage(uid, 'Розетку выключил', reply_markup=ReplyKeyboardMarkup(get_layout(socket=False)))

CHOOSE_MENU = range(1)
start_keyboard = [['Торренты']]

def start(bot, update):
    print(update)
    bot.sendMessage(update.message.chat_id, text='Hi!', reply_markup=ReplyKeyboardMarkup(start_keyboard, resize_keyboard=True))


def get_torrent_file_and_download(bot, update):
    url = update.message.text
    tc = transmissionrpc.Client()
    uid = update.message.from_user.id
    fname = str(dt.now()) + '.torrent'
    fpath = os.path.abspath(fname)
    if url.startswith('magnet'):
        fpath = url
    elif update.message.document:
        file_id = update.message.document.file_id
        torrent_file = bot.getFile(file_id)
        tc = transmissionrpc.Client()
        fpath = torrent_file.file_path
    else:
        with open(fname, 'wb') as out_stream:
            req = requests.get(url, stream=True)
            if req.headers._store.get('content-type')[1] == 'application/x-bittorrent':
                for chunk in req.iter_content(1024):
                    out_stream.write(chunk)
    added_torrent = tc.add_torrent(fpath)
    tname = added_torrent._fields['name'][0]
    bot.sendMessage(uid, 'Начинаю скачивать <b>' + tname + '</b>', parse_mode=ParseMode.HTML,
                    reply_markup=ReplyKeyboardMarkup(start_keyboard, resize_keyboard=True))
    os.remove(fpath)


def torrents(bot, update):
    uid = update.message.from_user.id
    tc = transmissionrpc.Client()
    msg = ''
    all_torrents = tc.get_torrents()
    if all_torrents:
        for t in all_torrents:
            msg += t.name + '\n'
            try:
                msg += str(t.eta) + '\n'
            except:
                pass
            msg += t.status + '\n'
            if t.status == 'downloading':
                msg += '/stop_' + str(t.id) + '\n'
            else:
                msg += '/start_' + str(t.id) + '\n'
            msg += '/remove_' + str(t.id) + '\n'
        bot.sendMessage(uid, msg)
    else:
        bot.sendMessage(uid, 'Торрентов нет')


def handle_torrent(bot, update):
    uid = update.message.from_user.id
    message = update.message.text.strip('/')
    cmd, torrent_id = message.split('_')
    tc = transmissionrpc.Client()
    if cmd == 'start':
        tc.start_torrent(torrent_id)
    elif cmd == 'stop':
        tc.stop_torrent(torrent_id)
    else:
        tc.remove_torrent(torrent_id, delete_data=True)


def check_torrents(bot):
    tc = transmissionrpc.Client()
    while True:
        for t in tc.get_torrents():
            if t.status in ('seed pending', 'seeding'):
                bot.sendMessage(ADMIN_ID, 'Скачал ' + t.name)
            time.sleep(60)


if __name__ == '__main__':
    updater = None
    token = None
    bot = None
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        token = sys.argv[-1]
        if token.lower() == 'pi':
            updater = Updater(PI_SMARTHOME)
            bot = Bot(PI_SMARTHOME)
            logging.basicConfig(filename=BASE_DIR + '/out.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    else:
        updater = Updater(ALLTESTS)
        bot = Bot(ALLTESTS)
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    checking = threading.Thread(target=check_torrents, args=(bot,), name='check_torrents').start()
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler([Filters.entity(MessageEntity.URL) | Filters.document], get_torrent_file_and_download))
    dp.add_handler(RegexHandler('^Торренты$', torrents))
    dp.add_handler(RegexHandler('^/\w+_\d+', handle_torrent))
    # dp.add_handler(RegexHandler('^Температура$', temperature))
    # dp.add_handler(RegexHandler('^.*лампу$', lamp))
    # dp.add_handler(RegexHandler('^.*розетку', socket))
    updater.start_polling()
    updater.idle()



