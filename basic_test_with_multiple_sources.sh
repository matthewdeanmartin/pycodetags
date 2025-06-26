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
export PYCODETAGS_NO_OPEN_BROWSER=1
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests
echo "-------------------------------------"
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests --format text
echo "-------------------------------------"
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests --format html
echo "-------------------------------------"
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests --format json
echo "-------------------------------------"
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests --format keep-a-changelog
echo "-------------------------------------"
uv run pycodetags report --module demo.__main__ --module pycodetags --src demo --src tests --format todo.md
