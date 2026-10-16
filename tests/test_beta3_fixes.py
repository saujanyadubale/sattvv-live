"""Beta.3 requirements on UI usability and research transparency."""
import unittest
from satvv.web_server import WEB_DIR

class Beta3Tests(unittest.TestCase):
 def test_layout_restoration_control_stays_visible(self):
  html=(WEB_DIR/'challenge.html').read_text()
  js=(WEB_DIR/'challenge.js').read_text()
  css=(WEB_DIR/'style.css').read_text()
  self.assertIn('id="missionLayout"',html)
  self.assertIn("$('missionPanel').classList.toggle('mission-data-view',layout==='data')",js)
  self.assertIn('#missionPanel.mission-data-view .mission-view-wrap',css)
  self.assertNotIn("$('missionPanel').classList.toggle('mission-hide-visual',layout==='data')",js)
  self.assertIn('mission-telemetry-notice',html)
 def test_icons_are_inline_svgs(self):
  js=(WEB_DIR/'challenge.js').read_text()
  self.assertIn('symbol.innerHTML',js)
  self.assertIn('viewBox',js)
  self.assertNotIn("EPS:'⚡'",js)
 def test_five_page_navigation(self):
  for name in ('challenge.html','how-it-works.html','industry.html','reference.html'):
   page=(WEB_DIR/name).read_text()
   for path in ('/how-it-works','/industry','/reference'):
    self.assertIn('href="'+path+'"',page)
   self.assertNotIn('href="/classic#research"',page)
 def test_fresh_reference_uses_live_catalog(self):
  html=(WEB_DIR/'reference.html').read_text()
  js=(WEB_DIR/'reference.js').read_text()
  self.assertIn('id="ref-body"',html)
  self.assertIn("fetch('/api/reference')",js)
  self.assertIn('Manual spacecraft scenarios',html)
  self.assertIn('Random or compound challenges',html)
 def test_research_comparison_is_not_external_score_claim(self):
  html=(WEB_DIR/'industry.html').read_text()
  self.assertIn('id="method-comparison"',html)
  self.assertIn('id="benchmark-comparison"',html)
  self.assertIn('not</strong> tests run on NASA/ESA',html)
  self.assertIn('18 synthetic faulty campaigns',html)
  js=(WEB_DIR/'benchmark_view.js').read_text()
  self.assertIn('83.3',js)
  self.assertIn('22.2',js)
 def test_glb_loader_reports_failure_and_does_not_silently_substitute(self):
  js=(WEB_DIR/'mission_beta.js').read_text()
  html=(WEB_DIR/'challenge.html').read_text()
  self.assertIn('Current model retained',js)
  self.assertIn('return false',js)
  self.assertIn('Custom GLB · loaded locally',html)
  self.assertIn('30 MB',html)
  self.assertIn('subsystem',html)
 def test_offline_arrow_no_overlap(self):
  html=(WEB_DIR/'how-it-works.html').read_text()
  self.assertNotIn('M748 533 V125 H640',html)
  self.assertNotIn('M986 677 H748 V533',html)
  self.assertIn('loaded before each run',html)
if __name__=='__main__':unittest.main()
