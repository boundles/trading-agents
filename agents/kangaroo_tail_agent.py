from typing import List, Dict
from datetime import datetime, timedelta

import pandas as pd

from agents.base_agent import BaseAgent
from data.wind_utils import get_data_in_range


class KangarooTailAgent(BaseAgent):
    def __init__(
        self,
        universe: List[str],
        tail_type: str = "lower",
        tail_min_ratio: float = 2.0,
        body_max_ratio: float = 0.35,
        min_trend_days: int = 3,
        trend_required: bool = True,
        fetch_window: int = 20,
    ) -> None:
        super().__init__()
        assert tail_type in ("lower", "upper")
        assert fetch_window > min_trend_days
        self.universe = universe
        self.tail_type = tail_type
        self.tail_min_ratio = tail_min_ratio
        self.body_max_ratio = body_max_ratio
        self.min_trend_days = min_trend_days
        self.trend_required = trend_required
        self.fetch_window = fetch_window

    @staticmethod
    def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)
        else:
            df = df.reset_index().rename(columns={"index": "date"})
        for c in ["open", "high", "low", "close", "volume"]:
            if c not in df.columns:
                raise ValueError(f"data frame missing required column: {c}")
        return df

    def _is_downtrend(self, prices: pd.Series) -> bool:
        if len(prices) < self.min_trend_days:
            return False
        diffs = prices.diff().dropna()
        return diffs.mean() < 0

    def _is_uptrend(self, prices: pd.Series) -> bool:
        if len(prices) < self.min_trend_days:
            return False
        diffs = prices.diff().dropna()
        return diffs.mean() > 0

    def detect_signals(self, df: pd.DataFrame) -> List[Dict]:
        df = self._prepare_df(df)
        signals = []
        eps = 1e-9
        N = self.min_trend_days

        for idx, row in df.iterrows():
            o, h, l, c = (
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
            )
            body = abs(c - o)
            upper_shadow = max(h - max(c, o), 0)
            lower_shadow = max(min(c, o) - l, 0)
            full_range = max(h - l, eps)

            # 计算最近N天的平均full_range（不包括当前idx）
            start_idx = max(0, idx - N)
            recent_ranges = []
            for i in range(start_idx, idx):
                hr = float(df.loc[i, "high"])
                lr = float(df.loc[i, "low"])
                recent_ranges.append(max(hr - lr, eps))
            if len(recent_ranges) == 0:
                avg_range = eps  # 避免除零
            else:
                avg_range = sum(recent_ranges) / len(recent_ranges)

            # 当前full_range要至少是平均的2倍
            if full_range < 2 * avg_range:
                continue

            if body / full_range > self.body_max_ratio:
                continue

            if self.tail_type == "lower":
                if lower_shadow < self.tail_min_ratio * max(body, eps):
                    continue
                if lower_shadow / full_range < 0.4:
                    continue
                if self.trend_required:
                    prev_closes = df["close"].iloc[
                        max(0, idx - self.min_trend_days) : idx
                    ]
                    if not self._is_downtrend(prev_closes):
                        continue
                signals.append(
                    {
                        "date": df.loc[idx, "date"],
                        "type": "lower",
                        "body": body,
                        "lower_shadow": lower_shadow,
                        "upper_shadow": upper_shadow,
                        "full_range": full_range,
                        "close": c,
                        "open": o,
                        "idx": idx,
                    }
                )

            else:  # upper
                if upper_shadow < self.tail_min_ratio * max(body, eps):
                    continue
                if upper_shadow / full_range < 0.4:
                    continue
                if self.trend_required:
                    prev_closes = df["close"].iloc[
                        max(0, idx - self.min_trend_days) : idx
                    ]
                    if not self._is_uptrend(prev_closes):
                        continue
                signals.append(
                    {
                        "date": df.loc[idx, "date"],
                        "type": "upper",
                        "body": body,
                        "lower_shadow": lower_shadow,
                        "upper_shadow": upper_shadow,
                        "full_range": full_range,
                        "close": c,
                        "open": o,
                        "idx": idx,
                    }
                )
        return signals

    def run(self, current_date: str = None) -> Dict[str, List[Dict]]:
        results = {}
        for sym in self.universe:
            try:
                start_date = (
                    datetime.strptime(current_date, "%Y-%m-%d")
                    - timedelta(days=self.fetch_window)
                ).strftime("%Y-%m-%d")
                df = get_data_in_range(
                    sym, start_date=start_date, end_date=current_date
                )
                if df is None or len(df) == 0:
                    continue
                signals = self.detect_signals(df)
                if signals:
                    today_signals = [s for s in signals if s["idx"] == len(df) - 1]
                    if today_signals:
                        results[sym] = today_signals
            except Exception:
                continue
        return results
