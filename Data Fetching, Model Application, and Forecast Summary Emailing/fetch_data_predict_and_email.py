import requests
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

client_id = "myID"
client_secret = "mySecret"

thing_id = "thingID"

def get_access_token(client_id, client_secret):
    token_url = "https://api2.arduino.cc/iot/v1/clients/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api2.arduino.cc/iot"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to obtain access token. Status code: {response.status_code}")
        return None

def fetch_sensor_data(access_token, thing_id):
    url = f"https://api2.arduino.cc/iot/v2/things/{thing_id}/properties"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

def save_data_to_csv(sensor_data, file="historical_data.csv"):
    property_names_to_include = ["Rain", "Max_temp_today", "Min_temp_today", "Max_wind_speed_today", "Prevailing_wind_direction"]
    property_values_in_order = {prop['name']: prop['last_value'] for prop in sensor_data if prop['name'] in property_names_to_include}

    wind_direction_degrees = {  # Need to convert readable wind direction abbreviation into a degree value for model to use
            "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
            "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
            "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
            "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5
        }

    with open(file, mode='a', newline='') as file:
        writer = csv.writer(file)

        row = [datetime.now().strftime("%Y-%m-%d")]
        for name in property_names_to_include:
            if name == "Prevailing_wind_direction":
                direction = property_values_in_order.get(name)
                degree = wind_direction_degrees.get(direction)
                row.append(degree)
            else:
                row.append(property_values_in_order.get(name))

        writer.writerow(row)

def preproccess_data_file(file="historical_data.csv"):
    df = pd.read_csv(file, index_col="timestamp")
    df.index = pd.to_datetime(df.index)
    df.columns = ["precip", "temp_max", "temp_min", "wind_speed", "wind_direction"]

    for window in [3, 7, 30]:
        df[f'temp_min_roll_avg_{window}'] = df['temp_min'].rolling(window).mean()
        df[f'temp_max_roll_avg_{window}'] = df['temp_max'].rolling(window).mean()
        df[f'precip_roll_sum_{window}'] = df['precip'].rolling(window).sum()
        df[f'wind_speed_roll_avg_{window}'] = df['wind_speed'].rolling(window).mean()

    for lag in [1, 2, 3, 7, 14, 30]:
        df[f'temp_min_lag_{lag}'] = df['temp_min'].shift(lag)
        df[f'temp_max_lag_{lag}'] = df['temp_max'].shift(lag)
        df[f'precip_lag_{lag}'] = df['precip'].shift(lag)
        df[f'wind_speed_lag_{lag}'] = df['wind_speed'].shift(lag)

    df['day_of_year'] = df.index.dayofyear
    df['month'] = df.index.month
    df['week_of_year'] = df.index.isocalendar().week

    df['sin_day_of_year'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['cos_day_of_year'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)

    df = df.dropna()

    latest_day_data = df.iloc[-1:].copy()

    return latest_day_data

def make_prediction(model, data):
    historical_data = preproccess_data_file(data)

    model = joblib.load(model)

    predictors = historical_data.columns.difference(['day_of_year'])

    prediction = model.predict(historical_data[predictors])

    return prediction

def email_results(high_prediction, low_prediction, precip_prediction):
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_tomorrow = tomorrow.strftime("%m-%d-%Y")

    sender_email = "mySenderEmail"
    reciever_emails = ["listHere"] # List of daily email recievers
    subject = f"Weather Prediction for {date_tomorrow}"
    body = f"Forecast for {date_tomorrow} in New Windsor, MD:\n\nHigh Temperature: {high_prediction:.1f} (F)\nLow Temperature: {low_prediction:.1f} (F)\nRain today?: {precip_prediction}"
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = ", ".join(reciever_emails)
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "mySenderEmail"
    smtp_password = "senderEmailPassword"

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)

    server.sendmail(sender_email, reciever_emails, message.as_string())

    server.quit()

def main():
    access_token = get_access_token(client_id, client_secret)
    
    if access_token:
        sensor_data = fetch_sensor_data(access_token, thing_id)
        if sensor_data:
            save_data_to_csv(sensor_data, "historical_data.csv")

            temp_max_prediction = make_prediction("max_temp_model_saved.pkl", "historical_data.csv")
            temp_min_prediction = make_prediction("min_temp_model_saved.pkl", "historical_data.csv")
            precip_prediction = make_prediction("precip_model_saved.pkl", "historical_data.csv")

            print(f"Max temp next day: {temp_max_prediction}")
            print(f"Min temp next day: {temp_min_prediction}")
            print(f"Rain next day?: {precip_prediction}")

            rain_status = "Error"
            if precip_prediction[0] == 1:
                rain_status = "Yes"
            elif precip_prediction[0] == 0:
                rain_status = "No"
            else:
                rain_status = "Error"

            email_results(temp_max_prediction[0], temp_min_prediction[0], rain_status)
        
        else:
            print("No sensor data obtained.")
    else:
        print("Failed to retrieve sensor data.")

main()
