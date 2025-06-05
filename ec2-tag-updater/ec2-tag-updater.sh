#!/bin/bash

echo "Enter The Instance Name.. : "
read NAME

# 인스턴스 이름을 입력받아 aws 명령어로 인스턴스 ID 출력 후 출력값 정제 및 배열 저장
INSTANCEID=(`aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME" --query 'Reservations[*].Instances[].InstanceId[]' | sort -u | cut -d "'" -f 1 | cut -c 5- | sed 's/,/ /g' | tr -d ' ' | sed '/^$/d' | sed 's/"//g'`)

# 배열 값 및 배열 길이 출력
echo ${INSTANCEID[@]}
echo "Total Instance Count : ${#INSTANCEID[@]}"
echo -e "\n"

# 조회되는 Instance ID 가 없을 경우 스크립트 종료
if [ ${#INSTANCEID[@]} -eq 0 ]; then
        echo -e "Invaild Instance NAME!\n"
        echo "exit Script.."
        exit 0
else

# 입력값 받아 각각 번호에 맞는 명령 실행 (1번 태그 변경, 2번 스크립트 종료)
echo "1) Change TAG Value.. 2) Exit.."
read number
case $number in
        1)
                echo "Please Input TAG Key.."
                read tagkey  # 태그 키 입력
                echo "Please Input Tag Value.."
                read tagvalue # 태그 값 입력

                # 위의 인스턴스 ID 배열로 반복문 진행
                for tagchange in "${INSTANCEID[@]}" ; do
                # 인스턴스 ID 마다 위에 입력받은 태그 키 / 태그 값으로 aws tag 변경/생성 명령어 진행
                aws ec2 create-tags --resources $tagchange --tags Key=$tagkey,Value=$tagvalue
                done
                echo "Tag Change Done!"
                echo "Exit Script.."
        ;;
        2)
                echo "Exiting Script.."
                exit 0

        ;;
        *)
                echo "Invaild Option.. Script Exit.."
        ;;
esac
exit 0
fi
