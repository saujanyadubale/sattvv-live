"""Visual release contracts; no scientific model parameters changed."""
import unittest
from satvv.web_server import WEB_DIR

class BetaOnePresentationTests(unittest.TestCase):
    def test_true_directed_svg_workflow(self):
        html=(WEB_DIR/'how-it-works.html').read_text()
        self.assertIn('<svg class="architecture-svg"',html)
        self.assertIn('marker-end="url(#arr-',html)
        self.assertIn('OFFLINE LEARNING',html)
        self.assertIn('Feedback loop',html)
        self.assertEqual(html.count('data-architecture='),10)
        self.assertGreaterEqual(html.count('<path class="arch-edge'),12)
        self.assertNotIn('M748 533 V125 H640',html)  # removed overlapping calibration arrow
    def test_labels_have_clean_default_and_accessible_alternatives(self):
        html=(WEB_DIR/'challenge.html').read_text()
        for field in ('missionLabelMode','Clean · active only','Annotated · show all','Hidden'):
            self.assertIn(field,html)
        self.assertIn('<option value="focus" selected>',html)
        js=(WEB_DIR/'mission_beta.js').read_text()
        self.assertIn("labelMode='focus'",js)
        self.assertIn("labelMode==='none'",js)
        self.assertIn("labelMode==='focus'",js)
        self.assertIn("labelMode==='focus'",(WEB_DIR/'mission3d.js').read_text())
    def test_detailed_parabolic_antenna_local_model(self):
        code=(WEB_DIR/'mission_beta.js').read_text()
        for snippet in ('LatheGeometry','TorusGeometry','Ground station parabolic reflector','const R=1.13','g.position.set(7.25','mount.quaternion','feed'):
            self.assertIn(snippet,code)
        # GLB loading preserved, no claim that an external dish binary is bundled.
        self.assertIn('GLTFLoader',code)
        self.assertIn('renderModel(buildConceptual())',code)
    def test_stage_supports_keyboard(self):
        js=(WEB_DIR/'workflow_beta.js').read_text()
        self.assertIn('keydown',js)
        self.assertIn("e.key==='Enter'",js)
        self.assertIn("e.key===' '",js)
    def test_beta1_health_version_and_docs(self):
        from inspect import getsource
        from satvv.web_server import PreviewHandler
        self.assertIn('1.0.0',getsource(PreviewHandler.do_GET))
        self.assertTrue((WEB_DIR.parent/'docs/v1.0-beta.1_release_notes.md').is_file())

if __name__=='__main__':unittest.main()
