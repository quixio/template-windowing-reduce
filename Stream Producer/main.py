from dataclasses import dataclass, asdict # used to define the data schema
from datetime import datetime # used to manage timestamps
from time import sleep  # used to slow down the data generator
import uuid # used for message id creation
import json # used for serializing data
import random

from quixstreams import Application

app = Application.Quix()
destination_topic = app.topic(name='raw-temp-data', value_serializer="json")

@dataclass
class Temperature:
    ts: datetime
    value: int

    def to_json(self):
        # Convert the dataclass to a dictionary
        data = asdict(self)
        # Format the datetime object as a string
        data['ts'] = self.ts.isoformat()
        # Serialize the dictionary to a JSON string
        return json.dumps(data)
    
i = 0
with app.get_producer() as producer:
    while i < 10000:
        sensor_id = random.choice(["Sensor1", "Sensor2", "Sensor3", "Sensor4", "Sensor5"])
        temperature = Temperature(datetime.now(), random.randint(0, 100))
        value = temperature.to_json()

        print(f"Producing value {value}")
        serialized = destination_topic.serialize(
            key=sensor_id, value=value, headers={"uuid": str(uuid.uuid4())}
        )
        producer.produce(
            topic=destination_topic.name,
            headers=serialized.headers,
            key=serialized.key,
            value=serialized.value,
        )
        i += 1
        sleep(random.randint(0, 1000) / 1000)