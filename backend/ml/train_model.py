"""
Train XGBoost + LightGBM ensemble model (without CatBoost).
Run this script once to create model files that can be loaded without CatBoost.
"""

import pandas as pd
import numpy as np
import sqlalchemy as sql
import xgboost as xgb
import lightgbm as lgb
import joblib
import os
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score
from category_encoders import TargetEncoder

print("=" * 60)
print("TRAINING ML MODEL (XGBoost + LightGBM)")
print("=" * 60)

# 1. Connect to Database using app config
db_connection_str = f'postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}'
print(f"Connecting to: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
db_connection = sql.create_engine(db_connection_str)

# 2. Load data
# Note: Using same table as main app (mods without schema prefix)
MASTER_QUERY = """
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
    occ_imp
FROM mods
WHERE occ_imp IS NOT NULL
"""

print("Loading data from database...")
df = pd.read_sql(MASTER_QUERY, db_connection)
print(f"✅ Loaded {len(df)} rows")

# Basic cleaning
df.fillna('Unknown', inplace=True)

# 3. Define Target
df['target'] = df['occ_imp'].apply(lambda x: 1 if x == 'High' else 0)

# 4. Feature Engineering
df['rock_struct'] = df['host_rocks'] + "_" + df['reg_struct']
df['rock_morpho'] = df['host_rocks'] + "_" + df['min_morpho']

# 5. Spatial Blocks
df['grid_id'] = (df['longitude'] // 0.1).astype(str) + '_' + (df['latitude'] // 0.1).astype(str)

# 6. Select Features
drop_cols = ['occ_imp', 'target', 'grid_id', 'longitude', 'latitude']
feature_cols = [c for c in df.columns if c not in drop_cols]
cat_cols = df[feature_cols].select_dtypes(include=['object']).columns.tolist()

X = df[feature_cols]
y = df['target']
groups = df['grid_id']

print(f"✅ Features: {len(feature_cols)}")
print(f"✅ Target distribution: {y.value_counts().to_dict()}")

# 7. Initialize Models
ratio = float(np.sum(y == 0)) / np.sum(y == 1)

clf_xgb = xgb.XGBClassifier(
    n_estimators=1200,
    learning_rate=0.03,
    max_depth=6,
    min_child_weight=2,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=2.0,
    scale_pos_weight=ratio,
    tree_method="hist",
    n_jobs=-1,
    random_state=42,
    eval_metric="logloss",
)

clf_lgbm = lgb.LGBMClassifier(
    n_estimators=5000,
    learning_rate=0.03,
    num_leaves=31,
    min_child_samples=30,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=2.0,
    class_weight="balanced",
    verbose=-1,
    n_jobs=-1,
    random_state=42,
)

# 8. Cross-Validation
print("\n🚀 Starting Cross-Validation...")
gkf = GroupKFold(n_splits=5)

p_xgb_oof = np.zeros(len(y))
p_lgbm_oof = np.zeros(len(y))
best_lgbm = []
fold_scores = []

for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=groups)):
    X_train_raw, X_val_raw = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    # Fit encoder on TRAIN ONLY
    encoder_fold = TargetEncoder(cols=cat_cols, smoothing=5.0)
    X_train = encoder_fold.fit_transform(X_train_raw, y_train)
    X_val = encoder_fold.transform(X_val_raw)
    
    # Train XGBoost
    clf_xgb.fit(X_train, y_train)
    
    # Train LightGBM with early stopping
    clf_lgbm.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="binary_logloss",
        callbacks=[lgb.early_stopping(stopping_rounds=100, verbose=False)],
    )
    
    if hasattr(clf_lgbm, "best_iteration_") and clf_lgbm.best_iteration_:
        best_lgbm.append(int(clf_lgbm.best_iteration_))
    
    # Predictions
    p1 = clf_xgb.predict_proba(X_val)[:, 1]
    p2 = clf_lgbm.predict_proba(X_val)[:, 1]
    p_avg = (p1 + p2) / 2
    
    p_xgb_oof[val_idx] = p1
    p_lgbm_oof[val_idx] = p2
    
    acc = balanced_accuracy_score(y_val, (p_avg >= 0.5).astype(int))
    fold_scores.append(acc)
    print(f"  Fold {fold+1}: Balanced Accuracy = {acc:.2%}")

print(f"\n🏆 CV Balanced Accuracy: {np.mean(fold_scores):.2%}")

# 9. Find best threshold
p_avg_oof = (p_xgb_oof + p_lgbm_oof) / 2
thresholds = np.linspace(0.05, 0.95, 91)
accs = [balanced_accuracy_score(y, (p_avg_oof >= t).astype(int)) for t in thresholds]
best_idx = int(np.argmax(accs))
best_thresh = float(thresholds[best_idx])
best_acc = float(accs[best_idx])
print(f"🎯 Best threshold: {best_thresh:.2f} (Balanced Acc = {best_acc:.2%})")

# 10. Stacking meta-model
P_oof = np.vstack([p_xgb_oof, p_lgbm_oof]).T
meta = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
meta.fit(P_oof, y)

p_meta_oof = meta.predict_proba(P_oof)[:, 1]
accs_meta = [balanced_accuracy_score(y, (p_meta_oof >= t).astype(int)) for t in thresholds]
best_idx_meta = int(np.argmax(accs_meta))
best_thresh_meta = float(thresholds[best_idx_meta])
best_acc_meta = float(accs_meta[best_idx_meta])
print(f"🎯 Stacking threshold: {best_thresh_meta:.2f} (Balanced Acc = {best_acc_meta:.2%})")

use_stacking = best_acc_meta >= best_acc
chosen_thresh = best_thresh_meta if use_stacking else best_thresh
print(f"✅ Using {'STACKING' if use_stacking else 'AVERAGE'}")

# 11. Train final models on ALL data
print("\n🔒 Training final models on ALL data...")
encoder = TargetEncoder(cols=cat_cols, smoothing=5.0)
X_enc = encoder.fit_transform(X, y)

final_lgbm_estimators = int(np.median(best_lgbm)) if best_lgbm else 500

clf_xgb_final = xgb.XGBClassifier(**{**clf_xgb.get_params(), "n_estimators": 1200})
clf_lgbm_final = lgb.LGBMClassifier(**{**clf_lgbm.get_params(), "n_estimators": final_lgbm_estimators})

clf_xgb_final.fit(X_enc, y)
clf_lgbm_final.fit(X_enc, y)

# 12. Save models
model_pack = {
    'xgb': clf_xgb_final,
    'lgbm': clf_lgbm_final,
    'meta': meta,
    'use_stacking': bool(use_stacking),
    'threshold': float(chosen_thresh),
}

output_dir = os.path.dirname(__file__)
joblib.dump(model_pack, os.path.join(output_dir, 'Ensemble_Pack_v1.pkl'))
joblib.dump(encoder, os.path.join(output_dir, 'Ensemble_Encoder.pkl'))

print("\n" + "=" * 60)
print("✅ DONE! Models saved:")
print(f"   - Ensemble_Pack_v1.pkl")
print(f"   - Ensemble_Encoder.pkl")
print(f"   - Threshold: {chosen_thresh:.2f}")
print(f"   - Accuracy: {best_acc_meta:.2%}")
print("=" * 60)
