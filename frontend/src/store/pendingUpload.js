/**
 * 임시로 업로드 대기 중인 파일과 요구사항을 저장
 * 홈에서 엔진 시작을 클릭한 뒤 즉시 이동할 때 사용하며, Process 페이지에서 API 호출을 다시 수행
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  isPending: false
})

export function setPendingUpload(files, requirement) {
  state.files = files
  state.simulationRequirement = requirement
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.isPending = false
}

export default state
