import json
import logging

from datetime import datetime, timedelta
from quixstreams import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TOPIC = "raw-temperature" # defines the input topic
SINK = "agg-temperature"  # defines the output topic
WINDOW = 10  # defines the length of the time window in seconds
WINDOW_EXPIRES = 1 # defines, in seconds, how late data can arrive before it is excluded from the window

app = Application.Quix(
       consumer_group="quix-stream-processor",
       auto_offset_reset="earliest")

input_topic = app.topic(TOPIC, value_deserializer="json")
output_topic = app.topic(SINK, value_serializer="json")

sdf = app.dataframe(input_topic)
sdf = sdf.update(lambda value: logger.info(f"Input value received: {value}"))

def custom_ts_extractor(value):
 
    # Extract the sensor's timestamp and convert to a datetime object
    dt_obj = datetime.strptime(value["ts"], "%Y-%m-%dT%H:%M:%S.%f") # 

    # Convert to milliseconds since the Unix epoch for efficent procesing with Quix
    milliseconds = int(dt_obj.timestamp() * 1000)
    value["timestamp"] = milliseconds
    logger.info(f"Value of new timestamp is: {value['timestamp']}")

    return value["timestamp"]

# Override the previously defined input_topic variable so that it uses the custom timestamp extractor 
input_topic = app.topic(TOPIC, timestamp_extractor=custom_ts_extractor, value_deserializer="json") 

def initializer(value: dict) -> dict:

    value_dict = json.loads(value)
    return {
        'count': 1,
        'min': value_dict['value'],
        'max': value_dict['value'],
        'mean': value_dict['value'],
    }

def reducer(aggregated: dict, value: dict) -> dict:
    aggcount = aggregated['count'] + 1
    value_dict = json.loads(value)
    return {
        'count': aggcount,
        'min': min(aggregated['min'], value_dict['value']),
        'max': max(aggregated['max'], value_dict['value']),
        'mean': (aggregated['mean'] * aggregated['count'] + value_dict['value']) / (aggregated['count'] + 1)
    }

### Define the window parameters such as type and length

sdf = (
    # Define a tumbling window of 10 seconds
    sdf.tumbling_window(timedelta(seconds=WINDOW), grace_ms=timedelta(seconds=WINDOW_EXPIRES))

    # Create a "reduce" aggregation with "reducer" and "initializer" functions
    .reduce(reducer=reducer, initializer=initializer)

    # Emit results only for closed 10 second windows
    .final()
)

### Apply the window to the Streaming DataFrame and define the data points to include in the output
sdf = sdf.apply(
    lambda value: {
        "time": value["end"], # Use the window end time as the timestamp for message sent to the 'agg-temperature' topic
        "temperature": value["value"], # Send a dictionary of {count, min, max, mean} values for the temperature parameter
    }
)

sdf = sdf.to_topic(output_topic)
sdf = sdf.update(lambda value: logger.info(f"Produced value: {value}"))

if __name__ == "__main__":
    logger.info("Starting application")
    app.run(sdf)