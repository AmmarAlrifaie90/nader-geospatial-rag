# 🧪 100 Training Questions for Geospatial Text-to-SQL System

This document provides 100 realistic user questions that test all system capabilities: **spatial operations** (ST_Intersects, ST_DWithin, ST_Distance), **fuzzy matching** (typo tolerance), **multi-table joins**, **aggregations**, and **complex geospatial queries** using **REAL DATA VALUES** from the actual database.

## Legend
- 🗺️ **Tests Spatial Operations** - ST_Intersects, ST_DWithin, ST_Distance, ST_Area, ST_Length
- 🔍 **Tests Fuzzy Matching** - Levenshtein distance for typos in names, regions, commodities
- 🔗 **Tests Multi-Join** - Combines multiple tables (mods, geology_master, faults, etc.)
- 📊 **Tests Aggregation** - COUNT, AVG, SUM, GROUP BY
- 🎯 **Tests Complex Filters** - Multiple conditions, regions, commodities, importance levels
- 📍 **Tests Point Queries** - Simple point-based queries
- 📐 **Tests Polygon/Line Queries** - MultiPolygon and MultiLineString geometries

---

## Real Data Values Reference

### Commodities (major_comm):
- "Sand And Gravels", "Quartzite", "Granite", "Zinc", "Feldspar", "Gossan", "Limestone"
- Note: minor_comm contains semicolon-separated values like "Silver; Copper; Gold", "Nickel; Zinc; Copper; Lead", "Cobalt; Nickel"

### Regions (with "Region" suffix):
- "Makkah Region", "Riyadh Region", "Qasim Region", "Tabouk Region", "Madinah Region"

### Occurrence Types (occ_type):
- "Metallic", "Non Metallic"

### Importance (occ_imp):
- "High", "Medium", "Low"

### Status (occ_status):
- "Occurrence", "Deposit", "Prospect"

### Exploration Status (exp_status):
- "Reconnaissance", "Deposit", "Prospect"

### Terranes (structural/reg_struct):
- "Phanerozoic deposits", "Jiddah terrane", "Afif composite terrane", "Midyan terrane"

### Host Rocks (host_rocks):
- "granite", "quartzite", "limestone", "pegmatite", "sandstone", "marble", "basalt", "granodiorite", "diorite"

### Alteration (alteration):
- "gossan alteration", "hematization; silicification; kaolinization", "silicification"

### Mineral Morphology (min_morpho):
- "Massive", "veins", "lenses", "DISSEMINATION; lenses; Stratiform", "bed"

### Surface Samples (sampletype):
- "Chip Sampling", "Stream", "Rock"

### Surface Samples (elements):
- "Au", "Ag; Al2X; As; Au; Ba; Be; Bi; CaO; Cd; Ce; Co; Cr; Cu; Dy; Er; Eu; Fe2X; Ga; Gd; Ge; Hf; Ho; K2O; La; Li; LOI; Lu; MgO; MnO; Mo; Na2O; Nb; Nd; Ni; P2O5; Pb; Pr; Sb; Sc; SiO2; Sm; Sn; SO3; Sr; Ta; Tb; Th; TiO2; Tm; U; V; W; Y; Yb; Zn; Zr"

### Geology Master (litho_fmly):
- "Igneous rock", "Polylithologic rocks", "Sedimentary rock"

### Geology Master (main_litho):
- "Basalt", "Granodiorite, tonalite, diorite", "Lithic arenite, wacke, siltstone, limestone, dolomite, conglomerate, rhyolite, dacite, basalt, andesite, tuff"

### Faults (newtype):
- "Fault", "Contact"

### Dikes (ltype):
- "Felsic and/or undifferentiated dike", "Mafic dike"

### Boreholes (project_na):
- "Al Hajar, Ma'aden Expired and Relinquished Licences", "SHA'IB LAMISAH", "ZALIM REGIONAL", "BIR TAWILAH TUNGSTEN", "JABAL SAYID", "Q'ALAT ZUMURRUD", "Tabuk Clay Deposit (East Tabuk Region)", "AZ ZABIRAH BAUXITE", "KHNAIGUIYAH"

### Boreholes (borehole_t):
- "Mineral Exploration", "Trench"

---

## EASY QUESTIONS (1-30)

### Basic Single-Table Queries

### 1. 📍 Show all gold deposits
**Question:** "Show me all gold deposits"

**What it tests:** Basic commodity filter on mods table  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%')`  
**Note:** Gold may be in minor_comm as "Silver; Copper; Gold"

---

### 2. 📍 Find all zinc occurrences
**Question:** "Find all zinc occurrences"

**What it tests:** Commodity filter with zinc in major_comm or minor_comm  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%zinc%' OR minor_comm ILIKE '%zinc%')`  
**Note:** Zinc can be major_comm or in minor_comm like "Nickel; Zinc; Copper; Lead"

---

### 3. 📍 Show all granite deposits
**Question:** "Show me all granite deposits"

**What it tests:** Exact commodity match  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%granite%'`  
**Real value:** "Granite"

---

### 4. 📍 Find all limestone occurrences
**Question:** "Find all limestone occurrences"

**What it tests:** Commodity filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%limestone%'`  
**Real value:** "Limestone"

---

### 5. 📍 Show all gossan deposits
**Question:** "Show me all gossan deposits"

**What it tests:** Commodity filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%gossan%'`  
**Real value:** "Gossan"

---

