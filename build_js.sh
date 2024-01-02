python manage.py assemble_ts
npm run --prefix js dev
if [[ "$1" == "--clean" ]]
then
  python manage.py assemble_ts -p
fi
