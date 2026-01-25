# 🔍 Real Example: How "show gold deposits in riyadh and makkah regions" Gets Fixed

## Step-by-Step Code Execution

### User Query:
```
"show me all gold deposits in riyadh and makkah regions"
```

---

## Step 1: Query Preprocessing

**Function:** `_preprocess_query(query)`

**Code Location:** `tools/tool1_sql_generator.py:332`

```python
def _preprocess_query(self, query: str) -> str:
    query_lower = query.lower()
    
    # Fix misspellings (none in this case)
    # Map synonyms (none needed)
    # Add region hints
    
    return query  # Returns: "show me all gold deposits in riyadh and makkah regions"
```

**Result:** Query unchanged (no misspellings)

---

## Step 2: LLM Prompt Generation

**Function:** `_get_dynamic_schema_prompt()`

**Code Location:** `tools/tool1_sql_generator.py:618`

```python
# Gets actual database schema
schema_desc = """
TABLE: mods
- Columns: gid, eng_name, major_comm, minor_comm, region, ...
"""

# Builds prompt with:
# 1. Schema information
# 2. Rules: "NEVER use 'deposits' as table name"
# 3. Examples: Shows correct SQL patterns
# 4. Instructions: "Use ILIKE with wildcards for regions"
```

**Prompt sent to LLM includes:**
```
NEVER use table names like "deposits", "mines" - use "mods"
ALWAYS use ILIKE with wildcards: region ILIKE '%Riyadh%'

Example:
Query: "show gold deposits in makkah region"
SQL: SELECT ... FROM mods WHERE ... AND region ILIKE '%Makkah%';
```

---

## Step 3: LLM Generates SQL

**Function:** `generate_sql()`

**Code Location:** `tools/tool1_sql_generator.py:566`

```python
result = await self.ollama.generate_json(
    prompt=f'Generate SQL for: "{processed}"',
    system=dynamic_prompt,
    temperature=0.0
)

# LLM returns:
{
    "sql_query": "SELECT ... FROM mods WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') AND (region ILIKE 'Riyadh' OR region ILIKE 'Makkah');",
    ...
}
```

**Note:** LLM might generate `region ILIKE 'Riyadh'` (without wildcards)

---

## Step 4: Post-Processing (The Fix!)

**Function:** `_fix_sql(sql)`

**Code Location:** `tools/tool1_sql_generator.py:371`

### Fix 16: Region Wildcards

**Code:**
```python
# Fix 16: Normalize region names with wildcards
def add_region_wildcards(match):
    value = match.group(1)
    if '%' not in value and len(value.split()) == 1:
        return f"region ILIKE '%{value}%'"
    return match.group(0)

sql = re.sub(
    r"region\s+ILIKE\s+'([^']+)'",
    add_region_wildcards,
    sql,
    flags=re.IGNORECASE
)
```

**What happens:**
```python
# Input SQL:
"WHERE region ILIKE 'Riyadh' OR region ILIKE 'Makkah'"

# Regex finds: region ILIKE 'Riyadh'
# Function checks: '%' not in 'Riyadh'? Yes. Single word? Yes.
# Returns: "region ILIKE '%Riyadh%'"

# Regex finds: region ILIKE 'Makkah'
# Returns: "region ILIKE '%Makkah%'"

# Final SQL:
"WHERE region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%'"
```

---

## Complete Code Flow

```python
# 1. User query
query = "show me all gold deposits in riyadh and makkah regions"

# 2. Preprocessing
processed = self._preprocess_query(query)
# Result: "show me all gold deposits in riyadh and makkah regions"

# 3. Get dynamic schema prompt
dynamic_prompt = self._get_dynamic_schema_prompt()
# Result: Prompt with schema, rules, examples

# 4. LLM generates SQL
result = await self.ollama.generate_json(
    prompt=f'Generate SQL for: "{processed}"',
    system=dynamic_prompt
)
sql = result["sql_query"]
# Result: "SELECT ... FROM mods WHERE ... AND (region ILIKE 'Riyadh' OR region ILIKE 'Makkah');"

# 5. Post-processing fixes
sql = self._fix_sql(sql)
# Fix 16 runs:
#   - Finds: region ILIKE 'Riyadh'
#   - Replaces: region ILIKE '%Riyadh%'
#   - Finds: region ILIKE 'Makkah'
#   - Replaces: region ILIKE '%Makkah%'
# Final: "SELECT ... FROM mods WHERE ... AND (region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%');"

# 6. Execute
results = self.db.execute_query(sql)
```

