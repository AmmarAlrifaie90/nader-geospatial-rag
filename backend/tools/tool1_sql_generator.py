"""
=============================================================================
GEOSPATIAL RAG - SQL GENERATOR (IMPROVED VERSION)
=============================================================================
Key Improvements:
1. Cleaner prompt structure with clear separation of concerns
2. Explicit "DO" and "DON'T" sections for clarity
3. Decision tree for query routing
4. Consolidated schema reference (single source of truth)
5. Better semantic understanding guidance
6. Reduced redundancy and cognitive load on LLM
7. More effective few-shot examples with reasoning chains
=============================================================================
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List

from llm.ollama_client import get_ollama_client
from database.postgis_client import get_postgis_client

logger = logging.getLogger(__name__)

# =============================================================================
# REGION MAPPINGS
# =============================================================================
SAUDI_REGIONS = {
    "riyadh": "Riyadh Region", "makkah": "Makkah Region", "mecca": "Makkah Region",
    "madinah": "Madinah Region", "medina": "Madinah Region", "eastern": "Eastern Region",
    "asir": "Asir Region", "tabuk": "Tabuk Region", "hail": "Hail Region",
    "jazan": "Jazan Region", "najran": "Najran Region", "qassim": "Qassim Region"
}

# =============================================================================
# IMPROVED SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT_TEMPLATE = """You are a PostGIS SQL generator for Saudi Arabia mining/geology data.

═══════════════════════════════════════════════════════════════════════════════
SCHEMA REFERENCE (USE EXACTLY THESE NAMES)
═══════════════════════════════════════════════════════════════════════════════

TABLE: mods (POINT)
├─ Purpose: Mineral deposits, mines, occurrences
├─ Columns: gid, eng_name, arb_name, major_comm, minor_comm, region, occ_imp, occ_type, occ_status, structural, host_rocks, alteration, min_morpho, trace_comm, geom
├─ Output: ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude
└─ query_type: "point"

TABLE: geology_master (POLYGON)
├─ Purpose: Geological areas, terranes, rock units
├─ Columns: gid, unit_name, main_litho, litho_fmly, family_dv, terrane, era, eon, period, epoch, geom
├─ Output: ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom
└─ query_type: "polygon"

TABLE: geology_faults_contacts_master (LINE)
├─ Purpose: Fault lines, geological contacts
├─ Columns: gid, newtype, shape_leng, geom
├─ Output: ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom
└─ query_type: "line"

TABLE: borholes (POINT) [Note: spelled "borholes" not "boreholes"]
├─ Purpose: Borehole drilling data
├─ Columns: gid, project_na, borehole_i, elements, geom
├─ Output: latitude/longitude (same as mods)
├─ query_type: "point"
└─ ⚠️ NO region column

TABLE: surface_samples (POINT)
├─ Purpose: Surface sample data
├─ Columns: gid, sampleid, sampletype, elements, geom
├─ Output: latitude/longitude (same as mods)
├─ query_type: "point"
└─ ⚠️ NO region column

{dynamic_schema}

═══════════════════════════════════════════════════════════════════════════════
QUERY ROUTING DECISION TREE
═══════════════════════════════════════════════════════════════════════════════

User says...                          → Use table...
─────────────────────────────────────────────────────────────────────────────
"mines", "deposits", "sites"          → mods
"gold", "copper", "silver", etc.      → mods (filter by major_comm/minor_comm)
"areas", "zones", "geology"           → geology_master
"volcanic", "igneous", "sedimentary"  → geology_master (filter by litho_fmly)
"faults", "fault lines"               → geology_faults_contacts_master
"boreholes", "drilling"               → borholes
"samples"                             → surface_samples

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════

✓ DO:
  • List columns explicitly (never SELECT *)
  • Use ILIKE for text matching (case-insensitive)
  • Use OR for commodity search: (major_comm ILIKE '%X%' OR minor_comm ILIKE '%X%')
  • Wrap ALL geometries with ST_SetSRID(..., 3857) in spatial operations
  • Include geojson_geom for polygon/line tables
  • Include latitude/longitude for point tables

✗ DON'T:
  • Invent table names (no "gold_deposits", "copper_mines")
  • Invent column names (no "deposit_id", "mine_name", "fault_type")
  • Use "id" instead of "gid"
  • Add LIMIT unless user explicitly requests a number
  • Filter by commodity when user just says "mines" or "deposits"