### 6. 📍 Find all quartzite occurrences
**Question:** "Find all quartzite occurrences"

**What it tests:** Commodity filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%quartzite%'`  
**Real value:** "Quartzite"

---

### 7. 📍 Show all sand and gravels deposits
**Question:** "Show me all sand and gravels deposits"

**What it tests:** Multi-word commodity filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%sand%' AND major_comm ILIKE '%gravel%'`  
**Real value:** "Sand And Gravels"

---

### 8. 📍 Find all feldspar occurrences
**Question:** "Find all feldspar occurrences"

**What it tests:** Commodity filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%feldspar%'`  
**Real value:** "Feldspar"

---

### 9. 📍 Show all boreholes
**Question:** "Show me all boreholes"

**What it tests:** Simple table query  
**Expected:** `SELECT ... FROM borholes`  
**Output:** Point with lat/lon

---

### 10. 📍 List all surface samples
**Question:** "List all surface samples"

**What it tests:** Simple table query  
**Expected:** `SELECT ... FROM surface_samples`  
**Output:** Point with lat/lon

---

### 11. 📐 Show all geological areas
**Question:** "Show all geological areas"

**What it tests:** Polygon geometry output  
**Expected:** `SELECT ..., ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_master`  
**Note:** MUST include geojson_geom column for map visualization

---

### 12. 📐 Display all faults
**Question:** "Display all faults"

**What it tests:** Line geometry output  
**Expected:** `SELECT ..., ST_AsGeoJSON(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS geojson_geom FROM geology_faults_contacts_master WHERE newtype ILIKE '%fault%'`  
**Note:** MUST include geojson_geom column for map visualization

---

### 13. 📍 Find gold deposits in Riyadh Region
**Question:** "Find gold deposits in Riyadh Region"

**What it tests:** Commodity + region filter  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%gold%' OR minor_comm ILIKE '%gold%') AND region ILIKE '%Riyadh%'`  
**Real region:** "Riyadh Region"

---

### 14. 📍 Show zinc occurrences in Makkah Region
**Question:** "Show zinc occurrences in Makkah Region"

**What it tests:** Commodity + region filter  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%zinc%' OR minor_comm ILIKE '%zinc%') AND region ILIKE '%Makkah%'`  
**Real region:** "Makkah Region"

---

### 15. 📍 Find granite deposits in Tabouk Region
**Question:** "Find granite deposits in Tabouk Region"

**What it tests:** Commodity + region filter  
**Expected:** `SELECT ... FROM mods WHERE major_comm ILIKE '%granite%' AND region ILIKE '%Tabouk%'`  
**Real region:** "Tabouk Region"

---

### 16. 📍 Show metallic occurrences
**Question:** "Show metallic occurrences"

**What it tests:** occ_type filter  
**Expected:** `SELECT ... FROM mods WHERE occ_type ILIKE '%metallic%'`  
**Real value:** "Metallic"

---

### 17. 📍 Find non-metallic deposits
**Question:** "Find non-metallic deposits"

**What it tests:** occ_type filter  
**Expected:** `SELECT ... FROM mods WHERE occ_type ILIKE '%non%metallic%'`  
**Real value:** "Non Metallic"

---

### 18. 📍 Show deposits with high importance
**Question:** "Show deposits with high importance"

**What it tests:** occ_imp filter  
**Expected:** `SELECT ... FROM mods WHERE occ_imp ILIKE '%high%'`  
**Real value:** "High"

---

### 19. 📍 Find deposits with medium importance
**Question:** "Find deposits with medium importance"

**What it tests:** occ_imp filter  
**Expected:** `SELECT ... FROM mods WHERE occ_imp ILIKE '%medium%'`  
**Real value:** "Medium"

---

### 20. 📍 Show deposits with low importance
**Question:** "Show deposits with low importance"

**What it tests:** occ_imp filter  
**Expected:** `SELECT ... FROM mods WHERE occ_imp ILIKE '%low%'`  
**Real value:** "Low"

---

### 21. 📍 Find all occurrences (status)
**Question:** "Find all occurrences"

**What it tests:** occ_status filter  
**Expected:** `SELECT ... FROM mods WHERE occ_status ILIKE '%occurrence%'`  
**Real value:** "Occurrence"

---

### 22. 📍 Show all deposits (status)
**Question:** "Show all deposits"

**What it tests:** occ_status filter  
**Expected:** `SELECT ... FROM mods WHERE occ_status ILIKE '%deposit%'`  
**Real value:** "Deposit"

---

### 23. 📍 Find all prospects
**Question:** "Find all prospects"

**What it tests:** occ_status filter  
**Expected:** `SELECT ... FROM mods WHERE occ_status ILIKE '%prospect%'`  
**Real value:** "Prospect"

---

### 24. 📍 Show deposits in reconnaissance stage
**Question:** "Show deposits in reconnaissance stage"

**What it tests:** exp_status filter  
**Expected:** `SELECT ... FROM mods WHERE exp_status ILIKE '%reconnaissance%'`  
**Real value:** "Reconnaissance"

---

### 25. 📍 Find deposits in Jiddah terrane
**Question:** "Find deposits in Jiddah terrane"

**What it tests:** Structural/terrane filter  
**Expected:** `SELECT ... FROM mods WHERE structural ILIKE '%jiddah%' OR reg_struct ILIKE '%jiddah%'`  
**Real value:** "Jiddah terrane"

---

### 26. 📍 Show deposits in Afif composite terrane
**Question:** "Show deposits in Afif composite terrane"

