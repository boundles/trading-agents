from typing import List, Dict
from datetime import datetime, timedelta
import logging

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

from agents.base_agent import BaseAgent
from data.wind_utils import get_data_in_range


logger = logging.getLogger(__name__)


class MACDDivergenceAgent(BaseAgent):
    def __init__(
        self,
        universe: List[str],
        short_window: int = 12,
        long_window: int = 26,
        signal_window: int = 9,
        min_gap_days: int = 5,
        fetch_window: int = 100,
    ) -> None:
        super().__init__()
        self.universe = universe
        self.short_window = short_window
        self.long_window = long_window
        self.signal_window = signal_window
        self.min_gap_days = min_gap_days
        self.fetch_window = fetch_window

    def _prepare_df(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)
        else:
            df = df.reset_index().rename(columns={"index": "date"})
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                raise ValueError(f"DataFrame missing required column: {col}")
        return df

    def _calc_macd(self, close: pd.Series):
        ema_short = close.ewm(span=self.short_window, adjust=False).mean()
        ema_long = close.ewm(span=self.long_window, adjust=False).mean()
        diff = ema_short - ema_long
        dea = diff.ewm(span=self.signal_window, adjust=False).mean()
        hist = diff - dea
        return diff, dea, hist

    def _find_local_extrema(
        self, series: pd.Series, order: int = 3, mode: str = "min"
    ) -> np.ndarray:
        """
        使用scipy的argrelextrema寻找局部极值点，返回索引数组。
        order参数决定窗口大小。
        mode=="min"找局部最小值，"max"找局部最大值。
        """
        if mode == "min":
            idxs = argrelextrema(series.values, np.less_equal, order=order)[0]
        else:
            idxs = argrelextrema(series.values, np.greater_equal, order=order)[0]
        return idxs

    def detect_signals(self, df: pd.DataFrame) -> List[Dict]:
        df = self._prepare_df(df)
        df["macd_diff"], df["macd_dea"], df["macd_hist"] = self._calc_macd(df["close"])

        signals = []

        # 找局部低点（价格最低点）和高点
        low_idxs = self._find_local_extrema(df["close"], order=3, mode="min")
        high_idxs = self._find_local_extrema(df["close"], order=3, mode="max")

        # 底背离检测：
        # 连续两个局部低点，第二个低点价格更低，但MACD柱状图对应低点抬高（背离）
        for i in range(len(low_idxs) - 1):
            idx1, idx2 = low_idxs[i], low_idxs[i + 1]

            date1 = pd.to_datetime(df.loc[idx1, "date"])
            date2 = pd.to_datetime(df.loc[idx2, "date"])
            if (date2 - date1).days < self.min_gap_days:
                continue

            price1, price2 = df.loc[idx1, "close"], df.loc[idx2, "close"]
            hist1, hist2 = df.loc[idx1, "macd_hist"], df.loc[idx2, "macd_hist"]

            # 底背离条件：价格创新低，但macd_hist却抬高
            if price2 < price1 and hist2 > hist1:
                signals.append(
                    {
                        "date": df.loc[idx2, "date"],
                        "type": "bullish_divergence",
                        "price1": float(price1),
                        "price2": float(price2),
                        "macd_hist1": float(hist1),
                        "macd_hist2": float(hist2),
                        "idx": idx2,
                    }
                )

        # 顶背离检测：
        # 连续两个局部高点，第二个高点价格更高，但MACD柱状图对应高点降低（背离）
        for i in range(len(high_idxs) - 1):
            idx1, idx2 = high_idxs[i], high_idxs[i + 1]

            date1 = pd.to_datetime(df.loc[idx1, "date"])
            date2 = pd.to_datetime(df.loc[idx2, "date"])
            if (date2 - date1).days < self.min_gap_days:
                continue

            price1, price2 = df.loc[idx1, "close"], df.loc[idx2, "close"]
            hist1, hist2 = df.loc[idx1, "macd_hist"], df.loc[idx2, "macd_hist"]

            # 顶背离条件：价格创新高，但macd_hist降低
            if price2 > price1 and hist2 < hist1:
                signals.append(
                    {
                        "date": df.loc[idx2, "date"],
                        "type": "bearish_divergence",
                        "price1": float(price1),
                        "price2": float(price2),
                        "macd_hist1": float(hist1),
                        "macd_hist2": float(hist2),
                        "idx": idx2,
                    }
                )

        return signals

    def run(self, current_date: str = None) -> Dict[str, List[Dict]]:
        results = {}
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        for sym in self.universe:
            try:
                start_dt = datetime.strptime(current_date, "%Y-%m-%d") - timedelta(
                    days=self.fetch_window
                )
                start_date = start_dt.strftime("%Y-%m-%d")
                # 需要你实现或替换get_data_in_range函数
                df = get_data_in_range(
                    sym, start_date=start_date, end_date=current_date
                )
                if df is None or len(df) == 0:
                    continue

                signals = self.detect_signals(df)
                if signals:
                    # 只保留当天最新的信号
                    df_prepared = self._prepare_df(df)
                    last_idx = len(df_prepared) - 1
                    today_signals = [s for s in signals if s["idx"] == last_idx]
                    if today_signals:
                        results[sym] = today_signals

            except Exception as e:
                logger.exception(f"Error processing {sym}: {e}")
                continue

        return results
