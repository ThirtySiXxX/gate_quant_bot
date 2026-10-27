import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

HAS_SKLEARN = importlib.util.find_spec('sklearn') is not None
if HAS_SKLEARN:
    from research.qr001.validation import (block_interval, load_manifest_data, paired_daily_losses,
                                         split_stages, validate_frame)
    from research.qr001.models import calibrate, fit_reference, temperature_probabilities
    from src.crypto_ml import FEATURE_NAMES, predict_probabilities
    from src.ml_training import fit_export


@unittest.skipUnless(HAS_SKLEARN, 'optional research requirements are not installed')
class ResearchValidationTests(unittest.TestCase):
    def test_explicit_manifest_ignores_glob_extra_and_detects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ETH_USDT_1h.csv'
            path.write_text('timestamp,open,high,low,close,volume\n0,100,102,99,101,10\n3600,101,103,100,102,12\n')
            record = dict(file=path.name, role='classification', symbol='ETH_USDT', interval_seconds=3600,
                          rows=2, start_ts=0, end_ts=3600, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            (Path(tmp) / 'clean_ETH_USDT_1h.csv').write_text('unexpected non-data')
            result = load_manifest_data(tmp, {'files': [record]}, ['ETH_USDT'])
            self.assertEqual(list(result), [path.name])
            path.write_text(path.read_text().replace('101,10', '101,11'))
            with self.assertRaisesRegex(ValueError, 'hash'):
                load_manifest_data(tmp, {'files': [record]}, ['ETH_USDT'])

    def test_series_rejects_gaps_duplicates_and_invalid_ohlc(self):
        frame = pd.DataFrame(dict(timestamp=[0, 3600, 7200], open=100., high=101., low=99., close=100., volume=10.))
        record = dict(role='classification', rows=3, start_ts=0, end_ts=7200, interval_seconds=3600)
        validate_frame(frame, record)
        for column, value in [('timestamp', 0), ('timestamp', 1800), ('high', 90), ('volume', -1), ('close', np.nan)]:
            bad = frame.copy(); bad.loc[1, column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                validate_frame(bad, record)

    def test_common_time_split_purges_label_overlap_for_all_assets(self):
        rows = pd.DataFrame([dict(symbol=s, feature_time=t, label_end=t + 4 * 3600)
                            for s in ('ETH_USDT', 'BTC_USDT') for t in range(0, 100 * 86400, 3600)])
        groups = split_stages(rows, 80 * 86400, 90 * 86400)
        self.assertLess(groups['fit'].label_end.max(), 49 * 86400)
        self.assertGreaterEqual(groups['calibration'].feature_time.min(), 50 * 86400)
        self.assertLess(groups['calibration'].label_end.max(), 79 * 86400)
        self.assertLess(groups['evaluation'].label_end.max(), 90 * 86400)
        for frame in groups.values():
            counts = frame.groupby('symbol').size()
            self.assertEqual(counts.iloc[0], counts.iloc[1])
        broken = rows[~((rows.symbol == 'BTC_USDT') & (rows.feature_time >= 80 * 86400))]
        with self.assertRaisesRegex(ValueError, 'missing asset'):
            split_stages(broken, 80 * 86400, 90 * 86400)

    def test_research_wrapper_matches_existing_export_and_heldout_inference(self):
        rng = np.random.default_rng(17)
        x = rng.normal(size=(1050, len(FEATURE_NAMES)))
        train = pd.DataFrame(x, columns=FEATURE_NAMES)
        train['target'] = np.resize([-1, 0, 1], len(train))
        train['label_end'] = np.arange(len(train))
        heldout = rng.normal(size=(60, len(FEATURE_NAMES)))
        for kind in ('logistic', 'gradient_boosting'):
            with self.subTest(kind=kind):
                candidate, native = fit_reference(kind, train, 2000, 3000)
                original = fit_export(kind, train, 2000, 3000)
                self.assertEqual(candidate, original)
                np.testing.assert_allclose(predict_probabilities(candidate, heldout), native(heldout), atol=1e-10)

    def test_calibration_boundary_and_native_export(self):
        model = dict(kind='logistic', mean=[0.] * 21, scale=[1.] * 21,
                     coef=np.zeros((3, 21)).tolist(), intercept=np.log([.05, .1, .85]).tolist(),
                     trained_until=0., valid_from=500000., valid_until=600000.)
        calibration = pd.DataFrame(np.zeros((300, 21)), columns=FEATURE_NAMES)
        calibration['target'] = np.resize([-1, 0, 1], 300)
        calibration['feature_time'] = 100000 + np.arange(300)
        calibration['label_end'] = calibration.feature_time + 14400
        unchanged = copy.deepcopy(model)
        scaled, temperature = calibrate(model, calibration, 500000)
        self.assertEqual(model, unchanged)
        self.assertGreater(temperature, 1)
        self.assertEqual(scaled['trained_until'], calibration.label_end.max())
        rows = np.zeros((10, 21))
        np.testing.assert_allclose(predict_probabilities(scaled, rows),
            temperature_probabilities(predict_probabilities(model, rows), temperature), atol=1e-12)
        # Equality at the embargo boundary is excluded, not silently accepted.
        bad = calibration.copy(); bad.loc[0, 'label_end'] = 500000 - 86400
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            calibrate(model, bad, 500000)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            calibrate(dict(model, trained_until=100000 - 86400), calibration, 500000)

    def test_cross_asset_duplication_does_not_shrink_daily_bootstrap(self):
        rows = pd.DataFrame(dict(fold=[1] * 20, symbol=['ETH_USDT'] * 20,
            feature_time=np.arange(20) * 86400, matched_raw_log_loss=np.ones(20),
            calibrated_log_loss=1 + np.sin(np.arange(20)) * .01))
        daily = paired_daily_losses(rows)
        duplicated = paired_daily_losses(pd.concat([rows, rows.assign(symbol='BTC_USDT')]))
        pd.testing.assert_frame_equal(daily, duplicated)
        a = block_interval(daily, 7, 100, 17)
        self.assertEqual(a, block_interval(duplicated, 7, 100, 17))
        self.assertEqual(a['day_clusters'], 20)
        self.assertLess(a['lower_95'], a['upper_95'])

    def test_fold_boundary_does_not_duplicate_or_overweight_utc_day(self):
        rows = pd.DataFrame(dict(fold=[1, 1, 2, 2, 2],
            symbol=['ETH', 'ETH', 'ETH', 'BTC', 'BTC'],
            feature_time=[0, 3600, 7200, 7200, 86400],
            matched_raw_log_loss=[1.] * 5, calibrated_log_loss=[1., 1., 4., 4., 2.]))
        daily = paired_daily_losses(rows)
        self.assertEqual(daily.day.tolist(), [0, 1])
        # Day zero: ETH mean=1, BTC mean=3, equal-asset aggregate=2.
        np.testing.assert_allclose(daily.difference, [2., 1.])
        pd.testing.assert_frame_equal(daily, paired_daily_losses(rows.assign(fold=1)))
        self.assertEqual(block_interval(daily, 1, 100)['day_clusters'], 2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            paired_daily_losses(pd.concat([rows, rows.iloc[:1]]))
        for bad in [pd.concat([daily, daily.iloc[:1]]), daily.assign(day=[0, 2])]:
            with self.assertRaisesRegex(ValueError, 'unique, consecutive'):
                block_interval(bad)
