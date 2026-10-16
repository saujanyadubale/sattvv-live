"""Prevent warning-only events from being drawn as long amber duration bars."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'web' / 'challenge.js'


class WarningChartVisualTests(unittest.TestCase):
    def test_warning_markers_are_points_not_intervals(self):
        source = SCRIPT.read_text()
        start = source.index('function renderComparisonChart(')
        end = source.index('function truth(){', start)
        fn = source[start:end]
        self.assertIn('ctx.arc(x, cy, 5, 0, 2 * Math.PI)', fn)
        self.assertNotIn('ctx.fillRect(x0,y+5', fn)
        self.assertIn('WARN · ', fn)
        self.assertIn('FAIL · ', fn)
        self.assertIn('No event', fn)

        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable; Python static checks completed')

        harness = '''
          const operations = [];
          const ctx = {
            fillStyle: '', strokeStyle: '', lineWidth: 1, font: '', textAlign: 'left', textBaseline: 'alphabetic',
            scale(...args){ operations.push(['scale',...args]); },
            clearRect(){},
            fillRect(...args){ operations.push(['rect',this.fillStyle,...args]); },
            beginPath(){}, moveTo(){}, lineTo(){}, stroke(){operations.push(['stroke',this.strokeStyle]);},
            arc(...args){operations.push(['arc',...args]);}, fill(){},
            fillText(...args){operations.push(['text',this.fillStyle,...args]);},
            measureText(s){return {width:s.length*6.15};}
          };
          const canvas = { clientWidth: 910, getContext(){return ctx;} };
          const $=()=>canvas;
          const window={devicePixelRatio: 2};
        '''
        sample = '''
          renderComparisonChart([
            {policy:'Fixed-order',detected:false,seconds:null,firstWarning:null},
            {policy:'Temporal adaptive',detected:false,seconds:null,firstWarning:4608},
            {policy:'Information gain',detected:true,seconds:3420,firstWarning:null},
          ],90);
          console.log(JSON.stringify(operations));
        '''
        proc = subprocess.run([node, '-e', harness + fn + sample], capture_output=True, text=True, timeout=5)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ops = json.loads(proc.stdout)
        self.assertTrue(any(x[0]=='arc' for x in ops), 'warning marker must be a drawn circular point')
        self.assertTrue(any(x[0]=='text' and x[2].startswith('WARN') for x in ops))
        self.assertTrue(any(x[0]=='text' and x[2].startswith('FAIL') for x in ops))
        self.assertTrue(any(x[0]=='text' and x[2]=='No event' for x in ops))
        self.assertFalse(any(x[0]=='rect' and x[1]=='#f0b767' for x in ops), 'amber bar must not be filled')
        self.assertTrue(any(x[0]=='rect' and x[1]=='#6ae3bd' for x in ops), 'verified failure uses mint bar')

    def test_chart_has_accessible_explanation(self):
        html = (ROOT / 'web' / 'challenge.html').read_text()
        self.assertIn('role="img" aria-label="Verification strategies:', html)
        self.assertIn('amber dots mark the first early-warning time', html)


if __name__ == '__main__':
    unittest.main()
