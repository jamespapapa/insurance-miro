# Current Architecture

이 문서는 현재 MiroFish 기반 프로젝트의 실제 주소를 정리한다. 목표는 앞단을 최대한 보존하고, 세계 구축 이후 SNS 기반 시뮬레이션을 보험상품 판매 시뮬레이터로 개조할 때 어디를 건드려야 하는지 빠르게 판단하는 것이다.

## Stack

- Root orchestration: `package.json`
  - `npm run dev`: `scripts/dev.sh`로 백엔드와 프론트엔드를 함께 실행
  - `npm run backend`: `cd backend && uv run python run.py`
  - `npm run frontend`: `cd frontend && npm run dev`
- Backend: Flask, Flask-CORS, OpenAI-compatible LLM client, Zep Cloud, camel-oasis/camel-ai
- Frontend: Vue 3, Vite, Vue Router, Axios, D3
- Runtime storage:
  - `backend/uploads/projects/<project_id>`
  - `backend/uploads/simulations/<simulation_id>`
  - `backend/uploads/reports/<report_id>`

## Source Map

- `backend/app/api/graph.py`
  - 프로젝트 관리
  - 문서 업로드 및 온톨로지 생성
  - Zep 그래프 구축
  - 그래프 데이터 조회
- `backend/app/api/simulation.py`
  - 그래프 엔티티 조회
  - 시뮬레이션 생성/준비/실행/중지
  - profile/config/action/timeline/posts/comments/agent stats 조회
  - Agent interview IPC
- `backend/app/services/ontology_generator.py`
  - 문서와 시뮬레이션 요구사항을 기반으로 소셜 여론 시뮬레이션용 온톨로지를 생성한다.
  - 현재 프롬프트는 정확히 10개 엔티티 타입과 6-10개 관계 타입을 요구한다.
- `backend/app/services/graph_builder.py`
  - Zep standalone graph를 만들고 온톨로지를 설정한 뒤 텍스트 chunk를 episode로 추가한다.
- `backend/app/services/zep_entity_reader.py`
  - Zep graph에서 노드/엣지를 읽고, 정의된 엔티티 타입에 맞게 필터링한다.
- `backend/app/services/oasis_profile_generator.py`
  - Zep entity를 OASIS profile로 변환한다.
  - Reddit은 JSON, Twitter는 CSV 형식으로 저장한다.
- `backend/app/services/simulation_config_generator.py`
  - 시간 설정, 초기 이벤트, Agent 활동 설정, 플랫폼 추천 알고리즘 설정을 LLM으로 만든다.
- `backend/app/services/simulation_manager.py`
  - `create_simulation`과 `prepare_simulation`의 영속 상태와 산출물 저장을 담당한다.
- `backend/app/services/simulation_runner.py`
  - 하위 OASIS 실행 프로세스를 시작하고 `actions.jsonl`을 읽어 상태를 갱신한다.
  - 선택적으로 Agent 활동을 Zep 그래프에 다시 episode로 적재한다.
- `backend/scripts/run_parallel_simulation.py`
  - Twitter/Reddit OASIS 환경을 병렬 실행한다.
  - 초기 게시물을 주입하고, 라운드마다 활성 Agent를 선택해 LLMAction을 실행한다.
  - SQLite trace DB를 읽어 `actions.jsonl`로 정규화한다.
  - 완료 후 환경을 닫지 않고 IPC 명령 대기 모드로 들어갈 수 있다.
- `frontend/src/views/MainView.vue`
  - 라우터의 `/process/:projectId`가 실제로 사용하는 Process 화면이다.
  - `Step1GraphBuild.vue`를 통해 그래프 구축 완료 후 simulation 생성 및 `/simulation/:simulationId`로 이동한다.
- `frontend/src/views/SimulationView.vue`
  - Step 2 환경 구축 화면이다.
  - `Step2EnvSetup.vue`를 사용해 `/api/simulation/prepare`를 호출하고 profile/config 생성을 보여준다.
- `frontend/src/views/SimulationRunView.vue`
  - Step 3 시뮬레이션 실행 화면이다.
  - `Step3Simulation.vue`를 사용해 실행 상태와 action timeline을 폴링한다.
