# Runtime Data Contracts

이 문서는 현재 코드가 파일과 API 사이에서 기대하는 데이터 계약을 정리한다. 보험 판매 시뮬레이터로 후반부를 바꿀 때, 이 계약을 유지할지 확장할지 먼저 결정해야 한다.

## Project Contract

저장 위치: `backend/uploads/projects/<project_id>/project.json`

주요 필드:

- `project_id`: `proj_<12 hex>`
- `name`
- `status`: `created`, `ontology_generated`, `graph_building`, `graph_completed`, `failed`
- `files`: 업로드 파일 메타데이터
- `total_text_length`
- `ontology.entity_types`
- `ontology.edge_types`
- `analysis_summary`
- `graph_id`: Zep graph id, 보통 `mirofish_<16 hex>`
- `graph_build_task_id`
- `simulation_requirement`
- `chunk_size`, `chunk_overlap`
- `error`

함께 저장되는 파일:

- `files/<random>.pdf|md|txt`
- `extracted_text.txt`

## Graph API Contract

- `POST /api/graph/ontology/generate`
  - multipart form: `files`, `simulation_requirement`, optional `project_name`, `additional_context`
  - returns `project_id`, `ontology`, `analysis_summary`, `files`, `total_text_length`
- `POST /api/graph/build`
  - JSON: `project_id`, optional `graph_name`, `chunk_size`, `chunk_overlap`, `force`
  - returns `task_id`
- `GET /api/graph/task/<task_id>`
  - task status/progress/result
- `GET /api/graph/data/<graph_id>`
  - Zep graph nodes/edges for D3 rendering and later entity reading

## Simulation State Contract

저장 위치: `backend/uploads/simulations/<simulation_id>/state.json`

주요 필드:

- `simulation_id`: `sim_<12 hex>`
- `project_id`
- `graph_id`
- `enable_twitter`, `enable_reddit`
- `status`: `created`, `preparing`, `ready`, `running`, `paused`, `stopped`, `completed`, `failed`
- `entities_count`
- `profiles_count`
- `entity_types`
- `config_generated`
- `config_reasoning`
- `current_round`
- `twitter_status`, `reddit_status`
- `error`

생성 API:

- `POST /api/simulation/create`
  - JSON: `project_id`, optional `graph_id`, `enable_twitter`, `enable_reddit`

준비 API:

- `POST /api/simulation/prepare`
  - JSON: `simulation_id`, optional `entity_types`, `use_llm_for_profiles`, `parallel_profile_count`, `force_regenerate`
  - background task로 profile/config를 생성한다.
- `POST /api/simulation/prepare/status`
  - JSON: `task_id` 또는 `simulation_id`

## Profile Contract

저장 위치:

- `backend/uploads/simulations/<simulation_id>/reddit_profiles.json`
- `backend/uploads/simulations/<simulation_id>/twitter_profiles.csv`

공통 의미 필드:

- `user_id`
- `username`
- `name`
- `bio`
- `persona`
- `age`
- `gender`
- `mbti`
- `country`
- `profession`
- `interested_topics`
- `created_at`

주의:

- Reddit JSON과 Twitter CSV는 OASIS loader가 직접 읽는다.
- `username` 필드는 OASIS가 기대하는 이름이다. 내부 dataclass의 `user_name`과 혼동하지 말아야 한다.
- 보험 도메인 속성을 추가할 경우, OASIS가 무시해도 되는 추가 컬럼/필드인지 먼저 검증해야 한다.

## Simulation Config Contract

저장 위치: `backend/uploads/simulations/<simulation_id>/simulation_config.json`

상위 필드:

- `simulation_id`
- `project_id`
- `graph_id`
- `simulation_requirement`
- `time_config`
- `agent_configs`
- `event_config`
- `twitter_config`
- `reddit_config`
- `llm_model`
- `llm_base_url`
- `generation_reasoning`

`time_config` 현재 의미:

- `total_simulation_hours`
- `minutes_per_round`
- `agents_per_hour_min`
- `agents_per_hour_max`
- `peak_hours`
- `off_peak_hours`
- `work_hours`
- `morning_hours`
- 각 시간대 multiplier

`agent_configs` 현재 의미:

