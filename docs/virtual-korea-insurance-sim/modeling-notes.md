# Modeling Notes — From Korea Data to Insurance Simulation

이 문서는 수집한 데이터를 실제 시뮬레이터 구조로 어떻게 변환할지에 대한 초안이다.

---

## 1. 시뮬레이션 단위

보험상품 실험은 SNS처럼 초단기 반응보다 **월 단위 의사결정과 누적성과**가 중요하다.

### 추천 time step
- 기본: 1 month
- 필요시 세부 이벤트는 week 단위 서브스텝

### 추천 관측 기간
- 12개월: 초기 실험용
- 24~36개월: 유지율/손해율 보기 위한 중기 실험

---

## 2. 핵심 에이전트 타입

### A. Household / Individual Agent
가상의 대한민국 주민/가구

#### 핵심 상태값
- age / age_band
- sex
- region
- household_type
- dependents / children
- income_band
- wealth_band
- debt_level
- occupation_group
- employment_stability
- health_risk_score
- chronic_condition_flags
- existing_insurance_profile
- risk_aversion
- digital_affinity
- brand_trust_by_carrier
- channel_preference
- monthly_budget_headroom

#### 핵심 행동
- 광고 인지
- 상품 탐색
- 비교 견적
- 상담 요청
- 가입 보류
- 가입
- 추가 특약 구매
- 갱신
- 해지/실효
- 청구
- 가족/지인 추천 또는 비추천

### B. Insurer Agent
우리 회사 + 경쟁사

#### 핵심 상태값
- carrier_name
- capital_constraint_proxy
- product_portfolio
- pricing_strategy
- underwriting_strictness
- target_segments
- marketing_budget
- channel_mix
- brand_strength
- claim_management_policy

#### 핵심 행동
- 상품 출시/개정
- 가격 조정
- 특약 추가/축소
- 채널 투자 확대/축소
- 세그먼트 타겟팅 변경
- 심사 기준 조정
- 마케팅 메시지 변경

### C. Channel Agent
설계사, GA, 온라인 직판, 비교플랫폼, 제휴채널 등

#### 핵심 상태값
- channel_type
- reach
- trust_level
- conversion_quality
- service_speed
- cost_per_acquisition
- persistency_quality

#### 핵심 행동
- 리드 생성
- 상담
- 추천상품 제시
- 계약 유도
- 유지관리

### D. Regulator / Environment Agent
금융당국, 제도 변경, 경제 충격 등

#### 핵심 상태값
- regulation_scenario
- disclosure_rules
- macro_conditions
- medical_cost_trend
- unemployment_trend

#### 핵심 행동
- 규제 변경 이벤트
- 공시 강화
- 판매행위 제한/완화
- 세제/정책 변화

---

## 3. 추천 상태 레이어

### 레이어 1 — Population Layer
- 인구/가구 분포
- 지역별 구조
- 연령, 가구형태, 직업

### 레이어 2 — Economic Layer
- 소득, 자산, 부채, 지출
- 경기 충격
- 보험료 부담 여력

### 레이어 3 — Health Risk Layer
- 질병/의료이용/사망위험
- 건강행동
- 상품 필요도

### 레이어 4 — Insurance Market Layer
- 보험사/경쟁사/상품/채널
- 가격·보장 구조
- 심사 정책

### 레이어 5 — Decision Layer
- 인지 → 고려 → 비교 → 청약 → 가입 → 유지/해지

### 레이어 6 — Outcome Layer
- 계약 수
- 유지율
- 손해율
- 수익성
- 점유율

---

## 4. 최소 의사결정 파이프라인

각 household agent는 매월 대략 이런 흐름을 탄다.

1. **Need update**
   - 가족상황, 연령, 건강상태, 경제사정 변화
2. **Exposure**
   - 어떤 채널/상품에 노출됐는가
3. **Eligibility**
   - 가입 가능 조건을 충족하는가
4. **Affordability**
   - 보험료를 감당 가능한가
5. **Preference scoring**
   - 브랜드/보장/가격/채널/추천을 반영한 선호도 계산
