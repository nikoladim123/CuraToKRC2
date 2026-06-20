# Cura KRL Writer Plugin (KUKA KRC2 3D Printing)

Developed by **Nikola Dimitrijevic** - DIATEH d.o.o., Croatia.

A lightweight, high-performance Ultimaker Cura output device plugin designed to bypass complex CAD/CAM software pipelines[cite: 1, 3, 4]. Created by **Nikola Dimitrijevic**, this tool natively translates your sliced 3D printing G-code paths directly into industrial KUKA Robot Language (`.src` / `.dat`) formatted blocks specifically optimized for legacy **KUKA KRC2** controllers[cite: 1, 2, 3, 4].

---

## ⚠️ CRITICAL REQUIREMENT

> ### 🛑 MANDATORY CURA SETTING
> You **MUST** enable **Relative Extrusion** in your Cura print profile settings before slicing. 
> 
> * **Why?** The plugin parses individual G-code line segments (`E` values) to calculate real-time volumetric material flow for the analog output signal. If absolute extrusion is used, the flow calculations will compound incorrectly, resulting in severe over-extrusion or extruder failure.
> * **How to enable it:** In Cura, go to *Configure Setting Visibility...*, search for **"Relative Extrusion"**, check the box to make it visible, and then ensure it is **turned ON** in your print settings panel.

---

## 🚀 Key Features

* **Direct KRL Export:** Adds an "Export KRL" option directly into the Cura saving menu.
* **Automatic KRC2 Memory Chunking:** KRC2 controllers have tight physical memory restrictions[cite: 2]. The plugin auto-splits massive print toolpaths into subroutines based on a configurable line limit, linking them dynamically to a primary `*Main.src` execution file.
* **Dynamic Flow Calculation (`$ANOUT`):** Automatically calculates required volumetric material flow based on feed rate, layer segment length, and your specific Cura nozzle size. This value outputs seamlessly to KUKA analog output `$ANOUT[1]`[cite: 3].
* **Advanced Motion Blending:** Generates precise continuous path movements using KUKA spatial approximation tags (`LIN ... C_DIS`) paired with on-the-fly extrusion adjusting (`TRIGGER WHEN DISTANCE=0 DELAY=0 DO $ANOUT[1]=...`) to prevent physical stops or material blobs at vertex coordinates[cite: 3].
* **Pre-configured Hardware Context:** Embeds essential KRC2 initialization scripts including safety subroutines (`IR_STOPM`), advance execution handling (`$ADVANCE = 5`), path parameters (`$APO.CDIS = 5`), and designated Base/Tool settings[cite: 3].

---

## 🛠️ Configuration & Extruder Calibration

All hardware parameters are read dynamically from the `krl_config.json` file inside the plugin folder[cite: 3]. 

### Customizing Hardware Variables
Before running your first print, open `krl_config.json` and adjust your physical robot coordinates, base coordinates, and orientation[cite: 2, 3]:
* `"tool_number"` & `"base_number"`: Matches your defined tool/base calibrations inside the KCP[cite: 2, 3].
* `"tool_orientation"` (`A`, `B`, `C`): Hardcodes the static printhead angle relative to your base matrix[cite: 2, 3].
* `"home_position"` & `"approach_position"`: PTP configuration vectors (Joint angles A1-A6) for safe initialization sequences[cite: 2, 3].
* `"chunk_size"`: Defines the max line allowance per `.src` subroutine file to safeguard KRC2 RAM limitations[cite: 2, 3].

### How to Calibrate Extruder Flow
To achieve accurate volumetric printing, you must compute the linear flow rate constant (`flow_at_1v_g_per_sec`)[cite: 2, 3]. 

1. Manually command your extruder driver to supply a constant 1 Volt analog baseline signal (equivalent to setting `ANOUT = 0.1` inside your KRC2 environment)[cite: 2].
2. Place an empty material container on a digital scale and tare it to zero[cite: 2].
3. Extrude continuous filament through the hotend for a fixed timeline (between 300 and 600 seconds)[cite: 2].
4. Measure the extruded weight in grams and divide it by your elapsed seconds[cite: 2]:
   $$\text{flow\_at\_1v\_g\_per\_sec} = \frac{\text{grams}}{\text{seconds}}$$
5. Update your value in `krl_config.json`[cite: 3]. To confirm linear extrusion response, repeat the test at 2 Volts (`ANOUT = 0.2`) and verify the output mass doubles[cite: 2]. If non-linear scaling occurs, restrict your system boundaries via the `"max_volt"` threshold[cite: 2, 3].

---

## 📦 Manual Installation

1. Download the repository source files as a `.zip` archive.
2. Locate your local Ultimaker Cura plugin installation folder:
   * **Windows:** `%APPDATA%\cura\<version>\plugins\`
3. Extract your downloaded directory straight into the folder and rename it to `CuraKRLWriter`.
4. Ensure the directory structure mirrors the following breakdown:
```text
   CuraKRLWriter/
   ├── plugin.json
   ├── __init__.py
   ├── KRLWriter.py
   └── krl_config.json
