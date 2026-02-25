# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib


class DualHalfTrendStrategy(IStrategy):
    """
    双重 HalfTrend 策略 - 从 Pine Script 转换
    
    使用两个不同参数的 HalfTrend 指标:
    - HalfTrend 1: amplitude=2, channelDeviation=2 (快速)
    - HalfTrend 2: amplitude=10, channelDeviation=2 (慢速)
    
    入场信号: 两个 HalfTrend 同时发出买入信号
    出场信号: 任一 HalfTrend 发出卖出信号
    """

    INTERFACE_VERSION = 3
    can_short: bool = True

    # Minimal ROI
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04,
    }

    stoploss = -0.10
    trailing_stop = False

    timeframe = "1h"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # HalfTrend 1 参数 (快速通道)
    amplitude1 = IntParameter(low=1, high=10, default=2, space="buy", optimize=True, load=True)
    channel_deviation1 = IntParameter(low=1, high=5, default=2, space="buy", optimize=True, load=True)

    # HalfTrend 2 参数 (慢速通道)
    amplitude2 = IntParameter(low=5, high=20, default=10, space="buy", optimize=True, load=True)
    channel_deviation2 = IntParameter(low=1, high=5, default=2, space="buy", optimize=True, load=True)

    startup_candle_count: int = 200

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            # HalfTrend 1 - 快速通道
            "ht1_up": {"color": "green", "type": "line"},
            "ht1_down": {"color": "red", "type": "line"},
            # HalfTrend 2 - 慢速通道  
            "ht2_up": {"color": "blue", "type": "line"},
            "ht2_down": {"color": "orange", "type": "line"},
        },
        "subplots": {
            "趋势状态": {
                "trend1": {"color": "green", "type": "line"},
                "trend2": {"color": "blue", "type": "line"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def calculate_halftrend(self, dataframe: DataFrame, amplitude: int, channel_deviation: int, suffix: str = "") -> DataFrame:
        """
        计算 HalfTrend 指标
        
        :param dataframe: OHLCV 数据
        :param amplitude: 振幅参数
        :param channel_deviation: 通道偏差参数
        :param suffix: 列名后缀
        :return: 添加了 HalfTrend 指标的 DataFrame
        """
        df = dataframe.copy()
        
        # 计算 ATR
        atr2 = ta.ATR(df, timeperiod=100) / 2
        dev = channel_deviation * atr2
        
        # 计算最高价和最低价 (在 amplitude 周期内)
        high_price = df['high'].rolling(window=amplitude).max()
        low_price = df['low'].rolling(window=amplitude).min()
        
        # 计算高低价的 SMA (转换为 pandas Series)
        high_ma = pd.Series(ta.SMA(df['high'], timeperiod=amplitude), index=df.index)
        low_ma = pd.Series(ta.SMA(df['low'], timeperiod=amplitude), index=df.index)
        
        # 初始化变量
        trend = pd.Series(0, index=df.index)
        next_trend = pd.Series(0, index=df.index)
        max_low_price = df['low'].copy()
        min_high_price = df['high'].copy()
        up = pd.Series(0.0, index=df.index)
        down = pd.Series(0.0, index=df.index)
        
        # 逐行计算趋势
        for i in range(1, len(df)):
            # 继承上一行的值
            trend.iloc[i] = trend.iloc[i-1]
            next_trend.iloc[i] = next_trend.iloc[i-1]
            max_low_price.iloc[i] = max_low_price.iloc[i-1]
            min_high_price.iloc[i] = min_high_price.iloc[i-1]
            up.iloc[i] = up.iloc[i-1]
            down.iloc[i] = down.iloc[i-1]
            
            if pd.isna(high_price.iloc[i]) or pd.isna(low_price.iloc[i]):
                continue
            
            if next_trend.iloc[i] == 1:
                max_low_price.iloc[i] = max(low_price.iloc[i], max_low_price.iloc[i-1])
                
                if not pd.isna(high_ma.iloc[i]) and high_ma.iloc[i] < max_low_price.iloc[i] and df['close'].iloc[i] < df['low'].iloc[i-1]:
                    trend.iloc[i] = 1
                    next_trend.iloc[i] = 0
                    min_high_price.iloc[i] = high_price.iloc[i]
            else:
                min_high_price.iloc[i] = min(high_price.iloc[i], min_high_price.iloc[i-1])
                
                if not pd.isna(low_ma.iloc[i]) and low_ma.iloc[i] > min_high_price.iloc[i] and df['close'].iloc[i] > df['high'].iloc[i-1]:
                    trend.iloc[i] = 0
                    next_trend.iloc[i] = 1
                    max_low_price.iloc[i] = low_price.iloc[i]
            
            # 计算 up/down 值
            if trend.iloc[i] == 0:
                if trend.iloc[i-1] != 0:
                    up.iloc[i] = down.iloc[i-1] if not pd.isna(down.iloc[i-1]) else down.iloc[i]
                else:
                    up.iloc[i] = max(max_low_price.iloc[i], up.iloc[i-1]) if not pd.isna(up.iloc[i-1]) else max_low_price.iloc[i]
            else:
                if trend.iloc[i-1] != 1:
                    down.iloc[i] = up.iloc[i-1] if not pd.isna(up.iloc[i-1]) else up.iloc[i]
                else:
                    down.iloc[i] = min(min_high_price.iloc[i], down.iloc[i-1]) if not pd.isna(down.iloc[i-1]) else min_high_price.iloc[i]
        
        # HalfTrend 值
        ht = pd.Series(index=df.index, dtype=float)
        ht = np.where(trend == 0, up, down)
        
        # 拆分为上升和下降两条线(用于不同颜色显示)
        ht_up = np.where(trend == 0, ht, np.nan)  # 多头时显示
        ht_down = np.where(trend == 1, ht, np.nan)  # 空头时显示
        
        # ATR 通道
        atr_high = np.where(trend == 0, up + dev, down + dev)
        atr_low = np.where(trend == 0, up - dev, down - dev)
        
        # 买卖信号
        buy_signal = (trend == 0) & (trend.shift(1) == 1)
        sell_signal = (trend == 1) & (trend.shift(1) == 0)
        
        # 添加到 dataframe
        df[f'ht{suffix}'] = ht
        df[f'ht{suffix}_up'] = ht_up  # 多头线条(绿色/蓝色)
        df[f'ht{suffix}_down'] = ht_down  # 空头线条(红色/橙色)
        df[f'trend{suffix}'] = trend
        df[f'atr_high{suffix}'] = atr_high
        df[f'atr_low{suffix}'] = atr_low
        df[f'buy_signal{suffix}'] = buy_signal.astype(int)
        df[f'sell_signal{suffix}'] = sell_signal.astype(int)
        
        return df

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        添加 HalfTrend 指标
        """
        # 计算 HalfTrend 1 (快速)
        dataframe = self.calculate_halftrend(
            dataframe, 
            self.amplitude1.value, 
            self.channel_deviation1.value, 
            suffix="1"
        )
        
        # 计算 HalfTrend 2 (慢速)
        dataframe = self.calculate_halftrend(
            dataframe, 
            self.amplitude2.value, 
            self.channel_deviation2.value, 
            suffix="2"
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        入场信号逻辑 (当两个通道从不一致转变为一致时入场)
        
        做多条件: 前一根K线两个通道不一致 → 当前K线两个通道都为多头 (trend=0)
        做空条件: 前一根K线两个通道不一致 → 当前K线两个通道都为空头 (trend=1)
        """
        # 前一根K线: 两个通道是否一致
        prev_trends_match = (dataframe['trend1'].shift(1) == dataframe['trend2'].shift(1))
        
        # 当前K线: 两个通道都是多头
        both_bullish = (dataframe['trend1'] == 0) & (dataframe['trend2'] == 0)
        # 当前K线: 两个通道都是空头
        both_bearish = (dataframe['trend1'] == 1) & (dataframe['trend2'] == 1)
        
        # 做多入场: 从不一致 → 都变为多头
        dataframe.loc[
            (
                (~prev_trends_match)  # 前一根K线不一致
                & both_bullish  # 当前K线都是多头
                & (dataframe['volume'] > 0)
            ),
            'enter_long',
        ] = 1

        # 做空入场: 从不一致 → 都变为空头
        dataframe.loc[
            (
                (~prev_trends_match)  # 前一根K线不一致
                & both_bearish  # 当前K线都是空头
                & (dataframe['volume'] > 0)
            ),
            'enter_short',
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        出场信号逻辑 (以 HalfTrend2 反转为准，下一根K线出场)
        
        平多条件: HalfTrend2 从多头转为空头 (trend2 从 0 变为 1)
        平空条件: HalfTrend2 从空头转为多头 (trend2 从 1 变为 0)
        """
        # HalfTrend2 反转信号 (使用 shift(1) 确保在信号确认后的下一根K线出场)
        ht2_turn_bearish = (dataframe['trend2'].shift(2) == 0) & (dataframe['trend2'].shift(1) == 1)
        ht2_turn_bullish = (dataframe['trend2'].shift(2) == 1) & (dataframe['trend2'].shift(1) == 0)
        
        # 平多: HalfTrend2 转为空头
        dataframe.loc[
            (
                ht2_turn_bearish
                & (dataframe['volume'] > 0)
            ),
            'exit_long',
        ] = 1

        # 平空: HalfTrend2 转为多头
        dataframe.loc[
            (
                ht2_turn_bullish
                & (dataframe['volume'] > 0)
            ),
            'exit_short',
        ] = 1

        return dataframe
