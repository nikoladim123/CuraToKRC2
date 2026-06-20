from UM.OutputDevice.OutputDevice import OutputDevice
from UM.Application import Application
from UM.Logger import Logger
from PyQt6.QtWidgets import QFileDialog
import os
import json
import math

class KRLWriter(OutputDevice):
    def __init__(self):
        super().__init__("krl_writer")
        self.setName("Export KRL")
        self.setShortDescription("KRL")
        self.setDescription("Export as KUKA KRL .src")
        self.setPriority(1)

        # Ucitaj konfiguraciju iz JSON fajla
        self._config = self._load_config()

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "krl_config.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            Logger.log("e", "KRLWriter: Ne mogu ucitati krl_config.json: %s", str(e))
            # Defaultne vrijednosti ako JSON ne postoji
            return {
                "flow_at_1v_g_per_sec": 0.065,
                "max_volt": 6.0,
                "material_density_g_cm3": 1.27,
                "extrude_wait_sec": 0.2,
                "tool_orientation": {"A": -178.635, "B": -0.000, "C": -180.000},
                "home_position": [0.0, -90.0, 90.0, 0.0, 0.0, 0.0],
                "approach_position": [1.62725, -51.99397, 108.41167, -178.04696, 56.43304, 178.91985],
                "tool_number": 1,
                "base_number": 1,
                "vel_cp_default": 0.2,
                "chunk_size": 25000
            }

    def requestWrite(self, nodes, file_name=None, limit_mimetypes=None, file_handler=None, **kwargs):
        scene = Application.getInstance().getController().getScene()
        gcode_dict = getattr(scene, "gcode_dict", None)
        if not gcode_dict:
            Logger.log("e", "KRLWriter: Nema G-code. Slicaj prvo.")
            return

        active_plate = Application.getInstance().getMultiBuildPlateModel().activeBuildPlate
        gcode_list = gcode_dict.get(active_plate, None)
        if not gcode_list:
            Logger.log("e", "KRLWriter: Nema G-code za aktivnu ploCu.")
            return

        gcode = "\n".join(gcode_list)

        path, _ = QFileDialog.getSaveFileName(
            None, "Save KRL File",
            os.path.expanduser("~") + "/print.src",
            "KUKA KRL (*.src)"
        )
        if not path:
            return

        program_name = os.path.splitext(os.path.basename(path))[0]
        moves = self._parse_gcode(gcode)
        self._split_and_write(moves, path, program_name)
        Logger.log("i", "KRLWriter: Saved to %s", path)

    def _split_and_write(self, moves, path, program_name):
        base_dir = os.path.dirname(path)
        chunk_size = self._config.get("chunk_size", 25000)

        all_lines = self._generate_moves(moves).splitlines()

        chunks = [all_lines[i:i+chunk_size] for i in range(0, len(all_lines), chunk_size)]

        sub_names = []
        for idx, chunk in enumerate(chunks):
            sub_name = program_name if idx == 0 else program_name + str(idx)
            sub_names.append(sub_name)

            sub_path = os.path.join(base_dir, sub_name + ".src")
            with open(sub_path, "w") as f:
                f.write(self._generate_subheader(sub_name))
                f.write("\n".join(chunk) + "\n")
                f.write("END\n")

        main_name = program_name + "Main"
        main_path = os.path.join(base_dir, main_name + ".src")
        with open(main_path, "w") as f:
            f.write(self._generate_main(main_name, sub_names))

    def _generate_main(self, main_name, sub_names):
        cfg = self._config
        tool = cfg.get("tool_number", 1)
        base = cfg.get("base_number", 1)
        vel = cfg.get("vel_cp_default", 0.2)
        home = cfg.get("home_position", [0.0, -90.0, 90.0, 0.0, 0.0, 0.0])
        approach = cfg.get("approach_position", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        lines = []
        lines.append("&ACCESS RVP")
        lines.append("&REL 1")
        lines.append("&PARAM TEMPLATE = C:\\KRC\\Roboter\\Template\\vorgabe")
        lines.append("&PARAM EDITMASK = *")
        lines.append("DEF " + main_name + " ( )")
        lines.append("")
        lines.append("; External program calls:")
        for sub in sub_names:
            lines.append("EXT " + sub + "()")
        lines.append("")
        lines.append("EXT BAS (BAS_COMMAND :IN,REAL :IN )")
        lines.append("")
        lines.append("GLOBAL INTERRUPT DECL 3 WHEN $STOPMESS==TRUE DO IR_STOPM ( )")
        lines.append("INTERRUPT ON 3")
        lines.append("")
        lines.append("BAS (#INITMOV,0)")
        lines.append("BAS (#VEL_PTP,100)")
        lines.append("BAS (#ACC_PTP,20)")
        lines.append("BAS (#TOOL,{})".format(tool))
        lines.append("BAS (#BASE,{})".format(base))
        lines.append("")
        lines.append("$ADVANCE = 5")
        lines.append("$ACC.CP = 10.0")
        lines.append("$APO.CPTP = 5")
        lines.append("$APO.CDIS = 5")
        lines.append("")
        lines.append("; Generated by KRL Writer Cura Plugin")
        lines.append("; Author: Nikola Dimitrijevic - DIATEH doo, Croatia")
        lines.append("; github.com/nikola-diateh/CuraKRLWriter")
        lines.append("")
        lines.append("PTP {{A1 {:.3f}, A2 {:.3f}, A3 {:.3f}, A4 {:.3f}, A5 {:.3f}, A6 {:.3f}, E1 0, E2 0, E3 0, E4 0, E5 0, E6 0}}".format(*home))
        lines.append("")
        lines.append("PTP {{A1 {:.5f}, A2 {:.5f}, A3 {:.5f}, A4 {:.5f}, A5 {:.5f}, A6 {:.5f}}} C_PTP".format(*approach))
        lines.append("")
        lines.append("$VEL.CP = {:.3f}".format(vel))
        lines.append("")
        for sub in sub_names:
            lines.append(sub + " ( )")
        lines.append("")
        lines.append("END")
        return "\n".join(lines) + "\n"

    def _generate_subheader(self, program_name):
        return (
            "&ACCESS RVP\n"
            "&REL 1\n"
            "&PARAM TEMPLATE = C:\\KRC\\Roboter\\Template\\vorgabe\n"
            "&PARAM EDITMASK = *\n"
            "DEF " + program_name + " ( )\n"
            "\n"
        )

    def _parse_gcode(self, gcode):
        import re
        moves = []
        current_x, current_y, current_z = 0.0, 0.0, 0.0
        current_f = 1000.0

        for line in gcode.splitlines():
            line = line.split(";")[0].strip()
            if not line:
                continue
            if not (line.startswith("G0") or line.startswith("G1")):
                continue

            x = re.search(r'X([-\d.]+)', line)
            y = re.search(r'Y([-\d.]+)', line)
            z = re.search(r'Z([-\d.]+)', line)
            f = re.search(r'F([-\d.]+)', line)
            e = re.search(r'E([-\d.]+)', line)

            if f:
                current_f = float(f.group(1))
            if x:
                current_x = float(x.group(1))
            if y:
                current_y = float(y.group(1))
            if z:
                current_z = float(z.group(1))

            e_val = float(e.group(1)) if e else 0.0
            is_print = line.startswith("G1") and e and e_val > 0.0

            moves.append({
                "x": current_x,
                "y": current_y,
                "z": current_z,
                "f": current_f,
                "e": e_val,
                "is_print": is_print
            })

        return moves

    def _calculate_anout(self, e_val, f_mm_per_min, seg_length, nozzle_radius_mm):
        # Konstante iz konfiguracije
        flow_at_1v = self._config.get("flow_at_1v_g_per_sec", 0.065)
        max_volt = self._config.get("max_volt", 6.0)
        density = self._config.get("material_density_g_cm3", 1.27)

        if seg_length <= 0 or f_mm_per_min <= 0 or e_val <= 0:
            return 0.0

        # Izracunaj potrebni flow
        feed_mm_per_sec = f_mm_per_min / 60.0
        time_sec = seg_length / feed_mm_per_sec
        volume_mm3 = e_val * math.pi * (nozzle_radius_mm ** 2)
        mass_g = volume_mm3 * density / 1000.0
        flow_g_per_sec = mass_g / time_sec

        # Linearna kalkulacija ANOUT
        # flow_at_1v = flow pri 1V, linearna relacija
        volt = flow_g_per_sec / flow_at_1v
        volt = max(0.0, min(volt, max_volt))

        anout = round(volt / 10.0, 4)
        return anout

    def _generate_moves(self, moves):
        # Dohvati nozzle size iz Cura settings
        try:
            stack = Application.getInstance().getGlobalContainerStack()
            extruder_stack = stack.extruderList[0]
            nozzle_mm = float(extruder_stack.getProperty("machine_nozzle_size", "value"))
        except Exception:
            nozzle_mm = 2.0
            Logger.log("w", "KRLWriter: Ne mogu dohvatiti nozzle size, koristim default 2.0mm")

        nozzle_radius_mm = nozzle_mm / 2.0

        cfg = self._config
        orient = cfg.get("tool_orientation", {"A": -178.635, "B": 0.0, "C": -180.0})
        A = orient.get("A", -178.635)
        B = orient.get("B", 0.0)
        C = orient.get("C", -180.0)
        wait_sec = cfg.get("extrude_wait_sec", 0.2)

        lines = []
        last_vel = None
        last_anout = None
        prev_is_print = False
        prev_x, prev_y, prev_z = None, None, None

        for move in moves:
            x = move["x"]
            y = move["y"]
            z = move["z"]
            f = move["f"]

            vel = round(f / 60000.0, 5)

            if prev_x is not None:
                seg_length = math.sqrt((x-prev_x)**2 + (y-prev_y)**2 + (z-prev_z)**2)
            else:
                seg_length = 0.0
            prev_x, prev_y, prev_z = x, y, z

            lin = "LIN {{X {:.3f},Y {:.3f},Z {:.3f},A {:.3f},B {:.3f},C {:.3f}}} C_DIS".format(
                x, y, z, A, B, C
            )

            if move["is_print"]:
                anout = self._calculate_anout(move["e"], f, seg_length, nozzle_radius_mm)

                if not prev_is_print:
                    lines.append("$ADVANCE = 0")
                    lines.append("$ANOUT[1] = {:.4f}".format(anout))
                    lines.append("WAIT SEC {:.3f}".format(wait_sec))
                    lines.append("$ADVANCE = 5")
                    last_anout = anout

                if anout != last_anout:
                    lines.append("TRIGGER WHEN DISTANCE=0 DELAY=0 DO $ANOUT[1]={:.4f}".format(anout))
                    last_anout = anout
            else:
                if last_anout != 0.0:
                    lines.append("$ANOUT[1] = 0.0")
                    last_anout = 0.0

            if vel != last_vel:
                lines.append("$VEL.CP = {:.5f}".format(vel))
                last_vel = vel

            lines.append(lin)
            prev_is_print = move["is_print"]

        return "\n".join(lines) + "\n"
