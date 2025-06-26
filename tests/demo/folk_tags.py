# TODO: Write this game!
def game():
    pass


# HACK: Why is this necessary? Remove extra syntax.
def _print(x):
    # pylint: disable=unnecessary-lambda
    (lambda x: print(x))(x)


# TODO(matth): Implement payment system
def payment():
    pass


# TODO(matth,alice,bob,carl): Implement payment system
def team_payment():
    pass


# TODO(TICKET123): Implement debit system
def debit():
    pass


# TODO(Jack): jira.example.com/ticker-123 Implement credit system
def credit():
    pass


# TODO(field=1, field2=value): Implement debit system
def super_debit():
    pass


if __name__ == "__main__":
    import pycodetags.folk_code_tags as folk

    for tag in folk.find_source_tags(__file__):
        print(tag)
