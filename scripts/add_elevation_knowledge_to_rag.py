"""
Add elevation interpretation knowledge to RAG.

This provides the elevation researcher with context for:
1. Understanding elevation terminology
2. Calculating pipe depths
3. Validating cover depths
4. Interpreting profile sheets
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


ELEVATION_KNOWLEDGE = [
    {
        "title": "Invert Elevation Definition",
        "content": """Invert Elevation (IE or INV): The elevation of the inside bottom of a pipe.

This is the lowest point inside the pipe where water flows. Invert elevations are critical for:
1. Ensuring proper gravity flow (water flows downhill)
2. Calculating pipe depth and cover
3. Verifying code compliance for minimum burial depth

Common notations:
- IE IN: Invert elevation at upstream end (inlet)
- IE OUT: Invert elevation at downstream end (outlet)
- INV IN / INV OUT: Same as IE IN / IE OUT

Example: "IE IN = 645.50 ft" means the pipe bottom at the inlet is at elevation 645.50 feet.""",
        "category": "elevation_fundamentals",
        "keywords": ["invert", "IE", "INV", "pipe bottom", "elevation"]
    },
    {
        "title": "Rim Elevation and Ground Level",
        "content": """Rim Elevation (RIM): The elevation of the top of a structure (manhole, catch basin).

Also called:
- TOP: Top of structure
- GL: Ground Level
- FFE: Finished Floor Elevation (for buildings)
- EG: Existing Ground

Rim elevation is used to calculate:
1. Structure depth = RIM - Invert Elevation
2. Cover depth = Ground Level - Top of Pipe
3. Surface drainage slopes

Example: If RIM = 655.00 ft and IE = 645.50 ft, then structure depth = 9.5 feet.""",
        "category": "elevation_fundamentals",
        "keywords": ["rim", "RIM", "ground level", "GL", "TOP", "surface"]
    },
    {
        "title": "Pipe Depth Calculation",
        "content": """Pipe Depth = Ground Elevation - Invert Elevation

Steps to calculate pipe depth:
1. Identify ground elevation (RIM, GL, or EG)
2. Identify pipe invert elevation (IE or INV)
3. Subtract: Depth = Ground - Invert

Example:
- Ground Level = 655.00 ft
- Invert Elevation = 645.50 ft
- Pipe Depth = 655.00 - 645.50 = 9.5 ft

Cover Depth = Ground Elevation - (Invert Elevation + Pipe Diameter)

Example with 18" diameter pipe:
- Cover Depth = 655.00 - (645.50 + 1.5) = 8.0 ft of cover over pipe""",
        "category": "calculations",
        "keywords": ["depth", "cover", "calculation", "ground", "invert"]
    },
    {
        "title": "Minimum Cover Requirements",
        "content": """Minimum pipe cover depths (soil above top of pipe):

Storm Drains (RCP, HDPE):
- Under roads: 2.0 ft minimum, 3.0 ft preferred
- Under parking/driveways: 1.5 ft minimum
- In landscaped areas: 1.0 ft minimum

Sanitary Sewers (PVC, VCP):
- Under roads: 3.0 ft minimum (frost protection)
- Under parking: 2.0 ft minimum  
- In yards: 1.5 ft minimum

Water Mains (DI):
- Under roads: 3.5 ft minimum (frost line dependent)
- Under parking: 3.0 ft minimum
- Frost line varies by region: 18"-48" typical

Insufficient cover leads to:
- Pipe damage from traffic loads
- Freezing in cold climates
- Settlement issues""",
        "category": "code_requirements",
        "keywords": ["cover", "minimum depth", "code", "requirements", "frost"]
    },
    {
        "title": "Profile Sheet Interpretation",
        "content": """Profile sheets show pipe elevations along a horizontal alignment (station).

Key elements on profile sheets:
1. Horizontal axis: Station (0+00, 1+00, 2+50)
2. Vertical axis: Elevation (feet above sea level or datum)
3. Existing ground line: Shows current terrain
4. Proposed invert line: Shows pipe bottom elevation
5. Pipe slope: Rise/run or percentage

Reading profile elevations:
- Find station location (e.g., 1+50)
- Read vertical scale for invert elevation
- Note: Ground elevation shown as separate line above pipe
- Calculate depth: Ground elevation - Invert elevation at that station

Example:
At Station 1+50:
- Ground Elevation = 658.0 ft
- Invert Elevation = 650.5 ft
- Pipe Depth = 7.5 ft""",
        "category": "plan_reading",
        "keywords": ["profile", "station", "alignment", "slope", "drawing"]
    },
    {
        "title": "Pipe Slope and Grade",
        "content": """Pipe slope ensures gravity flow in drainage systems.

Slope notation:
- Percentage: 1% = 1 ft drop per 100 ft length
- Ratio: 1:100 = same as 1%
- Feet per foot: 0.01 ft/ft = 1%

Minimum slopes by discipline:

Storm Drains:
- 0.5% minimum (0.005 ft/ft)
- 1.0% preferred for sediment transport
- Steeper in mountainous terrain

Sanitary Sewers:
- 1.0% minimum for 8" pipes
- 0.5% minimum for 10" and larger
- Must maintain 2 ft/sec minimum velocity

Calculating slope from inverts:
Slope = (IE_OUT - IE_IN) / Length

