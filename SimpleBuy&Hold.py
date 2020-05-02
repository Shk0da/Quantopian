def initialize(context):
    context.assets = [sid(3213), sid(38533), sid(39214)]
    context.desired_allocation = [(0.2), (0.4), (0.4)]

    schedule_function(
        rebalance,date_rules.month_start(days_offset=1),time_rules.market_open(minutes=60)
    ) 
    
def rebalance(context, data):
    for i in range(1, len(context.assets)):
        if data.can_trade(context.assets[i]):
            order_target_percent(context.assets[i], context.desired_allocation[i])
