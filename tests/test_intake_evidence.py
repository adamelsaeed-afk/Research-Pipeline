"""Approval bookkeeping regressions from the friend's research trial."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_workflow as fixtures
from check_intake import check, intake_sha256


class IntakeEvidenceTests(unittest.TestCase):
    def test_hashes_alone_do_not_establish_recorded_user_approval(self):
        brief = b'Brief with an agent-selected validation route'
        record = fixtures.intake(brief, external=False)
        del record['decisions']['validation_mode']['user_evidence']
        del record['confirmation']['user_evidence']
        record['confirmation']['intake_sha256'] = intake_sha256(record)
        errors = check(record, brief)
        self.assertTrue(any('validation_mode: user_evidence' in error for error in errors))
        self.assertTrue(any('confirmation: user_evidence' in error for error in errors))

    def test_each_external_routing_choice_requires_evidence(self):
        brief = b'External review'
        original = fixtures.intake(brief)
        for key in ('validation_mode', 'validator_cli', 'gap_filler_cli',
                    'validator_transport', 'gap_filler_transport',
                    'validator_model', 'gap_filler_model'):
            with self.subTest(key=key):
                record = copy.deepcopy(original)
                del record['decisions'][key]['user_evidence']
                record['confirmation']['intake_sha256'] = intake_sha256(record)
                self.assertTrue(any(f'{key}: user_evidence' in error
                                    for error in check(record, brief)))

    def test_evidence_requires_a_nonempty_message_reference_and_quote(self):
        brief = b'Confirmed scope'
        invalid = [None, False, 7, [], '', {},
                   {'message_ref': 'turn-2'}, {'quote': 'Approved'},
                   {'message_ref': ' ', 'quote': 'Approved'},
                   {'message_ref': 'turn-2', 'quote': []}]
        for location in ('validation_mode', 'confirmation'):
            for value in invalid:
                with self.subTest(location=location, value=value):
                    record = fixtures.intake(brief, external=False)
                    entry = (record['confirmation'] if location == 'confirmation'
                             else record['decisions'][location])
                    entry['user_evidence'] = value
                    record['confirmation']['intake_sha256'] = intake_sha256(record)
                    self.assertTrue(any(f'{location}: user_evidence' in error
                                        for error in check(record, brief)))

    def test_routing_evidence_changes_invalidate_confirmation(self):
        brief = b'Confirmed scope'
        record = fixtures.intake(brief, external=False)
        record['decisions']['validation_mode']['user_evidence']['quote'] = 'A different instruction'
        self.assertTrue(any('intake SHA-256' in error for error in check(record, brief)))

    def test_explicit_discretion_can_support_a_recorded_choice(self):
        brief = b'Confirmed scope'
        record = fixtures.intake(brief, external=False)
        record['decisions']['validation_mode']['user_evidence'] = {
            'message_ref': 'user-turn-2', 'quote': 'Choose the validation route and proceed.'}
        record['confirmation']['intake_sha256'] = intake_sha256(record)
        self.assertEqual(check(record, brief), [])

    def test_unused_model_can_remain_not_applicable_with_a_reason(self):
        brief = b'External review'
        record = fixtures.intake(brief)
        record['decisions']['validator_model'] = {
            'state': 'not_applicable', 'reason': 'Use the accepted CLI default model.'}
        record['confirmation']['intake_sha256'] = intake_sha256(record)
        self.assertEqual(check(record, brief), [])

    def test_required_routing_choice_cannot_be_marked_not_applicable(self):
        brief = b'External review'
        for key in ('validation_mode', 'validator_cli', 'gap_filler_cli',
                    'validator_transport', 'gap_filler_transport'):
            with self.subTest(key=key):
                record = fixtures.intake(brief)
                entry = record['decisions'][key]
                entry.update(state='not_applicable', reason='Route assumed by the agent')
                del entry['user_evidence']
                record['confirmation']['intake_sha256'] = intake_sha256(record)
                self.assertTrue(any(f'{key}: must be answered' in error
                                    for error in check(record, brief)))

    def test_cli_rejects_legacy_hash_only_confirmation(self):
        brief = b'Legacy confirmed scope'
        record = fixtures.intake(brief, external=False)
        del record['confirmation']['user_evidence']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'brief.md').write_bytes(brief)
            (root / 'intake.json').write_text(json.dumps(record), encoding='utf-8')
            script = Path(__file__).resolve().parents[1] / 'scripts' / 'check_intake.py'
            process = subprocess.run(
                [sys.executable, '-B', str(script), '--record', str(root / 'intake.json'),
                 '--brief', str(root / 'brief.md')], capture_output=True, text=True, timeout=5)
            self.assertEqual(process.returncode, 2)
            self.assertIn('confirmation: user_evidence', process.stderr)


if __name__ == '__main__':
    unittest.main()