**What it tests:** Structural/terrane filter  
**Expected:** `SELECT ... FROM mods WHERE structural ILIKE '%afif%' OR reg_struct ILIKE '%afif%'`  
**Real value:** "Afif composite terrane"

---

### 27. 📍 Find deposits in Midyan terrane
**Question:** "Find deposits in Midyan terrane"

**What it tests:** Structural/terrane filter  
**Expected:** `SELECT ... FROM mods WHERE structural ILIKE '%midyan%' OR reg_struct ILIKE '%midyan%'`  
**Real value:** "Midyan terrane"

---

### 28. 📍 Show deposits with gossan alteration
**Question:** "Show deposits with gossan alteration"

**What it tests:** Alteration filter  
**Expected:** `SELECT ... FROM mods WHERE alteration ILIKE '%gossan%'`  
**Real value:** "gossan alteration"

---

### 29. 📍 Find deposits with silicification
**Question:** "Find deposits with silicification"

**What it tests:** Alteration filter with semicolon-separated values  
**Expected:** `SELECT ... FROM mods WHERE alteration ILIKE '%silicification%'`  
**Real value:** "silicification" (may be combined like "hematization; silicification; kaolinization")

---

### 30. 📍 Show deposits with vein morphology
**Question:** "Show deposits with vein morphology"

**What it tests:** Mineral morphology filter  
**Expected:** `SELECT ... FROM mods WHERE min_morpho ILIKE '%vein%'`  
**Real value:** "veins"

---

## MEDIUM QUESTIONS (31-60)

### Spatial Joins and Proximity

### 31. 🗺️ Find zinc deposits within 5km of faults
**Question:** "Find zinc deposits within 5km of faults"

**What it tests:** ST_DWithin spatial join between mods and faults  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND f.newtype ILIKE '%fault%'`

---

### 32. 🗺️ Show granite deposits near faults
**Question:** "Show granite deposits near faults"

**What it tests:** ST_DWithin with 10km distance  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) WHERE m.major_comm ILIKE '%granite%' AND f.newtype ILIKE '%fault%'`

---

### 33. 🗺️ Find gossan deposits inside volcanic areas
**Question:** "Find gossan deposits inside volcanic areas"

**What it tests:** ST_Intersects between mods and geology_master  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE m.major_comm ILIKE '%gossan%' AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%')`

---

### 34. 🗺️ Show metallic deposits within geological areas
**Question:** "Show metallic deposits within geological areas"

**What it tests:** ST_Intersects with occ_type filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE m.occ_type ILIKE '%metallic%'`

---

### 35. 🗺️ Find high importance deposits 10km away from faults
**Question:** "Find high importance deposits 10km away from faults"

**What it tests:** ST_DWithin with importance filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) WHERE m.occ_imp ILIKE '%high%' AND f.newtype ILIKE '%fault%'`

---

### 36. 🗺️ Show deposits within 3km of contacts
**Question:** "Show deposits within 3km of contacts"

