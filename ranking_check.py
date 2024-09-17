import streamlit as st
import requests
import pandas as pd
import json
import pandas as pd
import datetime as dt
import os
from bs4 import BeautifulSoup

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


# 集計期間を入力
st.title("ranking_check")
start_date = st.date_input("start")
end_date = st.date_input("end")
# 集計する日付をリスト化
if start_date < end_date:
    st.error("end < start !!")
else:
    day_list = []
    current_date = start_date
    while current_date >= end_date:
        day_list.append(current_date.strftime('%Y%m%d'))
        current_date -= dt.timedelta(days=1)
    # 集計期間を表示
    st.write(f"date: {day_list[0]} ~ {day_list[-1]}")

# プライム市場
if st.button("プライム市場 売買代金上位50銘柄"):
    # prime_DataFrame
    prime_value_top50 = {'code': [], 'name': [], 'prime_margin_buy_new': [], 'prime_margin_buy_close': [], 'prime_margin_sell_new': [], 'prime_margin_sell_close': [], 'prime_buy_balance': [], 'prime_sell_balance': []}
    # growth_value_top50 = {'code': [], 'name': [], 'growth_margin_buy_new': [], 'growth_margin_buy_close': [], 'growth_margin_sell_new': [], 'growth_margin_sell_close': [], 'growth_buy_balance': [], 'growth_sell_balance': []}

    # プライム市場のランキング取得
    response = requests.get(prime_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # プライム上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            prime_value_top50['code'].append(row.find('li').get_text())
            prime_value_top50['name'].append(row.find('a').get_text())
        for day in day_list:
            for code in prime_value_top50['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = prime_value_top50['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    if len(prime_value_top50['prime_margin_sell_new']) <= idx:
                        prime_value_top50['prime_margin_sell_new'].append(margin_sell_new_value)
                        prime_value_top50['prime_margin_buy_close'].append(margin_buy_close_value)
                        prime_value_top50['prime_margin_buy_new'].append(margin_buy_new_value)
                        prime_value_top50['prime_margin_sell_close'].append(margin_sell_close_value)
                        prime_value_top50['prime_sell_balance'].append(prime_value_top50['prime_margin_sell_new'][idx] - prime_value_top50['prime_margin_buy_close'][idx])
                        prime_value_top50['prime_buy_balance'].append(prime_value_top50['prime_margin_buy_new'][idx] - prime_value_top50['prime_margin_sell_close'][idx])
                    else:
                        prime_value_top50['prime_margin_sell_new'][idx] += margin_sell_new_value
                        prime_value_top50['prime_margin_buy_close'][idx] += margin_buy_close_value
                        prime_value_top50['prime_margin_buy_new'][idx] += margin_buy_new_value
                        prime_value_top50['prime_margin_sell_close'][idx] += margin_sell_close_value
                        prime_value_top50['prime_sell_balance'][idx] = prime_value_top50['prime_margin_sell_new'][idx] - prime_value_top50['prime_margin_buy_close'][idx]
                        prime_value_top50['prime_buy_balance'][idx] = prime_value_top50['prime_margin_buy_new'][idx] - prime_value_top50['prime_margin_sell_close'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    prime_top50_list = pd.DataFrame({
                    'code': prime_value_top50['code'],
                    'name': prime_value_top50['name'],
                    '信用新規売': prime_value_top50['prime_margin_sell_new'],
                    '信用返済買': prime_value_top50['prime_margin_buy_close'],
                    '信用新規買': prime_value_top50['prime_margin_buy_new'],
                    '信用返済売': prime_value_top50['prime_margin_sell_close'],
                    '信用売残額': prime_value_top50['prime_sell_balance'],
                    '信用買残額': prime_value_top50['prime_buy_balance']
                    })

    prime_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']] = prime_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']].apply(lambda x: x / 100000000)

    st.write("プライム市場 売買代金上位50銘柄(億円)")
    st.table(prime_top50_list)

# スタンダード市場
if st.button("スタンダード市場 売買代金上位50銘柄"):
    # standard_DataFrame
    standard_value_top50 = {'code': [], 'name': [], 'standard_margin_buy_new': [], 'standard_margin_buy_close': [], 'standard_margin_sell_new': [], 'standard_margin_sell_close': [], 'standard_buy_balance': [], 'standard_sell_balance': []}

    # スタンダード市場のランキング取得
    response = requests.get(standard_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # スタンダード上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            standard_value_top50['code'].append(row.find('li').get_text())
            standard_value_top50['name'].append(row.find('a').get_text())
        for day in day_list:
            for code in standard_value_top50['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = standard_value_top50['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    if len(standard_value_top50['standard_margin_sell_new']) <= idx:
                        standard_value_top50['standard_margin_sell_new'].append(margin_sell_new_value)
                        standard_value_top50['standard_margin_buy_close'].append(margin_buy_close_value)
                        standard_value_top50['standard_margin_buy_new'].append(margin_buy_new_value)
                        standard_value_top50['standard_margin_sell_close'].append(margin_sell_close_value)
                        standard_value_top50['standard_sell_balance'].append(standard_value_top50['standard_margin_sell_new'][idx] - standard_value_top50['standard_margin_buy_close'][idx])
                        standard_value_top50['standard_buy_balance'].append(standard_value_top50['standard_margin_buy_new'][idx] - standard_value_top50['standard_margin_sell_close'][idx])
                    else:
                        standard_value_top50['standard_margin_sell_new'][idx] += margin_sell_new_value
                        standard_value_top50['standard_margin_buy_close'][idx] += margin_buy_close_value
                        standard_value_top50['standard_margin_buy_new'][idx] += margin_buy_new_value
                        standard_value_top50['standard_margin_sell_close'][idx] += margin_sell_close_value
                        standard_value_top50['standard_sell_balance'][idx] = standard_value_top50['standard_margin_sell_new'][idx] - standard_value_top50['standard_margin_buy_close'][idx]
                        standard_value_top50['standard_buy_balance'][idx] = standard_value_top50['standard_margin_buy_new'][idx] - standard_value_top50['standard_margin_sell_close'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    standard_top50_list = pd.DataFrame({
                    'code': standard_value_top50['code'],
                    'name': standard_value_top50['name'],
                    '信用新規売': standard_value_top50['standard_margin_sell_new'],
                    '信用返済買': standard_value_top50['standard_margin_buy_close'],
                    '信用新規買': standard_value_top50['standard_margin_buy_new'],
                    '信用返済売': standard_value_top50['standard_margin_sell_close'],
                    '信用売残額': standard_value_top50['standard_sell_balance'],
                    '信用買残額': standard_value_top50['standard_buy_balance']
                    })

    standard_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']] = standard_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']].apply(lambda x: x / 100000000)

    st.write("スタンダード市場 売買代金上位50銘柄(億円)")
    st.table(standard_top50_list)

# グロース市場
if st.button("グロース市場 売買代金上位50銘柄"):
    # growth_DataFrame
    growth_value_top50 = {'code': [], 'name': [], 'growth_margin_buy_new': [], 'growth_margin_buy_close': [], 'growth_margin_sell_new': [], 'growth_margin_sell_close': [], 'growth_buy_balance': [], 'growth_sell_balance': []}

    # グロース市場のランキング取得
    response = requests.get(growth_ranking_url)
    if response.status_code == 200:
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # グロース上位50銘柄コードを格納
        rows = soup.select('tbody tr')
        for row in rows:
            growth_value_top50['code'].append(row.find('li').get_text())
            growth_value_top50['name'].append(row.find('a').get_text())
        for day in day_list:
            for code in growth_value_top50['code']:
                r = requests.get(f"https://api.jquants.com/v1/markets/breakdown?code={code}&date={day}", headers=headers)
                data = r.json().get('breakdown')
                if data:
                    idx = growth_value_top50['code'].index(code)
                    margin_sell_new_value = data[0].get('MarginSellNewValue', 0)
                    margin_buy_close_value = data[0].get('MarginBuyCloseValue', 0)
                    margin_buy_new_value = data[0].get('MarginBuyNewValue', 0)
                    margin_sell_close_value = data[0].get('MarginSellCloseValue', 0)
                    if len(growth_value_top50['growth_margin_sell_new']) <= idx:
                        growth_value_top50['growth_margin_sell_new'].append(margin_sell_new_value)
                        growth_value_top50['growth_margin_buy_close'].append(margin_buy_close_value)
                        growth_value_top50['growth_margin_buy_new'].append(margin_buy_new_value)
                        growth_value_top50['growth_margin_sell_close'].append(margin_sell_close_value)
                        growth_value_top50['growth_sell_balance'].append(growth_value_top50['growth_margin_sell_new'][idx] - growth_value_top50['growth_margin_buy_close'][idx])
                        growth_value_top50['growth_buy_balance'].append(growth_value_top50['growth_margin_buy_new'][idx] - growth_value_top50['growth_margin_sell_close'][idx])
                    else:
                        growth_value_top50['growth_margin_sell_new'][idx] += margin_sell_new_value
                        growth_value_top50['growth_margin_buy_close'][idx] += margin_buy_close_value
                        growth_value_top50['growth_margin_buy_new'][idx] += margin_buy_new_value
                        growth_value_top50['growth_margin_sell_close'][idx] += margin_sell_close_value
                        growth_value_top50['growth_sell_balance'][idx] = growth_value_top50['growth_margin_sell_new'][idx] - growth_value_top50['growth_margin_buy_close'][idx]
                        growth_value_top50['growth_buy_balance'][idx] = growth_value_top50['growth_margin_buy_new'][idx] - growth_value_top50['growth_margin_sell_close'][idx]
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    growth_top50_list = pd.DataFrame({
                    'code': growth_value_top50['code'],
                    'name': growth_value_top50['name'],
                    '信用新規売': growth_value_top50['growth_margin_sell_new'],
                    '信用返済買': growth_value_top50['growth_margin_buy_close'],
                    '信用新規買': growth_value_top50['growth_margin_buy_new'],
                    '信用返済売': growth_value_top50['growth_margin_sell_close'],
                    '信用売残額': growth_value_top50['growth_sell_balance'],
                    '信用買残額': growth_value_top50['growth_buy_balance']
                    })

    growth_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']] = growth_top50_list[['信用新規売', '信用返済買', '信用新規買', '信用返済売', '信用売残額', '信用買残額']].apply(lambda x: x / 100000000)

    st.write("グロース市場 売買代金上位50銘柄(億円)")
    st.table(growth_top50_list)
