import json
import time
from kafka import KafkaProducer
import websocket

# Cấu hình cua Kafka
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

def on_message(ws, message):
    try:
        json_msg = json.loads(message)
        # Binance Multiplex trả về dạng: {"stream": "...", "data": {...}}
        data = json_msg['data']
        
        symbol_map = {
            "BTCUSDT": "BTC/USDT",
            "ETHUSDT": "ETH/USDT",
            "BNBUSDT": "BNB/USDT"
        }
        
        raw_symbol = data['s']
        display_symbol = symbol_map.get(raw_symbol, raw_symbol)

        processed_data = {
            'symbol': display_symbol,       # Tên coin (VD: BTC/USDT)
            'price': float(data['p']),      # Giá
            'volume': float(data['q']),     # Volume
            'timestamp': data['T'],         # Thời gian
            'time_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['T']/1000))
        }
        
        # Gửi vào Kafka
        producer.send('crypto_data', value=processed_data)
        print(f"[DATA] {processed_data['symbol']} | Price: {processed_data['price']}")
        
    except Exception as e:
        print(f"Lỗi parse data: {e}")

def on_error(ws, error):
    print(f"Lỗi kết nối: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Mất kết nối. Đang thử lại...")

def on_open(ws):
    print(">>> Đã kết nối ĐA LUỒNG (BTC, ETH, BNB) tới Binance!")

if __name__ == "__main__":
    # URL đặc biệt để nghe nhiều stream cùng lúc
    socket_url = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade/bnbusdt@trade"
    
    ws = websocket.WebSocketApp(socket_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
