# Log Monitoring & Alert Script

이 스크립트는 지정한 로그 파일 내에서 특정 문자열(에러 메시지 등)을 주기적으로 감시하고, 해당 문자열이 감지되면 지정된 Webhook URL로 알림을 전송합니다.  
범용적인 용도로 사용 가능하도록 설계되었습니다.

## 🔧 사용법

### 1. 변수 설정

```bash
TARGET_MENT="Error Ment"     # 감지할 에러 메시지
LOGFILE="/경로/로그파일.log"   # 모니터링할 로그 파일 경로
SCRIPT_PATH="/스크립트경로"     # 임시 로그 파일 저장 경로
```

### 2. 스크립트 실행

```bash
chmod +x log_keyword_alert.sh
./log_keyword_alert.sh
```

### 3. 알림 전송 형식

오류가 감지되면 Webhook URL로 다음과 같은 JSON이 전송됩니다:

```json
{
  "body": "서버IP - 감지된에러 - ERROR detected, VALUES: 3",
  "connectColor": "#FF0000",
  "connectInfo": [
    {
      "title": "Please Server Check. 상태 확인 필요",
      "description": "Log PATH : /경로/로그파일.log"
    }
  ]
}
```

## ✅ 의존성

- `curl` 명령어
- `grep`, `wc`, `tail`, `hostname` 등의 표준 유닉스 명령어

## 🧪 테스트

스크립트는 59초간 로그를 감시하며, 에러가 감지되면 즉시 Webhook을 호출합니다.

## 📝 참고사항

- Webhook URL을 반드시 설정하세요.
- 너무 잦은 감시는 서버에 부하를 줄 수 있으므로 주기를 조정하거나 `cron`과 연계해 사용하세요.

## 📄 라이선스

이 스크립트는 MIT 라이선스를 따릅니다. 자유롭게 수정, 재배포할 수 있습니다.
