# Source Inventory — Korea Data Sources for Insurance Market Simulation

이 문서는 **가상의 대한민국 + 보험상품 실험 시뮬레이션**에 활용 가능한 주요 데이터 소스를 정리한 인벤토리다.

---

## A. 공개/공식 소스 (우선 확인 대상)

### 1) 인구주택총조사
- 역할
  - 전국 인구, 가구, 주택의 규모와 특성 파악
  - synthetic population 생성의 기초 분포
- 왜 중요한가
  - 사람/가구/주거 단위를 지역별로 세팅하는 가장 기본 자료
- 확인 URL
  - <https://census.go.kr/main/ehpp/aa/ehppaa100m01?lang=en>
- 비고
  - 인구·가구·주택 분포의 베이스라인으로 적합

### 2) KOSIS 국가통계포털
- 역할
  - 인구, 소득, 자산, 부채, 소비, 노동, 지역경제 등 폭넓은 공식 통계 허브
- 특히 볼 것
  - 가계금융복지조사
  - 가계동향 / 소득 관련 통계
  - 지역별 인구/경제 지표
- 확인 URL
  - <https://kosis.kr>
- 참고 메모
  - 검색 결과에서 가계금융복지조사 기반 자산/가구부채/중위소득 통계 확인 가능

### 3) SGIS Plus
- 역할
  - 인구·가구·주택·사업체 등 센서스 기반 통계를 위치정보와 결합
- 왜 중요한가
  - 시군구/격자 단위 지역 기반 synthetic Korea 구축에 유리
- 확인 URL
  - <https://sgis.mods.go.kr/jsp/english/sopIntro.jsp>
- 확인된 설명 요약
  - SGIS Plus는 인구, 가구, 주택, 사업체 등 census data를 위치 기반으로 통합하는 오픈 서비스 플랫폼

### 4) KLIPS (Korean Labor & Income Panel Study)
- 역할
  - 가구/개인의 노동, 소득, 소비, 건강, 은퇴, 복지, 전이 분석
- 왜 중요한가
  - static 통계만으로 보기 어려운 **가구 상태 변화**를 보강 가능
- 확인 URL
  - <https://www.kli.re.kr/menu.es?mid=a50101000000>
- 확인된 설명 요약
  - 도시 거주 가구/개인을 추적하는 longitudinal survey로 노동, 소득, 소비, 건강, 은퇴 등 분석에 적합

### 5) KDCA 지역사회건강조사 / 지역건강통계
- 역할
  - 시군구 수준 건강지표, 생활습관, 만성질환 관련 통계
- 왜 중요한가
  - 지역별 건강위험과 보험 필요도 차이를 주기 좋음
- 후보 URL
  - <https://www.kdca.go.kr/eng/4418/subview.do>
  - <https://www.data.go.kr/data/3074658/fileData.do?recommendDataYn=Y>
- 검색 확인 메모
  - 지역건강통계 한눈에 보기 파일데이터가 공공데이터포털에 존재

### 6) NHIS / HIRA 관련 보건의료 빅데이터
- 역할
  - 의료이용, 진단, 처방, 청구 등 건강보험 기반 대규모 데이터
- 왜 중요한가
  - 건강보험/질병/상해/실손/의료 관련 상품 실험에 핵심
- 참고 URL
  - <https://pmc.ncbi.nlm.nih.gov/articles/PMC9133780/>
- 확인된 설명 요약
  - NHIS/HIRA 데이터는 사실상 거의 전 국민을 포괄하며, NHIS는 소득·사망 등 일부 사회경제 변수까지 포함
- 주의사항
  - 매우 강력하지만 접근 절차와 연구 목적 제약이 있음

### 7) K-CHSI (Korean Community Health Status Indicators)
- 역할
  - 시군구 수준 건강결과 및 건강결정요인 데이터베이스
- 왜 중요한가
  - 지역별 건강환경 차이를 시뮬레이션에 반영할 수 있음
- 참고 URL
  - <https://pmc.ncbi.nlm.nih.gov/articles/PMC10581888/>
- 검색 확인 메모
  - 다수의 공공 DB를 결합한 municipal-level health indicator database

### 8) 금융감독원 FISIS / 금융통계정보
- 역할
  - 보험사를 포함한 금융사 현황 및 사업 지표 확인
- 왜 중요한가
  - 보험업권 규모, 회사 수, 사업/건전성 지표, 공시형 통계의 기본 소스
- 확인 URL
  - <https://www.fss.or.kr/eng/main/contents.do?menuNo=400012>
  - <http://efisis.fss.or.kr>
- 확인된 설명 요약
  - 금융사 현황과 사업 데이터, 요약 통계, 건전성 지표, 엑셀 다운로드 제공

### 9) 보험개발원(KIDI)
- 역할
  - 업권 전반의 보험 계약/청구 통계, 요율/위험 분석, 상품/가격/마케팅/수익관리 지원 데이터
- 왜 중요한가
  - 보험 실험엔 사실상 가장 중요한 업권 전문 데이터 허브 중 하나
- 확인 URL
  - <https://www.kidi.or.kr/user/nd44262.do?menuCode=engsite>
- 확인된 설명 요약
  - KIDI는 국내 유일의 보험 통계 전문기관으로, 업계 전반의 policy-based contract and claims data를 수집·관리하며 product development, marketing, profit management에 활용 가능한 통계를 제공

