# Insurance Simulator Refactor Plan

이 문서는 MiroFish 후반부를 삼성생명 보험상품 신상품 판매 시뮬레이터로 바꾸기 위한 개조 지도를 정리한다.

## Product Direction

목표는 “신상품 출시 후 SNS 여론이 어떻게 흘러가는가”에서 한 단계 더 나아가 “상품 메시지, 채널 운영, 설계사/GA 대응, 소비자 불신, 커뮤니티 검증, 상담/가입 전환이 어떻게 연결되는가”를 시뮬레이션하는 것이다.

보존할 핵심:

- 문서 업로드
- 시뮬레이션 요구문 입력
- 온톨로지 생성
- Zep GraphRAG 구축
- Zep entity 기반 Agent 페르소나 생성
- 구축된 세계와 Agent를 프론트엔드에서 관찰하는 방식

개조할 핵심:

- SNS action 중심의 실행 루프
- Twitter/Reddit 플랫폼 의미
- 시뮬레이션 config schema
- 실행 결과 로그와 KPI
- Step 2/3 UI
- ReportAgent 분석 도구

## Domain Model Needed

보험상품 판매 시뮬레이터에는 현재 없는 도메인 상태가 필요하다.

- 상품 상태
  - 상품명, 보장 범위, 보험료/납입 구조, 가입조건, 면책/감액, 리워드/건강관리 연동, 청구 UX, 개인정보 처리 조건
- 고객/시장 세그먼트
  - 2030 직장인, 기혼/자녀 가구, 4050 건강 리스크 민감층, 기존 보험 보유자, 보험 불신층, 자기관리형 소비자
- 판매/영향 채널
  - 설계사, GA, 삼성생명 공식 채널, 지점, 콜센터, 앱/디지털 가입, 인플루언서, 언론, 커뮤니티, 맘카페, 재테크 커뮤니티
- Funnel 상태
  - 인지, 관심, 비교/검증, 상담/견적, 가입 의향, 가입, 이탈, 부정 확산, 재평가
- 개입 이벤트
  - 런칭 메시지, FAQ 공개, 약관 요약 카드, 보험료 예시 공개, 설계사 스크립트 배포, 개인정보 설명, 청구 후기 공개, 언론 기사, 커뮤니티 논쟁
- KPI
  - 호감/신뢰/이해도, 가격 저항, 개인정보 우려, 상담 요청, 견적 요청, 가입 의향, 예상 가입, 부정 이슈 확산, 채널별 전환 기여

## Recommended Architecture

단번에 OASIS를 제거하지 말고, 2단계로 가는 편이 안전하다.

1. Compatibility phase
   - 기존 OASIS 실행은 유지한다.
   - `simulation_config.json`에 보험 도메인 확장 필드를 추가한다.
   - `actions.jsonl` 옆에 `sales_events.jsonl` 또는 확장 action field를 추가한다.
   - ReportAgent와 UI에서 보험 KPI를 읽기 시작한다.

2. Domain engine phase
   - SNS action loop를 보험 판매/여론 복합 loop로 교체한다.
   - OASIS는 필요하면 “발화 생성기” 또는 “SNS 반응 서브엔진”으로만 사용한다.
   - Agent별 funnel state와 채널별 영향 모델을 자체 저장한다.

## Key Edit Points

### `backend/app/services/simulation_config_generator.py`

현재 역할은 시간 설정, 초기 게시물, Agent 활동 설정, 플랫폼 알고리즘 설정 생성이다.

보험화 방향:

- `SimulationParameters`에 보험 도메인 필드를 추가한다.
- 프롬프트가 상품 판매 시뮬레이션 목적을 명시하도록 바꾼다.
- `agent_configs`에 구매/상담 성향 관련 변수를 추가한다.
  - `price_sensitivity`
  - `trust_baseline`
  - `coverage_need`
  - `privacy_concern`
  - `advisor_influence`
  - `community_influence`
  - `family_decision_weight`
  - `conversion_propensity`
- `event_config.initial_posts`만으로 초기 자극을 표현하지 말고 `intervention_schedule`로 일반화한다.

### `backend/app/services/oasis_profile_generator.py`

현재 프로필은 상세 persona, profession, topics 중심이다.

보험화 방향:

- 초기에는 유지해도 된다.
- 이후 보험 고객/판매자 속성을 profile 또는 config 쪽에 추가한다.
- OASIS profile loader 호환성 때문에 profile 파일 자체보다 `simulation_config.agent_configs` 확장이 더 안전하다.

### `backend/scripts/run_parallel_simulation.py`

현재 핵심 실행 루프다.

보험화 방향:

- 현재는 라운드마다 활성 Agent를 골라 OASIS LLMAction을 실행한다.
- 초기 개조에서는 OASIS action 결과를 읽은 뒤 보험 도메인 상태를 업데이트하는 후처리 계층을 추가한다.
- 다음 단계에서는 라운드마다 다음을 계산한다.
  - 채널별 노출
  - Agent별 인지/신뢰/우려 변화
  - 상담/견적/가입/이탈 상태 전이
  - 커뮤니티/언론/설계사 이벤트가 KPI에 미치는 영향
- 출력은 기존 `actions.jsonl` 유지 + 신규 `sales_events.jsonl`, `kpi_snapshots.jsonl` 권장.

### `backend/app/services/simulation_runner.py`

현재 역할은 하위 프로세스 시작, action log 파싱, run_state 저장, optional Zep memory update다.

보험화 방향:

- 신규 로그 파일을 모니터링한다.
- `/run-status/detail` 응답에 보험 KPI snapshot을 추가한다.
- 그래프 메모리 업데이트 시 social action뿐 아니라 보험 도메인 사건도 Zep episode로 남긴다.

