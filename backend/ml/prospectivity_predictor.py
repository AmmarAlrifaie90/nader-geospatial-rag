"""
=============================================================================
MINERAL PROSPECTIVITY PREDICTOR (Multi-Class)
=============================================================================
Predicts mineral deposit importance: Low, Medium, High

Features:
- Location (longitude, latitude, elevation)
- Geology polygon features (litho_fmly, family_dv, family_sdv, main_litho, met_facies)
- Distance to faults/contacts
- Distance to dikes
- Deposit features (reg_struct, host_rocks, country_ro, gitology, alteration, min_morpho)

The model uses:
- XGBoost/RandomForest/GradientBoosting ensemble
- SMOTE for class balancing
- Feature selection via mutual information
=============================================================================
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Model files location
ML_MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(ML_MODEL_DIR, "prospectivity_model.pkl")
SCALER_PATH = os.path.join(ML_MODEL_DIR, "prospectivity_scaler.pkl")
FEATURE_INFO_PATH = os.path.join(ML_MODEL_DIR, "prospectivity_features.pkl")

# Class mapping
CLASS_MAP = {0: 'Low', 1: 'Medium', 2: 'High'}
REVERSE_CLASS_MAP = {'Low': 0, 'Medium': 1, 'High': 2}

# Feature definitions for the input form
MODS_FEATURES = {
    'elevation': {'type': 'number', 'placeholder': 'e.g., 850', 'label': 'Elevation (m)', 'required': False},
    'quad': {'type': 'text', 'placeholder': 'e.g., 21 39 B', 'label': 'Quad', 'required': False},
    'reg_struct': {'type': 'select', 'label': 'Regional Structure', 'required': False, 'options': [
        'Undefined', 'batholith; pluton', 'fold', 'shear zone', 'fault', 'isoclinal fold; shear zone', 'Other'
    ]},
    'host_rocks': {'type': 'text', 'placeholder': 'e.g., granite; quartz', 'label': 'Host Rocks', 'required': False},
    'country_ro': {'type': 'text', 'placeholder': 'e.g., granite; granodiorite', 'label': 'Country Rock', 'required': False},
    'gitology': {'type': 'select', 'label': 'Gitology', 'required': False, 'options': [
        'Unclassified', 'Hydrothermal', 'Igneous Rock', 'Volcanic sedimentary', 'Pegmatitic', 
        'Sedimentary rocks', 'Metamorphic', 'Other'
    ]},
    'alteration': {'type': 'select', 'label': 'Alteration', 'required': False, 'options': [
        'undefined', 'silicification', 'epidotization', 'gossan alteration', 'chloritization',
        'sericitization', 'carbonatization', 'Other'
    ]},
    'min_morpho': {'type': 'select', 'label': 'Mineral Morphology', 'required': False, 'options': [
        'Undetermined', 'Massive', 'veins', 'lenses', 'pods', 'DISSEMINATION', 'Stratiform', 
        'Massive Bed', 'Other'
    ]},
}

# Features auto-fetched from database when clicking on map
AUTO_FEATURES = [
    'litho_fmly', 'family_dv', 'family_sdv', 'main_litho', 'met_facies',
    'distance_to_nearest_line_m', 'lines_within_5000m',
    'distance_to_nearest_line_d', 'dikes_within_5000m'
]


class ProspectivityPredictor:
    """
    Multi-class mineral prospectivity predictor.
    Predicts: Low, Medium, High importance.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_info = None
        self.selected_features = None
        self.is_loaded = False
        
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained model, scaler, and feature info."""
        try:
            import joblib
            
            if not os.path.exists(MODEL_PATH):
                logger.warning(f"Model not found: {MODEL_PATH}")
                logger.info("Run 'python ml/train_prospectivity.py' to train the model")
                return
            
            logger.info("Loading prospectivity model...")
            self.model = joblib.load(MODEL_PATH)
            
            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
            
            if os.path.exists(FEATURE_INFO_PATH):
                self.feature_info = joblib.load(FEATURE_INFO_PATH)
                self.selected_features = self.feature_info.get('selected_features', [])
            
            self.is_loaded = True
            logger.info("✅ Prospectivity model loaded successfully")
            
        except ImportError as e:
            logger.warning(f"ML dependencies not installed: {e}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    
    def get_feature_definitions(self) -> Dict[str, Any]:
        """Get feature definitions for the input form."""
        return {
            'mods_features': MODS_FEATURES,
            'auto_features': AUTO_FEATURES,
            'class_labels': list(CLASS_MAP.values())
        }
    
    def preprocess_input(self, raw_input: Dict[str, Any]) -> pd.DataFrame:
        """
        Preprocess raw input into model-ready features.
        
        This replicates the preprocessing from the training notebook:
        1. One-hot encode single-valued categorical columns
        2. Multi-label binarize multi-valued columns (semicolon-separated)
        3. Fill missing values
        4. Scale numeric features
        """
        # Create DataFrame from input
        df = pd.DataFrame([raw_input])
        
        # Fill missing values
        df['elevation'] = pd.to_numeric(df.get('elevation', 0), errors='coerce').fillna(0)
        df['longitude'] = pd.to_numeric(df.get('longitude', 0), errors='coerce')
        df['latitude'] = pd.to_numeric(df.get('latitude', 0), errors='coerce')
        
        # Distance features
        df['distance_to_nearest_line_m'] = pd.to_numeric(
            df.get('distance_to_nearest_line_m', 5000), errors='coerce'
        ).fillna(5000)
        df['lines_within_5000m'] = pd.to_numeric(
            df.get('lines_within_5000m', 0), errors='coerce'
        ).fillna(0)
        df['distance_to_nearest_line_d'] = pd.to_numeric(
            df.get('distance_to_nearest_line_d', 10000), errors='coerce'
        ).fillna(10000)
        df['dikes_within_5000m'] = pd.to_numeric(
            df.get('dikes_within_5000m', 0), errors='coerce'
        ).fillna(0)
        
        # Fill text features with defaults
        text_defaults = {
            'quad': 'Unknown',
            'reg_struct': 'Undefined',
            'host_rocks': 'Unknown',
            'country_ro': 'Unknown',
            'gitology': 'Unclassified',
            'alteration': 'undefined',
            'min_morpho': 'Undetermined',
            'litho_fmly': 'Unknown',
            'family_dv': 'Unknown',
            'family_sdv': 'Unknown',
            'main_litho': 'Unknown',
            'met_facies': 'None',
        }
        
        for col, default in text_defaults.items():
            if col not in df.columns or pd.isna(df[col].iloc[0]) or df[col].iloc[0] == '':
                df[col] = default
            else:
                df[col] = df[col].fillna(default)
        
        return df
    
    def encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical features to match training encoding.
        Uses the feature_info saved during training.
        """
        if self.feature_info is None:
            raise RuntimeError("Feature info not loaded")
        
        # Get encoding info
        single_cols = self.feature_info.get('single_valued_cols', [])
        multi_cols = self.feature_info.get('multi_valued_cols', [])
        top_classes = self.feature_info.get('top_classes', {})
        
        encoded_df = df[['longitude', 'latitude', 'elevation',
                         'distance_to_nearest_line_m', 'lines_within_5000m',
                         'distance_to_nearest_line_d', 'dikes_within_5000m']].copy()
        
        # Encode single-valued columns
        for col in single_cols:
            if col in df.columns:
                val = str(df[col].iloc[0])
                col_top = top_classes.get(col, [])
                if val not in col_top:
                    val = 'Other'
                
                # Create one-hot columns
                for cls in col_top + ['Other']:
                    col_name = f"{col}_{cls}"
                    encoded_df[col_name] = 1 if val == cls else 0
        
        # Encode multi-valued columns
        for col in multi_cols:
            if col in df.columns:
                val = str(df[col].iloc[0])
                values = [v.strip() for v in val.split(';') if v.strip()]
                col_top = top_classes.get(col, [])
                
                # Map to top classes or 'Other'
                mapped = []
                for v in values:
                    if v in col_top:
                        mapped.append(v)
                    else:
                        mapped.append('Other')
                
                # Create multi-label columns
                for cls in col_top + ['Other']:
                    col_name = f"{col}_{cls}"
                    encoded_df[col_name] = 1 if cls in mapped else 0
        
        # Ensure all expected features exist
        for feat in self.selected_features:
            if feat not in encoded_df.columns:
                encoded_df[feat] = 0
        
        # Select only the features used by the model
        return encoded_df[self.selected_features]
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a prediction for a single location.
        
        Args:
            input_data: Dict with features (longitude, latitude, elevation, etc.)
            
        Returns:
            Dict with prediction, probabilities, and confidence
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Preprocess
            df = self.preprocess_input(input_data)
            
            # Encode features
            X = self.encode_features(df)
            
            # Scale numeric features if scaler exists
            if self.scaler is not None:
                numeric_cols = ['longitude', 'latitude', 'elevation',
                               'distance_to_nearest_line_m', 'lines_within_5000m',
                               'distance_to_nearest_line_d', 'dikes_within_5000m']
                numeric_cols = [c for c in numeric_cols if c in X.columns]
                if numeric_cols:
                    X[numeric_cols] = self.scaler.transform(X[numeric_cols])
            
            # Predict
            pred_class = self.model.predict(X)[0]
            pred_proba = self.model.predict_proba(X)[0]
            
            # Get class name
            class_name = CLASS_MAP.get(pred_class, 'Unknown')
            
            # Build probability dict
            probabilities = {
                CLASS_MAP[i]: round(float(p), 4)
                for i, p in enumerate(pred_proba)
            }
            
            # Confidence is the probability of the predicted class
            confidence = round(float(pred_proba[pred_class]), 4)
            
            return {
                'success': True,
                'prediction': class_name,
                'prediction_code': int(pred_class),
                'probabilities': probabilities,
                'confidence': confidence,
                'input_summary': {
                    'longitude': input_data.get('longitude'),
                    'latitude': input_data.get('latitude'),
                    'elevation': input_data.get('elevation'),
                }
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'is_loaded': self.is_loaded,
            'model_type': type(self.model).__name__ if self.model else None,
            'num_features': len(self.selected_features) if self.selected_features else 0,
            'classes': list(CLASS_MAP.values()),
            'feature_definitions': self.get_feature_definitions()
        }


# Singleton
_predictor: Optional[ProspectivityPredictor] = None


def get_prospectivity_predictor() -> ProspectivityPredictor:
    """Get or create the global prospectivity predictor."""
    global _predictor
    if _predictor is None:
        _predictor = ProspectivityPredictor()
    return _predictor
