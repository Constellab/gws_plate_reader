import numpy as np
import pandas as pd
import streamlit as st
from scipy.optimize import curve_fit
from sklearn.model_selection import KFold

from scipy.interpolate import interp1d, UnivariateSpline, LSQUnivariateSpline
from sklearn.metrics import r2_score
import plotly.graph_objs as go
import plotly.express as px

from gws_plate_reader.biolector_xt_analysis.biolector_state import BiolectorState

class LogisticGrowthFitter:
    def __init__(self, data: pd.DataFrame, n_splits: int = 3):
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

        dict_well_data_description = BiolectorState.get_well_data_description()
        for well in self.data.columns[1:]:
            # Extract plate name if well contains an underscore
            plate_name = None
            display_well = well
            if '_' in well:
                display_well, plate_name = well.split('_', 1)
            well_data = self.data[well].values
            # Get the label for the well from the dictionary
            if plate_name:
                label = dict_well_data_description.get(display_well, {}).get(plate_name, {}).get('label', None)
            else:
                label = dict_well_data_description.get(display_well, {}).get('label', None)

            r2_scores = []
            best_fit_params = None
            best_fit_r2 = -np.inf
            #weights = np.ones_like(well_data)
            #weights[0] = 10
            #spline_interp = LSQUnivariateSpline(time, well_data, t=time[1:-1], w=weights)
            spline_interp =UnivariateSpline(time, well_data,s=0.045)
            #spline_derivative = spline_interp.derivative()
            #derivative_values_max = np.max(spline_derivative(time))

            #time_fine = np.linspace(time.min(), time.max(), 500)
            well_data=spline_interp(time)
            initial_max_abs=np.max(well_data)
            initial_growth_rate= np.max(np.diff(well_data))
            initial_absorbance=well_data[0]
            initial_guesses=[initial_max_abs,initial_growth_rate,0,initial_absorbance]
            upperbound_initial_absorbance= initial_absorbance*1.1
            lowerbound_initial_absorbance= initial_absorbance*0.90

            for train_index, test_index in kf.split(time):
                time_train, time_test = time[train_index], time[test_index]
                well_data_train, well_data_test = well_data[train_index], well_data[test_index]

                bounds = ([0, 0, 0,lowerbound_initial_absorbance], [np.inf,np.inf , np.inf,upperbound_initial_absorbance])
                params, _ = curve_fit(self.logistic_growth, time_train, well_data_train, p0=initial_guesses, maxfev= 5000,bounds=bounds)
                max_absorbance, growth_rate, lag_time,initial_absorbance = params

                well_data_pred = self.logistic_growth(time_test, max_absorbance, growth_rate, lag_time, initial_absorbance)
                r2 = r2_score(well_data_test, well_data_pred)
                r2_scores.append(r2)

                if np.mean(r2_scores) > best_fit_r2:
                    best_fit_params = params
                    best_fit_r2 = np.mean(r2_scores)

            fitted_max_absorbance, fitted_growth_rate, fitted_lag_time,fitted_initial_absorbance = best_fit_params
            params_dict = {
            'Well': [display_well],
            'Label': [label],
            'Max_Absorbance': [fitted_max_absorbance],
            'Growth_Rate': [fitted_growth_rate],
            'Lag_Time': [fitted_lag_time],
            'Initial_Absorbance': [fitted_initial_absorbance],
            'Avg_R2': [best_fit_r2]
            }

            # Add plate name column if it exists
            if plate_name:
                params_dict['Plate_Name'] = [plate_name]
                # Create DataFrame
                df = pd.DataFrame(params_dict)
                # Ensure the correct column order
                desired_order = ['Well', 'Plate_Name', 'Label', 'Max_Absorbance', 'Growth_Rate', 'Lag_Time', 'Initial_Absorbance', 'Avg_R2']
            else:
                # Create DataFrame
                df = pd.DataFrame(params_dict)
                # Ensure the correct column order
                desired_order = ['Well', 'Label', 'Max_Absorbance', 'Growth_Rate', 'Lag_Time', 'Initial_Absorbance', 'Avg_R2']

            # Reorder columns
            df = df.reindex(columns=desired_order)

            df_params_list.append(df)

            time_fitted = np.linspace(min(time), max(time), 100)
            fitted_curve = self.logistic_growth(time_fitted, *best_fit_params)
            curves_dict = {
            'Time': time_fitted,
            'Fitted_Curve': fitted_curve,
            'Well': display_well
            }

            # Add plate name to fitted curves if it exists
            if plate_name:
                curves_dict['Plate_Name'] = plate_name

            df_fitted_curves_list.append(pd.DataFrame(curves_dict))

        self.df_params = pd.concat(df_params_list, ignore_index=True).set_index("Well")
        self.df_fitted_curves = pd.concat(df_fitted_curves_list, ignore_index=True).set_index("Well")

    def plot_fitted_curves_with_r2(self):
        """Plot fitted logistic growth curves with R² values and raw data points."""
        fig = go.Figure()

        # Generate a color palette
        colors = px.colors.qualitative.Plotly
        wells = self.data.columns[1:]

        # Add traces for raw data points and fitted curves
        for i, well in enumerate(wells):
            # Extract plate name if well contains an underscore
            plate_name = None
            display_well = well
            if '_' in well:
                display_well, plate_name = well.split('_', 1)

            color = colors[i % len(colors)]  # Cycle through the color palette

            # Get label from parameters dataframe
            if plate_name and 'Plate_Name' in self.df_params.columns:
                reduced_plate_name = self.df_params[self.df_params['Plate_Name'] == plate_name]
                label = reduced_plate_name.loc[display_well, 'Label'] if 'Label' in reduced_plate_name.columns else None
            else:
                label = self.df_params.loc[display_well, 'Label'] if 'Label' in self.df_params.columns else None


            # Create curve name with well, label and plate
            display_name = f"{display_well}"
            if label:
                display_name += f"-{label}"
            if plate_name:
                display_name += f"-{plate_name}"

            # Raw data points for the current well
            fig.add_trace(go.Scatter(
                x=self.data.iloc[:, 0],
                y=self.data[well],
                mode='markers',
                name=f'{display_name} - Raw Data',
                marker=dict(color=color, symbol='circle', size=6),
                showlegend=True
            ))

            # Fitted curve for the current well
            subset = self.df_fitted_curves[self.df_fitted_curves.index == display_well]
            r2 = self.df_params[self.df_params.index == display_well]['Avg_R2'].values[0]

            fig.add_trace(go.Scatter(
                x=subset['Time'],
                y=subset['Fitted_Curve'],
                mode='lines',
                name=f'{display_name} (R²={r2:.2f}) - Fitted',
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

    def plot_growth_rate_histogram(self):
        """
        Plot a histogram of growth rates from the fitted logistic growth parameters.

        Returns:
            Plotly figure object showing the distribution of growth rates across wells.
        """
        # Extract growth rates from parameters dataframe
        growth_rates = self.df_params['Growth_Rate'].values

        # Create labels for each well that include plate and label info
        labels = []
        for idx, row in self.df_params.iterrows():
            label_text = f"{idx}"

            if 'Label' in row and not pd.isna(row['Label']):
                label_text += f"_{row['Label']}"
            if 'Plate_Name' in row and not pd.isna(row['Plate_Name']):
                label_text += f"_{row['Plate_Name']}"

            labels.append(label_text)

        # Create a histogram
        fig = go.Figure()

        # Compute optimal bin size
        bin_size = (growth_rates.max() - growth_rates.min()) / 10

        # Create histogram trace with improved binning
        fig.add_trace(go.Histogram(
            x=growth_rates,
            name='Growth Rate Distribution',
            marker_color='rgba(50, 168, 82, 0.7)',
            hoverinfo='x+y',
            xbins=dict(
                start=growth_rates.min(),
                end=growth_rates.max(),
                size=bin_size
            )
        ))


        # Add scatter points on a secondary y-axis to show individual wells
        fig.add_trace(go.Scatter(
            x=growth_rates,
            y=[0.05] * len(growth_rates),  # Small y value to position at bottom
            mode='markers',
            marker=dict(
                size=8,
                color='rgba(0, 0, 0, 0.7)',
                symbol='circle'
            ),
            text=labels,
            hovertemplate='<b>%{text}</b><br>Growth Rate: %{x:.4f}<extra></extra>',
            name='Individual Wells'
        ))

        # Calculate statistics
        mean_growth = np.mean(growth_rates)
        std_growth = np.std(growth_rates)

        # Customize layout
        fig.update_layout(
            title='Distribution of Growth Rates Across Wells',
            xaxis_title='Growth Rate',
            yaxis_title='Count',
            bargap=0.1,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            annotations=[
                dict(
                    x=0.95,
                    y=0.95,
                    xref="paper",
                    yref="paper",
                    text=f"Mean ± Std: {mean_growth:.4f} ± {std_growth:.4f}",
                    showarrow=False,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="black",
                    borderwidth=1,
                    borderpad=4,
                    font=dict(size=12)
                )
            ]
        )

        return fig

