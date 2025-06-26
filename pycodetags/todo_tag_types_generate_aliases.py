"""
Generate main_types_aliases.py in a way that ensures intellisense works.
"""

import inspect
import textwrap
from dataclasses import field, fields
from typing import Any

from pycodetags.todo_tag_types import TODO


def generate_code_tags_file(output_filename: str = "main_types_aliases.py") -> None:
    """
    Generates a Python file containing the TODO dataclass and
    aliased factory functions with full IntelliSense support.
    """
    # --- 1. Define the TODO dataclass (or import it if it's in a separate file) ---
    # For this example, we'll embed the TODO definition for self-containment.
    # In a real project, you might import it from 'code_tags.main_types'.

    _temp_globals: dict[str, Any] = {}
    _TODO_cls = TODO

    # --- 2. Inspect TODO's fields for signature generation ---
    todo_init_fields = [f for f in fields(_TODO_cls) if f.init and f.name != "code_tag"]

    # Build the parameters string for the function signature
    params_str_parts = []
    for f in todo_init_fields:
        param_name = f.name
        param_type = inspect.formatannotation(f.type)  # Gets the string representation of the type

        # Handle default values
        if f.default is not field:
            # For simple defaults (strings, numbers, None)
            params_str_parts.append(f"{param_name}: {param_type} = {repr(f.default)}")
        elif f.default_factory is not field:
            # For default_factory, we can't put the factory in the signature directly.
            # Treat it as Optional and let the TODO constructor handle the default_factory.
            # Or you might omit it from the signature if it's always default-generated.
            # For IntelliSense, making it Optional[Type] is often best.
            if "None" not in param_type:  # Avoid double Optional or None | None
                params_str_parts.append(f"{param_name}: {param_type} | None = None")
            else:
                params_str_parts.append(f"{param_name}: {param_type} = None")
        else:
            # Required parameter with no default
            params_str_parts.append(f"{param_name}: {param_type}")

    # Add **kwargs to allow for future flexibility or passing through other arguments
    params_str = ", ".join(params_str_parts)
    if params_str:
        params_str += ", "
    # params_str += "**kwargs: Any"

    # Build the arguments string to pass to the TODO constructor
    args_to_pass = ", ".join([f"{f.name}={f.name}" for f in todo_init_fields])
    if args_to_pass:
        args_to_pass += ", "
    # args_to_pass += "**kwargs"

    # --- 3. Define the aliases and their corresponding code_tag values and docstrings ---
    aliases = {
        "REQUIREMENT": "Factory function to create a REQUIREMENT item.",
        "STORY": "Variation on TODO",
        "IDEA": "Variation on TODO",
        "FIXME": "This is broken, please fix",
        "BUG": "This is broken, please fix",
        "HACK": "Make code quality better",
        "CLEVER": "Make code quality better",
        "MAGIC": "Make code quality better",
        "ALERT": "An urgent TODO",
        "PORT": "Make this work in more environments",
        "DOCUMENT": "Add documentation. The code tag itself is not documentation.",
    }

    generated_alias_functions = []
    for alias_name, doc_string in aliases.items():
        func_code = textwrap.dedent(
            f"""
        def {alias_name}({params_str}) -> TODO:
            \"\"\"{doc_string}\"\"\"
            return TODO(code_tag="{alias_name}", {args_to_pass})
        """
        )
        generated_alias_functions.append(func_code)

    # --- 4. Assemble the full content of the output file ---
    full_output_content = ["\n\n".join(generated_alias_functions)]

    # --- 5. Write the content to the output file ---
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(
            """
\"\"\"
Aliases for TODO
\"\"\"
from __future__ import annotations

from typing import Any
from pycodetags.main_types import TODO
"""
        )
        file.write("\n\n".join(full_output_content))

    print(f"Successfully generated '{output_filename}' with IntelliSense-friendly aliases.")


if __name__ == "__main__":
    generate_code_tags_file()
