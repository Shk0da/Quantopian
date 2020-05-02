def initialize(context):
    schedule_function(
        rebalance,date_rules.month_start(days_offset=1),time_rules.market_open(minutes=60)
    ) 
    
def rebalance(context, data):
    month_num = get_datetime().date().month
    if (month_num >= 1 and month_num <= 6) or (month_num >= 9 and month_num <=12):
        order_target_percent(symbol('TLT'), 0.10)
        order_target_percent(symbol('VOO'), 0.90)
    else:
        order_target_percent(symbol('VOO'), 0.10)
        order_target_percent(symbol('TLT'), 0.90)
    log.info(str(context.portfolio.positions))
