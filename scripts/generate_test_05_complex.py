#!/usr/bin/env python3
"""
Generate test_05_complex_realistic.pdf

A challenging construction plan with:
- Unknown/modern materials NOT in knowledge base
- Recent code references
- Complex multi-utility scenario
- Obscure construction techniques

Tests if system can detect knowledge gaps and use API fallback.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def create_complex_realistic_pdf(filename):
    """Create complex realistic PDF with unknown terms."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10.5*inch, "RIVERSIDE COMMONS - UTILITY MASTER PLAN")
    
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 10.2*inch, "Sheet 3 of 12 - Storm & Sanitary Systems")
    c.drawString(5.5*inch, 10.2*inch, "Issued: October 2024")
    
    # Legend with MODERN/UNKNOWN materials
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 9.7*inch, "LEGEND & MATERIALS:")
    
    c.setFont("Helvetica", 9)
    legend = [
        "FPVC = Fabric-Reinforced PVC Pipe (ASTM F1803)",
        "TR-FLEX = Rubber Gasket Joint System",
        "CIPP = Cured-In-Place Pipe Rehabilitation",
        "HDD = Horizontal Directional Drilling Method",
        "SRPE = Spiral-Rib Polyethylene Pipe",
        "NYLOPLAST = Thermoplastic Drainage Structure",
        "Per 2024 IPC Section 705.12 & 2024 UPC 702.2"
    ]
    
    y = 9.5*inch
    for item in legend:
        c.drawString(1.2*inch, y, item)
        y -= 0.18*inch
    
    # Scale
    c.setFont("Helvetica", 9)
    c.drawString(1*inch, y - 0.2*inch, "SCALE: 1\" = 80' (Horizontal), 1\" = 20' (Vertical)")
    
    # PLAN VIEW
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 7.5*inch, "PLAN VIEW")
    
    c.setFont("Helvetica", 8)
    
    # Storm drain with MODERN material
    c.setStrokeColorRGB(0, 0.5, 1)
    c.line(1.5*inch, 7*inch, 6.5*inch, 7*inch)
    
    c.setFillColorRGB(0, 0, 0)
    c.drawString(1.3*inch, 7.2*inch, "NYLOPLAST")
    c.drawString(1.4*inch, 7.4*inch, "CB-101")
    
    c.drawString(3*inch, 7.2*inch, "24\" FPVC STORM")
    c.drawString(3*inch, 7.4*inch, "350 LF")
    c.drawString(2.8*inch, 6.8*inch, "TR-FLEX Joints")
    
    c.drawString(6.3*inch, 7.2*inch, "OUTLET")
    c.drawString(6.4*inch, 7.4*inch, "TO CREEK")
    
    # Sanitary with HDD callout
    c.setStrokeColorRGB(0, 0.5, 0)
    c.setDash(6, 3)
    c.line(1.5*inch, 6*inch, 6.5*inch, 6*inch)
    
    c.setDash([])
    c.setFillColorRGB(0, 0, 0)
    c.drawString(1.4*inch, 6.2*inch, "MH-201")
    c.drawString(3*inch, 6.2*inch, "12\" SRPE SANITARY")
    c.drawString(3*inch, 6.4*inch, "280 LF via HDD")
    c.drawString(2.8*inch, 5.8*inch, "(under wetland)")
    c.drawString(6.3*inch, 6.2*inch, "MH-202")
    
    # Water main (NEW PIPE)
    c.setStrokeColorRGB(0, 0.4, 0.8)
    c.setDash(6, 3)
    c.line(1.5*inch, 5*inch, 6.5*inch, 5*inch)
    
    c.setDash([])
    c.setFillColorRGB(0, 0, 0)
    c.drawString(1.4*inch, 5.2*inch, "HYD-301")
    c.drawString(3*inch, 5.2*inch, "8\" DI WATER MAIN")
    c.drawString(3*inch, 5.4*inch, "420 LF")
    c.drawString(6.3*inch, 5.2*inch, "GV-302")
    
    # PROFILE VIEW
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 4.3*inch, "PROFILE - STORM DRAIN (STA 0+00 TO 3+80)")
    
    c.setFont("Helvetica", 7)
    
    # Ground line
    c.setStrokeColorRGB(0.6, 0.4, 0.2)
    c.line(1.5*inch, 3.8*inch, 6.5*inch, 3.5*inch)
    c.drawString(1.2*inch, 3.8*inch, "GROUND")
    
    # Pipe line with FPVC callout
    c.setStrokeColorRGB(0, 0.5, 1)
    c.line(1.5*inch, 3.3*inch, 6.5*inch, 2.8*inch)
    
    # Stations and elevations
    c.drawString(1.5*inch, 3*inch, "STA 0+00")
    c.drawString(1.5*inch, 2.85*inch, "IE=452.3'")
    c.drawString(1.5*inch, 2.7*inch, "GL=458.5'")
    
    c.drawString(4*inch, 2.9*inch, "STA 1+90")
    c.drawString(4*inch, 2.75*inch, "IE=450.8'")
    
    c.drawString(6.5*inch, 2.65*inch, "STA 3+80")
    c.drawString(6.5*inch, 2.5*inch, "IE=449.1'")
    c.drawString(6.5*inch, 2.35*inch, "GL=456.2'")
    
    # Material callout
    c.setFont("Helvetica-Bold", 8)
    c.drawString(3.5*inch, 3.2*inch, "24\" FPVC w/ TR-FLEX")
    c.setFont("Helvetica", 7)
    c.drawString(3.5*inch, 3.05*inch, "Slope: 0.39%")
    
    # NOTES section with code references
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, 2*inch, "GENERAL NOTES:")
    
    c.setFont("Helvetica", 8)
    notes = [
        "1. FPVC pipe shall meet ASTM F1803 requirements with minimum DR of 18.",
        "2. TR-FLEX gasket joints per manufacturer specs, ASTM D3212 elastomer.",
        "3. HDD installation to be performed per ASTM F1962, min. 10ft cover.",
        "4. CIPP rehabilitation using UV-cured liner, min. thickness 6mm.",
        "5. NYLOPLAST drainage structures per ASTM F2618, load rated AASHTO H-20.",
        "6. SRPE outfall pipe (spiral-rib PE) per AASHTO M294, smooth interior.",
        "7. All installations must comply with 2024 IPC Section 705.12.",
        "8. Trench safety per OSHA 29 CFR 1926 Subpart P for depths >5ft.",
        "9. Bedding: ASTM D2321 Type 1 (>95% compaction) for FPVC.",
        "10. Testing: Deflection <5% per ASTM D3034, air test per ASTM F1417."
    ]
    
    y = 1.8*inch
    for note in notes:
        c.drawString(1.2*inch, y, note)
        y -= 0.15*inch
    
    # Footer
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(1*inch, 0.3*inch, "Designed by: Civil Tech Engineering | PE Seal: #C12345 | October 2024")
    
    c.save()
    print(f"✅ Created: {filename}")
    print(f"   Contains unknown materials: FPVC, TR-FLEX, CIPP, HDD, SRPE, NYLOPLAST")
    print(f"   Contains recent codes: 2024 IPC Section 705.12, 2024 UPC 702.2")


if __name__ == "__main__":
    create_complex_realistic_pdf("golden_dataset/pdfs/test_05_complex_realistic.pdf")

