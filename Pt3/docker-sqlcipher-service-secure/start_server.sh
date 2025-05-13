./test_tdx_attest

curl -k -X POST https://localhost:8799/attestation/sgx/dcap/v1/report \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg quote "$(base64 -w 0 valid_quote.dat)" '{isvQuote: $quote}')" \
  -o response.json \
  -w "%{http_code}\n"


# Check the response
# inv_status=$(jq -r '.isvEnclaveQuoteStatus' response.json)
# if [ "$inv_status" != "OK" ]; then
#     echo "Quote verification failed: isvEnclaveQuoteStatus=$inv_status"
#     exit 1
# fi
TIME_ENDED=$(date +%s%3N)
echo "$TIME_ENDED" > /shared_timing/time_ended.txt
# start the program
DB_KEY=$(gcloud secrets versions access latest --secret="dbKey" --project="computernetworks-450617")
export DB_KEY
node dist/server.js