**What it tests:** ST_DWithin with contact type filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 3000) WHERE f.newtype ILIKE '%contact%'`

---

### 37. 🗺️ Find boreholes inside sedimentary areas
**Question:** "Find boreholes inside sedimentary areas"

**What it tests:** ST_Intersects between borholes and geology_master  
**Expected:** `SELECT b.* FROM borholes b JOIN geology_master g ON ST_Intersects(ST_SetSRID(b.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE g.main_litho ILIKE '%sedimentary%' OR g.litho_fmly ILIKE '%sedimentary%'`

---

### 38. 🗺️ Show copper deposits near dikes
**Question:** "Show copper deposits near dikes"

**What it tests:** ST_DWithin with dikes table  
**Expected:** `SELECT m.* FROM mods m JOIN geology_dikes_master d ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(d.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%copper%' OR m.minor_comm ILIKE '%copper%')`

---

### 39. 🗺️ Find samples within 2km of gold deposits
**Question:** "Find samples within 2km of gold deposits"

**What it tests:** ST_DWithin between surface_samples and mods  
**Expected:** `SELECT s.* FROM surface_samples s JOIN mods m ON ST_DWithin(ST_SetSRID(s.geom, 3857), ST_SetSRID(m.geom, 3857), 2000) WHERE (m.major_comm ILIKE '%gold%' OR m.minor_comm ILIKE '%gold%')`

---

### 40. 🗺️ Show deposits in igneous formations
**Question:** "Show deposits in igneous formations"

**What it tests:** ST_Intersects with lithology filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE g.main_litho ILIKE '%igneous%' OR g.litho_fmly ILIKE '%igneous%'`

---

### Distance Calculations

### 41. 🗺️ Find distance from zinc deposits to nearest fault
**Question:** "Find distance from zinc deposits to nearest fault"

**What it tests:** ST_Distance calculation  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS distance FROM mods m, geology_faults_contacts_master f WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND f.newtype ILIKE '%fault%' ORDER BY distance LIMIT 1`

---

### 42. 🗺️ Show distance from boreholes to deposits
**Question:** "Show distance from boreholes to deposits"

**What it tests:** ST_Distance between two point tables  
**Expected:** `SELECT b.*, m.*, ST_Distance(ST_SetSRID(b.geom, 3857), ST_SetSRID(m.geom, 3857)) AS distance FROM borholes b, mods m ORDER BY distance LIMIT 50`

---

### 43. 🗺️ Find nearest sample to each deposit
**Question:** "Find nearest sample to each deposit"

**What it tests:** ST_Distance with window function or subquery  
**Expected:** `SELECT m.*, s.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(s.geom, 3857)) AS distance FROM mods m CROSS JOIN LATERAL (SELECT * FROM surface_samples ORDER BY ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(s.geom, 3857)) LIMIT 1) s`

---

### 44. 🗺️ Calculate distance from deposits to contacts
**Question:** "Calculate distance from deposits to contacts"

**What it tests:** ST_Distance with contact filter  
**Expected:** `SELECT m.*, f.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS distance FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%contact%' ORDER BY distance LIMIT 50`

---

### Buffer Operations

### 45. 🗺️ Find all deposits within 5km buffer of faults
**Question:** "Find all deposits within 5km buffer of faults"

**What it tests:** ST_DWithin buffer operation  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE f.newtype ILIKE '%fault%'`

---

### 46. 🗺️ Show areas within 10km of gold deposits
**Question:** "Show areas within 10km of gold deposits"

**What it tests:** ST_DWithin with polygon output  
**Expected:** `SELECT g.*, ST_AsGeoJSON(ST_Transform(ST_SetSRID(g.geom, 3857), 4326)) AS geojson_geom FROM geology_master g JOIN mods m ON ST_DWithin(ST_SetSRID(g.geom, 3857), ST_SetSRID(m.geom, 3857), 10000) WHERE (m.major_comm ILIKE '%gold%' OR m.minor_comm ILIKE '%gold%')`

---

### 47. 🗺️ Find boreholes in 3km buffer around deposits
**Question:** "Find boreholes in 3km buffer around deposits"

**What it tests:** ST_DWithin between borholes and mods  
**Expected:** `SELECT b.* FROM borholes b JOIN mods m ON ST_DWithin(ST_SetSRID(b.geom, 3857), ST_SetSRID(m.geom, 3857), 3000)`

---

### Aggregations

### 48. 📊 Count zinc deposits by region
**Question:** "Count zinc deposits by region"

**What it tests:** COUNT with GROUP BY  
**Expected:** `SELECT region, COUNT(*) AS count FROM mods WHERE (major_comm ILIKE '%zinc%' OR minor_comm ILIKE '%zinc%') GROUP BY region`

---

### 49. 📊 Show average distance from deposits to faults
**Question:** "Show average distance from deposits to faults"

**What it tests:** AVG aggregation with spatial function  
**Expected:** `SELECT AVG(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857))) AS avg_distance FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%'`

---

### 50. 📊 Count deposits in each geological area
**Question:** "Count deposits in each geological area"

**What it tests:** COUNT with spatial join and GROUP BY  
**Expected:** `SELECT g.gid, g.unit_name, COUNT(m.gid) AS deposit_count FROM geology_master g LEFT JOIN mods m ON ST_Intersects(ST_SetSRID(g.geom, 3857), ST_SetSRID(m.geom, 3857)) GROUP BY g.gid, g.unit_name`

---

### 51. 📊 Find total number of boreholes per project
**Question:** "Find total number of boreholes per project"

**What it tests:** COUNT with GROUP BY on project_na  
**Expected:** `SELECT project_na, COUNT(*) AS count FROM borholes GROUP BY project_na`

---

### 52. 📊 Show top 5 regions by deposit count
**Question:** "Show top 5 regions by deposit count"

**What it tests:** COUNT with GROUP BY, ORDER BY, LIMIT  
**Expected:** `SELECT region, COUNT(*) AS count FROM mods GROUP BY region ORDER BY count DESC LIMIT 5`

---

### 53. 📊 Count samples by type
**Question:** "Count samples by type"

**What it tests:** COUNT with GROUP BY on sampletype  
**Expected:** `SELECT sampletype, COUNT(*) AS count FROM surface_samples GROUP BY sampletype`  
**Real values:** "Chip Sampling", "Stream", "Rock"

---

### 54. 📊 Find areas with most deposits
**Question:** "Find areas with most deposits"

**What it tests:** COUNT with spatial join, ORDER BY  
**Expected:** `SELECT g.gid, g.unit_name, COUNT(m.gid) AS deposit_count FROM geology_master g LEFT JOIN mods m ON ST_Intersects(ST_SetSRID(g.geom, 3857), ST_SetSRID(m.geom, 3857)) GROUP BY g.gid, g.unit_name ORDER BY deposit_count DESC`

---

### 55. 📊 Count deposits by importance level
**Question:** "Count deposits by importance level"

**What it tests:** COUNT with GROUP BY on occ_imp  
**Expected:** `SELECT occ_imp, COUNT(*) AS count FROM mods GROUP BY occ_imp`  
**Real values:** "High", "Medium", "Low"

---

### 56. 📊 Show count of metallic vs non-metallic deposits
**Question:** "Show count of metallic vs non-metallic deposits"

**What it tests:** COUNT with GROUP BY on occ_type  
**Expected:** `SELECT occ_type, COUNT(*) AS count FROM mods GROUP BY occ_type`

---

### 57. 📊 Count deposits by status
**Question:** "Count deposits by status"

**What it tests:** COUNT with GROUP BY on occ_status  
**Expected:** `SELECT occ_status, COUNT(*) AS count FROM mods GROUP BY occ_status`  
**Real values:** "Occurrence", "Deposit", "Prospect"

---

### Complex Filters

### 58. 🎯 Show zinc deposits in Riyadh and Makkah Regions
**Question:** "Show zinc deposits in Riyadh and Makkah Regions"

**What it tests:** Multiple region filters with OR  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%zinc%' OR minor_comm ILIKE '%zinc%') AND (region ILIKE '%Riyadh%' OR region ILIKE '%Makkah%')`

---

### 59. 🎯 Find copper and nickel deposits
**Question:** "Find copper and nickel deposits"

**What it tests:** Multiple commodity filters  
**Expected:** `SELECT ... FROM mods WHERE (major_comm ILIKE '%copper%' OR minor_comm ILIKE '%copper%' OR major_comm ILIKE '%nickel%' OR minor_comm ILIKE '%nickel%')`  
**Note:** May be in minor_comm as "Nickel; Zinc; Copper; Lead" or "Cobalt; Nickel"

---

### 60. 🎯 Show high importance metallic deposits in Riyadh Region
**Question:** "Show high importance metallic deposits in Riyadh Region"

**What it tests:** Multiple filters combined with AND  
**Expected:** `SELECT ... FROM mods WHERE occ_type ILIKE '%metallic%' AND occ_imp ILIKE '%high%' AND region ILIKE '%Riyadh%'`

---

## HARD QUESTIONS (61-100)

### Complex Spatial Joins

### 61. 🗺️🔗 Find zinc deposits within 5km of faults AND inside volcanic areas
**Question:** "Find zinc deposits within 5km of faults AND inside volcanic areas"

**What it tests:** Multiple spatial joins (ST_DWithin + ST_Intersects)  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND f.newtype ILIKE '%fault%' AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%')`

---

### 62. 🗺️🔗 Show deposits near faults that are also near contacts
**Question:** "Show deposits near faults that are also near contacts"

**What it tests:** Multiple ST_DWithin joins  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f1 ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f1.geom, 3857), 5000) JOIN geology_faults_contacts_master f2 ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f2.geom, 3857), 5000) WHERE f1.newtype ILIKE '%fault%' AND f2.newtype ILIKE '%contact%'`

---

### 63. 🗺️🔗 Find boreholes within 2km of deposits AND inside igneous areas
**Question:** "Find boreholes within 2km of deposits AND inside igneous areas"

**What it tests:** ST_DWithin + ST_Intersects  
**Expected:** `SELECT b.* FROM borholes b JOIN mods m ON ST_DWithin(ST_SetSRID(b.geom, 3857), ST_SetSRID(m.geom, 3857), 2000) JOIN geology_master g ON ST_Intersects(ST_SetSRID(b.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE g.main_litho ILIKE '%igneous%' OR g.litho_fmly ILIKE '%igneous%'`

---

### 64. 🗺️🔗 Show deposits in Jiddah terrane areas
**Question:** "Show deposits in Jiddah terrane areas"

**What it tests:** ST_Intersects with structural filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE (m.structural ILIKE '%jiddah%' OR m.reg_struct ILIKE '%jiddah%')`

---

### 65. 🗺️🔗 Find samples near deposits that are also near boreholes
**Question:** "Find samples near deposits that are also near boreholes"

**What it tests:** Multiple ST_DWithin joins  
**Expected:** `SELECT s.* FROM surface_samples s JOIN mods m ON ST_DWithin(ST_SetSRID(s.geom, 3857), ST_SetSRID(m.geom, 3857), 2000) JOIN borholes b ON ST_DWithin(ST_SetSRID(s.geom, 3857), ST_SetSRID(b.geom, 3857), 2000)`

---

### Multiple ST_ Functions

### 66. 🗺️ Find deposits within 5km of faults, calculate distance, and check if inside areas
**Question:** "Find deposits within 5km of faults, calculate distance, and check if inside areas"

**What it tests:** ST_DWithin + ST_Distance + ST_Intersects  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, CASE WHEN ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) THEN true ELSE false END AS inside_area FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) LEFT JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE f.newtype ILIKE '%fault%'`

---

### 67. 🗺️ Show deposits with distance to nearest fault and area centroid
**Question:** "Show deposits with distance to nearest fault and area centroid"

**What it tests:** ST_Distance + ST_Centroid  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Distance(ST_SetSRID(m.geom, 3857), ST_Centroid(ST_SetSRID(g.geom, 3857))) AS centroid_distance FROM mods m, geology_faults_contacts_master f, geology_master g WHERE f.newtype ILIKE '%fault%' ORDER BY fault_distance LIMIT 50`

