if [[ -f "db.sqlite3" ]]; then
  rm db.sqlite3
fi
if [[ "$1" = "full" ]]; then
  rm ottm/migrations/0*.py
  python3 manage.py makemigrations
fi
python3 manage.py migrate
python3 manage.py initdb
