from flask import Blueprint, request, jsonify
from extensions import socketio
import time
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from datetime import datetime
from collections import deque

strategy_bp = Blueprint('strategy', __name__)

# Global variables for strategy control
running = False
sws = None

# SMA Crossover Strategy Variables
candles = []
current_candle = None
sma_window2 = deque(maxlen=2)
sma_window3 = deque(maxlen=3)
sma2 = 0
sma3 = 0
buy = False
buyPrice = 0
sellPrice = 0
profit = 0

correlation_id = "abc123"
mode = 1
token_list = [
    {
        "exchangeType": 2,
        "tokens": ["54947"]  # Replace with actual token
    }
]

def add_tick(tick):
    global current_candle, candles, sma_window2, sma_window3
    tick_time = datetime.fromtimestamp(tick['exchange_timestamp'] / 1000)
    minute = tick_time.replace(second=0, microsecond=0)

    if current_candle and current_candle['time'] != minute:
        candles.append(current_candle)
        update_sma2(current_candle['close'])
        update_sma3(current_candle['close'])
        check_crossover(current_candle['close'])
        current_candle = None

    if not current_candle:
        current_candle = {
            'time': minute,
            'close': tick['last_traded_price'],
        }
    else:
        current_candle['close'] = (current_candle['close'] + tick['last_traded_price']) / 2

def update_sma2(close_price):
    global sma_window2, sma2
    sma_window2.append(close_price)
    if len(sma_window2) == 2:
        sma2 = sum(sma_window2) / 2
        socketio.emit('sma2_update', {'sma2': sma2})
        print(f"SMA-2: {sma2}")

def update_sma3(close_price):
    global sma_window3, sma3
    sma_window3.append(close_price)
    if len(sma_window3) == 3:
        sma3 = sum(sma_window3) / 3
        socketio.emit('sma3_update', {'sma3': sma3})
        print(f"SMA-3: {sma3}")

def check_crossover(price):
    global buy, sma2, sma3, buyPrice, sellPrice, profit
    if sma2 >= sma3 and not buy and sma2 != 0 and sma3 != 0:
        buy = True
        buyPrice = price
        sellPrice = 0
        socketio.emit('buy_signal', {'price': buyPrice})
        print(f"Buy signal triggered at price {buyPrice}")
    elif sma2 < sma3 and buy:
        buy = False
        sellPrice = price
        profit += sellPrice - buyPrice
        buyPrice = 0
        socketio.emit('sell_signal', {'price': sellPrice, 'profit': profit})
        print(f"Sell signal triggered. Profit is {profit}")

def on_data(wsapp, tick):
    add_tick(tick)

def on_control_message(wsapp, message):
    print("Control message:", message)

def on_open(wsapp):
    print("WebSocket connection opened.")
    sws.subscribe(correlation_id, mode, token_list)

def on_error(wsapp, error):
    print("Error:", error)

def on_close(wsapp):
    print("WebSocket connection closed.")

def close_connection():
    if sws:
        sws.close_connection()

def run_sma_crossover():
    global running, sws
    # Define your credentials
    api_key = 'kk73BzpF'
    username = 'M62093595'
    pwd = '3110'
    smartApi = SmartConnect(api_key)
    
    try:
        token = "CP53B46372XGGKQFQZ5XTI5JCY"
        totp = pyotp.TOTP(token).now()
    except Exception as e:
        raise e
    
    correlation_id = "abcde"
    data = smartApi.generateSession(username, pwd, totp)

    if data['status'] == False:
        print("Error generating session:", data)
    else:
        authToken = data['data']['jwtToken']
        refreshToken = data['data']['refreshToken']
        feedToken = smartApi.getfeedToken()
        res = smartApi.getProfile(refreshToken)
        smartApi.generateToken(refreshToken)

        AUTH_TOKEN = authToken
        API_KEY = api_key
        CLIENT_CODE = username
        FEED_TOKEN = feedToken
        

        sws = SmartWebSocketV2(
            AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN,
            max_retry_attempt=0, retry_strategy=0, retry_delay=10, retry_duration=30
        )

        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close
        sws.on_control_message = on_control_message

        sws.connect()

        while running:
            time.sleep(1)

    close_connection()

@strategy_bp.route('/start_strategy', methods=['POST'])
def start_strategy():
    global running
    if not running:
        running = True
        run_sma_crossover()
        return jsonify({'status': 'Strategy started successfully'}), 200
    return jsonify({'status': 'Strategy already running'}), 400

@strategy_bp.route('/stop_strategy', methods=['POST'])
def stop_strategy():
    global running
    if running:
        running = False
        close_connection()
        return jsonify({'status': 'Strategy stopped successfully'}), 200
    return jsonify({'status': 'No strategy is running'}), 400
