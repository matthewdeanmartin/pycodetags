Title: Pycodetags, track your issues in code comments.
Date: 2025-07-07
Modified: 2025-07-07
Category: Pycodetags Core
Tags: main
Slug: home-page
Authors: Matthew Dean Martin
Summary: Pycodetags is a python library to help you track your issues, bugs and todo list items in source control.

Core Features:

- Parse out folk tags, that roughly follow the `# TODO: text` pattern
- Parse PEP-350 style tags, that rough follow, `# TODO: text <default key=value>` pattern
- Plugin infrastructure to allow for domain specific plugins, e.g. `# TODO:` for issue tracking and `# CHAT:` for
  discussion
- Domain free "data" views
- Pyproject.toml driven config

Main Plugins

- Issue Tracker - mostly complete
- Github issue sync - WIP
- Discussion - WIP
- Universal (code tags for all languages)- WIP
- Sqlite Exporter - WIP