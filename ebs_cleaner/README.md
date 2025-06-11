# EBS Cleaner Lambda

이 Lambda 함수는 AWS EC2에서 **3일 이상 사용되지 않은 EBS 볼륨**을 확인하고, 
**14일 이상 미사용된 볼륨은 삭제**하며, 해당 결과를 Webhook을 통해 알림으로 전송합니다.

## 주요 기능

- 상태가 `available`이고, 인스턴스에 연결되지 않은 EBS를 필터링
- 태그에 `Keep: true`가 없는 경우만 대상
- 3일 이상 미사용된 EBS: 삭제 예정 알림(Webhook)
- 14일 이상 미사용된 EBS: 삭제 수행 및 알림(Webhook)

## 사용 기술

- AWS Lambda (Python)
- Amazon EC2 API (boto3)
- EventBridge (스케줄 기반 트리거)
- Webhook 알림 (예: Slack, Jandi 등)

## 디렉터리 구조

```
ebs-cleaner/
├── lambda_function.py  # 메인 Lambda 코드
├── README.md           # 설명 문서
```

## 환경 변수 및 설정

- `Webhook URL`: 알림을 보낼 웹훅 주소
- `Region`: 사용할 AWS 리전

## 설정 방법

1. Lambda에 `boto3`, `requests` 라이브러리 포함 (또는 Lambda 레이어 사용)
2. IAM Role에 EC2 볼륨 조회/삭제 권한 부여
   - `ec2:DescribeVolumes`
   - `ec2:DeleteVolume`
3. EventBridge에서 스케줄 생성
   - 예: 매일 오전 9시 UTC

## 예시 스케줄 (EventBridge)

```json
{
  "source": ["aws.events"],
  "detail-type": ["Scheduled Event"]
}
```

## 주의 사항

- `SnapshotId`가 존재하는 경우 삭제 대상에서 제외됩니다.
- `Keep: true` 태그가 있을 경우 삭제되지 않습니다.
- `logger` 모듈을 사용한 디버깅 로그가 포함되어 있습니다.
