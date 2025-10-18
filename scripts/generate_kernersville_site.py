#!/usr/bin/env python3
"""
Generate realistic multi-utility construction site PDF.

Kernersville Commerce Park - Full utility layout with:
- 3 storm drain pipes (RCP)
- 3 sanitary sewer pipes (PVC) 
- 1 water main loop (DI)
- Calculated elevations from grading plane
- Profile view with inverts
- Professional legend and specs

This tests the system on realistic complexity.
"""
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path
import math


# Load schema
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
  },
  "details": {
    "spec_box": [
      "Trench Width = Pipe OD + 16 in (min).",
      "WM Minimum Cover = 36 in (3.0 ft).",
      "Sewer Manhole spacing ≤ 400 ft.",
      "Water over Sewer at crossings; maintain 18 in vertical separation."
    ]
  }
}


def ft_to_pdf(x_ft, y_ft, scale_ft_per_in=20, origin_x=1*inch, origin_y=1*inch):
    """Convert site coordinates (ft) to PDF coordinates (points)."""
    x_pdf = origin_x + (x_ft / scale_ft_per_in) * inch
    y_pdf = origin_y + (y_ft / scale_ft_per_in) * inch
    return x_pdf, y_pdf


def calc_ground_elevation(x, y):
    """Calculate ground elevation from grading plane."""
    plane = SCHEMA["grading"]["plane"]
    return plane["a"] * x + plane["b"] * y + plane["c"]


def calc_pipe_length(pt1, pt2):
    """Calculate pipe length in feet."""
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    return math.sqrt(dx*dx + dy*dy)


