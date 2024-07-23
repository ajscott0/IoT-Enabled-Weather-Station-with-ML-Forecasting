# IoT-Enabled-Weather-Station-with-ML-Forecasting

This project is comprised of two separate but cooperating parts: the weather station itself, as well as its accompanying software, and the machine learning algorithms that allow for short-term forecasting. The original intent of the project was to make rudimentary weather predictions (the next day's high and low temperature as well as some sort of precipitation prediction) based on data collected from my own constructed weather station - so without the use of radar and upper atmosphere data that is standard in modern forecasting methods. Despite these limitations, the forecasting capabilities of this system are reasonably accurate with the temperature predictions consistently within 2 to 3 degrees Fahrenheit of the actual next day temperatures (interestingly, the prediction for the next day's low temperature is consistently more accurate than the high prediction). Resulting from this project along with the daily next-day forecast, which is automatically emailed to set recipients each morning, is the data visualiation dashboard provided by the Arduino Cloud service that allows in-depth weather monitoring. An image example of this dashboard is included in this repository.

## Obtaining Data

The components of the weather station are: 
  1. A sealed plastic box that houses the Arduino Nano 33 Iot, all of the wiring necessary for proper data collection by the Arduino program, and two of the seven sensors -         the BH1750 light sensor and the GUVA-S12SD UV sensor.
  2. A wind-rain assembly that was purchased off the shelf and is intended to be used as a replacement part for a consumer weather station. This assembly includes an                 anemometer, a wind vain, and a tipping bucket type rain guage.
  3. A soil temperature probe which is connected to the Arduino Nano through a cable gland in the plastic box.
  4. A Stevenson screen that protects the BME280 from precipitation and direct sunlight, allowing it to accurately measures temperature, pressure, and humidity.

An important consideration in the Arduino program being run on the weather station is the use of interrupt service routines for the collection of wind speed and precipitation data. The anemometer sends a signal two times in a full rotation and it is from this accumulated count per duration of time that allows a wind speed to be calculated (using an equivalence reported on the data sheet). The rain guage works similarly, sending a signal each time the bucket tips from the weight of collected rain. The attachment of interrupts to the input pins of these devices allows their signals to be recieved and their associated counts incremented, regardless of what the program happens to be doing at that moment. All other seemingly peculiar things in the Arduino program are addressed by comments throughout the code itself.

## Training the Machine Learning Models

The next-day predictions are provided by three separate machine learning models - high temp, low temp, and yes/no for measurable precipitation. The basic structure for these weather forecasting models was provided by _Dataquest_'s video on the subject. The training and testing data for the models was ordered from NOAA's National Center for Enviromental Information. This was 62 years of daily data recorded at Baltimore/Washington International Thurgood Marshall Airport.

Feature engineering was aimed at best capturing the known patterns of weather. A notable limitation of these models is that they take data only from one location. Ideally, predictions would be made based also on weather data from another station further west. Furthermore, weight could be placed on data from different directions in the summer and the winter to account for the changing jet stream. Training the models to take in this data would not be especially challenging but it would take the project outside of its original scope of depending on data only from my own constructed weather station.

## Fetching Data and Applying the Models to Incoming Data