═══════════════════════════════════════════════════════════════════════════════
SEMANTIC UNDERSTANDING
═══════════════════════════════════════════════════════════════════════════════

KEY DISTINCTION - "mines/deposits" is a TABLE reference, not a filter:

"show mines"              → ALL from mods (NO commodity filter)
"show gold mines"         → mods WHERE commodity = 'gold'
"mines in volcanic areas" → JOIN mods + geology_master (NO commodity filter)

SPATIAL OPERATIONS:
"in", "within", "inside"  → ST_Intersects(ST_SetSRID(a.geom, 3857), ST_SetSRID(b.geom, 3857))
"near", "close to"        → ST_DWithin(ST_SetSRID(a.geom, 3857), ST_SetSRID(b.geom, 3857), meters)

FAULTS IN REGION (faults have no region column):
→ JOIN faults with mods WHERE mods.region = X

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON only, no markdown)
═══════════════════════════════════════════════════════════════════════════════

{{
  "reasoning": "step-by-step thought process",
  "sql_query": "complete SQL",
  "query_type": "point|polygon|line",
  "description": "brief description",
  "tables_used": ["table1", "table2"]
}}

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Query: "show mines"
{{
  "reasoning": "User says 'mines' without commodity → return ALL from mods, no filter",
  "sql_query": "SELECT gid, eng_name, major_comm, minor_comm, region, occ_imp, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude FROM mods;",
  "query_type": "point",
  "description": "All mines",
  "tables_used": ["mods"]
}}

Query: "show gold deposits"
{{
  "reasoning": "User specifies 'gold' → filter mods by commodity using OR",
  "sql_query": "SELECT gid, eng_name, major_comm, minor_comm, region, occ_imp, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude FROM mods WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%');",
  "query_type": "point",
  "description": "Gold deposits",
  "tables_used": ["mods"]
}}

Query: "show volcanic areas"
{{
  "reasoning": "Volcanic = geology_master filtered by litho_fmly/family_dv/main_litho. Polygon output needs geojson_geom.",
  "sql_query": "SELECT gid, unit_name, main_litho, litho_fmly, terrane, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_master WHERE (litho_fmly ILIKE '%volcanic%' OR family_dv ILIKE '%volcanic%' OR main_litho ILIKE '%volcanic%');",
  "query_type": "polygon",
  "description": "Volcanic geological areas",
  "tables_used": ["geology_master"]
}}

Query: "show mines in volcanic areas"
{{
  "reasoning": "'mines' without commodity = ALL mines. Spatial join with geology_master for volcanic. No commodity filter.",
  "sql_query": "SELECT m.gid, m.eng_name, m.major_comm, m.minor_comm, m.region, g.unit_name AS geology, ST_Y(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS longitude FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%');",
  "query_type": "point",
  "description": "All mines within volcanic areas",
  "tables_used": ["mods", "geology_master"]
}}

Query: "show faults"
{{
  "reasoning": "Faults = geology_faults_contacts_master. Line output needs geojson_geom.",
  "sql_query": "SELECT gid, newtype, shape_leng, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_faults_contacts_master WHERE newtype ILIKE '%fault%';",
  "query_type": "line",
  "description": "Fault lines",
  "tables_used": ["geology_faults_contacts_master"]
}}

Query: "show faults in makkah region"
{{
  "reasoning": "Faults have no region column. Join with mods (has region) via ST_Intersects.",
  "sql_query": "SELECT DISTINCT f.gid, f.newtype, f.shape_leng, ST_AsGeoJSON(ST_Transform(ST_SetSRID(f.geom, 3857), 4326)) AS geojson_geom FROM geology_faults_contacts_master f JOIN mods m ON ST_Intersects(ST_SetSRID(f.geom, 3857), ST_SetSRID(m.geom, 3857)) WHERE m.region ILIKE '%Makkah%';",
  "query_type": "line",
  "description": "Faults in Makkah region",
  "tables_used": ["geology_faults_contacts_master", "mods"]
}}

