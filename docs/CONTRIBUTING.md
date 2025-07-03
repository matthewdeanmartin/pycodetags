# Contributing

## General vs Idiosyncratic Features
The library and application should only implement rather general features, not things idiosyncratic to one person
or one team at one organization. 

Most large features should be implemented via plugins.

To handle idiosyncrasies without plugins

- Config via `[tools.code_tags]` section of `pyproject.toml`
- Env vars, optionally via `.env` file
- Custom fields, which all three schemas support

The following should be handled by plugins
- Source control
- File support

Either can't be handled or should be handled by synonyms in config
- Supporting standards other than PEP-350. I don't know of any other standards right now, but to support too many
 incompatible standards would pull the library in too many incompatible directions.

## Localization

Good, help wanted
- Translating into multiple languages
- Synonyms in config

Not Good
- Dates other than `YYYY-MM-DD`. Supporting all dates is hard, overexpands scope
- Idiosyncratic synonyms in source code


## Useful help for core library
- Finding bugs
- Logical inconsistencies in current design with current goals
- Improving the "accept anything, generate strict"

## How to make a plugin

TBD!



