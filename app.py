import logging
import requests
import threading

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import AppConfig
from scheduler import run_schedule
from rates_handler import RatesHandler

db = SQLAlchemy()

app = Flask(__name__)

app.config.from_object(AppConfig)
app.logger.setLevel(logging.INFO)

db.init_app(app)

from views import *
from models import *

with app.app_context():
    db.create_all()
    db.session.commit()


if __name__ == '__main__':
    rh = RatesHandler()

    # Schedule the rate fetching and storing to Redis every hour
    t = threading.Thread(target=run_schedule, args=(rh.update_rates,))
    t.start()

    url = f'{AppConfig.SERVER_URL}/{AppConfig.TELEGRAM_BOT_TOKEN}'
    requests.post(AppConfig.TELEGRAM_URL + 'setWebhook', json={'url': url})

    from bot import bot
    bot.remove_webhook()
    bot.set_webhook(url=f'{AppConfig.SERVER_URL}/{AppConfig.TELEGRAM_TOKEN}')

    app.run(host=AppConfig.HOST, port=AppConfig.PORT)
