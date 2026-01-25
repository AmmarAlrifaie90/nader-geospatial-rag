# Polygon and Line Display Fix

## Problem
Polygons and lines were not showing on the map, even though they worked in the old version.

## Root Cause
The `query_type` parameter was not being passed from the SQL generator result to the `prepare_visualization` method in `main.py`. This caused the visualizer to default to "point" geometry type, even when the query returned polygons or lines.

## Solution

### 1. Pass `query_type` to Visualizer
**File:** `geospatial-rag/backend/main.py`

**Changes:**
- Updated `_handle_sql_query` to pass `query_type` to `prepare_visualization`
- Updated `_handle_2d_visualization` to pass `query_type` to `prepare_visualization`

**Before:**
```python
visualization = viz.prepare_visualization(result["data"])
```

**After:**
```python
visualization = viz.prepare_visualization(
    result["data"],
    query_type=result.get("query_type")
)
```

### 2. Enhanced Geometry Type Detection
**File:** `geospatial-rag/backend/tools/tool2_visualizer_2d.py`

**Changes:**
- Improved `_detect_geometry_type` method with better logging
- Added fallback logic when `geojson_geom` exists but can't be parsed
- Priority order:
  1. `query_type` parameter (highest priority)
  2. Parse `geojson_geom` column
  3. Check table name hints
  4. Check for `latitude`/`longitude` columns
  5. Default to "point"

**Key Improvements:**
- Added logging to track detection decisions
- Better error handling for malformed GeoJSON
- Fallback to polygon if `geojson_geom` exists but is unparseable

## How It Works

1. **SQL Generation:**
   - LLM generates SQL with `query_type` set to "polygon" or "line" for geometry tables
   - Post-processor ensures `geojson_geom` column is included (Fix 0b, Fix 0c)

2. **Query Execution:**
   - SQL is executed and returns results with `geojson_geom` column
   - `query_type` is included in the result dictionary

3. **Visualization:**
   - `main.py` passes `query_type` to `prepare_visualization`
   - Visualizer uses `query_type` to determine geometry type
   - If `query_type` is missing, falls back to parsing `geojson_geom`
   - Builds appropriate GeoJSON (polygon/line/point)

4. **Map Display:**
   - Frontend receives GeoJSON with correct geometry type
   - Map renders polygons and lines correctly

## Testing

Test with these queries:
- "show me all geological areas" → Should show polygons
- "show me all faults" → Should show lines
- "show me all gold deposits" → Should show points

All should now display correctly on the map!

## Files Modified

1. `geospatial-rag/backend/main.py`
   - Lines 238-240: Pass `query_type` in `_handle_sql_query`
   - Lines 267-269: Pass `query_type` in `_handle_2d_visualization`

2. `geospatial-rag/backend/tools/tool2_visualizer_2d.py`
   - Lines 51-95: Enhanced `_detect_geometry_type` method

## Notes

- The SQL generator already includes `geojson_geom` in queries for polygons and lines (Fix 0b, Fix 0c)
- The visualizer already had logic to handle polygons and lines
- The only missing piece was passing `query_type` from the SQL result to the visualizer
- This fix ensures polygons and lines display correctly on the map
