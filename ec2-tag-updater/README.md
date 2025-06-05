# EC2 Tag Updater

이 스크립트는 **AWS EC2 인스턴스의 Name 태그**로 인스턴스를 조회하고, 해당 인스턴스들에 새로운 태그를 일괄로 생성하거나 수정하는 자동화 도구입니다.

---

## 🛠 사용 방법

### 1. 실행 권한 부여

```bash
chmod +x ec2-tag-updater.sh
```

### 2. 스크립트 실행

```bash
./ec2-tag-updater.sh
```

### 3. 실행 흐름 예시

```
Enter The Instance Name.. : my-instance-name
i-0123456789abcdef0 i-0fedcba9876543210
Total Instance Count : 2

1) Change TAG Value.. 2) Exit..
1
Please Input TAG Key..
Environment
Please Input Tag Value..
Production
Tag Change Done!
Exit Script..
```

---

## ✅ 전제 조건

- AWS CLI가 설치 및 설정되어 있어야 합니다 (`aws configure`)
- EC2 인스턴스에 대한 `describe-instances`, `create-tags` 권한이 필요합니다
- `bash` 쉘 환경에서 실행되어야 합니다

---

## 🧪 예시 사용 시나리오

- `Name=web-server` 태그를 가진 모든 인스턴스의 `Environment` 태그를 `staging`으로 설정하고자 할 때:

```
Enter The Instance Name.. : web-server
1) Change TAG Value.. 2) Exit.. : 1
Please Input TAG Key.. : Environment
Please Input Tag Value.. : staging
```

---

## ⚠️ 주의 사항

- **정확한 인스턴스 Name 태그 값을 입력**해야 조회됩니다
- 동일한 이름을 가진 다수 인스턴스가 있을 경우 모두 적용됩니다
- 입력값 오류로 잘못된 태그가 설정될 수 있으니 주의해주세요

---

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