---

### 68. 🗺️ Find deposits within buffer of faults and calculate area of intersecting geology
**Question:** "Find deposits within buffer of faults and calculate area of intersecting geology"

**What it tests:** ST_DWithin + ST_Intersects + ST_Area  
**Expected:** `SELECT m.*, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE f.newtype ILIKE '%fault%'`

---

### 69. 🗺️ Show deposits with distance to fault and length of intersecting contacts
**Question:** "Show deposits with distance to fault and length of intersecting contacts"

**What it tests:** ST_Distance + ST_Length  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Length(ST_SetSRID(c.geom, 3857)) AS contact_length FROM mods m, geology_faults_contacts_master f, geology_faults_contacts_master c WHERE f.newtype ILIKE '%fault%' AND c.newtype ILIKE '%contact%' AND ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(c.geom, 3857), 1000)`

---

### 70. 🗺️ Find deposits within multiple distance thresholds
**Question:** "Find deposits within multiple distance thresholds from faults"

**What it tests:** Multiple ST_DWithin conditions  
**Expected:** `SELECT m.*, CASE WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 1000) THEN '0-1km' WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) THEN '1-5km' WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) THEN '5-10km' ELSE '>10km' END AS distance_category FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%'`

---

### Advanced Aggregations with Spatial

### 71. 📊🗺️ Count deposits per area, ordered by count
**Question:** "Count deposits per area, ordered by count"