### 10) 생명보험협회(KLIA)
- 역할
  - 생명보험 업권 통계, 회사별/연도별/지역별/채널별 실적 자료
- 왜 중요한가
  - 신상품 시뮬레이션에서 생보 쪽 신규/보유/지역/채널 지표 확보에 유용
- 확인 URL
  - <https://www.klia.or.kr/eng/reportStatistics/annualStatistics.do>
- 확인된 설명 요약
  - Premium income by insurance type, premium income by distribution channel, new business by region, business in force by region, employment by region, consultant statistics 등을 제공

### 11) 손해보험협회(KNIA) / 관련 업권 자료
- 역할
  - 손보업권 구조, 상품군, 조직, 공시 자료 확인
- 후보 URL
  - <https://www.knia.or.kr/eng/insu/insu01>
- 비고
  - 세부 통계는 추가 확인 필요. 건강/상해/실손/자동차 등 손보성 상품 실험 시 중요

### 12) KISA 인터넷 이용실태조사
- 역할
  - 인터넷/모바일 사용, 디지털 친숙도, 연령별 이용행태 파악
- 왜 중요한가
  - 온라인 직판/비대면 가입/비교플랫폼 채널 선호 추정에 도움
- 후보 URL
  - <https://www.kisa.or.kr/eng/usefulreport/surveyReport_View.jsp?mode=view&p_No=4&b_No=262&d_No=81>
- 검색 확인 메모
  - 정부 조사 기반 한국 인터넷 이용 실태 자료로 보임
- 주의사항
  - 일부 페이지 접근 제한/403 가능

---

## B. 공개자료만으로 부족한 영역 (라이선스/사내 데이터 권장)

### 1) 실제 영업 퍼널 데이터
- 필요 이유
  - 노출 → 리드 → 상담 → 청약 → 계약 전환율을 실제처럼 보정하려면 필수
- 예시
  - 광고 채널 로그
  - 상담 예약/콜센터/GA 리드 데이터
  - 상품별 청약률/심사통과율

### 2) 유지·실효·해지 데이터
- 필요 이유
  - 장기 보험 실험에서 진짜 성패는 신계약보다 유지율에 좌우됨
- 예시
  - 월차별 유지율
  - 해지 사유
  - 채널별 lapse 패턴

### 3) 청구/손해율 데이터
- 필요 이유
  - 건강/상해 상품은 손해율 없이는 “판매 실험”이 아니라 “가입률 게임”으로 끝남
- 예시
  - 질환군별 청구 빈도
  - 연령/성별/직업군별 손해율
  - 특약별 loss experience

### 4) 경쟁상품 세부 feature DB
- 필요 이유
  - 비교구매와 대체효과를 제대로 보려면 상품 구조 비교가 필요
- 예시
  - 보험료, 면책, 감액, 가입조건, 특약 구조, 보장금액

### 5) 브랜드/소비자 인식 조사
- 필요 이유
  - 보험은 신뢰/브랜드/채널 선호 영향이 큼
- 예시
  - NPS/브랜드 신뢰도
  - 온라인 구매 장벽 조사
  - 보장 이해도

---

## C. 시뮬레이터에서 직접 만들어야 하는 파생 데이터

공개 원천데이터를 그대로 쓰기보단, 아래 같은 **파생 synthetic data** 를 만들어야 한다.

### 1) Synthetic households / individuals
- 예시 필드
  - age_band
  - sex
  - region
  - household_size
  - income_band
  - occupation_group
  - health_risk_score
  - digital_affinity
  - existing_insurance_profile
  - channel_preference
  - price_sensitivity

### 2) Competitor catalog
- 예시 필드
  - carrier
  - product_type
  - target_segment
  - premium_level_index
  - coverage_breadth_index
  - underwriting_strictness
  - dominant_channel

### 3) Channel agents
- 예시 필드
  - channel_type (agent / GA / online / banca / affiliate)
  - reach
  - CAC
  - conversion_rate
  - persistency_quality

### 4) Macro/regulatory scenario objects
- 예시 필드
  - interest_rate_path
  - inflation_path
  - medical_cost_inflation
  - unemployment_shock
  - regulation_event

---

## D. 권장 확보 순서

### Step 1 — 지금 당장 모을 것 (공개데이터 MVP)
- Census / KOSIS / SGIS
- KDCA 지역건강통계
- NHIS/HIRA 접근 가능 범위 문서화
- FISIS
- KLIA / KIDI 업권 통계

### Step 2 — 병행해서 정리할 것
- 경쟁상품 feature 목록
- 규제/공시 문서
- 채널 구조 자료

### Step 3 — 실제 예측력 향상을 위해 나중에 붙일 것
- 사내 CRM/청약/유지/손해 데이터
- 외부 시장조사 데이터
- 브랜드/소비자 설문

---

## E. 바로 써먹을 수 있는 판단

지금 단계에서 가장 실용적인 시작점은 이거다.

1. **공개 통계로 synthetic Korea를 만든다**
2. **업권 통계로 보험시장 구조를 올린다**
3. **health risk와 affordability를 household에 부여한다**
4. **상품/채널/경쟁사 실험을 월 단위로 돌린다**
5. **사내 데이터가 생기면 calibration 한다**

즉, 공개데이터만으로도 “개념 검증용 가상 대한민국 보험시장”은 만들 수 있다.
