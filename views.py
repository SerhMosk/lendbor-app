# 1. Create an .env file, where you add all the data that should be secret:
# - SECRET_KEY
# - Database name (and other details if available)
# - The host and port on which the service is running
# - Other values if necessary
#
# 2. Create a file .env.template, which will describe the structure of .env
# (variable names), but not contain values.
# The .env file DOES NOT need to be pushed to GitHub, the .env.template is required.
# (You can add .env to .gitignore)
#
# 3. Replace all secret values in the code with values from environment
#
# 4. Using flask_sqlalchemy, connect the database and create the following models:
# User,
# record,
# Payment.
# The data structure and relationships should be the same as in the homework for
# the topic “Basic work with databases. Part 2".
#
# 5. Modify existing or add new endpoints. Display data in JSON format or using an HTML template:
# - GET /user — display a list of all User objects (all records of the corresponding table)
# - GET /user/<int:user_id> — display information about the User with the corresponding id, or 404
# - GET /record — display a list of all Record objects (all records of the corresponding table)
# - GET /record/<int:record_id> — display information about the Record with the corresponding id, or 404
# - GET /payment — display a list of all Payment objects (all records of the corresponding table)
# - GET /payment/<int:payment_id> — display information about the Payment with the corresponding id, or 404
#
# 6. (optional) When transmitting with query param size=n for endpoints with a list
# of objects, show the corresponding number of objects.
#
# 7. (optional) When requesting endpoints /payment and /payment/<int:payment_id>,
# display not only information about payment, but also the name of the record and
# the name of the user who bought it.
#
# 8. (optional) Implement the possibility of creating new objects in the database.
# Endpoints can accept "application/json" or "application/x-www-form-urlencoded":
# - POST /user
# - POST /record
# - POST /payment (check if the corresponding User and Record exist)

import re
import datetime as dt

import telebot
from flask import abort, request, redirect, render_template, session, url_for
from sqlalchemy import desc, or_, and_, func

from app import app, db
from bot import bot
from bot_handler import MessageHandler, CallbackHandler
from config import AppConfig
from models import User, Record, Payment, TypeEnum


def get_list(query):
    result = db.session.execute(query).scalars()
    return [item.__dict__ for item in result]


# Set up a route to handle Telegram updates
@app.post(f'/{AppConfig.TELEGRAM_TOKEN}')
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return 'OK', 200


@app.post(f'/{AppConfig.TELEGRAM_BOT_TOKEN}')
def receive_data():
    handler = None
    data = request.get_json()

    if message := data.get('edited_message'):
        edited_msg_handler = MessageHandler(message)
        edited_msg_handler.send_message('Please do not edit messages')
    elif message := data.get('message'):
        handler = MessageHandler(message)
    elif callback := data.get('callback_query'):
        handler = CallbackHandler(callback)

    if handler:
        handler.handle()

    return 'OK', 200


@app.get('/users')
def user_list():
    if 'username' not in session:
        return redirect(url_for('login'))

    filters = request.values

    try:
        cnt = int(filters.get('size')) if filters.get('size') else None
    except ValueError:
        abort(400, 'Invalid size value')

    columns = ['id', 'username', 'first_name', 'last_name', 'phone']
    query = db.select(User).limit(cnt) if cnt else db.select(User)
    users = get_list(query)

    context = {
        'title': 'User List',
        'active': 'users',
        'users': users,
        'keys': columns
    }

    return render_template('user/list.html', **context), 200


