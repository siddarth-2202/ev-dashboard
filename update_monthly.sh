#!/usr/bin/env bash
# Monthly update: download from Vahan -> build the CSV -> publish to GitHub.
# Run it from a Codespace with ONE command:   bash update_monthly.sh
# It stops at the first problem and tells you which step failed. Nothing is pushed unless every check passes.
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python || command -v python3)"
RAW=/tmp/raw
SCRAPER=/tmp/scraper
RTOS=("BENGALURU CENTRAL" "BENGALURU EAST" "BENGALURU NORTH" "BENGALURU SOUTH" "BENGALURU WEST"
      "CHANDAPURA" "ELECTRONIC CITY" "JNANABHARATHI" "KRISHNARAJAPURAM" "YALAHANKA"
      "DEVANAHALLI" "NELAMANGALA")

echo "== 1/6 Syncing with GitHub"
git pull --ff-only

echo "== 2/6 Getting the scraper"
rm -rf "$SCRAPER"
git clone --depth 1 https://github.com/RevTpark/vahan-scraper.git "$SCRAPER"
pip install -q -r "$SCRAPER/requirements.txt" pandas

echo "== 3/6 Downloading from Vahan (up to 3 attempts, 5 minutes apart)"
rm -rf "$RAW"
for attempt in 1 2 3; do
  # A retry only fetches the files that are still missing.
  if "$PY" "$SCRAPER/scripts/api.py" --yaxis "Fuel" --xaxis "Month Wise" --state "Karnataka" \
       --start-year 2021 --out "$RAW" --rto "${RTOS[@]}"; then
    break
  fi
  if [ "$attempt" -eq 3 ]; then
    echo "STOPPED at step 3: Vahan did not answer after 3 attempts. Nothing was changed. Try again later."
    exit 1
  fi
  echo "Attempt $attempt failed. Waiting 5 minutes..."
  sleep 300
done

echo "== 4/6 Building the CSV (stops if anything looks wrong)"
"$PY" build_csv.py "$RAW" --strict

echo "== 5/6 Checking the result"
ROWS=$(wc -l < data/ev_data.csv)
if [ "$ROWS" -ne 361 ]; then
  echo "STOPPED at step 5: expected 361 lines in data/ev_data.csv but found $ROWS. Nothing was pushed."
  exit 1
fi
if git diff --quiet -- data/ev_data.csv data/last_updated.txt; then
  echo "No changes since the last update. Nothing to push."
  exit 0
fi

echo "== 6/6 Publishing to GitHub"
git add data/ev_data.csv data/last_updated.txt
git commit -m "Update EV data $(date -u +%F)"
git push

echo
echo "UPDATE FINISHED. The dashboard refreshes in a few minutes. Check its 'Last updated' date."