6. **Action**
   - 무시 / 비교 / 상담 / 가입 / 보류 / 해지 / 갱신
7. **Outcome**
   - 계약 체결, 유지, 청구 발생 여부 업데이트

---

## 5. 필요한 핵심 함수들

### 1) Need score
예시 입력:
- 연령
- 자녀 유무
- 건강위험도
- 기존 보장 공백
- 최근 의료이용

출력:
- 상품군별 필요도 점수

### 2) Affordability score
예시 입력:
- 소득
- 부채
- 월 여유자금
- 기대 보험료

출력:
- 가입 가능성 / 유지 가능성

### 3) Trust & channel score
예시 입력:
- 브랜드 신뢰
- 디지털 친숙도
- 설계사 선호 여부
- 지역 특성

출력:
- 온라인/설계사/GA/제휴 채널 선택 확률

### 4) Underwriting outcome
예시 입력:
- 나이
- 건강위험도
- 과거 병력 proxy
- 상품 조건

출력:
- 승인 / 조건부 / 거절

### 5) Claims / loss generator
예시 입력:
- 상품군
- 건강위험도
- 연령/성별
- 시간 경과

출력:
- 청구 발생 여부
- 청구 금액 분포

---

## 6. MVP에서 단순화할 것

처음부터 너무 많이 넣으면 망한다. MVP에선 다음처럼 단순화하는 게 좋다.

### Population
- 전국민 개별 5천만명 X
- 대표 household/individual 5천~5만 샘플 O

### Health
- 세밀한 ICD 코드 전부 X
- 질환 risk bucket O

### Insurance products
- 실제 약관 100% 복제 X
- 핵심 feature vector O
  - 가격 수준
  - 보장 범위
  - 가입조건
  - 채널 적합성

### Competitors
- 전 보험사 full fidelity X
- 상위 경쟁사 + archetype 경쟁사 O

### Marketing
- 크리에이티브별 미세 반응 X
- 채널/세그먼트 단위 전환률 O

---

## 7. 추천 MVP 산출물

시뮬레이션 1회 결과에서 최소한 아래는 나와야 한다.

- 세그먼트별 예상 가입자 수
- 세그먼트별 예상 가입률
- 채널별 계약 수 / CAC
- 월별 유지율 / 실효율 / 해지율
- 상품군별 예상 청구율 / 손해율
- 경쟁사 대비 점유율 변화
- 어떤 세그먼트에 잘 맞는지 설명

---

## 8. 공개데이터만으로 가능한 수준 vs 불가능한 수준

### 공개데이터만으로 가능한 것
- synthetic Korea population 생성
- 시장 크기와 대략적 세그먼트 반응 시뮬레이션
- 채널/가격/보장 구조 변화의 방향성 테스트
- 지역/연령/소득군별 타깃 적합도 테스트

### 공개데이터만으로 어려운 것
- 회사 고유 전환율 정확 예측
- 실제 실효/해지의 정밀 추정
- 미세한 underwriting 결과 예측
- 회사별 손해율 수준 정밀 예측

즉 MVP는 **전략 실험기**, 고도화 이후는 **사업 의사결정기** 가 된다.

---

## 9. 구현 구조 제안

### ingestion/
- census_ingest
- kosis_ingest
- health_ingest
- insurance_market_ingest
- regulatory_ingest

### synthesis/
- population_synthesizer
- health_risk_assigner
- insurance_profile_assigner
- channel_preference_assigner

### simulation/
- household_engine
- insurer_engine
- channel_engine
- regulator_engine
- event_scheduler

### evaluation/
- conversion_metrics
- persistency_metrics
- claims_metrics
- profitability_metrics
- scenario_compare

---

## 10. 핵심 메세지

소셜관계망 시뮬레이션을 보험 시뮬레이션으로 확장한다는 건,

- **“발화와 확산” 중심 엔진**을
- **“가구·시장·건강·규제·계약” 중심 엔진**으로 바꾸는 것

이다.

그래서 제일 먼저 필요한 건 더 많은 LLM이 아니라,
**어떤 데이터를 household / insurer / channel / regulator state로 매핑할지 정하는 일**이다.
