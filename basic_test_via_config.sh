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
# Don't export reports to same folder where you search for code tags!
export PYCODETAGS_NO_OPEN_BROWSER=1
formats=("text" "html" "json" "keep-a-changelog" "todo.md" "done")
labels=("text" "html" "json" "changelog" "todo.md" "done")

if [[ -z "$CI" ]]; then
  pycodetags report
  for i in "${!formats[@]}"; do
    echo "----------${labels[$i]}---------------------------"
    pycodetags data --format "${formats[$i]}"
  done
else
  pycodetags data --format text> pycodetags_report_default.txt
  for i in "${!formats[@]}"; do
    echo "----------${labels[$i]}---------------------------" >> pycodetags_report_all.txt
    pycodetags report --format "${formats[$i]}" >> pycodetags_report_all.txt
  done
fi