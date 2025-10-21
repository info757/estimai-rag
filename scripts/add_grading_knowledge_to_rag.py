"""
Add grading and earthwork calculation knowledge to RAG.

This provides the grading researcher with context for:
1. Earthwork volume calculation methods
2. Cut/fill calculations
3. Compaction factors
4. Topsoil stripping
"""
import sys
import os
import logging
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from langchain_openai import OpenAIEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


GRADING_KNOWLEDGE = [
    {
        "title": "Average End Area Method for Earthwork",
        "content": """Average End Area Method: Most common method for calculating earthwork volumes between cross-sections.

Formula:
Volume (CY) = [(Area1 + Area2) / 2] × Distance × (1 / 27)

Where:
- Area1 = Cross-sectional area at first station (SF)
- Area2 = Cross-sectional area at second station (SF)
- Distance = Distance between stations (feet)
- Divide by 27 to convert cubic feet to cubic yards

Example:
Station 1+00: Cut area = 150 SF
Station 2+00: Cut area = 200 SF
Distance = 100 feet

Volume = [(150 + 200) / 2] × 100 × (1/27)
       = [350 / 2] × 100 / 27
       = 175 × 100 / 27
       = 17,500 / 27
       = 648 CY of cut

Use this method when you have:
- Cross-sections at regular intervals (stations)
- Areas calculated or given at each station
- Linear features (roads, trenches, slopes)""",
        "category": "calculations",
        "keywords": ["average end area", "volume", "earthwork", "cross section", "formula"]
    },
    {
        "title": "Grid Method for Earthwork",
        "content": """Grid Method: Used for site grading over large areas with spot elevations.

Steps:
1. Overlay grid on site (typically 50' × 50' or 100' × 100')
2. Record existing elevation at each grid intersection
3. Record proposed elevation at each grid intersection
4. Calculate cut or fill at each grid point (Proposed - Existing)
5. Calculate volume for each grid cell

Volume per cell (CY) = (Grid Area × Average Depth) / 27

Four-corner average:
Depth_avg = (D1 + D2 + D3 + D4) / 4

Example for 50' × 50' grid cell:
Corner depths: +2.5 ft (fill), +3.0 ft, +2.0 ft, +2.8 ft
Average = (2.5 + 3.0 + 2.0 + 2.8) / 4 = 2.58 ft
Area = 50 × 50 = 2,500 SF
Volume = (2,500 × 2.58) / 27 = 239 CY fill

Sum all cells to get total cut and fill volumes.

Best for:
- Large pad sites
- Building pads
- Parking lots
- Sites with spot elevation grids""",
        "category": "calculations",
        "keywords": ["grid method", "spot elevations", "site grading", "cut fill", "pad"]
    },
    {
        "title": "Compaction Factors and Shrinkage",
        "content": """Compaction Factors: Account for volume change when soil is excavated and compacted.

Key Concepts:
1. **Swell Factor**: Excavated soil expands (increases volume)
   - Typical: 1.20 to 1.30 (20-30% increase)
   - Clay: 1.25-1.40
   - Rock: 1.50-1.80

2. **Shrinkage Factor**: Compacted soil shrinks (decreases volume)
   - Typical: 0.85 to 0.95 (5-15% decrease)
   - Well-compacted: 0.90
   - Heavy compaction: 0.85

3. **Net Change (Bank to Compacted)**:
   - Shrinkage = 1.00 - 0.90 = 0.10 (10% volume loss)
   - Must import extra material to compensate

Calculations:

**Cut Volume (Bank CY) to Loose Volume (Truck CY):**
Loose Volume = Bank Volume × Swell Factor
Example: 1,000 CY bank × 1.25 = 1,250 CY loose (truck loads)

**Fill Volume (Compacted CY) to Bank Volume Needed:**
Bank Volume Needed = Fill Volume / Compaction Factor
Example: Need 1,000 CY compacted fill
Bank needed = 1,000 / 0.90 = 1,111 CY bank material

**Cut/Fill Balance:**
If Cut = 1,000 CY bank and Fill = 1,000 CY compacted:
Excess = 1,000 - (1,000 / 0.90) = 1,000 - 1,111 = -111 CY (need to import 111 CY)

Always apply compaction factors when:
- Calculating import/export
- Bal ancing cut and fill
- Estimating truck loads
- Pricing earthwork""",
        "category": "calculations",
        "keywords": ["compaction", "shrinkage", "swell", "bank measure", "loose measure"]
    },
    {
        "title": "Topsoil Stripping",
        "content": """Topsoil Stripping: Remove and stockpile topsoil before grading.

Typical Depths:
- Residential: 6-12 inches
- Commercial: 6-8 inches  
- Agricultural: 12-18 inches
- Poor topsoil areas: 4-6 inches

Volume Calculation:
Volume (CY) = (Area × Depth) / 27

Example:
Area = 50,000 SF (approx 1.15 acres)
Depth = 8 inches = 0.67 feet
Volume = (50,000 × 0.67) / 27 = 1,235 CY

Considerations:
1. **Stockpile Location**: Designate area to store topsoil
2. **Stockpile Volume**: Topsoil swells when stripped
   - Stockpile volume = Stripped volume × 1.15 to 1.25
   - 1,235 CY × 1.20 = 1,482 CY stockpile
3. **Reuse**: Topsoil spread for final landscaping
   - Spreads thinner when compacted: 8" stripped → 6" replaced
4. **Import/Export**: May need to import if insufficient or export if excess

Cost Drivers:
- Stripping: $2-4 per CY
- Stockpile: $1-2 per CY
- Respread: $3-5 per CY
- Hauling if export: $10-20 per CY""",
        "category": "site_work",
        "keywords": ["topsoil", "stripping", "stockpile", "landscaping", "depth"]
    },
    {
        "title": "Cut and Fill Balance",
        "content": """Cut/Fill Balance: Minimize import/export by balancing cut and fill on-site.

Steps to Calculate Balance:

1. **Calculate Total Cut (Bank CY)**
   Sum all cut volumes from all areas

2. **Calculate Total Fill (Compacted CY Required)**
   Sum all fill volumes from all areas

3. **Adjust Fill for Compaction**
   Bank CY needed for fill = Fill Volume / Compaction Factor
   Example: 5,000 CY fill / 0.90 = 5,556 CY bank needed

4. **Calculate Balance**
   Balance = Cut - Bank Needed for Fill
   
   - Positive = Excess (export required)
   - Negative = Deficit (import required)
   - Zero = Balanced site

Example:
Total Cut = 8,000 CY bank
Total Fill = 7,000 CY compacted

Bank needed for fill = 7,000 / 0.90 = 7,778 CY
Balance = 8,000 - 7,778 = +222 CY excess (export)

Cost Implications:
- Export: $15-30 per CY (hauling + dump fees)
- Import: $20-40 per CY (material + hauling)
- Balanced site: $0 import/export (optimal)

Design Tip:
Adjust site grades slightly to minimize import/export:
- Lower finish grades to reduce fill needed
- Raise finish grades to reduce cut required
- A 0.1 ft elevation change on 1 acre = 160 CY""",
        "category": "calculations",
        "keywords": ["cut fill balance", "import", "export", "grading optimization"]
    },
    {
        "title": "Contour Grading and Interpolation",
        "content": """Contour Lines: Connect points of equal elevation on grading plans.

Reading Contours:
- Contour interval: Elevation change between lines (typically 1 ft, 2 ft, or 5 ft)
- Index contours: Darker/labeled contours (typically every 5th or 10th line)
- Intermediate contours: Lighter lines between index contours

Slope Calculation from Contours:
Slope (%) = (Elevation Change / Horizontal Distance) × 100

Example:
Contour interval = 1 ft
Distance between contours = 20 ft
Slope = (1 / 20) × 100 = 5%

Steep slopes = Contours close together
Flat slopes = Contours far apart

Interpolation (Finding elevation between contours):
If you need elevation at a point between two contours:

Formula:
Elevation = Lower Contour + [(Distance from lower / Total distance) × Interval]

Example:
Point is between 100 ft and 101 ft contours
Point is 8 ft from 100 ft contour
Total distance between contours = 20 ft
Elevation = 100 + [(8 / 20) × 1] = 100 + 0.4 = 100.4 ft

Use for:
- Calculating depths at specific locations
- Determining spot elevations for design
- Checking drainage flows""",
        "category": "plan_reading",
        "keywords": ["contours", "interpolation", "slope", "grading plan", "elevation"]
    }
]


