import copy,csv,json,math,os,re,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from prediction_cli.frontend import Frontend
from prediction_cli.protocol import decode,demo_snapshot,empty_snapshot,validate_snapshot,validate_event
from prediction_cli.tui import render

class ProtocolTests(unittest.TestCase):
 def test_empty_is_disconnected(self):self.assertEqual(empty_snapshot()['status'],'disconnected')
 def test_demo_is_labeled_without_invented_results(self):
  s=demo_snapshot();self.assertEqual(s['mode'],'synthetic');self.assertIsNone(s['metrics']['accuracy']);self.assertIsNone(s['metrics']['forecast_score'])
 def test_valid_snapshot(self):self.assertEqual(validate_snapshot(demo_snapshot())['schema'],'prediction-cli-snapshot-v1')
 def test_unknown_fields_rejected(self):
  for k in ('profit','bankroll','argv','token','scheduler'):
   s=demo_snapshot();s[k]=1
   with self.assertRaises(ValueError):validate_snapshot(s)
 def test_nonfinite_and_boolean_metrics_rejected(self):
  for v in (float('nan'),float('inf'),True,10**400,-1,2):
   s=demo_snapshot();s['metrics']['accuracy']=v
   with self.assertRaises(ValueError):validate_snapshot(s)
 def test_duplicate_json_keys_rejected(self):
  with self.assertRaises(ValueError):decode('{"a":1,"a":2}')
 def test_json_nan_rejected(self):
  with self.assertRaises(ValueError):decode('{"a":NaN}')
 def test_escape_sequence_rejected(self):
  s=demo_snapshot();s['events'][0]['summary']='danger\x1b[2J'
  with self.assertRaises(ValueError):validate_snapshot(s)
 def test_event_duplicate_ids_rejected(self):
  s=demo_snapshot();s['events'][1]['id']=s['events'][0]['id']
  with self.assertRaises(ValueError):validate_snapshot(s)
 def test_forecast_requires_probability_and_direction(self):
  e=demo_snapshot()['events'][0];e['type']='forecast'
  with self.assertRaises(ValueError):validate_event(e)
  e.update(p_up=.6,decision='up');self.assertEqual(validate_event(e)['decision'],'up')
 def test_outcome_requires_outcome(self):
  e=demo_snapshot()['events'][0];e['type']='outcome'
  with self.assertRaises(ValueError):validate_event(e)
 def test_wrong_market_and_horizon_rejected(self):
  for k,v in [('symbol','OTHER'),('horizon_seconds',60)]:
   s=demo_snapshot();s[k]=v
   with self.assertRaises(ValueError):validate_snapshot(s)
 def test_limits_and_invalid_model_rejected(self):
  for k,v in [('events',[demo_snapshot()['events'][0]]*201),('model','bad model'),('as_of',True)]:
   s=demo_snapshot();s[k]=v
   with self.assertRaises(ValueError):validate_snapshot(s)

class FrontendTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.d=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def test_snapshot_refresh_and_invalid_retains_view(self):
  p=self.d/'snapshot.json';p.write_text(json.dumps(demo_snapshot()));f=Frontend(snapshot_path=p);self.assertEqual(f.refresh()['mode'],'synthetic');p.write_text('{bad');self.assertEqual(f.refresh()['mode'],'synthetic');self.assertTrue(f.error)
 def test_unreadable_disconnected_error(self):
  f=Frontend(snapshot_path=self.d/'missing');self.assertEqual(f.refresh()['status'],'disconnected');self.assertTrue(f.error)
 def test_requests_disabled_by_default(self):
  f=Frontend()
  with self.assertRaises(ValueError):f.request('start')
  self.assertEqual(f.snapshot['status'],'disconnected')
 def test_requests_are_messages_not_state_changes(self):
  p=self.d/'requests.jsonl';f=Frontend(requests_path=p);a=f.request('start');b=f.request('stop');self.assertNotEqual(a['request_id'],b['request_id']);self.assertEqual(f.snapshot['status'],'disconnected');self.assertEqual(len(p.read_text().splitlines()),2)
 def test_request_rejects_execution_commands(self):
  with self.assertRaises(ValueError):Frontend(requests_path=self.d/'r').request('exec')
 def test_jsonl_stream(self):
  p=self.d/'events.jsonl';e=demo_snapshot()['events'][1];e.update(schema='prediction-cli-event-v1',status='idle');p.write_text(json.dumps(e)+'\n');f=Frontend(events_path=p);self.assertEqual(f.refresh()['status'],'idle')
 def test_stream_snapshot_mutually_exclusive(self):
  with self.assertRaises(ValueError):Frontend(snapshot_path='a',events_path='b')
 def test_demo_external_cannot_mix(self):
  with self.assertRaises(ValueError):Frontend(snapshot_path='a',demo=True)
 def test_exports_no_overwrite_and_no_paths(self):
  f=Frontend(demo=True);p=self.d/'out.json';f.export(p,'json');self.assertNotIn(str(self.d),p.read_text())
  with self.assertRaises(FileExistsError):f.export(p,'json')
 def test_csv_formula_injection(self):
  f=Frontend(demo=True);f.snapshot['events'][0]['summary']='=HYPERLINK("evil")';p=self.d/'out.csv';f.export(p)
  with p.open(encoding='utf-8-sig') as x:rows=list(csv.DictReader(x))
  self.assertTrue(rows[0]['summary'].startswith("'="))
 def test_prompt_and_hidden_details(self):
  out=render(empty_snapshot(),100,32,input_text='/help');plain=re.sub(r'\x1b\[[0-9;?]*[A-Za-z]','',out);self.assertIn('| > /help',plain);self.assertIn('/start  request',plain);self.assertNotIn('Backend-reported forecast details',plain);self.assertLessEqual(len(plain.splitlines()),31)
 def test_small_terminal(self):self.assertIn('Expand terminal',render(empty_snapshot(),40,12))
 def test_cli_headless_demo_and_disabled_start(self):
  for args,expected in [(['--demo','status','--json'],0),(['status'],0),(['start'],2),(['--help'],0)]:
   r=subprocess.run([sys.executable,'-m','prediction_cli',*args],capture_output=True,text=True);self.assertEqual(r.returncode,expected,r.stderr)

if __name__=='__main__':unittest.main()
