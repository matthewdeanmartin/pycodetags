# Plugin Design

## Core library
Responsible for 
- Iterating python files (raise event)
- Finding comments to parse data (raise event)
- Parsing to domain-free data format (TypeDict)
- Schema description
- Base class for strong type with events
- Validate (raise event)
- Default views for code tags as pure data (view events)

Core library has no domain specific things. Core library can use data structure that are python, e.g. strings, ints,
etc work the way they do in python.

## Apps
- Issue Tracker
- Discussion/Chat
- Code Review
- Documentation (Glossary, etc)
- Other apps that the community thinks up

## Low level events
- Validation
- Parse 
  - with new schemas 
  - for non-python
- Alternate parse for python

## Plugins for plugins
- Issue tracker 
  - could call validation & use issue tracker schema. 
  - reports that specifically use TODO schema
  - commands for done TODO, that remove DONE comments.
