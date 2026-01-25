"""
=============================================================================
TRAIN PROSPECTIVITY MODEL (Multi-Class: Low/Medium/High)
=============================================================================
Based on the ML.ipynb notebook from the 'last' folder.

This script:
1. Loads data from mods, geology_master, geology_faults_contacts_master, geology_dikes_master
2. Joins spatial features (distance to faults/dikes)
3. Encodes categorical features
4. Trains XGBoost model with SMOTE
5. Saves model and preprocessing artifacts
=============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Add parent to path for config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings

print("=" * 60)
print("TRAINING PROSPECTIVITY MODEL (Multi-Class)")
print("=" * 60)

# =============================================================================
# 1. DATABASE CONNECTION
# =============================================================================
import sqlalchemy as sql
import geopandas as gpd

db_url = f'postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}'
print(f"Connecting to: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
conn = sql.create_engine(db_url)

# =============================================================================
# 2. LOAD DATA
# =============================================================================
print("\n📥 Loading data from database...")

# Load mods (mineral deposits)
query_mods = """
SELECT 
    ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude,
    ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude,
    COALESCE(elevation::numeric, 0) as elevation,
    quad,
    reg_struct,
    host_rocks,
    country_ro,
    gitology,
    alteration,
    min_morpho,
    occ_imp,
    ST_Transform(ST_SetSRID(geom, 3857), 4326) as geom
FROM mods
WHERE (major_comm IS NOT NULL AND major_comm != '')
    OR (minor_comm IS NOT NULL AND minor_comm != '');
"""
gdf = gpd.read_postgis(query_mods, conn, geom_col="geom")
print(f"✅ Loaded {len(gdf)} mineral deposits")

# Load geology polygons
query_poly = """
SELECT 
    litho_fmly,
    family_dv,
    family_sdv,
    main_litho,
    met_facies,
    geom
FROM geology_master;
"""
gdf_poly = gpd.read_postgis(query_poly, conn, geom_col="geom")
print(f"✅ Loaded {len(gdf_poly)} geology polygons")

# =============================================================================
# 3. SPATIAL JOIN - GET GEOLOGY INFO FOR EACH POINT
# =============================================================================
print("\n🔗 Joining points with geology polygons...")

# Ensure same CRS
mods_projected = gdf.to_crs(gdf_poly.crs)

# Spatial join
joined = gpd.sjoin(mods_projected, gdf_poly, how='inner', predicate='intersects')
if 'index_right' in joined.columns:
    joined = joined.drop(columns=['index_right'])
print(f"✅ {len(joined)} points intersect with geology polygons")

# Fill missing values
joined["reg_struct"] = joined["reg_struct"].fillna("Undefined")
joined["host_rocks"] = joined["host_rocks"].fillna("Unknown")
joined["country_ro"] = joined["country_ro"].fillna("Unknown")
joined["gitology"] = joined["gitology"].fillna("Unknown")
joined["alteration"] = joined["alteration"].fillna("Unknown")
joined["min_morpho"] = joined["min_morpho"].fillna("Unknown")

# =============================================================================
# 4. CALCULATE DISTANCE TO FAULTS
# =============================================================================
print("\n📏 Calculating distance to faults...")

query_faults = """
SELECT
    m.geom AS geom,
    MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857))) AS distance_to_nearest_line_m,
    COUNT(*) FILTER (
        WHERE ST_DWithin(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857), 5000)
    ) AS lines_within_5000m
FROM mods m
JOIN geology_faults_contacts_master f
  ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857), 10000)
GROUP BY m.geom;
"""
point_near_f = gpd.read_postgis(query_faults, conn, geom_col="geom")
print(f"✅ Calculated fault distances for {len(point_near_f)} points")

# Merge with main data
joined['lon'] = joined.geometry.x.round(6)
joined['lat'] = joined.geometry.y.round(6)
point_near_f['lon'] = point_near_f.geometry.x.round(6)
point_near_f['lat'] = point_near_f.geometry.y.round(6)

joined_f = joined.merge(
    point_near_f[['lat', 'lon', 'distance_to_nearest_line_m', 'lines_within_5000m']],
    on=['lat', 'lon'],
    how='left'
)
joined_f = joined_f.drop(columns=['lat', 'lon'])

# =============================================================================
# 5. CALCULATE DISTANCE TO DIKES
# =============================================================================
print("\n📏 Calculating distance to dikes...")

query_dikes = """
SELECT
    m.geom AS geom,
    MIN(ST_Distance(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857))) AS distance_to_nearest_line_d,
    COUNT(*) FILTER (
        WHERE ST_DWithin(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857), 5000)
    ) AS dikes_within_5000m
