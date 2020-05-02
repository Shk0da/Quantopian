import numpy as np
 
def initialize(context):
    context.assets = [sid(3213), sid(38533), sid(39214)]
    context.desired_allocation = [(0.2), (0.4), (0.4)]
    
    context.port_value = 0
    context.contributions = 0 #set to the cumulative contributions you've put in the account
    context.cash_balance = 0 #put in starting cash balance in your account
    context.dividends = 0
    context.sma = 10
    context.cash_protect = 0.9 #reduce available cash by this to ensure no negative
        
    context.current_allocation = np.zeros(len(context.assets))
    context.desired_balance = np.zeros(len(context.assets))
    context.current_balance = np.zeros(len(context.assets))
    context.desired_contribution = np.zeros(len(context.assets))
    context.curr_price = np.zeros(len(context.assets))
    context.price = np.zeros(len(context.assets))
      
    schedule_function(buy_to_balance, date_rules.every_day(), time_rules.market_open(hours=2)) #buy to balance
    schedule_function(record_metrics, date_rules.every_day(), time_rules.market_open()) #record metrics
    schedule_function(log_balances, date_rules.week_end(), time_rules.market_close(minutes=15)) #log week end information
        
#buy to target asset allocation
def buy_to_balance(context, data):
    calculate_balance(context, data)
    
    #determine largest discrepancy stock
    max = context.desired_contribution[0]
    max_i = 0
    for x in range(1, len(context.assets)):
        if context.desired_contribution[x] > max:
            max = context.desired_contribution[x] 
            max_i = x
 
    #make all sales orders 0, don't sell        
    for x in range(0, len(context.assets)):    
        if context.desired_contribution[x]  < 0:
            context.desired_contribution[x]  = 0 #don't ever sell
            
    #determine cash and normalize to total contribution amount      
    cash = context.portfolio.cash*context.cash_protect
    for x in range(0, len(context.assets)):   
        context.desired_contribution[x] = context.desired_contribution[x]*cash/np.sum(context.desired_contribution)
            
    #determine how much to buy of each asset and what the remaining cash will be after    
    shares = np.zeros(len(context.assets))
    for x in range(0, len(context.assets)):
        shares[x] = np.trunc(context.desired_contribution[x]/context.price[x]) #truncate number of shares to buy
        cash = cash - shares[x]*context.price[x]
 
    #buy more of asset most off to reduce cash drag
    shares[max_i] = np.trunc(shares[max_i] + cash/context.price[max_i])
        
    #place orders for each asset
    for x in range(0, len(context.assets)):      
        if data.can_trade(context.assets[x]) and shares[x]>0:
                log.info('BUY: ' + '{:06.2f}'.format(shares[x]) + ' shares of: ' + context.assets[x].symbol + ' at: ' +          '{:06.2f}'.format(context.price[x]))
                order(context.assets[x], shares[x], style=LimitOrder(context.price[x]))     
 
#calculate specs        
def calculate_balance(context, data):
    context.port_value = context.portfolio.portfolio_value
    for x in range(0, len(context.assets)):
        context.desired_balance[x] = context.desired_allocation[x]*context.port_value
        context.curr_price[x] = data.current(context.assets[x],'price')
        context.current_balance[x] = context.portfolio.positions[context.assets[x]].amount*context.curr_price[x]    
        context.current_allocation[x] = context.current_balance[x]/context.portfolio.portfolio_value
        context.desired_contribution[x] = context.desired_balance[x]-context.current_balance[x]
        price_history = data.history(context.assets[x], "price", bar_count=context.sma, frequency="1d")
        context.price[x] = price_history.mean() #only buy at or below the simple moving average
 
#calculate recording metrics to log
def record_metrics(context, data):
    calculate_balance(context, data)
    cash = context.portfolio.cash
    contribution = cash-context.cash_balance
    
    if contribution > 0: #more cash added to the account
        remain = np.remainder(contribution, 100) #see if the cash infusion is a multiple of $100 = indicating a contribution not a dividend
        if remain == 0:
            context.contributions = context.contributions+contribution
        else:
            context.dividends = context.dividends+contribution
    
    context.cash_balance = cash
    total_off = np.sum(np.absolute(context.desired_contribution))
    
    record(value = context.portfolio.portfolio_value, 
           off_target = total_off, cash = context.cash_balance, contributions=context.contributions, dividends=context.dividends)   
    
#calculate and log weekly balances
def log_balances(context, data):    
    calculate_balance(context, data)
    log.info('--')
    log.info('{:09.2f}'.format(context.port_value) + ' Current Value')
    log.info('{:09.2f}'.format(context.contributions) + ' Total Contributions')
    log.info('{:09.2f}'.format(context.port_value-context.contributions) + ' Total Profit')
    log.info('{:09.2f}'.format(context.dividends)+ ' Total Dividends Received')
    log.info('{:09.2f}'.format(context.portfolio.cash)+ ' Cash Balance')
    log.info('{:09.2f}'.format(context.portfolio.cash)+ ' Off Target Allocation')
    for x in range(0, len(context.assets)):
        log.info(' ' + context.assets[x].symbol + ': ' + '{:04.1f}'.format(context.current_allocation[x]*100) + '%, $' + '{:09.2f}'.format(context.current_balance[x]) + ' || Current Price: ' +  '{:06.2f}'.format(context.curr_price[x])+ '|' +  '{:06.2f}'.format(context.price[x]) +  ' :10 day SMA')
    log.info('--')
