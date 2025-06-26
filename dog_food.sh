# Using code tags to manage code tag's workflow
set -e

code_tags --module code_tags --src code_tags --format html

code_tags --module code_tags.own_todos --src code_tags
echo "-------------------------------------"
code_tags --module code_tags.own_todos --src code_tags --format text>docs/todo.txt
echo "-------------------------------------"
code_tags --module code_tags.own_todos --src code_tags --format html
echo "-------------------------------------"
code_tags --module code_tags.own_todos --src code_tags --format json>todo.json
echo "-------------------------------------"
code_tags --module code_tags.own_todos --src code_tags --format keep-a-changelog>CHANGELOG.md
echo "-------------------------------------"
code_tags --module code_tags.own_todos --src code_tags --format todo.md>docs/todo.md
