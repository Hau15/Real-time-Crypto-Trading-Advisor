# 🚀 Hệ thống Tư vấn Giao dịch Crypto Đa luồng Thời gian thực (Real-time Multi-Crypto Trading Advisor)

Hệ thống tư vấn giao dịch tần suất cao (High-Frequency Trading) được xây dựng dựa trên nền tảng các công nghệ **Big Data**. Hệ thống thu thập dữ liệu giá tiền điện tử theo thời gian thực từ Binance, xử lý luồng bằng Apache Spark và cung cấp tín hiệu Mua/Bán dựa trên chiến thuật RSI thông qua Dashboard tương tác.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.x-black)
![Cassandra](https://img.shields.io/badge/Cassandra-NoSQL-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)

## 📊 Kiến trúc Hệ thống

Hệ thống tuân theo mô hình xử lý dòng dữ liệu thời gian thực (Real-time Stream Processing):

```mermaid
graph LR
    A[Binance WebSocket] -->|Dữ liệu Real-time| B(Kafka Producer)
    B -->|Topic: crypto_data| C{Spark Structured Streaming}
    D[(Cassandra DB)] -->|Dữ liệu Lịch sử| C
    C -->|Tính toán RSI & Tín hiệu| D
    D -->|Truy vấn| E[Streamlit Dashboard]