---

## All Post-Processing Fixes

### Fix 1: Wrong Table Names
```python
# Pattern matching
sql = re.sub(r'\bFROM\s+deposits\b', 'FROM mods', sql)
# "FROM deposits" → "FROM mods"
```

### Fix 2: Operator Precedence
```python
# Finds WHERE clause
where_match = re.search(r'WHERE\s+(.+?)(?:\s*;|\s*$)', sql)
# Splits by AND
parts = re.split(r'\s+AND\s+', where_clause)
# Wraps OR in parentheses
if ' OR ' in first_part:
    first_part = f"({first_part})"
```

### Fix 3: Case Sensitivity
```python
# Regex replacement
sql = re.sub(r"(\w+)\s*=\s*'([^']+)'", r"\1 ILIKE '\2'", sql)
# "region = 'Makkah'" → "region ILIKE 'Makkah'"
```

### Fix 4: Region Wildcards
```python
# Function-based replacement
def add_wildcards(match):
    value = match.group(1)
    if '%' not in value and len(value.split()) == 1:
        return f"region ILIKE '%{value}%'"
    return match.group(0)

sql = re.sub(r"region\s+ILIKE\s+'([^']+)'", add_wildcards, sql)
# "region ILIKE 'Riyadh'" → "region ILIKE '%Riyadh%'"
```

### Fix 5: Invalid Columns
```python
# Remove non-existent columns
sql = re.sub(r'\b(structural|structure)\s+(ILIKE|LIKE|=)\s+[^)]+', '', sql)
# "WHERE structural ILIKE '%...%'" → "WHERE"
# Then cleanup: "WHERE AND" → "WHERE"
```

### Fix 6: Table Aliases
```python
# Check if alias needed
if re.search(r'\bm\.\w+', sql):  # Using m. prefix?
    if not re.search(r'FROM\s+mods\s+m\b', sql):  # Alias missing?
        sql = re.sub(r'FROM\s+mods\b', 'FROM mods m', sql)
# "FROM mods" + "m.eng_name" → "FROM mods m" + "m.eng_name"
```

---

## Why This Works

### ✅ Regex Pattern Matching
- Finds specific patterns in SQL
- Replaces them with correct versions
- Works even if LLM makes mistakes

### ✅ Function-Based Logic
- Can check conditions (e.g., "has wildcards?")
- Can make decisions (e.g., "add wildcards if single word")
- More flexible than simple replacement

### ✅ Multiple Passes
- Each fix runs in sequence
- Later fixes can clean up earlier ones
- Comprehensive coverage

### ✅ Safety Net
- Even if LLM generates wrong SQL
- Post-processor fixes it automatically
- No manual intervention needed

---

## Real Example Trace

### Input:
```
Query: "show me all gold deposits in riyadh and makkah regions"
```

### After Preprocessing:
```
"show me all gold deposits in riyadh and makkah regions"
(no changes)
```

### LLM Generates:
```sql
SELECT gid, eng_name, major_comm, region, occ_imp, 
       ST_Y(...) AS latitude, ST_X(...) AS longitude 
FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE 'Riyadh' OR region ILIKE 'Makkah');
```

### Post-Processor Runs:

**Fix 16 - Region Wildcards:**
```python
# Finds: region ILIKE 'Riyadh'
# Pattern: r"region\s+ILIKE\s+'([^']+)'"
# Match: 'Riyadh'
# Check: '%' not in 'Riyadh'? Yes. Single word? Yes.
# Replace: region ILIKE '%Riyadh%'

# Finds: region ILIKE 'Makkah'
# Replace: region ILIKE '%Makkah%'
```

**Final SQL:**
```sql
SELECT gid, eng_name, major_comm, region, occ_imp, 
       ST_Y(...) AS latitude, ST_X(...) AS longitude 
FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%');
```

**Result:** ✅ Works! Matches "Riyadh Region" and "Makkah Region"

---

## Summary

**I fix problems using:**

1. **Regex Pattern Matching** - Finds and replaces specific patterns
2. **Function-Based Logic** - Makes decisions (e.g., add wildcards if needed)
3. **Multiple Fixes** - Each fix handles a specific issue
4. **Sequential Processing** - Fixes run in order, each building on previous

**The post-processor is like a spell-checker for SQL** - it automatically fixes common mistakes! 🛡️
