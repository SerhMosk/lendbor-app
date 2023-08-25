import json

import telebot
from telebot import types
from datetime import datetime as dt
from prettytable import PrettyTable

from app import app
from config import AppConfig
from services import WeatherService, WeatherServiceException, UserService, RecordService, RecordServiceException, \
    PaymentService, PaymentServiceException
from rates_handler import RatesHandler

commands = ('<b>Available commands:</b>\n'
            '/start - initialize main menu\n'
            '/help - show available commands\n'
            '/rates - get BTC and ETH rates\n'
            '/weather - get weather in entered city\n'
            '/lends - show your lends\n'
            '/borrows - show your borrows\n'
            '/payments - show your payments\n'
            '/record - show record detail by id\n'
            '/payment - show payment detail by id\n'
            '/add - create new lend or borrow record\n'
            '/pay - create new payment')

bot = telebot.TeleBot(AppConfig.TELEGRAM_TOKEN)


def create_user(data):
    with app.app_context():
        user = UserService(data.first_name, data.id, data.is_bot, data.language_code, data.last_name, data.username)
        return user.get_user()


def send_rates(message):
    rh = RatesHandler()
    rates = rh.get_stored_rates()
    text = f'<b>Rates</b>\nBTC/USDT: {rates.get("BTCUSDT")}\nETH/USDT: {rates.get("ETHUSDT")}'

    bot.send_message(message.chat.id, text, parse_mode='HTML')


def request_city(message):
    sent = bot.reply_to(message, 'Enter your city name:')
    bot.register_next_step_handler(sent, get_locations)


def get_locations(message):
    try:
        geo_data = WeatherService.get_geo_data(city_name=message.text)
    except WeatherServiceException as wse:
        bot.send_message(message.chat.id, str(wse))
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)

        for item in geo_data:
            kb.add(types.InlineKeyboardButton(
                text=f"{item.get('name')} - {item.get('admin1')} - {item.get('country_code')}",
                callback_data=json.dumps({
                    'type': 'weather',
                    'lat': item.get('latitude'),
                    'lon': item.get('longitude')
                })
            ))

        bot.send_message(message.chat.id, 'Choose your city:', reply_markup=kb)


def send_weather(chat_id, data):
    try:
        weather = WeatherService.get_current_weather_by_geo_data(**data)
    except WeatherServiceException as wse:
        bot.send_message(chat_id, str(wse))
    else:
        result_time = dt.strptime(weather.get("time"), "%Y-%m-%dT%H:%M").strftime("%d.%m.%Y %H:%M")
        result = (f'- Temperature: {weather.get("temperature")},\n'
                  f'- Wind speed: {weather.get("windspeed")},\n'
                  f'- Wind direction: {weather.get("winddirection")},\n'
                  f'- Weather code: {weather.get("weathercode")},\n'
                  f'- Is day: {"Yes" if weather.get("is_day") == 1 else "No"},\n'
                  f'- Time: {result_time}')

        bot.send_message(chat_id, f'<b>Weather in your city:</b>\n{result}', parse_mode='HTML')


def set_record(message):
    bot.send_message(message.chat.id, message.text)


def create_record(message, record_type, title):
    params = message.text.split(', ')

    if len(params) == 6:
        with app.app_context():
            data = {
                'type': record_type,
                'name': params[0],
                'amount': params[1],
                'remains': params[1],
                'months': params[2],
                'payment_amount': params[3],
                'payment_day': params[4],
                'last_date': params[5],
            }
            try:
                rs = RecordService(message.from_user)
                rs.create_record(data)
            except RecordServiceException as rse:
                bot.send_message(message.chat.id, str(rse))
            else:
                bot.send_message(message.chat.id, f'<b>Added new {title}</b>\n'
                                                  f'name: {params[0]},\n'
                                                  f'amount: {params[1]},\n'
                                                  f'months: {params[2]},\n'
                                                  f'payment_amount: {params[3]},\n'
                                                  f'payment_day: {params[4]},\n'
                                                  f'last_date: {params[5]}', parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, 'You entered wrong params string.')