def add_grading_knowledge():
    """Add grading knowledge chunks to Qdrant."""
    
    logger.info("=" * 80)
    logger.info("ADDING GRADING & EARTHWORK KNOWLEDGE TO RAG")
    logger.info("=" * 80)
    
    # Connect to Qdrant
    client = QdrantClient(url="http://localhost:6333")
    collection_name = "construction_standards"
    
    try:
        collection_info = client.get_collection(collection_name)
        logger.info(f"✓ Collection '{collection_name}' exists")
        logger.info(f"  Current points: {collection_info.points_count}")
    except Exception as e:
        logger.error(f"Collection not found: {e}")
        return
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    logger.info(f"\nAdding {len(GRADING_KNOWLEDGE)} grading knowledge chunks...")
    
    points = []
    for i, knowledge in enumerate(GRADING_KNOWLEDGE):
        logger.info(f"  {i+1}. {knowledge['title']}")
        
        # Generate embedding
        embedding = embeddings.embed_query(knowledge['content'])
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": knowledge['content'],
                "source": "grading_knowledge",
                "title": knowledge['title'],
                "category": knowledge['category'],
                "keywords": knowledge['keywords'],
                "chunk_type": "grading_guide"
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    logger.info(f"\nUploading to Qdrant...")
    client.upsert(collection_name=collection_name, points=points)
    
    collection_info = client.get_collection(collection_name)
    logger.info(f"✓ Successfully added {len(points)} grading knowledge chunks")
    logger.info(f"✓ Collection now contains {collection_info.points_count} total points")
    
    # Test retrieval
    logger.info("\n=== TESTING GRADING KNOWLEDGE RETRIEVAL ===")
    test_queries = [
        "How do I calculate earthwork volumes using average end area?",
        "What compaction factors should I use for cut and fill?",
        "How do I calculate topsoil stripping volumes?"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        query_embedding = embeddings.embed_query(query)
        
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=2,
            query_filter={
                "must": [{"key": "source", "match": {"value": "grading_knowledge"}}]
            }
        )
        
        if results:
            logger.info(f"  Top result: {results[0].payload.get('title')}")
            logger.info(f"  Score: {results[0].score:.3f}")
    
    logger.info("\n✓ Grading knowledge added successfully!")
    logger.info("\nThe grading researcher can now:")
    logger.info("  - Calculate earthwork volumes (average end area, grid method)")
    logger.info("  - Apply correct compaction factors")
    logger.info("  - Calculate topsoil stripping volumes")
    logger.info("  - Balance cut and fill")
    logger.info("  - Read contour lines and interpolate elevations")


if __name__ == "__main__":
    add_grading_knowledge()

