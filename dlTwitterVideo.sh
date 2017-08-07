#!/bin/bash

#set -eu -o pipefail
set -u -o pipefail
set -x

function usage(){
  cat << _EOT_
Twitter video downloader

Usage: ${0##*/} STATUS_ID
       ${0##*/} https://twitter.com/i/videos/STATUS_ID
       ${0##*/} https://twitter.com/USER_NAME/status/STATUS_ID
_EOT_
}

if [ $# -ne 1 ]; then
  usage
  exit 1
fi

STATUS_ID=${1##*/}
expr 1 + "${STATUS_ID}" > /dev/null 2>&1
if [ $? -ge 2 ]; then
  echo "STATUS_ID ?"
  usage
  exit 1
fi

# twepoch: 1288834974657(2010/11/04 10:42:54)
# snowflake: (STATUS_ID >> 22) + twepoch
echo "STATUS_ID: ${STATUS_ID}"
date --date="@$(( ((STATUS_ID >> 22) + 1288834974657) / 1000 ))"

TMP_DIR="/tmp/${STATUS_ID}"
mkdir -p "${TMP_DIR}"

TMP_FILE="${TMP_DIR}/${STATUS_ID}"
curl -sS "https://twitter.com/i/videos/${STATUS_ID}" -o "${TMP_FILE}"

HTML=$(sed -e 's/&quot;/\n/g' -e 's/\\//g' "${TMP_FILE}" | grep -e '\.mp4' -e '\.m3u8')
MP4=$(grep -oP '(?<=https://video.twimg.com/tweet_video/)\w*(?=\.mp4)' <<< "${HTML}")
if [ -n "${MP4}" ]; then
  curl -sS "https://video.twimg.com/tweet_video/${MP4}.mp4" -o "${TMP_DIR}/${MP4}.mp4"
  echo "MP4: ${TMP_DIR}/${MP4}.mp4"
  exit 0
fi

curl -sS $(grep '\.m3u8$' <<< "${HTML}") -o "${TMP_FILE}"
curl -sS "https://video.twimg.com$(grep '\.m3u8$' ${TMP_FILE} | tail -1)" -o "${TMP_FILE}"

for TS in $(grep -v '^#' "${TMP_FILE}"); do
  curl -sS "https://video.twimg.com${TS}" -o "${TMP_DIR}/$(grep -oP '(?<=/vid/)[0-9]+(?=/)' <<< ${TS}).ts"
done
cat $(ls -v1 ${TMP_DIR}/*.ts) > "${TMP_DIR}/${STATUS_ID}.ts"
echo "TS: ${TMP_DIR}/${STATUS_ID}.ts"
exit 0
