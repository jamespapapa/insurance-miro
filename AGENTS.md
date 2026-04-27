# Insurance Miro Project Memory

이 저장소는 MiroFish를 기반으로 삼성생명 보험상품 신상품 판매 시뮬레이션을 만들기 위한 개조 프로젝트다. 장기 방향은 앞단의 문서 입력, 온톨로지 생성, Zep GraphRAG 구축, Agent 페르소나 생성은 최대한 보존하고, 세계가 빌드된 뒤 실행되는 SNS/OASIS 기반 시뮬레이션과 결과 분석을 보험상품 판매 시뮬레이터로 바꾸는 것이다.

## Stable Truths

- 루트 프로젝트는 Node 스크립트로 프론트엔드와 백엔드를 함께 제어한다. 주요 명령은 `npm run setup:all`, `npm run dev`, `npm run backend`, `npm run frontend`, `npm run build`다.
- 백엔드는 Flask/Python 3.11+ 앱이며 `backend/app`에 있다. 기본 API 포트는 `5001`이다.
- 프론트엔드는 Vue 3/Vite 앱이며 `frontend/src`에 있다. 기본 개발 포트는 `3001`이다.
- 지속 데이터와 실행 산출물은 `backend/uploads/projects`, `backend/uploads/simulations`, `backend/uploads/reports` 아래에 저장된다. 이 경로는 분석 참고용 산출물이지 일반 소스 코드가 아니다.
- 첫 번째 큰 흐름은 `Home -> MainView(Process) -> /api/graph/ontology/generate -> /api/graph/build`다. 이 흐름이 문서 업로드, 온톨로지 생성, Zep 그래프 구축을 담당한다.
- 두 번째 큰 흐름은 `/api/simulation/create -> /api/simulation/prepare`다. 이 흐름이 Zep 그래프 엔티티를 읽고, OASIS Agent profile과 `simulation_config.json`을 만든다.
- 현재 후반 시뮬레이션 엔진은 OASIS/camel-oasis 기반이다. 실행 진입점은 `backend/app/services/simulation_runner.py`이고 실제 하위 프로세스는 `backend/scripts/run_parallel_simulation.py`, `run_twitter_simulation.py`, `run_reddit_simulation.py`다.
- 현재 SNS 플랫폼은 코드상 `twitter`와 `reddit`이지만 UI에서는 `Info Plaza`, `Topic Community`처럼 추상화되어 있다. 보험 시뮬레이터에서는 이를 영업/커뮤니티/미디어/설계사 채널로 재해석하거나 교체하는 것이 자연스럽다.
- `reddit_profiles.json`과 `twitter_profiles.csv`는 OASIS가 요구하는 형식이다. `username`, `user_id`, `persona` 등 필드명을 바꿀 때는 생성기와 실행 스크립트를 함께 바꿔야 한다.
- 시뮬레이션 실행 로그의 핵심 계약은 플랫폼별 `actions.jsonl`이다. 프론트엔드 실시간 타임라인과 백엔드 상태 조회가 이 로그를 읽는다.
- ReportAgent와 인터뷰 기능은 완료된 시뮬레이션 산출물과 살아 있는 OASIS 환경에 의존한다. 후반 엔진을 바꾸면 보고서 도구와 인터뷰 IPC도 같이 점검해야 한다.
- `scenarios/korea-health-insurance-launch`는 한국 보험시장 건강보험 신상품 출시를 위한 현재 스타터 시드다.

## Modification Boundary

사용자 의도는 1차 온톨로지 그래프와 Agent 생성까지는 크게 바꾸지 않는 것이다. 보험상품 판매 시뮬레이터 개조의 우선 경계는 다음이다.

- 우선 보존: `backend/app/api/graph.py`, `backend/app/services/ontology_generator.py`, `backend/app/services/graph_builder.py`, Zep 기반 프로젝트/그래프 저장 구조.
- 부분 확장: `backend/app/services/oasis_profile_generator.py`, `backend/app/services/simulation_config_generator.py`.
- 핵심 개조: `backend/scripts/run_parallel_simulation.py`, 플랫폼별 실행 스크립트, `backend/app/services/simulation_runner.py`, `frontend/src/components/Step2EnvSetup.vue`, `frontend/src/components/Step3Simulation.vue`, ReportAgent 도구/리포트 관점.

## Detailed Docs

- [Current Architecture](docs/current-architecture.md): 현재 코드 구조, API 흐름, 프론트엔드 라우트, 산출물 위치.
- [Runtime Data Contracts](docs/runtime-data-contracts.md): 프로젝트/시뮬레이션/profile/config/action log/IPC의 현재 데이터 계약.
- [Insurance Simulator Refactor Plan](docs/insurance-simulator-refactor-plan.md): 보험상품 판매 시뮬레이터로 후반부를 바꾸는 실무 개조 지도.
