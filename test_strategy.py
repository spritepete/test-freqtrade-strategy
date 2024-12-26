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
        
        # Initialize tracking columns
        dataframe['current_level'] = None  # Current price level
        dataframe['level_count'] = 0  # How many candles spent at current level
        dataframe['trend'] = None  # Current trend direction
        dataframe['trend_strength'] = 0  # Count of consecutive levels in same direction
        dataframe['max_price'] = dataframe['close']  # Max price seen in current level
        dataframe['min_price'] = dataframe['close']  # Min price seen in current level
        
        # Start from first valid step size
        start_idx = dataframe['step_size'].first_valid_index()
        if start_idx is None:
            return dataframe
            
        # Initialize first level
        first_close = dataframe.loc[start_idx, 'close']
        first_step = dataframe.loc[start_idx, 'step_size']
        current_level = first_close - (first_close % first_step)
        current_trend = None
        trend_strength = 0
        level_count = 0
        max_price = first_close
        min_price = first_close
        
        # Process each candle
        for idx in range(start_idx, len(dataframe)):
            close = dataframe.loc[idx, 'close']
            step = dataframe.loc[idx, 'step_size']
            
            # Update max/min prices
            max_price = max(max_price, close)
            min_price = min(min_price, close)
            
            # Check if price moved to new level
            levels_up = int((max_price - current_level) / step)
            levels_down = int((current_level - min_price) / step)
            
            if levels_up >= 1 or levels_down >= 1:
                # Price moved beyond current level
                new_trend = True if levels_up >= 1 else False
                
                if current_trend is None:
                    # First trend establishment
                    current_trend = new_trend
                    trend_strength = 1
                elif new_trend == current_trend:
                    # Trend continuation
                    trend_strength += 1
                else:
                    # Trend reversal
                    current_trend = new_trend
                    trend_strength = 1
                
                # Update level
                if new_trend:
                    current_level += step * levels_up
                else:
                    current_level -= step * levels_down
                    
                # Reset counters
                level_count = 0
                max_price = close
                min_price = close
            else:
                # Still within current level
                level_count += 1
            
            # Update dataframe
            dataframe.loc[idx, 'current_level'] = current_level
            dataframe.loc[idx, 'level_count'] = level_count
            dataframe.loc[idx, 'trend'] = current_trend
            dataframe.loc[idx, 'trend_strength'] = trend_strength
            dataframe.loc[idx, 'max_price'] = max_price
            dataframe.loc[idx, 'min_price'] = min_price
        
        # Add previous trend for signal generation
        dataframe['previous_trend'] = dataframe['trend'].shift(1)
        dataframe['previous_strength'] = dataframe['trend_strength'].shift(1)
        
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        dataframe['sell'] = 0
        
        # Buy conditions:
        # 1. Trend reversal from down to up
        # 2. Strong uptrend continuation (trend_strength >= 2)
        buy_mask = (
            ((dataframe['previous_trend'] == False) & (dataframe['trend'] == True)) |
            ((dataframe['trend'] == True) & (dataframe['trend_strength'] >= 2))
        )
        
        dataframe.loc[buy_mask, 'buy'] = 1
        dataframe.loc[~buy_mask, 'sell'] = 1
        
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Using buy=0 as sell signal
        return dataframe
