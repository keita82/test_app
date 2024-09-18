import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import mplfinance as mpf
import json
import datetime as dt

# 登録したメールアドレス、パスワードを設定
mail_password = {"mailaddress": "keita.shimamura1110@gmail.com", "password": "2ZgYBLJBkvxjoiwTjUeK"}
# リフレッシュトークン取得
r_ref = requests.post("https://api.jquants.com/v1/token/auth_user", data=json.dumps(mail_password))
# IDトークン取得
RefreshToken = r_ref.json()["refreshToken"]
r_token = requests.post(f"https://api.jquants.com/v1/token/auth_refresh?refreshtoken={RefreshToken}")
idToken = r_token.json()["idToken"]
headers = {'Authorization': f'Bearer {idToken}'}

# APIで日足データを取得する関数
def get_daily_quotes(code, day_list):
    all_data = []
    for day in day_list:
        r = requests.get(f"https://api.jquants.com/v1/prices/daily_quotes?code={code}&date={day}", headers=headers)
        if r.status_code == 200:
            data = r.json().get("daily_quotes", [])
            all_data.extend(data)
        else:
            st.error(f"Failed to fetch data for {day}")
    return pd.DataFrame(all_data)

# 売買内訳データを取得する関数
def get_trade_breakdown_data(code, day_list):
    trade_data = []
    for day in day_list:
        r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
        if r.status_code == 200:
            breakdown = r.json().get("breakdown", [])
            if breakdown:
                for data in breakdown:
                    # 信用売残高 (MarginSellNewValue - MarginBuyCloseValue)
                    sell_balance = data['MarginSellNewValue'] - data['MarginBuyCloseValue']
                    # 信用買残高 (MarginBuyNewValue - MarginSellCloseValue)
                    buy_balance = data['MarginBuyNewValue'] - data['MarginSellCloseValue']
                    # 現物 (LongBuyValue - LongSellValue)
                    spot_balance = data['LongBuyValue'] - data['LongSellValue']
                    trade_data.append({
                        'Date': data['Date'],
                        'SellBalance': sell_balance,
                        'BuyBalance': buy_balance,
                        'SpotBalance': spot_balance  # 現物残高
                    })
        else:
            st.error(f"Failed to fetch trade breakdown for {day}")
    return pd.DataFrame(trade_data)

# タイトル
st.title("stock balance")

# 銘柄コード入力フォーム
code = st.text_input("銘柄コードを入力してください", value="6920")
st.write(f"選択された銘柄コード: {code}")

# 集計期間を入力
start_date = st.date_input("開始日を選択")
end_date = st.date_input("終了日を選択")

# 日付をリスト化
if start_date > end_date:
    st.error("開始日は終了日より前の日付を選択してください。")
else:
    day_list = []
    current_date = start_date
    while current_date <= end_date:
        day_list.append(current_date.strftime('%Y%m%d'))
        current_date += dt.timedelta(days=1)
    # 集計期間を表示
    st.write(f"集計期間: {day_list[0]} ~ {day_list[-1]}")

# ボタン押下時に日足データ取得
if st.button("日足データを取得"):
    # 日足データ取得
    daily_data = get_daily_quotes(code, day_list)
    if not daily_data.empty:
        # 日付をdatetime型に変換し、インデックスに設定
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])
        daily_data.set_index('Date', inplace=True)

        # 最新の日付が右側になるようにデータをソート
        daily_data.sort_index(ascending=True, inplace=True)

        # ローソク足チャートを描画するために必要なカラム名を変更
        daily_data.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)

        # 売買内訳データ取得
        trade_data = get_trade_breakdown_data(code, day_list)
        if not trade_data.empty:
            # 売買内訳データも日付をdatetime型に変換し、インデックスに設定
            trade_data['Date'] = pd.to_datetime(trade_data['Date'])
            trade_data.set_index('Date', inplace=True)

            # Figureを作成し、mplfinanceのプロットを統合
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1, 1]})

            # ローソク足チャートの描画
            mpf.plot(daily_data[['open', 'high', 'low', 'close', 'volume']],type='candle', ax=ax1, volume=ax2, style='charles')

            # 売買内訳データを折れ線グラフで描画
            ax3.plot(trade_data.index, trade_data['SellBalance'], label='信用売残高', color='red')
            ax3.plot(trade_data.index, trade_data['BuyBalance'], label='信用買残高', color='green')
            ax3.plot(trade_data.index, trade_data['SpotBalance'], label='現物', color='blue')
            ax3.set_xlabel('日付')
            ax3.set_ylabel('残高')
            ax3.legend()

            # チャートをStreamlitで表示
            st.pyplot(fig)
        else:
            st.write("売買内訳データが見つかりませんでした。")
    else:
        st.write("日足データが見つかりませんでした。")
