from pycodetags import DATA

# Standalone items. They don't throw.
ITEMS = [
    DATA(comment="Write documentation"),
]


# Stand alone functions with TODO/Done decorators
@DATA(comment="Implement payment logic")
def unfinished_feature():
    print("This should not run if overdue and assignee is Matthew.")


# This is a folk style
# TODO(Jack): jira.example.com/ticker-123 Implement credit system
def credit():
    pass


# BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:14w p:2>
def progravity():
    print("Not as funny as antigravity")
