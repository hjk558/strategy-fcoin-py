#!-*-coding:utf-8 -*-
import math
import time
from fcoin3 import Fcoin
from collections import defaultdict
import config
from threading import Thread
from balance import balance
from log_back import Log
import csv
from concurrent.futures import ThreadPoolExecutor
class App():
    def __init__(self):
        self.fcoin = Fcoin()
        self.fcoin.auth(config.api_key, config.api_secret)
        self.log = Log("")
        self.symbol = 'ftusdt'
        self.order_id = None
        self.dic_balance = defaultdict(lambda: None)
        self.time_order = time.time()
        self.oldprice = self.digits(self.get_ticker(),6)
        self.now_price = 0.0
        self.type = 0
        self.fee = 0.0
        self.count_flag = 0
        self.fall_rise = 0
        self.buy_price =0.0
        self.sell_price = 0.0
        self.executor = ThreadPoolExecutor(max_workers=4)

    def digits(self, num, digit):
        site = pow(10, digit)
        tmp = num * site
        tmp = math.floor(tmp) / site
        return tmp

    def get_ticker(self):
        ticker = self.fcoin.get_market_ticker(self.symbol)['data']['ticker']
        self.now_price = ticker[0]
        self.buy_price = ticker[2]
        self.sell_price = ticker[4]
        return self.now_price

    def get_blance(self):
        dic_blance = defaultdict(lambda: None)
        data = self.fcoin.get_balance()
        if data:
            for item in data['data']:
                dic_blance[item['currency']] = balance(float(item['available']), float(item['frozen']),float(item['balance']))
        return dic_blance

    def save_csv(self,array):
        with open("data/trade.csv","a+",newline='') as w:
            writer = csv.writer(w)
            writer.writerow(array)

    def reset_save_attrubute(self):
        self.now_price = 0.0
        self.type = 0
        self.fee = 0.0
        self.order_id = None

    def my_process(self):
        self.dic_balance = self.get_blance()
        ft = self.dic_balance["ft"]
        usdt = self.dic_balance["usdt"]
        print("usdt ---",usdt.available,"ft----",ft.available)
        self.log.info("usdt has---%s ft has---%s"% (usdt.available, ft.available))
        price = self.digits(self.get_ticker(),6)
        new_old_price = abs(price/self.oldprice - 1)*100
        print("new price --",price)
        print("old price --",self.oldprice)
        print("price波动百分比----",new_old_price)
        self.log.info("new price--%s" % price)
        self.log.info("old price--%s" % self.oldprice)
        self.log.info("price波动百分比%s" % new_old_price)
        if new_old_price > 0.005:
            if price > self.oldprice and self.fall_rise < 5:
                self.fall_rise = self.fall_rise + 1
            elif price < self.oldprice and self.fall_rise > -5:
                self.fall_rise = self.fall_rise - 1
        print("跌涨标志----", self.fall_rise)
        self.log.info("跌涨标志---%s"% self.fall_rise)
        if 0.008 <= new_old_price < 0.4:
            order_list = self.fcoin.list_orders(symbol=self.symbol,states="submitted")["data"]
            print("size",len(order_list))
            self.log.info("size--%s"% len(order_list))
            if not order_list or len(order_list) < 5:
                self.count_flag = 0
                dif_price = (self.sell_price * 0.001 + self.buy_price * 0.001)/2
                if (price > self.oldprice and new_old_price > 0.08) or self.fall_rise > 3:
                    print("涨--------------")
                    self.log.info("涨----------")
                    bids_dif = self.buy_price - dif_price * 0.6
                    asks_dif = self.sell_price + dif_price * 1.5
                elif (price < self.oldprice and new_old_price > 0.08) or self.fall_rise < -3:
                    print("跌---------------")
                    self.log.info("跌--------------")
                    bids_dif = self.buy_price - dif_price * 1.5
                    asks_dif = self.sell_price + dif_price * 0.6
                else:
                    print("平衡-------------")
                    self.log.info("平衡-----------------")
                    bids_dif = self.buy_price - dif_price
                    asks_dif = self.sell_price + dif_price

                bids_price_b = self.digits(bids_dif,6)
                print("bids_price",bids_price_b)
                self.log.info("bids_price----%s"% bids_price_b)
                asks_price_a = self.digits(asks_dif,6)
                print("asks_price",asks_price_a)
                self.log.info("asks_price----%s"% asks_price_a)
                print("交易差------",(asks_price_a-bids_price_b)*1000)
                self.log.info("交易差------%s"%((asks_price_a-bids_price_b)*1000))

                buy_task = self.executor.submit(self.fcoin.buy, self.symbol, bids_price_b, 6)
                sell_task = self.executor.submit(self.fcoin.sell, self.symbol, asks_price_a, 6)
                time.sleep(1)
                if buy_task.done():
                    self.log.info("sell success")
                    print("sell success")
                if sell_task.done():
                    self.log.info("buy success")
                    print("buy success")
            else:
                self.count_flag = self.count_flag+1
                print("sleep begin")
                self.log.info("sleep begin")
                time.sleep(2)
                if len(order_list) >= 1 and self.count_flag >2:
                    order_id = order_list[-1]['id']
                    self.count_flag = 0
                    data = self.fcoin.cancel_order(order_id)
                    print("*******cancel result",data)
                    self.log.info("*******cancel result {%s}" % data)
        else:
            print("##########当前波动无效###########")
            self.log.info("##########当前波动无效###########")

        self.oldprice = price


    def process(self):
        price = self.digits(self.get_ticker(),6)
        self.oldprice.append(price)
        self.dic_balance = self.get_blance()
        ft = self.dic_balance['ft']
        usdt = self.dic_balance['usdt']

        self.log.info("usdt has--[%s]   ft has--[%s]" % (usdt.balance, ft.balance))

        order_list = self.fcoin.list_orders(symbol=self.symbol,states='submitted')['data']
        print(order_list)
        self.log.info("order trading: %s" % order_list)

        if not order_list or len(order_list) < 2:
            if usdt and abs(price/self.oldprice[len(self.oldprice)-2]-1) < 0.02:
                if price*2 < self.oldprice[len(self.oldprice)-2]+self.oldprice[len(self.oldprice)-3]:
                    amount = self.digits(usdt.available / price * 0.25, 2)
                    if amount > 5:
                        data = self.fcoin.buy(self.symbol, price, amount)
                        if data:
                            self.fee = amount*0.001
                            self.order_id = data['data']
                            self.time_order = time.time()
                            self.type = 1
                            self.log.info('buy success price--[%s] amout--[%s] fee--[%s]' % (price,amount ,self.fee))
                else:
                    if float(ft.available) * 0.25 > 5:
                        amount = self.digits(ft.available * 0.25, 2)
                        data = self.fcoin.sell(self.symbol, price, amount)
                        if data:
                            self.fee = amount*price*0.001
                            self.time_order = time.time()
                            self.order_id = data['data']
                            self.type = 2
                            self.log.info("sell success price--[%s] amout--[%s] fee--[%s]" % (price,amount, self.fee))

            else:
                print('价格波动过大 %s' % usdt)
                self.log.info("价格波动过大%s" % usdt)
        else:
            print('system busy')
            if len(order_list) >= 1:
                self.log.info("cancel order {%s}" % order_list[-1])
                order_id = order_list[-1]['id']
                data = self.fcoin.cancel_order(order_id)
                self.log.info("cancel result {%s}" % data)
                if data:
                    if order_list[len(order_list)-1]['side'] == 'buy' and order_list[len(order_list)-1]['symbol'] == 'ftusdt':
                        self.fee = -float(order_list[len(order_list)-1]['amount'])*0.001
                    elif order_list[len(order_list)-1]['side'] == 'sell' and order_list[len(order_list)-1]['symbol'] == 'ftusdt':
                        self.fee = -float(order_list[len(order_list)-1]['amount'])*float(order_list[len(order_list)-1]['price'])*0.001
                    self.type = 3
                    self.order_id = order_id

    def loop(self):
        while True:
            try:
                self.my_process()
                # time1 = time.time()
                # self.process()
                # array = [self.order_id,self.now_price,self.type,self.fee,self.symbol,time.strftime('%Y-%m-%d %H:%M:%S')]
                # if self.type != 0:
                #     self.save_csv(array)
                # self.log.info("--------success-------")
                # time2 = time.time()
                # self.log.info("app time--%s"% str(time2-time1))
                time.sleep(5)
            except Exception as e:
                self.log.info(e)
                print(e)
            # finally:
            #     self.reset_save_attrubute()



if __name__ == '__main__':
    run = App()
    thread = Thread(target=run.loop)
    thread.start()
    thread.join()
    print('done')
