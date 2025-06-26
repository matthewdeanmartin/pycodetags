#❯ pycodetags --help
#usage: pycodetags [-h] {report,plugin-info,jira-sync} ...
#
#TODOs in source code as a first class construct (v0.1.0)
#
#positional arguments:
#  {report,plugin-info,jira-sync}
#                        Available commands
#    report              Generate code tag reports
#    plugin-info         Display information about loaded plugins
#    jira-sync           Synchronize TODOs with Jira
#
#options:
#  -h, --help            show this help message and exit
set -e
if [[ -z "$CI" ]]; then
  export PYCODETAGS_NO_OPEN_BROWSER=1
  uv run pycodetags report --module demo.__main__ --src demo --verbose --bug-trail
  echo "-------------------------------------"
  uv run pycodetags report --module demo.__main__ --src demo --format text --verbose --bug-trail
  echo "-------------------------------------"
  uv run pycodetags report --module demo.__main__ --src demo --format html --verbose --bug-trail
  echo "-------------------------------------"
  uv run pycodetags report --module demo.__main__ --src demo --format json --verbose --bug-trail
  echo "-------------------------------------"
  uv run pycodetags report --module demo.__main__ --src demo --format keep-a-changelog --verbose --bug-trail
  echo "-------------------------------------"
  uv run pycodetags report --module demo.__main__ --src demo --format todo.md --verbose --bug-trail
fi
