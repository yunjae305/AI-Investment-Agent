# AI Investment Agent Web

Flask 기반 투자 분석 애플리케이션입니다.  
현재 프로젝트는 단순 추천 엔진을 넘어, 멀티 에이전트 기반 투자 리포트 생성 파이프라인으로 구성되어 있습니다.

주요 기능:

- 국내/미국 종목 후보 분석
- 멀티 에이전트 기반 투자 리포트 생성
- 결론 우선형 PDF 리포트 다운로드
- EPS, PER, ROE, BPS, PBR 지표 비교 그래프 생성
- 모의매매 실행 payload 생성
- KIS Open API 연동 시세 사용 시도
- 외부 공급자 실패 시 mock fallback

## Install

```powershell
python -m pip install -r requirements.txt
```

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

## Input

핵심 입력값은 아래 4개입니다.

- `asset`: 투자 자산 규모
- `propensity`: 투자 성향 (`안정추구형`, `중립형`, `공격투자형`)
- `market`: 시장 (`국내`, `미국`)
- `duration`: 투자 기간 (`단기`, `중기`, `장기`)

예시:

```json
{
  "asset": 10000000,
  "propensity": "중립형",
  "market": "국내",
  "duration": "중기",
  "data_source": "hybrid",
  "auto_execute": false,
  "execution_broker": "auto",
  "execution_env": "demo"
}
```

## Output

분석 결과는 다음 형태로 생성됩니다.

- 웹 화면 결과
- 마크다운 리포트
- PDF 리포트
- 매매 실행 payload

생성 파일:

- PDF 리포트: `generated_reports/`
- mock 주문 ledger: `mock_trading/`
- KIS 주문 ledger: `kis_trading/`

## Multi-Agent Architecture

현재 멀티 에이전트 파이프라인은 [multi_agent.py](/c:/Users/kyj31/Desktop/hacker/ai_invest_agent/multi_agent.py) 중심으로 구성됩니다.

에이전트 구성:

1. `Persona Agent`
   - 입력: `InvestmentRequest`
   - 역할: 투자 성향, 시장, 기간, 자산 규모를 바탕으로 투자자 페르소나 생성

2. `Topic Selection Agent`
   - 입력: 페르소나 + 추천 후보 종목
   - 역할: 사용자 성향과 맞는 핵심 종목 선정

3. `Planning Agent`
   - 입력: 선정 종목
   - 역할: 종목별 조사 우선순위와 리서치 키워드 생성

4. `Research Agent`
   - 입력: 계획 + 종목 스냅샷 데이터
   - 역할: 사실 기반 리서치 포인트와 부정 플래그 정리

5. `Insight Agent`
   - 입력: 리서치 결과 + 페르소나
   - 역할: 투자자가 알아야 할 핵심 투자 앵글과 대응 시나리오 도출

6. `Writing Agent`
   - 입력: 인사이트 + 추천 정보
   - 역할: 최종 투자 전략 리포트 초안 생성

7. `Verification Agent`
   - 입력: 리포트 초안 + 원본 시세 데이터
   - 역할: 수치 불일치, 위험도 충돌, 추천 논리 검증

## Multi-Agent Flow

전체 플로우는 아래 순서로 동작합니다.

1. 사용자가 투자 조건 입력
2. `providers.py`에서 시장 데이터 수집
3. `analysis.py`에서 기본 추천 종목 계산
4. `Persona Agent`가 투자자 프로필 생성
5. `Topic Selection Agent`가 상위 종목 선정 근거 정리
6. `Planning Agent`가 종목별 조사 우선순위 작성
7. `Research Agent`가 사실 기반 데이터 정리
8. `Insight Agent`가 매수/리스크 관점 인사이트 생성
9. `Writing Agent`가 최종 리포트 초안 생성
10. `Verification Agent`가 리포트 수치 검증
11. `reporting.py`가 최종 마크다운/HTML/PDF 리포트 생성

요약 구조:

