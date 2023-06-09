import asyncio
import time
import requests
import pandas as pd

# ДАННЫЕ
Data = [None, None] # минимум и максимум за последний час
LastUpdate = pd.Series([]) # -> price of bitcoin, price of ethirium

# КОНСТАНТЫ

T = 8 # частота обновлений текущих данных
H = 120 # частота обновлений данных за последний час
K = 0.8 # коэффициент корреляции BTC и ETH
HOUR = 3600 # константа для вычитания часа

NAMES = ['bitcoin','ethereum'] # список для удобного обращения по именам
url_curr = 'https://api.cryptorank.io/v1/currencies?api_key=e6527d21c11b808e717b0cf4845933cecc59eaf80666c32a131f88784972'
# ссылка для запроса по текущим данным

def true_price(pr , delt): # дельты
    return pr + pr * delt


# функция для запроса данных часовой давности
async def recheck():
    global Data
    # создает ссылку для парсинга в зависимости от параметра
    def create_url_for_hist(name):
        return f'https://api.coingecko.com/api/v3/coins/{name}/market_chart/range'

    # получает данные, сохраняет в джейсон
    def parsing(name):
        cur_time = time.time()
        params = {'vs_currency': 'usd',
                  'from': cur_time - HOUR,
                  'to': cur_time}
        url = create_url_for_hist(name)
        result = requests.get(url, params).json()
        return result

    # преобразует данные в конкретную форму
    def saving(js):
        pricing = js.get('prices')
        table = [] #итоговый список
        for item in pricing:
            table.append(item[1]) # единица - это индекс, данные парсятся списком вместе с указателем времени
        return table

    def count_the_delta_for_list(btc, eth):
        btc_prev = pd.concat([pd.Series([btc[0]]), btc])
        eth_prev = pd.concat([pd.Series([eth[0]]), eth])
        btc_prev.pop(11)
        eth_prev.pop(11)
        btc_prev.index = range(0,12,1)
        dB = (btc - btc_prev )/ btc_prev
        dE = (eth - eth_prev )/ eth_prev
        return dE - dB * K

    def inner_main():
        global Data
        cur_tab = pd.DataFrame([])
        for coin in NAMES:
            answer_for_request = parsing(coin)
            cur_tab[coin] = saving(answer_for_request)
        deltas = count_the_delta_for_list(cur_tab[NAMES[0]], cur_tab[NAMES[1]])
        prices = true_price(cur_tab[NAMES[1]], deltas)
        Data[0] = prices.min()
        Data[1] = prices.max()
        return

    inner_main()
    print("Произошло обновление данных последнего часа")
    await asyncio.create_task(asyncio.sleep(H))  # 300 секунд - время ожидания до обновления данных сайта  ### !!! Возможно следует поставить таску
    return await asyncio.create_task(recheck())

# main() - функция запроса сиюминутных данных
async def main():
    def cleaning(r):
        r = r.get('data')
        table = {}
        for bar in r:
            name = bar.get('slug')
            if name in NAMES:
                cur = bar
                cur = cur.get('values')
                cur = cur.get('USD')
                price = cur.get('price')
                table[name] = price
        return table


    def count_the_delta(btc, eth):
        global LastUpdate
        if  LastUpdate.empty:
            dE, dB = 0,0
        else:
            dB = (btc - LastUpdate[0])/btc
            dE = (eth - LastUpdate[1])/eth
        return dE - dB * K

    def comparison(curr):
        global Data
        for value in Data:
            percent_of_change = abs(curr - value) / value * 100
            print(percent_of_change)
            if percent_of_change >= 1:
                print("В течение последнего часа произошло изменение цены на 1%")
        return
    answer = requests.get(url_curr).json()
    answer_cleaned = cleaning(answer)
    b = answer_cleaned.get(NAMES[0])
    e = answer_cleaned.get(NAMES[1])
    delta = count_the_delta(b, e)
    global LastUpdate
    LastUpdate[0] = b
    LastUpdate[1] = e
    result = true_price(LastUpdate[1],delta)
    comparison(result)
    print("Актуальная цена : ", result)
    await asyncio.create_task(asyncio.sleep(T))
    return await asyncio.create_task(main())

async def general():
    task1 = asyncio.create_task(recheck())
    task2 = asyncio.create_task(main())
    await task1
    await task2

if __name__ == "__main__":
    asyncio.run(general())


