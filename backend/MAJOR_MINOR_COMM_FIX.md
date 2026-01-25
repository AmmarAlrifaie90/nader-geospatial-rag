# Fix: AND vs OR Between major_comm and minor_comm

## Problem

The LLM was generating incorrect SQL using `AND` between `major_comm` and `minor_comm` when it should use `OR`.

### Incorrect SQL (WRONG):
```sql
SELECT * FROM mods 
WHERE major_comm ILIKE '%silver%' AND minor_comm ILIKE '%silver%' 
AND region ILIKE '%Makkah%';
```

**Problem:** This requires BOTH `major_comm` AND `minor_comm` to contain "silver", which is too restrictive. A commodity appears in EITHER `major_comm` OR `minor_comm`, not both. This would return 0 results.

### Correct SQL (CORRECT):
```sql
SELECT gid, eng_name, major_comm, minor_comm, region, occ_imp, 
       ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, 
       ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude 
FROM mods 
WHERE (major_comm ILIKE '%silver%' OR minor_comm ILIKE '%silver%') 
AND region ILIKE '%Makkah%';
```

**Solution:** Use `OR` to find records where EITHER `major_comm` OR `minor_comm` contains the commodity.

## Why This Matters

- A commodity can be in **EITHER** `major_comm` **OR** `minor_comm`, not both
- Using `AND` requires both columns to match, which is logically incorrect
- This causes queries to return 0 results even when data exists

## Fixes Applied

### 1. Enhanced SYSTEM_PROMPT Rules

Added explicit rules in multiple places:

**In Decision Hierarchy (STEP 5):**
```
- Commodity condition → (major_comm ILIKE '%commodity%' OR minor_comm ILIKE '%commodity%')
  * CRITICAL: ALWAYS use OR between major_comm and minor_comm, NEVER use AND
  * WRONG: major_comm ILIKE '%silver%' AND minor_comm ILIKE '%silver%' (too restrictive)
  * CORRECT: (major_comm ILIKE '%silver%' OR minor_comm ILIKE '%silver%')
```

**In Validation Checklist:**
```
- [ ] CRITICAL: For commodities, did I use OR between major_comm and minor_comm? (NEVER use AND)
  - WRONG: major_comm ILIKE '%silver%' AND minor_comm ILIKE '%silver%'
  - CORRECT: (major_comm ILIKE '%silver%' OR minor_comm ILIKE '%silver%')
```

**In Hard Constraints:**
```
- CRITICAL RULE: ALWAYS use OR between major_comm and minor_comm, NEVER use AND
  * WRONG: major_comm ILIKE '%silver%' AND minor_comm ILIKE '%silver%' (too restrictive)
  * CORRECT: (major_comm ILIKE '%silver%' OR minor_comm ILIKE '%silver%')
  * Reason: A commodity appears in EITHER major_comm OR minor_comm, not both.
```

### 2. Post-Processor Fix (Fix 21)

Added automatic correction in `_fix_sql()` method:

```python
# Fix 21: CRITICAL - Fix AND between major_comm and minor_comm (should be OR)
# Pattern: major_comm ILIKE '%X%' AND minor_comm ILIKE '%X%' → (major_comm ILIKE '%X%' OR minor_comm ILIKE '%X%')
and_comm_pattern = re.compile(
    r"major_comm\s+ILIKE\s+('[^']+')\s+AND\s+minor_comm\s+ILIKE\s+\1",
    re.IGNORECASE
)

def replace_and_with_or(match):
    """Replace AND with OR and wrap in parentheses."""
    commodity_pattern = match.group(1)  # e.g., '%silver%'
    replacement = f"(major_comm ILIKE {commodity_pattern} OR minor_comm ILIKE {commodity_pattern})"
    logger.warning(f"Fixed AND to OR between major_comm and minor_comm")
    return replacement

sql = and_comm_pattern.sub(replace_and_with_or, sql)
```

**How it works:**
- Detects pattern: `major_comm ILIKE '%commodity%' AND minor_comm ILIKE '%commodity%'`
- Replaces with: `(major_comm ILIKE '%commodity%' OR minor_comm ILIKE '%commodity%')`
- Logs a warning for monitoring

## Testing

Test with queries like:
- "show me all silver deposits in makkah region"
- "find gold deposits"
- "show copper occurrences"

**Expected behavior:**
- SQL should use `OR` between `major_comm` and `minor_comm`
- If LLM generates `AND`, post-processor automatically fixes it
- Results should include all records where commodity appears in either column

## Prevention

This fix prevents the issue through:
1. **Explicit prompt rules** - Multiple warnings in SYSTEM_PROMPT
2. **Validation checklist** - LLM must check this before generating SQL
3. **Post-processor safety net** - Automatically fixes if LLM makes mistake
4. **All examples use OR** - Training examples show correct pattern

## Related Issues

This is similar to other logical errors:
- Using `=` instead of `ILIKE` for case-insensitive matching
- Missing parentheses around `OR` conditions when combined with `AND`
- Using `occ_type` instead of `major_comm`/`minor_comm` for commodities

All of these have been fixed with similar multi-layered approaches.