def create_realistic_site_pdf(filename):
    """Generate realistic multi-utility construction site PDF."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title block
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10.5*inch, "KERNERSVILLE COMMERCE PARK")
    
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 10.2*inch, "UTILITY PLAN - STORM, SEWER, WATER")
    c.drawString(1*inch, 10.0*inch, "Sheet C-301")
    c.drawString(5*inch, 10.2*inch, "Scale: 1\" = 20'")
    c.drawString(5*inch, 10.0*inch, "North: Up")
    
    # Legend
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 9.5*inch, "LEGEND:")
    
    c.setFont("Helvetica", 9)
    y = 9.3*inch
    for abbr_item in SCHEMA["legend"]["abbreviations"]:
        c.drawString(1.2*inch, y, f"{abbr_item['abbr']} = {abbr_item['text']}")
        y -= 0.15*inch
    
    # Spec box
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.5*inch, 9.5*inch, "SPECIFICATIONS:")
    
    c.setFont("Helvetica", 8)
    y = 9.3*inch
    for note in SCHEMA["details"]["spec_box"]:
        c.drawString(4.7*inch, y, note)
        y -= 0.13*inch
    
    # Plan view title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 8.5*inch, "PLAN VIEW")
    
    # Draw plan view (simplified - just structures and pipes)
    origin_x = 1*inch
    origin_y = 1.5*inch
    scale = 20  # ft per inch
    
    # Storm structures
    c.setStrokeColorRGB(0, 0, 0.8)
    c.setFillColorRGB(0, 0, 0.8)
    c.setFont("Helvetica", 7)
    
    for struct in SCHEMA["storm"]["structures"]:
        x_pdf, y_pdf = ft_to_pdf(struct["pt"][0], struct["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 3, fill=0, stroke=1)
        c.drawString(x_pdf + 5, y_pdf + 5, struct["id"])
    
    # Storm pipes
    c.setLineWidth(2)
    for pipe in SCHEMA["storm"]["pipes"]:
        from_pt = next(s["pt"] for s in SCHEMA["storm"]["structures"] if s["id"] == pipe["from"])
        to_pt = next(s["pt"] for s in SCHEMA["storm"]["structures"] if s["id"] == pipe["to"])
        
        x1, y1 = ft_to_pdf(from_pt[0], from_pt[1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(to_pt[0], to_pt[1], scale, origin_x, origin_y)
        
        c.line(x1, y1, x2, y2)
        
        # Label
        mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
        length = calc_pipe_length(from_pt, to_pt)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(mid_x, mid_y + 8, f"{pipe['size_in']}\" {pipe['material']}")
        c.drawString(mid_x, mid_y - 2, f"{length:.0f} LF")
    
    # Sewer manholes
    c.setStrokeColorRGB(0.6, 0.3, 0)
    c.setFillColorRGB(0.6, 0.3, 0)
    c.setLineWidth(1)
    
    for mh in SCHEMA["sewer"]["manholes"]:
        x_pdf, y_pdf = ft_to_pdf(mh["pt"][0], mh["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 4, fill=0, stroke=1)
        c.circle(x_pdf, y_pdf, 2, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x_pdf + 6, y_pdf + 6, mh["id"])
        c.setFillColorRGB(0.6, 0.3, 0)
    
    # Sewer pipes
    c.setStrokeColorRGB(0.6, 0.3, 0)
    c.setLineWidth(1.5)
    for pipe in SCHEMA["sewer"]["pipes"]:
        from_pt = next(m["pt"] for m in SCHEMA["sewer"]["manholes"] if m["id"] == pipe["from"])
        to_pt = next(m["pt"] for m in SCHEMA["sewer"]["manholes"] if m["id"] == pipe["to"])
        
        x1, y1 = ft_to_pdf(from_pt[0], from_pt[1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(to_pt[0], to_pt[1], scale, origin_x, origin_y)
        
        c.line(x1, y1, x2, y2)
        
        # Label
        mid_x, mid_y = (x1+x2)/2, (y1+y2)/2 - 12
        length = calc_pipe_length(from_pt, to_pt)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(mid_x, mid_y, f"{pipe['size_in']}\" {pipe['material']} SS")
    
    # Water main
    c.setStrokeColorRGB(0, 0.6, 0)
    c.setLineWidth(2)
    
    path = SCHEMA["water"]["mains"][0]["path_ft"]
    for i in range(len(path) - 1):
        x1, y1 = ft_to_pdf(path[i][0], path[i][1], scale, origin_x, origin_y)
        x2, y2 = ft_to_pdf(path[i+1][0], path[i+1][1], scale, origin_x, origin_y)
        c.line(x1, y1, x2, y2)
    
    # Water main label
    c.setFillColorRGB(0, 0, 0)
    x_mid, y_mid = ft_to_pdf(400, 570, scale, origin_x, origin_y)
    c.drawString(x_mid, y_mid + 10, "12\" DI WM")
    
    # Hydrants
    c.setFillColorRGB(0, 0.6, 0)
    for hyd in SCHEMA["water"]["hydrants"]:
        x_pdf, y_pdf = ft_to_pdf(hyd["pt"][0], hyd["pt"][1], scale, origin_x, origin_y)
        c.rect(x_pdf-3, y_pdf-3, 6, 6, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x_pdf + 5, y_pdf + 5, hyd["id"])
        c.setFillColorRGB(0, 0.6, 0)
    
    # Valves
    for valve in SCHEMA["water"]["valves"]:
        x_pdf, y_pdf = ft_to_pdf(valve["pt"][0], valve["pt"][1], scale, origin_x, origin_y)
        c.circle(x_pdf, y_pdf, 2, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 6)
        c.drawString(x_pdf + 4, y_pdf + 4, valve["id"])
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0.6, 0)
    
    # Profile view (sewer)
    c.setFont("Helvetica-Bold", 11)
    profile_y_start = 5.5*inch
    c.setFillColorRGB(0, 0, 0)
    c.drawString(1*inch, profile_y_start + 0.3*inch, "PROFILE: SANITARY SEWER MH-1 TO MH-4")
    
    # Profile grid
    profile_x = 1*inch
    profile_width = 6*inch
    profile_height = 1.5*inch
    
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.rect(profile_x, profile_y_start - profile_height, profile_width, profile_height, fill=0, stroke=1)
    
    # Calculate horizontal distances and inverts
    manholes = SCHEMA["sewer"]["manholes"]
    pipes = SCHEMA["sewer"]["pipes"]
    
    # Cumulative stations
    stations = [0]
    for i, pipe in enumerate(pipes):
        from_pt = next(m["pt"] for m in manholes if m["id"] == pipe["from"])
        to_pt = next(m["pt"] for m in manholes if m["id"] == pipe["to"])
        length = calc_pipe_length(from_pt, to_pt)
        stations.append(stations[-1] + length)
    
    # Draw profile
    c.setStrokeColorRGB(0.6, 0.3, 0)
    c.setLineWidth(2)
    
    start_inv = SCHEMA["sewer"]["profile_runs"][0]["start_inv_ft"]
    current_inv = start_inv
    
    for i, pipe in enumerate(pipes):
        from_pt = next(m["pt"] for m in manholes if m["id"] == pipe["from"])
        to_pt = next(m["pt"] for m in manholes if m["id"] == pipe["to"])
        length = calc_pipe_length(from_pt, to_pt)
        
        # Calculate drop
        drop_ft = length * (pipe["slope_pct"] / 100.0)
        next_inv = current_inv - drop_ft
        
        # Profile coordinates
        x1_prof = profile_x + (stations[i] / stations[-1]) * profile_width
        x2_prof = profile_x + (stations[i+1] / stations[-1]) * profile_width
        
        # Normalize inverts to profile height
        inv_range = 10  # Show 10 ft vertical range
        y1_prof = profile_y_start - profile_height + (1 - (start_inv - current_inv) / inv_range) * profile_height
        y2_prof = profile_y_start - profile_height + (1 - (start_inv - next_inv) / inv_range) * profile_height
        
        # Draw pipe
        c.line(x1_prof, y1_prof, x2_prof, y2_prof)
        
        # Labels
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x1_prof, y1_prof + 8, f"IE={current_inv:.2f}'")
        mid_x = (x1_prof + x2_prof) / 2
        mid_y = (y1_prof + y2_prof) / 2
        c.drawString(mid_x, mid_y - 10, f"{pipe['size_in']}\" {pipe['material']}")
        c.drawString(mid_x, mid_y - 18, f"S={pipe['slope_pct']}%, L={length:.0f}'")
        
        current_inv = next_inv
    
    # Final invert
    c.drawString(x2_prof, y2_prof + 8, f"IE={current_inv:.2f}'")
    
    # Station labels
    c.setFont("Helvetica", 6)
    for i, mh_id in enumerate(["MH-1", "MH-2", "MH-3", "MH-4"]):
        x_prof = profile_x + (stations[i] / stations[-1]) * profile_width
        c.drawString(x_prof, profile_y_start - profile_height - 10, f"STA {stations[i]:.0f}")
        c.drawString(x_prof, profile_y_start - profile_height - 20, mh_id)
    
    # Scale bar
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(2)
    scale_x = 6.5*inch
    scale_y = 0.7*inch
    scale_len_ft = 100
    scale_len_pdf = (scale_len_ft / 20) * inch
    
    c.line(scale_x, scale_y, scale_x + scale_len_pdf, scale_y)
    c.line(scale_x, scale_y - 3, scale_x, scale_y + 3)
    c.line(scale_x + scale_len_pdf, scale_y - 3, scale_x + scale_len_pdf, scale_y + 3)
    
    c.setFont("Helvetica", 8)
    c.drawString(scale_x + scale_len_pdf/2 - 15, scale_y - 15, "0     100 ft")
    
    # North arrow
    north_x = 7*inch
    north_y = 9*inch
    c.setLineWidth(1)
    c.line(north_x, north_y, north_x, north_y + 0.4*inch)  # Arrow shaft
    c.line(north_x, north_y + 0.4*inch, north_x - 0.05*inch, north_y + 0.3*inch)
    c.line(north_x, north_y + 0.4*inch, north_x + 0.05*inch, north_y + 0.3*inch)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(north_x - 5, north_y - 15, "N")
    
    c.save()
    print(f"✅ Generated: {filename}")
    print(f"   Complexity: {len(SCHEMA['storm']['pipes'])} storm + {len(SCHEMA['sewer']['pipes'])} sewer + 1 water = {len(SCHEMA['storm']['pipes']) + len(SCHEMA['sewer']['pipes']) + 1} pipes")
    print(f"   Features: Plan view, profile view, legend, specs")
    print(f"   Materials: RCP, PVC, DI (all in knowledge base)")


if __name__ == "__main__":
    output_file = "golden_dataset/pdfs/test_06_realistic_site.pdf"
    create_realistic_site_pdf(output_file)
    print(f"\n✅ Ready for blind testing!")
    print(f"   Run: python -c \"from app.agents.main_agent import run_takeoff; run_takeoff('{output_file}')\"")

