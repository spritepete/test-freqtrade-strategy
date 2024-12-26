import talib.abstract as ta
from pandas import DataFrame, Series, DatetimeIndex, merge
import pandas as pd
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
pd.set_option("display.precision", 10)

class TestStrategy(IStrategy):
    """
    Rolling Renko strategy with percentage-based brick size
    Tracks high/low levels until step size threshold is reached
    """
    
    minimal_roi = {
        "0": 100
    }

    stoploss = -100
    timeframe = '15m'
    
    use_sell_signal = True
    sell_profit_only = True
    sell_profit_offset = 0.1
    ignore_roi_if_buy_signal = True

    # Strategy parameters
    window_size = 100  # Initial window for average price calculation
    step_percentage = 0.02  # 2% step size

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate rolling Renko bars based on percentage steps
        """
        # Calculate initial average price for step size
        dataframe['rolling_avg'] = dataframe['close'].rolling(window=self.window_size, min_periods=1).mean()
        dataframe['step_size'] = dataframe['rolling_avg'] * self.step_percentage
        
        columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'step_size']
        df = dataframe[columns].copy()
        
        # Initialize output dataframe
        renko_data = []
        current_high = df.iloc[0]['close']
        current_low = df.iloc[0]['close']
        current_trend = None  # None: undecided, True: uptrend, False: downtrend
        last_brick_price = df.iloc[0]['close']
        
        for idx, row in df.iterrows():
            close = row['close']
            step = row['step_size']
            date = row['date']
            volume = row['volume']
            
            if current_trend is None:
                # Initialize trend
                if close >= last_brick_price + step:
                    current_trend = True
                    last_brick_price = close - (close % step)
                elif close <= last_brick_price - step:
                    current_trend = False
                    last_brick_price = close + (step - (close % step))
                continue
            
            if current_trend:  # In uptrend
                current_high = max(current_high, close)
                # Check for trend continuation or reversal
                if close <= last_brick_price - (2 * step):  # Reversal
                    # Add brick for trend change
                    renko_data.append({
                        'date': date,
                        'open': last_brick_price,
                        'high': current_high,
                        'low': close,
                        'close': close,
                        'volume': volume,
                        'trend': False,
                        'step_size': step
                    })
                    current_trend = False
                    last_brick_price = close + (step - (close % step))
                    current_high = close
                    current_low = close
                elif close >= last_brick_price + step:  # New brick in same trend
                    renko_data.append({
                        'date': date,
                        'open': last_brick_price,
                        'high': close,
                        'low': last_brick_price,
                        'close': close,
                        'volume': volume,
                        'trend': True,
                        'step_size': step
                    })
                    last_brick_price = close - (close % step)
            else:  # In downtrend
                current_low = min(current_low, close)
                # Check for trend continuation or reversal
                if close >= last_brick_price + (2 * step):  # Reversal
                    renko_data.append({
                        'date': date,
                        'open': last_brick_price,
                        'high': close,
                        'low': current_low,
                        'close': close,
                        'volume': volume,
                        'trend': True,
                        'step_size': step
                    })
                    current_trend = True
                    last_brick_price = close - (close % step)
                    current_high = close
                    current_low = close
                elif close <= last_brick_price - step:  # New brick in same trend
                    renko_data.append({
                        'date': date,
                        'open': last_brick_price,
                        'high': last_brick_price,
                        'low': close,
                        'close': close,
                        'volume': volume,
                        'trend': False,
                        'step_size': step
                    })
                    last_brick_price = close + (step - (close % step))
        
        # Convert to DataFrame
        if renko_data:
            renko_df = pd.DataFrame(renko_data)
            renko_df['previous_trend'] = renko_df['trend'].shift(1)
            return renko_df
        else:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trend', 'previous_trend', 'step_size'])

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate buy signals based on trend changes and continuations
        """
        dataframe['buy'] = 0
        dataframe['sell'] = 0
        
        # Buy on trend reversal from down to up or trend continuation in uptrend
        for idx, row in dataframe.iterrows():
            if pd.isna(row['previous_trend']):  # Skip first row
                continue
                
            if (row['previous_trend'] == False and row['trend'] == True) or \
               (row['previous_trend'] == True and row['trend'] == True):
                dataframe.loc[idx, 'buy'] = 1
            else:
                dataframe.loc[idx, 'sell'] = 1
        
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        No additional sell signals - using buy=0 as sell signal
        """
        return dataframe