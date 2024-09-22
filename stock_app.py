import streamlit as st
import requests
import pandas as pd
import json
import datetime as dt
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import mplfinance as mpf

# 登録したメールアドレス、パスワードを設定
# EMAIL_ADDRESSに登録メールアドレス、PASSWORDにパスワードを入力
mail_password={"mailaddress":"keita.shimamura1110@gmail.com", "password":"2ZgYBLJBkvxjoiwTjUeK"}
# リフレッシュトークン取得
r_ref = requests.post("https://api.jquants.com/v1/token/auth_user", data=json.dumps(mail_password))
######### IDトークン取得 ###########
# IDトークンの有効期間は２４時間
# 受け取ったリフレッシュトークンを設定
RefreshToken = r_ref.json()["refreshToken"]
# IDトークン取得
r_token = requests.post(f"https://api.jquants.com/v1/token/auth_refresh?refreshtoken={RefreshToken}")
# 取得したIDトークンを設定
idToken = r_token.json()["idToken"]
headers = {'Authorization': 'Bearer {}'.format(idToken)}
# 売買代金ランキングURL(yahoo_finance参照)
prime_ranking_url = "https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=tokyo1&term=daily"
standard_ranking_url = "https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=tokyo2&term=daily"
growth_ranking_url = "https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=tokyoM&term=daily"

st.set_page_config(layout="wide")

# 集計期間を入力
start_date = st.date_input("start")
end_date = st.date_input("end")

# 日付をリスト化
if start_date > end_date:
    st.error("start < end !!")
else:
    day_list = []
    current_date = start_date
    while current_date <= end_date:
        day_list.append(current_date.strftime('%Y%m%d'))
        current_date += dt.timedelta(days=1)
    # 集計期間を表示
    st.write(f"""<p style="color:darkgray;">date: {day_list[0]} ~ {day_list[-1]}</p>""", unsafe_allow_html=True)

# ここからグラフ描画用のコード
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

# 銘柄コード入力フォーム
code = st.text_input("search_code", value="6920")
st.write(f"""<p style="color:darkgray;">stock_code: {code}</p>""", unsafe_allow_html=True)

# ボタン押下時に日足データ取得
if st.button("get_stock_data"):
    # 日足データ取得
    daily_data = get_daily_quotes(code, day_list)
    if not daily_data.empty:
        # 日付をdatetime型に変換し、インデックスに設定
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])
        daily_data.set_index('Date', inplace=True)

        # 最新の日付が右側になるようにデータをソート
        daily_data.sort_index(ascending=True, inplace=True)

        # ローソク足チャートを描画するために必要なカラム名を変更
        daily_data.rename(columns={"AdjustmentOpen": "open", "AdjustmentHigh": "high", "AdjustmentLow": "low", "AdjustmentClose": "close", "AdjustmentVolume": "volume"}, inplace=True)

        # 売買内訳データ取得
        trade_data = get_trade_breakdown_data(code, day_list)
        if not trade_data.empty:
            # 売買内訳データも日付をdatetime型に変換し、インデックスに設定
            trade_data['Date'] = pd.to_datetime(trade_data['Date'])
            trade_data.set_index('Date', inplace=True)

            # Figureを作成し、mplfinanceのプロットを統合
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1, 1]})

            # ローソク足チャートの描画
            mpf.plot(daily_data[['open', 'high', 'low', 'close', 'volume']],type='candle', ax=ax1, volume=ax2, style='yahoo', datetime_format='%Y/%m/%d')

            # 売買内訳データを折れ線グラフで描画
            ax3.plot(trade_data.index, trade_data['SellBalance'], color='red')
            ax3.plot(trade_data.index, trade_data['BuyBalance'], color='green')
            ax3.plot(trade_data.index, trade_data['SpotBalance'], color='blue')
            ax3.set_xlabel('day')
            ax3.set_ylabel('balance')
            ax3.legend()

            # チャートをStreamlitで表示
            st.pyplot(fig)
            st.write("""<p style="text-align: right; color:darkgray;">(red: 売残, green: 買残, blue: 現残)</p>""", unsafe_allow_html=True)
        else:
            st.write("not find")
    else:
        st.write("not data")

