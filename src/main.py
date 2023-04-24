from bme680 import BME680
from bme680.constants import (
    ENABLE_GAS_MEAS,
    FILTER_SIZE_3,
    I2C_ADDR_PRIMARY,
    I2C_ADDR_SECONDARY,
    OS_2X,
    OS_4X,
    OS_8X,
)
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class Sensor:
    def __init__(self):
        try:
            self.sensor = BME680(I2C_ADDR_PRIMARY)
        except (RuntimeError, IOError):
            self.sensor = BME680(I2C_ADDR_SECONDARY)

        self.sensor.set_humidity_oversample(OS_2X)
        self.sensor.set_pressure_oversample(OS_4X)
        self.sensor.set_temperature_oversample(OS_8X)
        self.sensor.set_filter(FILTER_SIZE_3)
        self.sensor.set_gas_status(ENABLE_GAS_MEAS)

        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

    def calibrate(self):
        for name in dir(self.sensor.calibration_data):
            for name in dir(self.sensor.calibration_data):
                if not name.startswith("_"):
                    value = getattr(self.sensor.calibration_data, name)

                    if isinstance(value, int):
                        print("{}: {}".format(name, value))

    def read(self):
        m = Point("bme680")

        if self.sensor.get_sensor_data():
            if self.sensor.data.temperature is not None:
                m = m.field("celcius", self.sensor.data.temperature)

            if self.sensor.data.pressure is not None:
                m = m.field("pressure", self.sensor.data.pressure)

            if self.sensor.data.humidity is not None:
                m = m.field("humidity", self.sensor.data.humidity)

            if (
                self.sensor.data.heat_stable
                and self.sensor.data.gas_resistance is not None
            ):
                m = m.field("gas_resistance", self.sensor.data.gas_resistance)

            return m

        return None


class DataStore:
    def __init__(self, url: str, token: str, organization: str, bucket: str) -> None:
        self.url = url
        self.token = token
        self.organization = organization
        self.bucket = bucket

        self.client = InfluxDBClient(url=url, token=token, org=organization)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def save_metric(self, metrics: Point):
        self.write_api.write(bucket=self.bucket, org=self.organization, record=metrics)


if __name__ == "__main__":
    import time
    from os import environ

    from dotenv import load_dotenv

    load_dotenv()

    token = environ.get("INFLUXDB_TOKEN")

    if token is None:
        raise Exception("Missing INFLUXDB_TOKEN env")

    organization = environ.get("INFLUXDB_ORGANIZATION")

    if organization is None:
        raise Exception("Missing INFLUXDB_ORGANIZATION env")

    url = environ.get("INFLUXDB_URL")

    if url is None:
        raise Exception("Missing INFLUXDB_URL env")

    bucket = environ.get("INFLUXDB_BUCKET")

    if bucket is None:
        raise Exception("Missing INFLUXDB_BUCKET env")

    store = DataStore(token=token, url=url, organization=organization, bucket=bucket)

    sensor = Sensor()

    sensor.calibrate()

    while True:
        reading = sensor.read()

        if reading is not None:
            store.save_metric(reading)

        time.sleep(1)
