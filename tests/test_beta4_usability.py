"""Beta.4 prevents inaccessible comparison and misleading geometry controls."""
import unittest
from pathlib import Path
from satvv.web_server import WEB_DIR

class Beta4Tests(unittest.TestCase):
 def test_compare_link_targets_visible_anchor(self):
  html=(WEB_DIR/'challenge.html').read_text()
  self.assertIn('href="/#compare-workspace"',html)
  self.assertIn('id="compare-workspace"',html)
  self.assertIn('id="compareNow"',html)
  self.assertIn('id="compareActivity"',html)
  self.assertNotIn('id="comparisonPanel" hidden',html)
 def test_compare_directly_from_current_settings(self):
  js=(WEB_DIR/'challenge.js').read_text()
  a=js.index('async function compare(){')
  body=js[a:js.index('function renderComparisonChart(',a)]
  self.assertIn('const s=settings()',body)
  self.assertIn('await post({...s,policy})',body)
  self.assertNotIn('if(!current)return',body)
  self.assertIn('for(let i=0;i<all.length;i++)',body)
  self.assertIn("$('compareNow').onclick=compare",js)
 def test_two_bundled_models_and_user_file(self):
  html=(WEB_DIR/'challenge.html').read_text()
  scene=(WEB_DIR/'mission_beta.js').read_text()
  self.assertIn('value="conceptual"',html)
  self.assertIn('value="cubesat"',html)
  self.assertIn('Compact 6U CubeSat',html)
  self.assertNotIn('value="nasa"',html)
  for snippet in ('function buildCubeSat()','renderModel(buildCubeSat())','renderModel(buildConceptual())','anchorProfile(\'cubesat\')','loadCustom(', 'DRACOLoader'):
   self.assertIn(snippet,scene)
 def test_stars_behind_craft(self):
  js=(WEB_DIR/'mission_beta.js').read_text()
  css=(WEB_DIR/'style.css').read_text()
  self.assertIn('scene.background=null',js)
  self.assertIn('.mission-view-wrap::before',css)
  self.assertIn('z-index:0',css)
  self.assertIn('.mission-view-wrap>.mission-webgl{z-index:2}',css)
  self.assertNotIn('scene.add(new THREE.Points(stars',js)
 def test_all_active_research_navigation_updated(self):
  for name in ('challenge.html','how-it-works.html','industry.html','reference.html'):
   html=(WEB_DIR/name).read_text()
   self.assertIn('href="/#compare-workspace"',html)
   self.assertNotIn('href="/#comparisonPanel"',html)
 def test_api_version(self):
  from inspect import getsource
  from satvv.web_server import PreviewHandler
  self.assertIn('1.0.0',getsource(PreviewHandler.do_GET))

if __name__=='__main__':unittest.main()
