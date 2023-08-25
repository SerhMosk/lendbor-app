import redis
import requests

from config import AppConfig


class RatesHandler:
    PROVIDER_URL = 'https://api.binance.com/api/v3/ticker/price'
    CURRENCY_PAIRS = ('BTCUSDT', 'ETHUSDT')

    def __init__(self):
        self.r = redis.StrictRedis(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT, decode_responses=True)

    def update_rates(self):
        self.store_rates(self.request_rates())

    def store_rates(self, rates):
        self.r.hmset('rates', rates)

    def get_stored_rates(self):
        return self.r.hgetall('rates')

    def request_rates(self, pairs=None):
        rates = {}

        if pairs is None:
            pairs = self.CURRENCY_PAIRS

        for pair in pairs:
            response = requests.get(self.PROVIDER_URL, params={'symbol': pair})
            rates[pair] = response.json()['price']

        return rates
