# Fix: Invented Table Names (e.g., "gold_deposits")

## Problem
The LLM was generating SQL with invented table names like `gold_deposits`, `copper_mines`, etc., which don't exist in the database. The actual table name is `mods`.

**Error Example:**
```sql
SELECT * FROM gold_deposits WHERE region IN ('Riyadh', 'Makkah')
-- Error: relation "gold_deposits" does not exist
```

## Root Cause
Even though the schema is provided to the LLM dynamically, it sometimes invents compound table names based on the query (e.g., "gold deposits" → `gold_deposits` table).

## Solution: Multi-Layer Fix

### Layer 1: Enhanced Prompt (Prevention)
Updated `SYSTEM_PROMPT` to be more explicit:
- Added: `NEVER invent compound table names like "gold_deposits", "mining_sites", "copper_deposits" - these DO NOT EXIST`
- Added: `CRITICAL: If user says "gold deposits", use table "mods" (NOT "gold_deposits", NOT "deposits")`
- Updated example to show correct thinking process

### Layer 2: Post-Processor Fixes (Correction)

**Fix 1a:** Basic table name replacements
- `deposits` → `mods`
- `mines` → `mods`
- `sites` → `mods`

**Fix 1b:** Compound table names (NEW)
Catches patterns like:
- `FROM gold_deposits` → `FROM mods`
- `FROM copper_mines` → `FROM mods`
- `FROM mining_sites` → `FROM mods`
- `FROM deposits_gold` → `FROM mods`

**Fix 1c:** Generic safety net (NEW)
- Scans all `FROM`/`JOIN` clauses
- If table name is not in allowed list AND contains keywords like "deposit", "mine", "site" → replaces with `mods`
- If contains "fault", "line" → replaces with `geology_faults_contacts_master`
- If contains "geology", "area" → replaces with `geology_master`

## How It Works

### Example: "show me all gold deposits in riyadh region and makkah region"

**LLM might generate (wrong):**
```sql
SELECT * FROM gold_deposits WHERE region IN ('Riyadh', 'Makkah')
```

**Post-processor fixes:**

**Fix 1b catches it:**
```python
# Pattern: FROM gold_deposits
# Matches: r'(FROM|JOIN)\s+\w+_deposits\b'
# Replaces: FROM mods
```

**Fix 1c also catches it (backup):**
```python
# Finds: FROM gold_deposits
# Checks: 'gold_deposits' not in allowed_tables? Yes
# Checks: 'deposit' in 'gold_deposits'? Yes
# Replaces: FROM mods
```

**Final SQL (fixed):**
```sql
SELECT gid, eng_name, major_comm, region, occ_imp, 
       ST_Y(...) AS latitude, ST_X(...) AS longitude 
FROM mods 
WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') 
  AND (region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%')
```

## Schema Learning
The system DOES know the schema:
- `schema_learner.py` queries `information_schema` to get actual table names
- `_get_dynamic_schema_prompt()` injects the learned schema into the prompt
- The prompt explicitly lists: `mods, borholes, surface_samples, geology_master, geology_faults_contacts_master`

However, LLMs can still make mistakes, so the post-processor acts as a safety net.

## Testing
After restarting the server, test:
- "show me all gold deposits in riyadh region and makkah region" ✅
- "show me all copper mines" ✅
- "show me all mining sites" ✅

All should use `mods` table, not invented table names.
