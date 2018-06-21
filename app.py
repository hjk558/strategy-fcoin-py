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


class App():
    def __init__(self):
        self.fcoin = Fcoin()
        self.fcoin.auth(config.api_key, config.api_secret)
        self.log = Log("coin")
        self.symbol = 'ftusdt'
        self.order_id = None
        self.dic_balance = defaultdict(lambda: None)
        self.time_order = time.time()
        self.oldprice = [self.digits(self.get_ticker(),6)]
        self.now_price = 0.0
        self.type = 0
        self.fee = 0.0
        self.begin_balance=self.get_blance()

    def digits(self, num, digit):
        site = pow(10, digit)
        tmp = num * site
        tmp = math.floor(tmp) / site
        return tmp

    def get_ticker(self):
        ticker = self.fcoin.get_market_ticker(self.symbol)
        self.now_price = ticker['data']['ticker'][0]
        self.log.info("now price%s" % self.now_price )
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
            if usdt and abs(price/self.oldprice[len(self.oldprice)-2]-1)<0.02:
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
                time1 = time.time()
                self.process()
                array = [self.order_id,self.now_price,self.type,self.fee,self.symbol,time.strftime('%Y-%m-%d %H:%M:%S')]
                if type != 0:
                    self.save_csv(array)
                self.log.info("--------success-------")
                time2 = time.time()
                self.log.info("app time--%s"% str(time2-time1))
                time.sleep(3)
            except Exception as e:
                self.log.info(e)
                print(e)
            finally:
                self.reset_save_attrubute()



if __name__ == '__main__':
    run = App()
    thread = Thread(target=run.loop)
    thread.start()
    thread.join()
    print('done')
