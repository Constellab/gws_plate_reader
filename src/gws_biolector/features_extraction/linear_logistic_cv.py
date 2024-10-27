import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
import plotly.graph_objs as go
import plotly.express as px

class LogisticGrowthFitter:
    def __init__(self, data: pd.DataFrame, n_splits: int = 5):
        """
        Initialize the LogisticGrowthFitter class.

        Parameters:
        data (DataFrame): Input DataFrame with the first column as time and subsequent columns as well data.
        n_splits (int): Number of splits for cross-validation.
        """
        self.data = data
        self.n_splits = n_splits
        self.df_params = pd.DataFrame()
        self.df_fitted_curves = pd.DataFrame()

    def logistic_growth(self, time, max_absorbance, growth_rate, lag_time,initial_absorbance):
        """Logistic growth function."""
        return initial_absorbance + (max_absorbance - initial_absorbance) / (1 + np.exp(-growth_rate * (time - lag_time)))

    def fit_logistic_growth_with_cv(self):
        """Fit logistic growth model using cross-validation for each well."""
        df_params_list = []  # List to collect parameter dataframes
        df_fitted_curves_list = []  # List to collect fitted curve dataframes

        kf = KFold(n_splits=self.n_splits, shuffle=True, random_state=42)
        time = self.data.iloc[:, 0].values

        for well in self.data.columns[1:]:
            well_data = self.data[well].values
            initial_max_abs=np.max(well_data)
            initial_growth_rate= np.max(np.diff(well_data))
            initial_absorbance=well_data[0]
            r2_scores = []
            best_fit_params = None
            best_fit_r2 = -np.inf

            initial_guesses=[initial_max_abs,initial_growth_rate,0,initial_absorbance]


            for train_index, test_index in kf.split(time):
                time_train, time_test = time[train_index], time[test_index]
                well_data_train, well_data_test = well_data[train_index], well_data[test_index]

                initial_guesses = [2, 0.8, 1]
                params, _ = curve_fit(self.logistic_growth, time_train, well_data_train, p0=initial_guesses, maxfev= 5000,bounds=(0,np.inf))
                max_absorbance, growth_rate, lag_time,initial_absorbance = params

                well_data_pred = self.logistic_growth(time_test, max_absorbance, growth_rate, lag_time, initial_absorbance)
                r2 = r2_score(well_data_test, well_data_pred)
                r2_scores.append(r2)

                if np.mean(r2_scores) > best_fit_r2:
                    best_fit_params = params
                    best_fit_r2 = np.mean(r2_scores)

            fitted_max_absorbance, fitted_growth_rate, fitted_lag_time,fitted_initial_absorbance = best_fit_params
            df_params_list.append(pd.DataFrame({
                'Well': [well],
                'Max_Absorbance': [fitted_max_absorbance],
                'Growth_Rate': [fitted_growth_rate],
                'Lag_Time': [fitted_lag_time],
                'Initial_Absorbance': [fitted_initial_absorbance],
                'Avg_R2': [best_fit_r2]
            }))

            time_fitted = np.linspace(min(time), max(time), 100)
            fitted_curve = self.logistic_growth(time_fitted, *best_fit_params)
            df_fitted_curves_list.append(pd.DataFrame({
                'Time': time_fitted,
                'Fitted_Curve': fitted_curve,
                'Well': well
            }))

        self.df_params = pd.concat(df_params_list, ignore_index=True)
        self.df_fitted_curves = pd.concat(df_fitted_curves_list, ignore_index=True)

    def plot_fitted_curves_with_r2(self):
        """Plot fitted logistic growth curves with R² values and raw data points."""
        fig = go.Figure()

        # Generate a color palette
        colors = px.colors.qualitative.Plotly
        wells = self.data.columns[1:]

        # Add traces for raw data points and fitted curves
        for i, well in enumerate(wells):
            color = colors[i % len(colors)]  # Cycle through the color palette

            # Raw data points for the current well
            fig.add_trace(go.Scatter(
                x=self.data.iloc[:, 0],
                y=self.data[well],
                mode='markers',
                name=f'Well {well} - Raw Data',
                marker=dict(color=color, symbol='circle', size=6),
                showlegend=True
            ))

            # Fitted curve for the current well
            subset = self.df_fitted_curves[self.df_fitted_curves['Well'] == well]
            r2 = self.df_params[self.df_params['Well'] == well]['Avg_R2'].values[0]

            fig.add_trace(go.Scatter(
                x=subset['Time'],
                y=subset['Fitted_Curve'],
                mode='lines',
                name=f'Well {well} (R²={r2:.2f}) - Fitted',
                line=dict(color=color, width=2)
            ))

        # Customize layout
        fig.update_layout(
            title='Logistic Growth Fitting with Raw Data and R² for Each Well',
            xaxis_title='Time',
            yaxis_title='Absorbance',
            legend_title='Wells and Fits',
            template='plotly_white'  # You can change the template here
        )
        return fig

# logistic_fitter = LogisticGrowthFitter(df)
# logistic_fitter.fit_logistic_growth_with_cv()
# logistic_fitter.plot_fitted_curves_with_r2()