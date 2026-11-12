import math
import unittest

from msp430sim import board_g2et as B
from msp430sim.board3d import (DIP_MAP, J1_MAP, J2_MAP, LEDS, Camera, Scene, led_levels, pin_class,
                               pin_states)
from tests.test_sim import run

GPIO = {(p, b) for p in ('P1', 'P2') for b in range(8)}


class BoardData(unittest.TestCase):
    """TI tasarim dosyalarindan uretilen geometrinin tutarliligi."""

    def test_outline_size(self):
        xs = [p[0] for p in B.OUTLINE]
        ys = [p[1] for p in B.OUTLINE]
        self.assertAlmostEqual(max(xs) - min(xs), 58.42, places=2)       # 2.3"
        self.assertAlmostEqual(max(ys) - min(ys), 78.74, places=2)       # 3.1"

    def test_parts_on_board_and_dnp_removed(self):
        refs = {p[0] for p in B.PARTS}
        for ref, _, x, y, _, _, _ in B.PARTS:
            self.assertTrue(-1 <= x <= B.W + 1 and -1 <= y <= B.H + 1, ref)
        for ref in ('XU1', 'J1', 'J2', 'J101', 'S1', 'S2', 'D1', 'D2', 'D3', 'J102', 'U100'):
            self.assertIn(ref, refs)
        self.assertFalse(refs & set(B.DNP))

    def test_boosterpack_header_spacing(self):
        P = {p[0]: p for p in B.PARTS}
        self.assertAlmostEqual(P['J2'][2] - P['J1'][2], 45.72, places=2)   # 1.8" LaunchPad standardi
        self.assertAlmostEqual(P['XU1'][3], P['J1'][3], places=2)          # soket headerlarla hizali

    def test_led_mapping_matches_schematic(self):
        self.assertEqual(LEDS['D1'][:2], ('green', ('P1', 0)))
        self.assertEqual(LEDS['D2'][:2], ('red', ('P1', 6)))
        self.assertEqual(LEDS['D3'][1], (('P2', 1), ('P2', 3), ('P2', 5)))


class PinMaps(unittest.TestCase):
    def test_headers_cover_all_gpio_once(self):
        sig = [s for s in list(J1_MAP.values()) + list(J2_MAP.values()) if isinstance(s, tuple)]
        self.assertEqual(len(sig), 16)
        self.assertEqual(set(sig), GPIO)
        self.assertEqual(sorted(J1_MAP), list(range(1, 11)))
        self.assertEqual(sorted(J2_MAP), list(range(11, 21)))

    def test_dip_pinout(self):
        sig = [s for s in DIP_MAP.values() if isinstance(s, tuple)]
        self.assertEqual(set(sig), GPIO)
        self.assertEqual(len(sig), 16)
        self.assertEqual((DIP_MAP[1], DIP_MAP[20], DIP_MAP[2], DIP_MAP[14]), ('DVCC', 'DVSS', ('P1', 0), ('P1', 6)))


class SceneGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = Scene()

    def test_faces_reference_valid_vertices_and_unit_normals(self):
        n = len(self.scene.V)
        for g in self.scene.groups:
            for b in g.boxes:
                for idx, nrm, *_ in b.faces:
                    self.assertTrue(all(0 <= i < n for i in idx))
                    self.assertAlmostEqual(math.sqrt(sum(c * c for c in nrm)), 1.0, places=6)

    def test_box_normals_point_outwards(self):
        for g in self.scene.groups:
            for b in g.boxes:
                cx, cy, cz = b.center
                for idx, nrm, d, *_ in b.faces:
                    self.assertLess(nrm[0] * cx + nrm[1] * cy + nrm[2] * cz - d, 1e-9, g.name)

    def test_dynamic_roles_present(self):
        roles = {f[6] for g in self.scene.groups for b in g.boxes for f in b.faces if f[6]}
        for ref in LEDS:
            self.assertIn(('lens', ref), roles)
        for num in range(1, 21):
            self.assertIn(('pin', ('XU1', num)), roles)
        self.assertIn(('pin', ('J1', 2)), roles)
        self.assertIn(('shunt', 'TXD'), roles)
        self.assertIn(('shunt', 'RXD'), roles)

    def test_buttons_have_pressed_variants(self):
        for ref in ('S1', 'S2'):
            g = next(g for g in self.scene.groups if g.name == ref)
            self.assertEqual({b.only[1] for b in g.boxes if b.only}, {False, True})


