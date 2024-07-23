#include "thingProperties.h"
#include <Wire.h> // I2C connection
#include <BH1750.h> // light meter
#include <Adafruit_Sensor.h>  // BME sensor
#include <Adafruit_BME280.h>  // BME sensor
#include <OneWire.h>  // Ground temp
#include <DallasTemperature.h> // Ground temp

// Pin declarations
#define UV_PIN A7
#define SOIL_PROBE_PIN 4
#define WIND_SPEED_PIN 2
#define WIND_DIRECTION_PIN A0
#define RAIN_PIN 3

// Objects
BH1750 light_meter;  // Address: 0x23
Adafruit_BME280 bme;  // Address: 0x77
OneWire one_wire(SOIL_PROBE_PIN);
DallasTemperature sensors(&one_wire);

// Global variables
const unsigned long ONE_DAY_SECONDS = 86400;
const float VOLT2UV_FACTOR = 10;
bool new_day = false; /* Variable allows ease of checking by certain processes if a new day has begun.
This variable is updated by a function that relies on time since the epoch which is obtained through a Arduino Cloud provided function. */

volatile unsigned long wind_speed_count = 0;  // Volatile for use with ISR
unsigned long last_wind_speed_time = 0;
float wind_speed = 0;

// Wind rolling average variables
const int ROLLING_WINDOW_SIZE = 120; // 120 seconds for a 2-minute window
float wind_speed_buffer[ROLLING_WINDOW_SIZE] = {0};
int wind_read_index = 0;
float wind_sum = 0;

int wind_direction = 0;

volatile unsigned long rain_count = 0; // Volatile for use with ISR

// UV rolling average variables
int uv_index;
float uv_buffer[ROLLING_WINDOW_SIZE] = {0};
int uv_buffer_index = 0;
float uv_sum = 0;

// Function prototypes
void windSpeedISR();
void rainISR();
void checkForNewDay();
void readBMESensor();
void updateUVIndex();
void updateWindSpeed();
void calculateWindDirection();
void calculateRainAccumulation();
void resetDailyMetrics();

void setup() {
  Serial.begin(9600);
  delay(1500); 

  // Defined in thingProperties.h
  initProperties();

  // Connect to Arduino IoT Cloud
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);
  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();

  Wire.begin();

  // Light meter
  if (!light_meter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("BH1750 Failure");
    while (1);
  }

  // BME sensor
  if (!bme.begin(0x77)) {
    Serial.println("BMP Failure");
    while(1);
  }

  pinMode(UV_PIN, INPUT);
  pinMode(WIND_SPEED_PIN, INPUT_PULLUP);
  pinMode(WIND_DIRECTION_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT_PULLUP);

  sensors.begin();  // Ground temp probe

  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(WIND_SPEED_PIN), windSpeedISR, FALLING);
  attachInterrupt(digitalPinToInterrupt(RAIN_PIN), rainISR, FALLING);
}

void loop() {
  ArduinoCloud.update();
  
  checkForNewDay();
  
  // Light meter
  lux = light_meter.readLightLevel();

  // BME sensor (temp, humidity, pressure)
  readBMESensor();

  // UV sensor
  updateUVIndex();

  // Gound temperature
  sensors.requestTemperatures();
  float temp_c = sensors.getTempCByIndex(0);
  temp_f = sensors.toFahrenheit(temp_c);

  // Calculate wind speed
  updateWindSpeed();

  // Calculate wind directions
  calculateWindDirection();

  // Calculate rain accumulation
  calculateRainAccumulation();

  // Reset daily max and min temps, reset max wind speed and direction
  resetDailyMetrics();

  delay(500); // Reduce CPU load
}

// Function implementations
void windSpeedISR() {
  static unsigned long last_interrupt_time = 0;
  unsigned long interrupt_time = millis();

  if (interrupt_time - last_interrupt_time > 50) {  // Debounce time of 50 ms
    wind_speed_count++;
    last_interrupt_time = interrupt_time;
  }
}

void rainISR() {
  static unsigned long last_interrupt_time = 0;
  unsigned long interrupt_time = millis();

  if (interrupt_time - last_interrupt_time > 10) { // Debounce time of 10 ms
    rain_count++;
    last_interrupt_time = interrupt_time;
  }
}

void checkForNewDay() {
  epoch_time = ArduinoCloud.getLocalTime();

  if ((epoch_time % ONE_DAY_SECONDS) < 3) { // Not simply chekcing equality to zero to allow for the expected delays that result from this program
    new_day = true;
  }
}

