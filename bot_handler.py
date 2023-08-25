import json
import requests
from datetime import datetime as dt

from config import AppConfig
from services import WeatherService, WeatherServiceException, UserService
from rates_handler import RatesHandler


class TelegramHandler:
    user = None

    def __init__(self, data):
        self.user = UserService(**data.get('from'))
        # self.text = data.get('text')

    def send_message(self, text, markup=None):
        data = {
            'chat_id': self.user.tg_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if markup:
            data.reply_markup = markup
        requests.post(f'{AppConfig.TELEGRAM_URL}sendMessage', json=data)


class MessageHandler(TelegramHandler):
    def __init__(self, data):
        super().__init__(data)
        self.text = data.get('text')
        # print('TEXT:', self.text)

    def send_rates(self):
        rh = RatesHandler()
        rates = rh.get_stored_rates()
        msg = f'<b>Rates</b>\nBTC/USDT: {rates.get("BTCUSDT")}\nETH/USDT: {rates.get("ETHUSDT")}'

        self.send_message(msg)

    def handle(self):
        args = self.text.split()
        command = args.pop(0)
        # print(f'COMMAND: {command}')

        match command:
            case '/weather':
                if len(args) > 0:
                    city = ' '.join(args)
                    # print(f'CITY: {city}')
                    try:
                        geo_data = WeatherService.get_geo_data(city_name=city)
                    except WeatherServiceException as wse:
                        self.send_message(str(wse))
                    else:
                        buttons = []

                        if len(geo_data):
                            for item in geo_data:
                                city_button = {
                                    'text': f"{item.get('name')} - {item.get('admin1')} - {item.get('country_code')}",
                                    'callback_data': json.dumps({
                                        'type': 'weather',
                                        'lat': item.get('latitude'),
                                        'lon': item.get('longitude')
                                    })
                                }
                                buttons.append([city_button])

                            markup = {
                                'inline_keyboard': buttons
                            }

                            # print(f'MARKUP: {markup}')
                            self.send_message('Choose your city:', markup)
                        else:
                            self.send_message('City not found')
                else:
                    self.send_message('The parameter "city" - is not specified')
            case '/rates':
                self.send_rates()
            case _:
                self.send_message('Unknown command')


class CallbackHandler(TelegramHandler):
    def __init__(self, data):
        super().__init__(data)
        self.callback_data = json.loads(data.get('data'))

    def handle(self):
        callback_type = self.callback_data.pop('type')
        match callback_type:
            case 'weather':
                try:
                    weather = WeatherService.get_current_weather_by_geo_data(**self.callback_data)
                except WeatherServiceException as wse:
                    self.send_message(str(wse))
                else:
                    result_time = dt.strptime(weather.get("time"), "%Y-%m-%dT%H:%M").strftime("%d.%m.%Y %H:%M")
                    result = (f'- Temperature: {weather.get("temperature")},\n'
                              f'- Wind speed: {weather.get("windspeed")},\n'
                              f'- Wind direction: {weather.get("winddirection")},\n'
                              f'- Weather code: {weather.get("weathercode")},\n'
                              f'- Is day: {"Yes" if weather.get("is_day") == 1 else "No"},\n'
                              f'- Time: {result_time}')

                    self.send_message(f'<b>Weather in your city:</b>\n{result}')