Example:
- IE IN = 650.00 ft
- IE OUT = 648.00 ft
- Length = 200 ft
- Slope = (648.00 - 650.00) / 200 = -2.00 / 200 = -0.01 = -1% (drops 1 ft per 100 ft)""",
        "category": "calculations",
        "keywords": ["slope", "grade", "flow", "velocity", "drop"]
    },
    {
        "title": "Station and Offset Notation",
        "content": """Stations measure horizontal distance along pipe alignment.

Station format:
- 0+00: Starting point (zero station)
- 1+00: 100 feet from start
- 2+50: 250 feet from start
- 10+00: 1000 feet from start

Offset notation:
- 10 LT: 10 feet left of centerline
- 15 RT: 15 feet right of centerline

Full location notation:
"Station 5+25, 10 LT" = 525 feet along alignment, 10 feet left

Use cases:
- Profile sheets: Show elevations at stations
- Plan views: Reference structures by station
- Construction staking: Locate features in field

Pipe length between stations:
Station 2+50 to Station 4+00 = 400 ft - 250 ft = 150 ft length""",
        "category": "plan_reading",
        "keywords": ["station", "stationing", "offset", "alignment", "centerline"]
    },
    {
        "title": "Elevation Datum and Benchmarks",
        "content": """Elevation datum: Reference point from which all elevations are measured.

Common datums:
- NAVD 88: North American Vertical Datum of 1988 (most common)
- NGVD 29: National Geodetic Vertical Datum of 1929 (older plans)
- Project datum: Arbitrary 100.00 or 1000.00 for relative elevations
- Mean Sea Level (MSL): Historic reference

Benchmark (BM):
- Known elevation point in the field
- Used to transfer elevations to construction site
- Example: "BM #1: NAVD 88 = 652.45 ft, Top of fire hydrant near south property line"

Importance for takeoff:
- All elevations on a plan use the same datum
- Can't compare elevations from plans with different datums
- Verify datum notation (usually in title block or notes)

Typical notation:
"ALL ELEVATIONS SHOWN ARE NAVD 88 DATUM"
"BENCHMARKS: SEE SHEET C-1.0 FOR SURVEY CONTROL" """,
        "category": "fundamentals",
        "keywords": ["datum", "NAVD", "benchmark", "BM", "reference", "survey"]
    },
    {
        "title": "Common Elevation Errors and Validation",
        "content": """Common elevation errors to watch for during takeoff:

1. **Negative depths**: Pipe above ground
   - If IE > GL, pipe is exposed (error unless intentional)

2. **Insufficient cover**: Too shallow
   - Storm drain under road with 0.5 ft cover (should be 2+ ft)

3. **Excessive depth**: Too deep (cost issue)
   - Pipe at 20 ft depth when 6 ft would work

4. **Uphill flow**: Gravity pipe going upward
   - IE IN < IE OUT means water flows uphill (impossible for gravity)

5. **Datum mismatch**: Mixing elevation systems
   - Plan sheet shows NAVD 88, profile uses project datum

6. **Decimal errors**: Typos in elevation values
   - IE = 64.50 ft (should be 645.50 ft based on context)

Validation checks:
- Cover depth 1-15 ft range (typical)
- Invert elevations decrease downstream (gravity flow)
- All structures on same datum
- Rim > Invert (always)
- Slopes between 0.5% and 10% (typical)""",
        "category": "quality_control",
        "keywords": ["errors", "validation", "QC", "check", "mistakes"]
    }
]


def add_elevation_knowledge():
    """Add elevation knowledge chunks to Qdrant."""
    
    logger.info("=" * 80)
    logger.info("ADDING ELEVATION KNOWLEDGE TO RAG")
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
    
    logger.info(f"\nAdding {len(ELEVATION_KNOWLEDGE)} elevation knowledge chunks...")
    
    points = []
    for i, knowledge in enumerate(ELEVATION_KNOWLEDGE):
        logger.info(f"  {i+1}. {knowledge['title']}")
        
        # Generate embedding
        embedding = embeddings.embed_query(knowledge['content'])
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": knowledge['content'],
                "source": "elevation_knowledge",
                "title": knowledge['title'],
                "category": knowledge['category'],
                "keywords": knowledge['keywords'],
                "chunk_type": "elevation_guide"
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    logger.info(f"\nUploading to Qdrant...")
    client.upsert(collection_name=collection_name, points=points)
    
    collection_info = client.get_collection(collection_name)
    logger.info(f"✓ Successfully added {len(points)} elevation knowledge chunks")
    logger.info(f"✓ Collection now contains {collection_info.points_count} total points")
    
    # Test retrieval
    logger.info("\n=== TESTING ELEVATION KNOWLEDGE RETRIEVAL ===")
    test_queries = [
        "How do I calculate pipe depth from invert elevation?",
        "What is minimum cover for storm drains under roads?",
        "How do I read a profile sheet?"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        query_embedding = embeddings.embed_query(query)
        
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=2,
            query_filter={
                "must": [{"key": "source", "match": {"value": "elevation_knowledge"}}]
            }
        )
        
        if results:
            logger.info(f"  Top result: {results[0].payload.get('title')}")
            logger.info(f"  Score: {results[0].score:.3f}")
    
    logger.info("\n✓ Elevation knowledge added successfully!")
    logger.info("\nThe elevation researcher can now:")
    logger.info("  - Understand invert elevation terminology")
    logger.info("  - Calculate pipe depths correctly")
    logger.info("  - Validate cover depth requirements")
    logger.info("  - Interpret profile sheets")
    logger.info("  - Check for common elevation errors")


if __name__ == "__main__":
    add_elevation_knowledge()

