# Data Sample Inventory

이 디렉터리는 보험상품 실험용 가상 대한민국 시뮬레이터를 위해 실제로 확보한 공개 샘플과 접근 가이드를 유형별로 정리한 곳이다.

재수집 스크립트:

- `scripts/download_data_samples.sh`

## 디렉터리 구조

### `population-household`

- `mois_resident_population_households_2026-02_current_view.xlsx`
  - 출처: MOIS 주민등록 인구통계
  - 용도: 지역별 인구, 세대, 성비, 세대당 인구
- `data_go_kr_3033301_mois_population_metadata.json`
  - 출처: data.go.kr 카탈로그 메타데이터
  - 용도: 파일 형식, 업데이트 주기, 라이선스, 담당부서 기록

### `health-risk`

- `kdca_regional_health_statistics_2025_summary.pdf`
  - 출처: KDCA
  - 용도: 지역별 건강행태, 만성질환, 정신건강, 보건의료 이용
- `data_go_kr_3074658_kdca_health_metadata.json`
  - 출처: data.go.kr 카탈로그 메타데이터
  - 용도: 지역건강통계 공개 메타데이터 기록

### `insurance-market`

- `klia_annual_2022_premium_by_distribution_channel.xlsx`
  - 용도: 채널 믹스
- `klia_annual_2022_new_business_by_region.xlsx`
  - 용도: 지역별 신계약
- `klia_annual_2022_business_in_force_by_region.xlsx`
  - 용도: 지역별 보유계약
- `klia_annual_2022_industry_employment_by_region.xlsx`
  - 용도: 채널 운영 capacity proxy
- `klia_annual_2022_life_insurance_consultant_statistics.xlsx`
  - 용도: 설계사 관련 업권 통계
- `klia_monthly_2023-11.xlsx`
  - 용도: 월별 업권 추이 샘플

### `channel-digital`

- `kisa_2018_internet_usage_survey_report_ko.pdf`
  - 용도: 디지털 친숙도, 인터넷 이용행태
- `kisa_2018_internet_usage_survey_tables_ko.pdf`
  - 용도: 통계표 확인

### `macro-regulatory`

- `bok_household_credits_q2_2025.pdf`
  - 출처: Bank of Korea
  - 용도: 가계부채/거시 affordability shock 참고

### `access-guides`

- `hira_research_task_usage_guide.pdf`
  - 출처: HIRA
  - 용도: 연구과제 기반 자료 이용 절차 파악

## 수집 메모

- 파일명은 모두 ASCII로 정리했다.
- 공개 포털 중 일부는 단순 `curl`만으로는 실패하고, 세션 쿠키나 `Referer`가 필요했다.
- `KLIA`, `KISA`, `MOIS`는 재현 가능한 다운로드 경로를 스크립트에 남겼다.
- `KOSIS`, `SGIS`, `NHIS`는 별도 키 발급/신청 절차가 필요하거나 표 선택 자동화가 남아 있어 이번 턴에서는 접근 가이드 중심으로만 정리했다.
