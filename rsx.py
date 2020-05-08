import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.filters import Q3000US  
from quantopian.pipeline.factors import SimpleMovingAverage as SMA  
from quantopian.pipeline.factors import CustomFactor, Returns
from quantopian.pipeline.data.builtin import USEquityPricing  
from quantopian.pipeline.data.morningstar import Fundamentals as ms
import quantopian.optimize as opt  
import pandas as pd
 
def initialize(context):
    # Research benchmark: RTS (Russia in $)
    set_benchmark(symbol('RSX'))
    # List of bond ETFs when market is down. Can be more than one.
    context.BONDS = [symbol('IEF'), symbol('TLT')]
 
    # First sort by ROE
    context.TOP_ROE_QTY = 50 
    # Set target number of securities to hold and top ROE qty to filter  
    context.TARGET_SECURITIES = 5
 
    # This is for the trend following filter  
    context.SPY = symbol('IWM')
    context.TF_LOOKBACK = 50
    context.TF_CURRENT_LOOKBACK = 5
 
    # This is for the determining momentum  
    context.MOMENTUM_LOOKBACK_DAYS = 126 #Momentum lookback  
    context.MOMENTUM_SKIP_DAYS = 2 
    # Initialize any other variables before being used  
    context.stock_weights = pd.Series()  
    context.bond_weights = pd.Series()
 
    # Should probably comment out the slippage and using the default  
    # Create and attach pipeline for fetching all data  
    algo.attach_pipeline(make_pipeline(context), 'pipeline')  
    
    # Schedule functions  
    # Separate the stock selection from the execution for flexibility  
    schedule_function(select_stocks_and_set_weights, date_rules.week_start(), time_rules.market_open(minutes = 1))  
    schedule_function(trade, date_rules.week_start(), time_rules.market_open(minutes = 1))  
    # Metrics
    schedule_function(record_metrics, date_rules.every_day(), time_rules.market_open(minutes=60))
 
def make_pipeline(context):  
    spy_ma50_slice = SMA(inputs=[USEquityPricing.close], window_length=context.TF_CURRENT_LOOKBACK)[context.SPY]  
    spy_ma200_slice = SMA(inputs=[USEquityPricing.close], window_length=context.TF_LOOKBACK)[context.SPY]  
    spy_ma_fast = SMA(inputs=[spy_ma50_slice], window_length=1)  
    spy_ma_slow = SMA(inputs=[spy_ma200_slice], window_length=1)  
    trend_up = spy_ma_fast > spy_ma_slow
    
    # Filters for top quality and momentum to use in our selection criteria  
    universe = Q3000US() 
    quality = ms.long_term_debt_equity_ratio.latest.rank(mask=universe)
    top_quality = quality.top(context.TOP_ROE_QTY, mask=universe)
    
    shifted_quality = ms.total_debt_equity_ratio.latest.rank(mask=top_quality)
    shifted_top = shifted_quality.bottom(context.TOP_ROE_QTY - context.TARGET_SECURITIES, mask=top_quality)
    
    returns_overall = Returns(window_length=context.MOMENTUM_LOOKBACK_DAYS + context.MOMENTUM_SKIP_DAYS)  
    returns_recent = Returns(window_length=context.MOMENTUM_SKIP_DAYS)  
    momentum = returns_overall - returns_recent  
    top_quality_momentum = momentum.top(context.TARGET_SECURITIES, mask=shifted_top)
    
    # Only return values we will use in our selection criteria  
    pipe = Pipeline(
        columns={'trend_up': trend_up, 'top_quality_momentum': top_quality_momentum},
        screen=top_quality_momentum
    )  
    return pipe
 
def select_stocks_and_set_weights(context, data):  
    """  
    Select the stocks to hold based upon data fetched in pipeline.  
    Then determine weight for stocks.  
    Finally, set bond weight to 1-total stock weight to keep portfolio fully invested  
    Sets context.stock_weights and context.bond_weights used in trade function  
    """  
    # Get pipeline output and select stocks  
    df = algo.pipeline_output('pipeline')  
    current_holdings = context.portfolio.positions  
    # Define our rule to open/hold positions  
    # top momentum and don't open in a downturn but, if held, then keep  
    rule = 'top_quality_momentum & (trend_up or (not trend_up & index in @current_holdings))'  
    stocks_to_hold = df.query(rule).index  
    # Set desired stock weights  
    # Equally weight  
    stock_weight = 1.0 / context.TARGET_SECURITIES  
    context.stock_weights = pd.Series(index=stocks_to_hold, data=stock_weight)  
    # Set desired bond weight  
    # Open bond position to fill unused portfolio balance  
    # But always have at least 1 'share' of bonds  
    bond_weight = max(1.0 - context.stock_weights.sum(), 0) / len(context.BONDS)  
    context.bond_weights = pd.Series(index=context.BONDS, data=bond_weight)  
    
def trade(context, data):  
    """  
    Execute trades using optimize.  
    Expects securities (stocks and bonds) with weights to be in context.weights  
    """  
    # Create a single series from our stock and bond weights  
    total_weights = pd.concat([context.stock_weights, context.bond_weights])
 
    # Create a TargetWeights objective  
    target_weights = opt.MaximizeAlpha(total_weights) 

    # Execute the order_optimal_portfolio method with above objective and any constraint  
    constraints = []
    constraints.append(opt.MaxGrossExposure(1.0))
    order_optimal_portfolio(objective = target_weights, constraints = constraints)

def record_metrics(context, data):
    avaliable_cash = context.portfolio.cash + context.portfolio.portfolio_value
    record(usd = avaliable_cash)