def create_payment(message):
    params = message.text.split(', ')

    if len(params) == 3:
        with app.app_context():
            data = {
                'record_id': params[0],
                'amount': params[1],
                'payment_date': params[2],
            }
            try:
                ps = PaymentService(message.from_user)
                ps.create_payment(data)
            except PaymentServiceException as pse:
                bot.send_message(message.chat.id, str(pse))
            else:
                bot.send_message(message.chat.id, f'<b>Added new Payment</b>\n'
                                                  f'record_id: {params[0]},\n'
                                                  f'amount: {params[1]},\n'
                                                  f'payment_date: {params[2]}', parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, 'You entered wrong params string.')


def request_record(message, record_type):
    sent = bot.reply_to(message, f'Type new {record_type} record data in format:\n'
                                 f'<name>, <amount>, <months>, <payment_amount>, <payment_day>, <last_date>\n'
                                 f'Example: Credit Card, 12000, 12, 1000, 25, 2024/08/25')
    if record_type == 'lend':
        bot.register_next_step_handler(sent, create_lend)
    else:
        bot.register_next_step_handler(sent, create_borrow)


def request_payment(message):
    sent = bot.reply_to(message, f'Type new payment data in format:\n'
                                 f'<record_id>, <amount>, <payment_date>\n'
                                 f'Example: 1, 1000, 2023/08/25')
    bot.register_next_step_handler(sent, create_payment)


def get_record(chat_id, from_user, data):
    with app.app_context():
        rs = RecordService(from_user)
        record = rs.get_record(data['id'])
        if record:
            text = (f'<b>Record detail:</b>\n'
                    f'id: {record.id}\n'
                    f'user_id: {record.user_id}\n'
                    f'type: {record.type}\n'
                    f'name: {record.name}\n'
                    f'amount: {record.amount}\n'
                    f'remains: {record.remains}\n'
                    f'months: {record.months}\n'
                    f'payment_amount: {record.payment_amount}\n'
                    f'payment_day: {record.payment_day}\n'
                    f'last_date: {record.last_date.strftime("%d.%m.%Y")}\n'
                    f'created_at: {record.created_at.strftime("%H:%M:%S %d.%m.%Y")}\n'
                    f'updated_at: {record.updated_at.strftime("%H:%M:%S %d.%m.%Y")}')

            kb = types.InlineKeyboardMarkup(row_width=1)
            btn = types.InlineKeyboardButton(
                text=f"🗑️ Delete",
                callback_data=json.dumps({
                    'type': 'record-delete',
                    'id': record.id,
                })
            )
            kb.add(btn)

            bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(chat_id, 'Record not found')


def get_payment(chat_id, from_user, data):
    with app.app_context():
        ps = PaymentService(from_user)
        payment = ps.get_payment(data['id'])
        if payment:
            text = (f'<b>Payment detail:</b>\n'
                    f'id: {payment.id}\n'
                    f'user_id: {payment.user_id}\n'
                    f'record_id: {payment.record_id}\n'
                    f'amount: {payment.amount}\n'
                    f'remains: {payment.remains}\n'
                    f'payment_date: {payment.payment_date.strftime("%d.%m.%Y")}\n'
                    f'created_at: {payment.created_at.strftime("%H:%M:%S %d.%m.%Y")}\n'
                    f'updated_at: {payment.updated_at.strftime("%H:%M:%S %d.%m.%Y")}')

            kb = types.InlineKeyboardMarkup(row_width=1)
            btn = types.InlineKeyboardButton(
                text=f"🗑️ Delete",
                callback_data=json.dumps({
                    'type': 'payment-delete',
                    'id': payment.id,
                })
            )
            kb.add(btn)

            bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)
        else:
            bot.send_message(chat_id, 'Record not found')