- `agent_id`
- `entity_name`
- `entity_type`
- `active_hours`
- `activity_level`
- `posts_per_hour`
- `comments_per_hour`
- `response_delay_min`
- `response_delay_max`
- `sentiment_bias`
- `influence_weight`
- `stance`

`event_config` 현재 의미:

- `initial_posts`: `poster_type`, `poster_agent_id`, `content` 중심
- `hot_topics`
- `narrative_direction`
- 트리거/시나리오 설명 필드

보험 시뮬레이터 확장 후보:

- `insurance_product_config`: 상품명, 보장/보험료/가입조건/리워드/면책/개인정보 쟁점
- `sales_funnel_config`: awareness, interest, quote, 상담, 가입, 해지/이탈 같은 상태 정의
- `channel_config`: 설계사, GA, 지점, 콜센터, 앱, 커뮤니티, 언론, 인플루언서
- `intervention_schedule`: 메시지 수정, FAQ 공개, 약관 카드뉴스, 보험료 프로모션, 설계사 스크립트 배포
- `kpi_config`: 전환율, 상담 요청, 견적 요청, 가입 의향, 부정 이슈 확산, 신뢰 점수

## Run State Contract

저장 위치: `backend/uploads/simulations/<simulation_id>/run_state.json`

주요 필드:

- `runner_status`: `idle`, `starting`, `running`, `paused`, `stopping`, `stopped`, `completed`, `failed`
- `current_round`, `total_rounds`
- `simulated_hours`, `total_simulation_hours`
- `twitter_current_round`, `reddit_current_round`
- `twitter_running`, `reddit_running`
- `twitter_completed`, `reddit_completed`
- `twitter_actions_count`, `reddit_actions_count`
- `recent_actions`
- `process_pid`
- `error`

## Action Log Contract

저장 위치:

- `backend/uploads/simulations/<simulation_id>/twitter/actions.jsonl`
- `backend/uploads/simulations/<simulation_id>/reddit/actions.jsonl`

이벤트 레코드:

```json
{"round": 1, "timestamp": "...", "event_type": "round_start", "simulated_hour": 9}
```

```json
{"round": 1, "timestamp": "...", "event_type": "round_end", "actions_count": 3}
```

```json
{"timestamp": "...", "event_type": "simulation_end", "platform": "twitter", "total_rounds": 40, "total_actions": 120}
```

Agent action 레코드:

```json
{
  "round": 1,
  "timestamp": "...",
  "agent_id": 3,
  "agent_name": "Agent display name",
  "action_type": "CREATE_POST",
  "action_args": {"content": "..."},
  "result": null,
  "success": true
}
```

현재 프론트엔드 타임라인은 `action_type`과 `action_args`에 강하게 의존한다. 보험 판매 KPI를 추가하려면 다음 중 하나가 필요하다.

- 기존 action log에 `domain_event_type`, `funnel_stage`, `kpi_delta` 같은 필드를 추가하고 기존 필드는 유지한다.
- 별도 `sales_events.jsonl`을 만들고 백엔드 조회 API와 프론트엔드를 확장한다.

## SQLite Contract

OASIS 실행 중 플랫폼별 DB가 생성된다.

- `twitter_simulation.db`
- `reddit_simulation.db`

`run_parallel_simulation.py`는 `trace` 테이블의 `rowid`, `user_id`, `action`, `info`를 읽고, `post`, `comment`, `user`, `follow` 테이블을 보조 조회해 action context를 보강한다.

보험 도메인 엔진으로 교체하면 SQLite trace 의존을 제거하거나, 호환되는 정규화 계층을 새로 제공해야 한다.

## IPC Contract

저장 위치:

- commands: `backend/uploads/simulations/<simulation_id>/ipc_commands`
- responses: `backend/uploads/simulations/<simulation_id>/ipc_responses`
- env status: `backend/uploads/simulations/<simulation_id>/env_status.json`

지원 명령:

- `interview`
- `batch_interview`
- `close_env`

현재 인터뷰는 살아 있는 OASIS env와 agent graph에 질의를 주입하는 방식이다. 보험 시뮬레이터가 자체 엔진으로 바뀌면, 같은 API를 유지하더라도 “Agent 인터뷰”를 어떤 상태/기억에서 응답시킬지 별도 설계가 필요하다.