Query: "gold deposits near faults"
{{
  "reasoning": "'gold' = commodity filter. 'near' = ST_DWithin. Join mods + faults.",
  "sql_query": "SELECT DISTINCT m.gid, m.eng_name, m.major_comm, m.region, f.newtype AS fault_type, ST_Y(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(m.geom, 3857), 4326)) AS longitude FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) WHERE (m.major_comm ILIKE '%gold%' OR m.minor_comm ILIKE '%gold%') AND f.newtype ILIKE '%fault%';",
  "query_type": "point",
  "description": "Gold deposits within 10km of faults",
  "tables_used": ["mods", "geology_faults_contacts_master"]
}}

Query: "top 10 gold deposits in riyadh"
{{
  "reasoning": "'top 10' = explicit LIMIT 10. 'gold' = commodity filter. 'riyadh' = region filter.",
  "sql_query": "SELECT gid, eng_name, major_comm, minor_comm, region, occ_imp, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude FROM mods WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') AND region ILIKE '%Riyadh%' LIMIT 10;",
  "query_type": "point",
  "description": "Top 10 gold deposits in Riyadh",
  "tables_used": ["mods"]
}}

Query: "show all areas" or "show all geology areas" or "show 10 areas"
{{
  "reasoning": "'areas' = geology_master table (POLYGON). Output must use geojson_geom NOT latitude/longitude.",
  "sql_query": "SELECT gid, unit_name, main_litho, litho_fmly, terrane, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_master LIMIT 10;",
  "query_type": "polygon",
  "description": "Geological areas",
  "tables_used": ["geology_master"]
}}

Query: "show all geology"
{{
  "reasoning": "'geology' without 'faults' = geology_master (POLYGON). Polygon tables use geojson_geom.",
  "sql_query": "SELECT gid, unit_name, main_litho, litho_fmly, terrane, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_master;",
  "query_type": "polygon",
  "description": "All geological units",
  "tables_used": ["geology_master"]
}}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: GEOMETRY OUTPUT RULES
═══════════════════════════════════════════════════════════════════════════════

POINT tables (mods, borholes, surface_samples):
  → Use: ST_Y(...) AS latitude, ST_X(...) AS longitude
  → query_type: "point"

POLYGON table (geology_master):
  → Use: ST_AsGeoJSON(...) AS geojson_geom
  → NEVER use ST_Y/ST_X on polygons!
  → query_type: "polygon"

LINE table (geology_faults_contacts_master):
  → Use: ST_AsGeoJSON(...) AS geojson_geom
  → NEVER use ST_Y/ST_X on lines!
  → query_type: "line"

