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

Your task: Identify ALL utility pipes and extract complete information.

Read the drawing systematically:

1. LEGEND: Find and read the legend to understand symbols, colors, abbreviations
2. SCALE: Note the horizontal and vertical scales
3. UTILITY LINES: Identify water mains, sanitary sewers, storm drains
4. ELEVATIONS: Extract invert elevations (IE/INV) from labels and profile views
5. DETAILS: Material, diameter, length for each pipe

CRITICAL for elevations:
- Elevation values are typically 100-500 feet above sea level
- In profile views, read Y-axis grid for elevations (e.g., 410', 420', 430')
- Don't confuse station numbers (0+00, 1+00, 2+00) with elevations
- Invert = bottom inside of pipe

Be accurate - only report what you can clearly see."""
    
    # User prompt
    user_prompt = """Analyze this utility construction plan.

For each pipe, extract:
- discipline: "storm", "sanitary", or "water"
- length_ft: length in feet
- material: pipe material (PVC, DI, RCP, concrete, etc.)
- dia_in: diameter in inches
- invert_in_ft: invert elevation at start (if shown)
- invert_out_ft: invert elevation at end (if shown)
- ground_elev_ft: ground surface elevation (if shown)

Return JSON:
{
  "page_summary": "Brief description of what's on this page",
  "pipes": [
    {
      "discipline": "storm",
      "length_ft": 245.0,
      "material": "RCP",
      "dia_in": 18,
      "invert_in_ft": 420.5,
      "invert_out_ft": 418.2,
      "ground_elev_ft": 425.0
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

