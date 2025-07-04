# FAQ

## Why introduce the concept of Data Tags?

I am hoping someone will use this library. The PEP-350 standard is very domain specific. The underlying idea-- data in
source code-- is not domain specific. So domain specific issues can be pushed to plugins and developers do not
need to reject the library on account of the implied workflow not matching their own.

## Why does this support so many schemas (folk, data, issue tracker, discussion,...)?

The most likely users are people with `# TODO:` comments in their code base and they shouldn't need to rewrite to get
started.

## Why PEP-330 if it was rejected?

I haven't found any other attempts to write standard's specification. The spec wasn't bad, it just wasn't something
that made sense to have the python central body promulgate.

## I don't want these to clutter my code. What can I do?

Put the comments in a separate submodule or separate file. You lose code adjacency though. Eventually there will
be a plugin or feature to surgically remove code tags that meet certain criteria.

## Why not plain text?

It is plain text in the sense of being a utf-8 file. It is structured, so it can be validated or take actions
when the code is run.

## What are actions?

When a due date is passed, the strongly typed code TODO can log, warn, or stop the program.

## Is there a workflow that supports removing he TODOs at some point?

Yes, you can accumulate TODOs and periodically remove them all, export them to an issue tracker then remove them. Right
not it is not implemented in the base library but could be implemented by a 3rd party plugin.

## Why aren't all PEP-350 tags supported?

The core library should do one thing well, which is serialize and deserialize a data structure similar to code tags.
This concept is called data tags.

For domain specific things, like tracking work items, there is a plugin. Discussion, documentation and code review are
different
problems and should be different libraries/applications to support them, hence the support for plugins.

Now, regarding specific tags mentioned in the PEP. Obscure names are those that need something more than an English
dictionary to interpret. If you need a specific organization's acronym dictionary to interpret, it is obscure and not
general. Obscure names might be supportable through localization mechanisms.

The issue tracking library won't implement:

- **Mutable tags**: DONE, NOBUG, WONTFIX are mutable tags and change from BUG to NOBUG. They change over the lifecycle
  of a tag, hurting the ability to do identity check
- **Abbreviations**: Users can implement their own synonyms via a localization, config
- **Obscure**: XXX, RFE, FEETCH, NYI, FR, FTRQ, FTR, let users implement via config
- **Invalid python identifier**: ???, !!!. Maybe.

Other plugins will implement

- **Discussion**: ???, QUESTION. Support via plugin
- **Documentation**: CAVEAT, NOTE, HELP, FAQ, GLOSS, SEE, CRED(IT), STAT(US). Support via plugin.
- **Code Review**: RVD/REVIEWED. Support via plugin.

## Anything else from PEP350 that didn't make the cut?

- **Idiosyncratic dates**: YYYY-\[[MM]-DD\]. Maybe via plugin.

## Should I remove my tags?

If you deploy your application to your own server no external team will import or read your code.

If you are distributing a library, you might want to remove code tags on release to declutter and keep TODO objects out
of the object graph.

## Code tas or codetags?

It is two words, so "code tags"
