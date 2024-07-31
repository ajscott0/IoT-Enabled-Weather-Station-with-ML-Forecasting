#include <ArduinoIoTCloud.h>
#include <Arduino_ConnectionHandler.h>

const char SSID[]     = "******";
const char PASS[]     = "******";

void onEpochTimeChange();

String prevailing_wind_direction;
String wind_dir_string;
float bme_humidity;
float bme_pressure;
float bme_temp;
float dew_point;
float max_temp_today;
float max_wind_speed_today;
float min_temp_today;
float rain_1d_ago;
float rain_2d_ago;
float rain_3d_ago;
float rain_4d_ago;
float rain_5d_ago;
float rain_6d_ago;
float rain_accumulation;
float temp_f;
float uv_rolling_average;
float wind_rolling_average;
int epoch_time;
int lux;

void initProperties() {
    ArduinoCloud.addProperty(prevailing_wind_direction, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(wind_dir_string, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(bme_humidity, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(bme_pressure, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(bme_temp, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(dew_point, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(max_temp_today, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(max_wind_speed_today, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(min_temp_today, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(rain_1d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_2d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_3d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_4d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_5d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_6d_ago, READ, ON_CHANGE, NULL);
    ArduinoCloud.addProperty(rain_accumulation, READ, 10 * SECONDS, NULL);
    ArduinoCloud.addProperty(temp_f, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(uv_rolling_average, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(wind_rolling_average, READ, 3 * SECONDS, NULL);
    ArduinoCloud.addProperty(epoch_time, READWRITE, ON_CHANGE, onEpochTimeChange);
    ArduinoCloud.addProperty(lux, READ, 3 * SECONDS, NULL);
}

WiFiConnectionHandler ArduinoIoTPreferredConnection(SSID, PASS);
