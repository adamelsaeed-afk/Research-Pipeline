"""Observable regressions from the V1.1 legal-AI trial."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import test_workflow as fixtures
FakeProcess = fixtures.FakeProcess
intake = fixtures.intake
from check_intake import check, intake_sha256
from research_dispatch import input_ids, run_dispatch, source_locator, validate_result


def validation(ids=('C1',)):
    return {'role': 'validate', 'verdict': 'approved', 'summary': 'Checked sources',
            'issues': [], 'checked_claim_ids': list(ids),
            'checks': [{'claim_id': i, 'source_url': 'https://example.org/docs#section',
                        'evidence': 'Supports the finding', 'verdict': 'confirmed'} for i in ids]}


class ValueRegressions(unittest.TestCase):
    def test_required_answer_types_and_not_applicable_reasons(self):
        brief = b'Confirmed scope'
        for value in (None, '', '  ', False, 7, [], ['US'], {}):
            with self.subTest(value=value):
                record = intake(brief)
                record['decisions']['geography']['answer'] = value
                self.assertTrue(any('geography' in e for e in check(record, brief)))
        for value in (None, False, 7, []):
            with self.subTest(reason=value):
                record = intake(brief)
                record['decisions']['source_leads'] = {'state': 'not_applicable', 'reason': value}
                self.assertTrue(any('source_leads' in e for e in check(record, brief)))
        record = intake(brief)
        record['decisions']['source_leads']['answer'] = 'none'
        record['confirmation']['intake_sha256'] = intake_sha256(record)
        self.assertEqual(check(record, brief), [])

    def test_malformed_gap_sources_and_unresolved(self):
        result = {'role': 'gap_fill', 'verdict': 'completed', 'summary': 'Correction',
                  'changes': [{'gap_id': 'G1', 'corrected_finding': 'Correction',
                               'source_urls': ['https://example.org']}], 'unresolved': []}
        for sources in ('not a URL list', ['not a URL'], [4], ['javascript:alert(1)']):
            with self.subTest(sources=sources):
                bad = copy.deepcopy(result); bad['changes'][0]['source_urls'] = sources
                with self.assertRaises(ValueError): validate_result('gap_fill', bad, {'G1'})
        bad = copy.deepcopy(result); bad['unresolved'] = [None]
        with self.assertRaises(ValueError): validate_result('gap_fill', bad, {'G1'})

    def test_document_citations_and_url_syntax(self):
        for source in ('Policy.pdf', 'Policy.pdf#page=7', 'capture.html#FAQ', 'document:Policy#section=Retention',
                       'C:\\Documents\\Policy.docx#section=Records', 'https://example.org:443/a#b',
                       'https://[::1]/docs', 'HTTPS://example.org'):
            with self.subTest(source=source):
                self.assertTrue(source_locator(source))
                result = validation()
                result['checks'][0]['source_url'] = source
                validate_result('validate', result, {'C1'})
        for source in (None, 7, '', 'https://', 'https://bad host/x', 'https://host:99999',
                       'ftp://example.org', 'Policy.pdf# ', 'document:Policy# ', 'https://bad_host/a',
                       'javascript:evil.pdf#page=1', 'ftp://host/Policy.pdf#page=7'):
            with self.subTest(source=source):
                self.assertFalse(source_locator(source))

    def test_invalid_summary_issue_and_unresolved_types(self):
        for value in (None, False, 1, [], {}, '  '):
            with self.subTest(value=value):
                result = validation(); result['summary'] = value
                with self.assertRaises(ValueError): validate_result('validate', result, {'C1'})
                result = validation(); result['verdict'] = 'gaps_found'
                result['issues'] = [{'id':'G1', 'claim_id':'C1', 'problem':value,
                                     'evidence_urls':[], 'severity':'material'}]
                with self.assertRaises(ValueError): validate_result('validate', result, {'C1'})
                gap = {'role':'gap_fill', 'verdict':'completed', 'summary':'Unknown', 'changes':[],
                       'unresolved':[{'gap_id':'G1', 'reason':value}]}
                with self.assertRaises(ValueError): validate_result('gap_fill', gap, {'G1'})

    def test_malformed_enum_values_are_gate_errors(self):
        for key in ('research_type', 'validation_mode', 'validator_transport'):
            with self.subTest(key=key):
                record = intake(b'Scope'); record['decisions'][key]['answer'] = []
                self.assertTrue(check(record, b'Scope'))


class CoverageRegressions(unittest.TestCase):
    def dispatch(self, root, result, text='## C1 Finding\nSource: https://example.org\n\n## C2 Finding\nSource: https://example.org\n', role='validate', explicit=None):
        helper = fixtures.DispatchTests()
        helper.setup_files(root)
        options = helper.options(root)
        options.role = role
        if role == 'gap_fill': options.target = 'gap_filler'
        options.input.write_text(text, encoding='utf-8')
        if explicit is not None:
            options.input_ids = root/'ids.json'
            options.input_ids.write_text(json.dumps(explicit), encoding='utf-8')
        FakeProcess.output = json.dumps({'event': 'result', 'result': {'status': 'SUCCESS', 'response': json.dumps(result)}}) if role == 'validate' else json.dumps(result)
        with patch('research_dispatch.subprocess.Popen', FakeProcess):
            return run_dispatch(options)

    def test_dispatch_rejects_missing_unknown_and_duplicate_claims(self):
        for ids in (['C1'], ['C1', 'ABSENT'], ['C1', 'C2', 'C2']):
            with self.subTest(ids=ids), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(ValueError): self.dispatch(root, validation(ids))
                stage = next((root/'dispatch').iterdir())
                self.assertEqual(json.loads((stage/'dispatch.json').read_text())['status'], 'failed')
                self.assertFalse((stage/'result.json').exists())

    def test_complete_multisource_and_explicit_uncertainty(self):
        result = validation(('C1','C2'))
        result['checks'].append({**result['checks'][0], 'source_url':'https://example.org/other'})
        with tempfile.TemporaryDirectory() as directory:
            path = self.dispatch(Path(directory), result)
            self.assertEqual(json.loads(path.read_text())['verdict'],'approved')
        result['verdict']='approved_with_limits'
        result['checks'][1]['verdict']='unverifiable'
        result['limitations']=[{'claim_id':'C2','reason':'Minor metadata unavailable'}]
        with tempfile.TemporaryDirectory() as directory:
            self.dispatch(Path(directory),result)

    def test_partial_nonapproval_is_explicit_and_unknown_issues_fail(self):
        result = validation(); result['verdict'] = 'blocked'
        with tempfile.TemporaryDirectory() as directory:
            path = self.dispatch(Path(directory), result)
            self.assertEqual(json.loads((path.parent/'dispatch.json').read_text())['unaccounted_input_ids'], ['C2'])
        result['verdict'] = 'gaps_found'; result['issues'] = [{'id':'G1', 'claim_id':'ABSENT', 'problem':'Missing',
                                                            'evidence_urls':[], 'severity':'material'}]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): self.dispatch(Path(directory), result)

    def test_gap_accounting_and_valid_change_plus_residual_uncertainty(self):
        gap = {'role':'gap_fill', 'verdict':'completed', 'summary':'Resolved or disclosed',
               'changes':[{'gap_id':'i1','corrected_finding':'Qualified claim','source_urls':['Policy.pdf#page=7']}],
               'unresolved':[{'gap_id':'i1','reason':'Release unclear'}, {'gap_id':'i2','reason':'Inaccessible'}]}
        validate_result('gap_fill', gap, {'i1','i2'})
        for mutation in ('missing', 'unknown', 'duplicate'):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(gap)
                if mutation == 'missing': bad['unresolved'].pop()
                elif mutation == 'unknown': bad['unresolved'][1]['gap_id'] = 'absent'
                else: bad['unresolved'].append(bad['unresolved'][1])
                with self.assertRaises(ValueError): validate_result('gap_fill', bad, {'i1','i2'})

    def test_legacy_parser_ignores_references_examples_and_tables(self):
        text = ('# Findings\n\n## C1 Finding\nReferences C9.\n| C8 | example |\n'
                '```md\n## C7 Example\n```\n<!-- ## C6 Comment -->\n'
                '~~~\nG5: example\n~~~\n- C2: Second claim\n')
        self.assertEqual(input_ids(text), ['C1','C2'])
        self.assertEqual(input_ids('## i1 Issue\ni2: Another issue'), ['i1','i2'])
        with self.assertRaises(ValueError): input_ids('## C1 One\nC1: Two')

    def test_explicit_custom_layout_and_exact_staged_hash(self):
        import hashlib
        content = '| ID | Finding |\n|---|---|\n| clio-chat | Documented |\n| filevine-chat | Unknown |\n'
        result = validation(('clio-chat','filevine-chat'))
        with tempfile.TemporaryDirectory() as directory:
            path = self.dispatch(Path(directory), result, content, explicit=['clio-chat','filevine-chat'])
            bound = json.loads((path.parent/'input_ids.json').read_text())
            self.assertEqual(bound['input_sha256'], hashlib.sha256((path.parent/'findings.md').read_bytes()).hexdigest())
            self.assertEqual(bound['ids'], ['clio-chat','filevine-chat'])
        for explicit in ([], ['clio-chat','clio-chat'], ['absent'], [None], [' clio-chat ']):
            with self.subTest(explicit=explicit), self.assertRaises(ValueError): input_ids(content, explicit)
        with self.assertRaises(ValueError): input_ids('C1: One\nC2: Two', ['C1'])

    def test_ambiguous_input_fails_before_launch_with_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('research_dispatch.subprocess.Popen', side_effect=AssertionError('launched')):
                with self.assertRaises(ValueError): self.dispatch(root, validation(), 'A finding without an ID.')
            stage = next((root/'dispatch').iterdir())
            metadata=json.loads((stage/'dispatch.json').read_text())
            self.assertEqual(metadata['status'], 'failed')
            self.assertNotIn('process_id',metadata)
            self.assertFalse((stage/'result.json').exists())

    def test_inline_prompt_and_ids_use_the_same_staged_snapshot(self):
        import shutil
        original_copy=shutil.copyfile
        def copy_then_change(source,destination):
            original_copy(source,destination)
            source.write_text('C9: Original input changed after staging.',encoding='utf-8')
        with tempfile.TemporaryDirectory() as directory:
            with patch('research_dispatch.shutil.copyfile',side_effect=copy_then_change):
                path=self.dispatch(Path(directory),validation(('C1','C2')))
            prompt=json.loads(FakeProcess.last_input)['message']['content']
            self.assertIn('## C1 Finding',prompt)
            self.assertNotIn('C9: Original input changed',prompt)
            self.assertEqual(json.loads((path.parent/'input_ids.json').read_text())['ids'],['C1','C2'])

    def test_mailbox_routes_explicit_ids_and_rejects_outside_path(self):
        import argparse
        from contextlib import redirect_stdout
        from io import StringIO
        from research_mailbox import submit, process_one
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); helper = fixtures.DispatchTests(); helper.setup_files(root)
            (root/'findings.md').write_text('| custom-claim | Supported |')
            (root/'ids.json').write_text('["custom-claim"]')
            args = argparse.Namespace(shared_root=root, record=root/'intake.json', brief=root/'brief.md',
                                      input=root/'findings.md', input_ids=root/'ids.json', role='validate',
                                      target='validator', timeout=10, wait=False)
            with redirect_stdout(StringIO()): submit(args)
            request = next((root/'requests').glob('*.json')); job_id = request.stem
            FakeProcess.output = json.dumps({'event':'result','result':{'status':'SUCCESS',
                                              'response':json.dumps(validation(('custom-claim',)))}})
            with patch('research_dispatch.subprocess.Popen', FakeProcess): process_one(root, root/'config.json', request)
            self.assertEqual(json.loads((root/'responses'/f'{job_id}.json').read_text())['status'], 'completed')
            job = {'id':'outside','role':'validate','target':'validator','record':'intake.json','brief':'brief.md',
                   'input':'findings.md','input_ids':'../outside.json','timeout':10, 'expires_at':time.time()+40}
            request = root/'requests'/'outside.json'; request.write_text(json.dumps(job))
            with patch('research_dispatch.subprocess.Popen', side_effect=AssertionError('launched')):
                process_one(root, root/'config.json', request)
            self.assertEqual(json.loads((root/'responses'/'outside.json').read_text())['status'], 'failed')


class ExportRegressions(unittest.TestCase):
    def test_rows_and_headers_keep_context_without_chaining_body(self):
        from docx import Document
        from docx.oxml.ns import qn
        from export_to_word import apply_document_style, load_style, parse_markdown, Renderer
        doc=Document(); style=load_style('corporate'); apply_document_style(doc,style)
        Renderer(doc,style).render(parse_markdown('# Report\n\nTable context.\n\n|Feature|Suite|\n|---|---|\n|Questions|Advanced tier|\n|Summaries|Documented|\n'))
        table=doc.tables[0]
        context = next(p for p in doc.paragraphs if p.text == 'Table context.')
        self.assertTrue(context.paragraph_format.keep_with_next)
        self.assertIsNotNone(table.rows[0]._tr.find('./'+qn('w:trPr')+'/'+qn('w:tblHeader')))
        for row in table.rows:
            self.assertIsNotNone(row._tr.find('./'+qn('w:trPr')+'/'+qn('w:cantSplit')))
        self.assertTrue(all(p.paragraph_format.keep_with_next for c in table.rows[0].cells for p in c.paragraphs))
        self.assertFalse(any(p.paragraph_format.keep_with_next for c in table.rows[1].cells for p in c.paragraphs))
        from io import BytesIO
        saved = BytesIO(); doc.save(saved); saved.seek(0)
        reopened = Document(saved)
        self.assertTrue(next(p for p in reopened.paragraphs if p.text == 'Table context.').paragraph_format.keep_with_next)
        self.assertIsNotNone(reopened.tables[0].rows[0]._tr.find('./'+qn('w:trPr')+'/'+qn('w:tblHeader')))

    def test_oversized_row_can_continue_in_every_style(self):
        from docx import Document
        from docx.oxml.ns import qn
        from export_to_word import apply_document_style, load_style, parse_markdown, Renderer
        text = 'Full content retained. '*500
        for name in ('corporate','academic','minimal'):
            with self.subTest(style=name):
                doc=Document(); style=load_style(name); apply_document_style(doc,style)
                Renderer(doc,style).render(parse_markdown('| ID | Details |\n|---|---|\n| TALL | '+text+' |\n| AFTER | Visible |\n'))
                row=doc.tables[0].rows[1]
                self.assertIsNone(row._tr.find('./'+qn('w:trPr')+'/'+qn('w:cantSplit')))
                self.assertEqual(row.cells[1].text,text.strip())
                self.assertEqual(doc.tables[0].rows[2].cells[1].text,'Visible')
