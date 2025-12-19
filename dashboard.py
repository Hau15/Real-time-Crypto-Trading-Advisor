import streamlit as st
import pandas as pd
import altair as alt
from cassandra.cluster import Cluster
import time

# 1. CẤU HÌNH
st.set_page_config(page_title="Multi-Crypto Advisor", page_icon="💎", layout="wide")

st.markdown("""
<style>
    .metric-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# 2. DATABASE
@st.cache_resource
def get_session():
    cluster = Cluster(['localhost'], port=9042)
    session = cluster.connect('crypto_db')
    return session

def get_data(symbol_filter):
    session = get_session()
    # Lấy dữ liệu theo Symbol được chọn
    query = f"SELECT symbol, timestamp, price, signal FROM market_data WHERE symbol = '{symbol_filter}' LIMIT 60 ALLOW FILTERING"
    rows = session.execute(query)
    df = pd.DataFrame(list(rows))
    
    if not df.empty:
        df = df.sort_values(by='timestamp')
        # Chỉnh giờ Việt Nam
        df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=7)
        
        df['diff'] = df['price'].diff().fillna(0)
        df['status'] = df['diff'].apply(lambda x: 'Tăng' if x >= 0 else 'Giảm')
    return df

# 3. SIDEBAR (THANH BÊN TRÁI)
with st.sidebar:
    st.header("⚙️ Cấu hình")
    st.markdown("Chọn loại tiền tệ bạn muốn theo dõi:")
    # Hộp chọn Coin
    selected_coin = st.selectbox(
        "Cặp tiền tệ (Pair)",
        ("BTC/USDT", "ETH/USDT", "BNB/USDT")
    )
    st.info(f"Đang theo dõi: **{selected_coin}**")
    st.markdown("---")
    st.caption("Powered by Apache Spark & Kafka")

# 4. GIAO DIỆN CHÍNH
st.title(f"🚀 {selected_coin} Trading Advisor")
st.markdown("### Hệ thống phân tích kỹ thuật đa luồng thời gian thực")
st.divider()

col1, col2, col3 = st.columns(3)
metric_price = col1.empty()
metric_signal = col2.empty()
metric_time = col3.empty()
chart_placeholder = st.empty()
table_placeholder = st.empty()

# 5. VÒNG LẶP
while True:
    try:
        # Truyền coin đã chọn vào hàm lấy dữ liệu
        df = get_data(selected_coin)
        
        if not df.empty:
            latest = df.iloc[-1]
            
            with metric_price:
                st.metric(f"Giá {selected_coin}", f"${latest['price']:,.2f}")
            
            with metric_signal:
                sig = latest['signal']
                if sig == "BUY":
                    msg, icon, color, bg, border = "MUA VÀO", "▲", "#00a83e", "#e6f4ea", "#b7e1cd"
                    desc = "Vùng quá bán (RSI < 30)"
                elif sig == "SELL":
                    msg, icon, color, bg, border = "BÁN RA", "▼", "#d93025", "#fce8e6", "#fad2cf"
                    desc = "Vùng quá mua (RSI > 70)"
                else:
                    msg, icon, color, bg, border = "GIỮ VỊ THẾ", "⏸", "#b58900", "#fff9db", "#ffe066"
                    desc = "Thị trường đi ngang"

                st.markdown(f"""
                    <div style="border: 2px solid {border}; background-color: {bg}; border-radius: 10px; padding: 10px; text-align: center;">
                        <p style="color: {color}; margin: 0; font-size: 11px; font-weight: bold;">KHUYẾN NGHỊ AI</p>
                        <h2 style="color: {color}; margin: 5px 0 0 0; font-size: 24px; font-weight: 800;">{icon} {msg}</h2>
                        <p style="color: #666; font-size: 10px; margin: 0;">{desc}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            with metric_time:
                st.metric("Cập nhật (VN Time)", str(latest['timestamp'].time()))

            # Biểu đồ
            base = alt.Chart(df).encode(
                x=alt.X('timestamp', axis=alt.Axis(format='%H:%M:%S', title='Thời gian')),
                y=alt.Y('price', scale=alt.Scale(zero=False), title='Giá (USD)'),
                tooltip=['timestamp', 'price', 'signal']
            )
            line = base.mark_line(color='#b0b0b0', opacity=0.3)
            points = base.mark_circle(size=90, opacity=1).encode(
                color=alt.Color('status', scale=alt.Scale(domain=['Tăng', 'Giảm'], range=['#00a83e', '#d93025']), legend=None)
            )
            chart = (line + points).properties(height=450).interactive()
            chart_placeholder.altair_chart(chart, use_container_width=True)

            with table_placeholder:
                st.caption(f"Lịch sử tín hiệu của {selected_coin}:")
                def color_sig(val):
                    if val == 'BUY': return 'color: #00a83e; font-weight: bold'
                    elif val == 'SELL': return 'color: #d93025; font-weight: bold'
                    else: return 'color: #b58900; font-weight: bold'
                
                show_df = df.sort_values(by='timestamp', ascending=False).head(5)[['timestamp', 'price', 'signal']]
                st.dataframe(show_df.style.map(color_sig, subset=['signal']), use_container_width=True)
        
        time.sleep(1)

    except Exception as e:
        st.warning(f"Đang chờ dữ liệu của {selected_coin}... ({e})")
        time.sleep(1)
