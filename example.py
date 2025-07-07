import pycodetags
from pycodetags import DataTagSchema

# DATA: temperature <98 humidity=54 wind=3>
# DATA: temperature <78 humidity=67 wind=2>
# DATA: temperature <humidity=67 wind=2>


# Schema-free example
data = pycodetags.load_all(open(__file__), include_folk_tags=False)

for datum in data:
    print(datum)

# Custom Schema Example
Temperatures: DataTagSchema = {
    "name": "Temperatures",
    "matching_tags": ["DATA", "TEMP"],
    "default_fields": {
        "int": "temperature"
    },
    "data_fields": {
        "wind": "int",
        "humidity": "int"
    },
    "data_field_aliases": {
        "w": "wind",
        "h": "humidity"
    },
    "field_infos": [{
        "name": "wind",
        "data_type": "float",
        "valid_values": [],
        "label": "Wind",
        "description": "Wind speed",
        "aliases": ["w", "vind"],

        "value_on_new": "",
        "value_on_blank": "",
        "value_on_delete": ""
    },
        {
            "name": "wind",
            "data_type": "float",
            "valid_values": [],
            "label": "Humidity",
            "description": "Humidity in Percent",
            "aliases": ["h", "humidity"],
            "value_on_new": "",
            "value_on_blank": "",
            "value_on_delete": ""
        }
    ]
}

data = pycodetags.load_all(open(__file__),
                           schema=Temperatures,
                           include_folk_tags=False)

for datum in data:
    print(datum.to_flat_dict())
