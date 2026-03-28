# CityScout - 현실 도시 환경 분석 에이전트

CityScout은 현실 세계의 지형 데이터를 3D로 시각화하고, 보행로 접근성과 일조권을 빠르게 점검할 수 있는 데모 앱입니다.

## 주요 기능(MVP)

- 지형 데이터 업로드 UI(샘플/Mock)
- 변환 진행 UI(샘플/Mock)
- 대시보드(Three.js 기반 3D 뷰어 포함)
- Mock API(Express)

## 실행 방법

### 1) 의존성 설치

```bash
npm install
```

Windows PowerShell에서 `npm` 실행이 차단되면(Execution Policy 오류), 현재 터미널 세션에서만 허용 후 다시 실행합니다:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### 2) 개발 서버 실행

```bash
npm run dev
```

- 프론트: `http://localhost:5173/`
- 백엔드(API): `http://localhost:3001/`

## 기술 스택

- Frontend: React, Tailwind CSS, Vite
- 3D: Three.js, @react-three/fiber, @react-three/drei
- Backend: Express

## 참고 문서

- PRD: `.trae/documents/city-environment-analysis-prd.md`
- Tech: `.trae/documents/city-environment-analysis-tech.md`