**What it tests:** COUNT with spatial join, ORDER BY  
**Expected:** `SELECT g.gid, g.unit_name, COUNT(m.gid) AS deposit_count FROM geology_master g LEFT JOIN mods m ON ST_Intersects(ST_SetSRID(g.geom, 3857), ST_SetSRID(m.geom, 3857)) GROUP BY g.gid, g.unit_name ORDER BY deposit_count DESC`

---

### 72. 📊🗺️ Find average distance from deposits to faults by region
**Question:** "Find average distance from deposits to faults by region"

**What it tests:** AVG with GROUP BY and spatial function  
**Expected:** `SELECT m.region, AVG(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857))) AS avg_distance FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%' GROUP BY m.region`

---

### 73. 📊🗺️ Show areas with most deposits within 10km of faults
**Question:** "Show areas with most deposits within 10km of faults"

**What it tests:** COUNT with multiple spatial joins  
**Expected:** `SELECT g.gid, g.unit_name, COUNT(m.gid) AS deposit_count FROM geology_master g JOIN mods m ON ST_Intersects(ST_SetSRID(g.geom, 3857), ST_SetSRID(m.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) WHERE f.newtype ILIKE '%fault%' GROUP BY g.gid, g.unit_name ORDER BY deposit_count DESC`

---

### 74. 📊 Count deposits by commodity and region
**Question:** "Count deposits by commodity and region"

**What it tests:** COUNT with GROUP BY on multiple columns  
**Expected:** `SELECT major_comm, region, COUNT(*) AS count FROM mods GROUP BY major_comm, region`

---

### 75. 📊🗺️ Find total length of faults near zinc deposits
**Question:** "Find total length of faults near zinc deposits"

**What it tests:** SUM with ST_Length and spatial join  
**Expected:** `SELECT SUM(ST_Length(ST_SetSRID(f.geom, 3857))) AS total_length FROM geology_faults_contacts_master f JOIN mods m ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND f.newtype ILIKE '%fault%'`

---

### Top N with Spatial

### 76. 🗺️ Show top 10 zinc deposits closest to faults
**Question:** "Show top 10 zinc deposits closest to faults"

**What it tests:** ST_Distance with ORDER BY and LIMIT  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS distance FROM mods m, geology_faults_contacts_master f WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND f.newtype ILIKE '%fault%' ORDER BY distance ASC LIMIT 10`

---

### 77. 🗺️ Find 5 deposits farthest from contacts
**Question:** "Find 5 deposits farthest from contacts"

**What it tests:** ST_Distance with ORDER BY DESC  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS distance FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%contact%' ORDER BY distance DESC LIMIT 5`

---

### 78. 🗺️ Show top 20 high importance deposits near faults
**Question:** "Show top 20 high importance deposits near faults"

**What it tests:** ST_DWithin with importance filter and LIMIT  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE m.occ_imp ILIKE '%high%' AND f.newtype ILIKE '%fault%' ORDER BY m.occ_imp LIMIT 20`

---

### 79. 🗺️ Find 15 deposits with largest intersecting areas
**Question:** "Find 15 deposits with largest intersecting areas"

**What it tests:** ST_Area with ORDER BY DESC  
**Expected:** `SELECT m.*, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) ORDER BY intersection_area DESC LIMIT 15`

---

### 80. 🗺️ Show bottom 10 deposits by distance to nearest fault
**Question:** "Show bottom 10 deposits by distance to nearest fault"

**What it tests:** ST_Distance with ORDER BY DESC and LIMIT  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS distance FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%' ORDER BY distance DESC LIMIT 10`

---

### Complex Multi-Table Queries

### 81. 🗺️🔗 Find zinc deposits in volcanic areas within 5km of faults
**Question:** "Find zinc deposits in volcanic areas within 5km of faults"

**What it tests:** Multiple spatial joins with commodity and lithology filters  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%') AND f.newtype ILIKE '%fault%'`

---

### 82. 🗺️🔗 Show boreholes near deposits that are in sedimentary areas
**Question:** "Show boreholes near deposits that are in sedimentary areas"

**What it tests:** ST_DWithin + ST_Intersects with multiple tables  
**Expected:** `SELECT b.* FROM borholes b JOIN mods m ON ST_DWithin(ST_SetSRID(b.geom, 3857), ST_SetSRID(m.geom, 3857), 2000) JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE g.main_litho ILIKE '%sedimentary%' OR g.litho_fmly ILIKE '%sedimentary%'`

---

### 83. 🗺️🔗 Find samples within 2km of gold deposits that are near faults
**Question:** "Find samples within 2km of gold deposits that are near faults"

**What it tests:** Multiple ST_DWithin joins  
**Expected:** `SELECT s.* FROM surface_samples s JOIN mods m ON ST_DWithin(ST_SetSRID(s.geom, 3857), ST_SetSRID(m.geom, 3857), 2000) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%gold%' OR m.minor_comm ILIKE '%gold%') AND f.newtype ILIKE '%fault%'`

---

### 84. 🗺️🔗 Show deposits in areas that intersect with dikes
**Question:** "Show deposits in areas that intersect with dikes"