@app.get('/users/<user_id>')
def user_detail(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = db.get_or_404(User, user_id)

    context = {
        'title': 'User Details',
        'active': 'users',
        'user': user.__dict__
    }

    return render_template('user/detail.html', **context), 200


@app.route("/users/create", methods=["GET", "POST"])
def user_create():
    if request.method == "POST":
        data = request.form

        query = db.select(User).filter(or_(
            User.username == data["username"],
            User.first_name == data["first_name"],
            User.last_name == data["last_name"]
        ))
        users = get_list(query)

        if len(users):
            return 'Username, first name or last name is not unique', 409

        user = User(
            username=data["username"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('user_detail', user_id=user.id))

    context = {
        'title': 'Create User',
        'active': 'users'
    }

    return render_template("user/create.html", **context)


@app.delete("/users/<int:user_id>")
def user_delete(user_id):
    user = db.get_or_404(User, user_id)

    db.session.delete(user)
    db.session.commit()

    # return redirect(url_for("user_list"))
    return 'OK', 200


@app.get('/records')
def record_list():
    if 'username' not in session:
        return redirect(url_for('login'))

    filters = request.values
    try:
        cnt = int(filters.get('size')) if filters.get('size') else None
    except ValueError:
        abort(400, 'Invalid size value')

    columns = ['id', 'user_id', 'type', 'name', 'amount', 'remains', 'months', 'payment_amount', 'payment_day', 'last_date']
    query = db.select(Record).limit(cnt) if cnt else db.select(Record)
    records = get_list(query)

    context = {
        'title': 'Record List',
        'active': 'records',
        'records': records,
        'users': db.session.query(User).all(),
        'types': [item for item in TypeEnum],
        'keys': columns
    }

    return render_template('record/list.html', **context), 200


@app.get('/records/<record_id>')
def record_detail(record_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    record = db.get_or_404(Record, record_id)
    user = User.query.get(record.user_id)

    context = {
        'title': 'Record Details',
        'active': 'records',
        'record': record.__dict__,
        'user': user,
    }

    return render_template('record/detail.html', **context), 200


@app.route("/records/create", methods=["GET", "POST"])
def record_create():
    if request.method == "POST":
        data = request.form

        query = db.select(Record).filter(and_(
            Record.user_id == data["user_id"],
            Record.type == TypeEnum(int(data["type"])),
            Record.name == data["name"],
            Record.amount == data["amount"],
            Record.months == data["months"],
            Record.payment_amount == data["payment_amount"],
            Record.payment_day == data["payment_day"],
            Record.last_date == data["last_date"]
        ))
        records = get_list(query)

        if len(records):
            return 'The record was added earlier', 409

        record = Record(
            user_id=data["user_id"],
            type=TypeEnum(int(data["type"])),
            name=data["name"],
            amount=data["amount"],
            remains=data["amount"],
            months=data["months"],
            payment_amount=data["payment_amount"],
            payment_day=data["payment_day"],
            last_date=data["last_date"],
        )

        db.session.add(record)
        db.session.commit()

        return redirect(url_for('record_detail', record_id=record.id))

    context = {
        'title': 'Create Record',
        'active': 'records',
        'users': db.session.query(User).all(),
        'types': [item for item in TypeEnum],
    }

    return render_template("record/create.html", **context)


@app.delete("/records/<int:record_id>")
def record_delete(record_id):
    record = db.get_or_404(Record, record_id)

    db.session.delete(record)
    db.session.commit()

    # return redirect(url_for("record_list"))
    return 'OK', 200


@app.get('/payments')
def payment_list():
    if 'username' not in session:
        return redirect(url_for('login'))

    filters = request.values
    try:
        cnt = int(filters.get('size')) if filters.get('size') else None
    except ValueError:
        abort(400, 'Invalid size value')

    columns = ['id', 'record', 'username', 'amount', 'months', 'payment_amount', 'remains', 'payment_date', 'last_date']

    # First solution
    # query = db.session
    #     .query(Payment.id, Record.id, Record.name, User.id, User.username, Payment.payment_date)\
    #     .join(Record).join(User).limit(cnt if cnt else -1)

    # Second solution
    if cnt:
        query = db.session.query(Payment, Record).join(Record).limit(cnt)
    else:
        query = db.session.query(Payment, Record).join(Record)
    payments = query.all()

    records = get_list(db.select(Record))
    users = get_list(db.select(User))

    context = {
        'title': 'Payment List',
        'active': 'payments',
        'payments': payments,
        'keys': columns,
        'records': records,
        'users': users
    }

    return render_template('payment/list.html', **context), 200


@app.get('/payments/<payment_id>')
def payment_detail(payment_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    result = db.get_or_404(Payment, payment_id)
    query = db.session.query(Payment, Record).join(Record).filter(Payment.id == payment_id).limit(1)
    context = {
        'title': 'Payment Details',
        'active': 'payments',
        'payment': query.all()
    }

    return render_template('payment/detail.html', **context), 200


@app.route("/payments/create", methods=["GET", "POST"])
def payment_create():
    if request.method == "POST":
        data = request.form

        if data['record_id'] is None or data['user_id'] is None:
            return 'Invalid record_id or user_id value', 400

        try:
            record_id = int(data['record_id']) if data['record_id'] else 0
            user_id = int(data['user_id']) if data['user_id'] else 0
        except ValueError:
            return 'Invalid record_id or user_id value', 400

        record = db.session.query(Record).get(record_id)
        payed = db.session.query(func.sum(Payment.amount)).filter(Payment.record_id == record_id).one()

        remains = record.amount - float(data['amount'])

        if payed[0]:
            remains -= payed[0]

        record.remains = remains

        payment = Payment(
            user_id=user_id,
            record_id=record_id,
            amount=data['amount'],
            payment_date=data['payment_date'],
            remains=remains
        )

        db.session.add(payment)
        db.session.commit()

        return redirect(url_for('payment_detail', payment_id=payment.id))

    records = get_list(db.select(Record))
    users = get_list(db.select(User))

    context = {
        'title': 'Create Payment',
        'active': 'payments',
        'records': records,
        'users': users
    }

    return render_template("payment/create.html", **context)


@app.delete("/payments/<int:payment_id>")
def payment_delete(payment_id):
    payment = db.get_or_404(Payment, payment_id)

    db.session.delete(payment)
    db.session.commit()

    # return redirect(url_for("record_list"))
    return 'OK', 200


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)

    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ''
    password = ''
    username_error = ''
    password_error = ''

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username and password:
            if len(username) < 5:
                # abort(400, 'Invalid username')
                username_error = 'Username at least 5 characters'
            if re.fullmatch(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$', password) is None:
                # abort(400, 'Invalid password')
                password_error = ('Password must be at least 8 characters and '
                                  'contain at least 1 number and 1 capital letter')

            if username_error == '' and password_error == '':
                session['username'] = username

                # Process user login
                return redirect(url_for('home_page'))
        else:
            abort(400, 'Invalid username or password')

    context = {
        'username': username,
        'password': password,
        'username_error': username_error,
        'password_error': password_error
    }

    return render_template('auth/login.html', **context), 200


def get_error_content(title, error, page):
    context = {
        'title': title,
        'error': error
    }

    return render_template(page + '.html', **context)


@app.errorhandler(400)
def bad_req_error(error):
    return get_error_content('Bad Request', error, '40x'), 400


@app.errorhandler(404)
def not_found_error(error):
    return get_error_content('Not Found', error, '40x'), 404


@app.errorhandler(405)
def not_allowed(error):
    return get_error_content('Not Allowed', error, '40x'), 405


@app.errorhandler(500)
def server_error(error):
    return get_error_content('Server Error', error, '50x'), 500


@app.route('/')
def home_page():
    app.logger.info('GET Home page')

    context = {
        'title': 'Home Page',
        'active': '/'
    }

    return render_template('index.html', **context), 200
