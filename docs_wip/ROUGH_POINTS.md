## high churn fields
- interation/sprint - 10-20 issue to update commits every 3 week
- status - depending on workflow, 3+ transitions/commits *per code tag*
- release - many issues to update and then remove at roughtly the same time

Possible solution
- keep high churn data out of tag. 
- Minimize transitions to 1, 2, or 3 max.
- Bulk update for release (all status done gets a release number, close date)

## Invisible Data
- Close data will be only visible in git history as the natural thing to do is to delete the code tag!

Possible solution
- Move to done module outside of /SRC/
- git integration

## High initialization cost
- Many fields to fill in to support features
- Deferred validation. Someone other that issue creator may have to fix the issue

## Branching
- Different views of reality on different branches


## Social Structure Implications
- assignee, originator - Someone makes an issue, some tells someone to work it. (Tech lead and devs?)
- Other roles missing, tester, product owner
- No tester or acceptance criteria. (ie. assumes non-objective close criteria)

## Project Management Implications
- Missing level of effort, except maybe developer self determined "due"
  - No story points, hours of effort, no days of work, no t-shirt size

## Calendar Implications
- origination date, due date, done date - What if it is an open source project and "due" is meaningless?

## Release/Iteration
- Releases have a string, e.g. 1.0.0, but no description, goal, etc.
- missing SAFe epics, missing fixed sprints