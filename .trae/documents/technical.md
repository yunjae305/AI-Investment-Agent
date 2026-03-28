# 기술 사양서 - CityScout

## 1. 아키텍처
- **프론트엔드**: React, TypeScript, Vite, Tailwind CSS
- **백엔드**: Node.js, Express (Mock API)
- **3D 렌더링**: Three.js, @react-three/fiber, @react-three/drei
- **상태 관리**: Zustand

## 2. 데이터 흐름
1. 클라이언트에서 파일을 API 서버로 전송.
2. 서버는 가상의 Arnis 엔진을 통해 데이터 처리 (시뮬레이션).
3. 분석 완료 후 결과 데이터(JSON)와 3D 모델(GLB 또는 원시 데이터) 반환.
4. 클라이언트 대시보드에서 Three.js를 사용하여 렌더링.

## 3. UI/UX 디자인 가이드
- **컬러**: Zinc (기본), Emerald (포인트), Amber (일조권), Blue (변환 중).
- **컴포넌트**: Lucide-react 아이콘 사용, Radix UI 기반 모듈화.
- **레이아웃**: 반응형 디자인, 다크 모드 지원.