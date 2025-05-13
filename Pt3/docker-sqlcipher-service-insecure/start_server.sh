TIME_ENDED=$(date +%s%3N)
echo "$TIME_ENDED" > /shared_timing/time_ended.txt
# start the program
DB_KEY=$(gcloud secrets versions access latest --secret="dbKey" --project="computernetworks-450617")
export DB_KEY
node dist/server.js