from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from src.crypto_ml import (FEATURE_NAMES,FEATURE_VERSION,causal_features,supervised_samples,
                           load_bundle,prepare_predictions,predict_probabilities)
from src.config import SystematicConfig
from src.portfolio import InstrumentSignal,InstrumentTarget
from src.execution_timing import ExecutionTiming
from src.position_sizing import EntrySizingBook
from src.strategy_execution import decide_execution
from src.strategy_signals import prepare_features,signal_at


def bars(n=600):
    close=100*np.exp(np.cumsum(np.random.default_rng(71).normal(0,.003,n)))
    return pd.DataFrame(dict(timestamp=np.arange(n)*3600+1700000000,open=close,close=close,
                             high=close*1.01,low=close*.99,volume=np.arange(n)+1000.))


def bundle(frame):
    return dict(feature_version=FEATURE_VERSION,feature_names=FEATURE_NAMES,classes=[-1,0,1],models=[dict(
        kind='logistic',mean=[0.]*len(FEATURE_NAMES),scale=[1.]*len(FEATURE_NAMES),
        coef=np.zeros((3,len(FEATURE_NAMES))).tolist(),intercept=np.log([.1,.2,.7]).tolist(),
        trained_until=float(frame.timestamp.iloc[190]),valid_from=float(frame.timestamp.iloc[200]),
        valid_until=float(frame.timestamp.iloc[400]))])


class CryptoMLTests(unittest.TestCase):
    def test_features_match_prefix_and_ignore_future_changes(self):
        frame=bars();before=causal_features(frame)
        pd.testing.assert_frame_equal(before.iloc[:300],causal_features(frame.iloc[:300]))
        frame.loc[300:,'close']*=10
        pd.testing.assert_frame_equal(before.iloc[:300],causal_features(frame).iloc[:300])

    def test_gaps_invalidate_lookbacks_and_labels_and_unknown_tail_is_removed(self):
        frame=bars();full=supervised_samples(frame,'ETH_USDT')
        self.assertLessEqual(full.feature_time.max(),frame.timestamp.iloc[-5])
        self.assertEqual(full.label_end.max(),frame.timestamp.iloc[-1])
        missing=float(frame.timestamp.iloc[250]);gap=frame.drop(index=250).reset_index(drop=True)
        features=causal_features(gap)
        self.assertTrue(features.iloc[250:418].isna().any(axis=1).all())
        samples=supervised_samples(gap,'ETH_USDT')
        self.assertFalse(((samples.feature_time<=missing)&(samples.label_end>=missing)).any())
        self.assertTrue((samples.label_end>samples.feature_time).all())

    def test_label_classes_have_distinct_up_down_and_neutral_meanings(self):
        sample=supervised_samples(bars(),'ETH_USDT')
        self.assertEqual(set(sample.target),{-1,0,1})
        self.assertTrue((sample.loc[sample.target==1,'forward_return']>.0024).all())
        self.assertTrue((sample.loc[sample.target==-1,'forward_return']<-.0024).all())
        self.assertTrue((sample.loc[sample.target==0,'forward_return'].abs()<=.0024).all())

    def test_model_availability_is_causal_and_exports_softmax_probabilities(self):
        frame=bars();model=bundle(frame)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model.json';path.write_text(json.dumps(model))
            predictions=prepare_predictions(frame,path)
            self.assertNotEqual(predictions[198]['status'],'ok')
            self.assertAlmostEqual(predictions[199]['long'],.7)
            self.assertNotEqual(predictions[399]['status'],'ok')
            model['models'][0]['trained_until']=model['models'][0]['valid_from']
            path.write_text(json.dumps(model))
            with self.assertRaises(ValueError):load_bundle(path)
            self.assertTrue(all(p['status']!='ok' for p in prepare_predictions(frame,path)))

    def test_tree_json_uses_three_classes_and_rejects_nonfinite_features(self):
        tree=lambda v:dict(left=[-1],right=[-1],feature=[-2],threshold=[-2.],value=[v])
        model=dict(kind='gradient_boosting',initial_raw=[0.,0.,0.],learning_rate=.1,
                   trees=[[tree(-1),tree(0),tree(1)]])
        p=predict_probabilities(model,np.zeros((2,len(FEATURE_NAMES))))
        self.assertTrue((p[:,2]>p[:,1]).all());np.testing.assert_allclose(p.sum(axis=1),1)
        with self.assertRaises(ValueError):predict_probabilities(model,np.full((1,len(FEATURE_NAMES)),np.nan))

    def test_malformed_json_schema_blocks_predictions_without_raising(self):
        frame=bars()
        cases=[[],None,{},dict(bundle(frame),models=[None]),dict(bundle(frame),models={})]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model.json'
            for malformed in cases:
                with self.subTest(model=malformed):
                    path.write_text(json.dumps(malformed))
                    predictions=prepare_predictions(frame,path)
                    self.assertEqual(len(predictions),len(frame))
                    self.assertTrue(all(p['status'].startswith('模型不可用') for p in predictions))

    def test_live_intrahour_tick_uses_latest_closed_prediction_and_missing_file_blocks_entry(self):
        frame=bars()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model.json';path.write_text(json.dumps(bundle(frame)))
            cfg=SystematicConfig(ml_model_path=str(path),short_trend_interval='1h',main_trend_interval='1h',
                min_bars_short=1,min_bars_main=1,regime_ema_long=1)
            data=prepare_features(frame,frame,frame,None,28800,cfg)
            timestamp=float(frame.timestamp.iloc[300])
            self.assertEqual(signal_at('ETH_USDT',data,timestamp+300,cfg).ml_entry['status'],'ok')
            prefix=frame.iloc[:300]
            short_data=prepare_features(prefix,prefix,prefix,None,28800,cfg)
            self.assertNotEqual(signal_at('ETH_USDT',short_data,timestamp+3600,cfg).ml_entry['status'],'ok')
            path.unlink()
            missing=prepare_features(frame,frame,frame,None,28800,cfg)
            self.assertNotEqual(signal_at('ETH_USDT',missing,timestamp,cfg).ml_entry['status'],'ok')

    def test_entry_filter_respects_executed_direction_and_cannot_block_existing_exit(self):
        cfg=SystematicConfig(ml_model_path='fixture',no_trade_buffer_pct=0,execution_timing={'enabled':False})
        signal=InstrumentSignal('ETH_USDT',10,0,10,.2,ml_entry={'status':'ok','long':.7,'short':.1})
        target=InstrumentTarget('ETH_USDT',10,1000,.1,.1)
        def decide(current=0,settings=cfg,tgt=target):
            return decide_execution('ETH_USDT',tgt,signal,current,10000,settings,ExecutionTiming(),EntrySizingBook())
        self.assertTrue(decide().needs_entry_ticket)
        self.assertFalse(decide(settings=replace(cfg,invert_direction=True)).needs_entry_ticket)
        signal.ml_entry={'status':'ok','long':float('nan')}
        self.assertFalse(decide().needs_entry_ticket)
        signal.ml_entry={'status':'missing'}
        exit_plan=decide(current=1000,tgt=replace(target,target_notional=0))
        self.assertTrue(exit_plan.rebalance);self.assertEqual(exit_plan.target_notional,0)

    def test_config_rejects_unsupported_ml_interval(self):
        with self.assertRaises(ValueError):SystematicConfig.build({'ml_model_path':'fixture','short_trend_interval':'15m'})

