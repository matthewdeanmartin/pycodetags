# Data Tags

A data tag holds any data in a python comment.

```python
# DATA: temperature <98 humidity=54 wind=3>
# DATA: temperature <78 humidity=67 wind=2>
```

Data tags are not intended to be a general purpose data format. They enable a separation of domain specific concerns
from the data serialization and parsing concerns. You should still use json,
dict, or other formats first and data tags when your application has a
compelling reason to store data in python comments.

## Schema

A data tag has:

- a tag name that informs what schema is active
- a comment that is natural language for humans to read
- custom fields, which are domain free
- default fields, which do not have a key and are recognized by type

A data tag does not have

- data fields, those require a domain specific schema.

## Views

Export to

- Json
- Python comments


## Complete Example

```python
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
```