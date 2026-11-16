import os, tempfile, pathlib, unittest
from unittest.mock import patch
import chaos_actions as c

class GateTest(unittest.TestCase):
    def evaluate(self, fault, before, after, recovered=True):
        steady=dict(p95_ms=100,local_error=0,complete=1,requests=100)
        values={'steady':steady,'round0':steady|before,'round1':steady|after}
        with tempfile.TemporaryDirectory() as folder, patch.object(c,'OUT',pathlib.Path(folder)), patch.object(c,'rollback',return_value=recovered), patch.object(c,'run_load',side_effect=lambda name,*a:values[name]), patch.object(c.subprocess,'run'), patch.dict(os.environ,{'CHAOS_WINDOW_ACK':'yes','CHAOS_TOKEN':'t'*40,'EXPERIMENT':'test'}):
            return c.run_suite(fault)
    def test_latency_improves(self):
        self.assertTrue(self.evaluate('latency',{'p95_ms':3000},{'p95_ms':800}))
    def test_gate_rejects_no_refutation(self):
        self.assertFalse(self.evaluate('latency',{'p95_ms':100},{'p95_ms':100}))
    def test_gate_rejects_failed_improvement(self):
        self.assertFalse(self.evaluate('unavailable',{'local_error':1},{'local_error':.05}))
    def test_one_percent_boundary_is_allowed(self):
        self.assertTrue(self.evaluate('unavailable',{'local_error':1},{'local_error':.01}))
    def test_recovery_is_mandatory(self):
        self.assertFalse(self.evaluate('latency',{'p95_ms':3000},{'p95_ms':800},False))
