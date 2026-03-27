# AI Investment Agent Web

Flask 기반 투자 분석 앱입니다. 현재 상태에서 아래 기능이 연결돼 있습니다.

- 국내/미국 추천 분석
- PDF 리포트 자동 생성
- 모의매매 실행 payload 생성
- KIS Open API 연동 준비
- KIS 미설정 시 자동 mock fallback

## Install

```powershell
python -m pip install -r requirements.txt
```

## Optional Config

KIS 모의투자 또는 실전투자를 쓰려면 루트에 `.env` 파일을 만들고 [.env.example](/c:/Users/kyj31/Desktop/hacker/.env.example) 형식으로 값을 넣으면 됩니다.

필수 키:

- `KIS_PAPER_APP_KEY`
- `KIS_PAPER_APP_SECRET`
- `KIS_PAPER_ACCOUNT_NO`

선택 키:

- `KIS_PAPER_ACCOUNT_PRODUCT_CODE`
- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_ACCOUNT_NO`
- `KIS_ACCOUNT_PRODUCT_CODE`
- `KIS_USER_AGENT`

## Run

```powershell
python app.py
```

브라우저:

```text
http://127.0.0.1:5000
```

설정 상태 확인:

```text
GET /api/config-status
```

## API

### Analyze

`POST /api/analyze`

예시:

```json
{
  "asset": 10000000,
  "propensity": "중립형",
  "market": "국내",
  "duration": "중기",
  "data_source": "hybrid",
  "auto_execute": true,
  "execution_broker": "auto",
  "execution_env": "demo"
}
```

### Execute

`POST /api/execute`

예시:

```json
{
  "execution_broker": "auto",
  "execution_env": "demo",
  "signals": [
    {
      "symbol": "005930.KS",
      "action": "BUY",
      "quantity": 1,
      "entry_price": 70000,
      "reason": "test"
    }
  ]
}
```

## Data Sources

- `hybrid`: 기본값. yfinance 중심, 가능하면 defeatbeta 연구 보강
- `kis`: KIS 시세 사용 시도, 미설정이면 fallback
- `yfinance`: Yahoo Finance
- `defeatbeta`: 미국 리서치 보강
- `mock`: 로컬 mock 데이터

## Execution Brokers

- `auto`: KIS 설정이 있으면 KIS, 없으면 mock
- `kis`: KIS 강제 사용
- `mock`: 로컬 모의브로커

## Output

- PDF 리포트: `generated_reports/`
- mock 주문 ledger: `mock_trading/`
- KIS 주문 ledger: `kis_trading/`
