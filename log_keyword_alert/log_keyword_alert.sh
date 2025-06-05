#!/bin/bash


#TARGET_MENT="Broker not available"
TARGET_MENT="Error Ment"   # 감지할 에러로그 변경 시 이부분 변수 내용 변경 
LOGFILE="Log Path"
SCRIPT_PATH=Script Path
IP=`hostname -I | awk '{print $1}'`

DATETIME=$(date -d '9 hour' +"%Y.%m.%d.%H:%M")

# Logging Start

tail -n0 -F $LOGFILE  > $SCRIPT_PATH/error_check.log &

CHECK_PID=$!

sleep 59

kill $CHECK_PID


ERROR_VALUE=`cat $SCRIPT_PATH/error_check.log | grep -a "$TARGET_MENT" | wc -l`
echo $ERROR_VALUE
if [ $ERROR_VALUE -gt 0 ]; then

echo true! over then 0!
echo $ERROR_VALUE

 curl https://Wehhook URL  \
 -H 'Content-Type: application/json' \
 --data-binary '{
    "body": "'"$IP"' - '"$TARGET_MENT"' -  ERROR detected, VALUES: '"$ERROR_VALUE"'",
        "connectColor" : "#FF0000",
            "connectInfo": [
                {
                "title": "Please Server Check. 상태 확인 필요",
                "description": "Log PATH : '"$LOGFILE"' "
        }]
}'

else

echo under then 0!
echo $ERROR_VALUE

fi