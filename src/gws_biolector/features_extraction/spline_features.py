import BiolectorXTParser
import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline
from sklearn.model_selection import KFold

import numpy as np
from scipy.interpolate import UnivariateSpline
from sklearn.model_selection import KFold

class GrowthRateSplineInference:
    def __init__(self, time, absorbance):
        self.time = np.array(time)
        self.absorbance = np.array(absorbance)

    def growth_rate_inference_with_spline(self, s_values=np.logspace(-2, 2, 500), n_splits=5):
        kf = KFold(n_splits=n_splits)
        best_s = None
        best_cv_score = np.inf  # Minimize the cross-validation error
        best_spline = None

        # Cross-validation loop over smoothing parameters
        for s in s_values:
            cv_scores = []

            # Perform KFold cross-validation
            for train_idx, val_idx in kf.split(self.time):
                time_train, time_val = self.time[train_idx], self.time[val_idx]
                absorbance_train, absorbance_val = self.absorbance[train_idx], self.absorbance[val_idx]

                # Fit a spline on the training data
                spline = UnivariateSpline(time_train, absorbance_train, s=s)

                # Predict on validation data and compute error
                absorbance_pred = spline(time_val)
                cv_scores.append(np.mean((absorbance_val - absorbance_pred) ** 2))  # Mean Squared Error (MSE)

            # Calculate average validation score
            avg_cv_score = np.mean(cv_scores)

            # Update best smoothing parameter if a lower validation error is found
            if avg_cv_score < best_cv_score:
                best_cv_score = avg_cv_score
                best_s = s
                best_spline = UnivariateSpline(self.time, self.absorbance, s=best_s)  # Refit on full data with best s

        # Calculate the derivative of the best spline (growth rate)
        derivative_spline = best_spline.derivative()

        # Infer the growth rate as the maximum of the derivative
        growth_rate_values = derivative_spline(self.time)
        max_growth_rate = np.max(growth_rate_values)
        max_growth_time = self.time[np.argmax(growth_rate_values)]

        return best_s, max_growth_rate, max_growth_time, best_spline, derivative_spline
