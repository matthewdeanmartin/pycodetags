from __future__ import annotations

import os


def init_pycodetags_config() -> None:
    """
    Initializes the [tool.pycodetags] section in pyproject.toml with 0 dependencies.

    This interactive script will:
    1. Check for an existing `pycodetags` configuration and exit if found.
    2. Scan the current directory for potential Python source folders.
    3. Ask the user to confirm the correct source folder.
    4. Generate a default configuration for pycodetags with helpful comments.
    5. Safely add this configuration to `pyproject.toml`, creating the file if it
       doesn't exist.
    """
    pyproject_path = "pyproject.toml"
    print("--- PyCodeTags Config Initializer ---")

    # Step 1: Check if the configuration already exists to prevent overwriting.
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, encoding="utf-8") as f:
                content = f.read()
            if "[tool.pycodetags]" in content:
                print(f"\nConfiguration for '[tool.pycodetags]' already exists in {pyproject_path}.")
                print("Initialization is not needed. Please edit the file manually for any changes.")
                return
        except OSError as e:
            print(f"Error reading {pyproject_path}: {e}")
            return

    # Step 2: Find potential source folders and get user selection.
    print("\nSearching for potential source code folders...")
    potential_folders = _find_potential_src_folders()

    if not potential_folders:
        print("Could not automatically detect any source folders.")
        src_folder = input("Please manually enter the path to your source folder (e.g., 'src', 'my_app'): ")
    else:
        src_folder = _select_src_folder_interactive(potential_folders) or ""

    if not src_folder or not src_folder.strip():
        print("\nNo source folder selected. Aborting initialization.")
        return

    print(f"\nUsing '{src_folder}' as the primary source folder.")

    # Step 3: Generate the TOML content.
    toml_section = _generate_pycodetags_toml_section(src_folder)

    # Step 4: Safely write the content to pyproject.toml.
    _write_to_pyproject_safe(toml_section, pyproject_path)

    print("\nInitialization complete! You can now customize the settings in pyproject.toml.")


def _find_potential_src_folders(root: str = ".") -> list[str]:
    """
    Identifies potential source code folders in the given root directory.

    It prioritizes common names like 'src' and the project's root folder name,
    then scans for other directories containing Python files.
    """
    folders = []
    # The current directory's name is often the package name.
    project_name = os.path.basename(os.path.abspath(root))

    # Check for common source folder names first.
    for name in ["src", "app", project_name]:
        if os.path.isdir(name) and name not in folders:
            # Check if it actually contains python files to reduce noise.
            try:
                if any(f.endswith(".py") for f in os.listdir(name)):
                    folders.append(name)
            except OSError:
                continue  # Ignore permission errors

    # Find other directories at the top level that contain .py files.
    for item in os.listdir(root):
        if os.path.isdir(item) and not item.startswith(".") and "venv" not in item:
            if item in folders:
                continue
            try:
                if any(f.endswith(".py") for f in os.listdir(item)):
                    folders.append(item)
            except OSError:
                continue  # Ignore permission errors

    return folders


def _select_src_folder_interactive(folders: list[str]) -> str | None:
    """
    Prompts the user to select their source folder from a list.
    """
    print("\nPlease select your primary source folder from the list below:")
    for i, folder in enumerate(folders):
        print(f"  {i+1}) {folder}")
    print(f"  {len(folders)+1}) [Manual Entry]")
    print(f"  {len(folders)+2}) [Cancel]")

    while True:
        try:
            choice_str = input(f"Enter your choice [1-{len(folders)+2}]: ")
            choice_int = int(choice_str)
            if 1 <= choice_int <= len(folders):
                return folders[choice_int - 1]
            elif choice_int == len(folders) + 1:
                return input("Enter path to your source folder: ")
            elif choice_int == len(folders) + 2:
                return None
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(folders)+2}.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number from the list.")


def _generate_pycodetags_toml_section(src_folder: str) -> str:
    """
    Generates the [tool.pycodetags] TOML string with helpful comments.
    """
    return f"""
[tool.pycodetags]
# Source folders to scan for code tags.
# This allows you to run `pycodetags` without specifying the path every time.
src = ["{src_folder}"]

# --- Optional: Common Configurations ---

# Specify Python modules to scan. Useful if your project structure is complex.
# modules = []

# Define which tag schemas are active.
# Default schemas are: todo, fixme, hack, note, perf, bug, question, important
# Example: active_schemas = ["todo", "fixme", "bug"]

# --- Runtime Behavior Control ---
# These settings control pycodetags's behavior when imported in your code.

# Master switch to disable all runtime features (e.g., for production).
# Setting this to true ensures zero performance overhead from the library.
disable_all_runtime_behavior = false

# Enables or disables the runtime actions ('log', 'warn', 'stop').
# If false, runtime checks are silent, even if `disable_all_runtime_behavior` is false.
enable_actions = true

# Default action for runtime checks if a tag doesn't specify one.
# Valid options: "warn", "stop" (raises TypeError), "log", or "nothing".
default_action = "warn"

# Automatically disables all runtime actions when in a CI environment.
# Checks for common CI environment variables (e.g., CI, GITHUB_ACTIONS).
disable_on_ci = true

# Allow pycodetags to load environment variables from a .env file.
use_dot_env = true
"""


def _write_to_pyproject_safe(toml_section: str, pyproject_path: str) -> None:
    """
    Safely appends the configuration to pyproject.toml.

    It creates the file if it doesn't exist and adds newlines for separation
    if the file already has content.
    """
    try:
        # Open in append mode, which creates the file if it doesn't exist.
        with open(pyproject_path, "a", encoding="utf-8") as f:
            # f.tell() gives the current position. If > 0, the file is not empty.
            if f.tell() > 0:
                f.write("\n")  # Add a blank line for separation.

            f.write(toml_section.strip())

        print(f"\nSuccessfully configured '[tool.pycodetags]' in {pyproject_path}")
    except OSError as e:
        print(f"\nError: Could not write to {pyproject_path}. {e}")


if __name__ == "__main__":
    # To run this script directly, save it as a .py file (e.g., setup_codetags.py)
    # and run `python setup_codetags.py` in your project's root directory.
    init_pycodetags_config()
