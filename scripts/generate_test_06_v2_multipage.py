#!/usr/bin/env python3
"""
Generate multi-page realistic construction document set.

Kernersville Commerce Park - Professional multi-sheet plan set:
- Sheet 1 (C-301): PLAN VIEW - All utilities at full scale
- Sheet 2 (C-401): PROFILE - Sanitary sewer MH-1 to MH-4
- Sheet 3 (C-402): PROFILE - Storm drain CI-1 to OUT-1
- Sheet 4 (G-001): GENERAL NOTES & LEGEND

This mimics real construction documents with separate sheets for clarity.
"""
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path
import math


# Load schema (same as single-page version)
SCHEMA = {
  "project": {
    "name": "Kernersville Commerce Park",
    "sheet_prefix": "C",
    "scale": {"ft_per_in": 20},
    "font": "Helvetica"
  },
  "site": {
    "bounds_ft": {"x_min": 0, "y_min": 0, "x_max": 800, "y_max": 600},
    "north_deg": 0
  },
  "grading": {
    "contour_interval_ft": 2,
    "plane": { "a": -0.005, "b": -0.002, "c": 740 }
  },
  "legend": {
    "abbreviations": [
      {"abbr":"INV/IE","text":"Invert Elevation"},
      {"abbr":"WM","text":"Water Main"},
      {"abbr":"DI","text":"Ductile Iron"},
      {"abbr":"PVC","text":"Polyvinyl Chloride"},
      {"abbr":"RCP","text":"Reinforced Concrete Pipe"}
    ],
    "notes": [
      "Water main minimum cover: 3.0 feet.",
      "Gravity sewer slope: 0.4% to 2.0%.",
      "Trench width: pipe OD + 16 inches.",
      "Hydrants spaced approximately 500 feet."
    ]
  },
  "storm": {
    "pipes": [
      {"id":"STM-1","from":"CI-1","to":"DI-1","size_in":18,"material":"RCP","slope_pct":0.9},
      {"id":"STM-2","from":"DI-1","to":"ST-1","size_in":24,"material":"RCP","slope_pct":1.0},
      {"id":"STM-3","from":"ST-1","to":"OUT-1","size_in":30,"material":"RCP","slope_pct":1.2}
    ],
    "structures": [
      {"id":"CI-1","type":"curb_inlet","pt":[200,520]},
      {"id":"DI-1","type":"drop_inlet","pt":[450,520]},
      {"id":"ST-1","type":"junction_box","pt":[700,480]},
      {"id":"OUT-1","type":"outfall","pt":[780,450]}
    ]
  },
  "sewer": {
    "pipes": [
      {"id":"SS-1","from":"MH-1","to":"MH-2","size_in":8,"material":"PVC","slope_pct":0.6},
      {"id":"SS-2","from":"MH-2","to":"MH-3","size_in":8,"material":"PVC","slope_pct":0.6},
      {"id":"SS-3","from":"MH-3","to":"MH-4","size_in":10,"material":"PVC","slope_pct":0.5}
    ],
    "manholes": [
      {"id":"MH-1","pt":[150,580]},
      {"id":"MH-2","pt":[350,560]},
      {"id":"MH-3","pt":[550,540]},
      {"id":"MH-4","pt":[720,520]}
    ],
    "profile_runs": [
      {"id":"PR-SS-A","nodes":["MH-1","MH-2","MH-3","MH-4"], "start_inv_ft": 738.5}
    ]
  },
  "water": {
    "mains": [
      {"id":"WM-1","path_ft":[[120,570],[730,570],[730,320],[120,320],[120,570]],"size_in":12,"material":"DI"}
    ],
    "hydrants": [
      {"id":"H-1","pt":[300,570]},{"id":"H-2","pt":[600,570]},{"id":"H-3","pt":[700,330]}
    ],
    "valves": [
      {"id":"GV-1","pt":[120,570]}, {"id":"GV-2","pt":[730,570]}, {"id":"GV-3","pt":[730,320]}, {"id":"GV-4","pt":[120,320]}
    ],
    "cover_min_ft": 3.0
  }
}


