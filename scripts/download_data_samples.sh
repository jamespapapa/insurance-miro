#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$ROOT_DIR/data-sample"
UA="Mozilla/5.0"

mkdir -p \
  "$DATA_DIR/population-household" \
  "$DATA_DIR/health-risk" \
  "$DATA_DIR/insurance-market" \
  "$DATA_DIR/channel-digital" \
  "$DATA_DIR/macro-regulatory" \
  "$DATA_DIR/access-guides"

download_mois_population() {
  local cookie
  cookie="$(mktemp)"
  curl -s -A "$UA" -c "$cookie" 'https://jumin.mois.go.kr/statMonth.do' >/dev/null
  curl -s -A "$UA" -b "$cookie" -e 'https://jumin.mois.go.kr/statMonth.do' -L \
    'https://jumin.mois.go.kr/downloadExcel2.do?searchYearMonth=month&xlsStats=1' \
    --data 'sltOrgType=1&sltOrgLvl1=A&sltOrgLvl2=&gender=gender&genderPer=genderPer&generation=generation&sltUndefType=&searchYearStart=2026&searchMonthStart=02&searchYearEnd=2026&searchMonthEnd=02&sltOrderType=1&sltOrderValue=ASC&category=month' \
    -o "$DATA_DIR/population-household/mois_resident_population_households_2026-02_current_view.xlsx"
  rm -f "$cookie"
}

download_data_go_kr_metadata() {
  curl -L -s 'https://www.data.go.kr/catalog/3033301/fileData.json' \
    -o "$DATA_DIR/population-household/data_go_kr_3033301_mois_population_metadata.json"
  curl -L -s 'https://www.data.go.kr/catalog/3074658/fileData.json' \
    -o "$DATA_DIR/health-risk/data_go_kr_3074658_kdca_health_metadata.json"
}

download_kdca_health_pdf() {
  curl --http1.1 -L -s -A "$UA" \
    'https://www.kdca.go.kr/bbs/kdca/42/240811/download.do' \
    -o "$DATA_DIR/health-risk/kdca_regional_health_statistics_2025_summary.pdf"
}

download_hira_guide() {
  curl -L -s \
    'https://opendata.hira.or.kr/co.apndFile.dir/download.do?fileNm=%EC%97%B0%EA%B5%AC%EA%B3%BC%EC%A0%9C_%EC%9D%B4%EC%9A%A9_%EA%B0%80%EC%9D%B4%EB%93%9C.pdf' \
    -o "$DATA_DIR/access-guides/hira_research_task_usage_guide.pdf"
}

download_klia_file() {
  local referer="$1"
  local file_no="$2"
  local seq="$3"
  local output_path="$4"
  local cookie
  cookie="$(mktemp)"
  curl -s -A "$UA" -c "$cookie" "$referer" >/dev/null
  curl -s -A "$UA" -b "$cookie" -e "$referer" \
    "https://www.klia.or.kr/FileDown.do?fileNo=${file_no}&seq=${seq}" \
    -o "$output_path"
  rm -f "$cookie"
}

download_klia_files() {
  local annual_ref='https://www.klia.or.kr/eng/reportStatistics/annualStatistics.do'
  local monthly_ref='https://www.klia.or.kr/eng/reportStatistics/monthlyStatisticsView.do'

  download_klia_file "$annual_ref" '19514' '1' \
    "$DATA_DIR/insurance-market/klia_annual_2022_premium_by_distribution_channel.xlsx"
  download_klia_file "$annual_ref" '19519' '1' \
    "$DATA_DIR/insurance-market/klia_annual_2022_new_business_by_region.xlsx"
  download_klia_file "$annual_ref" '19520' '1' \
    "$DATA_DIR/insurance-market/klia_annual_2022_business_in_force_by_region.xlsx"
  download_klia_file "$annual_ref" '19529' '1' \
    "$DATA_DIR/insurance-market/klia_annual_2022_industry_employment_by_region.xlsx"
  download_klia_file "$annual_ref" '19531' '1' \
    "$DATA_DIR/insurance-market/klia_annual_2022_life_insurance_consultant_statistics.xlsx"
  download_klia_file "$monthly_ref" '19669' '1' \
    "$DATA_DIR/insurance-market/klia_monthly_2023-11.xlsx"
}

download_kisa_attachment() {
  local attach_seq="$1"
  local output_path="$2"
  local cookie
  cookie="$(mktemp)"
  curl --http1.1 -s -A "$UA" -c "$cookie" \
    'https://www.kisa.or.kr/20503/form?lang_type=KO&page=&postSeq=0011998' >/dev/null
  curl --http1.1 -s -A "$UA" -b "$cookie" \
    -e 'https://www.kisa.or.kr/20503/form?lang_type=KO&page=&postSeq=0011998' \
    'https://www.kisa.or.kr/post/fileDownload?menuSeq=20503&postSeq=0011998&lang_type=KO' \
    --get --data-urlencode "attachSeq=${attach_seq}" \
    -o "$output_path"
  rm -f "$cookie"
}

download_kisa_files() {
  download_kisa_attachment '1' \
    "$DATA_DIR/channel-digital/kisa_2018_internet_usage_survey_report_ko.pdf"
  download_kisa_attachment '2' \
    "$DATA_DIR/channel-digital/kisa_2018_internet_usage_survey_tables_ko.pdf"
}

download_bok_file() {
  curl -L -s -A "$UA" \
    'https://www.bok.or.kr/fileSrc/eng/556142c2d1cf4d9aaa5dc4e1dd0d235a/2/2c545426938341df9caac5fc9b178f56.pdf' \
    -o "$DATA_DIR/macro-regulatory/bok_household_credits_q2_2025.pdf"
}

download_mois_population
download_data_go_kr_metadata
download_kdca_health_pdf
download_hira_guide
download_klia_files
download_kisa_files
download_bok_file

echo "Downloaded sample files into: $DATA_DIR"
