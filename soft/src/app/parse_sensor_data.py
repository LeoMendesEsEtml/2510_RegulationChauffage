import csv

def parse_sensor_data(file_path):
    """
    Parse the sensor data from the provided CSV file.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        dict: A dictionary where keys are sensor names and values are lists of (temperature, resistance) tuples.
    """
    sensor_data = {}

    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            section = row['section']
            sensor = row['sensor']
            temp = float(row['temp_C'])
            resistance = float(row['R_ohm'])

            if section not in sensor_data:
                sensor_data[section] = {}

            if sensor not in sensor_data[section]:
                sensor_data[section][sensor] = []

            sensor_data[section][sensor].append((temp, resistance))

    return sensor_data

# Example usage
if __name__ == "__main__":
    file_path = "sensor_resistance_reference.csv"
    data = parse_sensor_data(file_path)
    print(data)