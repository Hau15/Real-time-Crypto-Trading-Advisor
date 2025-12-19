import os
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,com.datastax.spark:spark-cassandra-connector_2.12:3.5.0 pyspark-shell'

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, TimestampType
import pandas as pd
from cassandra.cluster import Cluster

# 1. Khởi tạo Spark
spark = SparkSession.builder \
    .appName("MultiCryptoAdvisor") \
    .master("local[*]") \
    .config("spark.cassandra.connection.host", "localhost") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# 2. Schema
schema = StructType([
    StructField("symbol", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("volume", DoubleType(), True),
    StructField("timestamp", LongType(), True),
    StructField("time_str", StringType(), True)
])

# 3. Hàm tính RSI
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 4. Logic xử lý Đa Coin
def process_multi_coin(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    
    print(f"--- Đang xử lý Batch {batch_id} ---")
    
    # Chuyển sang Pandas để xử lý cho linh hoạt
    incoming_data = batch_df.toPandas()
    
    # Kết nối DB
    try:
        cluster = Cluster(['localhost'], port=9042)
        session = cluster.connect('crypto_db')
        
        final_results = []

        # Lấy danh sách các coin có trong batch này (VD: ['BTC/USDT', 'ETH/USDT'])
        unique_symbols = incoming_data['symbol'].unique()
        
        for sym in unique_symbols:
            # Lọc dữ liệu của riêng coin này trong batch
            coin_data = incoming_data[incoming_data['symbol'] == sym].copy()
            
            # Lấy lịch sử CỦA RIÊNG COIN NÀY từ Cassandra
            query = f"SELECT price FROM market_data WHERE symbol = '{sym}' ORDER BY timestamp DESC LIMIT 30"
            rows = session.execute(query)
            history_df = pd.DataFrame(list(rows))
            
            # Đảo ngược lại vì lấy DESC (mới nhất) -> cần xếp cũ nhất lên trước để tính RSI
            if not history_df.empty:
                history_df = history_df.iloc[::-1] 
                full_df = pd.concat([history_df['price'], coin_data['price']], ignore_index=True)
            else:
                full_df = coin_data['price']
            
            # Tính RSI
            rsi_values = calculate_rsi(full_df, period=6)
            
            # Map ngược lại RSI vào dữ liệu mới
            # Lấy phần đuôi tương ứng với số lượng dữ liệu mới
            coin_data['rsi'] = rsi_values.tail(len(coin_data)).values
            
            # Logic Tín hiệu
            def get_signal(row):
                rsi = row['rsi']
                if pd.isna(rsi): return "HOLD"
                elif rsi > 70: return "SELL"
                elif rsi < 30: return "BUY"
                else: return "HOLD"
            
            coin_data['signal'] = coin_data.apply(get_signal, axis=1)
            final_results.append(coin_data)
        
        # Gộp kết quả các coin lại và lưu
        if final_results:
            final_df = pd.concat(final_results)
            
            # In ra màn hình console để kiểm tra
            print(final_df[['time_str', 'symbol', 'price', 'signal']].tail(3))
            
            # Lưu xuống Cassandra
            spark_df = spark.createDataFrame(final_df[['symbol', 'timestamp', 'price', 'signal']])
            spark_df.write \
                .format("org.apache.spark.sql.cassandra") \
                .mode("append") \
                .options(table="market_data", keyspace="crypto_db") \
                .save()
        
        session.shutdown()
        cluster.shutdown()

    except Exception as e:
        print(f"Lỗi: {e}")

# 5. Pipeline
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "crypto_data") \
    .load()

parsed_df = kafka_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("timestamp", (col("timestamp") / 1000).cast(TimestampType()))

query = parsed_df.writeStream \
    .foreachBatch(process_multi_coin) \
    .outputMode("update") \
    .start()

query.awaitTermination()
