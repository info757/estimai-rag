#!/usr/bin/env python3
"""
Generate test_04_abbreviations.pdf with heavy abbreviation use.

Tests retrieval quality on real-world construction drawings where
abbreviations are standard practice.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def create_abbreviation_heavy_pdf(filename):
    """Create PDF with heavy abbreviation use."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "UTILITY PLAN - Test 04 (Abbreviations)")
    
    # Legend with abbreviations ONLY (no definitions)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 9.5*inch, "LEGEND:")
    
    c.setFont("Helvetica", 10)
    legend_items = [
        "MH = Access Structure",
        "SSMH = Sewer Access",
        "CB = Drainage Inlet",
        "DI = Metal Pipe or Surface Drain",
        "RCP = Concrete Pipe",
        "HDPE = Plastic Pipe",
        "IE = Pipe Bottom Elev.",
        "FES = Outfall Structure",
        "STA = Distance Marker",
        "CL = Alignment Center"
    ]
    
    y = 9.2*inch
    for item in legend_items:
        c.drawString(1.2*inch, y, item)
        y -= 0.2*inch
    
    # Scale
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, y - 0.3*inch, "SCALE: 1\" = 100'")
    
    # Plan view with HEAVY abbreviation use
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 6*inch, "PLAN VIEW")
    
    c.setFont("Helvetica", 9)
    
    # Sanitary sewer line
    c.setStrokeColorRGB(0, 0.5, 0)
    c.setDash(6, 3)
    c.line(2*inch, 5.5*inch, 6*inch, 5.5*inch)
    
    # Labels with abbreviations
    c.setFillColorRGB(0, 0, 0)
    c.drawString(2*inch, 5.7*inch, "SSMH-1")
    c.drawString(3.8*inch, 5.7*inch, "12\" DI")
    c.drawString(4*inch, 5.9*inch, "300 LF")
    c.drawString(5.8*inch, 5.7*inch, "SSMH-2")
    
    # Storm line
    c.setStrokeColorRGB(0, 0.5, 1)
    c.setDash([])
    c.line(2*inch, 4.5*inch, 6*inch, 4.5*inch)
    
    c.drawString(2*inch, 4.7*inch, "CB-1")
    c.drawString(3.8*inch, 4.7*inch, "18\" RCP")
    c.drawString(4*inch, 4.9*inch, "250 LF")
    c.drawString(5.8*inch, 4.7*inch, "MH-1")
    
    # Water line
    c.setStrokeColorRGB(0, 0, 1)
    c.setDash(3, 3)
    c.line(2*inch, 3.5*inch, 6*inch, 3.5*inch)
    
    c.drawString(2*inch, 3.7*inch, "GATE VALVE")
    c.drawString(3.8*inch, 3.7*inch, "8\" DI")
    c.drawString(4*inch, 3.9*inch, "400 LF")
    c.drawString(5.8*inch, 3.7*inch, "HYDRANT")
    
    # Profile view with abbreviations
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 2.8*inch, "PROFILE - SANITARY SEWER")
    
    c.setFont("Helvetica", 8)
    
    # Ground line
    c.setStrokeColorRGB(0.6, 0.4, 0.2)
    c.line(2*inch, 2.3*inch, 6*inch, 2*inch)
    c.drawString(1.5*inch, 2.3*inch, "GL")
    
    # Pipe line
    c.setStrokeColorRGB(0, 0.5, 0)
    c.line(2*inch, 1.8*inch, 6*inch, 1.5*inch)
    
    # Station markers
    c.drawString(2*inch, 1.5*inch, "STA 0+00")
    c.drawString(4*inch, 1.4*inch, "STA 1+50")
    c.drawString(6*inch, 1.3*inch, "STA 3+00")
    
    # Invert elevations
    c.drawString(2*inch, 1.6*inch, "IE=105.5'")
    c.drawString(6*inch, 1.3*inch, "IE=103.2'")
    
    # Manholes
    c.drawString(2*inch, 2.5*inch, "SSMH-1")
    c.drawString(6*inch, 2.2*inch, "SSMH-2")
    
    # Notes with more abbreviations
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, 1*inch, "NOTES:")
    
    c.setFont("Helvetica", 8)
    notes = [
        "1. All DI pipe per AWWA C151",
        "2. RCP per ASTM C76, Class III min.",
        "3. HDPE pipe per ASTM F714",
        "4. All MH and SSMH structures per std. detail",
        "5. CB with FES at outfall",
        "6. Verify IE at all structures",
        "7. CL elevations shown at each STA"
    ]
    
    y = 0.8*inch
    for note in notes:
        c.drawString(1.2*inch, y, note)
        y -= 0.15*inch
    
    c.save()
    print(f"Created: {filename}")


if __name__ == "__main__":
    create_abbreviation_heavy_pdf("golden_dataset/pdfs/test_04_abbreviations.pdf")

