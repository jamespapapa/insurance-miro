# MiroFish Reference Map

현재 `reference/MiroFish` 는 이 프로젝트의 구조적 레퍼런스다.

- reference clone path: `/Users/jules/Desktop/work/miromiro/reference/MiroFish`
- cloned reference HEAD: `5d35f9a`

아래는 **무엇을 재사용 / 변형 / 교체**할지 정리한 맵이다.

---

## 요약

- **재사용**: 프로젝트/문서/작업 흐름, 파이프라인 분리 방식, 리포트 orchestration 개념
- **변형**: graph/ontology를 사회관계망이 아니라 한국 시장·가구 구조용으로 사용
- **교체**: Twitter/Reddit/OASIS 중심 시뮬레이션 엔진

---

## 맵

| MiroFish 레퍼런스 | 현재 역할 | 우리 프로젝트에서의 처리 | 새 역할 / 대응 모듈 |
| --- | --- | --- | --- |
| `backend/app/api/graph.py` | 프로젝트 생성, 파일 입력, ontology/graph 파이프라인 시작점 | **변형** | 문서/통계 입력, source registry, scenario bootstrap API/CLI |
| `backend/app/services/ontology_generator.py` | SNS 여론 시뮬레이션용 ontology 생성 | **교체에 가까운 변형** | Korea market schema builder / domain schema templates |
| `backend/app/services/graph_builder.py` | Zep graph 구축 | **선택적 재사용** | knowledge graph / source graph / entity graph builder |
| `backend/app/services/zep_entity_reader.py` | graph entity 읽기 | **변형** | segment/entity extractor |
| `backend/app/services/oasis_profile_generator.py` | SNS persona/profile 생성 | **교체** | household/insurer/channel/regulator profile builder |
| `backend/app/services/simulation_config_generator.py` | Twitter/Reddit simulation config 생성 | **변형** | insurance experiment scenario builder |
| `backend/app/services/simulation_manager.py` | simulation 준비/저장/상태관리 | **재사용 패턴** | simulation workspace manager |
| `backend/app/services/simulation_runner.py` | SNS runtime 실행 | **교체** | monthly market simulation engine |
| `backend/scripts/run_twitter_simulation.py` | Twitter world runtime | **제거/교체** | not used |
| `backend/scripts/run_reddit_simulation.py` | Reddit world runtime | **제거/교체** | not used |
| `backend/scripts/run_parallel_simulation.py` | parallel SNS runtime | **교체** | monthly / cohort-based insurance simulation runner |
| `backend/app/services/zep_graph_memory_updater.py` | agent 활동을 graph에 write-back | **후순위 변형** | optional state/event write-back layer |
| `backend/app/services/report_agent.py` | 시뮬레이션 결과 리포트 작성 | **변형** | KPI explainer / scenario report writer |
| `backend/app/api/report.py` | 보고서 생성/조회 API | **재사용 패턴** | report export interface |
| `backend/app/models/project.py` | project state 저장 | **재사용 패턴** | experiment project state |
| `backend/app/models/task.py` | task/progress 상태관리 | **재사용 패턴** | run/task tracker |
| `frontend/` 전체 | MiroFish 웹 UI | **후순위** | Phase 0에서는 보류, CLI 우선 |

---

## 가장 중요한 판단

### 그대로 가져오면 안 되는 것

아래는 그대로 쓰면 안 된다.

- Twitter/Reddit action set
- follower/karma/statuses 기반 profile schema
- 소셜 여론 확산 중심 prompt
- SNS post/comment/like/follow 로직

### 적극적으로 참고할 것

아래는 구조적으로 참고 가치가 높다.

- 입력 → 구조화 → 시뮬레이션 준비 → 실행 → 보고서 흐름
- 상태 저장 방식
- 긴 작업을 task/progress로 관리하는 방식
- 결과 리포팅을 별도 모듈로 분리한 점

---

## 현재 프로젝트 대응 폴더

이 프로젝트에서는 아래 Python 패키지를 중심으로 새 엔진을 만든다.

- `src/virtual_korea_insurance_sim/ingestion`
- `src/virtual_korea_insurance_sim/domain`
- `src/virtual_korea_insurance_sim/synthesis`
- `src/virtual_korea_insurance_sim/simulation`
- `src/virtual_korea_insurance_sim/evaluation`

즉, **MiroFish는 뼈대를 참고하는 레퍼런스 저장소**고,
실제 구현은 `src/virtual_korea_insurance_sim/` 아래에서 진행한다.