FROM mods m
JOIN geology_dikes_master f
  ON ST_DWithin(ST_SetSRID(m.geom, 3857), ST_Transform(f.geom, 3857), 10000)
GROUP BY m.geom;
"""
try:
    point_near_d = gpd.read_postgis(query_dikes, conn, geom_col="geom")
    print(f"✅ Calculated dike distances for {len(point_near_d)} points")
    
    # Merge
    joined_f['lon'] = joined_f.geometry.x.round(6)
    joined_f['lat'] = joined_f.geometry.y.round(6)
    point_near_d['lon'] = point_near_d.geometry.x.round(6)
    point_near_d['lat'] = point_near_d.geometry.y.round(6)
    
    joined_d = joined_f.merge(
        point_near_d[['lat', 'lon', 'distance_to_nearest_line_d', 'dikes_within_5000m']],
        on=['lat', 'lon'],
        how='left'
    )
    joined_d = joined_d.drop(columns=['lat', 'lon'])
except Exception as e:
    print(f"⚠️ No dikes table or error: {e}")
    joined_d = joined_f
    joined_d['distance_to_nearest_line_d'] = 10000
    joined_d['dikes_within_5000m'] = 0

# Fill NaN distances
joined_d['distance_to_nearest_line_m'] = joined_d['distance_to_nearest_line_m'].fillna(10000)
joined_d['lines_within_5000m'] = joined_d['lines_within_5000m'].fillna(0)
joined_d['distance_to_nearest_line_d'] = joined_d['distance_to_nearest_line_d'].fillna(10000)
joined_d['dikes_within_5000m'] = joined_d['dikes_within_5000m'].fillna(0)

# =============================================================================
# 6. ENCODE TARGET
# =============================================================================
print("\n🎯 Processing target variable...")

# Map target to 3 classes
target_map = {
    'Very Low': 'Low',
    'Low': 'Low',
    'Medium': 'Medium',
    'High': 'High',
    'Very high': 'High',
    'Very High': 'High'
}

df = joined_d.copy()
df['occ_imp'] = df['occ_imp'].map(target_map)
df = df[df['occ_imp'].isin(['Low', 'Medium', 'High'])]

print(f"Class distribution:")
print(df['occ_imp'].value_counts())

# =============================================================================
# 7. ENCODE CATEGORICAL FEATURES
# =============================================================================
print("\n🔢 Encoding categorical features...")

from sklearn.preprocessing import MultiLabelBinarizer

single_valued_cols = ['litho_fmly', 'family_dv', 'met_facies', 'quad']
multi_valued_cols = ['family_sdv', 'main_litho', 'reg_struct', 'host_rocks', 
                     'country_ro', 'gitology', 'alteration', 'min_morpho']

TOP_N = 10
top_classes = {}

# Single-valued columns
for col in single_valued_cols:
    if col in df.columns:
        top = df[col].value_counts().head(TOP_N).index.tolist()
        top_classes[col] = top
        df[col] = df[col].apply(lambda x: x if x in top else 'Other')
        dummies = pd.get_dummies(df[col], prefix=col)
        df = pd.concat([df, dummies], axis=1)
        df.drop(columns=[col], inplace=True)

# Multi-valued columns
for col in multi_valued_cols:
    if col in df.columns:
        df[col + '_list'] = df[col].fillna('').apply(
            lambda x: [v.strip() for v in x.split(';') if v.strip()]
        )
        all_values = df[col + '_list'].explode()
        top = all_values.value_counts().head(TOP_N).index.tolist()
        top_classes[col] = top
        
        df[col + '_top'] = df[col + '_list'].apply(
            lambda vals: [v if v in top else 'Other' for v in vals]
        )
        
        mlb = MultiLabelBinarizer()
        encoded = pd.DataFrame(
            mlb.fit_transform(df[col + '_top']),
            columns=[f"{col}_{c}" for c in mlb.classes_],
            index=df.index
        )
        df = pd.concat([df, encoded], axis=1)
        df.drop(columns=[col, col + '_list', col + '_top'], inplace=True)

# Drop age_ma if exists
if 'age_ma' in df.columns:
    df.drop(columns=['age_ma'], inplace=True)

print(f"✅ Encoded {len(single_valued_cols)} single-valued and {len(multi_valued_cols)} multi-valued columns")

# =============================================================================
# 8. PREPARE FEATURES AND TARGET
# =============================================================================
print("\n📊 Preparing features...")

ordinal_map = {'Low': 0, 'Medium': 1, 'High': 2}

drop_cols = ['occ_imp', 'geom']
for col in df.columns:
    if df[col].dtype == 'object' and col not in drop_cols:
        drop_cols.append(col)

X = df.drop(columns=[c for c in drop_cols if c in df.columns])
y = df['occ_imp'].map(ordinal_map).values

print(f"Feature matrix shape: {X.shape}")

# Handle missing values
for col in X.columns:
    if X[col].dtype in ['float64', 'int64']:
        X[col] = X[col].fillna(X[col].median())
    else:
        X[col] = X[col].fillna(0)

# =============================================================================
# 9. FEATURE SELECTION
# =============================================================================
print("\n🎯 Selecting top features...")

from sklearn.feature_selection import SelectKBest, mutual_info_classif

k_best = min(50, X.shape[1])
selector = SelectKBest(score_func=mutual_info_classif, k=k_best)
X_selected = selector.fit_transform(X, y)

selected_mask = selector.get_support()
selected_features = X.columns[selected_mask].tolist()
X_selected_df = pd.DataFrame(X_selected, columns=selected_features, index=X.index)

print(f"✅ Selected {len(selected_features)} features")

# =============================================================================
# 10. TRAIN-TEST SPLIT
# =============================================================================
print("\n📊 Splitting data...")

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X_selected_df, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"Training set: {X_train.shape}")
print(f"Test set: {X_test.shape}")

# =============================================================================
# 11. SCALE FEATURES
# =============================================================================
print("\n⚖️ Scaling numeric features...")

from sklearn.preprocessing import StandardScaler

numeric_cols = ['longitude', 'latitude', 'elevation',
                'distance_to_nearest_line_m', 'lines_within_5000m',
                'distance_to_nearest_line_d', 'dikes_within_5000m']
numeric_cols = [c for c in numeric_cols if c in X_train.columns]

scaler = StandardScaler()
X_train_scaled = X_train.copy()
X_test_scaled = X_test.copy()

if numeric_cols:
    X_train_scaled[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
    X_test_scaled[numeric_cols] = scaler.transform(X_test[numeric_cols])
    print(f"✅ Scaled {len(numeric_cols)} numeric features")

# =============================================================================
# 12. APPLY SMOTE
# =============================================================================
print("\n⚖️ Applying SMOTE for class balancing...")

try:
    from imblearn.over_sampling import SMOTE
    
    print(f"Before SMOTE: {pd.Series(y_train).value_counts().to_dict()}")
    smote = SMOTE(random_state=42, k_neighbors=5)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)
    print(f"After SMOTE: {pd.Series(y_train_resampled).value_counts().to_dict()}")
except ImportError:
    print("⚠️ imbalanced-learn not installed, skipping SMOTE")
    X_train_resampled = X_train_scaled
    y_train_resampled = y_train

# =============================================================================
# 13. TRAIN MODEL
# =============================================================================
print("\n🚀 Training XGBoost model...")

from xgboost import XGBClassifier
from sklearn.metrics import classification_report, balanced_accuracy_score

model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.05,
    min_child_weight=15,
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=0.5,
    reg_lambda=2.0,
    random_state=42,
    use_label_encoder=False,
    eval_metric='mlogloss'
)

model.fit(X_train_resampled, y_train_resampled)

# Evaluate
y_pred = model.predict(X_test_scaled)
bal_acc = balanced_accuracy_score(y_test, y_pred)

print(f"\n📊 Test Balanced Accuracy: {bal_acc:.2%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Low', 'Medium', 'High']))

# =============================================================================
# 14. SAVE MODEL AND ARTIFACTS
# =============================================================================
print("\n💾 Saving model and artifacts...")

import joblib

output_dir = os.path.dirname(__file__)

# Save model
joblib.dump(model, os.path.join(output_dir, 'prospectivity_model.pkl'))

# Save scaler
joblib.dump(scaler, os.path.join(output_dir, 'prospectivity_scaler.pkl'))

# Save feature info
feature_info = {
    'selected_features': selected_features,
    'single_valued_cols': single_valued_cols,
    'multi_valued_cols': multi_valued_cols,
    'top_classes': top_classes,
    'numeric_cols': numeric_cols,
    'ordinal_map': ordinal_map
}
joblib.dump(feature_info, os.path.join(output_dir, 'prospectivity_features.pkl'))

print("\n" + "=" * 60)
print("✅ TRAINING COMPLETE!")
print("=" * 60)
print(f"Model saved: prospectivity_model.pkl")
print(f"Scaler saved: prospectivity_scaler.pkl")
print(f"Features saved: prospectivity_features.pkl")
print(f"Balanced Accuracy: {bal_acc:.2%}")
print("=" * 60)
