import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
import joblib
from datetime import datetime
import numpy as np
from typing import List, Optional
from ..domain.models import PredictionResult

class ModelServer:
    """Serves predictions using the latest model"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = self._load_model(model_path) if model_path else self._create_default_model()
        self.model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def predict(self, features: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions with confidence intervals"""
        predictions = []
        for _, row in features.iterrows():
            # Make prediction with all trees to get confidence interval
            point_pred = self.model.predict(row.values.reshape(1, -1))[0]
            
            # We can get standard error from model's residuals
            residuals = np.std([
                tree.predict(row.values.reshape(1, -1))[0]
                for tree in self.model.estimators_
            ])
            
            ci_width = 1.96 * residuals  # 95% confidence interval
            predictions.append(PredictionResult(
                timestamp=row['timestamp'],
                endpoint=row['endpoint'],
                predicted_latency=point_pred,
                confidence_interval=(point_pred - ci_width, point_pred + ci_width),
                features_used={col: row[col] for col in features.columns},
                model_version=self.model_version
            ))
            
        return predictions
    
    def _create_default_model(self) -> GradientBoostingRegressor:
        """Create a default model with reasonable parameters"""
        return GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
    
    def _load_model(self, path: str) -> GradientBoostingRegressor:
        """Load a trained model from disk"""
        return joblib.load(path)
    
    def save_model(self, path: str):
        """Save the current model to disk"""
        joblib.dump(self.model, path)
