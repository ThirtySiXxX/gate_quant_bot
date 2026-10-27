from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from src import data_fetcher as df


def candles(times):
    return pd.DataFrame(dict(timestamp=times,open=100.,high=101.,low=99.,close=100.,volume=10.))


class HistoryGapTests(unittest.TestCase):
    def test_cache_hit_repairs_internal_gap_instead_of_only_refreshing_latest(self):
        with tempfile.TemporaryDirectory() as temp:
            candles([0,3600,14400,18000]).to_csv(Path(temp)/'ETH_USDT_1h.csv',index=False)
            def page(ex,symbol,interval,limit,to_ts=None):
                return candles([7200,10800]) if to_ts==10800 else candles([14400,18000])
            with patch('src.data_fetcher.time.time',return_value=21600), \
                 patch('src.data_fetcher.time.sleep'), patch('src.data_fetcher._fetch_page',side_effect=page) as fetch:
                result=df.fetch_candles(None,'ETH_USDT','1h',.25,cache_dir=temp)
            self.assertEqual(result.timestamp.tolist(),[0,3600,7200,10800,14400,18000])
            self.assertTrue(any(c.kwargs.get('to_ts')==10800 for c in fetch.call_args_list))
            self.assertEqual(len(pd.read_csv(Path(temp)/'ETH_USDT_1h.csv')),6)

    def test_unfillable_gap_raises_and_does_not_invent_flat_candles(self):
        with patch('src.data_fetcher._fetch_page',return_value=candles([])):
            with self.assertRaisesRegex(ValueError,'仍缺少2根'):
                df._repair_gaps(None,'ETH_USDT','1h',candles([0,10800]),0)

    def test_prefix_before_listing_is_not_an_internal_gap(self):
        result=df._repair_gaps(None,'NEW_USDT','1h',candles([100*3600,101*3600]),0)
        self.assertEqual(len(result),2)

