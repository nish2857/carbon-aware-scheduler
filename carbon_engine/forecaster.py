"""
Machine Learning Forecaster for Dynamic Carbon-Aware Cloud Workload Scheduler.
Trains ensemble ML models to predict regional hourly grid carbon intensity (gCO2eq/kWh).
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from .grid_data_provider import REGION_METADATA

class CarbonForecaster:
    """Ensemble ML Model for multi-region grid carbon forecasting."""

    def __init__(self, model_type: str = 'rf', seed: int = 42):
        self.regions = list(REGION_METADATA.keys())
        self.model_type = model_type
        self.seed = seed
        self.models: Dict[str, Any] = {}
        self._init_models()

    def _init_models(self):
        for r in self.regions:
            if self.model_type == 'gbr':
                self.models[r] = GradientBoostingRegressor(n_estimators=120, learning_rate=0.08, random_state=self.seed)
            else:
                self.models[r] = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=self.seed)

    def extract_features(self, df: pd.DataFrame, region: str) -> pd.DataFrame:
        """Extracts temporal, cyclical, and lag features for ML training and prediction."""
        features = pd.DataFrame(index=df.index)
        features['hour'] = df['hour']
        features['day_of_week'] = df['day_of_week']
        features['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24.0)
        features['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24.0)
        
        carbon_col = f'{region}_carbon'
        if carbon_col in df.columns:
            features['lag_1h'] = df[carbon_col].shift(1).bfill()
            features['lag_24h'] = df[carbon_col].shift(24).bfill()
            features['rolling_6h'] = df[carbon_col].rolling(6, min_periods=1).mean()
        else:
            features['lag_1h'] = REGION_METADATA[region]['base_carbon']
            features['lag_24h'] = REGION_METADATA[region]['base_carbon']
            features['rolling_6h'] = REGION_METADATA[region]['base_carbon']

        return features

    def train(self, df_train: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Trains ML models per region and returns feature importance and training metrics."""
        training_metrics = {}
        for region in self.regions:
            X = self.extract_features(df_train, region)
            y = df_train[f'{region}_carbon']
            
            self.models[region].fit(X, y)
            
            preds = self.models[region].predict(X)
            rmse = np.sqrt(mean_squared_error(y, preds))
            mae = mean_absolute_error(y, preds)
            r2 = r2_score(y, preds)

            training_metrics[region] = {
                'rmse': round(float(rmse), 2),
                'mae': round(float(mae), 2),
                'r2': round(float(r2), 4)
            }

        return training_metrics

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        """Predicts hourly carbon intensity for all regions on test dataset."""
        predictions = {}
        for region in self.regions:
            X = self.extract_features(df_test, region)
            preds = self.models[region].predict(X)
            predictions[f'{region}_predicted_carbon'] = preds
        
        result_df = pd.DataFrame(predictions, index=df_test.index)
        return result_df

    def evaluate(self, df_test: pd.DataFrame, predictions_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Evaluates prediction error against ground truth carbon values."""
        eval_results = {}
        for region in self.regions:
            actual = df_test[f'{region}_carbon']
            pred = predictions_df[f'{region}_predicted_carbon']

            rmse = np.sqrt(mean_squared_error(actual, pred))
            mae = mean_absolute_error(actual, pred)
            r2 = r2_score(actual, pred)

            eval_results[region] = {
                'rmse': round(float(rmse), 2),
                'mae': round(float(mae), 2),
                'r2': round(float(r2), 4)
            }
        return eval_results


if __name__ == '__main__':
    from grid_data_provider import GridDataProvider
    provider = GridDataProvider()
    df = provider.generate_timeline_data(days=14)

    split = int(len(df) * 0.7)
    train_df = df.iloc[:split]
    test_df = df.iloc[split:].reset_index(drop=True)

    forecaster = CarbonForecaster(model_type='rf')
    train_metrics = forecaster.train(train_df)
    preds = forecaster.predict(test_df)
    eval_metrics = forecaster.evaluate(test_df, preds)

    print("=== TRAIN METRICS ===")
    print(train_metrics)
    print("\n=== TEST EVALUATION METRICS ===")
    print(eval_metrics)
