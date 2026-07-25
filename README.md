# ctftime-discord-webhook

CTFtime에 새로 등록된 CTF 일정을 Discord 웹훅으로 알려줍니다.  
상시 서버 없이 **GitHub Actions**가 1시간마다 실행합니다.

메시지 형식은 기존 Zapier 알림과 같습니다.

```
`New CTF Time!`
| CTF Title : ImaginaryCTF 2025
|
| Start Time : Jul 26, 2025 04:00AM
| End Time : Jul 28, 2025 04:00AM
|
| CTF URL : https://ctftime.org/event/...
------------------------------------
```

## 서버가 필요한가?

**아닙니다.** Discord Incoming Webhook은 URL에 HTTP POST만 하면 됩니다.  
이 프로젝트는 GitHub Actions가 주기적으로 CTFtime API를 조회한 뒤 웹훅으로 전송합니다.

## 설정 방법

### 1. Discord 웹훅 만들기

1. Discord 서버 → 알림을 받을 채널
2. 채널 설정 → **연동** → **웹후크** → **새 웹후크**
3. 이름 예: `CTF Time Manager`
4. **웹후크 URL 복사**

### 2. GitHub 저장소 준비

이 프로젝트를 GitHub에 푸시한 뒤:

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: 복사한 웹훅 URL

### 3. 첫 실행 (기존 일정 스팸 방지)

Actions 탭 → **CTFtime Discord Notify** → **Run workflow**

- `bootstrap` = **true** 로 실행  
  → 현재 등록된 일정은 기록만 하고 메시지는 보내지 않습니다.
- 이후부터는 새로 등록된 일정만 알림이 갑니다.

원하면 `bootstrap=false`로 한 번 실행해 테스트 메시지를 보낼 수도 있습니다.

### 4. 자동 실행

- 매시 정각(UTC) cron으로 자동 실행됩니다.
- GitHub scheduled workflow는 수 분 지연될 수 있습니다.

## 로컬 테스트

```bash
# PowerShell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
$env:TIMEZONE="Asia/Seoul"
$env:BOOTSTRAP="true"
python notify.py
```

## 동작 방식

1. CTFtime API에서 앞으로 90일 이내 일정 조회
2. `data/seen_events.json`에 없는 새 일정만 Discord로 전송
3. 전송한 ID를 파일에 저장하고 Actions가 커밋/푸시

## 환경 변수

| 이름 | 설명 | 기본값 |
|------|------|--------|
| `DISCORD_WEBHOOK_URL` | Discord 웹훅 URL (필수) | — |
| `TIMEZONE` | 시작/종료 시각 표시 타임존 | `Asia/Seoul` |
| `LOOKAHEAD_DAYS` | 조회할 미래 일수 | `90` |
| `BOOTSTRAP` | `true`면 첫 기록만 하고 전송 안 함 | `false` |