### `frontend/src/components/Step2EnvSetup.vue`

현재 표시 내용은 Agent profile과 시간/활동/초기 게시물/플랫폼 추천 알고리즘이다.

보험화 방향:

- 상품 구조/핵심 쟁점/채널/세그먼트/개입 시나리오를 보여준다.
- `추천 알고리즘 설정` 대신 `판매 채널/여론 채널 설정`을 표시한다.
- Agent 구성 카드에 보험 관련 속성을 표시한다.

### `frontend/src/components/Step3Simulation.vue`

현재 표시 내용은 두 플랫폼 action timeline이다.

보험화 방향:

- 타임라인은 유지하되 KPI panel을 상단에 추가한다.
- 채널별 funnel을 시각화한다.
- 예: 인지율, 상담 요청, 견적 요청, 가입 의향, 부정 이슈, 개인정보 우려, 가격 저항.
- action badge는 SNS 행동만이 아니라 `CONSULT_REQUEST`, `QUOTE_COMPARE`, `PURCHASE_INTENT_UP`, `PRIVACY_OBJECTION`, `AGENT_SCRIPT_SHARED` 같은 도메인 이벤트를 처리해야 한다.

### `backend/app/services/report_agent.py`

현재 ReportAgent는 시뮬레이션 산출물, action, posts/comments, agent interview를 도구로 사용한다.

보험화 방향:

- KPI snapshot 읽기 도구 추가
- funnel 전이 분석 도구 추가
- 채널별 성과/리스크 비교 도구 추가
- 추천 메시지/FAQ/상품 보완 항목을 고정 산출 형식으로 정리

## Output Files To Add

초기 보험화에서는 기존 산출물에 아래 파일을 추가하는 방식을 권장한다.

- `sales_events.jsonl`
  - Agent 또는 채널 단위 보험 도메인 이벤트
- `kpi_snapshots.jsonl`
  - 라운드별 집계 지표
- `agent_funnel_state.json`
  - 최종 Agent별 funnel/state
- `channel_metrics.json`
  - 채널별 노출, 반응, 전환, 부정 이슈

예상 `sales_events.jsonl` 레코드:

```json
{
  "round": 12,
  "timestamp": "...",
  "agent_id": 7,
  "agent_name": "직장인 소비자",
  "channel": "community",
  "event_type": "QUOTE_COMPARE",
  "funnel_from": "interest",
  "funnel_to": "comparison",
  "sentiment_delta": -0.1,
  "trust_delta": 0.0,
  "purchase_intent_delta": -0.05,
  "reason": "보험료 대비 보장 범위를 비교하며 약관 복잡성을 우려"
}
```

예상 `kpi_snapshots.jsonl` 레코드:

```json
{
  "round": 12,
  "simulated_hour": 6,
  "awareness": 0.62,
  "positive_sentiment": 0.31,
  "negative_sentiment": 0.44,
  "consult_requests": 18,
  "quote_requests": 9,
  "purchase_intent": 0.12,
  "privacy_concern": 0.38,
  "price_resistance": 0.51,
  "top_negative_driver": "premium_burden",
  "top_positive_driver": "simple_claim_ux"
}
```

## Refactor Phases

### Phase 1: Document and Schema Extension

- `simulation_config.json`에 보험 도메인 확장 필드 추가
- 기존 OASIS 실행은 그대로 둠
- 프론트엔드 Step 2에서 확장 필드를 표시
- ReportAgent가 확장 config를 읽어 보험 관점 보고서를 생성

### Phase 2: KPI Event Layer

- `run_parallel_simulation.py`에 action 후처리 계층 추가
- action과 Agent profile/config를 바탕으로 `sales_events.jsonl`, `kpi_snapshots.jsonl` 생성
- `simulation_runner.py`와 API가 신규 KPI를 반환
- Step 3 UI에 KPI dashboard 추가

### Phase 3: Insurance Decision Engine

- Agent별 funnel state를 명시적으로 저장
- 개입 이벤트가 상태 전이를 일으키도록 모델링
- 판매 채널별 영향력과 신뢰/반감 전파를 반영
- OASIS는 SNS 발화/댓글 생성용으로 제한하거나 제거

### Phase 4: Report and Scenario Hardening

- ReportAgent 결과 형식을 보험 출시 의사결정용으로 고정
- 시나리오 파일을 삼성생명 상품 구조에 맞게 확장
- 경쟁상품, 약관, 민원, 커뮤니티 반응 데이터 업로드 기준을 문서화

## Risks

- OASIS profile 형식은 외부 라이브러리 계약이므로 무리하게 바꾸면 실행이 깨질 수 있다.
- 현재 `actions.jsonl`는 프론트엔드와 runner 상태 계산의 핵심이다. 제거보다 확장이 안전하다.
- 보험 판매 전환은 단순 sentiment보다 상태 변수가 많다. KPI를 action count에서 직접 추론하면 품질이 낮다.
- ReportAgent가 기존 SNS 행동만 읽으면 보험 의사결정 보고서가 빈약해진다. KPI/전환/채널 도구 추가가 필요하다.
- Zep 그래프 memory update는 유용하지만 비용과 지연이 있다. KPI 이벤트까지 모두 episode로 저장할지 샘플링할지 결정해야 한다.

## Near-Term Recommendation

가장 현실적인 첫 작업은 `simulation_config_generator.py`를 보험 도메인 schema로 확장하고, 기존 OASIS 실행 후처리로 KPI 파일을 만들며, Step 3에 KPI dashboard를 추가하는 것이다. 이렇게 하면 앞단을 보존하면서도 후반부의 제품 방향을 보험상품 판매 시뮬레이터로 즉시 전환할 수 있다.

