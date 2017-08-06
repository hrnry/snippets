#!/bin/bash

#set -eu -o pipefail

DEBUG=0


function usage(){
  cat << _EOT_
Usage:
  ${0##*/} [option] <URL> <dst-dir>

Description:
  Download images
  http://estar.jp/_comic_view?w=01234567
  http://viewer.tonarinoyj.jp/series/FlR8CfEXXXX/FlR8CfEZZZZ
  https://togetter.com/li/0123456
  https://www.slideshare.net/user-name/slide-name

Options:
  -v    verbose  set -x ${0}
  -h    help

_EOT_
}

while getopts "pvh" OPT; do
  case ${OPT} in
    v)  DEBUG=1; set -x;;
    h)  usage; exit 0;;
  esac
done
shift $((OPTIND - 1))


TARGET_URL="${1}"

if [ $# -eq 1 ]; then
  DST_DIR="."
elif [ $# -eq 2 ]; then
  DST_DIR=$(sed -e 's/\/$//' <<< "${2}")
else
  usage
  exit 1
fi


function debug(){ ((DEBUG)) && echo ">>> $*"; }

function init(){
  TMP_DIR="/tmp/${TARGET_NAME}"
  TARGET_HTML="${TMP_DIR}/${TARGET_NAME}"

  mkdir -p "${TMP_DIR}"
  echo "target: ${TARGET_URL}"
  curl --silent --show-error "${TARGET_URL}" -o "${TARGET_HTML}"
}

function archive(){
  echo "archive: ${DST_DIR}/${TARGET_TITLE}_${TARGET_NAME}.zip"
  zip -j -q "${DST_DIR}/${TARGET_TITLE}_${TARGET_NAME}.zip" ${TMP_DIR}/*
}

# http://estar.jp/_comic_view?w=...
function download_estar_images(){
  init
  local TARGET_TITLE=$(echo "$(grep 'og:title' ${TARGET_HTML} | cut -d '"' -f 4)-$(grep -oP -e '(?<=m-workData__title">).*(?=</h1>)' ${TARGET_HTML})" )
  echo "title: ${TARGET_TITLE}"
  local PAGES=$(grep -oP -e '[0-9]+(?=ページ)' ${TARGET_HTML})
  echo "pages: ${PAGES}"
  local W=$(grep 'id="work_id"' ${TARGET_HTML} | cut -d '"' -f 6)
  #local WS=$(grep 'id="workset_id"' ${TARGET_HTML} | cut -d '"' -f 6)
  local D=$(grep -oP -e '(?<=work_cover480.png\?d=)[0-9]*(?="/>)' ${TARGET_HTML})
  local REFERER="http://estar.jp/"
  local USER_AGENT="Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0"
  for (( N = 1; N <= ${PAGES}; N++ )); do
    echo -n "${N},"
    curl --silent --show-error --referer "${REFERER}" --user-agent "${USER_AGENT}" "http://estar.jp/_get_pro_comic_page_image?w=${W}&p=${N}&vt=2&mod_date=${D}" -o ${TMP_DIR}/${N}.jpg
  done
  archive
}

# https://www.slideshare.net/...
function download_slideshare_images(){
  init
  local TARGET_TITLE=$(grep -oP -e '(?<=<title>)[^<]*(?=</title>)' ${TARGET_HTML})
  echo "title: ${TARGET_TITLE}"
  local TARGET_FILES=( $(grep -oP -e '(?<=data-full=")https?://[^"]*(?=")' ${TARGET_HTML}) )
  echo "pages: ${#TARGET_FILES[@]}"
  for (( N = 0; N < ${#TARGET_FILES[@]}; N++ )); do
    echo -n "${N},"
    curl --silent --show-error "${TARGET_FILES[${N}]%\?cb=*}" -o ${TMP_DIR}/${N}.jpg
  done
  archive
}

# https://togetter.com/li/...
function download_togetter_images(){
  init
  local TARGET_TITLE=$(grep -oP -e '(?<=<title>)[^<]*(?=</title>)' ${TARGET_HTML})
  echo "title: ${TARGET_TITLE}"

  local REGEX='https://pbs.twimg.com/media/[^\.]*\.\(jpg\|png\):small'
  local TARGET_FILES=( $(grep -o -e "${REGEX}" ${TARGET_HTML} | sed 's/small$/orig/') )
  TARGET_FILES=("${TARGET_FILES[@]}" $(echo -e $(grep 'var moreTweetContent = "' ${TARGET_HTML}) | sed 's/\\\([\/\"]\)/\1/g' | grep -o -e "${REGEX}" | sed 's/small$/orig/') )

  echo "images: ${#TARGET_FILES[@]}"
  for (( N = 0; N < ${#TARGET_FILES[@]}; N++ )); do
    echo -n "${N},"
    local FILE_NAME=${TARGET_FILES[${N}]##*/}
    curl --silent --show-error "${TARGET_FILES[${N}]}" -o ${TMP_DIR}/${N}-${FILE_NAME%:orig}
  done
  archive

  local TARGET_NEXT=$(grep '<link rel="next" href="'"${TARGET_URL}"'?page=[2-9]"/>' ${TARGET_HTML} | cut -d '"' -f 4)
  if [ -n "${TARGET_NEXT}" ]; then
    echo "next: ${TARGET_NEXT}"
    download_togetter_images "${TARGET_NEXT}"
  fi
}

# http://viewer.tonarinoyj.jp/series/...
function download_tonarinoyj_images(){
  init
  local TARGET_TITLE=$(grep -oP -e '(?<=<title>)[^<]*(?=</title>)' ${TARGET_HTML})
  echo "title: ${TARGET_TITLE}"
  local TARGET_FILES=( $(grep -oP -e '(?<=js-page-image" src=")[^"]*(?="></p>)' ${TARGET_HTML}) )
  echo "pages: ${#TARGET_FILES[@]}"
  for (( N = 0; N < ${#TARGET_FILES[@]}; N++ )); do
    echo -n "${N},"
    curl --silent --show-error "${TARGET_FILES[${N}]}" -o ${TMP_DIR}/${N}-${TARGET_FILES[${N}]##*/}.jpg
  done
  archive
}


case "${TARGET_URL}" in
  http://estar.jp/_comic_view\?w=[0-9]*)
    TARGET_NAME="${TARGET_URL##*\?w=}"
    download_estar_images
    ;;
  https://togetter.com/li/[0-9]*)
    TARGET_NAME="${TARGET_URL##*/}"
    download_togetter_images
    ;;
  https://www.slideshare.net/?*/?*)
    TARGET_NAME="$(basename ${TARGET_URL})"
    download_slideshare_images
    ;;
  http://viewer.tonarinoyj.jp/series/?*/?*)
    TARGET_NAME="${TARGET_URL##*/}"
    download_tonarinoyj_images
    ;;
  *)
    echo "URL?"
    usage
    exit 1
    ;;
esac
