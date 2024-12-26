from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import pandas as pd
import numpy as np
import talib.abstract as ta

class TestStrategy(IStrategy):
    minimal_roi = {
        "0": 100
    }
    stoploss = -100
    timeframe = '15m'
    
    # Strategy parameters
    window_size = 100  # Initial window for average price calculation
    step_percentage = 0.02  # 2% step size
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate initial average price for step size
        dataframe['rolling_avg'] = dataframe['close'].rolling(window=self.window_size, min_periods=1).mean()
        dataframe['step_size'] = dataframe['rolling_avg'] * self.step_percentage
        
        # Track high/low levels and generate Renko bars
        current_high = dataframe['close'].iloc[0]
        current_low = dataframe['close'].iloc[0]
        current_trend = None
        last_brick_price = dataframe['close'].iloc[0]
        
        dataframe['trend'] = None
        dataframe['brick_high'] = None
        dataframe['brick_low'] = None
        
        for idx in range(len(dataframe)):
            close = dataframe['close'].iloc[idx]
            step = dataframe['step_size'].iloc[idx]
            
            if current_trend is None:
                if close >= last_brick_price + step:
                    current_trend = True
                    last_brick_price = close - (close % step)
                elif close <= last_brick_price - step:
                    current_trend = False
                    last_brick_price = close + (step - (close % step))
            elif current_trend:  # In uptrend
                current_high = max(current_high, close)
                if close <= last_brick_price - (2 * step):  # Reversal
                    dataframe.loc[idx, 'trend'] = False
                    dataframe.loc[idx, 'brick_high'] = current_high
                    dataframe.loc[idx, 'brick_low'] = close
                    current_trend = False
                    last_brick_price = close + (step - (close % step))
                    current_high = close
                    current_low = close
                elif close >= last_brick_price + step:  # Continue trend
                    dataframe.loc[idx, 'trend'] = True
                    dataframe.loc[idx, 'brick_high'] = close
                    dataframe.loc[idx, 'brick_low'] = last_brick_price
                    last_brick_price = close - (close % step)
            else:  # In downtrend
                current_low = min(current_low, close)
                if close >= last_brick_price + (2 * step):  # Reversal
                    dataframe.loc[idx, 'trend'] = True
                    dataframe.loc[idx, 'brick_high'] = close
                    dataframe.loc[idx, 'brick_low'] = current_low
                    current_trend = True
                    last_brick_price = close - (close % step)
                    current_high = close
                    current_low = close
                elif close <= last_brick_price - step:  # Continue trend
                    dataframe.loc[idx, 'trend'] = False
                    dataframe.loc[idx, 'brick_high'] = last_brick_price
                    dataframe.loc[idx, 'brick_low'] = close
                    last_brick_price = close + (step - (close % step))
        
        dataframe['previous_trend'] = dataframe['trend'].shift(1)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        dataframe['sell'] = 0
        
        # Buy on trend reversal from down to up or trend continuation in uptrend
        buy_mask = (
            ((dataframe['previous_trend'] == False) & (dataframe['trend'] == True)) |
            ((dataframe['previous_trend'] == True) & (dataframe['trend'] == True))
        )
        dataframe.loc[buy_mask, 'buy'] = 1
        dataframe.loc[~buy_mask, 'sell'] = 1
        
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Using buy=0 as sell signal
        return dataframe