**What it tests:** ST_Intersects with dikes table  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_dikes_master d ON ST_Intersects(ST_SetSRID(g.geom, 3857), ST_SetSRID(d.geom, 3857))`

---

### 85. 🗺️🔗 Find deposits near contacts that are also near dikes
**Question:** "Find deposits near contacts that are also near dikes"

**What it tests:** Multiple ST_DWithin joins  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) JOIN geology_dikes_master d ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(d.geom, 3857), 5000) WHERE f.newtype ILIKE '%contact%'`

---

### Advanced Spatial Analysis

### 86. 🗺️ Find deposits within 5km of faults, calculate distance, and show if inside areas
**Question:** "Find deposits within 5km of faults, calculate distance, and show if inside areas"

**What it tests:** ST_DWithin + ST_Distance + ST_Intersects with CASE  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, CASE WHEN ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) THEN true ELSE false END AS inside_area FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) LEFT JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE f.newtype ILIKE '%fault%'`

---

### 87. 🗺️ Show deposits with distance to nearest fault and area of intersecting geology
**Question:** "Show deposits with distance to nearest fault and area of intersecting geology"

**What it tests:** ST_Distance + ST_Intersects + ST_Area  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area FROM mods m, geology_faults_contacts_master f, geology_master g WHERE f.newtype ILIKE '%fault%' AND ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) ORDER BY fault_distance LIMIT 50`

---

### 88. 🗺️ Find deposits within multiple buffer zones (1km, 5km, 10km) of faults
**Question:** "Find deposits within multiple buffer zones of faults"

**What it tests:** Multiple ST_DWithin with CASE  
**Expected:** `SELECT m.*, CASE WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 1000) THEN '0-1km' WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) THEN '1-5km' WHEN ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 10000) THEN '5-10km' ELSE '>10km' END AS buffer_zone FROM mods m, geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%'`

---

### 89. 🗺️ Show deposits with distance to fault and length of intersecting contacts
**Question:** "Show deposits with distance to fault and length of intersecting contacts"

**What it tests:** ST_Distance + ST_Length  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Length(ST_SetSRID(c.geom, 3857)) AS contact_length FROM mods m, geology_faults_contacts_master f, geology_faults_contacts_master c WHERE f.newtype ILIKE '%fault%' AND c.newtype ILIKE '%contact%' AND ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(c.geom, 3857), 1000)`

---

### 90. 🗺️ Find deposits in areas with specific lithology near faults
**Question:** "Find deposits in basalt areas near faults"

**What it tests:** ST_Intersects + ST_DWithin with lithology filter  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE g.main_litho ILIKE '%basalt%' AND f.newtype ILIKE '%fault%'`

---

### Ultra Complex Queries

### 91. 🗺️🔗📊 Find top 10 high importance zinc deposits in volcanic areas within 5km of faults, ordered by importance
**Question:** "Find top 10 high importance zinc deposits in volcanic areas within 5km of faults, ordered by importance"

**What it tests:** Multiple spatial joins + filters + ORDER BY + LIMIT  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND m.occ_imp ILIKE '%high%' AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%') AND f.newtype ILIKE '%fault%' ORDER BY m.occ_imp LIMIT 10`

---

### 92. 🗺️🔗📊 Show deposits in sedimentary areas near contacts, calculate distance and area
**Question:** "Show deposits in sedimentary areas near contacts, calculate distance and area"

**What it tests:** ST_Intersects + ST_DWithin + ST_Distance + ST_Area  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS contact_distance, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE g.main_litho ILIKE '%sedimentary%' AND f.newtype ILIKE '%contact%'`

---

### 93. 🗺️🔗 Find deposits within 3km of faults AND 2km of contacts, in igneous areas
**Question:** "Find deposits within 3km of faults AND 2km of contacts, in igneous areas"

**What it tests:** Multiple ST_DWithin + ST_Intersects  
**Expected:** `SELECT m.* FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 3000) JOIN geology_faults_contacts_master c ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(c.geom, 3857), 2000) JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE f.newtype ILIKE '%fault%' AND c.newtype ILIKE '%contact%' AND (g.main_litho ILIKE '%igneous%' OR g.litho_fmly ILIKE '%igneous%')`

---

### 94. 🗺️🔗📊 Count deposits by region and commodity, only for those near faults
**Question:** "Count deposits by region and commodity, only for those near faults"

**What it tests:** COUNT with GROUP BY and spatial join  
**Expected:** `SELECT m.region, m.major_comm, COUNT(*) AS count FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE f.newtype ILIKE '%fault%' GROUP BY m.region, m.major_comm`

---

### 95. 🗺️🔗 Show deposits with distance to nearest fault, contact, and dike
**Question:** "Show deposits with distance to nearest fault, contact, and dike"

**What it tests:** Multiple ST_Distance calculations  
**Expected:** `SELECT m.*, (SELECT MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857))) FROM geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%') AS fault_distance, (SELECT MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(c.geom, 3857))) FROM geology_faults_contacts_master c WHERE c.newtype ILIKE '%contact%') AS contact_distance, (SELECT MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(d.geom, 3857))) FROM geology_dikes_master d) AS dike_distance FROM mods m`

---

### 96. 🗺️🔗 Find deposits in Jiddah terrane areas that intersect with volcanic formations
**Question:** "Find deposits in Jiddah terrane areas that intersect with volcanic formations"

