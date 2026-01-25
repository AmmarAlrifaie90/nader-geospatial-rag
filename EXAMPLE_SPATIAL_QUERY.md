# Example: "Show me all points inside a polygon"

## Complete System Flow

### User Query
```
"show me all points inside a polygon"
```

---

## Step-by-Step Process

### Step 1: Intent Routing
**File:** `router/intent_router.py`

The system classifies the query:
```python
{
    "tool": "sql_query",
    "confidence": 0.9,
    "reason": "User wants to find data from database"
}
```

**Result:** Routes to SQL Generator tool

---

### Step 2: SQL Generation
**File:** `tools/tool1_sql_generator.py`

The LLM (Qwen 2.5 7B) generates SQL based on:
- Database schema (knows `mods`, `borholes`, `surface_samples` are POINTS)
- Database schema (knows `geology_master` is POLYGON)
- Spatial operation pattern: "inside" → `ST_Intersects`

**Generated SQL:**
```sql
SELECT 
    m.gid, 
    m.eng_name, 
    m.major_comm, 
    m.region,
    g.unit_name AS polygon_name,
    ST_Y(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS latitude,
    ST_X(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS longitude
FROM mods m
JOIN geology_master g 
    ON ST_Intersects(
        ST_SetSRID(m.geom, 3857), 
        ST_SetSRID(g.geom, 3857)
    )
WHERE m.geom IS NOT NULL;
```

**Key Components:**
- **Spatial Join:** `JOIN ... ON ST_Intersects(...)`
- **Point Table:** `mods` (aliased as `m`)
- **Polygon Table:** `geology_master` (aliased as `g`)
- **Spatial Function:** `ST_Intersects` checks if point is inside polygon
- **SRID Handling:** `ST_SetSRID(geom, 3857)` ensures correct coordinate system

---

### Step 3: SQL Execution in PostGIS
**File:** `database/postgis_client.py`

The SQL is executed directly in PostGIS:

```python
results = db.execute_query(sql_query)
```

**What PostGIS Does:**
1. Uses spatial index (GIST) for fast lookup
2. Checks each point in `mods` table
3. Finds which polygons in `geology_master` contain each point
4. Returns matching records

**PostGIS Spatial Join Process:**
```
For each point in mods:
    For each polygon in geology_master:
        If ST_Intersects(point, polygon):
            Include this row in results
```

---

### Step 4: Results Returned

**Response Format:**
```json
{
    "success": true,
    "tool_used": "sql_query",
    "data": [
        {
            "gid": 123,
            "eng_name": "Gold Deposit Site A",
            "major_comm": "gold",
            "region": "Riyadh Region",
            "polygon_name": "Volcanic Formation",
            "latitude": 24.7136,
            "longitude": 46.6753
        },
        {
            "gid": 456,
            "eng_name": "Copper Mine B",
            "major_comm": "copper",
            "region": "Eastern Region",
            "polygon_name": "Igneous Rock Area",
            "latitude": 26.4207,
            "longitude": 50.0888
        }
        // ... more results
    ],
    "sql_query": "SELECT m.gid, m.eng_name, ... FROM mods m JOIN geology_master g ON ST_Intersects(...)",
    "row_count": 45,
    "description": "Points inside polygons"
}
```

---

## Alternative Query Examples

### Example 1: "Show boreholes inside volcanic areas"
**Generated SQL:**
```sql
SELECT 
    b.gid,
    b.project_na,
    b.borehole_i,
    g.unit_name AS geology_area,
    ST_Y(ST_Transform(ST_SetSRID(b.geom, 3857), 4326)) AS latitude,
    ST_X(ST_Transform(ST_SetSRID(b.geom, 3857), 4326)) AS longitude
FROM borholes b
JOIN geology_master g 
    ON ST_Intersects(
        ST_SetSRID(b.geom, 3857), 
        ST_SetSRID(g.geom, 3857)
    )
WHERE g.litho_fmly ILIKE '%volcanic%';
```

### Example 2: "Find all surface samples within sedimentary formations"
**Generated SQL:**
```sql
SELECT 
    s.gid,
    s.sampleid,
    s.sampletype,
    g.unit_name AS formation,
    ST_Y(ST_Transform(ST_SetSRID(s.geom, 3857), 4326)) AS latitude,
    ST_X(ST_Transform(ST_SetSRID(s.geom, 3857), 4326)) AS longitude
FROM surface_samples s
JOIN geology_master g 
    ON ST_Intersects(
        ST_SetSRID(s.geom, 3857), 
        ST_SetSRID(g.geom, 3857)
    )
WHERE g.main_litho ILIKE '%sedimentary%';
```

---

## Spatial Join Explanation

### What is ST_Intersects?
- **Function:** `ST_Intersects(geometry1, geometry2)`
- **Returns:** `true` if geometries intersect (point inside polygon)
- **Uses:** Spatial index for fast performance

### How It Works:
```
Point (24.7136, 46.6753) 
    ↓
Check if inside Polygon (geology_master.geom)
    ↓
ST_Intersects returns TRUE
    ↓
Row included in results
```

### Performance:
- PostGIS uses **GIST spatial index**
- Very fast even with millions of points
- Index automatically created on `geom` columns

---

## Complete API Request/Response

### Request:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me all points inside a polygon",
    "include_visualization": true
  }'
```

### Response:
```json
{
    "success": true,
    "tool_used": "sql_query",
    "data": [
        {
            "gid": 123,
            "eng_name": "Gold Deposit Site A",
            "major_comm": "gold",
            "region": "Riyadh Region",
            "polygon_name": "Volcanic Formation",
            "latitude": 24.7136,
            "longitude": 46.6753
        }
        // ... more results
    ],
    "visualization": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [46.6753, 24.7136]
                },
                "properties": {
                    "name": "Gold Deposit Site A",
                    "commodity": "gold"
                }
            }
        ]
    },
    "sql_query": "SELECT m.gid, m.eng_name, ... FROM mods m JOIN geology_master g ON ST_Intersects(...)",
    "row_count": 45
}
```

---

## Summary

✅ **Yes, the system:**
1. ✅ Generates SQL query using LLM
2. ✅ Uses spatial join (`ST_Intersects`) in PostGIS
3. ✅ Executes query in PostGIS database
4. ✅ Returns results with point coordinates
5. ✅ Can visualize on map

**The spatial join happens entirely in PostGIS** - the system leverages PostGIS's powerful spatial indexing and functions to efficiently find points inside polygons!
