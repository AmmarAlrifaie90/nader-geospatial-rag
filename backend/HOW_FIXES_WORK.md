# 🔧 How The Fixes Work - Technical Explanation

## Multi-Layered Defense System

I use **4 layers** to fix problems:

```
User Query
    ↓
Layer 1: Query Preprocessing (fixes user input)
    ↓
Layer 2: LLM Prompt (teaches LLM correct patterns)
    ↓
Layer 3: LLM Generates SQL
    ↓
Layer 4: Post-Processing (fixes SQL mistakes)
    ↓
Final SQL → Database
```

---

## Layer 1: Query Preprocessing

**File:** `tools/tool1_sql_generator.py` → `_preprocess_query()`

**What it does:** Fixes the user's query BEFORE sending to LLM

**Example:**
```python
User says: "show me all areas that consider Volcanos terrain"

Preprocessing:
1. "Volcanos" → "volcanic" (misspelling fix)
2. "terrain" → "terrane" (synonym fix)
3. Adds hints: "areas (column: terrane)"

Result sent to LLM:
"show me all areas (column: terrane) that consider volcanic terrane"
```

**Code:**
```python
def _preprocess_query(self, query: str) -> str:
    # Fix misspellings
    misspellings = {
        "volcanos": "volcanic",
        "terrain": "terrane",
    }
    for misspelled, correct in misspellings.items():
        query = re.sub(rf'\b{misspelled}\b', correct, query, flags=re.IGNORECASE)
    
    # Map synonyms
    synonym_map = self.schema_learner.build_synonym_map()
    for synonym, column in synonym_map.items():
        if synonym in query_lower:
            query = query.replace(synonym, f"{synonym} (column: {column})")
    
    return query
```

---

## Layer 2: Enhanced LLM Prompt

**File:** `tools/tool1_sql_generator.py` → `SYSTEM_PROMPT` and `_get_dynamic_schema_prompt()`

**What it does:** Teaches the LLM correct patterns with:
1. **Explicit rules** (NEVER use "deposits" as table name)
2. **Examples** (shows correct SQL patterns)
3. **Dynamic schema** (learns actual database structure)

**Example - Table Name Fix:**
```python
SYSTEM_PROMPT = """
NEVER use table names like "deposits", "mines", "sites" - these DO NOT EXIST
ONLY use these exact table names: mods, borholes, surface_samples, ...
- For deposits, mines, minerals, gold, copper → use table "mods"

Query: "show gold deposits"
{
    "thinking": "User says 'deposits' but table name is 'mods'. NEVER use 'deposits' as table name.",
    "sql_query": "SELECT ... FROM mods WHERE ..."
}
"""
```

**Example - Region Fix:**
```python
STRING COMPARISONS:
- ALWAYS use ILIKE instead of = for text comparisons
- Example: region ILIKE 'Makkah' (not region = 'Makkah')
- Region names include 'Region' suffix, so use wildcards: region ILIKE '%Makkah%'
```

---

## Layer 3: LLM Generates SQL

The LLM (Qwen 2.5 7B) generates SQL based on:
- Preprocessed query (with hints)
- Enhanced prompt (with rules and examples)
- Dynamic schema (actual database structure)

**Example:**
```
Input: "show gold deposits in riyadh and makkah regions"
    ↓
LLM generates:
SELECT ... FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE 'Riyadh' OR region ILIKE 'Makkah')
```

---

## Layer 4: Post-Processing (The Safety Net)

**File:** `tools/tool1_sql_generator.py` → `_fix_sql()`

**What it does:** Automatically fixes SQL mistakes using regex patterns

### Fix 1: Wrong Table Names
```python
# Pattern: FROM deposits → FROM mods
sql = re.sub(r'\bFROM\s+deposits\b', 'FROM mods', sql, flags=re.IGNORECASE)
sql = re.sub(r'\bFROM\s+mines\b', 'FROM mods', sql, flags=re.IGNORECASE)
```

**Example:**
```sql
-- LLM generates (wrong):
SELECT * FROM deposits WHERE ...

-- Post-processor fixes:
SELECT * FROM mods WHERE ...
```

### Fix 2: Region Wildcards
```python
# Pattern: region ILIKE 'Riyadh' → region ILIKE '%Riyadh%'
def add_region_wildcards(match):
    value = match.group(1)
    if '%' not in value and len(value.split()) == 1:
        return f"region ILIKE '%{value}%'"
    return match.group(0)

sql = re.sub(r"region\s+ILIKE\s+'([^']+)'", add_region_wildcards, sql)
```

**Example:**
```sql
-- LLM generates (wrong):
WHERE region ILIKE 'Riyadh' OR region ILIKE 'Makkah'

-- Post-processor fixes:
WHERE region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%'
```

### Fix 3: Operator Precedence
```python
# Pattern: condition1 OR condition2 AND condition3
# Should be: (condition1 OR condition2) AND condition3

if ' OR ' in sql.upper() and ' AND ' in sql.upper():
    where_match = re.search(r'WHERE\s+(.+?)(?:\s*;|\s*$)', sql)
    if where_match:
        where_clause = where_match.group(1)
        parts = re.split(r'\s+AND\s+', where_clause)
        if len(parts) > 1:
            first_part = parts[0].strip()
            if ' OR ' in first_part and not first_part.startswith('('):
                first_part = f"({first_part})"
                where_clause_fixed = ' AND '.join([first_part] + parts[1:])
                sql = sql[:where_match.start(1)] + where_clause_fixed + sql[where_match.end(1):]
```

