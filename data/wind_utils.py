import sys
from typing import List, Optional
import pandas as pd

sys.path.append("/Applications/Wind API.app/Contents/python")

from WindPy import w

w.start()


def get_data_in_range(
    instrument: str,
    start_date: str,
    end_date: str,
    indicators: List[str] = None,
    options: str = "unit=1;TradingCalendar=NASDAQ;Currency=USD",
) -> Optional[pd.DataFrame]:
    """
    Fetch historical data from Wind API for a given instrument and date range.

    Parameters
    ----------
    instrument : str
        Instrument code (e.g., 'AAPL.O').
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    indicators : List[str], optional
        List of indicators to fetch. Defaults to standard OHLCV set.
    options : str, optional
        Additional Wind API options string.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with Date index and requested indicators, or None if failed.
    """
    if indicators is None:
        indicators = [
            "high",
            "open",
            "low",
            "close",
            "volume",
            "amt",
            "vwap",
            "adjfactor",
        ]

    data = w.wsd(instrument, ",".join(indicators), start_date, end_date, options)

    if data.ErrorCode != 0:
        raise RuntimeError(
            f"Wind API error {data.ErrorCode} while fetching {instrument}"
        )

    if not data.Times or not data.Data:
        return None

    df = pd.DataFrame(
        list(zip(*data.Data)),
        columns=indicators,
        index=pd.to_datetime(data.Times).strftime("%Y-%m-%d"),
    )
    df.index.name = "date"
    return df
