# miromiro

가상의 대한민국을 시뮬레이션하고, 그 안에서 보험상품을 실험/예측하기 위한 작업 디렉터리다.

현재 방향은 **MiroFish를 레퍼런스로 삼되, SNS 여론 시뮬레이터를 보험 시장 디지털 트윈 엔진으로 개조**하는 것이다.

## 현재 셋업 상태

- 공개 샘플 데이터 수집 완료: `data-sample/`
- 수집 가능성/우선순위 정리 완료: `docs/virtual-korea-insurance-sim/`
- MiroFish 레퍼런스 클론 완료: `reference/MiroFish`
  - 현재 기준 reference HEAD: `5d35f9a`
- Python 구현 스켈레톤 생성 완료: `src/virtual_korea_insurance_sim/`

## 핵심 목표

1. 공개데이터 기반으로 synthetic Korea household/market 레이어를 만든다.
2. 보험사/상품/채널/규제 시나리오를 월 단위로 돌리는 MVP를 만든다.
3. 결과로 가입률, 유지율, 해지율, 채널 효율, 손해율 proxy 같은 KPI를 산출한다.
4. 이후 KOSIS/SGIS/NHIS/HIRA/사내 데이터를 붙여 정확도를 높인다.

## 주요 폴더

- `reference/MiroFish`
  - 원본 MiroFish 레퍼런스 클론
- `docs/virtual-korea-insurance-sim`
  - 조사 문서, 목표, 레퍼런스 맵, 로드맵
- `data-sample`
  - 실제 수집된 공개 샘플
- `src/virtual_korea_insurance_sim`
  - Python 구현 시작점
- `scripts`
  - 데이터 재수집 및 유틸 스크립트

## 바로 보면 좋은 문서

- `docs/virtual-korea-insurance-sim/implementation-goals.md`
- `docs/virtual-korea-insurance-sim/mirofish-reference-map.md`
- `docs/virtual-korea-insurance-sim/implementation-roadmap.md`

## 빠른 시작

```bash
cd /Users/jules/Desktop/work/miromiro
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m virtual_korea_insurance_sim summary
```

## 참고

레퍼런스 업데이트가 필요하면:

```bash
bash scripts/update_reference_mirofish.sh
```
