from pycodetags_issue_tracker.converters import convert_datas_to_TODOs

import pycodetags as p

bug = p.loads("# BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:14w p:2 x:1>")
print(bug)
print(bug.as_data_comment())
print(bug.custom_fields)
todos = convert_datas_to_TODOs([bug])
for todo in todos:
    print("---")
    print(todo.custom_fields)