# ここからランキング集計
# プライム市場
if st.button("prime_value_top10"):
    # prime_DataFrame
    prime_value_top10 = {'code': [], 'name': [], 'prime_margin_buy_new': [], 'prime_margin_buy_close': [], 'prime_margin_sell_new': [], 'prime_margin_sell_close': [], 'prime_buy_balance': [], 'prime_sell_balance': [], 'prime_long_buy': [], 'prime_long_sell': [], 'prime_long_balance': []}

    # プライム市場のランキング取得
    response = requests.get(prime_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # プライム上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            prime_value_top10['code'].append(row.find('li').get_text())
            prime_value_top10['name'].append(row.find('a').get_text())
            if len(prime_value_top10['code']) == 10:
                break
        for day in day_list:
            for code in prime_value_top10['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = prime_value_top10['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    long_buy_value = data[0].get('LongBuyValue', 0)
                    long_sell_value = data[0].get('LongSellValue', 0)
                    if len(prime_value_top10['prime_margin_sell_new']) <= idx:
                        prime_value_top10['prime_margin_sell_new'].append(margin_sell_new_value)
                        prime_value_top10['prime_margin_buy_close'].append(margin_buy_close_value)
                        prime_value_top10['prime_margin_buy_new'].append(margin_buy_new_value)
                        prime_value_top10['prime_margin_sell_close'].append(margin_sell_close_value)
                        prime_value_top10['prime_long_buy'].append(long_buy_value)
                        prime_value_top10['prime_long_sell'].append(long_sell_value)
                        prime_value_top10['prime_sell_balance'].append(prime_value_top10['prime_margin_sell_new'][idx] - prime_value_top10['prime_margin_buy_close'][idx])
                        prime_value_top10['prime_buy_balance'].append(prime_value_top10['prime_margin_buy_new'][idx] - prime_value_top10['prime_margin_sell_close'][idx])
                        prime_value_top10['prime_long_balance'].append(prime_value_top10['prime_long_buy'][idx] - prime_value_top10['prime_long_sell'][idx])
                    else:
                        prime_value_top10['prime_margin_sell_new'][idx] += margin_sell_new_value
                        prime_value_top10['prime_margin_buy_close'][idx] += margin_buy_close_value
                        prime_value_top10['prime_margin_buy_new'][idx] += margin_buy_new_value
                        prime_value_top10['prime_margin_sell_close'][idx] += margin_sell_close_value
                        prime_value_top10['prime_long_buy'][idx] += long_buy_value
                        prime_value_top10['prime_long_sell'][idx] += long_sell_value
                        prime_value_top10['prime_sell_balance'][idx] = prime_value_top10['prime_margin_sell_new'][idx] - prime_value_top10['prime_margin_buy_close'][idx]
                        prime_value_top10['prime_buy_balance'][idx] = prime_value_top10['prime_margin_buy_new'][idx] - prime_value_top10['prime_margin_sell_close'][idx]
                        prime_value_top10['prime_long_balance'][idx] = prime_value_top10['prime_long_buy'][idx] - prime_value_top10['prime_long_sell'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    prime_top10_list = pd.DataFrame({
                    'code': prime_value_top10['code'],
                    'name': prime_value_top10['name'],
                    '●信用売残額': prime_value_top10['prime_sell_balance'],
                    '●信用買残額': prime_value_top10['prime_buy_balance'],
                    '●現物残額': prime_value_top10['prime_long_balance'],
                    '信用新規売': prime_value_top10['prime_margin_sell_new'],
                    '信用返済買': prime_value_top10['prime_margin_buy_close'],
                    '信用新規買': prime_value_top10['prime_margin_buy_new'],
                    '信用返済売': prime_value_top10['prime_margin_sell_close'],
                    '現物買': prime_value_top10['prime_long_buy'],
                    '現物売': prime_value_top10['prime_long_sell']
                    })

    prime_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']] = prime_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']].apply(lambda x: x / 100000000)

    st.write("""<p style="text-align: right;">(単位: 億)</p>""", unsafe_allow_html=True)
    st.table(prime_top10_list)

# スタンダード市場
if st.button("standard_value_top10"):
    # standard_DataFrame
    standard_value_top10 = {'code': [], 'name': [], 'standard_margin_buy_new': [], 'standard_margin_buy_close': [], 'standard_margin_sell_new': [], 'standard_margin_sell_close': [], 'standard_buy_balance': [], 'standard_sell_balance': [],  'standard_long_buy': [], 'standard_long_sell': [], 'standard_long_balance': []}

    # スタンダード市場のランキング取得
    response = requests.get(standard_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # スタンダード上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            standard_value_top10['code'].append(row.find('li').get_text())
            standard_value_top10['name'].append(row.find('a').get_text())
            if len(standard_value_top10['code']) == 10:
                break
        for day in day_list:
            for code in standard_value_top10['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = standard_value_top10['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    long_buy_value = data[0].get('LongBuyValue', 0)
                    long_sell_value = data[0].get('LongSellValue', 0)
                    if len(standard_value_top10['standard_margin_sell_new']) <= idx:
                        standard_value_top10['standard_margin_sell_new'].append(margin_sell_new_value)
                        standard_value_top10['standard_margin_buy_close'].append(margin_buy_close_value)
                        standard_value_top10['standard_margin_buy_new'].append(margin_buy_new_value)
                        standard_value_top10['standard_margin_sell_close'].append(margin_sell_close_value)
                        standard_value_top10['standard_long_buy'].append(long_buy_value)
                        standard_value_top10['standard_long_sell'].append(long_sell_value)
                        standard_value_top10['standard_sell_balance'].append(standard_value_top10['standard_margin_sell_new'][idx] - standard_value_top10['standard_margin_buy_close'][idx])
                        standard_value_top10['standard_buy_balance'].append(standard_value_top10['standard_margin_buy_new'][idx] - standard_value_top10['standard_margin_sell_close'][idx])
                        standard_value_top10['standard_long_balance'].append(standard_value_top10['standard_long_buy'][idx] - standard_value_top10['standard_long_sell'][idx])
                    else:
                        standard_value_top10['standard_margin_sell_new'][idx] += margin_sell_new_value
                        standard_value_top10['standard_margin_buy_close'][idx] += margin_buy_close_value
                        standard_value_top10['standard_margin_buy_new'][idx] += margin_buy_new_value
                        standard_value_top10['standard_margin_sell_close'][idx] += margin_sell_close_value
                        standard_value_top10['standard_long_buy'][idx] += long_buy_value
                        standard_value_top10['standard_long_sell'][idx] += long_sell_value
                        standard_value_top10['standard_sell_balance'][idx] = standard_value_top10['standard_margin_sell_new'][idx] - standard_value_top10['standard_margin_buy_close'][idx]
                        standard_value_top10['standard_buy_balance'][idx] = standard_value_top10['standard_margin_buy_new'][idx] - standard_value_top10['standard_margin_sell_close'][idx]
                        standard_value_top10['standard_long_balance'][idx] = standard_value_top10['standard_long_buy'][idx] - standard_value_top10['standard_long_sell'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    standard_top10_list = pd.DataFrame({
                    'code': standard_value_top10['code'],
                    'name': standard_value_top10['name'],
                    '●信用売残額': standard_value_top10['standard_sell_balance'],
                    '●信用買残額': standard_value_top10['standard_buy_balance'],
                    '●現物残額': standard_value_top10['standard_long_balance'],
                    '信用新規売': standard_value_top10['standard_margin_sell_new'],
                    '信用返済買': standard_value_top10['standard_margin_buy_close'],
                    '信用新規買': standard_value_top10['standard_margin_buy_new'],
                    '信用返済売': standard_value_top10['standard_margin_sell_close'],
                    '現物買': standard_value_top10['standard_long_buy'],
                    '現物売': standard_value_top10['standard_long_sell']
                    })

    standard_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']] = standard_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']].apply(lambda x: x / 100000000)

    st.write("""<p style="text-align: right;">(単位: 億)</p>""", unsafe_allow_html=True)
    st.table(standard_top10_list)

# グロース市場
if st.button("growth_value_top10"):
    # growth_DataFrame
    growth_value_top10 = {'code': [], 'name': [], 'growth_margin_buy_new': [], 'growth_margin_buy_close': [], 'growth_margin_sell_new': [], 'growth_margin_sell_close': [], 'growth_buy_balance': [], 'growth_sell_balance': [], 'growth_long_buy': [], 'growth_long_sell': [], 'growth_long_balance': []}

    # グロース市場のランキング取得
    response = requests.get(growth_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # グロース上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            growth_value_top10['code'].append(row.find('li').get_text())
            growth_value_top10['name'].append(row.find('a').get_text())
            if len(growth_value_top10['code']) == 10:
                break
        for day in day_list:
            for code in growth_value_top10['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = growth_value_top10['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    long_buy_value = data[0].get('LongBuyValue', 0)
                    long_sell_value = data[0].get('LongSellValue', 0)
                    if len(growth_value_top10['growth_margin_sell_new']) <= idx:
                        growth_value_top10['growth_margin_sell_new'].append(margin_sell_new_value)
                        growth_value_top10['growth_margin_buy_close'].append(margin_buy_close_value)
                        growth_value_top10['growth_margin_buy_new'].append(margin_buy_new_value)
                        growth_value_top10['growth_margin_sell_close'].append(margin_sell_close_value)
                        growth_value_top10['growth_long_buy'].append(long_buy_value)
                        growth_value_top10['growth_long_sell'].append(long_sell_value)
                        growth_value_top10['growth_sell_balance'].append(growth_value_top10['growth_margin_sell_new'][idx] - growth_value_top10['growth_margin_buy_close'][idx])
                        growth_value_top10['growth_buy_balance'].append(growth_value_top10['growth_margin_buy_new'][idx] - growth_value_top10['growth_margin_sell_close'][idx])
                        growth_value_top10['growth_long_balance'].append(growth_value_top10['growth_long_buy'][idx] - growth_value_top10['growth_long_sell'][idx])
                    else:
                        growth_value_top10['growth_margin_sell_new'][idx] += margin_sell_new_value
                        growth_value_top10['growth_margin_buy_close'][idx] += margin_buy_close_value
                        growth_value_top10['growth_margin_buy_new'][idx] += margin_buy_new_value
                        growth_value_top10['growth_margin_sell_close'][idx] += margin_sell_close_value
                        growth_value_top10['growth_long_buy'][idx] += long_buy_value
                        growth_value_top10['growth_long_sell'][idx] += long_sell_value
                        growth_value_top10['growth_sell_balance'][idx] = growth_value_top10['growth_margin_sell_new'][idx] - growth_value_top10['growth_margin_buy_close'][idx]
                        growth_value_top10['growth_buy_balance'][idx] = growth_value_top10['growth_margin_buy_new'][idx] - growth_value_top10['growth_margin_sell_close'][idx]
                        growth_value_top10['growth_long_balance'][idx] = growth_value_top10['growth_long_buy'][idx] - growth_value_top10['growth_long_sell'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    growth_top10_list = pd.DataFrame({
                    'code': growth_value_top10['code'],
                    'name': growth_value_top10['name'],
                    '●信用売残額': growth_value_top10['growth_sell_balance'],
                    '●信用買残額': growth_value_top10['growth_buy_balance'],
                    '●現物残額': growth_value_top10['growth_long_balance'],
                    '信用新規売': growth_value_top10['growth_margin_sell_new'],
                    '信用返済買': growth_value_top10['growth_margin_buy_close'],
                    '信用新規買': growth_value_top10['growth_margin_buy_new'],
                    '信用返済売': growth_value_top10['growth_margin_sell_close'],
                    '現物買': growth_value_top10['growth_long_buy'],
                    '現物売': growth_value_top10['growth_long_sell']
                    })

    growth_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']] = growth_top10_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '現物買', '現物売', '●信用売残額', '●信用買残額', '●現物残額']].apply(lambda x: x / 100000000)

    st.write("""<p style="text-align: right;">(単位: 億)</p>""", unsafe_allow_html=True)
    st.table(growth_top10_list)




# 投資部門別売買状況
st.write("↓ error")
section = st.selectbox('select_section', ['TSEPrime', 'TSEStandard', 'TSEGrowth'])
# データを抽出してリストに格納
dates = []
individuals_balance = []
foreigners_balance = []
proprietary_balance = []
investment_trusts_balance = []

if st.button("Investors Trading Trends"):
    r = requests.get(f"https://api.jquants.com/v1/markets/trades_spec?section={section}&from={day_list[0]}&to={day_list[-1]}", headers=headers)
    for entry in r.json()["trades_spec"]:
        dates.append(entry["PublishedDate"])
        individuals_balance.append(entry["IndividualsBalance"])
        foreigners_balance.append(entry["ForeignersBalance"])
        proprietary_balance.append(entry["ProprietaryBalance"])
        investment_trusts_balance.append(entry["InvestmentTrustsBalance"])

    # データをDataFrameに変換
    data = {
        "PublishedDate": dates,
        "IndividualsBalance": individuals_balance,
        "ForeignersBalance": foreigners_balance,
        "ProprietaryBalance": proprietary_balance,
        "InvestmentTrustsBalance": investment_trusts_balance
    }
    df = pd.DataFrame(data)

    # 日付でソート
    df.sort_values("PublishedDate", inplace=True)

    st.write("blue: 個人, orange: 外人, green: 自己, red: 投信")
    # グラフを作成
    plt.figure(figsize=(12, 6))

    plt.plot(df["PublishedDate"], df["IndividualsBalance"], marker='o', label="個人")
    plt.plot(df["PublishedDate"], df["ForeignersBalance"], marker='o', label="海外投資家")
    plt.plot(df["PublishedDate"], df["ProprietaryBalance"], marker='o', label="自己")
    plt.plot(df["PublishedDate"], df["InvestmentTrustsBalance"], marker='o', label="投信")

    plt.xlabel("公表日")
    plt.ylabel("差引残高（円）")
    plt.title("投資部門別差引残高の推移")
    plt.legend()
    plt.grid(True)

    plt.xticks(rotation=45)
    plt.tight_layout()

    # Streamlitで表示する場合
    st.pyplot(plt)
