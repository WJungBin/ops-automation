# Kafka Lag 기반 ASG 스케일링 Lambda 함수

## 개요
이 Lambda 함수는 Kafka 소비 지연(Lag)을 모니터링하여, Lag 상태에 따라 AWS Auto Scaling Group(ASG)의 인스턴스 수를 자동으로 조절합니다.  
Karpenter 의 Spot 인스턴스를 사용할 경우, 인스턴스 가용 불가능 등의 상황에서 ASG로 의 빠른 전환을 하여 LAG 해소를 목적으로 합니다.  
Lag이 매우 높으면 ASG 인스턴스를 늘리고, Lag이 해소되면 ASG 인스턴스를 줄여 Karpenter와 같은 자동 스케일링 솔루션으로 전환합니다.

주기적으로 EventBridge를 통해 호출되어 Kafka Lag 상태를 점검하고, 적절히 ASG 용량을 조절합니다.

---

## 주요 기능

- Prometheus API로 Kafka Lag 조회 (HTTP GET 요청)
- ASG 인스턴스 수 조회 및 조절 (boto3 사용)
- Lag 상태에 따른 ASG 스케일 아웃/스케일 인 실행
- Slack 또는 지정한 Webhook으로 상태 알림 전송
- 다양한 Lag 기준에 따라 세밀한 스케일링 정책 적용

---

## 환경 설정

### 사전 준비

- AWS Lambda 실행 역할에 `autoscaling:DescribeAutoScalingGroups`, `autoscaling:UpdateAutoScalingGroup`, `autoscaling:SetDesiredCapacity` 권한 부여
- Prometheus HTTP API 엔드포인트 접근 가능해야 함
- Webhook URL (예: Slack, MS Teams 등) 준비

### Lambda 환경 변수

- `PROMETHEUS_ENDPOINT` : Prometheus API URL
- `PROMETHEUS_QUERY` : Lag 조회 Prometheus 쿼리 (예: `sum(kafka_consumergroup_lag{topic=~"Kafka_Topic"}) by (consumergroup, topic)`)
- `ASG_NAME` : 조절 대상 ASG 이름
- `WEBHOOK_URL` : 알림 전송용 Webhook URL

---

## EventBridge Rule 설정 예시

EventBridge에서 주기적으로 (예: 5분 간격) Lambda 함수를 호출하도록 Rule을 생성합니다.

```json
{
  "source": ["aws.events"],
  "detail-type": ["Scheduled Event"],
  "detail": {}
}
```
---

## 스케줄 예시 (cron)

`rate(5 minutes)`

Lambda 대상 지정 후, Lambda 함수가 실행되며 Kafka Lag 상태를 점검하고 ASG 스케일링 정책에 따라 동작합니다.

---

## 사용 방법

1. AWS Lambda 콘솔 또는 CLI를 통해 본 코드를 배포  
2. 환경 변수 설정  
3. EventBridge Rule 생성하여 주기 호출 설정  
4. 로그(CloudWatch Logs) 및 Webhook 메시지로 상태 확인  

---

## 주요 코드 설명

- **check_lag 클래스**  
  Prometheus API에 GET 요청을 보내 Kafka Lag 정보를 조회  

- **asg_check 클래스**  
  ASG 현재 용량 정보 조회  

- **asg_instance_capacity_modify 클래스**  
  ASG의 MinSize 및 DesiredCapacity를 수정하여 스케일링 수행  

- **webhook 클래스**  
  Slack 등 Webhook으로 상태 메시지 전송  

- **lambda_handler 함수**  
  위 클래스들을 조합하여 Lag 상태에 따른 스케일링 로직 수행  

---

## 스케일링 로직 간략 설명

| Lag 상태                 | 현재 ASG 인스턴스 수    | 동작                              |
|-------------------------|---------------------|----------------------------------|
| Lag > 10,000,000        | 0                   | ASG 인스턴스 4대로 스케일 아웃         |
| Lag 100,000 ~ 10,000,000| 1 ~ 3               | ASG 인스턴스 4대로 조정              |
| Lag > 10,000,000        | 4 이상               | 유지 (더 이상 스케일 아웃 하지 않음)     |
| Lag < 100,000           | 4 이상               | ASG 인스턴스 0으로 스케일 인 (카펜터 전환)|
| Lag < 100,000           | 0                   | 유지                              |
| 기타                     | -                   | 로그 기록 및 패스                    |

---

## 로깅 및 모니터링

- CloudWatch Logs에 Lambda 실행 로그가 기록됩니다.  
- Webhook을 통해 ASG 스케일링 상태 알림을 받습니다.  

---

## 참고 사항

- Prometheus API URL 및 쿼리는 환경에 맞게 수정하세요.  
- ASG 이름, Webhook URL도 실제 사용 환경에 맞게 변경하세요.  
- boto3 클라이언트는 기본 AWS Lambda 역할 권한으로 동작합니다. 필요한 IAM 권한 부여를 반드시 확인하세요.

---

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
