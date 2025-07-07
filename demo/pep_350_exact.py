import datetime
import os

# Example script demonstrating codetags as defined in PEP 350

# --- Custom Fields ---
# CUSTOM: Everything here is custom. <q:123 flurb:abc>
while True:
    break

# --- FIXME ---
# FIXME: Seems like this loop should be finite. <MDE,CLE d:14w p:2>
while True:
    break  # Simulate a fix

# --- BUG ---
# BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:14w p:2>

day = datetime.datetime.now().strftime("%A")
if day == "Sunday":
    print("Warning: Avoid running this on Sunday!")


# --- TODO ---
# TODO: Implement feature X. <MicahE d:2025-08-01 p:1>
def feature_x():
    pass  # placeholder for implementation


# --- NOBUG ---
# NOBUG: Known limitation due to third-party API. <MDE d:2025-09-01 p:0>
def third_party_wrapper():
    pass  # Won't fix the issue


# --- REQ ---
# REQ: Must comply with data regulation XYZ. <CLE 2025-07-01 d:2025-09-01 p:2>
data_policy_compliance = True


# --- RFE ---
# RFE: Add support for YAML configuration files. <CLE a:MDE d:2025-10-15 p:1>
def load_yaml_config():
    pass  # Enhancement pending


# --- IDEA ---
# IDEA: Could optimize this algorithm with memoization. <MDE d:30w p:2>
def slow_function(n):
    if n <= 1:
        return n
    return slow_function(n - 1) + slow_function(n - 2)


# --- ??? ---
# ???: Why is this conversion necessary? <CLE 2025-07-05 p:1>
def mysterious_conversion(x):
    return int(str(x))


# --- !!! ---
# !!!: This must be fixed before release! <MDE d:28w p:3>
assert True  # Critical section check placeholder


# --- HACK ---
# HACK: Bypass login in dev environment. <CLE 2025-07-01 s:inprogress>
def login():
    return True  # Stub


# --- PORT ---
# PORT: Use `os.name` to detect OS-specific behavior. <MDE 2025-07-01 c:win>


if os.name == "nt":
    print("Running on Windows")


# --- CAVEAT ---
# CAVEAT: Does not handle leap seconds. <CLE 2025-07-12 d:36w p:1>
def timestamp():
    return datetime.datetime.now().timestamp()


# --- NOTE ---
# NOTE: Review this logic for edge cases. <MDE 2025-07-10 p:1>
def process(data):
    return sorted(data)


# --- FAQ ---
# FAQ: Why not use numpy here? Simplicity. <CLE d:35w p:0>
def sum_list(lst):
    return sum(lst)


# --- GLOSS ---
# GLOSS: 'Codetag' = tagged comment for tracking. <MicahE 2025-07-12>

# --- SEE ---
# SEE: https://example.com/docs <CLE t:1024>

# --- TODOC ---
# TODOC: Add proper docstrings to all public functions. <MDE d:38w p:1>

# --- CRED ---
# CRED: Thanks to CLE for original algorithm idea. <MDE 2025-07-12>

# --- STAT ---
# STAT: Prototype code, not production ready. <CLE s:inprogress>

# --- RVD ---
# RVD: Reviewed and approved by MDE. <>

if __name__ == "__main__":
    print("Codetag demo complete.")
