from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTagSchema


class CHAT(DATA):
    pass


ChatSchema: DataTagSchema = {
    "name": "CHAT",
    "matching_tags": ["CHAT", "DISCUSSION", "QUESTION", "ANSWER", "POST", "COMMENT"],
    "default_fields": {"str": "op", "date": "posting_date"},
    "data_fields": {
        "id": "id",
        "post": "post",
        "comment": "comment",
        "question": "question",
        "answer": "answer",
        "replyto": "replyto",
    },
    "data_field_aliases": {"i": "id", "p": "post", "c": "comment", "q": "question", "a": "answer", "r": "replyto"},
}