class CameraMath(unittest.TestCase):
    def test_target_projects_to_center(self):
        cam = Camera()
        xs, ys, zs = cam.project([tuple(cam.target)])
        self.assertAlmostEqual(xs[0], cam.w / 2, places=6)
        self.assertAlmostEqual(ys[0], cam.h / 2, places=6)
        self.assertAlmostEqual(zs[0], cam.dist, places=6)

    def test_top_view_orientation(self):
        cam = Camera()
        cam.preset('top')
        t = cam.target
        xs, ys, _ = cam.project([tuple(t), (t[0] + 10, t[1], 0), (t[0], t[1] + 10, 0)])
        self.assertGreater(xs[1], xs[0] + 1)          # +x sagda
        self.assertLess(ys[2], ys[0] - 1)             # +y (USB kenari) yukarida

    def test_pan_keeps_projection_consistent(self):
        cam = Camera()
        cam.pan(40, 0)
        xs, _, _ = cam.project([(B.W / 2, B.H / 2, 0.0)])
        self.assertAlmostEqual(xs[0], cam.w / 2 + 40, delta=1.0)


class SimulatorState(unittest.TestCase):
    def test_led_and_pin_state_from_program(self):
        cpu, _ = run('    bis.b #BIT0|BIT1, &P1DIR\n    bis.b #BIT0, &P1OUT\n'
                     '    bis.b #BIT1|BIT5, &P2DIR\n    bis.b #BIT5, &P2OUT\n')
        pins = pin_states(cpu)
        self.assertEqual(pin_class(pins[('P1', 0)]), 'out1')
        self.assertEqual(pin_class(pins[('P1', 1)]), 'out0')
        self.assertEqual(pin_class(pins[('P1', 3)]), 'in1')        # S1 harici pull-up
        lv = led_levels(pins)
        self.assertEqual((lv['D1'], lv['D2']), (1.0, 0.0))
        self.assertEqual(lv['D3'], (0.0, 0.0, 1.0))
        cpu.p1.set_input(3, 0)                                       # S1 basili
        self.assertEqual(pin_class(pin_states(cpu)[('P1', 3)]), 'in0')


class WindowSmoke(unittest.TestCase):
    def test_render_and_update(self):
        try:
            import tkinter as tk
            root = tk.Tk()
        except Exception as e:                      # ekran / Tk yok
            self.skipTest(f'Tk yok: {e}')
        try:
            from msp430sim.board3d import Board3D
            from msp430sim.cpu import MSP430
            root.withdraw()
            root.cpu, root.running = MSP430(), False
            root.refresh = root.do_reset = root.do_run = lambda: None
            b = Board3D(root)
            root.update()
            b.render(hq=True)
            items = len(b.cv.find_all())
            self.assertGreater(items, 1000)
            root.cpu.p1.rg[2] = root.cpu.p1.rg[1] = 1        # P1.0 cikis 1 -> D1 yanar
            b.update_state()
            lens = b.dyn[('lens', 'D1')][0][0]
            self.assertNotEqual(b.cv.itemcget(lens, 'fill'), '')
            spill = b.dyn[('spill', 'D1')][0][0]
            self.assertEqual(b.cv.itemcget(spill, 'state'), 'normal')
            b.flash('TXD')

            def visible():
                return sum(1 for i in b.cv.find_all() if b.cv.itemcget(i, 'state') != 'hidden')
            b.render(hq=False)
            n_drag = visible()
            b.render(hq=True)
            n_full = visible()
            self.assertLess(n_drag, n_full * 0.6)       # surukleme karesi belirgin sekilde hafif
            b.close()
        finally:
            root.destroy()


class TickBudget(unittest.TestCase):
    def test_busy_loop_does_not_block_ui(self):
        """Gercek zamana yetisemeyen program (mesgul dongu) bir tick'te butceden fazla calismamali."""
        import time
        try:
            import msp430sim.gui as G
            app = G.App(initial_file=None)
        except Exception as e:
            self.skipTest(f'Tk yok: {e}')
        try:
            app.withdraw()
            app.set_text(open('msp430sim/examples/blink.asm').read())
            self.assertTrue(app.do_assemble())
            app.running = True
            app.last = time.perf_counter() - 0.1            # 100 ms birikmis is (eskiden ~130 ms bloklardi)
            t = time.perf_counter()
            app.tick()
            self.assertLess(time.perf_counter() - t, G.TICK_BUDGET + 0.03)
            self.assertTrue(app.running)
        finally:
            app.running = False
            app.dirty = False
            app.destroy()


if __name__ == '__main__':
    unittest.main()
