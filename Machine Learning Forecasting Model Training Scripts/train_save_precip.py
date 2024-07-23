import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
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

# Need to add a binary rain column: 1 if it rained any amount, 0 if it did not
core_weather["rain"] = (core_weather["precip"] > 0).astype(int)

# Target variable is whether it will rain any amount the next day
core_weather["target"] = core_weather["rain"].shift(-1)
core_weather = core_weather.iloc[:-1, :]

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

# Trying to capture the nature of a year's dates - it wraps around (Dec 31 is next to Jan 1)
core_weather['sin_day_of_year'] = np.sin(2 * np.pi * core_weather['day_of_year'] / 365.25)
core_weather['cos_day_of_year'] = np.cos(2 * np.pi * core_weather['day_of_year'] / 365.25)

core_weather = core_weather.dropna()

# Define predictors (removing target, day_of_year, and the binary rain column)
predictors = core_weather.columns.difference(['target', 'day_of_year', 'rain'])

# Spliting data into training and testing sets
train = core_weather.loc[:'2020-12-31']
test = core_weather.loc['2021-01-01':]

rf = RandomForestClassifier(random_state=42)
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
joblib.dump(best_rf, "precip_model_saved.pkl")