"areas", "zones", "geology" (without "faults") → geology_master (POLYGON)
"faults", "fault lines", "contacts" → geology_faults_contacts_master (LINE)
"""


class SQLGenerator:
    """SQL Generator with improved prompt and post-processor."""
    
    def __init__(self):
        self.ollama = get_ollama_client()
        self.db = get_postgis_client()
        self._column_values: Dict[str, Dict[str, List[str]]] = {}
        self._reverse_mapping: Dict[str, Dict[str, Any]] = {}
        self._load_column_values()
        self._build_reverse_mapping()
    
    # =========================================================================
    # COLUMN VALUE LOADING (unchanged from original)
    # =========================================================================
    
    def _load_column_values(self):
        """Load distinct values from key columns in database."""
        logger.info("Loading column values from database...")
        
        tables_columns = {
            'mods': ['major_comm', 'minor_comm', 'region', 'occ_imp', 'occ_type', 
                     'occ_status', 'structural', 'host_rocks', 'alteration', 
                     'min_morpho', 'trace_comm'],
            'geology_master': ['litho_fmly', 'main_litho', 'family_dv', 'terrane', 
                               'era', 'eon', 'period', 'epoch', 'unit_name'],
            'geology_faults_contacts_master': ['newtype'],
            'borholes': ['borehole_t', 'elements', 'project_na'],
            'surface_samples': ['sampletype', 'elements']
        }
        
        self._column_values = {}
        
        for table, columns in tables_columns.items():
            self._column_values[table] = {}
            for column in columns:
                try:
                    query = f'SELECT DISTINCT "{column}" FROM {table} WHERE "{column}" IS NOT NULL AND "{column}" != \'\' LIMIT 100'
                    results = self.db.execute_query(query)
                    values = []
                    for row in results:
                        if isinstance(row, dict):
                            val = row.get(column) or row.get(column.lower())
                        else:
                            val = row[0] if len(row) > 0 else None
                        if val and str(val).strip():
                            values.append(str(val).strip())
                    self._column_values[table][column] = values
                except Exception as e:
                    logger.warning(f"Failed to load values for {table}.{column}: {e}")
                    self._column_values[table][column] = []
        
        logger.info(f"Loaded column values for {len(self._column_values)} tables")
    
    def _build_reverse_mapping(self):
        """Build reverse mapping: value → (table, column, original_value, priority)."""
        logger.info("Building reverse value mapping...")
        
        priority_map = {
            'region': 100, 'occ_imp': 90, 'occ_type': 90, 'era': 80,
            'terrane': 75, 'litho_fmly': 70, 'major_comm': 60, 'minor_comm': 55,
            'main_litho': 50, 'family_dv': 50, 'newtype': 50
        }
        
        self._reverse_mapping = {}
        
        for table, columns in self._column_values.items():
            for column, values in columns.items():
                priority = priority_map.get(column, 20)
                
                for value in values:
                    if not value or len(str(value).strip()) == 0:
                        continue
                    
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    
                    if value_lower not in self._reverse_mapping:
                        self._reverse_mapping[value_lower] = []
                    self._reverse_mapping[value_lower].append({
                        'table': table, 'column': column,
                        'original_value': value_str, 'priority': priority
                    })
        
        for value_key in self._reverse_mapping:
            self._reverse_mapping[value_key].sort(key=lambda x: x['priority'], reverse=True)
        
        logger.info(f"Built reverse mapping with {len(self._reverse_mapping)} unique values")
    
    # =========================================================================
    # PREPROCESSING
    # =========================================================================
    
    def _preprocess_query(self, query: str) -> str:
        """Add context hints to query."""
        query_lower = query.lower()
        hints = []
        
        # Region normalization
        for city, region in SAUDI_REGIONS.items():
            if city in query_lower and 'region' not in query_lower:
                hints.append(f"REGION: {city} → {region}")
        
        # Semantic hints
        has_commodity = any(c in query_lower for c in ['gold', 'copper', 'silver', 'zinc', 'iron', 'lead', 'nickel'])
        has_mine_word = any(w in query_lower for w in ['mines', 'deposits', 'sites', 'occurrences'])
        
        if has_mine_word and not has_commodity:
            hints.append("SEMANTIC: 'mines/deposits' without commodity → NO commodity filter")
        
        if hints:
            return query + " [" + " | ".join(hints) + "]"
        return query
    
    def _build_dynamic_schema_prompt(self) -> str:
        """Build concise schema section with sample values."""
        lines = ["SAMPLE VALUES FROM DATABASE:\n"]
        
        important_cols = {
            'mods': ['major_comm', 'region', 'occ_imp'],
            'geology_master': ['litho_fmly', 'main_litho', 'terrane'],
            'geology_faults_contacts_master': ['newtype']
        }
        
        for table, columns in important_cols.items():
            if table not in self._column_values:
                continue
            lines.append(f"{table}:")
            for col in columns:
                vals = self._column_values.get(table, {}).get(col, [])[:6]
                if vals:
                    lines.append(f"  {col}: {', '.join(vals)}")
            lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # SQL POST-PROCESSOR (SAFETY NET)
    # =========================================================================
    
    def _fix_sql(self, sql: str) -> str:
        """Fix common LLM mistakes in generated SQL."""
        original_sql = sql
        
        # 1. Fix SELECT * statements
        sql = self._fix_select_star(sql)
        
        # 2. Fix table names
        sql = self._fix_table_names(sql)
        
        # 3. Fix column names
        sql = self._fix_column_names(sql)
        
        # 4. Fix spatial operations (ensure both geoms have ST_SetSRID)
        sql = self._fix_spatial_operations(sql)
        
        # 5. Ensure geojson_geom for polygon/line tables
        sql = self._ensure_geojson_geom(sql)
        
        # 6. Fix borholes spelling
        sql = re.sub(r'\bboreholes\b', 'borholes', sql, flags=re.IGNORECASE)
        
        # 7. Fix AND → OR for commodity search
        sql = self._fix_commodity_logic(sql)
        if ' JOIN ' in sql.upper() and 'DISTINCT' not in sql.upper():
            sql = re.sub(r'\bSELECT\b', 'SELECT DISTINCT', sql, count=1, flags=re.IGNORECASE)
            logger.info("Added DISTINCT to JOIN query")
        
        if sql != original_sql:
            logger.info(f"SQL fixed: {original_sql} → {sql}")
        
        return sql
    
    def _fix_select_star(self, sql: str) -> str:
        """Replace SELECT * with proper column lists."""
        if not re.search(r'SELECT\s+\*\s+FROM', sql, re.IGNORECASE):
            return sql
        
        sql_lower = sql.lower()
        
        replacements = {
            'geology_faults_contacts_master': 'gid, newtype, shape_leng, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom',
            'geology_master': 'gid, unit_name, main_litho, litho_fmly, terrane, ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom',
            'mods': 'gid, eng_name, major_comm, minor_comm, region, occ_imp, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude',
            'borholes': 'gid, project_na, borehole_i, elements, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude',
            'surface_samples': 'gid, sampleid, sampletype, elements, ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude, ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude'
        }
        
        for table, columns in replacements.items():
            if table in sql_lower:
                pattern = rf'SELECT\s+\*\s+FROM\s+{table}'
                sql = re.sub(pattern, f'SELECT {columns} FROM {table}', sql, flags=re.IGNORECASE)
                logger.warning(f"Fixed SELECT * for {table}")
                break
        
        return sql
    
    def _fix_table_names(self, sql: str) -> str:
        """Fix invented/wrong table names."""
        # Compound names → mods
        sql = re.sub(r'(FROM|JOIN)\s+\w+_deposits\b', r'\1 mods', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(FROM|JOIN)\s+\w+_mines\b', r'\1 mods', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(FROM|JOIN)\s+\w+_sites\b', r'\1 mods', sql, flags=re.IGNORECASE)
        
        # Simple wrong names
        simple_fixes = {
            'deposits': 'mods', 'mines': 'mods', 'sites': 'mods',
            'faults': 'geology_faults_contacts_master',
            'areas': 'geology_master', 'zones': 'geology_master'
        }
        
        for wrong, correct in simple_fixes.items():
            sql = re.sub(rf'(FROM|JOIN)\s+{wrong}\b', rf'\1 {correct}', sql, flags=re.IGNORECASE)
        
        return sql
    
    def _fix_column_names(self, sql: str) -> str:
        """Fix invented column names."""
        column_fixes = {
            r'\bdeposit_id\b': 'gid', r'\bmine_id\b': 'gid', r'\bsite_id\b': 'gid',
            r'\barea_id\b': 'gid', r'\bfault_id\b': 'gid',
            r'\bdeposit_name\b': 'eng_name', r'\bmine_name\b': 'eng_name', r'\bsite_name\b': 'eng_name',
            r'\barea_name\b': 'unit_name', r'\bfault_name\b': 'newtype', r'\bfault_type\b': 'newtype',
            r'\bcommodity\b': 'major_comm', r'\bimportance\b': 'occ_imp',
            r'\brock_type\b': 'main_litho', r'\blithology\b': 'main_litho',
        }
        
        for wrong, correct in column_fixes.items():
            sql = re.sub(wrong, correct, sql, flags=re.IGNORECASE)
        
        # Fix generic "id" → "gid"
        sql = re.sub(r'(\w+)\.id\b(?!\w)', r'\1.gid', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bSELECT\s+id\s*,', 'SELECT gid,', sql, flags=re.IGNORECASE)
        sql = re.sub(r',\s*id\s+FROM', ', gid FROM', sql, flags=re.IGNORECASE)
        
        return sql
    
    def _fix_spatial_operations(self, sql: str) -> str:
        """Ensure both geometries in spatial ops have ST_SetSRID(..., 3857)."""
        spatial_ops = ['ST_Intersects', 'ST_DWithin', 'ST_Within', 'ST_Contains', 'ST_Crosses']
        
        for op in spatial_ops:
            # Pattern: op(geom, geom) → op(ST_SetSRID(geom, 3857), ST_SetSRID(geom, 3857))
            pattern = rf'{op}\s*\(\s*(\w+\.)?geom\s*,\s*(\w+\.)?geom'
            def fix_both(m):
                a1, a2 = m.group(1) or '', m.group(2) or ''
                return f'{op}(ST_SetSRID({a1}geom, 3857), ST_SetSRID({a2}geom, 3857)'
            sql = re.sub(pattern, fix_both, sql, flags=re.IGNORECASE)
            
            # Handle mixed cases (one with ST_SetSRID, one without)
            pattern2 = rf'{op}\s*\(\s*ST_SetSRID\s*\([^)]+\)\s*,\s*(\w+\.)?geom\b'
            def fix_second(m):
                alias = m.group(1) or ''
                # Find the first argument
                full_match = m.group(0)
                first_arg = re.search(r'ST_SetSRID\([^)]+\)', full_match).group(0)
                return f'{op}({first_arg}, ST_SetSRID({alias}geom, 3857)'
            sql = re.sub(pattern2, fix_second, sql, flags=re.IGNORECASE)
        
        return sql
    
    def _ensure_geojson_geom(self, sql: str) -> str:
        """Ensure geojson_geom is present for polygon/line tables and remove ST_Y/ST_X if present."""
        sql_upper = sql.upper()
        sql_lower = sql.lower()
        
        tables_needing_geojson = [
            ('geology_master', 'polygon'),
            ('geology_faults_contacts_master', 'line')
        ]
        
        # Check if this is a pure polygon/line query (not a JOIN with mods)
        is_point_table_in_query = any(
            f'from {t}' in sql_lower or f'join {t}' in sql_lower 
            for t in ['mods', 'borholes', 'surface_samples']
        )
        
        for table, geom_type in tables_needing_geojson:
            table_in_from = f'from {table.lower()}' in sql_lower
            table_in_join = f'join {table.lower()}' in sql_lower
            
            if table_in_from or table_in_join:
                # If this is a PURE polygon/line query (no point tables), fix ST_Y/ST_X errors
                if not is_point_table_in_query:
                    # Remove any ST_Y/ST_X calls which are wrong for polygon/line
                    if 'st_y(' in sql_lower or 'st_x(' in sql_lower:
                        logger.warning(f"Removing ST_Y/ST_X from {geom_type} query - these only work on points!")
                        # Remove the latitude/longitude columns entirely
                        sql = re.sub(
                            r',?\s*ST_Y\s*\([^)]+\)\s*AS\s+latitude',
                            '', sql, flags=re.IGNORECASE
                        )
                        sql = re.sub(
                            r',?\s*ST_X\s*\([^)]+\)\s*AS\s+longitude',
                            '', sql, flags=re.IGNORECASE
                        )
                        # Clean up any double commas
                        sql = re.sub(r',\s*,', ',', sql)
                        sql = re.sub(r'SELECT\s*,', 'SELECT ', sql, flags=re.IGNORECASE)
                
                # Add geojson_geom if not present
                if 'GEOJSON_GEOM' not in sql_upper:
                    from_match = re.search(rf'\bFROM\s+{table}\b', sql, re.IGNORECASE)
                    if from_match and sql.strip().upper().startswith('SELECT'):
                        from_pos = from_match.start()
                        before_from = sql[:from_pos].rstrip().rstrip(',')
                        after_from = sql[from_pos:]
                        
                        alias_match = re.search(rf'FROM\s+{table}\s+(\w+)', sql, re.IGNORECASE)
                        geom_ref = f'{alias_match.group(1)}.geom' if alias_match else 'geom'
                        geojson = f'ST_AsGeoJSON(ST_Transform(ST_SetSRID({geom_ref}, 3857), 4326)) AS geojson_geom'
                        
                        sql = f"{before_from}, {geojson} {after_from}"
                        logger.warning(f"Added geojson_geom to {table}")
        
        return sql
    
    def _fix_commodity_logic(self, sql: str) -> str:
        """Fix AND → OR for major_comm/minor_comm searches."""
        pattern = re.compile(
            r"major_comm\s+ILIKE\s+('[^']+')\s+AND\s+minor_comm\s+ILIKE\s+\1",
            re.IGNORECASE
        )
        def replace_with_or(m):
            val = m.group(1)
            return f"(major_comm ILIKE {val} OR minor_comm ILIKE {val})"
        return pattern.sub(replace_with_or, sql)
    
    # =========================================================================
    # LIMIT EXTRACTION
    # =========================================================================
    
    def _extract_limit_from_query(self, query: str) -> Optional[int]:
        """Extract limit if user explicitly requests a number."""
        patterns = [
            r'top\s+(\d+)', r'first\s+(\d+)', r'give\s+me\s+(\d+)',
            r'show\s+(\d+)', r'get\s+(\d+)', r'nearest\s+(\d+)',
            r'(\d+)\s+(?:nearest|closest|top|first)', r'limit\s+(?:to\s+)?(\d+)'
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return int(match.group(1))
        return None
    
    # =========================================================================
    # SQL GENERATION
    # =========================================================================
    
    async def generate_sql(self, query: str) -> Dict[str, Any]:
        """Generate SQL from natural language query."""
        processed_query = self._preprocess_query(query)
        
        try:
            dynamic_schema = self._build_dynamic_schema_prompt()
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(dynamic_schema=dynamic_schema)
            
            result = await self.ollama.generate_json(
                prompt=f'Generate SQL for: "{processed_query}"',
                system=system_prompt,
                temperature=0.0
            )
            
            if "sql_query" not in result:
                raise ValueError("No sql_query in response")
            
            sql = self._fix_sql(result["sql_query"])
            query_type = self._determine_query_type(sql, result.get("query_type", "point"))
            
            logger.info(f"Generated SQL: {sql}")
            
            return {
                "sql_query": sql,
                "query_type": query_type,
                "description": result.get("description", ""),
                "tables_used": result.get("tables_used", []),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise ValueError(f"Failed to generate SQL: {e}")
    
    def _determine_query_type(self, sql: str, suggested_type: str) -> str:
        """
        ═══════════════════════════════════════════════════════════════════════
        CRITICAL FIX: Determine query_type based on OUTPUT columns AND tables!
        ═══════════════════════════════════════════════════════════════════════
        
        The query_type must match what's being SELECTED:
        - If latitude/longitude are in SELECT → POINT
        - If geojson_geom is selected from faults table → LINE
        - If geojson_geom is selected from geology_master → POLYGON
        """
        sql_lower = sql.lower()
        
        # =====================================================================
        # RULE 1: If latitude/longitude are in SELECT → this is a POINT query
        # =====================================================================
        if ' as latitude' in sql_lower and ' as longitude' in sql_lower:
            logger.info("query_type = POINT (latitude/longitude in SELECT)")
            return "point"
        
        # =====================================================================
        # RULE 2: Check the FROM clause to determine table type
        # =====================================================================
        
        # Check for faults table first (more specific)
        is_faults_query = (
            'from geology_faults_contacts_master' in sql_lower or
            'join geology_faults_contacts_master' in sql_lower
        )
        
        # Check for geology_master table
        is_geology_query = (
            'from geology_master' in sql_lower or
            'join geology_master' in sql_lower
        )
        
        # If ONLY faults table (no geology_master), it's LINE
        if is_faults_query and not is_geology_query:
            logger.info("query_type = LINE (faults table only)")
            return "line"
        
        # If ONLY geology_master table (no faults), it's POLYGON
        if is_geology_query and not is_faults_query:
            logger.info("query_type = POLYGON (geology_master table only)")
            return "polygon"
        
        # =====================================================================
        # RULE 3: If geojson_geom is in SELECT → check alias to determine source
        # =====================================================================
        if 'as geojson_geom' in sql_lower or 'geojson_geom' in sql_lower:
            # Check if geojson is from faults table (look for f.geom pattern)
            if re.search(r'st_asgeojson\s*\([^)]*f\.geom', sql_lower):
                logger.info("query_type = LINE (geojson_geom from faults alias 'f')")
                return "line"
            
            # Check if geojson is from geology_master (look for g.geom pattern)
            if re.search(r'st_asgeojson\s*\([^)]*g\.geom', sql_lower):
                logger.info("query_type = POLYGON (geojson_geom from geology_master alias 'g')")
                return "polygon"
            
            # If geojson_geom exists but source unclear, use suggested type
            logger.info(f"query_type = {suggested_type} (geojson_geom with unclear source)")
            return suggested_type if suggested_type in ['line', 'polygon'] else 'polygon'
        
        # =====================================================================
        # RULE 4: Check for point tables
        # =====================================================================
        point_tables = ['mods', 'borholes', 'surface_samples']
        for table in point_tables:
            if f'from {table}' in sql_lower:
                logger.info(f"query_type = POINT (from {table} table)")
                return "point"
        
        # =====================================================================
        # RULE 5: Fallback to suggested type
        # =====================================================================
        logger.info(f"query_type = {suggested_type} (fallback to suggested)")
        return suggested_type
    
    # =========================================================================
    # RETRY MECHANISM
    # =========================================================================
    
    async def generate_sql_with_retry(self, query: str, max_retries: int = 4) -> Dict[str, Any]:
        """Generate SQL with retry mechanism on validation failure."""
        attempt = 0
        attempt_history = []
        
        while attempt < max_retries:
            attempt += 1
            logger.info(f"SQL Generation Attempt {attempt}/{max_retries}")
            
            try:
                if attempt == 1:
                    result = await self.generate_sql(query)
                else:
                    result = await self._regenerate_with_feedback(query, attempt_history, attempt)
                
                # Validate with EXPLAIN
                explain_query = f"EXPLAIN {result['sql_query']}"
                self.db.execute_query(explain_query)
                
                logger.info(f"SQL validation passed on attempt {attempt}")
                return {**result, "attempts": attempt, "failed_attempts": attempt_history}
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt} failed: {error_msg}")
                attempt_history.append({
                    'sql': result.get('sql_query', 'N/A') if 'result' in dir() else 'N/A',
                    'error': error_msg
                })
                
                if attempt >= max_retries:
                    raise ValueError(f"Failed after {max_retries} attempts. Last error: {error_msg}")
        
        raise ValueError(f"Failed to generate valid SQL after {max_retries} attempts")
    
    async def _regenerate_with_feedback(self, query: str, history: List[Dict], attempt: int) -> Dict[str, Any]:
        """Regenerate SQL with error feedback from previous attempts."""
        error_text = "\n".join([
            f"Attempt {i+1}: {h['sql']}\nError: {h['error']}"
            for i, h in enumerate(history)
        ])
        
        retry_prompt = f"""Original: "{query}"