**What it tests:** ST_Intersects with structural and lithology filters  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE (m.structural ILIKE '%jiddah%' OR m.reg_struct ILIKE '%jiddah%') AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%')`

---

### 97. 🗺️🔗📊 Show top 15 high importance deposits in volcanic areas near faults
**Question:** "Show top 15 high importance deposits in volcanic areas near faults"

**What it tests:** Multiple spatial joins + importance filter + LIMIT  
**Expected:** `SELECT m.* FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE m.occ_imp ILIKE '%high%' AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%') AND f.newtype ILIKE '%fault%' ORDER BY m.occ_imp LIMIT 15`

---

### 98. 🗺️🔗📊 Find deposits within 5km of faults, calculate distance, show area of intersecting geology, and count nearby samples
**Question:** "Find deposits within 5km of faults, calculate distance, show area of intersecting geology, and count nearby samples"

**What it tests:** Multiple spatial operations + COUNT aggregation  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area, (SELECT COUNT(*) FROM surface_samples s WHERE ST_DWithin(ST_SetSRID(s.geom, 3857), ST_SetSRID(m.geom, 3857), 2000)) AS nearby_samples_count FROM mods m JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) LEFT JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) WHERE f.newtype ILIKE '%fault%'`

---

### 99. 🗺️🔗 Show deposits in sedimentary areas near contacts, with distance to nearest fault and dike
**Question:** "Show deposits in sedimentary areas near contacts, with distance to nearest fault and dike"

**What it tests:** ST_Intersects + ST_DWithin + multiple ST_Distance  
**Expected:** `SELECT m.*, (SELECT MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857))) FROM geology_faults_contacts_master f WHERE f.newtype ILIKE '%fault%') AS fault_distance, (SELECT MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(d.geom, 3857))) FROM geology_dikes_master d) AS dike_distance FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master c ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(c.geom, 3857), 5000) WHERE g.main_litho ILIKE '%sedimentary%' AND c.newtype ILIKE '%contact%'`

---

### 100. 🗺️🔗📊 Find zinc deposits in volcanic areas within 5km of faults, calculate all distances and areas, show top 20 by importance
**Question:** "Find zinc deposits in volcanic areas within 5km of faults, calculate all distances and areas, show top 20 by importance"

**What it tests:** Ultimate combination of all spatial operations + aggregations + filters  
**Expected:** `SELECT m.*, ST_Distance(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857)) AS fault_distance, ST_Area(ST_Intersection(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857))) AS intersection_area FROM mods m JOIN geology_master g ON ST_Intersects(ST_SetSRID(m.geom, 3857), ST_SetSRID(g.geom, 3857)) JOIN geology_faults_contacts_master f ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_SetSRID(f.geom, 3857), 5000) WHERE (m.major_comm ILIKE '%zinc%' OR m.minor_comm ILIKE '%zinc%') AND (g.litho_fmly ILIKE '%volcanic%' OR g.family_dv ILIKE '%volcanic%') AND f.newtype ILIKE '%fault%' ORDER BY m.occ_imp, fault_distance LIMIT 20`

---

## Testing Guidelines

Each question is designed to test specific system capabilities:

1. **Questions 1-30**: Basic single-table queries, simple filters
2. **Questions 31-60**: Spatial operations, distance calculations, aggregations
3. **Questions 61-100**: Complex multi-table spatial joins, advanced aggregations, ultimate combinations

## Expected System Behavior

### ✅ Spatial Operations
- System should use `ST_SetSRID(geom, 3857)` for all geometries
- Use `ST_Transform(ST_SetSRID(geom, 3857), 4326)` for output
- For polygons/lines: MUST include `ST_AsGeoJSON(...) AS geojson_geom` for map visualization
- ST_DWithin distances are in **meters**
- ST_Intersects for point-in-polygon and line intersections
- ST_Distance returns distance in meters (SRID 3857)

### ✅ Fuzzy Matching
- System should use `ILIKE` for case-insensitive matching
- Use wildcards `%` for partial matches
- Handle region names with "Region" suffix
- Handle semicolon-separated values in minor_comm

### ✅ Query Limits
- Spatial searches: LIMIT 50-100
- List queries: LIMIT 50
- Aggregations: appropriate grouping
- Maximum: LIMIT 100 (hard cap unless user specifies more)

### ✅ Proper JOINs
- Correct spatial relationships (ST_Intersects, ST_DWithin)
- Appropriate table aliases (m for mods, g for geology_master, f for faults, etc.)
- No Cartesian products (use proper JOIN conditions)

### ✅ Geometry Output
- Points: Use `ST_Y(ST_Transform(...)) AS latitude, ST_X(ST_Transform(...)) AS longitude`
- Polygons/Lines: Use `ST_AsGeoJSON(ST_Transform(...)) AS geojson_geom`
- Always set SRID to 3857 before operations, transform to 4326 for output

---

## Success Criteria

A well-functioning Geospatial Text-to-SQL system should:

1. ✅ Handle all 100 questions without errors
2. ✅ Generate syntactically correct SQL with proper PostGIS functions
3. ✅ Use appropriate spatial operations (ST_Intersects, ST_DWithin, ST_Distance)
4. ✅ Include geojson_geom for polygons and lines
5. ✅ Apply all filters correctly (regions, commodities, importance, etc.)
6. ✅ Return reasonable result sets (proper LIMIT)
7. ✅ Use real data values from the database
8. ✅ Handle MultiPolygon and MultiLineString geometries correctly

Good luck testing! 🚀
