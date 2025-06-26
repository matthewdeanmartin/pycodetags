import datetime

from pycodetags import FIXME, TODO, TodoException

# Standalone items. They don't throw.
ITEMS = [
    TODO(comment="Write documentation", due="05/01/2025"),
    TODO(
        status="done",
        comment="Name project",
        closed_date=datetime.datetime(2025, 6, 1),
        tracker="https://example.com/done/123",
    ),
    FIXME(comment="Division by zero", tracker="https://example.com/project/456"),
]


# Stand alone functions with TODO/Done decorators
@TODO(assignee="matth", due="06/01/2025", comment="Implement payment logic")
def unfinished_feature():
    print("This should not run if overdue and assignee is Matthew.")


@TODO(status="done", tracker="https://ticketsystem/123")
def finished_feature():
    print("This is a completed feature.")


@TODO(assignee="matth", due="06/01/2025", comment="This whole game needs to be written")
class Game:
    def __init__(self):
        pass

    @TODO(assignee="matth", due="06/01/2025", comment="Implement game loop")
    def game_loop(self):
        pass

    def hero_screen(self):
        raise TodoException(assignee="alice", due="06/01/2025", message="Do game art")


if __name__ == "__main__":
    finished_feature()
    unfinished_feature()