**Example:**
```sql
-- LLM generates (wrong):
WHERE major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%' AND region ILIKE 'Makkah'

-- Post-processor fixes:
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') AND region ILIKE '%Makkah%'
```

### Fix 4: Case Sensitivity
```python
# Pattern: column = 'value' → column ILIKE 'value'
sql = re.sub(
    r"(\w+\.?\w*)\s*=\s*'([^']+)'",
    r"\1 ILIKE '\2'",
    sql,
    flags=re.IGNORECASE
)
```

**Example:**
```sql
-- LLM generates (wrong):
WHERE region = 'Makkah'

-- Post-processor fixes:
WHERE region ILIKE '%Makkah%'
```

### Fix 5: Remove Invalid Columns
```python
# Pattern: structural ILIKE '...' → (removed)
sql = re.sub(
    r'\b(structural|structure)\s+(ILIKE|LIKE|=)\s+[^)]+',
    '',
    sql,
    flags=re.IGNORECASE
)

# Clean up double AND/OR
sql = re.sub(r'\s+AND\s+AND\s+', ' AND ', sql)
sql = re.sub(r'WHERE\s+AND\s+', 'WHERE ', sql)
```

**Example:**
```sql
-- LLM generates (wrong):
WHERE structural ILIKE '%...%' AND ...

-- Post-processor fixes:
WHERE ...
```

### Fix 6: Table Aliases
```python
# Pattern: If using m.eng_name but no alias defined, add it
if 'FROM mods' in sql.upper():
    if re.search(r'\bm\.\w+', sql):  # Using m. prefix
        if not re.search(r'FROM\s+mods\s+m\b', sql):
            sql = re.sub(r'FROM\s+mods\b', 'FROM mods m', sql)
```

**Example:**
```sql
-- LLM generates (wrong):
FROM mods JOIN ...
SELECT m.eng_name ...  -- Error: alias 'm' not defined

-- Post-processor fixes:
FROM mods m JOIN ...
SELECT m.eng_name ...  -- Works!
```

---

## Complete Flow Example

### User Query:
```
"show me all gold deposits in riyadh and makkah regions"
```

### Step 1: Preprocessing
```python
Query: "show me all gold deposits in riyadh and makkah regions"
# No misspellings to fix
# No synonyms to map
# Returns as-is
```

### Step 2: LLM Prompt
```python
Prompt includes:
- "NEVER use 'deposits' as table name, use 'mods'"
- "Use ILIKE with wildcards for regions"
- Example: "show gold deposits in makkah region" → correct SQL
```

### Step 3: LLM Generates SQL
```sql
SELECT gid, eng_name, major_comm, region, occ_imp, 
       ST_Y(...) AS latitude, ST_X(...) AS longitude 
FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE 'Riyadh' OR region ILIKE 'Makkah');
```

### Step 4: Post-Processing
```python
# Fix 16: Add wildcards to regions
region ILIKE 'Riyadh' → region ILIKE '%Riyadh%'
region ILIKE 'Makkah' → region ILIKE '%Makkah%'

# Final SQL:
SELECT ... FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%');
```

---

## Why This Approach?

### ✅ Defense in Depth
- If LLM makes mistake → Post-processor fixes it
- If post-processor misses → Schema learning catches it
- Multiple safety nets

### ✅ Handles Edge Cases
- Misspellings → Preprocessing fixes
- Wrong table names → Post-processor fixes
- Operator precedence → Post-processor fixes
- Case sensitivity → Post-processor fixes

### ✅ Learns from Database
- Schema learner queries actual database
- Knows real column names
- Adapts to changes

---

## Code Locations

| Layer | File | Function |
|-------|------|----------|
| Preprocessing | `tools/tool1_sql_generator.py` | `_preprocess_query()` |
| Prompt | `tools/tool1_sql_generator.py` | `SYSTEM_PROMPT`, `_get_dynamic_schema_prompt()` |
| LLM | `llm/ollama_client.py` | `generate_json()` |
| Post-processing | `tools/tool1_sql_generator.py` | `_fix_sql()` |
| Schema Learning | `tools/schema_learner.py` | `learn_schema()`, `build_synonym_map()` |

---

## Summary

**I fix problems using 4 layers:**

1. **Preprocessing** - Fixes user input (misspellings, synonyms)
2. **Enhanced Prompt** - Teaches LLM correct patterns
3. **LLM Generation** - Generates SQL (with guidance)
4. **Post-Processing** - Automatically fixes SQL mistakes (regex patterns)

**This creates a robust system that:**
- Handles misspellings
- Fixes wrong table names
- Corrects operator precedence
- Adds wildcards for regions
- Removes invalid columns
- Ensures table aliases are correct

**The post-processor is the safety net** - even if the LLM makes mistakes, the post-processor fixes them automatically! 🛡️
