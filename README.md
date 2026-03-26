# AI Investment Agent Web

투자 조건을 입력받아 종목 후보를 평가하고, 웹 대시보드와 자동 매매용 JSON 시그널을 생성하는 Flask 기반 시스템입니다.

## Install

```powershell
python -m pip install -r requirements.txt
```

## Run Web

```powershell
python app.py
```

브라우저에서 `http://127.0.0.1:5000`에 접속합니다.

## API

`POST /api/analyze`

예시 JSON:

```json
{
  "asset": 10000000,
  "propensity": "중립형",
  "market": "국내",
  "duration": "중기",
  "data_source": "yfinance"
}
```

## Current State

- 기본 데이터 소스는 `yfinance`입니다.
- `yfinance` 초기화 또는 호출 실패 시 `MockMarketDataProvider`로 fallback 할 수 있습니다.
- Yahoo Finance 응답 특성상 일부 기본적 지표는 비어 있을 수 있습니다.

## Files

- `app.py`: Flask 웹 서버 및 API 엔드포인트
- `main.py`: CLI 진입점
- `templates/index.html`: 웹 UI 템플릿
- `static/styles.css`: 스타일시트
- `ai_invest_agent/models.py`: 요청/지표/추천 데이터 모델
- `ai_invest_agent/providers.py`: 시장 데이터 공급자 인터페이스 및 mock 구현
- `ai_invest_agent/providers.py`: 시장 데이터 공급자 인터페이스, Yahoo Finance 구현, mock fallback
- `ai_invest_agent/analysis.py`: 점수화, 진입가/목표가/손절가, 시그널 생성
- `ai_invest_agent/reporting.py`: 웹/CLI 공용 결과 컨텍스트 및 Markdown 렌더링

## Next Integration

실데이터 연동 시 `ai_invest_agent/providers.py`에 새 공급자를 추가하면 됩니다.

- 한국투자증권 API, Alpaca, Polygon, Finnhub 등에서 시세/재무/뉴스 수집
- `MarketDataProvider.list_candidates()`가 `SecuritySnapshot` 목록을 반환하도록 구현
- PDF 생성기는 `build_report_context()` 또는 Markdown 출력 결과를 후처리해 연결