```text
InvestmentRequest
  -> MarketDataProvider
  -> Recommendation Engine
  -> Persona Agent
  -> Topic Selection Agent
  -> Planning Agent
  -> Research Agent
  -> Insight Agent
  -> Writing Agent
  -> Verification Agent
  -> Markdown / HTML / PDF Report
```

## Report Structure

최종 리포트는 결론 우선형으로 정렬됩니다.

1. `Final Conclusion`
   - 전체 전략 요약
   - 가장 먼저 봐야 할 최종 결론

2. `Recommended Actions`
   - 상위 종목의 진입가
   - 목표가
   - 손절가
   - 기대 수익률

3. `Why This Conclusion`
   - 투자자 페르소나
   - 시장 트렌드
   - 종목 선정 근거
   - 리서치 인사이트
   - 기업 분석
   - 재무지표 차트
   - 검증 결과

## Financial Analysis Included In Report

리포트에는 아래 항목이 포함됩니다.

- 기업 분석
  - 재무제표 분석
  - 경영진 평가
  - 경쟁사 비교
- 시장 트렌드 이해
  - 거시 경제 분석
  - 업종별 트렌드
- 재무지표 분석
  - `EPS`
  - `PER`
  - `ROE`
  - `BPS`
  - `PBR`

현재 그래프는 종목 간 비교형 막대 차트로 생성됩니다.

## Data Sources

- `hybrid`: 기본은 yfinance, 가능하면 defeatbeta 연구 데이터 보강
- `kis`: KIS Open API 시세 사용 시도, 실패 시 fallback
- `yfinance`: Yahoo Finance
- `defeatbeta`: 미국 리서치 보강
- `mock`: 개발용 mock 데이터

## Execution Brokers

- `auto`: KIS 설정이 있으면 KIS, 없으면 mock
- `kis`: KIS 강제 사용
- `mock`: 로컬 mock broker

## Environment Variables

기본 예시는 [.env.example](/c:/Users/kyj31/Desktop/hacker/.env.example)에 있습니다.

KIS 관련:

- `KIS_PAPER_APP_KEY`
- `KIS_PAPER_APP_SECRET`
- `KIS_PAPER_ACCOUNT_NO`
- `KIS_PAPER_ACCOUNT_PRODUCT_CODE`
- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_ACCOUNT_NO`
- `KIS_ACCOUNT_PRODUCT_CODE`
- `KIS_USER_AGENT`

PDF 관련:

- `PDF_EXPORT_PROVIDER`
- `CLOUDMERSIVE_API_KEY`

멀티 에이전트 모델 관련:

- `OPENAI_API_KEY`
- `AI_DEFAULT_MODEL`
- `AI_PERSONA_MODEL`
- `AI_TOPIC_SELECTION_MODEL`
- `AI_PLANNING_MODEL`
- `AI_RESEARCH_MODEL`
- `AI_INSIGHT_MODEL`
- `AI_WRITING_MODEL`
- `AI_VERIFICATION_MODEL`

기본 모델은 `gpt-4.1-mini` 입니다.

## LLM Behavior

- `OPENAI_API_KEY`가 설정되어 있으면 각 에이전트가 OpenAI Responses API를 사용합니다.
- 기본 모델은 `gpt-4.1-mini` 입니다.
- 각 단계는 개별 모델로 override 할 수 있습니다.
- API 키가 없거나 호출 실패 시 deterministic rule-based fallback으로 동작합니다.

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
  "auto_execute": false,
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

## Notes

- `Cloudmersive` 경로를 사용하면 HTML 기반 PDF 변환이 가능해서 그래프가 포함된 PDF 품질이 더 좋습니다.
- 로컬 fallback PDF는 텍스트 기반이라 그래프 표현에는 한계가 있습니다.
- 현재 일부 한글 문자열은 기존 코드 인코딩 문제의 영향을 일부 받을 수 있습니다. 필요하면 후속 작업으로 전역 정리 가능합니다.
