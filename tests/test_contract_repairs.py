"""Regression coverage for the post-review V1.2 contract repairs."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_regressions as fixtures
from research_dispatch import input_ids, parse_role_object, run_dispatch, validate_result
from check_intake import check, intake_sha256


def issue():
    return {'id': 'G1', 'claim_id': 'C1', 'problem': 'Source contradicts the claim',
            'evidence_urls': ['https://example.org/docs'], 'severity': 'material'}


class ResultContractTests(unittest.TestCase):
    def test_zero_progress_blocked_preserves_all_unaccounted_claims(self):
        result = fixtures.validation(())
        result.update(verdict='blocked', summary='Authentication failed before source access')
        with tempfile.TemporaryDirectory() as directory:
            path = fixtures.CoverageRegressions().dispatch(Path(directory), result)
            self.assertEqual(json.loads(path.read_text())['verdict'], 'blocked')
            metadata = json.loads((path.parent / 'dispatch.json').read_text())
            self.assertEqual(metadata['unaccounted_input_ids'], ['C1', 'C2'])

    def test_empty_checks_are_allowed_only_for_zero_progress_blocking(self):
        for verdict in ('approved', 'approved_with_limits', 'gaps_found'):
            result = fixtures.validation(())
            result.update(verdict=verdict, issues=[issue()] if verdict == 'gaps_found' else [])
            with self.subTest(verdict=verdict), self.assertRaises(ValueError):
                validate_result('validate', result, ['C1'])
        for field in ('checks', 'checked_claim_ids'):
            result = fixtures.validation()
            result.update(verdict='blocked')
            result[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_result('validate', result, ['C1'])
        result = fixtures.validation(())
        result.update(verdict='blocked', summary='  ')
        with self.assertRaises(ValueError):
            validate_result('validate', result, ['C1'])

    def test_parser_rejects_nested_quoted_and_incomplete_results(self):
        encoded = json.dumps(fixtures.validation())
        invalid = [
            '{"outer": ' + encoded,
            '{"outer":\n' + encoded,
            '{"example": ' + encoded + '}',
            '[' + encoded + ']',
            json.dumps(encoded),
            "'" + encoded + "'",
            '```json\n' + encoded + '\n```',
            '> ' + encoded,
            '"Quoted result:\n' + encoded + '\n"',
            "'Quoted result:\n" + encoded,
            'Example:\n```json\n' + encoded + '\n```',
            encoded + '\n' + encoded,
            encoded + '\nTrailing explanation.',
        ]
        for content in invalid:
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_role_object(content)

    def test_parser_accepts_contractions_but_rejects_quotation_delimiters(self):
        result = {"role": "validate", "verdict": "approved"}
        encoded = json.dumps(result)
        for prefix in ("I'll check the source.\n", "I've checked it; it's supported.\n"):
            with self.subTest(prefix=prefix):
                self.assertEqual(parse_role_object(prefix + encoded), result)
        for prefix in ("'\n", "The result is '\n", "'example'\n", "I'll quote '\n"):
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    parse_role_object(prefix + encoded)

    def test_parser_accepts_plain_final_result_with_optional_narration(self):
        result = fixtures.validation()
        result['summary'] = 'Evidence contains {braces}, [arrays], and "quotes"'
        encoded = json.dumps(result, indent=2)
        for content in (encoded, 'Checked sources.\n\n' + encoded + '\n'):
            with self.subTest(content=content):
                self.assertEqual(parse_role_object(content), result)

    def test_truncated_response_fails_dispatch_and_retains_raw_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = fixtures.fixtures.DispatchTests()
            helper.setup_files(root)
            content = '{"outer": ' + json.dumps(fixtures.validation(('F1',)))
            fixtures.FakeProcess.output = json.dumps({'event': 'result', 'result': {
                'status': 'SUCCESS', 'response': content}})
            with patch('research_dispatch.subprocess.Popen', fixtures.FakeProcess):
                with self.assertRaises(ValueError):
                    run_dispatch(helper.options(root))
            stage = next((root / 'dispatch').iterdir())
            self.assertEqual(json.loads((stage / 'dispatch.json').read_text())['status'], 'failed')
            self.assertFalse((stage / 'result.json').exists())
            self.assertIn('outer', (stage / 'stdout.txt').read_text())

    def test_issues_require_claim_evidence_and_severity(self):
        result = fixtures.validation()
        result.update(verdict='gaps_found', issues=[issue()])
        for field in ('id', 'claim_id', 'problem', 'evidence_urls', 'severity'):
            invalid_values = [None, False, 7, {}, '  ']
            if field != 'evidence_urls':
                invalid_values.append([])
            for value in ['MISSING', *invalid_values]:
                bad = copy.deepcopy(result)
                if value == 'MISSING':
                    del bad['issues'][0][field]
                else:
                    bad['issues'][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_result('validate', bad, ['C1'])
        for field, value in [('claim_id', 'ABSENT'), ('severity', 'unknown'),
                             ('evidence_urls', ['javascript:bad']), ('evidence_urls', [None])]:
            bad = copy.deepcopy(result)
            bad['issues'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_result('validate', bad, ['C1'])

    def test_valid_issues_keep_document_and_inaccessible_evidence(self):
        for severity, sources, problem in (
            ('material', ['Policy.pdf#page=7', 'https://example.org'], 'Contradictory sources'),
            ('nonmaterial', [], 'Source inaccessible: authentication failed'),
        ):
            result = fixtures.validation()
            result.update(verdict='gaps_found', issues=[{
                **issue(), 'severity': severity, 'evidence_urls': sources, 'problem': problem}])
            validate_result('validate', result, ['C1'])

    def test_incomplete_issue_is_rejected_by_dispatch(self):
        result = fixtures.validation(('C1', 'C2'))
        result.update(verdict='gaps_found', issues=[{'id': 'G1', 'problem': 'Incomplete gap'}])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                fixtures.CoverageRegressions().dispatch(root, result)
            stage = next((root / 'dispatch').iterdir())
            self.assertEqual(json.loads((stage / 'dispatch.json').read_text())['status'], 'failed')
            self.assertFalse((stage / 'result.json').exists())
            self.assertTrue((stage / 'stdout.txt').read_text())


class InputContractTests(unittest.TestCase):
    def test_explicit_ids_cannot_be_supplied_by_examples_or_references(self):
        for text in ('```md\nC1: example only\n```', '~~~\n## C1 example\n~~~',
                     '<!-- C1: comment -->', 'See C1 elsewhere.', 'C1 is referenced elsewhere.', '> C1: quoted example',
                     'The example is `C1: text`.', '`C1`: inline example'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                input_ids(text, ['C1'])

    def test_explicit_ids_preserve_custom_headings_records_and_tables(self):
        for text in ('## custom-claim Finding', 'custom-claim: Finding',
                     '- custom-claim: Finding', '| custom-claim | Finding |'):
            with self.subTest(text=text):
                self.assertEqual(input_ids(text, ['custom-claim']), ['custom-claim'])

    def test_changed_scope_or_operational_decision_invalidates_confirmation(self):
        brief = b'Confirmed scope'
        record = fixtures.intake(brief)
        self.assertEqual(check(record, brief), [])
        for key, answer in (('targets', 'Different subjects'), ('geography', 'Different geography'),
                            ('validator_model', 'different/model'), ('validator_cli', 'other-target'),
                            ('validator_transport', 'docker'), ('validation_mode', 'same_session')):
            changed = copy.deepcopy(record)
            changed['decisions'][key]['answer'] = answer
            with self.subTest(key=key):
                self.assertTrue(any('confirmation' in error for error in check(changed, brief)))

    def test_changed_branch_inventory_invalidates_confirmation(self):
        brief = b'Confirmed scope'
        record = fixtures.intake(brief)
        record['decisions']['extra'] = {'state': 'answered', 'answer': 'New requirement'}
        record['required_branches'].append('extra')
        self.assertTrue(any('confirmation' in error for error in check(record, brief)))

    def test_legacy_confirmation_requires_explicit_renewal(self):
        brief = b'Confirmed scope'
        record = fixtures.intake(brief)
        del record['confirmation']['intake_sha256']
        self.assertTrue(any('confirmation' in error for error in check(record, brief)))
        record['confirmation']['intake_sha256'] = intake_sha256(record)
        self.assertEqual(check(record, brief), [])
        reordered = {**record, 'decisions': dict(reversed(list(record['decisions'].items())))}
        self.assertEqual(check(reordered, brief), [])

    def test_confirmation_hash_preview_does_not_approve_or_modify_intake(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brief = b'Pending approval'
            record = fixtures.intake(brief)
            record['confirmation']['confirmed'] = False
            original = json.dumps(record)
            (root / 'intake.json').write_text(original)
            (root / 'brief.md').write_bytes(brief)
            script = Path(__file__).resolve().parents[1] / 'scripts' / 'check_intake.py'
            process = subprocess.run([sys.executable, '-B', str(script), '--record', str(root / 'intake.json'),
                                      '--brief', str(root / 'brief.md'), '--confirmation-hashes'],
                                     capture_output=True, text=True, timeout=5)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)['intake_sha256'], intake_sha256(record))
            self.assertEqual((root / 'intake.json').read_text(), original)
            self.assertTrue(any('confirmation' in error for error in check(record, brief)))
