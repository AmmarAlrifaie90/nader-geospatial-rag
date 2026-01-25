"""
=============================================================================
MINERAL PROSPECTIVITY PREDICTOR
=============================================================================
Ensemble ML model (XGBoost + LightGBM) for predicting
mineral deposit importance (High Value vs Background).

Uses pre-trained models from Machine_Learning folder.
Gracefully handles missing CatBoost (uses XGBoost + LightGBM only).
=============================================================================
"""

import os
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Path to ML models - files are now in the same folder as this script
ML_MODEL_DIR = os.path.dirname(__file__)  # backend/ml/
MODEL_PATH = os.path.join(ML_MODEL_DIR, "Ensemble_Pack_v1.pkl")
ENCODER_PATH = os.path.join(ML_MODEL_DIR, "Ensemble_Encoder.pkl")

# Required features for the model
REQUIRED_FEATURES = [
    "elevation",
    "quad", 
    "reg_struct",
    "host_rocks",
    "country_ro",
    "gitology",
    "alteration",
    "min_morpho"
]

# Feature engineering columns
ENGINEERED_FEATURES = [
    "rock_struct",  # host_rocks + "_" + reg_struct
    "rock_morpho"   # host_rocks + "_" + min_morpho
]

# Check which ML libraries are available
CATBOOST_AVAILABLE = False
try:
    import catboost
    CATBOOST_AVAILABLE = True
except ImportError:
    logger.info("CatBoost not available - will use XGBoost + LightGBM only")


