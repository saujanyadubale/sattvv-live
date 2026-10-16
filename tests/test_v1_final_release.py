"""V1 presentation/contract checks: no simulation-algorithm changes."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from satvv.web_server import WEB_DIR

class FinalReleaseChecks(unittest.TestCase):
    def test_six_technical_icons_not_emoji(self):
        s=(WEB_DIR/'how-it-works.html').read_text()
        self.assertEqual(s.count('class="decision-icon"'),6)
        for name in ('Detect','Predict','Diagnose','Verify','Audit','Boundary'):
            self.assertIn(f'aria-label="{name} icon"',s)
            self.assertIn(f'<span>{name}</span></h3>',s)
    def test_select_padding_and_native_chevron(self):
        s=(WEB_DIR/'style.css').read_text()
        self.assertIn('padding:10px 38px 10px 14px',s)
        self.assertIn('min-height:43px',s)
        self.assertIn('appearance:none',s)
        self.assertIn('background-color:#0b2031!important',s)
    def test_static_stars_are_pure_background(self):
        root=ET.parse(WEB_DIR/'scene-background.svg').getroot()
        stars=root.findall('{http://www.w3.org/2000/svg}circle')
        self.assertGreaterEqual(len(stars),100)
        css=(WEB_DIR/'style.css').read_text()
        self.assertIn("url('/scene-background.svg')",css)
        js=(WEB_DIR/'mission3d.js').read_text()
        self.assertIn('g.clearRect(0,0,w,h)',js)
        self.assertNotIn("g.fillRect(0,0,w,h)",js)
        self.assertIn('scene.background=null',(WEB_DIR/'mission_beta.js').read_text())
    def test_primary_pages_are_final(self):
        for f in ('challenge.html','reference.html','industry.html','how-it-works.html'):
            s=(WEB_DIR/f).read_text()
            self.assertIn('v1.0.3 ·',s)
            self.assertNotIn('v1.0 beta.4',s)
            self.assertIn('href="/#compare-workspace"',s)
        self.assertTrue((WEB_DIR.parent/'docs'/'V1_PUBLIC_RELEASE_CHECKLIST.md').is_file())
    def test_new_resource_route_exists(self):
        from inspect import getsource
        from satvv.web_server import PreviewHandler
        s=getsource(PreviewHandler.do_GET)
        self.assertIn("'/scene-background.svg'",s)
        self.assertIn('image/svg+xml',s)
        self.assertIn('1.0.0',s)

if __name__=='__main__':unittest.main()
