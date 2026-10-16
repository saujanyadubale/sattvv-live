import json
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
PAGES=ROOT/'github-pages'/'satvv'
class PortfolioEditionTests(unittest.TestCase):
    def test_expanded_method_details_have_inset(self):
        css=(WEB/'style.css').read_text()
        self.assertIn('.model-guide-list>article details>p',css)
        self.assertIn('padding:12px 18px 18px',css)
    def test_portfolio_theme_matches_source_tokens(self):
        css=(PAGES/'site.css').read_text()
        for token in ('#080d17','#f5f3ef','#b5ecdf','#ccf4b5','Space Grotesk','DM Sans'):
            self.assertIn(token,css)
    def test_static_assets_and_archived_data(self):
        for asset in ('index.html','site.css','app.js','scene-background.svg','mission3d.js','campaigns.json'):
            self.assertTrue((PAGES/asset).exists(),asset)
        obj=json.loads((PAGES/'campaigns.json').read_text())
        self.assertEqual({x['key'] for x in obj},{'battery','healthy','wheel','planner_v102','weak_seed7'})
        self.assertTrue(all(x['evidence'] and x['observations'] for x in obj))
        self.assertTrue(all(x['source'].startswith(('v0.','v1.')) for x in obj))
        wheel=next(x for x in obj if x['key']=='wheel')
        self.assertTrue(wheel['detected'])
        self.assertEqual(wheel['evidence'][-1]['test_id'],'T17')
        self.assertTrue(any(e['decision'].get('coverage_guard')!='adaptive_score' for e in wheel['evidence']))
        planner=next(x for x in obj if x['key']=='planner_v102')
        self.assertTrue(planner['detected'])
        self.assertEqual(planner['meta']['software_release'],'1.0.2')
        self.assertTrue(any(e['decision'].get('planned_sequence') for e in planner['evidence']))
        weak=next(x for x in obj if x['key']=='weak_seed7')
        self.assertFalse(weak['detected'])
        self.assertTrue(weak['weak_fault_analysis']['warning_events'])
        self.assertEqual(weak['meta']['software_release'],'1.0.3')
    def test_no_fake_python_backend_in_static_showcase(self):
        src=(PAGES/'app.js').read_text()
        self.assertNotIn('/api/unified',src)
        self.assertIn("fetch('./campaigns.json')",src)
        self.assertIn('Archived', (PAGES/'index.html').read_text()+' '+(PAGES/'README_STATIC.md').read_text())