def delete_record(chat_id, data):
    with app.app_context():
        result = RecordService.delete_record(data['id'])
        if result:
            text = f'Record <b>#{data["id"]}</b> has been deleted'
        else:
            text = 'Record not found'
        bot.send_message(chat_id, text, parse_mode='HTML')


def delete_payment(chat_id, data):
    with app.app_context():
        result = PaymentService.delete_payment(data['id'])
        if result:
            text = f'Payment <b>#{data["id"]}</b> has been deleted'
        else:
            text = 'Payment not found'
        bot.send_message(chat_id, text, parse_mode='HTML')


def get_records_pt(records):
    pt = PrettyTable()
    pt.field_names = ['id', 'name', 'amount', 'remains', 'months', 'payment amount', 'payment day', 'last date']

    for item in records:
        pt.add_row([
            item.id,
            item.name,
            item.amount,
            item.remains,
            item.months,
            item.payment_amount,
            item.payment_day,
            item.last_date.strftime('%d.%m.%Y')
        ])

    return pt


def get_payments_pt(payments):
    pt = PrettyTable()
    pt.field_names = ['id', 'record id', 'amount', 'remains', 'payment date']

    for item in payments:
        pt.add_row([
            item.id,
            item.record_id,
            item.amount,
            item.remains,
            item.payment_date.strftime('%d.%m.%Y')
        ])

    return pt


def send_records(message, record_type, title):
    with app.app_context():
        rs = RecordService(message.from_user)
        records = rs.get_records(record_type)
        pt = get_records_pt(records)

        bot.send_message(message.chat.id, f'<b>Your {title} list</b>\n{pt}', parse_mode='HTML')

        kb = types.InlineKeyboardMarkup(row_width=2)

        for item in records:
            btn1 = types.InlineKeyboardButton(
                text=f"📂 #{item.id} - {item.name}",
                callback_data=json.dumps({
                    'type': 'record-detail',
                    'id': item.id,
                }),
            )
            btn2 = types.InlineKeyboardButton(
                text=f"🗑️ Delete",
                callback_data=json.dumps({
                    'type': 'record-delete',
                    'id': item.id,
                })
            )
            kb.add(btn1, btn2)

        bot.send_message(message.chat.id, f'<b>{title} detail:</b>', parse_mode='HTML', reply_markup=kb)


def send_payments(message):
    with app.app_context():
        ps = PaymentService(message.from_user)
        payments = ps.get_payments()
        pt = get_payments_pt(payments)

        bot.send_message(message.chat.id, f'<b>Your Payment list</b>\n{pt}', parse_mode='HTML')

        kb = types.InlineKeyboardMarkup(row_width=3)

        for item in payments:
            btn1 = types.InlineKeyboardButton(
                text=f"📂 #{item.id} - {item.record_id} - {item.amount}",
                callback_data=json.dumps({
                    'type': 'payment-detail',
                    'id': item.id,
                }),
            )
            btn2 = types.InlineKeyboardButton(
                text=f"🗑️ Delete",
                callback_data=json.dumps({
                    'type': 'payment-delete',
                    'id': item.id,
                })
            )
            btn3 = types.InlineKeyboardButton(
                text=f"📂 Record #{item.record_id}",
                callback_data=json.dumps({
                    'type': 'record-detail',
                    'id': item.record_id,
                }),
            )
            kb.add(btn1, btn2, btn3)

        bot.send_message(message.chat.id, f'<b>Payment detail:</b>', parse_mode='HTML', reply_markup=kb)


def send_lends(message):
    send_records(message, 1, 'Lend')


def send_borrows(message):
    send_records(message, 2, 'Borrow')


def create_lend(message):
    create_record(message, 1, 'Lend')


def create_borrow(message):
    create_record(message, 2, 'Borrow')


def request_record_id(message):
    get_record(message.chat.id, message.from_user, {'id': message.text})


