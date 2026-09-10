# pycodetags-chat

Discussion code-tag schema for pycodetags 0.8.x. Supports Python 3.9–3.15.

Install with `pip install pycodetags-chat`, then explicitly select the schema:

```toml
[tool.pycodetags]
schema = "discussion"
src = ["src"]
```

The discussion schema uses extended PEP-350 with first-line titles and subsequent body lines:

```python
# QUESTION: Why do we retry here?
# Is the upstream operation idempotent?
# <author=alice thread_id=uploads>
```

Recognized tags: QUESTION, ANSWER, CHAT, POST, COMMENT, DISCUSSION. Named fields include author,
date, tags, mastodon_id, in_reply_to, spoiler_text, thread_id, language, and idempotency_key.
This plugin supplies a schema; it does not implement Mastodon synchronization or a chat service.
Use the core load/dump and reporting APIs. TDG and PEP350 remain built-in core schema names.
