from pycodetags import DATA

# Standalone items. They don't throw.
ITEMS = [
    DATA(comment="Write documentation", custom_fields={"due": "2015-06-06"}),
    DATA(comment="Name project", custom_fields={"due": "2015-06-06"}),
    DATA(comment="Division by zero", custom_fields={"due": "2015-06-06"}),
]


# Stand alone functions with TODO/Done decorators
@DATA(custom_fields={"due": "2015-06-06"}, comment="Implement payment logic")
def unfinished_feature():
    print("This should not run if overdue and assignee is Matthew.")


@DATA(custom_fields={"due": "2015-06-06"})
def finished_feature():
    print("This is a completed feature.")


@DATA(custom_fields={"due": "2015-06-06"}, comment="This whole game needs to be written")
class Game:
    def __init__(self):
        pass

    @DATA(custom_fields={"due": "2015-06-06"}, comment="Implement game loop")
    def game_loop(self):
        pass


if __name__ == "__main__":
    finished_feature()
    unfinished_feature()