class MineralPredictor:
    """
    Mineral Prospectivity Predictor using ensemble ML models.
    
    Predicts whether a mineral deposit site is "High Value" or "Background"
    based on geological and spatial features.
    
    Works with XGBoost + LightGBM even if CatBoost is not installed.
    """
    
    def __init__(self):
        self.model_pack = None
        self.encoder = None
        self.is_loaded = False
        self.threshold = 0.42  # Default threshold from training
        self.use_stacking = True
        self.has_catboost = CATBOOST_AVAILABLE
        
        # Try to load models
        self._load_models()
    
    def _load_models(self):
        """Load the pre-trained ensemble models."""
        try:
            import joblib
            
            logger.info(f"Looking for ML models in: {ML_MODEL_DIR}")
            logger.info(f"Model path: {MODEL_PATH}")
            logger.info(f"Encoder path: {ENCODER_PATH}")
            
            if not os.path.exists(MODEL_PATH):
                logger.warning(f"Model file not found: {MODEL_PATH}")
                logger.warning(f"Directory exists: {os.path.exists(ML_MODEL_DIR)}")
                if os.path.exists(ML_MODEL_DIR):
                    logger.warning(f"Directory contents: {os.listdir(ML_MODEL_DIR)}")
                return
            
            if not os.path.exists(ENCODER_PATH):
                logger.warning(f"Encoder file not found: {ENCODER_PATH}")
                return
            
            logger.info("Loading ML models...")
            self.model_pack = joblib.load(MODEL_PATH)
            self.encoder = joblib.load(ENCODER_PATH)
            
            # Extract saved settings
            if 'threshold' in self.model_pack:
                self.threshold = self.model_pack['threshold']
            if 'use_stacking' in self.model_pack:
                self.use_stacking = self.model_pack['use_stacking']
            
            # Check which models we can actually use
            available_models = []
            if 'xgb' in self.model_pack:
                available_models.append('XGBoost')
            if 'lgbm' in self.model_pack:
                available_models.append('LightGBM')
            if 'cat' in self.model_pack and self.has_catboost:
                available_models.append('CatBoost')
            
            self.is_loaded = True
            logger.info(f"✅ ML models loaded: {', '.join(available_models)} (threshold={self.threshold:.2f})")
            
            if not self.has_catboost and 'cat' in self.model_pack:
                logger.info("Note: CatBoost model present but library not installed - using XGBoost + LightGBM")
            
        except ImportError as e:
            logger.warning(f"ML dependencies not installed: {e}")
            logger.info("Install with: pip install xgboost lightgbm category_encoders")
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
    
    def predict(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict mineral prospectivity for given data points.
        
        Args:
            data: List of dicts with features (from database query)
            
        Returns:
            List of dicts with predictions added
        """
        if not self.is_loaded:
            raise RuntimeError("ML models not loaded. Check if model files exist.")
        
        if not data:
            return []
        
        try:
            import pandas as pd
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Check for required features
            missing = [f for f in REQUIRED_FEATURES if f not in df.columns]
            if missing:
                logger.warning(f"Missing features: {missing}. Using 'Unknown' as default.")
                for col in missing:
                    df[col] = "Unknown"
            
            # Fill NaN values
            df.fillna("Unknown", inplace=True)
            
            # Feature engineering (same as training)
            df["rock_struct"] = df["host_rocks"].astype(str) + "_" + df["reg_struct"].astype(str)
            df["rock_morpho"] = df["host_rocks"].astype(str) + "_" + df["min_morpho"].astype(str)
            
            # Ensure elevation is numeric
            df["elevation"] = pd.to_numeric(df["elevation"], errors="coerce").fillna(0)
            
            # Select features for model
            feature_cols = REQUIRED_FEATURES + ENGINEERED_FEATURES
            X = df[feature_cols].copy()
            
            # Encode features
            X_enc = self.encoder.transform(X)
            
            # Get predictions from available models
            predictions_list = []
            
            if 'xgb' in self.model_pack:
                p1 = self.model_pack['xgb'].predict_proba(X_enc)[:, 1]
                predictions_list.append(p1)
            
            if 'lgbm' in self.model_pack:
                p2 = self.model_pack['lgbm'].predict_proba(X_enc)[:, 1]
                predictions_list.append(p2)
            
            # Only use CatBoost if library is available
            if 'cat' in self.model_pack and self.has_catboost:
                p3 = self.model_pack['cat'].predict_proba(X_enc)[:, 1]
                predictions_list.append(p3)
            
            if not predictions_list:
                raise RuntimeError("No models available for prediction")
            
            # Combine predictions
            # If we have all 3 models and stacking meta-model, use it
            if (len(predictions_list) == 3 and 
                self.use_stacking and 
                'meta' in self.model_pack):
                P = np.vstack(predictions_list).T
                probabilities = self.model_pack['meta'].predict_proba(P)[:, 1]
            else:
                # Average available models
                probabilities = np.mean(predictions_list, axis=0)
            
            # Apply threshold
            predictions = (probabilities >= self.threshold).astype(int)
            
            # Add results to original data
            results = []
            for i, row in enumerate(data):
                result = row.copy()
                result['ml_probability'] = round(float(probabilities[i]), 4)
                result['ml_prediction'] = "High Value" if predictions[i] == 1 else "Background"
                result['ml_prediction_binary'] = int(predictions[i])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def predict_from_query_result(
        self, 
        query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add ML predictions to a query result from the SQL generator.
        
        Args:
            query_result: Result from SQL generator with 'data' key
            
        Returns:
            Same result with predictions added to data
        """
        if not query_result.get("success") or not query_result.get("data"):
            return query_result
        
        if not self.is_loaded:
            logger.warning("ML models not loaded, returning original result")
            return query_result
        
        try:
            # Get predictions
            data_with_predictions = self.predict(query_result["data"])
            
            # Count high value predictions
            high_value_count = sum(
                1 for d in data_with_predictions 
                if d.get("ml_prediction") == "High Value"
            )
            
            # Update result
            query_result["data"] = data_with_predictions
            query_result["ml_predictions"] = {
                "total": len(data_with_predictions),
                "high_value": high_value_count,
                "background": len(data_with_predictions) - high_value_count,
                "threshold": self.threshold
            }
            
            return query_result
            
        except Exception as e:
            logger.error(f"Failed to add predictions: {e}")
            return query_result
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        available_models = []
        if self.model_pack:
            if 'xgb' in self.model_pack:
                available_models.append('XGBoost')
            if 'lgbm' in self.model_pack:
                available_models.append('LightGBM')
            if 'cat' in self.model_pack and self.has_catboost:
                available_models.append('CatBoost')
        
        return {
            "is_loaded": self.is_loaded,
            "threshold": self.threshold,
            "use_stacking": self.use_stacking,
            "available_models": available_models,
            "catboost_available": self.has_catboost,
            "required_features": REQUIRED_FEATURES,
            "model_path": MODEL_PATH,
            "encoder_path": ENCODER_PATH
        }


# =============================================================================
# SINGLETON
# =============================================================================

_predictor: Optional[MineralPredictor] = None


def get_mineral_predictor() -> MineralPredictor:
    """Get or create the global mineral predictor."""
    global _predictor
    if _predictor is None:
        _predictor = MineralPredictor()
    return _predictor
