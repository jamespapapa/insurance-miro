# Implementation Goals — Virtual Korea Insurance Simulation

이 문서는 `miromiro` 프로젝트의 **실행 목표**를 고정해두기 위한 문서다.

---

## North Star

**가상의 대한민국 보험시장 디지털 트윈을 만들고, 그 안에서 보험 신상품/가격/채널/경쟁 시나리오를 실험해 월 단위 사업 성과를 예측한다.**

---

## 왜 MiroFish를 레퍼런스로 쓰는가

MiroFish는 아래 뼈대를 이미 가지고 있다.

- 문서/프로젝트 기반 입력 처리
- 온톨로지/그래프 기반 세계 구성
- 엔티티 → agent 변환
- 시뮬레이션 실행 orchestration
- 결과 분석/리포트 생성

우리가 가져갈 것은 이 **파이프라인의 구조**이고,
대신 **SNS-specific runtime** 은 보험시장용으로 교체한다.

---

## 제품 목표

### Goal 1 — Phase 0 MVP
공개 샘플 데이터만으로 돌아가는 최소 시뮬레이터를 만든다.

#### MVP가 반드시 해야 하는 일
- 샘플 데이터를 읽을 수 있다.
- synthetic household segment를 생성할 수 있다.
- 보험사/상품/채널/규제 시나리오를 정의할 수 있다.
- 월 단위 시뮬레이션을 12개월 이상 실행할 수 있다.
- 아래 KPI를 출력할 수 있다.
  - 예상 가입자 수
  - 가입률
  - 채널별 계약 수
  - 유지율 / 해지율
  - 손해율 proxy / 수익성 proxy

### Goal 2 — 구조적 확장성 확보
나중에 아래 데이터를 붙일 수 있도록 구조를 미리 분리한다.

- KOSIS 표 기반 집계 데이터
- SGIS 공간 데이터
- NHIS / HIRA 승인 기반 데이터
- 보험사 상품요약서 / 약관 구조화 데이터
- 사내 CRM / 퍼널 / 유지 / 손해 데이터

### Goal 3 — MiroFish 개조 방향 명확화
“무엇을 살리고 무엇을 버릴지”를 문서와 코드 구조 양쪽에 반영한다.

---

## 이번 셋업에서 확정한 기본 원칙

### 1. 시뮬레이션 단위
- 기본 time step: **month**
- 보조 이벤트 단위: week 또는 event-based hook

### 2. 주요 agent 타입
- Household / Individual
- Insurer
- Channel
- Regulator / Macro Environment

### 3. 우선 구현 대상
- 생명/건강/보장성 보험 실험에 필요한 구조 우선
- SNS 반응 레이어는 부가 요소로 뒤로 미룸

### 4. 우선 정확도보다 구조
처음부터 정확한 판매 예측 모델을 만들려 하지 말고,
먼저 **세계가 굴러가고 KPI가 일관되게 나오는 구조**를 만든다.

---

## Non-goals (지금 당장 안 하는 것)

- 전국민 5천만명 개별 에이전트 모델링
- 보험약관 100% 충실 복제
- 실시간 외부 데이터 스트리밍
- 정교한 UI/대시보드 프론트엔드
- 사내 비공개 데이터를 전제로 한 초기 설계

---

## Phase 0 Acceptance Criteria

아래를 만족하면 1차 MVP로 본다.

1. `data-sample/`의 현재 샘플 파일 목록을 자동으로 읽고 요약할 수 있다.
2. 지역/연령/소득/건강위험/디지털 성향을 포함한 household segment schema가 존재한다.
3. 상품/보험사/채널 시나리오 schema가 존재한다.
4. 12개월짜리 보험시장 시뮬레이션 루프를 실행할 수 있다.
5. 결과를 JSON/Markdown 형태로 저장할 수 있다.
6. 적어도 하나의 예시 시나리오를 재현 가능하게 실행할 수 있다.

---

## 첫 구현 타깃

가장 먼저 만들 구현물은 아래 4개다.

1. **Sample ingestion layer**
2. **Synthetic household generator**
3. **Monthly insurance market engine**
4. **KPI / report exporter**

---

## 한 줄 실행 방침

**데이터 수집은 계속 병행하되, 지금 확보된 샘플만으로도 바로 MiroFish 개조 작업을 시작한다.**
