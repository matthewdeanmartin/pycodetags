import pycodetags
from pycodetags import DataTagSchema

# DATA: temperature <98 humidity=54 wind=3>
# DATA: temperature <78 humidity=67 wind=2>


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
        "wind":"int",
        "humidity":"int"
    },
    "data_field_aliases": {
        "w": "wind",
        "h": "humidity"
    }
}

data = pycodetags.load_all(open(__file__),
                           schema=Temperatures,
                           include_folk_tags=False)

for datum in data:
    print(datum.to_flat_dict())
