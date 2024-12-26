from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class TestStrategy(IStrategy):
    minimal_roi = {
        "0": 100
    }
    stoploss = -100
    timeframe = '15m'
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['sell'] = 0
        return dataframe