# 📦 AMI 생성 및 정리 자동화 시스템

이 프로젝트는 **AWS Lambda**, **Step Functions**, 그리고 **API Gateway**를 조합하여 다음과 같은 기능을 제공합니다:

1. **API Gateway POST 요청**으로 AMI 생성 시작  
2. EC2 인스턴스로부터 **AMI 자동 생성**
3. 생성된 AMI가 정상 상태(`available`)가 될 때까지 상태 감지  
4. 완료 시 **웹훅으로 알림 전송**  
5. **특정 태그가 붙은 14일 이상 경과된 AMI 및 관련 스냅샷을 자동으로 정리 및 삭제 내역 웹훅으로 알림 전송**

## 📁 구성 파일

```
.
├── ami_creator_and_cleaner.py   # AMI 생성 및 정리 Lambda
├── ami_notifier.py              # AMI 상태 확인 및 웹훅 전송 Lambda
└── step_functions.json          # Step Functions 정의
```

## 🔧 기능 설명

## ✅ AMI 생성 Lambda (`ami_creator_and_cleaner.py`)

- 지정된 인스턴스 이름(`Name` 태그 기준)의 EC2 인스턴스 중 **가장 오래된 실행 중 인스턴스**를 선택하여 AMI 생성
- AMI 이름 형식:
  ```
  {INSTANCE_NAME}-Deploy-YYYY-MM-DD_HH_MM
  ```
- 생성된 AMI에 태그 추가:
  - `Name`: AMI 이름
  - `Reason`: `Deploy`  
  
- **AMI 생성 이후 자동으로 다음 실행됨**:
  - Step Functions 실행 → 상태 확인
  - 동일 인스턴스의 **14일 이상 경과된 AMI 및 관련 스냅샷 자동 삭제** (`Reason` : `Deploy` 태그가 붙어있는 경우)


### 🌐 AMI 생성 API

AMI 생성을 시작하려면 **API Gateway** 엔드포인트에 **POST 요청**을 보내세요.

### 예시

**HTTP POST**  
`https://{your-api-gateway-id}.execute-api.{region}.amazonaws.com/prod/create-ami`

**요청 본문**:

```json
{
  "instance_name_list": ["service-api", "service-worker"]
}
```

- 여러 인스턴스 이름을 배열로 보내면 각각에 대해 병렬로 AMI가 생성됩니다.

> API Gateway는 `ami_creator_and_cleaner.py`를 연결해야 합니다.
    
### 🧹 AMI 및 스냅샷 자동 정리

- `Reason=Deploy` 태그가 있는 AMI 중 **14일 이상 경과한 항목 자동 삭제**
- AMI 생성 요청 후 **자동으로 정리 수행**:
  - 해당 AMI 및 스냅샷까지 제거
  - 웹훅 알림 전송

> 수동 개입 없이 **생성 + 감시 + 정리**가 자동화됩니다.

### 🔐 IAM 정책 예시

```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeInstances",
    "ec2:CreateImage",
    "ec2:DeregisterImage",
    "ec2:DescribeImages",
    "ec2:DescribeSnapshots",
    "ec2:DeleteSnapshot",
    "states:StartExecution"
  ],
  "Resource": "*"
}
```

---
## ✅ AMI 상태 체크 및 웹훅 발송 Lambda (ami_notifier.py)

- AMI 상태가 `available`일 경우, 웹훅으로 알림 전송

```json
{
  "body": "AMI Is Available.",
  "connectColor": "#28a745",
  "connectInfo": [
    {
      "title": "Complete AMI Create. AMI State Available.",
      "description": "AMI ID: ami-xxxxxxxx, Name: my-app-Deploy-2025-06-05_12_00"
    }
  ]
}
```
### 🔐 IAM 정책 예시
```json
{
    "Effect": "Allow",
    "Action": [
        "ec2:DescribeImages"
    ],
    "Resource": "*"
}
```


---
## 🔄 AMI 상태 확인 및 알람 웹훅 발송

### Step Functions (`step_functions.json`)

### 📊 Step Functions 구조 예시

- **Map 상태**를 사용하여 모든 AMI ID를 병렬로 처리
- 각 AMI에 대해:
  1. 최초 60초 대기 후 `ami_notifier` 람다 호출
  2. `ami_notifier` 람다의 AMI 조회 결과를 통해 상태가 `available`이면 종료, 아니면 다시 60초 대기
  3. 대기 후 `ami_notifier` Lambda 재 호출 → 상태 확인 반복

```json
{
  "StartAt": "MapAMIList",
  "States": {
    "MapAMIList": {
      "Type": "Map",
      "ItemsPath": "$.ami_ids",
      "Parameters": {
        "ami_id.$": "$$.Map.Item.Value"
      },
      "Iterator": {
        "StartAt": "Wait60Seconds",
        "States": {
          "Wait60Seconds": {
            "Type": "Wait",
            "Seconds": 60,
            "Next": "CheckAmiState"
          },
          "CheckAmiState": {
            "Type": "Task",
            "Resource": "ami_notifier Lambda ARN",
            "Next": "AMIReady?"
          },
          "AMIReady?": {
            "Type": "Choice",
            "Choices": [
              {
                "Variable": "$.ami_state",
                "StringEquals": "available",
                "Next": "Success"
              }
            ],
            "Default": "Wait60Seconds"
          },
          "Success": {
            "Type": "Succeed"
          }
        }
      },
      "Next": "AllDone"
    },
    "AllDone": {
      "Type": "Succeed"
    }
  }
}
```



## 🏷️ AMI 예시 태그

```json
[
  { "Key": "Name", "Value": "service-api-Deploy-2025-06-05_16_30" },
  { "Key": "Reason", "Value": "Deploy" }
]
```

## 🛠️ 환경 요구 사항

- Python 3.9+
- boto3
- requests
- AWS Lambda
- AWS API Gateway
- AWS Step Functions

## 📌 참고 사항

- `requests`는 Lambda 패키징 시 함께 번들링 필요
- Step Functions 실행 시 CloudWatch 로그 권장

---

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