PREVIOUS FAILURES:
{error_text}

Fix ALL errors. Common issues:
- Wrong table/column names
- Missing ST_SetSRID on geometries  
- SELECT * (list columns explicitly)
- Missing geojson_geom for polygon/line
- AND instead of OR for commodity search

Generate corrected SQL."""
        
        dynamic_schema = self._build_dynamic_schema_prompt()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(dynamic_schema=dynamic_schema)
        
        result = await self.ollama.generate_json(
            prompt=retry_prompt,
            system=system_prompt,
            temperature=0.0
        )
        
        if "sql_query" not in result:
            raise ValueError("No sql_query in regenerated response")
        
        sql = self._fix_sql(result["sql_query"])
        query_type = self._determine_query_type(sql, result.get("query_type", "point"))
        
        return {
            "sql_query": sql,
            "query_type": query_type,
            "description": result.get("description", ""),
            "tables_used": result.get("tables_used", []),
            "reasoning": result.get("reasoning", "")
        }
    
    # =========================================================================
    # EXECUTION
    # =========================================================================
    
    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL for safety."""
        return self.db.validate_query(sql)
    
    async def execute(self, query: str, use_retry: bool = True) -> Dict[str, Any]:
        """Generate, validate, and execute SQL."""
        
        if use_retry:
            gen_result = await self.generate_sql_with_retry(query)
        else:
            gen_result = await self.generate_sql(query)
        
        sql = gen_result["sql_query"]
        user_limit = self._extract_limit_from_query(query)
        
        is_valid, error = self.validate_sql(sql)
        if not is_valid:
            return {
                "success": False,
                "error": f"Invalid SQL: {error}",
                "sql_query": sql,
                "natural_query": query
            }
        
        try:
            effective_limit = user_limit if user_limit else 10_000_000
            results, truncated = self.db.execute_safe_query(sql, max_rows=effective_limit)
            
            return {
                "success": True,
                "data": results,
                "row_count": len(results),
                "was_truncated": truncated if user_limit else False,
                "sql_query": sql,
                "query_type": gen_result["query_type"],
                "description": gen_result["description"],
                "tables_used": gen_result["tables_used"],
                "natural_query": query
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": sql,
                "natural_query": query
            }
    
    def refresh_column_values(self):
        """Refresh column values from database."""
        self._load_column_values()
        self._build_reverse_mapping()


# Singleton
_sql_generator: Optional[SQLGenerator] = None

def get_sql_generator() -> SQLGenerator:
    global _sql_generator
    if _sql_generator is None:
        _sql_generator = SQLGenerator()
    return _sql_generator