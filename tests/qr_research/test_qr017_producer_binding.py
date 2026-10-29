"""One metadata-only check for the exact QD015 handoff; no dataset or replay."""
import copy
import unittest

from research.qr015 import dataset


class ProducerBindingTest(unittest.TestCase):
    def test_qd015_exact_identity_accepts_and_old_or_mixed_identity_rejects(self):
        request = {
            'schema': 'qr015.import-request.v1', 'training_authorized': False,
            'input_kind': 'SYNTHETIC',
            'qd_commit': '577aeed903b9eefdb2c176dac7e3e67f999731ea',
            'qd_manifest_sha256': 'a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2',
            'qd_code_sha256': {
                'research/qd013/exports.py': 'bbd8e0f79fa4ff597f064ade8fb70eae1d5e323fdb3d9a454a069526bd842f46',
                'research/qd013/market.py': 'c0017f6c5d8d464395888a8c91d284dbdf9cd85b8b457dee87c5e99e605e2729',
                'research/qd013/inputs.py': '545b6959faf9113084286abf5ec133529feac8e98d46231c071e0b10b5977bed',
            },
            'source_metadata': {key: '1'*64 for key in ('ohlcv','funding','mark','mark_result')},
            'source_binding_ref': 'fixture:qd015-metadata-only',
            'binding': {
                'account_id': 'fixture:account', 'trajectory_id': 'fixture:trajectory',
                'scenario_id': 'P0', 'policy_id': 'ALLOW_ALL',
                'account_binding_id': 'QR010_SHARED_NATIVE_X10',
                'instruments': ['gate:usdt:BTC_USDT', 'gate:usdt:ETH_USDT'],
                'scope': {'warmup_start_us': 1672531200000000, 'initial_us': 1704067200000000,
                          'economic_end_us': 1790812800000000, 'tail_end_us': 1790820000000000},
            },
            'input_received_at_us': 1790823600000000, 'assembled_at_us': 1790827200000000,
            'purge': {'complete': False, 'source_ref': 'fixture:unassessed',
                      'instruments': ['gate:usdt:BTC_USDT', 'gate:usdt:ETH_USDT']},
            'limits': {'max_records': 1, 'max_input_bytes': 1024, 'max_row_bytes': 1024,
                       'max_output_bytes': 4096},
        }
        self.assertEqual(dataset._request(request), request['binding']['scope'])
        old_commit = '9adcbb01a584b35ba384e1ca6bc461d97a782469'
        old_manifest = 'd6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a'
        for commit, manifest in ((old_commit, old_manifest),
                                 (old_commit, request['qd_manifest_sha256']),
                                 (request['qd_commit'], old_manifest)):
            altered = copy.deepcopy(request)
            altered.update(qd_commit=commit, qd_manifest_sha256=manifest)
            with self.assertRaisesRegex(dataset.DatasetError, 'QD_VERSION_MISMATCH'):
                dataset._request(altered)
        altered = copy.deepcopy(request)
        altered['qd_code_sha256']['research/qd013/exports.py'] = '0'*64
        with self.assertRaisesRegex(dataset.DatasetError, 'QD_VERSION_MISMATCH'):
            dataset._request(altered)


if __name__ == '__main__':
    unittest.main()
