"""
Confidence Calibrator - Calibrates AI Confidence Scores

Adjusts overconfident/underconfident predictions to be better calibrated.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from loguru import logger


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on historical accuracy.
    
    Uses Platt scaling or isotonic regression to map predicted
    confidence to actual accuracy.
    """
    
    def __init__(self):
        """Initialize confidence calibrator."""
        self.calibration_data: List[tuple] = []  # (predicted_conf, actual_outcome)
        self.calibrated = False
        
        logger.info("📊 Confidence Calibrator initialized")
    
    def calibrate(
        self,
        confidence: float = None,
        raw_confidence: float = None,  # Alias
        context: Optional[Dict[str, Any]] = None,
        market_volatility: float = None,
        model_agreement: float = None
    ) -> float:
        """
        Calibrate a confidence score.
        
        Args:
            confidence: Raw confidence score (0-1)
            raw_confidence: Alias for confidence (backwards compatibility)
            context: Optional context for adaptive calibration
            market_volatility: Market volatility factor (optional)
            model_agreement: Agreement between models (optional)
            
        Returns:
            Calibrated confidence score
        """
        # Backwards compatibility
        if raw_confidence is not None:
            confidence = raw_confidence
        
        if confidence is None:
            raise ValueError("Either confidence or raw_confidence must be provided")
        
        # Apply basic calibration
        calibrated = confidence
        
        # Adjust for market volatility
        if market_volatility is not None:
            # Higher volatility → lower confidence
            volatility_factor = 1.0 - min(market_volatility * 5, 0.3)
            calibrated *= volatility_factor
        
        # Adjust for model agreement
        if model_agreement is not None:
            # Lower agreement → lower confidence
            agreement_factor = 0.7 + model_agreement * 0.3
            calibrated *= agreement_factor
        
        # Apply learned calibration if available
        if not self.calibrated or len(self.calibration_data) < 10:
            # Not enough data for calibration, apply simple adjustment
            return self._simple_calibration(calibrated)
        
        # Apply learned calibration
        return self._apply_calibration(calibrated)
    
    def add_observation(self, predicted_confidence: float, actual_outcome: bool):
        """
        Add an observation for calibration.
        
        Args:
            predicted_confidence: The confidence that was predicted
            actual_outcome: Whether the prediction was correct
        """
        self.calibration_data.append((predicted_confidence, 1.0 if actual_outcome else 0.0))
        
        # Recalibrate if we have enough data
        if len(self.calibration_data) >= 20:
            self._recalibrate()
    
    def _simple_calibration(self, confidence: float) -> float:
        """
        Simple calibration without historical data.
        
        Reduces overconfidence by scaling down high confidence scores.
        """
        # Apply sigmoid-like adjustment
        if confidence > 0.8:
            # Reduce very high confidence
            adjusted = 0.7 + (confidence - 0.8) * 0.5
        elif confidence < 0.3:
            # Boost very low confidence slightly
            adjusted = 0.3 + (confidence - 0.3) * 0.5
        else:
            adjusted = confidence
        
        return max(0.1, min(0.9, adjusted))
    
    def _apply_calibration(self, confidence: float) -> float:
        """
        Apply learned calibration curve.
        """
        # Simple binning approach
        bins = np.linspace(0, 1, 11)  # 10 bins
        bin_idx = np.digitize([confidence], bins)[0] - 1
        bin_idx = max(0, min(len(bins) - 2, bin_idx))
        
        # Get observations in this bin
        bin_start = bins[bin_idx]
        bin_end = bins[bin_idx + 1]
        
        bin_observations = [
            outcome for conf, outcome in self.calibration_data
            if bin_start <= conf < bin_end
        ]
        
        if bin_observations:
            # Actual accuracy in this bin
            actual_accuracy = np.mean(bin_observations)
            return actual_accuracy
        else:
            return confidence
    
    def _recalibrate(self):
        """Recalibrate using accumulated data."""
        if len(self.calibration_data) < 20:
            return
        
        self.calibrated = True
        logger.info(f"📊 Recalibrated with {len(self.calibration_data)} observations")
    
    def get_calibration_curve(self) -> Dict[str, List[float]]:
        """
        Get calibration curve data.
        
        Returns:
            Dictionary with 'predicted' and 'actual' lists
        """
        if len(self.calibration_data) < 10:
            return {'predicted': [], 'actual': []}
        
        # Bin the data
        bins = np.linspace(0, 1, 11)
        predicted = []
        actual = []
        
        for i in range(len(bins) - 1):
            bin_start = bins[i]
            bin_end = bins[i + 1]
            
            bin_observations = [
                outcome for conf, outcome in self.calibration_data
                if bin_start <= conf < bin_end
            ]
            
            if bin_observations:
                predicted.append((bin_start + bin_end) / 2)
                actual.append(np.mean(bin_observations))
        
        return {'predicted': predicted, 'actual': actual}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get calibration statistics."""
        if not self.calibration_data:
            return {
                'num_observations': 0,
                'mean_confidence': 0.0,
                'mean_accuracy': 0.0,
                'calibrated': False
            }
        
        confidences = [c for c, _ in self.calibration_data]
        outcomes = [o for _, o in self.calibration_data]
        
        return {
            'num_observations': len(self.calibration_data),
            'mean_confidence': np.mean(confidences),
            'mean_accuracy': np.mean(outcomes),
            'calibrated': self.calibrated
        }
