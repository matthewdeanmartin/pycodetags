# PYCODETAGS PEP 005 — Optional Quotes on Data Fields


| PEP:             | 005                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Optional Quotes on Data Fields                                                    |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.6.0                                                                           |


## Abstract
This PEP proposes relaxing the requirement for quoted values in code tag field syntax. By enforcing an ordering constraint—default/anonymous fields must appear before named fields—we can safely allow spaces in named field values without requiring quotes.

---

## Motivation

Currently, field values that include spaces or special characters must be quoted:

```python
# TODO: Improve logging <tracker:"https://example.com/t/123" data:"High priority task">
```

This is safe but verbose. In practice, most users expect the following to work:

```python
# TODO: Improve logging <tracker:https://example.com/t/123 data:High priority task>
```

However, unquoted values with spaces are currently ambiguous in the parser.

We propose an update to the parser that removes this ambiguity by requiring **default/anonymous values always appear first**, thus allowing a safe greedy parse of named fields regardless of spacing.

---

## Proposal

### New Field Ordering Rule:

* **Unlabeled/default fields** (e.g., `"alice"`, `"2025-07-12"`) must appear **at the beginning** of the `<...>` block.
* **Named fields** (`key:value`) must follow.
* Once a named field is encountered, all subsequent tokens must be named fields.

### Relaxed Quoting

* Values containing spaces in **named fields** do **not** require quotes.
* Quoting is still respected and supported for values containing special characters like `:`, `=`, or `<`.

---

## Examples

### ✅ Valid (new style):

```python
# TODO: Improve logging <alice 2025-07-12 priority:high tracker:https://example.com/t/123 data:High priority task>
```

### ✅ Valid (old style):

```python
# TODO: Improve logging <"alice" "2025-07-12" priority:"high" tracker:"https://example.com/t/123" data:"High priority task">
```

### ❌ Invalid:

```python
# TODO: <priority:high alice>  # Default field after named field is disallowed
```

---

## Parsing Semantics

### Updated Parsing Algorithm:

1. **Tokenize** the field block (`<...>`) by whitespace.
2. **Consume leading tokens** as **unlabeled** until a `:` or `=` is detected in a token.
3. From the first labeled token onward, **treat all subsequent tokens** as `key:value` pairs.
4. For labeled tokens:

   * Assume the first `:` or `=` splits the key and value.
   * The value may contain spaces if it does not begin a new `key:...` pattern.
   * Whitespace joins are greedy within that field.

### Greedy Join Example:

```python
# TODO: <data:High priority task with follow-up required>
```

Is parsed as:

```json
{
  "default_fields": [],
  "data_fields": {
    "data": "High priority task with follow-up required"
  }
}
```

---

## Backward Compatibility

This is fully backward compatible:

* Existing quoted field values continue to parse identically.
* Existing field orderings (default followed by named) are typically already respected.

---

## Migration Notes

For forward compatibility, users should:

* Always place anonymous/default fields first.
* Avoid mixing unlabeled values after labeled fields.

---

## Implementation Plan

* [ ] Update `parse_fields()` in `data_tags_parsers.py` to track parsing phase (`default` vs `named`)
* [ ] Relax field value matching to be greedy until next `key:` or `key=`
* [ ] Update error reporting for out-of-order default fields
* [ ] Document new syntax in CLI help and README
* [ ] Add regression tests covering quote and no-quote cases

---

## Benefits

* Improved ergonomics and readability
* Closer alignment with user expectations and common tag styles
* Avoids “quoted hell” when entering simple text fields

---

## Risks

* Incorrect field order (e.g., unlabeled after named) will now raise a parse error
* Some ambiguity remains in edge cases (e.g., `foo:bar:baz`) but these are rare and already supported

---

## Summary

This PEP simplifies the PyCodeTags syntax while preserving full safety and backward compatibility by introducing a single constraint: default fields must appear before named ones. This enables users to write natural, readable field values without excessive quoting.

---

## Reference Implementation

```python
def parse_fields(field_string: str, schema: DataTagSchema, strict: bool) -> DataTagFields:
    legit_names = {}
    for key in schema["data_fields"]:
        legit_names[key] = key
    field_aliases: dict[str, str] = merge_two_dicts(schema["data_field_aliases"], legit_names)

    fields: DataTagFields = {
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {},
        "unprocessed_defaults": [],
        "identity_fields": [],
    }

    tokens = field_string.strip().split()
    phase = "default"  # or "named"

    default_type_order = ["int", "date", "str", "str|list[str]"]
    default_key_map = {t: schema["default_fields"].get(t) for t in default_type_order}

    def assign_default_token(token: str) -> bool:
        for dtype in default_type_order:
            key = default_key_map.get(dtype)
            if not key:
                continue
            if dtype == "int" and is_int(token):
                fields["default_fields"][key] = token
                return True
            elif dtype == "date" and re.match(r"\d{4}-\d{2}-\d{2}", token):
                fields["default_fields"][key] = token
                return True
            elif dtype in ("str", "str|list[str]"):
                if key in fields["default_fields"]:
                    fields["default_fields"][key].append(token)
                else:
                    fields["default_fields"][key] = [token]
                return True
        return False

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if ":" in token or "=" in token:
            phase = "named"
            sep = ":" if ":" in token else "="
            key, first_part = token.split(sep, 1)
            value_parts = [first_part]
            i += 1
            while i < len(tokens) and not (":" in tokens[i] or "=" in tokens[i]):
                value_parts.append(tokens[i])
                i += 1
            value = " ".join(value_parts)
            key_lower = key.lower()
            if key_lower in field_aliases:
                fields["data_fields"][field_aliases[key_lower]] = value
            else:
                fields["custom_fields"][key] = value
        else:
            if phase == "named":
                raise SchemaError(
                    f"Default field '{token}' appears after named fields. "
                    "Default (anonymous) values must appear first."
                )
            assigned = assign_default_token(token)
            if not assigned:
                fields["unprocessed_defaults"].append(token)
            i += 1

    return fields

```
## Copyright

This document is licensed under the MIT License.