- `frontend/src/views/Process.vue`
  - 현재 라우터에서 직접 쓰이지 않는 구형/대체 Process 구현으로 보인다.

## End-to-End Flow

1. 사용자가 홈에서 PDF/MD/TXT 파일과 시뮬레이션 요구문을 입력한다.
2. `frontend/src/store/pendingUpload.js`에 임시 저장한 뒤 `/process/new`로 이동한다.
3. `MainView.vue`가 `/api/graph/ontology/generate`를 호출한다.
4. 백엔드는 업로드 파일을 `backend/uploads/projects/<project_id>/files`에 저장하고, 추출 텍스트를 `extracted_text.txt`에 저장한다.
5. `OntologyGenerator`가 LLM으로 온톨로지를 만들고 `project.json`에 저장한다.
6. `MainView.vue`가 `/api/graph/build`를 호출한다.
7. `GraphBuilderService`가 Zep graph를 생성하고 episode를 넣은 뒤 `project.graph_id`를 저장한다.
8. 그래프 구축 완료 후 `Step1GraphBuild.vue`가 `/api/simulation/create`를 호출하고 `/simulation/:simulationId`로 이동한다.
9. `SimulationView.vue`가 simulation과 project/graph 데이터를 로드한다.
10. `Step2EnvSetup.vue`가 `/api/simulation/prepare`를 호출한다.
11. `SimulationManager.prepare_simulation`이 Zep entity를 읽고, profile 파일과 `simulation_config.json`을 만든다.
12. 준비 완료 후 `/simulation/:simulationId/start`로 이동한다.
13. `Step3Simulation.vue`가 `/api/simulation/start`를 호출한다.
14. `SimulationRunner`가 `backend/scripts/run_parallel_simulation.py`를 하위 프로세스로 실행한다.
15. 실행 스크립트가 `twitter/actions.jsonl`, `reddit/actions.jsonl`, SQLite DB, `simulation.log`를 생성한다.
16. 프론트엔드는 `/run-status`와 `/run-status/detail`을 폴링해 타임라인을 표시한다.
17. 완료 후 ReportAgent가 결과 보고서와 인터랙션을 제공한다.

## Current Back-Half Behavior

현재 후반부는 실제 보험 판매 퍼널이라기보다 SNS 여론 확산 엔진이다.

- Agent는 OASIS social platform 계정으로 생성된다.
- 행동은 `CREATE_POST`, `LIKE_POST`, `REPOST`, `QUOTE_POST`, `CREATE_COMMENT`, `SEARCH_POSTS`, `FOLLOW`, `MUTE`, `DO_NOTHING` 등이다.
- `simulation_config.json`의 `event_config.initial_posts`가 초기 여론 자극으로 작동한다.
- 시간 경과는 `time_config.total_simulation_hours`와 `minutes_per_round`로 계산된다.
- Agent 활성화는 `active_hours`, `activity_level`, 피크/비수 시간 multiplier로 결정된다.
- 결과 지표는 action count, posts/comments/timeline, agent stats 중심이다.

보험상품 판매 시뮬레이터로 바꾸려면, 이 action 중심 구조 위에 판매 퍼널 상태와 KPI를 추가하거나, OASIS 실행 스크립트를 보험 도메인 엔진으로 교체해야 한다.

## Known Implementation Notes

- `Process.vue`는 라우터에서 사용하지 않는다. 현재 `/process/:projectId`는 `MainView.vue`로 연결된다.
- `Step2EnvSetup.vue`는 `simulationId`가 필요하다. 정상 흐름에서는 `SimulationView.vue`가 이 값을 전달한다.
- `MainView.vue` 안의 Step 2 분기는 현재 정상 라우팅 흐름에서는 핵심이 아니다.
- `backend/uploads` 아래에는 이미 보험 시나리오 실행 산출물이 많다. 소스 검색 시 `backend/uploads/**`를 제외해야 결과가 명확하다.
- `social_actions/`와 `social_media_actions.log`는 별도/이전 실험 산출물로 보이며, 현재 프론트엔드 실행 경로의 핵심 계약은 `backend/uploads/simulations/<simulation_id>/**`다.

