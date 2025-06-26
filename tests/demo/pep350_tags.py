# --- Example Usage ---


# Example 1: Simple tag on its own line
# FIXME: Seems like this Loop should be finite. <MDE, CLE d:14w p:2>

# Example 2: Tag on the same line as code
while False:  # BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:14w p:2>
    pass


# Example 3: Multi-line field block
# TODO: This is a complex task that needs more details.
# <
#   assignee=JRNewbie
#   priority:3
#   due=2025-12-25
#   custom_field: some_value
# >


# Example 4: No codetag found
x = 2 + 1  # This is just a regular comment


# Example 5: Tag with mixed and spelled-out fields
# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>


# Example 6: Empty fields block
# NOTE: Remember to check performance. <>

# Not a comment
"""

Docstring contents are not comments, for our purposes.

NOTE: NOTHING TO SEE HERE. <>


"""

# Also not a comment
xyz = "NOTE: NOTHING TO SEE HERE. <>"

# Consecutive
# TODO: 1 <>
# NOTE: 2 <>
# RFE: 3 <>

if __name__ == "__main__":
    from code_tags.standard_code_tags import collect_pep350_code_tags

    for item in collect_pep350_code_tags(__file__):
        print(item)
