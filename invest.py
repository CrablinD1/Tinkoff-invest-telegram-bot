# pip install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple/ tinkoff-invest-openapi-client
# pip install pytelegrambotapi
# pip install -U python-dotenv
import os
from dotenv import load_dotenv
from openapi_client import openapi
import requests
import telebot


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

TINKOFF_TOKEN = os.environ.get("TINKOFF_TOKEN")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

client = openapi.api_client(TINKOFF_TOKEN)
bot = telebot.TeleBot(BOT_TOKEN)

keyboard1 = telebot.types.ReplyKeyboardMarkup(True)
keyboard1.row('Счёт', 'Активы')


def usd_rub():
    URL = 'https://www.cbr-xml-daily.ru/daily_json.js'
    data = requests.get(URL).json()['Valute']['USD']['Value']
    return data


def get_price_by_ticker(name, signal=1, last=True):
    ticker = client.market.market_search_by_ticker_get(
        name).payload.instruments
    figi = ticker[0].figi
    prices = client.market.market_orderbook_get(figi, 2).payload

    if len(prices.asks) and len(prices.bids):
        if signal == -1:
            return prices.asks[0].price, prices.bids[0].price
        else:
            return (prices.asks[0].price, prices.bids[0].price)[signal]
    elif last:
        return prices.last_price


def portfolio_get():
    portfolio = client.portfolio.portfolio_get().payload.positions
    stocks = []

    for i in portfolio:
        if i.instrument_type == 'Bond':
            price = i.average_position_price.value
        elif i.instrument_type in ['Stock', 'Etf']:
            price = get_price_by_ticker(i.ticker)
        req = {
            'ticker': i.ticker,
            'name': i.name,
            'count': int(i.balance),
            'price': price,
            'currency': i.average_position_price.currency,
        }

        if i.average_position_price.currency == 'RUB':
            req['summ'] = req['count'] * price
        else:
            req['summ'] = req['count'] * price * usd_rub()

        if i.instrument_type != 'Currency':
            stocks.append(req)

    return stocks


def count_summ(sum):
    summa = 0
    for i in sum:
        summa += i['summ']
    return summa


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, ты написал мне /start',
                     reply_markup=keyboard1)


@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.lower() == 'счёт':
        reply = f'Счет: *{round(count_summ(portfolio_get()), 2)} руб.*'
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")
    elif message.text.lower() == 'активы':
        for i in portfolio_get():
            reply = f"{i['name']}_({i['ticker']})_: *{round(i['summ'], 2)} руб.*"
            bot.send_message(message.chat.id, reply, parse_mode="Markdown")


bot.polling()
