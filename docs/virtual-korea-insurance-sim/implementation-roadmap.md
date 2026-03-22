# Implementation Roadmap

이 문서는 `miromiro`의 실제 구현 순서를 짧고 명확하게 고정하기 위한 로드맵이다.

---

## Milestone 0 — Bootstrap (done now)

목표:
- 레퍼런스와 샘플 데이터, 문서, 초기 코드 구조를 확보한다.

현재 상태:
- [x] 샘플 데이터 수집
- [x] 수집 가능성 정리
- [x] MiroFish 레퍼런스 클론
- [x] 구현 목표/로드맵 문서화
- [x] Python 스켈레톤 생성

---

## Milestone 1 — Sample ingestion

목표:
- `data-sample/`의 현재 파일들을 코드에서 읽을 수 있게 한다.

해야 할 일:
- [ ] sample inventory 로더 구현
- [ ] 파일 메타데이터(schema, category, source, size) 정규화
- [ ] 샘플별 parser stub 추가
  - [ ] XLSX: MOIS / KLIA
  - [ ] PDF: KDCA / KISA / BOK / HIRA guide
  - [ ] JSON: data.go.kr metadata
- [ ] ingestion summary JSON 출력

완료 기준:
- `python -m virtual_korea_insurance_sim summary` 로 현재 샘플 목록과 카테고리를 안정적으로 보여줄 수 있다.

---

## Milestone 2 — Core domain schema

목표:
- household / insurer / product / channel / regulator schema를 고정한다.

해야 할 일:
- [ ] household segment dataclass / model 확정
- [ ] insurer profile model 추가
- [ ] insurance product model 추가
- [ ] channel profile model 추가
- [ ] macro / regulation scenario model 추가

완료 기준:
- 예시 시나리오 JSON 또는 Python object로 최소 실험 단위를 만들 수 있다.

---

## Milestone 3 — Synthetic Korea v0

목표:
- 공개 샘플을 기반으로 최소 synthetic Korea segment를 만든다.

해야 할 일:
- [ ] 지역 레이어 생성
- [ ] 인구/가구 segment 생성
- [ ] health risk bucket 할당
- [ ] digital affinity / channel preference proxy 할당
- [ ] affordability proxy 할당

완료 기준:
- household segment 목록이 생성되고, 각 segment가 보험 실험에 필요한 핵심 상태값을 가진다.

---

## Milestone 4 — Insurance market engine v0

목표:
- 월 단위로 굴러가는 보험시장 실험 엔진을 만든다.

해야 할 일:
- [ ] exposure step
- [ ] need / affordability scoring
- [ ] product comparison step
- [ ] apply / subscribe step
- [ ] persist / churn step
- [ ] competitor response hook
- [ ] simple claims / loss proxy hook

완료 기준:
- 12개월 시나리오를 실행하고 월별 KPI를 반환할 수 있다.

---

## Milestone 5 — KPI / reporting

목표:
- 결과를 해석 가능한 형태로 저장/출력한다.

해야 할 일:
- [ ] KPI 집계기 구현
- [ ] segment/channel/product별 결과표 생성
- [ ] Markdown report exporter 구현
- [ ] 시나리오 비교 기능 초안 추가

완료 기준:
- 하나의 시나리오를 실행하고 Markdown 리포트를 생성할 수 있다.

---

## Milestone 6 — Data upgrade path

목표:
- 더 강한 외부/승인/내부 데이터를 붙일 경로를 준비한다.

해야 할 일:
- [ ] KOSIS 표 ID 고정
- [ ] SGIS API key 연결
- [ ] NHIS / HIRA 승인 데이터용 별도 ingest 경로 설계
- [ ] 상품요약서 / 약관 extractor 설계
- [ ] calibration 입력 포인트 정의

완료 기준:
- MVP 구조를 깨지 않고 데이터 정밀도를 점진적으로 높일 수 있다.

---

## 작업 우선순위

지금 당장 구현 순서는 아래처럼 간다.

1. sample ingestion
2. core domain schema
3. synthetic household/segment builder
4. monthly market engine
5. KPI/report exporter

즉 **데이터 수집과 고도화는 병행하되, 지금 가진 샘플만으로 엔진부터 돌려보는 방향**이다.
