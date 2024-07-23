import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
import joblib

# Data preprocessing
weather = pd.read_csv("weather_data.csv", index_col="DATE") # 62 years of historical daily data from local airport
core_weather = weather[["PRCP", "TMAX", "TMIN", "AWND", "WDF2"]].copy()
core_weather.columns = ["precip", "temp_max", "temp_min", "wind_speed", "wind_direction"]

# Handling of missing values
core_weather["precip"] = core_weather["precip"].fillna(0)
core_weather["temp_min"] = core_weather["temp_min"].fillna(method="ffill")
core_weather["temp_max"] = core_weather["temp_max"].fillna(method="ffill")
core_weather["wind_speed"] = core_weather["wind_speed"].fillna(method="ffill").fillna(method="bfill")
core_weather["wind_speed"].fillna(core_weather["wind_speed"].mean(), inplace=True)
core_weather["wind_direction"] = core_weather["wind_direction"].fillna(method="ffill").fillna(method="bfill")
core_weather["wind_direction"].fillna(core_weather["wind_direction"].mean(), inplace=True)

core_weather.index = pd.to_datetime(core_weather.index)

# Target variable: next day's minimum temperature
core_weather["target"] = core_weather["temp_min"].shift(-1)
core_weather = core_weather.iloc[:-1, :]  # Drop the last row with NaN target

# Rolling and lagged features
for window in [3, 7, 30]:
    core_weather[f'temp_min_roll_avg_{window}'] = core_weather['temp_min'].rolling(window).mean()
    core_weather[f'temp_max_roll_avg_{window}'] = core_weather['temp_max'].rolling(window).mean()
    core_weather[f'precip_roll_sum_{window}'] = core_weather['precip'].rolling(window).sum()
    core_weather[f'wind_speed_roll_avg_{window}'] = core_weather['wind_speed'].rolling(window).mean()

for lag in [1, 2, 3, 7, 14, 30]:
    core_weather[f'temp_min_lag_{lag}'] = core_weather['temp_min'].shift(lag)
    core_weather[f'temp_max_lag_{lag}'] = core_weather['temp_max'].shift(lag)
    core_weather[f'precip_lag_{lag}'] = core_weather['precip'].shift(lag)
    core_weather[f'wind_speed_lag_{lag}'] = core_weather['wind_speed'].shift(lag)

# Temporal features
core_weather['day_of_year'] = core_weather.index.dayofyear
core_weather['month'] = core_weather.index.month
core_weather['week_of_year'] = core_weather.index.isocalendar().week

core_weather['sin_day_of_year'] = np.sin(2 * np.pi * core_weather['day_of_year'] / 365.25)
core_weather['cos_day_of_year'] = np.cos(2 * np.pi * core_weather['day_of_year'] / 365.25)

core_weather = core_weather.dropna()

# Define predictors (removing target and day_of_year)
predictors = core_weather.columns.difference(['target', 'day_of_year'])

# Spliting data into training and testing sets
train = core_weather.loc[:'2020-12-31']
test = core_weather.loc['2021-01-01':]

rf = RandomForestRegressor(random_state=42)
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2],
    'bootstrap': [True]
}

# Initialize RandomizedsearchCV
random_search = RandomizedSearchCV(estimator=rf, param_distributions=param_grid,
                                   n_iter=10, cv=3, verbose=2, random_state=42, n_jobs=-1)

random_search.fit(train[predictors], train['target'])

best_rf = random_search.best_estimator_

# Save model to .pkl file for later application to weather station data
joblib.dump(best_rf, "min_temp_model_saved.pkl")