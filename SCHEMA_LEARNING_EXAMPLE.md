# Schema Learning & Synonym Handling Example

## Problem Solved

**Before:** System had hardcoded schema, couldn't handle synonyms like "area" → "terrane"

**After:** System dynamically learns schema from database and handles synonyms automatically!

---

## Example: "Show me points in areas with terrane = 'X'"

### User Query
```
"Show me all gold deposits in areas where terrane is 'Arabian Shield'"
```

**OR user might say:**
```
"Show me all gold deposits in areas where area is 'Arabian Shield'"
```

Both should work! The system maps "area" → "terrane" automatically.

---

## Step-by-Step Process

### Step 1: Schema Learning (Automatic)
**File:** `tools/schema_learner.py`

When the system starts, it:
1. Queries PostGIS `information_schema` to get all tables
2. Gets column names, types, and geometry info
3. Builds synonym map:
   ```python
   {
       "area": "terrane",
       "areas": "terrane",
       "zone": "terrane",
       "formation": "unit_name",
       "mineral": "major_comm",
       # ... more mappings
   }
   ```

### Step 2: Query Preprocessing
**File:** `tools/tool1_sql_generator.py`

User query: `"gold deposits in areas where area is 'Arabian Shield'"`

System preprocesses:
- Detects "area" → maps to "terrane (column: terrane)"
- Adds hint: `"gold deposits in areas where area (column: terrane) is 'Arabian Shield'"`

### Step 3: Dynamic Schema Prompt
The LLM receives:
```
DATABASE SCHEMA (Learned from actual database):

TABLE: geology_master
- Type: POLYGON
- Row count: 1234
- Columns:
  - gid: integer
  - unit_name: character varying
  - main_litho: character varying
  - terrane: character varying  ← ACTUAL COLUMN NAME
  - geom: geometry

COLUMN SYNONYMS:
- 'area' → terrane
- 'areas' → terrane
- 'formation' → unit_name
- 'mineral' → major_comm
```

### Step 4: SQL Generation
LLM generates:
```sql
SELECT 
    m.gid, 
    m.eng_name, 
    m.major_comm,
    g.terrane,  ← Correctly uses 'terrane' not 'area'
    ST_Y(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS latitude,
    ST_X(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS longitude
FROM mods m
JOIN geology_master g 
    ON ST_Intersects(
        ST_SetSRID(m.geom, 3857), 
        ST_SetSRID(g.geom, 3857)
    )
WHERE (m.major_comm ILIKE '%gold%' OR m.minor_comm ILIKE '%gold%')
  AND g.terrane = 'Arabian Shield';  ← Correct column!
```

### Step 5: Post-Processing (Safety Net)
Even if LLM makes a mistake, post-processor fixes:
- `g.area` → `g.terrane`
- `WHERE area =` → `WHERE terrane =`

---

## More Examples

### Example 1: "Show deposits in formations"
**User says:** "Show me copper deposits in sedimentary formations"

**System maps:**
- "formations" → "unit_name"
- "deposits" → "mods" table

**Generated SQL:**
```sql
SELECT m.gid, m.eng_name, m.major_comm, g.unit_name AS formation
FROM mods m
JOIN geology_master g 
    ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))
WHERE m.major_comm ILIKE '%copper%'
  AND g.main_litho ILIKE '%sedimentary%';
```

### Example 2: "Find minerals near faults"
**User says:** "Find all minerals near fault lines"

**System maps:**
- "minerals" → "major_comm" column
- "fault lines" → "geology_faults_contacts_master" table

**Generated SQL:**
```sql
SELECT DISTINCT m.gid, m.eng_name, m.major_comm, f.newtype
FROM mods m
JOIN geology_faults_contacts_master f 
    ON ST_DWithin(
        ST_SetSRID(m.geom, 3857), 
        ST_SetSRID(f.geom, 3857), 
        10000
    )
WHERE f.newtype ILIKE '%fault%';
```

### Example 3: "Boreholes in zones"
**User says:** "Show boreholes in volcanic zones"

**System maps:**
- "zones" → "terrane" (via synonym)
- "boreholes" → "borholes" table

**Generated SQL:**
```sql
SELECT b.gid, b.project_na, b.borehole_i, g.terrane AS zone
FROM borholes b
JOIN geology_master g 
    ON ST_Intersects(ST_SetSRID(b.geom, 3857), ST_SetSRID(g.geom, 3857))
WHERE g.litho_fmly ILIKE '%volcanic%';
```

---

## Key Features

### ✅ Dynamic Schema Learning
- Queries actual database schema
- No hardcoded tables/columns
- Adapts to schema changes automatically

### ✅ Synonym Mapping
- "area" → "terrane"
- "formation" → "unit_name"
- "mineral" → "major_comm"
- Learns from actual data values

### ✅ Handles ANY Spatial Join
- Points in polygons: `ST_Intersects`
- Points near lines: `ST_DWithin`
- Points within distance: `ST_DWithin`
- Any combination of tables

### ✅ Flexible Column Names
- User can say "area", "zone", "terrane" → all map to `terrane` column
- User can say "formation", "unit" → maps to `unit_name`
- System learns from context

---

## How It Works Technically

### 1. Schema Learning
```python
schema_learner = get_schema_learner()
schema = schema_learner.learn_schema()  # Queries PostGIS
```

### 2. Synonym Building
```python
synonym_map = schema_learner.build_synonym_map()
# {
#     "area": "terrane",
#     "areas": "terrane",
#     "formation": "unit_name",
#     ...
# }
```

### 3. Query Enhancement
```python
column = schema_learner.get_column_for_term("area", "geology_master")
# Returns: "terrane"
```

### 4. SQL Generation
- LLM receives dynamic schema (not hardcoded)
- LLM receives synonym mappings
- LLM generates SQL with correct column names
- Post-processor fixes any remaining issues

---

## Testing

### Test Query 1: Synonym Handling
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show gold deposits in areas where area is Arabian Shield"
  }'
```

**Expected:** Uses `terrane` column, not `area`

### Test Query 2: Dynamic Schema
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show all points inside polygons"
  }'
```

**Expected:** Works with ANY point/polygon tables in database

### Test Query 3: Complex Spatial Join
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find boreholes in volcanic formations near fault lines"
  }'
```

**Expected:** Creates multi-table spatial join automatically

---

## Summary

✅ **System can now:**
1. Learn database schema dynamically
2. Handle synonyms (area → terrane)
3. Handle ANY spatial join question
4. Adapt to schema changes
5. Work with any column names

**The system is now truly flexible and learns from your actual database!** 🎉
