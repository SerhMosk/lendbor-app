import requests
from sqlalchemy import and_, func

from app import db
from models import User, Record, TypeEnum, Payment


class UserServiceException(Exception):
    pass


class RecordServiceException(Exception):
    pass


class PaymentServiceException(Exception):
    pass


class WeatherServiceException(Exception):
    pass


class UserService:
    def __init__(self, first_name, id, is_bot, language_code, last_name, username):
        self.id = None
        self.tg_id = id
        self.is_bot = is_bot
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.language_code = language_code

        try:
            user = User.query.filter_by(tg_id=str(id)).first()
        except Exception as error:
            raise UserServiceException(f'Get User Error: {error}')

        if user:
            self.update_user(user)
        else:
            self.create_user()

    def get_user(self):
        return {
            'id': self.id,
            'tg_id': self.tg_id,
            'is_bot': self.is_bot,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language_code': self.language_code,
        }

    def create_user(self):
        user = User(
            tg_id=str(self.tg_id),
            is_bot=self.is_bot,
            language_code=self.language_code,
            username=self.username,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        db.session.add(user)
        db.session.commit()
        self.id = user.id

    def update_user(self, user):
        self.id = user.id
        user.is_bot = self.is_bot
        user.language_code = self.language_code
        user.username = self.username
        user.first_name = self.first_name
        user.last_name = self.last_name

        db.session.commit()


class RecordService:
    def __init__(self, data):
        user = UserService(data.first_name, data.id, data.is_bot, data.language_code, data.last_name, data.username)
        self.user_id = user.id

    def get_records(self, record_type):
        record_type = TypeEnum(record_type)
        records = Record.query.filter_by(user_id=self.user_id, type=record_type).all()
        return records

    def get_record(self, record_id):
        record = Record.query.filter_by(user_id=self.user_id, id=int(record_id)).first()
        return record

    @staticmethod
    def delete_record(record_id):
        try:
            record = Record.query.get(record_id)
            db.session.delete(record)
            db.session.commit()
            return True
        except Exception as error:
            raise RecordServiceException(f'Delete Record Error: {error}')

    def create_record(self, data):
        try:
            record = Record(
                user_id=self.user_id,
                type=TypeEnum(data['type']),
                name=data['name'],
                amount=data['amount'],
                remains=data['remains'],
                months=data['months'],
                payment_amount=data['payment_amount'],
                payment_day=data['payment_day'],
                last_date=data['last_date'],
            )

            db.session.add(record)
            db.session.commit()

        except Exception as error:
            raise RecordServiceException(f'Create Record Error: {error}')


class PaymentService:
    def __init__(self, data):
        user = UserService(data.first_name, data.id, data.is_bot, data.language_code, data.last_name, data.username)
        self.user_id = user.id

    def get_payments(self):
        payments = Payment.query.filter_by(user_id=self.user_id).all()
        return payments

    def get_payment(self, payment_id):
        payment = Payment.query.filter_by(user_id=self.user_id, id=int(payment_id)).first()
        return payment

    @staticmethod
    def delete_payment(payment_id):
        try:
            payment = Payment.query.get(payment_id)
            db.session.delete(payment)
            db.session.commit()
            return True
        except Exception as error:
            raise PaymentServiceException(f'Delete Payment Error: {error}')

    def create_payment(self, data):
        try:
            record = db.session.query(Record).get(data['record_id'])
            payed = db.session.query(func.sum(Payment.amount)).filter(Payment.record_id == data['record_id']).one()

            remains = record.amount - float(data['amount'])

            if payed[0]:
                remains -= payed[0]

            record.remains = remains

            payment = Payment(
                user_id=self.user_id,
                record_id=data['record_id'],
                amount=data['amount'],
                payment_date=data['payment_date'],
                remains=remains,
            )

            db.session.add(payment)
            db.session.commit()

        except Exception as error:
            raise PaymentServiceException(f'Create Payment Error: {error}')


class WeatherService:
    GEO_URL = 'https://geocoding-api.open-meteo.com/v1/search'
    WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'

    @staticmethod
    def get_geo_data(city_name):
        params = {
            'name': city_name
        }

        res = requests.get(f'{WeatherService.GEO_URL}', params=params)

        if res.status_code != 200:
            raise WeatherServiceException('Can not get geo data')
        elif not res.json().get('results'):
            raise WeatherServiceException('City not found')

        return res.json().get('results')

    @staticmethod
    def get_current_weather_by_geo_data(lat, lon):
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': True
        }

        res = requests.get(f'{WeatherService.WEATHER_URL}', params=params)

        if res.status_code != 200:
            raise WeatherServiceException('Can not get weather data')

        return res.json().get('current_weather')
