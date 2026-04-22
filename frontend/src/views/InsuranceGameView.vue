<template>
  <div class="main-view">
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MIROFISH</div>
      </div>

      <div class="header-center">
        <span class="mode-badge">3D GAME SPACE</span>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">Step 3/5</span>
          <span class="step-name">보험 시뮬레이션 게임</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <main class="content-area">
      <InsuranceGameSpace
        :simulationId="currentSimulationId"
        :projectData="projectData"
        :graphData="graphData"
        :systemLogs="systemLogs"
        @go-back="handleGoBack"
        @add-log="addLog"
        @update-status="updateStatus"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import InsuranceGameSpace from '../components/InsuranceGameSpace.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation } from '../api/simulation'

const route = useRoute()
const router = useRouter()

defineProps({
  simulationId: String
})

const currentSimulationId = ref(route.params.simulationId)
const projectData = ref(null)
const graphData = ref(null)
const systemLogs = ref([])
const currentStatus = ref('processing')

const statusClass = computed(() => currentStatus.value)

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Paused'
  return 'Running'
})

const addLog = (msg) => {
  const now = new Date()
  const time = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) + '.' + now.getMilliseconds().toString().padStart(3, '0')

  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const handleGoBack = () => {
  router.push({ name: 'Simulation', params: { simulationId: currentSimulationId.value } })
}

const loadSimulationData = async () => {
  if (!currentSimulationId.value) return

  try {
    addLog(`보험 게임 데이터 로드: ${currentSimulationId.value}`)
    const simRes = await getSimulation(currentSimulationId.value)

    if (!simRes.success || !simRes.data?.project_id) {
      addLog(`시뮬레이션 메타데이터 로드 실패: ${simRes.error || '프로젝트 정보 없음'}`)
      return
    }

    const projRes = await getProject(simRes.data.project_id)
    if (projRes.success && projRes.data) {
      projectData.value = projRes.data
      addLog(`프로젝트 로드 성공: ${projRes.data.project_id}`)

      if (projRes.data.graph_id) {
        const graphRes = await getGraphData(projRes.data.graph_id)
        if (graphRes.success) {
          graphData.value = graphRes.data
          addLog('그래프 데이터를 보험 게임 공간에 연결했습니다')
        }
      }
    }
  } catch (err) {
    addLog(`보험 게임 메타데이터 로드 예외: ${err.message}`)
  }
}

onMounted(() => {
  addLog('InsuranceGameView 초기화')
  loadSimulationData()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.app-header {
  height: 60px;
  border-bottom: 1px solid #EAEAEA;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #FFFFFF;
  z-index: 100;
  position: relative;
  flex: 0 0 auto;
}

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  cursor: pointer;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.mode-badge {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #999999;
}

.step-name {
  font-weight: 700;
  color: #000000;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: #E0E0E0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666666;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #CCCCCC;
}

.status-indicator.processing .dot {
  background: #FF5722;
  animation: pulse 1s infinite;
}

.status-indicator.completed .dot {
  background: #4CAF50;
}

.status-indicator.error .dot {
  background: #F44336;
}

@keyframes pulse {
  50% {
    opacity: 0.5;
  }
}

.content-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 760px) {
  .app-header {
    padding: 0 12px;
  }

  .header-center {
    display: none;
  }

  .workflow-step {
    font-size: 12px;
  }

  .brand {
    font-size: 16px;
  }
}
</style>