def request_payment_id(message):
    get_payment(message.chat.id, message.from_user, {'id': message.text})


@bot.callback_query_handler(func=lambda callback: callback.data)
def check_callback_data(callback):
    if chat_id := callback.message.chat.id:
        callback_data = json.loads(callback.data)

        callback_type = callback_data.pop('type')
        match callback_type:
            case 'weather':
                send_weather(chat_id, callback_data)
            case 'lend' | 'borrow':
                request_record(callback.message, callback_type)
            case 'record-detail':
                get_record(chat_id, callback.from_user, callback_data)
            case 'record-delete':
                delete_record(chat_id, callback_data)
            case 'payment-detail':
                get_payment(chat_id, callback.from_user, callback_data)
            case 'payment-delete':
                delete_payment(chat_id, callback_data)
            case _:
                bot.send_message(chat_id, 'Unknown callback')


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(message.chat.id, commands, parse_mode='HTML')


@bot.message_handler(commands=["start"])
def cmd_start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

    btn1 = types.KeyboardButton(text='💵 Rates')
    btn2 = types.KeyboardButton(text='🌤 Weather')
    btn3 = types.KeyboardButton(text='💸 Lends')
    btn4 = types.KeyboardButton(text='💰 Borrows')
    btn5 = types.KeyboardButton(text='✅ Payments')
    btn6 = types.KeyboardButton(text='＋ Lend')
    btn7 = types.KeyboardButton(text='＋ Borrow')
    btn8 = types.KeyboardButton(text='＋ Payment')

    kb.add(btn1, btn2)
    kb.add(btn3, btn4, btn5)
    kb.add(btn6, btn7, btn8)

    user = create_user(message.from_user)
    bot.send_message(message.chat.id, 'Select what you want in menu', reply_markup=kb)


@bot.message_handler(commands=["rates"])
def cmd_rates(message):
    send_rates(message)


@bot.message_handler(commands=["weather"])
def cmd_weather(message):
    request_city(message)


@bot.message_handler(commands=["lends"])
def cmd_lends(message):
    send_lends(message)


@bot.message_handler(commands=["borrows"])
def cmd_borrows(message):
    send_borrows(message)


@bot.message_handler(commands=["payments"])
def cmd_payments(message):
    send_payments(message)


@bot.message_handler(commands=["record"])
def cmd_record(message):
    sent = bot.reply_to(message, 'Enter record id:')
    bot.register_next_step_handler(sent, request_record_id)


@bot.message_handler(commands=["payment"])
def cmd_payment(message):
    sent = bot.reply_to(message, 'Enter payment id:')
    bot.register_next_step_handler(sent, request_payment_id)


@bot.message_handler(commands=["add"])
def cmd_add(message):
    kb = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton(
        text="Lend",
        callback_data=json.dumps({'type': 'lend'})
    )
    btn2 = types.InlineKeyboardButton(
        text="Borrow",
        callback_data=json.dumps({'type': 'borrow'})
    )
    kb.add(btn1, btn2)

    bot.send_message(message.chat.id, 'Choose record type:', reply_markup=kb)


@bot.message_handler(commands=["pay"])
def cmd_pay(message):
    request_payment(message)


@bot.message_handler(content_types=["text"])
def message_handler(message):
    text = message.text
    # print('TEXT:', text)

    match text:
        case '💵 Rates':
            send_rates(message)
        case '🌤 Weather':
            request_city(message)
        case '💸 Lends':
            send_lends(message)
        case '💰 Borrows':
            send_borrows(message)
        case '✅ Payments':
            send_payments(message)
        case '＋ Lend':
            request_record(message, 'lend')
        case '＋ Borrow':
            request_record(message, 'borrow')
        case '＋ Payment':
            request_payment(message)
        case _:
            text = "I don't know what you want.\nTry some available command.\nSend /help for details."
            bot.send_message(message.chat.id, text)
