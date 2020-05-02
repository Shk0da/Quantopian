# Average Daily Returns in pipe  
from quantopian.pipeline import factors, filters, classifiers, Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing as USEP  
from quantopian.algorithm import attach_pipeline, pipeline_output
import quantopian.pipeline.filters as Filters
import quantopian.pipeline.factors as Factors
import pandas as pd
import numpy as np
from sqlalchemy import or_

def initialize(context): 
    context.mv = 0.01
    context.ma = 14
    context.ma_long = 200
    context.mains = [symbol('GOLD'), symbol('SPY')]
    context.assets = [symbol('GIM'), symbol('UPRO'), symbol('TQQQ')]
    context.desired_allocation = [(0.2), (0.2), (0.2)]
    context.cash_protect = 1.00/len(context.assets)
    context.available_money = context.portfolio.cash
    
    schedule_function(calculate, date_rules.every_day(), time_rules.market_open(minutes = 65))
    schedule_function(record_metrics, date_rules.every_day(), time_rules.market_open())
    schedule_function(
        rebalance,date_rules.month_start(days_offset=1),time_rules.market_open(minutes=60)
    )
    
def rebalance(context, data):
    for i in range(1, len(context.assets)):
        if data.can_trade(context.assets[i]) and context.portfolio.cash > data.current(context.assets[i], 'price'):
            order_target_percent(context.assets[i], context.desired_allocation[i])
    context.available_money = context.portfolio.cash
    
def calculate(context, data):  
    for it in range(1, len(context.assets)):
        ticker = context.assets[it]
        price = data.current(ticker, 'price') 
        pct_avg = data.history(ticker, "close", 4, "1d").pct_change().mean()
        if (context.portfolio.cash > 0):
            decision(context, data, ticker, price, pct_avg)

def decision(context, data, ticker, price, pct_avg):
    is_move = abs(pct_avg) > context.mv
    if is_move and data.can_trade(ticker):
        if pct_avg < 0 and context.available_money>0:
             # buy
             buy_position(context, data, ticker, price)
        elif pct_avg > 0 and context.portfolio.positions[ticker].amount>0:
             # sell
             sell_position(context, data, ticker, price)
            
def get_better_main(context, data):
    best = context.mains[0]
    for it in range(1, len(context.mains)):
        ticker = context.mains[it]
        ma = data.history(ticker, 'close', context.ma,'1d').mean()
        ma_long = data.history(ticker, 'close', context.ma_long,'1d').mean()
        if (ma > ma_long):
            return ticker
    return best
    
def get_worse_main(context, data):
    best = context.mains[0]
    for it in range(1, len(context.mains)):
        ticker = context.mains[it]
        amount = context.portfolio.positions[ticker].amount
        ma = data.history(ticker, 'close', context.ma,'1d').mean()
        ma_long = data.history(ticker, 'close', context.ma_long,'1d').mean()
        if (ma < ma_long):
            return ticker
        if (amount > 0):
            best = ticker
    return best

def buy_position(context, data, ticker, price):
    main = get_worse_main(context, data)
    cash = context.available_money*context.cash_protect
    main_price = data.current(main, 'price')
    real_main_amount = context.portfolio.positions[main].amount
    main_amount = min(real_main_amount, round(cash / main_price))
    if main_amount>0 and data.can_trade(main):
        log.info("MAIN SELL "+str(main_amount)+". Ticker: "+str(main)+", price: " + str(main_price))
        order(main, -main_amount, main_price)
        context.available_money = context.available_money + (main_amount*main_price)
            
    amount = round(cash / price)
    if amount>0 and context.available_money > amount * price:
        log.info("BUY "+str(amount)+". Ticker: "+str(ticker)+", price: " + str(price))
        order(ticker, amount, price)
        context.available_money = context.available_money - (amount*price)
        log.info(" ")
        
def sell_position(context, data, ticker, price):
    amount = context.portfolio.positions[ticker].amount
    if amount>0:
        log.info("SELL "+str(amount)+". Ticker: "+str(ticker)+", price: " + str(price))
        order(ticker, -amount, price)
        context.available_money = context.available_money + (amount*price)
    
        free_cash = amount * price
        main = get_better_main(context, data)
        main_price = data.current(main, 'price')
        main_amount = round(free_cash / main_price)
        if main_amount>0 and data.can_trade(main) and context.available_money > (main_amount * main_price):
            log.info("MAIN BUY "+str(main_amount)+". Ticker: "+str(main)+", price: " + str(main_price))
            order(main, main_amount, main_price) 
            context.available_money = context.available_money - (main_amount*main_price)
            log.info(" ")
    
def record_metrics(context, data):
    total_cash = context.available_money
    
    for it in range(1, len(context.mains)):
        ticker = context.mains[it]
        price = data.current(ticker, 'price') 
        amount = context.portfolio.positions[ticker].amount
        total_cash = total_cash + (amount * price)
    
    for it in range(1, len(context.assets)):
        ticker = context.assets[it]
        price = data.current(ticker, 'price') 
        amount = context.portfolio.positions[ticker].amount
        total_cash = total_cash + (amount * price)
    
    record(usd = total_cash)
