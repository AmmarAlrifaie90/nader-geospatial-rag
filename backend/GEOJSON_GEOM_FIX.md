# GeoJSON Geometry Fix for Map Display

## Problem
Queries like "show me all areas" and "show me all faults" were returning data but nothing was showing on the map.

**Example problematic queries:**
- `SELECT terrane FROM geology_master` - Missing `geojson_geom`
- `SELECT * FROM geology_faults_contacts_master` - Should include `geojson_geom` but wasn't

## Root Cause
The LLM was generating SQL queries that:
1. Selected specific columns but forgot to include `geojson_geom`
2. Used `SELECT *` which was being fixed, but the fix wasn't comprehensive enough

Without `geojson_geom`, the frontend has no geometry data to display on the map.

## Solution

### Added Two New Post-Processor Fixes

**Fix 0d: Ensure `geojson_geom` for `geology_master` (polygons)**
- Detects when `geology_master` is queried but `geojson_geom` is missing
- Automatically adds `ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom`
- Handles both aliased and non-aliased table references

**Fix 0e: Ensure `geojson_geom` for `geology_faults_contacts_master` (lines)**
- Detects when `geology_faults_contacts_master` is queried but `geojson_geom` is missing
- Automatically adds `ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom`
- Handles both aliased and non-aliased table references

## How It Works

1. **Detection:** After SQL generation, the post-processor checks:
   - Is `geology_master` or `geology_faults_contacts_master` in the FROM clause?
   - Is `geojson_geom` missing from the SELECT clause?

2. **Injection:** If both conditions are true:
   - Finds the position of the FROM clause
   - Inserts `, ST_AsGeoJSON(...) AS geojson_geom` before FROM
   - Handles table aliases correctly (e.g., `g.geom` if table is aliased as `g`)

3. **Result:** The SQL now includes `geojson_geom`, which the visualizer can use to build GeoJSON for map display.

## Examples

### Before Fix:
```sql
SELECT terrane FROM geology_master
```

### After Fix:
```sql
SELECT terrane, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_master
```

### Before Fix:
```sql
SELECT * FROM geology_faults_contacts_master
```

### After Fix (by Fix 0c):
```sql
SELECT gid, newtype, shape_leng, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_faults_contacts_master
```

## Testing

Test with these queries:
- "show me all areas" → Should show polygons on map
- "show me all faults" → Should show lines on map
- "show me all geological areas" → Should show polygons on map

All should now display correctly on the map!

## Files Modified

1. `geospatial-rag/backend/tools/tool1_sql_generator.py`
   - Lines 907-960: Added Fix 0d and Fix 0e

## Related Fixes

- **Fix 0b:** Handles `SELECT *` for `geology_master` (polygons)
- **Fix 0c:** Handles `SELECT *` for `geology_faults_contacts_master` (lines)
- **Fix 0d:** Ensures `geojson_geom` for `geology_master` (new)
- **Fix 0e:** Ensures `geojson_geom` for `geology_faults_contacts_master` (new)

These fixes work together to ensure geometry is always included for map visualization.