void readBMESensor() {
  bme_temp = ((bme.readTemperature()) * 1.8) + 32;
  float bme_temp_cels = bme.readTemperature();  // Celsius needed for dew point calculation
  bme_pressure = bme.readPressure() / 100.0; // Pa to hPa
  bme_humidity = bme.readHumidity();
  float bme_humidity_dec = bme_humidity / 100;  // Humidity as a decimal needed for dew point calculation

  // Daily max and min temps
  if (bme_temp > max_temp_today) {
    max_temp_today = bme_temp;
  }
  if (bme_temp < min_temp_today) {
    min_temp_today = bme_temp;
  }
  // **Resetting of max/min daily temps done in resetDailyMetrics()

  // Dew point calculation
  float alpha = (17.27 * bme_temp_cels) / (237.7 + bme_temp_cels) + log(bme_humidity_dec);
  float dew_point_c = (237.7 * alpha) / (17.27 - alpha);
  dew_point = (dew_point_c * 1.8) + 32;
}

void updateUVIndex() {
  int uv_value = analogRead(UV_PIN);
  float voltage = uv_value * (3.3 / 1023);
  uv_index = voltage * VOLT2UV_FACTOR;

  // Update the UV rolling average
  /* Rolling average desired because of the possibility of a partly cloudy sky 
  causing semi-rapid changes to the measured UV index - I want to see an average */
  uv_sum -= uv_buffer[uv_buffer_index];
  uv_buffer[uv_buffer_index] = uv_index;
  uv_sum += uv_index;
  uv_buffer_index = (uv_buffer_index + 1) % ROLLING_WINDOW_SIZE;
  uv_rolling_average = uv_sum / ROLLING_WINDOW_SIZE;
}

void updateWindSpeed() {
  unsigned long current_time = millis();

  if (current_time - last_wind_speed_time >= 1000) { // Update every second
    noInterrupts(); // Temporarily disable interrupts while we calculate wind speed
    float rotations = wind_speed_count;
    wind_speed = (rotations * 1.492) / 2; // 1.492 mph wind speed --> 1 rot/sec, there is 2 drops per rotation
    wind_speed_count = 0; // Reset counter for the next second
    last_wind_speed_time = current_time;
    interrupts(); // Re-enable interrupts

    // Update the rolling average
    wind_sum -= wind_speed_buffer[wind_read_index]; // Subtract the oldest value
    wind_speed_buffer[wind_read_index] = wind_speed; // Add the new wind speed
    wind_sum += wind_speed; // Update the sum
    wind_read_index = (wind_read_index + 1) % ROLLING_WINDOW_SIZE; // Update the index
    wind_rolling_average = wind_sum / ROLLING_WINDOW_SIZE; // Calculate the rolling average
  }
}

void calculateWindDirection() {
  wind_direction = analogRead(WIND_DIRECTION_PIN); // Reading the differing voltage as analog value
  // Convert analog value from wind vane into corresponding wind direction. 
  switch (wind_direction) {
    case 644 ... 662: wind_dir_string = "N"; break;
    case 591 ... 609: wind_dir_string = "NNW"; break;
    case 891 ... 909: wind_dir_string = "NW"; break;
    case 841 ... 859: wind_dir_string = "WNW"; break;
    case 954 ... 972: wind_dir_string = "W"; break;
    case 920 ... 938: wind_dir_string = "WSW"; break;
    case 983 ... 1001: wind_dir_string = "SW"; break;
    case 766 ... 784: wind_dir_string = "SSW"; break;
    case 791 ... 809: wind_dir_string = "S"; break;
    case 403 ... 421: wind_dir_string = "SSE"; break;
    case 458 ... 476: wind_dir_string = "SE"; break;
    case 228 ... 246: wind_dir_string = "ESE"; break;
    case 319 ... 337: wind_dir_string = "E"; break;
    case 122 ... 140: wind_dir_string = "ENE"; break;
    case 171 ... 189: wind_dir_string = "NE"; break;
    case 151 ... 169: wind_dir_string = "NNE"; break;
    default: wind_dir_string = "Erroneous reading"; break;
  }

  // Daily max wind speed and direction
  if (wind_speed > max_wind_speed_today) {
    max_wind_speed_today = wind_speed;
    prevailing_wind_direction = wind_dir_string;  /* Prevailing wind direction is direction of current wind which has just been updated */
  } 
  // **Resetting of max daily wind speed done in resetDailyMetrics()
}

void calculateRainAccumulation() {
  noInterrupts();
  rain_accumulation = rain_count * 0.011; // 0.011 inches of rain per tip of sensor
  interrupts();

  // Reset rain accumulation data
  if (new_day) {  // 1 day has elapsed
    // Using individual variables because Arduino Cloud does not support arrays
    rain_6d_ago = rain_5d_ago;
    rain_5d_ago = rain_4d_ago;
    rain_4d_ago = rain_3d_ago;
    rain_3d_ago = rain_2d_ago;
    rain_2d_ago = rain_1d_ago;
    rain_1d_ago = rain_accumulation;

    noInterrupts();
    rain_count = 0;
    interrupts();
  }
}

void resetDailyMetrics() {
  if (new_day) {
    max_temp_today = -100;
    min_temp_today = 200;
    max_wind_speed_today = -1;
    new_day = false; // Reset new_day now that variables are reset
  }
}

void onEpochTimeChange()  {  // Function for read-write variable from cloud
}