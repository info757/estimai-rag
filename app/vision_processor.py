"""
Vision-based PDF processor using GPT-4o.

Converts PDF pages to images and uses Vision LLM to extract pipe information.
"""
import logging
import os
import base64
from typing import Dict, Any, List
import httpx
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


async def pdf_page_to_base64(pdf_path: str, page_num: int = 0) -> str:
    """
    Convert PDF page to base64-encoded image.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page index (0-based)
    
    Returns:
        Base64-encoded PNG image
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render at 150 DPI for good quality without huge file size
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.pil_tobytes(format="PNG")
    
    doc.close()
    
    return base64.b64encode(img_bytes).decode('utf-8')


async def analyze_pdf_page_with_vision(
    pdf_path: str,
    page_num: int = 0,
    model: str = "gpt-4o",
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Analyze a PDF page using GPT-4o Vision.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page index
        model: Vision model to use
        timeout: Request timeout
    
    Returns:
        Dict with analysis results
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    logger.info(f"Analyzing page {page_num} of {pdf_path} with {model}")
    
    # Convert page to image
    image_base64 = await pdf_page_to_base64(pdf_path, page_num)
    
    # System prompt
    system_prompt = """You are an expert civil engineer analyzing utility construction plans.

YOUR CRITICAL TASK: Find and extract EVERY SINGLE pipe shown on this drawing, from BOTH plan view AND profile view sections.

STEP-BY-STEP ANALYSIS:

1. IDENTIFY ALL VIEWS ON THE PAGE:
   - Plan View: Top-down map showing pipe routes, structures, and connections
   - Profile View: Side view showing pipe slopes and elevations
   - Each view shows pipes - extract from BOTH

2. READ THE LEGEND FIRST:
   - Find abbreviations (STM/SD=Storm, SS=Sanitary, WM=Water, etc.)
   - Identify line types and colors (solid, dashed, blue, green, brown)
   - Note material codes (RCP, PVC, DI, HDPE, etc.)

3. SCAN PLAN VIEW - Look for:
   - Blue lines = Storm drain pipes
   - Brown/tan lines = Sanitary sewer pipes
   - Green lines or dashed lines = Water mains
   - Labels near lines showing: size (18"), material (RCP), length (250 LF)
   - Structure symbols: circles (manholes/inlets), squares (valves/hydrants)

4. SCAN PROFILE VIEW - Look for:
   - Sloped lines showing pipe runs
   - Labels directly on pipes: "8\" PVC", "18\" RCP"
   - Invert elevations (IE = 738.5)
   - Length and slope labels (L=200', S=0.6%)

5. EXTRACT EVERY PIPE YOU FIND:
   - If you see a line with a label like "18\" RCP STM" → that's a storm pipe
   - If you see "12\" DI WM" or "12\" DI WATER MAIN" → that's a water pipe
   - If you see "8\" PVC SS" → that's a sanitary pipe
   - Even if some details are missing, extract what you can see

CRITICAL: Don't stop at just the profile view! Also extract pipes from the plan view even if they have less detail."""
    
    # User prompt
    user_prompt = """Analyze this utility construction plan and extract EVERY pipe you can find.

LOOK IN THESE LOCATIONS:
1. Plan View (top section) - pipes drawn as lines connecting structures
2. Profile View (bottom section) - pipes shown with slopes and elevations
3. Any labels near pipe lines

For EACH pipe you find, extract:
- discipline: "storm", "sanitary", or "water" (look for: STM/SD=storm, SS=sanitary, WM/W=water)
- length_ft: length in feet (look for "250 LF", "200'", "L=250", etc.)
- material: (PVC, DI, RCP, HDPE, Concrete, etc.)
- dia_in: diameter in inches (look for: 18", 8", 12", etc.)
- invert_in_ft: start invert elevation (IE/INV values, typically 700-750 range)
- invert_out_ft: end invert elevation
- ground_elev_ft: ground surface elevation

IMPORTANT: 
- If a pipe label says "18\" RCP STM" → {discipline: "storm", material: "RCP", dia_in: 18}
- If you see "12\" DI WATER MAIN" → {discipline: "water", material: "DI", dia_in: 12}
- If you see "8\" PVC SS" → {discipline: "sanitary", material: "PVC", dia_in: 8}
- Extract pipes from BOTH plan view AND profile view - they're separate pipes!

Return JSON with ALL pipes found:
{
  "page_summary": "Plan view shows X utilities, profile view shows Y pipes",
  "pipes": [
    {
      "discipline": "storm",
      "length_ft": 245.0,
      "material": "RCP",
      "dia_in": 18,
      "source": "plan_view"
    },
    {
      "discipline": "sanitary",
      "length_ft": 200.0,
      "material": "PVC",
      "dia_in": 8,
      "invert_in_ft": 738.5,
      "source": "profile_view"
    }
  ]
}"""
    
    # Make API request
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0
            }
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Parse response
        content = data["choices"][0]["message"]["content"]
        
        # Extract JSON from response (might be wrapped in markdown)
        import json
        import re
        
        # Try to find JSON in response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"page_summary": content, "pipes": []}
        
        logger.info(
            f"Vision analysis complete: {len(result.get('pipes', []))} pipes found"
        )
        
        return result


def process_pdf_with_vision(
    pdf_path: str,
    max_pages: int = 10
) -> Dict[str, Any]:
    """
    Process entire PDF with vision (synchronous wrapper).
    
    Args:
        pdf_path: Path to PDF
        max_pages: Maximum pages to process
    
    Returns:
        Combined results from all pages
    """
    logger.info(f"Processing PDF with vision: {pdf_path}")
    
    # Get page count
    doc = fitz.open(pdf_path)
    num_pages = min(len(doc), max_pages)
    doc.close()
    
    logger.info(f"Processing {num_pages} pages")
    
    # Process pages asynchronously
    async def process_all_pages():
        tasks = [
            analyze_pdf_page_with_vision(pdf_path, page_num=i)
            for i in range(num_pages)
        ]
        return await asyncio.gather(*tasks)
    
    # Run async code in sync context
    import asyncio
    import nest_asyncio
    
    # Allow nested event loops (needed for FastAPI)
    nest_asyncio.apply()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    page_results = loop.run_until_complete(process_all_pages())
    
    # Combine results from all pages
    all_pipes = []
    for page_idx, page_result in enumerate(page_results):
        pipes = page_result.get("pipes", [])
        for pipe in pipes:
            pipe["page_num"] = page_idx
            all_pipes.append(pipe)
    
    logger.info(f"Total pipes across all pages: {len(all_pipes)}")
    
    return {
        "pipes": all_pipes,
        "num_pages_processed": num_pages,
        "page_summaries": [r.get("page_summary", "") for r in page_results]
    }

