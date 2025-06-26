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
# Don't export reports to same folder where you search for code tags!
pycodetags report --module demo.__main__ --src demo>demo_reports/default.txt
echo "-------------------------------------"
pycodetags report --module demo.__main__ --src demo --format text>demo_reports/todo.txt
echo "-------------------------------------"
pycodetags report  --module demo.__main__ --src demo --format html
echo "-------------------------------------"
pycodetags report  --module demo.__main__ --src demo --format json>demo_reports/todo.json
echo "-------------------------------------"
pycodetags report  --module demo.__main__ --src demo --format keep-a-changelog>demo_reports/CHANGELOG.md
echo "-------------------------------------"
pycodetags report  --module demo.__main__ --src demo --format todo.md>demo_reports/todo.md