def ft_to_pdf(x_ft, y_ft, scale, origin_x, origin_y):
    """Convert site coords (ft) to PDF coords (pts)."""
    x_pdf = origin_x + (x_ft / scale)
    y_pdf = origin_y + (y_ft / scale)
    return x_pdf, y_pdf


def ground_elev(x, y):
    """Calculate ground elevation from grading plane."""
    a = SCHEMA["grading"]["plane"]["a"]
    b = SCHEMA["grading"]["plane"]["b"]
    c = SCHEMA["grading"]["plane"]["c"]
    return a*x + b*y + c


def draw_title_block(c, sheet_num, sheet_title):
    """Draw professional title block."""
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.5*inch, 10.5*inch, SCHEMA["project"]["name"])
    
    c.setFont("Helvetica", 10)
    c.drawString(0.5*inch, 10.2*inch, f"Sheet {sheet_num}: {sheet_title}")
    c.drawString(0.5*inch, 10*inch, "Scale: 1\" = 20'")
    c.drawString(0.5*inch, 9.8*inch, f"Date: October 2025")
    
    # Draw north arrow
    c.setFont("Helvetica-Bold", 12)
    c.drawString(7.5*inch, 10.5*inch, "N ↑")


def generate_page_1_plan_view(c):
    """Sheet C-301: PLAN VIEW - All utilities at full scale."""
    
    draw_title_block(c, "C-301", "UTILITY PLAN VIEW")
    
    # Drawing area: use most of the page for plan view
    scale = SCHEMA["project"]["scale"]["ft_per_in"]  # 20 ft/inch
    origin_x = 0.75 * inch
    origin_y = 1.5 * inch
    
    # Draw site boundary
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setLineWidth(1)
    bounds = SCHEMA["site"]["bounds_ft"]
    x0, y0 = ft_to_pdf(bounds["x_min"], bounds["y_min"], scale, origin_x, origin_y)
    x1, y1 = ft_to_pdf(bounds["x_max"], bounds["y_max"], scale, origin_x, origin_y)
    c.rect(x0, y0, x1-x0, y1-y0)
    
    # === STORM DRAINS (BLUE) ===
    c.setStrokeColorRGB(0, 0, 0.8)
    c.setFillColorRGB(0, 0, 0.8)
    
    # Storm structures
    c.setFont("Helvetica-Bold", 8)
    for struct in SCHEMA["storm"]["structures"]:
        x_pdf, y_pdf = ft_to_pdf(struct["pt"][0], struct["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 6, fill=0, stroke=1)
        c.drawString(x_pdf + 8, y_pdf + 8, struct["id"])
    
    # Storm pipes (thick blue lines with labels)
    c.setLineWidth(4)
    for pipe in SCHEMA["storm"]["pipes"]:
        from_struct = next(s for s in SCHEMA["storm"]["structures"] if s["id"] == pipe["from"])
        to_struct = next(s for s in SCHEMA["storm"]["structures"] if s["id"] == pipe["to"])
        
        x1, y1 = ft_to_pdf(from_struct["pt"][0], from_struct["pt"][1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(to_struct["pt"][0], to_struct["pt"][1], scale, origin_x, origin_y)
        
        c.line(x1, y1, x2, y2)
        
        # Label pipe
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        length = math.sqrt((to_struct["pt"][0]-from_struct["pt"][0])**2 + 
                          (to_struct["pt"][1]-from_struct["pt"][1])**2)
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(mid_x, mid_y + 15, f"{pipe['size_in']}\" {pipe['material']} STORM")
        c.setFont("Helvetica", 8)
        c.drawString(mid_x, mid_y + 3, f"{length:.0f} LF @ {pipe['slope_pct']}%")
    
    # === SANITARY SEWER (BROWN/TAN) ===
    c.setStrokeColorRGB(0.6, 0.4, 0.2)
    c.setFillColorRGB(0.6, 0.4, 0.2)
    
    # Manholes
    c.setFont("Helvetica-Bold", 8)
    for mh in SCHEMA["sewer"]["manholes"]:
        x_pdf, y_pdf = ft_to_pdf(mh["pt"][0], mh["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 6, fill=0, stroke=1)
        c.drawString(x_pdf + 8, y_pdf + 8, mh["id"])
    
    # Sanitary pipes (thick brown lines)
    c.setLineWidth(4)
    for pipe in SCHEMA["sewer"]["pipes"]:
        from_mh = next(m for m in SCHEMA["sewer"]["manholes"] if m["id"] == pipe["from"])
        to_mh = next(m for m in SCHEMA["sewer"]["manholes"] if m["id"] == pipe["to"])
        
        x1, y1 = ft_to_pdf(from_mh["pt"][0], from_mh["pt"][1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(to_mh["pt"][0], to_mh["pt"][1], scale, origin_x, origin_y)
        
        c.line(x1, y1, x2, y2)
        
        # Label pipe
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        length = math.sqrt((to_mh["pt"][0]-from_mh["pt"][0])**2 + 
                          (to_mh["pt"][1]-from_mh["pt"][1])**2)
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(mid_x, mid_y + 15, f"{pipe['size_in']}\" {pipe['material']} SANITARY")
        c.setFont("Helvetica", 8)
        c.drawString(mid_x, mid_y + 3, f"{length:.0f} LF @ {pipe['slope_pct']}%")
    
    # === WATER MAIN (GREEN, DASHED) ===
    c.setStrokeColorRGB(0, 0.6, 0)
    c.setLineWidth(4)
    c.setDash(8, 4)
    
    # Water main loop
    wm = SCHEMA["water"]["mains"][0]
    path = wm["path_ft"]
    for i in range(len(path)-1):
        x1, y1 = ft_to_pdf(path[i][0], path[i][1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(path[i+1][0], path[i+1][1], scale, origin_x, origin_y)
        c.line(x1, y1, x2, y2)
    
    # Water main labels (multiple for visibility)
    c.setFont("Helvetica-Bold", 11)
    c.setDash()  # Solid for text
    c.drawString(4*inch, 8*inch, "12\" DI WATER MAIN (LOOP)")
    c.drawString(1.5*inch, 7.5*inch, "12\" DI WM")
    c.drawString(5.5*inch, 3*inch, "12\" WM")
    
    # Hydrants
    c.setFillColorRGB(0, 0.6, 0)
    for hyd in SCHEMA["water"]["hydrants"]:
        x_pdf, y_pdf = ft_to_pdf(hyd["pt"][0], hyd["pt"][1], scale, origin_x, origin_y)
        c.rect(x_pdf-3, y_pdf-3, 6, 6, fill=1, stroke=1)
        c.setFont("Helvetica", 7)
        c.drawString(x_pdf + 5, y_pdf, hyd["id"])
    
    # Gate valves
    for valve in SCHEMA["water"]["valves"]:
        x_pdf, y_pdf = ft_to_pdf(valve["pt"][0], valve["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 4, fill=1, stroke=1)
    
    # Legend on page
    c.setStrokeColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.5*inch, 1*inch, "LEGEND:")
    c.setFont("Helvetica", 8)
    c.setStrokeColorRGB(0, 0, 0.8)
    c.line(0.5*inch, 0.8*inch, 0.8*inch, 0.8*inch)
    c.setStrokeColorRGB(0, 0, 0)
    c.drawString(0.9*inch, 0.75*inch, "Storm Drain (Blue)")
    
    c.setStrokeColorRGB(0.6, 0.4, 0.2)
    c.line(2.5*inch, 0.8*inch, 2.8*inch, 0.8*inch)
    c.setStrokeColorRGB(0, 0, 0)
    c.drawString(2.9*inch, 0.75*inch, "Sanitary Sewer (Brown)")
    
    c.setStrokeColorRGB(0, 0.6, 0)
    c.setDash(6, 3)
    c.line(5*inch, 0.8*inch, 5.3*inch, 0.8*inch)
    c.setDash()
    c.setStrokeColorRGB(0, 0, 0)
    c.drawString(5.4*inch, 0.75*inch, "Water Main (Green, Dashed)")


def generate_page_2_sanitary_profile(c):
    """Sheet C-401: PROFILE - Sanitary sewer."""
    
    draw_title_block(c, "C-401", "SANITARY SEWER PROFILE: MH-1 TO MH-4")
    
    # Profile drawing area
    origin_x = 1 * inch
    origin_y = 3 * inch
    
    # Calculate cumulative stations
    manholes = SCHEMA["sewer"]["manholes"]
    pipes = SCHEMA["sewer"]["pipes"]
    
    stations = [0]
    for i, pipe in enumerate(pipes):
        from_mh = next(m for m in manholes if m["id"] == pipe["from"])
        to_mh = next(m for m in manholes if m["id"] == pipe["to"])
        length = math.sqrt((to_mh["pt"][0]-from_mh["pt"][0])**2 + 
                          (to_mh["pt"][1]-from_mh["pt"][1])**2)
        stations.append(stations[-1] + length)
    
    # Scale for profile
    h_scale = 4.0 / stations[-1]  # 4 inches for horizontal
    v_scale = 0.5  # 0.5 inch per foot vertical
    
    # Draw ground line
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(1)
    start_inv = SCHEMA["sewer"]["profile_runs"][0]["start_inv_ft"]
    
    for i in range(len(manholes)):
        mh = manholes[i]
        ground = ground_elev(mh["pt"][0], mh["pt"][1])
        x = origin_x + stations[i] * inch * h_scale
        y = origin_y + (ground - 735) * inch * v_scale
        
        if i > 0:
            c.line(prev_x, prev_y, x, y)
        prev_x, prev_y = x, y
    
    # Draw pipe profile
    c.setStrokeColorRGB(0.6, 0.4, 0.2)
    c.setLineWidth(3)
    
    inv = start_inv
    for i, pipe in enumerate(pipes):
        from_mh = manholes[i]
        to_mh = manholes[i+1]
        length = math.sqrt((to_mh["pt"][0]-from_mh["pt"][0])**2 + 
                          (to_mh["pt"][1]-from_mh["pt"][1])**2)
        
        inv_out = inv - (length * pipe["slope_pct"] / 100.0)
        
        x1 = origin_x + stations[i] * inch * h_scale
        y1 = origin_y + (inv - 735) * inch * v_scale
        x2 = origin_x + stations[i+1] * inch * h_scale
        y2 = origin_y + (inv_out - 735) * inch * v_scale
        
        c.line(x1, y1, x2, y2)
        
        # Label pipe
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        c.setFont("Helvetica-Bold", 9)
        c.drawString(mid_x - 30, mid_y - 15, f"{pipe['size_in']}\" {pipe['material']}")
        c.setFont("Helvetica", 8)
        c.drawString(mid_x - 30, mid_y - 25, f"{length:.0f} LF @ {pipe['slope_pct']}%")
        
        # Label inverts
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x1 - 15, y1 - 35, f"IE={inv:.1f}")
        if i == len(pipes) - 1:
            c.drawString(x2 - 15, y2 - 35, f"IE={inv_out:.1f}")
        
        inv = inv_out
    
    # Draw manholes
    c.setFillColorRGB(0.6, 0.4, 0.2)
    for i, mh in enumerate(manholes):
        x = origin_x + stations[i] * inch * h_scale
        ground = ground_elev(mh["pt"][0], mh["pt"][1])
        y_ground = origin_y + (ground - 735) * inch * v_scale
        
        c.circle(x, y_ground, 5, fill=1, stroke=1)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x - 10, y_ground + 10, mh["id"])
        c.setFont("Helvetica", 7)
        c.drawString(x - 20, y_ground + 20, f"Grd={ground:.1f}")
    
    # Station labels
    c.setFont("Helvetica", 8)
    for i, sta in enumerate(stations):
        x = origin_x + sta * inch * h_scale
        c.drawString(x - 15, origin_y - 0.3*inch, f"{sta:.0f}'")


def generate_page_3_storm_profile(c):
    """Sheet C-402: PROFILE - Storm drain."""
    
    draw_title_block(c, "C-402", "STORM DRAIN PROFILE: CI-1 TO OUT-1")
    
    # Profile drawing area
    origin_x = 1 * inch
    origin_y = 3 * inch
    
    # Calculate cumulative stations
    structures = SCHEMA["storm"]["structures"]
    pipes = SCHEMA["storm"]["pipes"]
    
    stations = [0]
    for i, pipe in enumerate(pipes):
        from_struct = next(s for s in structures if s["id"] == pipe["from"])
        to_struct = next(s for s in structures if s["id"] == pipe["to"])
        length = math.sqrt((to_struct["pt"][0]-from_struct["pt"][0])**2 + 
                          (to_struct["pt"][1]-from_struct["pt"][1])**2)
        stations.append(stations[-1] + length)
    
    # Scale
    h_scale = 4.5 / stations[-1]
    v_scale = 0.5
    
    # Draw ground line
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(1)
    
    for i in range(len(structures)):
        struct = structures[i]
        ground = ground_elev(struct["pt"][0], struct["pt"][1])
        x = origin_x + stations[i] * inch * h_scale
        y = origin_y + (ground - 735) * inch * v_scale
        
        if i > 0:
            c.line(prev_x, prev_y, x, y)
        prev_x, prev_y = x, y
    
    # Draw storm pipes
    c.setStrokeColorRGB(0, 0, 0.8)
    c.setLineWidth(3)
    
    # Estimate starting invert
    inv = 737.0
    for i, pipe in enumerate(pipes):
        from_struct = structures[i]
        to_struct = structures[i+1]
        length = math.sqrt((to_struct["pt"][0]-from_struct["pt"][0])**2 + 
                          (to_struct["pt"][1]-from_struct["pt"][1])**2)
        
        inv_out = inv - (length * pipe["slope_pct"] / 100.0)
        
        x1 = origin_x + stations[i] * inch * h_scale
        y1 = origin_y + (inv - 735) * inch * v_scale
        x2 = origin_x + stations[i+1] * inch * h_scale
        y2 = origin_y + (inv_out - 735) * inch * v_scale
        
        c.line(x1, y1, x2, y2)
        
        # Label
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        c.setFont("Helvetica-Bold", 9)
        c.drawString(mid_x - 30, mid_y - 15, f"{pipe['size_in']}\" {pipe['material']}")
        c.setFont("Helvetica", 8)
        c.drawString(mid_x - 30, mid_y - 25, f"{length:.0f} LF @ {pipe['slope_pct']}%")
        
        # Inverts
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x1 - 15, y1 - 35, f"IE={inv:.1f}")
        if i == len(pipes) - 1:
            c.drawString(x2 - 15, y2 - 35, f"IE={inv_out:.1f}")
        
        inv = inv_out
    
    # Draw structures
    c.setFillColorRGB(0, 0, 0.8)
    for i, struct in enumerate(structures):
        x = origin_x + stations[i] * inch * h_scale
        ground = ground_elev(struct["pt"][0], struct["pt"][1])
        y_ground = origin_y + (ground - 735) * inch * v_scale
        
        c.circle(x, y_ground, 5, fill=1, stroke=1)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x - 10, y_ground + 10, struct["id"])
        c.setFont("Helvetica", 7)
        c.drawString(x - 20, y_ground + 20, f"Grd={ground:.1f}")
    
    # Stations
    c.setFont("Helvetica", 8)
    for i, sta in enumerate(stations):
        x = origin_x + sta * inch * h_scale
        c.drawString(x - 15, origin_y - 0.3*inch, f"{sta:.0f}'")


def generate_page_4_notes(c):
    """Sheet G-001: General notes and legend."""
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "GENERAL NOTES & LEGEND")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 9.5*inch, "Abbreviations:")
    
    c.setFont("Helvetica", 10)
    y = 9.2*inch
    for abbr in SCHEMA["legend"]["abbreviations"]:
        c.drawString(1.2*inch, y, f"{abbr['abbr']} = {abbr['text']}")
        y -= 0.25*inch
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y - 0.3*inch, "General Notes:")
    
    c.setFont("Helvetica", 10)
    y -= 0.6*inch
    for i, note in enumerate(SCHEMA["legend"]["notes"], 1):
        c.drawString(1.2*inch, y, f"{i}. {note}")
        y -= 0.25*inch
    
    # Utility summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y - 0.3*inch, "Utility Summary:")
    
    c.setFont("Helvetica", 10)
    y -= 0.6*inch
    c.drawString(1.2*inch, y, f"Storm Drain: {len(SCHEMA['storm']['pipes'])} pipes, "
                 f"{sum(math.sqrt((next(s for s in SCHEMA['storm']['structures'] if s['id']==p['to'])['pt'][0]-next(s for s in SCHEMA['storm']['structures'] if s['id']==p['from'])['pt'][0])**2 + (next(s for s in SCHEMA['storm']['structures'] if s['id']==p['to'])['pt'][1]-next(s for s in SCHEMA['storm']['structures'] if s['id']==p['from'])['pt'][1])**2) for p in SCHEMA['storm']['pipes']):.0f} LF")
    y -= 0.25*inch
    c.drawString(1.2*inch, y, f"Sanitary Sewer: {len(SCHEMA['sewer']['pipes'])} pipes, "
                 f"{sum(math.sqrt((next(m for m in SCHEMA['sewer']['manholes'] if m['id']==p['to'])['pt'][0]-next(m for m in SCHEMA['sewer']['manholes'] if m['id']==p['from'])['pt'][0])**2 + (next(m for m in SCHEMA['sewer']['manholes'] if m['id']==p['to'])['pt'][1]-next(m for m in SCHEMA['sewer']['manholes'] if m['id']==p['from'])['pt'][1])**2) for p in SCHEMA['sewer']['pipes']):.0f} LF")
    y -= 0.25*inch
    c.drawString(1.2*inch, y, f"Water Main: 1 loop, 1720 LF (approx)")


def main():
    """Generate multi-page PDF."""
    output_dir = Path(__file__).parent.parent / "golden_dataset" / "pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_06_v2_multipage.pdf"
    
    print(f"Generating multi-page construction document set...")
    print(f"Output: {output_path}")
    
    # Create PDF with multiple pages
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Page 1: Plan View
    print("  Page 1/4: Plan view (all utilities)...")
    generate_page_1_plan_view(c)
    c.showPage()
    
    # Page 2: Sanitary Profile
    print("  Page 2/4: Sanitary sewer profile...")
    generate_page_2_sanitary_profile(c)
    c.showPage()
    
    # Page 3: Storm Profile
    print("  Page 3/4: Storm drain profile...")
    generate_page_3_storm_profile(c)
    c.showPage()
    
    # Page 4: Notes
    print("  Page 4/4: General notes & legend...")
    generate_page_4_notes(c)
    c.showPage()
    
    # Save
    c.save()
    print(f"✅ Multi-page PDF generated: {output_path}")
    print(f"   Total pages: 4")
    print(f"   Expected pipes: 7 (3 storm + 3 sanitary + 1 water)")
    print(f"   Page 1 should detect: 4 pipes (plan view: 3 storm + 1 water)")
    print(f"   Page 2 should detect: 3 pipes (sanitary profile)")
    print(f"   Page 3 should detect: 3 pipes (storm profile)")


if __name__ == "__main__":
    main()

