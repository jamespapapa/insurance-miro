<template>
  <section class="game-space">
    <div class="top-strip">
      <div class="title-group">
        <span class="eyebrow">INSURANCE SIMULATION GAME</span>
        <h1>{{ productDisplayName }}</h1>
      </div>

      <div class="kpi-strip">
        <div v-for="item in kpiCards" :key="item.label" class="kpi-card">
          <span class="kpi-label">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>

      <div class="top-actions">
        <button class="ghost-btn" @click="emit('go-back')">환경 구축</button>
        <button class="ghost-btn" @click="resetWorld">초기화</button>
        <button class="primary-btn" @click="toggleRunning">
          {{ isRunning ? '일시정지' : '자유행동 재개' }}
        </button>
      </div>
    </div>

    <div class="game-layout">
      <div class="scene-panel">
        <div
          ref="sceneHost"
          class="scene-host"
          tabindex="0"
          @pointerdown="handlePointerDown"
          @pointermove="handlePointerMove"
          @pointerup="handlePointerUp"
          @pointerleave="handlePointerLeave"
          @contextmenu.prevent="handleContextMenu"
          @wheel.prevent="handleWheel"
        ></div>

        <div class="scene-overlay channel-legend">
          <button
            v-for="channel in CHANNELS"
            :key="channel.id"
            class="channel-chip"
            @click="focusChannel(channel)"
          >
            <span class="chip-swatch" :style="{ backgroundColor: channel.color }"></span>
            {{ channel.label }}
          </button>
        </div>

        <div class="scene-overlay world-meta">
          <span class="meta-pill">{{ currentCalendarLabel }}</span>
          <span class="meta-pill">Round {{ currentRound + 1 }}/{{ maxRounds }}</span>
          <span class="meta-pill">Agent {{ agentStates.length }}</span>
          <span class="meta-pill">{{ profileSource }}</span>
          <span class="meta-pill">{{ isPlayerMode ? 'PLAYER VIEW' : (isRunning ? 'FREE ACTION' : 'PAUSED') }}</span>
          <span v-if="isPlayerMode" class="meta-pill">{{ playerPositionLabel }}</span>
        </div>

        <div class="scene-overlay timeline-control">
          <div class="timeline-control-head">
            <span>{{ currentYearLabel }}</span>
            <strong>{{ Math.round(timelineProgress) }}%</strong>
          </div>
          <div class="timeline-bar">
            <span :style="{ width: `${timelineProgress}%` }"></span>
          </div>
          <div class="timeline-targets">
            <button
              v-for="option in targetYearOptions"
              :key="option"
              class="target-btn"
              :class="{ active: targetYears === option }"
              @click="setTargetYears(option)"
            >
              {{ option }}년
            </button>
          </div>
        </div>

        <div class="scene-overlay speed-control">
          <button
            class="speed-btn mode-btn"
            :class="{ active: isPlayerMode }"
            @click="togglePlayerMode"
          >
            {{ isPlayerMode ? '관전' : '플레이어' }}
          </button>
          <button
            v-for="option in speedOptions"
            :key="option"
            class="speed-btn"
            :class="{ active: speed === option }"
            @click="speed = option"
          >
            {{ option }}x
          </button>
        </div>

        <div v-if="isPlayerMode" class="scene-overlay player-reticle" aria-hidden="true"></div>
      </div>

      <aside class="inspector">
        <div v-if="simulationComplete" class="inspector-section result-summary">
          <div class="section-head">
            <span class="section-title">FINAL SUMMARY</span>
            <span class="section-count">{{ targetYears }}Y</span>
          </div>
          <p class="summary-lead">{{ resultSummary.headline }}</p>
          <div class="summary-grid">
            <span v-for="item in resultSummary.items" :key="item.label">
              <small>{{ item.label }}</small>
              <strong>{{ item.value }}</strong>
            </span>
          </div>
          <div class="summary-actions">
            <p v-for="item in resultSummary.recommendations" :key="item">{{ item }}</p>
          </div>
        </div>

        <div class="inspector-section selected-agent">
          <div class="section-head">
            <span class="section-title">SELECTED AGENT</span>
            <span class="section-count">{{ selectedAgent ? selectedAgent.funnel : 'NONE' }}</span>
          </div>

          <template v-if="selectedAgent">
            <div class="agent-headline">
              <div class="agent-avatar">
                <img :src="selectedAgent.avatarUrl" :alt="selectedAgent.displayName" loading="lazy" />
              </div>
              <div>
                <strong>{{ selectedAgent.displayName }}</strong>
                <span>{{ selectedAgent.role }} · {{ selectedAgent.profile.profession || '프로필 직군 없음' }}</span>
              </div>
            </div>
            <div class="agent-state-pills">
              <span class="state-pill" :class="`policy-${selectedAgent.policyState}`">{{ selectedAgent.policyLabel }}</span>
              <span class="state-pill">{{ selectedAgent.segment }}</span>
              <span class="state-pill">{{ selectedAgent.lastAction }}</span>
            </div>
            <p class="agent-bio">{{ selectedAgent.profile.bio || selectedAgent.profile.persona || '프로필 설명 없음' }}</p>
            <div class="agent-metrics">
              <span>인지 {{ Math.round(selectedAgent.awareness) }}</span>
              <span>신뢰 {{ Math.round(selectedAgent.trust) }}</span>
              <span>의향 {{ Math.round(selectedAgent.intent) }}</span>
              <span>우려 {{ Math.round(selectedAgent.privacyConcern) }}</span>
              <span>가입기간 {{ selectedAgent.tenureWeeks }}주</span>
              <span>상태 {{ selectedAgent.policyLabel }}</span>
            </div>
            <div v-if="selectedAgentHistory.length" class="agent-history">
              <div class="history-title">
                <span>최근 행적</span>
                <strong>{{ selectedAgentHistory.length }}</strong>
              </div>
              <div
                v-for="event in selectedAgentHistory.slice(0, 4)"
                :key="event.id"
                class="history-line"
              >
                <span>{{ event.time }} · {{ event.channel }}</span>
                <p>{{ event.outcome || event.message }}</p>
                <small>{{ event.reason }}</small>
              </div>
            </div>
            <div class="agent-chat">
              <div ref="chatLogRef" class="chat-log">
                <div
                  v-for="message in selectedAgent.chatMessages"
                  :key="message.id"
                  class="chat-message"
                  :class="message.role"
                >
                  <span>{{ message.role === 'user' ? '나' : selectedAgent.displayName }}</span>
                  <p>{{ message.text }}</p>
                </div>
              </div>
              <form class="chat-form" @submit.prevent="sendAgentChat">
                <input
                  v-model="chatDraft"
                  :disabled="chatBusy"
                  placeholder="가입, 해지, 전환 이유를 물어보세요"
                />
                <button type="submit" :disabled="chatBusy || !chatDraft.trim()">
                  {{ chatBusy ? '...' : '전송' }}
                </button>
              </form>
            </div>
          </template>

          <div v-else class="empty-agent">
            Agent 캐릭터를 선택하면 상태가 표시됩니다.
          </div>
        </div>

        <div class="inspector-section channel-detail" v-if="selectedChannel">
          <div class="section-head">
            <span class="section-title">CHANNEL DETAIL</span>
            <span class="section-count">{{ selectedChannel.label }}</span>
          </div>
          <div class="channel-role">
            <strong>{{ selectedChannel.role }}</strong>
            <p>{{ selectedChannel.inside }}</p>
          </div>
          <p>{{ selectedChannel.detail }}</p>
          <div class="channel-detail-grid">
            <span>
              <small>방문</small>
              <strong>{{ channelStats[selectedChannel.id]?.visits || 0 }}</strong>
            </span>
            <span>
              <small>현재 체류</small>
              <strong>{{ selectedChannelAgents.length }}</strong>
            </span>
            <span>
              <small>최근 이벤트</small>
              <strong>{{ selectedChannelEvents.length }}</strong>
            </span>
            <span>
              <small>대화/행동</small>
              <strong>{{ channelStats[selectedChannel.id]?.conversations || 0 }}</strong>
            </span>
            <span>
              <small>전환</small>
              <strong>{{ channelStats[selectedChannel.id]?.conversions || 0 }}</strong>
            </span>
            <span>
              <small>보류/이탈</small>
              <strong>{{ channelStats[selectedChannel.id]?.blocks || 0 }}</strong>
            </span>
          </div>
          <div class="channel-outcome">
            <p><strong>성공 조건</strong> {{ selectedChannel.outcome }}</p>
            <p><strong>이탈 조건</strong> {{ selectedChannel.failure }}</p>
          </div>
          <div class="signal-list">
            <span v-for="signal in selectedChannel.signals" :key="signal">{{ signal }}</span>
          </div>
          <div class="channel-events">
            <p v-for="event in selectedChannelEvents.slice(0, 3)" :key="event.id">
              <strong>{{ event.agentName }} · {{ event.action }}</strong>
              <span>{{ event.outcome }}</span>
            </p>
          </div>
        </div>

        <div class="inspector-section">
          <div class="section-head">
            <span class="section-title">CHANNEL FLOW</span>
            <span class="section-count">{{ totalVisits }} visits</span>
          </div>
          <button
            v-for="channel in CHANNELS"
            :key="channel.id"
            class="channel-row"
            :class="{ active: selectedChannelId === channel.id }"
            @click="focusChannel(channel)"
          >
            <span class="row-swatch" :style="{ backgroundColor: channel.color }"></span>
            <span class="row-copy">
              <span class="row-label">{{ channel.label }}</span>
              <small>{{ channel.role }}</small>
            </span>
            <span class="row-count">{{ channelStats[channel.id]?.visits || 0 }}</span>
          </button>
        </div>

        <div class="inspector-section agent-list">
          <div class="section-head">
            <span class="section-title">AGENTS</span>
            <span class="section-count">{{ agentStates.length }}</span>
          </div>
          <button
            v-for="agent in visibleAgents"
            :key="agent.id"
            class="agent-row"
            :class="{ active: selectedAgentId === agent.id }"
            @click="focusAgent(agent.id)"
          >
            <span class="mini-avatar">
              <img :src="agent.avatarUrl" :alt="agent.displayName" loading="lazy" />
            </span>
            <span class="agent-row-name">{{ agent.displayName }}</span>
            <span class="agent-row-funnel">{{ agent.policyLabel }}</span>
          </button>
        </div>

        <div class="inspector-section event-feed">
          <div class="section-head">
            <span class="section-title">LIVE SALES EVENTS</span>
            <span class="section-count">{{ eventFeed.length }}</span>
          </div>
          <div v-for="event in visibleEvents" :key="event.id" class="event-item">
            <span class="event-time">{{ event.time }}</span>
            <strong>{{ event.agentName }} · {{ event.action }}</strong>
            <p>{{ event.message }}</p>
            <p v-if="event.dialogue" class="event-dialogue">{{ event.dialogue }}</p>
            <p v-if="event.reason" class="event-reason">{{ event.reason }}</p>
            <span class="event-tag">{{ event.channel }} · {{ event.policy || event.funnel }}</span>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import * as THREE from 'three'
import { chatWithSimulationAgent, getSimulationConfigRealtime, getSimulationProfilesRealtime } from '../api/simulation'

const props = defineProps({
  simulationId: String,
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'add-log', 'update-status'])

const CHANNELS = [
  {
    id: 'official',
    label: '공식 디지털',
    role: '상품 정보를 공식 언어로 확인하는 가입 홈페이지와 앱 접점',
    inside: '보장표, 약관 요약, 보험료 계산, 개인정보 고지, 전자청약 화면을 확인합니다.',
    outcome: '정보가 명확하면 신뢰와 가입의향이 오르고, 조건이 모호하면 저장만 하고 이탈합니다.',
    failure: '보험료 예시, 면책/감액 조건, 데이터 활용 고지가 흐리면 가입 직전 보류가 발생합니다.',
    x: -420,
    z: -330,
    width: 96,
    depth: 70,
    color: '#2563EB',
    detail: '상품 설명, 약관 요약, 청구 UX, 개인정보 고지를 확인하는 공식 접점입니다.',
    signals: ['약관 요약', 'FAQ', '앱 가입', '청구 UX'],
    actions: ['상품 메시지 확인', '보장 요약 비교', '청구 UX 탐색'],
    effect: { awareness: 8, trust: 4, intent: 2, privacy: -1, price: 1 }
  },
  {
    id: 'advisor',
    label: '설계사/GA',
    role: '설계사와 GA가 개인 상황에 맞춰 반론을 처리하는 상담 접점',
    inside: '기존 보험 중복, 가족 보장 공백, 갱신 보험료, 전환 손익을 상담합니다.',
    outcome: '설명이 납득되면 상담 단계로 진입하고, 과장으로 보이면 신뢰가 떨어집니다.',
    failure: '기존 계약 해지 손실이나 월 보험료 부담을 해결하지 못하면 체결이 지연됩니다.',
    x: 420,
    z: -330,
    width: 96,
    depth: 72,
    color: '#7C3AED',
    detail: '설계사와 GA가 가족 보장, 기존 계약 중복, 전환 리스크를 설명하는 상담 채널입니다.',
    signals: ['가족 보장', '반론 처리', '전환 상담', '설계사 신뢰'],
    actions: ['상담 스크립트 검토', '가족 보장 설계', '반론 처리'],
    effect: { awareness: 4, trust: 6, intent: 7, privacy: 0, price: -1 }
  },
  {
    id: 'community',
    label: '커뮤니티',
    role: '소비자가 실제 후기와 약관 캡처를 검증하는 비공식 여론 접점',
    inside: '보험료 인증, 청구 후기, 약관 예외, 광고성 글 여부를 서로 검증합니다.',
    outcome: '긍정 후기는 신뢰를 보강하지만, 부정 사례는 가격저항과 개인정보 우려를 키웁니다.',
    failure: '후기 불신, 청구 거절 사례, 개인정보 이슈가 커지면 가입 보류가 확산됩니다.',
    x: -430,
    z: 330,
    width: 112,
    depth: 82,
    color: '#D97706',
    detail: '맘카페, 직장인/재테크 커뮤니티에서 보험료와 청구 후기를 검증하는 공간입니다.',
    signals: ['후기 검증', '보험료 비교', '약관 캡처', '불신 확산'],
    actions: ['보험료 반응 공유', '후기 검증', '약관 논쟁'],
    effect: { awareness: 5, trust: -1, intent: -1, privacy: 3, price: 4 }
  },
  {
    id: 'media',
    label: '미디어/인플루언서',
    role: '출시 프레임과 비교 콘텐츠가 시장 인지를 키우는 확산 접점',
    inside: '기사, 숏폼, 전문가 비교표, 댓글 반응을 통해 상품 이미지를 형성합니다.',
    outcome: '인지도는 빠르게 오르지만, 논란도 같이 커질 수 있습니다.',
    failure: '과장 광고 프레임이나 경쟁상품 비교 열세가 보이면 상담 전환이 약해집니다.',
    x: 430,
    z: 340,
    width: 112,
    depth: 82,
    color: '#DC2626',
    detail: '기자, 인플루언서, 경제 논객이 출시 프레임과 논란을 증폭시키는 채널입니다.',
    signals: ['비교 콘텐츠', '전문가 해설', '기사화', '바이럴'],
    actions: ['출시 기사 확인', '비교 콘텐츠 확산', '전문가 해설 반응'],
    effect: { awareness: 9, trust: 1, intent: 2, privacy: 1, price: 1 }
  },
  {
    id: 'consult',
    label: '상담/가입',
    role: '견적과 특약을 조정하고 실제 가입 여부를 결정하는 전환 접점',
    inside: '보험료 견적, 가입 조건, 특약 조정, 전자청약 마지막 확인을 진행합니다.',
    outcome: '신뢰와 의향이 충분하면 가입이 발생하고, 부담 요인이 남으면 장바구니처럼 보류됩니다.',
    failure: '월 납입액, 기존 보험 중복, 개인정보 동의 범위가 마지막 이탈 이유가 됩니다.',
    x: 0,
    z: 0,
    width: 96,
    depth: 76,
    color: '#059669',
    detail: '견적 요청, 가입 조건 확인, 특약 조정이 발생하는 전환 지점입니다.',
    signals: ['견적', '가입 조건', '특약 조정', '전환 판단'],
    actions: ['견적 요청', '가입 조건 확인', '가입 의향 형성'],
    effect: { awareness: 3, trust: 4, intent: 9, privacy: 0, price: -2 }
  },
  {
    id: 'service',
    label: '유지/청구',
    role: '가입 후 보장 확인, 청구 경험, 갱신 보험료를 관리하는 유지 접점',
    inside: '청구 가능성 문의, 보장 내역 재확인, 갱신 안내, 해지/전환 상담이 일어납니다.',
    outcome: '청구가 쉽고 보장이 납득되면 유지, 불만이 커지면 해지나 전환으로 이동합니다.',
    failure: '청구 지연, 갱신 보험료 상승, 데이터 연동 불신이 유지 실패의 핵심입니다.',
    x: 0,
    z: -560,
    width: 120,
    depth: 74,
    color: '#0891B2',
    detail: '가입 이후 보장 확인, 청구 문의, 보험료 갱신, 해지/전환 신호를 추적하는 사후 접점입니다.',
    signals: ['청구 문의', '보장 재확인', '갱신 보험료', '해지/전환'],
    actions: ['보장 내역 재확인', '청구 가능성 문의', '보험료 갱신 안내 확인'],
    effect: { awareness: 1, trust: 3, intent: 0, privacy: 0, price: 2 }
  }
]

const FUNNEL_STAGES = ['인지', '관심', '비교', '상담', '가입']
const POLICY_LABELS = {
  none: '미가입',
  prospect: '검토중',
  subscribed: '가입',
  retained: '유지',
  switched: '전환',
  cancelled: '해지'
}
const ROLE_COLORS = {
  소비자: '#0F766E',
  설계사: '#7C3AED',
  보험사: '#B91C1C',
  커뮤니티: '#D97706',
  인플루언서: '#2563EB',
  일반: '#475569'
}
const speedOptions = [0.5, 1, 2, 4]
const targetYearOptions = [1, 5, 10]
const WEEKS_PER_YEAR = 52
const DEFAULT_TARGET_YEARS = 10
const WORLD_SIZE = 2200
const WORLD_HALF = WORLD_SIZE / 2
const AVATAR_STYLE = 'open-peeps'
const AVATAR_API_BASE = `https://api.dicebear.com/9.x/${AVATAR_STYLE}/svg`
const KOREAN_NAME_POOL = [
  '박민영', '이민호', '김서연', '정현우', '최지은', '한도윤', '오수진', '강민재',
  '윤하늘', '장유진', '임태준', '신가은', '서지훈', '문소라', '배준호', '권나윤',
  '조은비', '류성민', '홍지아', '남기훈', '유다은', '안재원', '백세희', '전우진',
  '차예린', '송민규', '심지호', '노윤서', '하준영', '구혜린'
]
const COMMON_KOREAN_SURNAMES = new Set(['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '홍', '전', '문', '배', '남', '유', '차', '구', '심', '노'])
const SEGMENTS = [
  '2030 직장인', '자녀가구', '4050 건강관리층', '은퇴준비층',
  '보험 불신층', '설계사 채널', '커뮤니티 검증층', '미디어 관찰층'
]

const sceneHost = ref(null)
const chatLogRef = ref(null)
const agentStates = ref([])
const eventFeed = ref([])
const selectedAgentId = ref(null)
const selectedChannelId = ref('consult')
const profileSource = ref('profiles loading')
const productName = ref('')
const isRunning = ref(true)
const speed = ref(1)
const profilesLoadedFromApi = ref(false)
const currentRound = ref(0)
const targetYears = ref(DEFAULT_TARGET_YEARS)
const simulationStartYear = ref(2026)
const weeksPerYear = ref(WEEKS_PER_YEAR)
const chatDraft = ref('')
const chatBusy = ref(false)
const isPlayerMode = ref(false)

const metrics = reactive({
  awareness: 0,
  trust: 0,
  purchaseIntent: 0,
  privacyConcern: 0,
  priceResistance: 0,
  consultRequests: 0,
  subscribed: 0,
  retained: 0,
  switched: 0,
  cancelled: 0
})

const channelStats = reactive(
  CHANNELS.reduce((acc, channel) => {
    acc[channel.id] = { visits: 0, conversations: 0, blocks: 0, conversions: 0 }
    return acc
  }, {})
)

let scene
let camera
let renderer
let resizeObserver
let animationFrameId = null
let decisionTimer = null
let tickCounter = 0
let clock
let raycaster
let pointer
let ambientLight
let keyLight
let agentPickTargets = []
let channelPickTargets = []
let playerMesh = null
let roamingTerrain = null
let roamingGrid = null
const activeKeys = new Set()
const agentMeshes = new Map()
const cameraTarget = new THREE.Vector3(0, 0, 0)
const orbit = {
  yaw: -0.7,
  pitch: 0.68,
  radius: 620
}
const player = reactive({
  x: 0,
  y: 2.05,
  z: 115,
  yaw: Math.PI,
  pitch: -0.04,
  speed: 13,
  moveTargetX: null,
  moveTargetZ: null
})
const pointerState = {
  down: false,
  moved: false,
  button: 0,
  x: 0,
  y: 0
}
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
const groundPoint = new THREE.Vector3()
const cameraPanForward = new THREE.Vector3()
const cameraPanRight = new THREE.Vector3()
const worldUp = new THREE.Vector3(0, 1, 0)

const productDisplayName = computed(() => {
  if (productName.value) return productName.value
  const source = props.projectData?.simulation_requirement || ''
  const quoted = source.match(/['"‘“]([^'"’”]+)['"’”]/)
  if (quoted?.[1]) return quoted[1]
  return '삼성생명 보험 신상품'
})

const kpiCards = computed(() => [
  { label: '현재 주차', value: currentCalendarShortLabel.value },
  { label: '신뢰', value: `${Math.round(metrics.trust)}점` },
  { label: '가입', value: `${metrics.subscribed}명` },
  { label: '유지', value: `${metrics.retained}명` },
  { label: '전환', value: `${metrics.switched}명` },
  { label: '해지', value: `${metrics.cancelled}명` },
  { label: '상담', value: `${metrics.consultRequests}건` },
  { label: '가격저항', value: `${Math.round(metrics.priceResistance)}%` }
])

const selectedAgent = computed(() => {
  return agentStates.value.find(agent => agent.id === selectedAgentId.value) || null
})
const selectedChannel = computed(() => CHANNELS.find(channel => channel.id === selectedChannelId.value) || CHANNELS[0])

const visibleAgents = computed(() => agentStates.value.slice(0, 48))
const visibleEvents = computed(() => eventFeed.value.slice(0, 12))
const totalVisits = computed(() => {
  return CHANNELS.reduce((sum, channel) => sum + (channelStats[channel.id]?.visits || 0), 0)
})
const maxRounds = computed(() => Math.max(weeksPerYear.value * targetYears.value, weeksPerYear.value))
const currentWeekIndex = computed(() => Math.min(currentRound.value, maxRounds.value - 1))
const currentYearIndex = computed(() => Math.floor(currentWeekIndex.value / weeksPerYear.value))
const currentYear = computed(() => simulationStartYear.value + currentYearIndex.value)
const weekOfYear = computed(() => (currentWeekIndex.value % weeksPerYear.value) + 1)
const currentMonth = computed(() => Math.min(12, Math.floor((weekOfYear.value - 1) / (weeksPerYear.value / 12)) + 1))
const currentWeekOfMonth = computed(() => Math.floor(((weekOfYear.value - 1) % (weeksPerYear.value / 12)) + 1))
const currentCalendarLabel = computed(() => {
  return `${currentYear.value}년 ${currentMonth.value}월 ${currentWeekOfMonth.value}째주 · ${weekOfYear.value}/${weeksPerYear.value}주`
})
const currentCalendarShortLabel = computed(() => {
  return `${currentMonth.value}월 ${currentWeekOfMonth.value}주`
})
const currentYearLabel = computed(() => `${targetYears.value}년 시뮬레이션 · ${currentYear.value}년 ${weekOfYear.value}주차`)
const playerPositionLabel = computed(() => `X ${Math.round(player.x)} · Z ${Math.round(player.z)}`)
const timelineProgress = computed(() => {
  if (!maxRounds.value) return 0
  return clamp(((currentRound.value + 1) / maxRounds.value) * 100, 0, 100)
})
const simulationComplete = computed(() => currentRound.value >= maxRounds.value - 1)
const selectedChannelAgents = computed(() => {
  if (!selectedChannel.value) return []
  return agentStates.value.filter(agent => agent.targetChannelId === selectedChannel.value.id)
})
const selectedChannelEvents = computed(() => {
  if (!selectedChannel.value) return []
  return eventFeed.value.filter(event => event.channel === selectedChannel.value.label)
})
const selectedAgentHistory = computed(() => {
  return selectedAgent.value?.history || []
})
const resultSummary = computed(() => {
  const total = Math.max(agentStates.value.length, 1)
  const subscribedRate = Math.round((metrics.subscribed / total) * 100)
  const retainedRate = Math.round((metrics.retained / total) * 100)
  const churnRate = Math.round(((metrics.cancelled + metrics.switched) / total) * 100)
  const bestChannel = CHANNELS.reduce((best, channel) => {
    const visits = channelStats[channel.id]?.visits || 0
    return visits > best.visits ? { label: channel.label, visits } : best
  }, { label: '-', visits: -1 })
  const dominantRisk = metrics.priceResistance >= metrics.privacyConcern
    ? '보험료/보장 체감'
    : '개인정보/데이터 연동'
  const recommendations = [
    metrics.priceResistance > 58 ? '보험료 부담을 낮추는 가입 예시와 기존 보험 중복 제거 메시지를 강화' : '가격 저항은 관리 가능하므로 보장 실효성 증거를 더 전면화',
    metrics.privacyConcern > 52 ? '개인정보 연동 범위, 철회 방법, 청구 데이터 사용 목적을 별도 화면으로 분리' : '개인정보 이슈는 FAQ와 약관 요약 수준에서 유지 가능',
    churnRate > 20 ? '가입 후 3개월 이내 청구 UX와 유지 상담 접점을 강화' : '가입 후 유지 흐름은 양호하므로 후기와 청구 성공 사례를 축적'
  ]
  return {
    headline: `${targetYears.value}년 추적 결과, 가입률 ${subscribedRate}% / 유지율 ${retainedRate}% / 이탈 ${churnRate}% 흐름입니다. 핵심 리스크는 ${dominantRisk}입니다.`,
    items: [
      { label: '가입률', value: `${subscribedRate}%` },
      { label: '유지율', value: `${retainedRate}%` },
      { label: '이탈', value: `${churnRate}%` },
      { label: '주요 채널', value: bestChannel.label }
    ],
    recommendations
  }
})

const addLog = (message) => {
  emit('add-log', message)
}

const clamp = (value, min = 0, max = 100) => Math.min(max, Math.max(min, value))
const randomBetween = (min, max) => min + Math.random() * (max - min)
const sample = (items) => items[Math.floor(Math.random() * items.length)]
const stablePick = (items, idx, salt = 0) => items[Math.abs((idx * 17 + salt * 31) % items.length)]

const resolveHumanName = (profile, idx) => {
  const candidate = profile.name || profile.realname || profile.display_name
  if (candidate && /^[가-힣]{2,5}$/.test(candidate.trim()) && COMMON_KOREAN_SURNAMES.has(candidate.trim().slice(0, 1))) {
    return candidate.trim()
  }
  return stablePick(KOREAN_NAME_POOL, idx, 3)
}

const BROKEN_PERSONA_PATTERNS = [
  '기관 기본 정보',
  '정식 명칭',
  '비공식 집단 계정',
  '특정 회사나 판매채널에 속하지 않은',
  '그래프 엔티티',
  '원천 엔티티',
  '집단 계정'
]

const looksLikeInstitutionalPersona = (text = '') => {
  return BROKEN_PERSONA_PATTERNS.some(pattern => text.includes(pattern))
}

const stripBrokenPersona = (text = '') => {
  return text
    .replace(/기관 기본 정보[:：]?.*/g, '')
    .replace(/정식 명칭은[^.。]*[.。]?/g, '')
    .replace(/특정 회사나 판매채널에 속하지 않은[^.。]*[.。]?/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

const buildHumanPersona = (displayName, idx, role, sourceText = '') => {
  const salesTone = [
    '초기 문의는 많은데 실제 가입은 보험료와 기존 보험 중복에서 많이 걸러진다고 본다',
    '건강보험 관심은 높아졌지만 청구 경험과 갱신 보험료 설명이 부족하면 쉽게 보류한다고 느낀다',
    '주변 반응은 나쁘지 않지만 약관 예외와 개인정보 연동 조건을 확인하기 전에는 확신하지 않는다',
    '상담 현장에서는 암/심혈관 보장에는 반응이 있고, 2030은 가격에 민감하며 4050은 보장 공백에 민감하다고 본다'
  ]
  const personalBases = [
    '서울 서부권에 사는 30대 직장인으로 실손보험은 있지만 새 건강보험은 보험료 대비 실제 지급 가능성을 따져본다',
    '수도권 맞벌이 가구 구성원으로 가족 의료비와 기존 계약 해지 손실을 함께 비교한다',
    '보험 커뮤니티 후기를 자주 확인하는 소비자로 광고 문구보다 실제 청구 사례와 갱신 보험료를 더 믿는다',
    '건강검진 결과와 가족력을 계기로 건강보험을 검토하지만 개인정보 연동에는 선을 긋는 편이다'
  ]
  const sellerBases = [
    'GA 소속 설계사로 고객이 보험료, 기존 계약 중복, 청구 편의성을 물을 때 가입 전환이 생긴다고 본다',
    '전속 설계사 관점에서 신상품은 상담 유입은 만들지만 체결은 가족 보장 공백과 갱신 보험료 설명에 달려 있다고 본다',
    '보험 상담 경험이 있는 현장형 인물로 과장된 장점보다 해지율을 낮추는 설명을 중시한다'
  ]
  const marketerBases = [
    '보험사 상품/마케팅 담당자로 출시 초기 문의량, 상담 전환, 부정 이슈를 함께 보며 판매 흐름을 판단한다',
    '상품 운영 담당자로 약관 요약, FAQ, 개인정보 고지, 청구 UX 반응을 보고 판매 장애물을 조정한다'
  ]
  const mediaBases = [
    '보험 전문 콘텐츠를 보는 미디어 관찰자로 출시 기사, 커뮤니티 반응, 전문가 비교 콘텐츠를 종합해 시장 반응을 읽는다',
    '건강관리 콘텐츠를 다루는 인플루언서형 인물로 앱 연동 리워드와 개인정보 우려에 대한 댓글 반응을 민감하게 본다'
  ]
  const pool = role === '설계사'
    ? sellerBases
    : role === '보험사'
      ? marketerBases
      : role === '인플루언서'
        ? mediaBases
        : personalBases
  const base = stablePick(pool, idx, 9)
  const market = stablePick(salesTone, idx, 11)
  const sourceHint = stripBrokenPersona(sourceText)
  return `${displayName}은 ${base}. ${market}. ${sourceHint ? `참고 배경은 ${sourceHint.slice(0, 80)}이다.` : ''}`.trim()
}

const normalizeHumanProfile = (profile, displayName, idx, role) => {
  const rawBio = `${profile.bio || ''}`.trim()
  const rawPersona = `${profile.persona || ''}`.trim()
  const sourceText = `${rawBio} ${rawPersona}`.replace(/\s+/g, ' ').trim()
  const shouldHumanize = !sourceText || looksLikeInstitutionalPersona(sourceText) || sourceText.length > 420
  const persona = shouldHumanize
    ? buildHumanPersona(displayName, idx, role, sourceText)
    : stripBrokenPersona(rawPersona || rawBio)
  const bio = shouldHumanize
    ? persona
    : stripBrokenPersona(rawBio || rawPersona)
  return {
    bio,
    persona,
    raw_bio: rawBio,
    raw_persona: rawPersona
  }
}

const buildAvatarUrl = (seed, idx) => {
  const params = new URLSearchParams({
    seed: `${seed}-${idx}`,
    radius: '8',
    size: '96',
    backgroundType: idx % 2 === 0 ? 'solid' : 'gradientLinear',
    backgroundColor: ['e0f2fe', 'dcfce7', 'fef3c7', 'fee2e2', 'ede9fe', 'f1f5f9'][idx % 6]
  })
  return `${AVATAR_API_BASE}?${params.toString()}`
}

const buildVisualProfile = (idx, role) => {
  const skin = ['#F2C9A5', '#D9A066', '#A96F45', '#8D5524', '#F6D7B0', '#C68642']
  const hair = ['#111827', '#3F2A1D', '#7C2D12', '#6B7280', '#1F2937']
  const outfit = [ROLE_COLORS[role] || ROLE_COLORS['일반'], '#0E7490', '#BE123C', '#4338CA', '#047857', '#A16207']
  return {
    skin: stablePick(skin, idx, 1),
    hair: stablePick(hair, idx, 2),
    outfit: stablePick(outfit, idx, 4),
    height: 0.96 + ((idx % 7) * 0.04),
    width: 0.92 + ((idx % 5) * 0.05),
    hairStyle: idx % 4,
    accessory: idx % 6 === 0,
    stance: idx % 3
  }
}

const buildSegment = (profile, idx, role) => {
  if (role === '설계사') return '설계사 채널'
  if (role === '보험사') return '보험사 운영'
  if (role === '커뮤니티') return '커뮤니티 검증층'
  if (role === '인플루언서') return '미디어 관찰층'
  const text = `${profile.bio || ''} ${profile.persona || ''}`
  if (text.includes('자녀') || text.includes('가족') || text.includes('부모')) return '자녀가구'
  if (text.includes('4050') || text.includes('암') || text.includes('심혈관')) return '4050 건강관리층'
  return stablePick(SEGMENTS, idx, 5)
}

const inferRole = (profile) => {
  const text = `${profile.username || ''} ${profile.name || ''} ${profile.profession || ''} ${profile.bio || ''} ${profile.persona || ''}`.toLowerCase()
  if (text.includes('커뮤니티 이용자') || text.includes('소비자') || text.includes('직장인') || text.includes('부모') || text.includes('고객')) return '소비자'
  if (text.includes('설계사') || text.includes(' ga ') || text.includes('ga 소속') || text.includes('advisor')) return '설계사'
  if (text.includes('보험사') || text.includes('삼성생명') || text.includes('회사') || text.includes('마케팅')) return '보험사'
  if (text.includes('커뮤니티') || text.includes('카페') || text.includes('운영')) return '커뮤니티'
  if (text.includes('인플루언서') || text.includes('기자') || text.includes('미디어') || text.includes('블로거')) return '인플루언서'
  return '일반'
}

const normalizeProfile = (profile, idx) => {
  const displayName = resolveHumanName(profile, idx)
  const sourceName = profile.entity_name || profile.source_entity_name || profile.username || profile.name || `Agent ${idx + 1}`
  const role = inferRole(profile)
  const humanProfile = normalizeHumanProfile(profile, displayName, idx, role)
  return {
    ...profile,
    ...humanProfile,
    user_id: Number(profile.user_id ?? idx),
    username: profile.username || sourceName,
    name: displayName,
    source_name: sourceName,
    role
  }
}

const buildGraphFallbackProfiles = () => {
  const nodes = props.graphData?.nodes || props.graphData?.data?.nodes || []
  return nodes.slice(0, 80).map((node, idx) => normalizeProfile({
    user_id: idx,
    username: node.label || node.name || node.id || `Graph Agent ${idx + 1}`,
    name: node.label || node.name || `Graph Agent ${idx + 1}`,
    profession: node.type || node.entity_type || '그래프 엔티티',
    bio: node.summary || node.description || '그래프에서 생성된 보험 시뮬레이션 참여자',
    persona: node.description || node.summary || ''
  }, idx))
}

const buildSeedProfiles = () => {
  const seeds = [
    ['박민영', '소비자', '서울 마포에 사는 32세 직장인. 실손보험은 보유했지만 건강보험 신상품의 암/심혈관 보장과 월 보험료를 꼼꼼히 비교한다. 가입 전 커뮤니티 후기와 약관 요약을 반드시 확인한다.'],
    ['이민호', '소비자', '경기 성남의 41세 맞벌이 가장. 자녀 의료비와 가족 보장을 중시하지만 보험료 인상에는 민감하다. 설계사 상담을 듣고도 온라인 비교표로 다시 검증한다.'],
    ['정수현', '설계사', 'GA 소속 12년차 설계사. 기존 고객의 보장 공백과 신상품 전환 가능성을 따져 상담한다. 과장된 판매보다 해지율을 낮추는 유지 전략을 선호한다.'],
    ['김도윤', '설계사', '삼성생명 전속 설계사 팀장. 라이프핏 건강보험의 핵심 보장, 면책/감액 조건, 청구 UX를 고객 눈높이에 맞춰 설명하려고 한다.'],
    ['최지은', '보험사', '상품 마케팅 실무자. 출시 메시지, 약관 요약, 개인정보 활용 안내, FAQ 반응을 모니터링하며 부정 이슈가 커지면 설명자료를 조정한다.'],
    ['오수진', '커뮤니티', '맘카페 운영진. 가족 보장, 보험료 부담, 청구 후기 제보를 모아 회원들에게 공유한다. 광고성 글과 실제 경험담을 강하게 구분한다.'],
    ['강민재', '커뮤니티', '직장인 재테크 커뮤니티 회원. 월 납입액 대비 보장 실효성과 기존 보험 중복을 숫자로 비교한다. 약관 캡처와 비교표를 자주 올린다.'],
    ['윤하늘', '인플루언서', '건강관리 콘텐츠 크리에이터. 앱 연동 리워드, 건강 데이터 활용 조건, 개인정보 우려를 쉽게 설명하고 댓글 반응을 빠르게 반영한다.'],
    ['장유진', '인플루언서', '보험 전문 기자. 출시 초기 홍보 프레임보다 소비자 보호, 약관 복잡성, 보험료 부담 이슈를 기사화한다.'],
    ['임태준', '소비자', '47세 자영업자. 암과 뇌혈관 보장을 중점적으로 보며, 갱신형 보험료와 청구 거절 가능성을 크게 걱정한다.'],
    ['신가은', '소비자', '기존 건강보험 보유자. 새 상품 가입보다 갈아타기 손익과 기존 계약 해지 리스크를 먼저 따진다.'],
    ['서지훈', '소비자', '보험 불신이 큰 29세 개발자. 개인정보 연동, 약관 예외, 실제 지급 사례가 명확하지 않으면 가입하지 않는다.']
  ]
  return seeds.map(([name, profession, bio], idx) => normalizeProfile({
    user_id: idx,
    username: `seed_agent_${idx + 1}`,
    name,
    profession,
    bio,
    persona: bio
  }, idx))
}

const loadConfig = async () => {
  if (!props.simulationId) return
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    const config = res?.data?.config || res?.data
    const source = config?.simulation_requirement || props.projectData?.simulation_requirement || ''
    const quoted = source.match(/['"‘“]([^'"’”]+)['"’”]/)
    if (quoted?.[1]) productName.value = quoted[1]
    const timeConfig = config?.time_config || {}
    simulationStartYear.value = Number(timeConfig.start_year || 2026)
    weeksPerYear.value = Number(timeConfig.weeks_per_year || WEEKS_PER_YEAR)
    const configuredYears = Number(timeConfig.target_years || timeConfig.max_years || DEFAULT_TARGET_YEARS)
    if (targetYearOptions.includes(configuredYears)) targetYears.value = configuredYears
  } catch (error) {
    addLog(`보험 게임 설정 로드 실패: ${error.message}`)
  }
}

const loadProfiles = async () => {
  let profiles = []
  if (props.simulationId) {
    try {
      const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
      profiles = (res?.data?.profiles || []).map(normalizeProfile)
      profilesLoadedFromApi.value = profiles.length > 0
      if (profiles.length > 0) {
        profileSource.value = `profile ${profiles.length}`
        addLog(`보험 게임 공간에 Agent ${profiles.length}명을 배치했습니다`)
      }
    } catch (error) {
      addLog(`Agent 프로필 로드 실패: ${error.message}`)
    }
  }

  if (!profiles.length) {
    profiles = buildGraphFallbackProfiles()
    if (profiles.length) {
      profileSource.value = `graph ${profiles.length}`
      addLog(`프로필 파일 대신 그래프 엔티티 ${profiles.length}개를 게임 캐릭터로 배치했습니다`)
    }
  }

  if (!profiles.length) {
    profiles = buildSeedProfiles()
    profileSource.value = 'seed agents'
    addLog('표시 가능한 프로필이 없어 보험 게임용 기본 Agent를 배치했습니다')
  }

  initializeAgentStates(profiles)
}

const initializeAgentStates = (profiles) => {
  agentStates.value = profiles.map((profile, idx) => {
    const role = profile.role || inferRole(profile)
    const angle = (idx / Math.max(profiles.length, 1)) * Math.PI * 2
    const radius = 70 + (idx % 18) * 7
    const displayName = profile.name || resolveHumanName(profile, idx)
    const segment = buildSegment(profile, idx, role)
    const agent = {
      id: idx,
      profile,
      displayName,
      initial: displayName.slice(0, 1).toUpperCase(),
      role,
      color: ROLE_COLORS[role] || ROLE_COLORS['일반'],
      avatarUrl: buildAvatarUrl(displayName, idx),
      visual: buildVisualProfile(idx, role),
      segment,
      x: Math.cos(angle) * radius,
      z: Math.sin(angle) * radius,
      targetX: 0,
      targetZ: 0,
      targetChannelId: null,
      speed: randomBetween(18, 34),
      awareness: randomBetween(12, 32),
      trust: randomBetween(36, 64),
      intent: randomBetween(4, 18),
      privacyConcern: randomBetween(18, 46),
      priceResistance: randomBetween(22, 56),
      funnelIndex: 0,
      funnel: FUNNEL_STAGES[0],
      policyState: 'none',
      policyLabel: POLICY_LABELS.none,
      policyProduct: null,
      subscribedRound: null,
      tenureWeeks: 0,
      lastAction: '대기',
      history: [],
      chatMessages: [
        {
          id: `hello-${idx}`,
          role: 'assistant',
          text: `${displayName}입니다. ${segment} 관점에서 ${productDisplayName.value} 가입 판단을 이야기할 수 있어요.`
        }
      ]
    }
    pickNextTarget(agent)
    return agent
  })
  currentRound.value = 0
  selectedAgentId.value = agentStates.value[0]?.id ?? null
  updateMetrics()
}

const chooseChannelForAgent = (agent) => {
  if (['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)) {
    const postPurchaseChannels = CHANNELS.filter(channel => ['service', 'consult', 'community', 'official'].includes(channel.id))
    const weights = postPurchaseChannels.map(channel => {
      let weight = 1
      if (channel.id === 'service') weight += 7
      if (agent.policyState === 'cancelled' && channel.id === 'community') weight += 4
      if (agent.policyState === 'switched' && channel.id === 'consult') weight += 4
      if (agent.priceResistance > 68 && ['community', 'consult'].includes(channel.id)) weight += 3
      if (agent.trust > 66 && channel.id === 'official') weight += 2
      return { channel, weight }
    })
    const total = weights.reduce((sum, item) => sum + item.weight, 0)
    let roll = Math.random() * total
    for (const item of weights) {
      roll -= item.weight
      if (roll <= 0) return item.channel
    }
    return sample(postPurchaseChannels)
  }

  const weights = CHANNELS.map(channel => {
    let weight = 1
    if (agent.role === '설계사' && ['advisor', 'consult', 'official'].includes(channel.id)) weight += 4
    if (agent.role === '보험사' && ['official', 'media', 'advisor'].includes(channel.id)) weight += 4
    if (agent.role === '커뮤니티' && ['community', 'media'].includes(channel.id)) weight += 5
    if (agent.role === '인플루언서' && ['media', 'community'].includes(channel.id)) weight += 5
    if (agent.role === '소비자' && ['community', 'official', 'advisor', 'consult'].includes(channel.id)) weight += 2
    if (agent.intent > 48 && channel.id === 'consult') weight += 5
    if (agent.priceResistance > 62 && channel.id === 'community') weight += 4
    if (channel.id === 'service') weight = 0.2
    return { channel, weight }
  })
  const total = weights.reduce((sum, item) => sum + item.weight, 0)
  let roll = Math.random() * total
  for (const item of weights) {
    roll -= item.weight
    if (roll <= 0) return item.channel
  }
  return sample(CHANNELS)
}

const pickNextTarget = (agent) => {
  if (['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)) {
    const channel = chooseChannelForAgent(agent)
    agent.targetChannelId = channel.id
    agent.targetX = channel.x + randomBetween(-channel.width / 2 + 8, channel.width / 2 - 8)
    agent.targetZ = channel.z + randomBetween(-channel.depth / 2 + 8, channel.depth / 2 - 8)
    return
  }

  if (Math.random() < 0.78) {
    const channel = chooseChannelForAgent(agent)
    agent.targetChannelId = channel.id
    agent.targetX = channel.x + randomBetween(-channel.width / 2 + 8, channel.width / 2 - 8)
    agent.targetZ = channel.z + randomBetween(-channel.depth / 2 + 8, channel.depth / 2 - 8)
  } else {
    agent.targetChannelId = null
    agent.targetX = randomBetween(-820, 820)
    agent.targetZ = randomBetween(-760, 760)
  }
}

const advanceFunnel = (agent) => {
  if (['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)) return
  let nextIndex = 0
  if (agent.awareness > 42) nextIndex = 1
  if (agent.awareness > 55 && agent.trust > 42) nextIndex = 2
  if (agent.intent > 42 && agent.trust > 46) nextIndex = 3
  if (agent.intent > 66 && agent.trust > 55 && agent.priceResistance < 64) nextIndex = 4
  agent.funnelIndex = Math.max(agent.funnelIndex, nextIndex)
  agent.funnel = FUNNEL_STAGES[agent.funnelIndex]
  if (agent.funnelIndex >= 4 && agent.policyState === 'none') {
    agent.policyState = 'subscribed'
    agent.policyLabel = POLICY_LABELS.subscribed
    agent.policyProduct = productDisplayName.value
    agent.subscribedRound = currentRound.value
    agent.tenureWeeks = 0
    agent.lastAction = `${productDisplayName.value} 가입`
  } else if (agent.funnelIndex >= 2 && agent.policyState === 'none') {
    agent.policyState = 'prospect'
    agent.policyLabel = POLICY_LABELS.prospect
  }
}

const updatePolicyTenure = (agent) => {
  if (agent.subscribedRound === null) {
    agent.tenureWeeks = 0
    return
  }
  agent.tenureWeeks = Math.max(0, currentRound.value - agent.subscribedRound)
}

const getPrimaryBarrier = (agent) => {
  if (agent.priceResistance >= 68) return '월 보험료가 기존 보험 대비 높게 느껴짐'
  if (agent.privacyConcern >= 64) return '건강 데이터와 개인정보 활용 범위가 불분명함'
  if (agent.trust < 42) return '약관 예외와 실제 지급 사례를 아직 믿기 어려움'
  if (agent.intent < 38) return '당장 의료비 리스크를 크게 체감하지 못함'
  return '기존 계약과 보장 중복 여부를 더 확인해야 함'
}

const getDecisionTone = (agent) => {
  if (agent.policyState === 'subscribed') return '가입 완료'
  if (agent.policyState === 'retained') return '유지'
  if (agent.policyState === 'switched') return '전환'
  if (agent.policyState === 'cancelled') return '해지'
  if (agent.policyState === 'prospect') return '검토 지속'
  return '보류'
}

const buildChannelInteraction = (agent, channel, action, before) => {
  const barrier = getPrimaryBarrier(agent)
  const decision = getDecisionTone(agent)
  const changedPolicy = before.policyState !== agent.policyState
  const trustDelta = Math.round(agent.trust - before.trust)
  const intentDelta = Math.round(agent.intent - before.intent)
  const deltaText = `신뢰 ${trustDelta >= 0 ? '+' : ''}${trustDelta}, 의향 ${intentDelta >= 0 ? '+' : ''}${intentDelta}`
  let counterparty = channel.label
  let dialogue = ''
  let outcome = ''
  let reason = ''

  if (channel.id === 'official') {
    counterparty = '가입 홈페이지'
    dialogue = agent.policyState === 'subscribed'
      ? `"보장표와 보험료가 이 정도로 정리되면 오늘 청약까지 진행해도 되겠네요."`
      : `"보험료 계산까지는 해봤는데, ${barrier} 부분이 남아서 저장만 해둘게요."`
    outcome = agent.policyState === 'subscribed'
      ? '가입 홈페이지에서 보험료와 보장표를 확인하고 전자청약을 완료했습니다.'
      : `가입 홈페이지에서 가입 직전까지 갔지만 ${barrier} 때문에 다음 확인으로 미뤘습니다.`
    reason = '공식 정보가 신뢰를 올리지만, 숫자와 고지 문구가 부족하면 마지막 단계에서 멈춥니다.'
  } else if (channel.id === 'advisor') {
    counterparty = '설계사'
    dialogue = `"기존 보험이랑 겹치는 담보를 빼면 월 납입액이 얼마나 내려가나요?"`
    outcome = changedPolicy && agent.policyState === 'subscribed'
      ? '설계사 상담에서 기존 보험 중복을 정리한 뒤 가입 쪽으로 결론을 냈습니다.'
      : `설계사와 가족 보장과 전환 손익을 상담했지만 ${barrier} 때문에 추가 비교가 필요해졌습니다.`
    reason = '설계사 채널은 반론 처리가 강하지만, 보험료와 해지 손실 설명이 부족하면 전환이 지연됩니다.'
  } else if (channel.id === 'community') {
    counterparty = '커뮤니티 댓글'
    dialogue = `"실제 청구된 사례랑 갱신 보험료 후기를 더 보고 결정하겠습니다."`
    outcome = agent.privacyConcern > before.privacyConcern || agent.priceResistance > before.priceResistance
      ? '커뮤니티 후기 검증 과정에서 우려가 커져 가입 판단이 더 보수적으로 바뀌었습니다.'
      : '커뮤니티에서 실제 후기와 약관 캡처를 확인해 판단 근거를 보강했습니다.'
    reason = '커뮤니티는 공식 설명을 검증하는 장소라서 신뢰 보강과 불신 확산이 동시에 일어납니다.'
  } else if (channel.id === 'media') {
    counterparty = '비교 콘텐츠'
    dialogue = `"비슷한 상품과 비교했을 때 보장 차이가 숫자로 보여야 납득할 수 있겠어요."`
    outcome = '미디어/인플루언서 콘텐츠를 보고 상품 인지도는 올라갔지만, 비교 우위는 추가 확인이 필요합니다.'
    reason = '미디어는 인지를 빠르게 만들지만, 체결은 상담과 공식 견적에서 다시 검증됩니다.'
  } else if (channel.id === 'consult') {
    counterparty = '가입 상담 데스크'
    dialogue = agent.policyState === 'subscribed'
      ? `"이 조건이면 기존 보험을 유지하면서 필요한 보장만 추가하겠습니다."`
      : `"청약 버튼까지 왔는데 ${barrier} 때문에 오늘은 상담 기록만 남기겠습니다."`
    outcome = agent.policyState === 'subscribed'
      ? '상담/가입 데스크에서 견적과 특약을 확정하고 가입을 완료했습니다.'
      : `상담/가입 데스크에서 견적을 받았지만 ${barrier} 때문에 가입하지 않았습니다.`
    reason = '이 채널은 실제 전환 지점이라 작은 의문도 가입 보류로 바로 이어집니다.'
  } else if (channel.id === 'service') {
    counterparty = '유지/청구 센터'
    dialogue = agent.policyState === 'cancelled'
      ? `"청구와 데이터 연동 설명이 계속 불편해서 해지 절차를 확인하겠습니다."`
      : agent.policyState === 'switched'
        ? `"갱신 보험료가 오른다면 다른 상품으로 갈아타는 조건을 보겠습니다."`
        : `"청구가 실제로 며칠 걸리는지와 갱신 때 보험료가 어떻게 바뀌는지 알려주세요."`
    outcome = agent.policyState === 'cancelled'
      ? '유지/청구 접점에서 불만이 해소되지 않아 계약 해지로 이동했습니다.'
      : agent.policyState === 'switched'
        ? '갱신 부담과 보장 비교 때문에 경쟁상품 전환으로 이동했습니다.'
        : '가입 후 청구 가능성과 갱신 보험료를 확인하며 유지 판단을 갱신했습니다.'
    reason = '가입 이후에는 청구 경험과 갱신 안내가 유지, 전환, 해지를 가르는 핵심입니다.'
  }

  return {
    counterparty,
    dialogue,
    outcome,
    reason,
    decision,
    impact: deltaText,
    blocked: ['none', 'prospect'].includes(agent.policyState) && ['official', 'consult'].includes(channel.id),
    converted: changedPolicy && ['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)
  }
}

const resolvePostPurchaseAction = (agent, channel) => {
  updatePolicyTenure(agent)
  const highDissatisfaction = agent.priceResistance > 72 || agent.trust < 34 || agent.privacyConcern > 72
  const renewalPressure = agent.tenureWeeks > 0 && agent.tenureWeeks % 52 === 0

  if (agent.policyState === 'subscribed' && agent.tenureWeeks >= 8 && agent.trust > 58 && agent.priceResistance < 66) {
    agent.policyState = 'retained'
    agent.policyLabel = POLICY_LABELS.retained
    agent.lastAction = '유지 확정'
    return '보험 유지 확정'
  }

  if (['subscribed', 'retained'].includes(agent.policyState) && (highDissatisfaction || renewalPressure) && Math.random() < 0.32) {
    if (agent.priceResistance > agent.privacyConcern || renewalPressure) {
      agent.policyState = 'switched'
      agent.policyLabel = POLICY_LABELS.switched
      agent.intent = clamp(agent.intent - randomBetween(8, 18))
      agent.trust = clamp(agent.trust - randomBetween(4, 12))
      agent.lastAction = '경쟁상품 전환'
      return '보험료와 보장범위를 비교한 뒤 경쟁상품으로 갈아탐'
    }
    agent.policyState = 'cancelled'
    agent.policyLabel = POLICY_LABELS.cancelled
    agent.intent = clamp(agent.intent - randomBetween(14, 26))
    agent.trust = clamp(agent.trust - randomBetween(8, 18))
    agent.lastAction = '계약 해지'
    return '개인정보 연동과 약관 불신 때문에 보험 해지 상담을 진행'
  }

  const actions = {
    service: ['청구 가능성 문의', '보장 내역 재확인', '보험료 갱신 안내 확인', '건강 데이터 연동 범위 조정'],
    consult: ['기존 계약 유지 조건 재상담', '특약 조정 상담', '가족 보장 설계 재검토'],
    community: ['가입 후기를 공유', '보험료 인상 반응 확인', '청구 경험담을 검증'],
    official: ['약관 요약과 청구 절차를 다시 확인']
  }
  return sample(actions[channel.id] || channel.actions)
}

const generateAgentEvent = (agent, channel) => {
  const before = {
    policyState: agent.policyState,
    policyLabel: agent.policyLabel,
    trust: agent.trust,
    intent: agent.intent,
    privacyConcern: agent.privacyConcern,
    priceResistance: agent.priceResistance
  }
  const wasPostPurchase = ['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)
  const action = wasPostPurchase ? resolvePostPurchaseAction(agent, channel) : sample(channel.actions)
  const effect = channel.effect
  const variance = randomBetween(-2, 2)

  agent.awareness = clamp(agent.awareness + effect.awareness + variance)
  agent.trust = clamp(agent.trust + effect.trust + randomBetween(-2, 2))
  agent.intent = clamp(agent.intent + (wasPostPurchase ? 0 : effect.intent) + randomBetween(-2, 2))
  agent.privacyConcern = clamp(agent.privacyConcern + effect.privacy + randomBetween(-1, 2))
  agent.priceResistance = clamp(agent.priceResistance + effect.price + randomBetween(-1, 2))
  agent.lastAction = action
  advanceFunnel(agent)
  updatePolicyTenure(agent)

  const interaction = buildChannelInteraction(agent, channel, action, before)
  channelStats[channel.id].visits += 1
  channelStats[channel.id].conversations += 1
  if (interaction.blocked) channelStats[channel.id].blocks += 1
  if (interaction.converted) channelStats[channel.id].conversions += 1

  const event = {
    id: `${Date.now()}-${agent.id}-${Math.random().toString(16).slice(2)}`,
    time: currentCalendarLabel.value,
    agentId: agent.id,
    agentName: agent.displayName,
    channelId: channel.id,
    channel: channel.label,
    funnel: agent.funnel,
    policy: agent.policyLabel,
    beforePolicy: before.policyLabel,
    action,
    counterparty: interaction.counterparty,
    dialogue: interaction.dialogue,
    outcome: interaction.outcome,
    reason: interaction.reason,
    impact: interaction.impact,
    decision: interaction.decision,
    message: `${channel.label}에서 ${interaction.counterparty}와 ${action}. ${interaction.outcome} (${interaction.impact})`
  }
  eventFeed.value.unshift(event)
  if (eventFeed.value.length > 80) eventFeed.value.pop()
  agent.history.unshift(event)
  if (agent.history.length > 40) agent.history.pop()

  showActionBubble(agent, interaction.dialogue.replace(/[“”"]/g, '').slice(0, 28) || action)
  showChannelPulse(channel, interaction.converted ? '#10B981' : channel.color)
  updateAgentVisual(agent)
  updateMetrics()
}

const updateMetrics = () => {
  const agents = agentStates.value
  if (!agents.length) return
  const avg = (key) => agents.reduce((sum, agent) => sum + agent[key], 0) / agents.length
  metrics.awareness = avg('awareness')
  metrics.trust = avg('trust')
  metrics.purchaseIntent = avg('intent')
  metrics.privacyConcern = avg('privacyConcern')
  metrics.priceResistance = avg('priceResistance')
  metrics.consultRequests = agents.filter(agent => agent.funnelIndex >= 3).length
  metrics.subscribed = agents.filter(agent => ['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)).length
  metrics.retained = agents.filter(agent => agent.policyState === 'retained').length
  metrics.switched = agents.filter(agent => agent.policyState === 'switched').length
  metrics.cancelled = agents.filter(agent => agent.policyState === 'cancelled').length
}

const runDecisionTick = () => {
  if (!agentStates.value.length) return
  tickCounter += 1
  if (speed.value === 0.5 && tickCounter % 2 !== 0) return

  const repeats = Math.max(1, Math.floor(speed.value))
  for (let i = 0; i < repeats; i += 1) {
    if (currentRound.value >= maxRounds.value - 1) {
      isRunning.value = false
      emit('update-status', 'completed')
      addLog(`${targetYears.value}년 보험 가입 시뮬레이션이 ${currentCalendarLabel.value}에서 종료되었습니다`)
      updateMetrics()
      return
    }
    currentRound.value += 1
    agentStates.value.forEach(updatePolicyTenure)

    const activeCount = Math.max(1, Math.floor(agentStates.value.length * 0.08))
    for (let j = 0; j < activeCount; j += 1) {
      const agent = sample(agentStates.value)
      if (Math.random() < 0.55 || ['subscribed', 'retained', 'switched', 'cancelled'].includes(agent.policyState)) {
        const channel = chooseChannelForAgent(agent)
        agent.targetChannelId = channel.id
        agent.targetX = channel.x + randomBetween(-channel.width / 2 + 8, channel.width / 2 - 8)
        agent.targetZ = channel.z + randomBetween(-channel.depth / 2 + 8, channel.depth / 2 - 8)
      }
    }
  }
  updateMetrics()
}

const bootstrapInitialEvents = () => {
  agentStates.value.slice(0, Math.min(5, agentStates.value.length)).forEach(agent => {
    const channel = chooseChannelForAgent(agent)
    generateAgentEvent(agent, channel)
    agent.targetChannelId = channel.id
    agent.targetX = channel.x + randomBetween(-channel.width / 2 + 8, channel.width / 2 - 8)
    agent.targetZ = channel.z + randomBetween(-channel.depth / 2 + 8, channel.depth / 2 - 8)
  })
}

const initThree = () => {
  scene = new THREE.Scene()
  scene.background = new THREE.Color('#CFE3EC')
  scene.fog = new THREE.Fog('#CFE3EC', 720, 2600)

  camera = new THREE.PerspectiveCamera(56, 1, 0.1, 6000)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.08
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  sceneHost.value.appendChild(renderer.domElement)

  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2()
  clock = new THREE.Clock()

  ambientLight = new THREE.HemisphereLight('#FFFFFF', '#B7C6D6', 2.6)
  scene.add(ambientLight)

  keyLight = new THREE.DirectionalLight('#FFFFFF', 3.2)
  keyLight.position.set(15, 24, 12)
  keyLight.castShadow = true
  keyLight.shadow.mapSize.width = 2048
  keyLight.shadow.mapSize.height = 2048
  keyLight.shadow.camera.left = -900
  keyLight.shadow.camera.right = 900
  keyLight.shadow.camera.top = 900
  keyLight.shadow.camera.bottom = -900
  scene.add(keyLight)

  const rimLight = new THREE.DirectionalLight('#BEE3F8', 1.2)
  rimLight.position.set(-28, 18, -22)
  scene.add(rimLight)

  addSkyDome()
  buildStaticWorld()
  createPlayerMesh()
  updateCamera()

  resizeObserver = new ResizeObserver(resizeRenderer)
  resizeObserver.observe(sceneHost.value)
  resizeRenderer()
}

const addSkyDome = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 32
  canvas.height = 512
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height)
  gradient.addColorStop(0, '#A9D8F5')
  gradient.addColorStop(0.42, '#D9EEF4')
  gradient.addColorStop(0.72, '#EEF7EF')
  gradient.addColorStop(1, '#F8FAFC')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(3100, 32, 18),
    new THREE.MeshBasicMaterial({ map: texture, side: THREE.BackSide })
  )
  sky.position.y = 220
  scene.add(sky)
}

const makeDistrictFloorTexture = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 2048
  canvas.height = 2048
  const ctx = canvas.getContext('2d')
  const worldWidth = WORLD_SIZE
  const worldDepth = WORLD_SIZE
  const worldToCanvas = (x, z) => ({
    x: ((x + worldWidth / 2) / worldWidth) * canvas.width,
    y: ((worldDepth / 2 - z) / worldDepth) * canvas.height
  })
  const drawWorldRect = (x, z, width, depth, color, alpha = 1) => {
    const center = worldToCanvas(x, z)
    const pixelWidth = (width / worldWidth) * canvas.width
    const pixelHeight = (depth / worldDepth) * canvas.height
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.fillStyle = color
    ctx.fillRect(center.x - pixelWidth / 2, center.y - pixelHeight / 2, pixelWidth, pixelHeight)
    ctx.restore()
  }
  const drawWorldLine = (x1, z1, x2, z2, color, width = 6, alpha = 1) => {
    const a = worldToCanvas(x1, z1)
    const b = worldToCanvas(x2, z2)
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.strokeStyle = color
    ctx.lineWidth = width
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.stroke()
    ctx.restore()
  }

  ctx.fillStyle = '#CADCCB'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.strokeStyle = '#AFC2B7'
  ctx.lineWidth = 1
  for (let x = -WORLD_HALF; x <= WORLD_HALF; x += 5) {
    const a = worldToCanvas(x, -WORLD_HALF)
    const b = worldToCanvas(x, WORLD_HALF)
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.stroke()
  }
  for (let z = -WORLD_HALF; z <= WORLD_HALF; z += 5) {
    const a = worldToCanvas(-WORLD_HALF, z)
    const b = worldToCanvas(WORLD_HALF, z)
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.stroke()
  }

  const roadColor = '#8FA7B5'
  drawWorldRect(0, 0, 1900, 18, roadColor, 0.86)
  drawWorldRect(0, -330, 1840, 15, roadColor, 0.82)
  drawWorldRect(0, 330, 1840, 15, roadColor, 0.82)
  drawWorldRect(0, -560, 1720, 14, roadColor, 0.78)
  drawWorldRect(-230, 0, 15, 1760, roadColor, 0.82)
  drawWorldRect(230, 0, 15, 1760, roadColor, 0.82)
  drawWorldRect(-650, 0, 12, 1660, roadColor, 0.64)
  drawWorldRect(650, 0, 12, 1660, roadColor, 0.64)
  drawWorldLine(-900, -820, 850, 820, roadColor, 42, 0.48)
  drawWorldLine(-860, 780, 900, -760, roadColor, 36, 0.42)

  ctx.fillStyle = '#F8FAFC'
  for (let i = -900; i <= 900; i += 70) {
    drawWorldRect(i, 0, 8, 16, '#F8FAFC', 0.72)
    drawWorldRect(i, -330, 8, 14, '#F8FAFC', 0.66)
    drawWorldRect(i, 330, 8, 14, '#F8FAFC', 0.66)
    drawWorldRect(i, -560, 8, 12, '#F8FAFC', 0.58)
  }
  for (let i = -860; i <= 860; i += 70) {
    drawWorldRect(-230, i, 14, 8, '#F8FAFC', 0.66)
    drawWorldRect(230, i, 14, 8, '#F8FAFC', 0.66)
    drawWorldRect(-650, i, 12, 7, '#F8FAFC', 0.52)
    drawWorldRect(650, i, 12, 7, '#F8FAFC', 0.52)
  }

  CHANNELS.forEach(channel => {
    const center = worldToCanvas(channel.x, channel.z)
    const width = (channel.width / worldWidth) * canvas.width
    const height = (channel.depth / worldDepth) * canvas.height
    ctx.save()
    ctx.globalAlpha = 0.16
    ctx.fillStyle = channel.color
    ctx.fillRect(center.x - width / 2, center.y - height / 2, width, height)
    ctx.globalAlpha = 0.72
    ctx.strokeStyle = channel.color
    ctx.lineWidth = 4
    ctx.strokeRect(center.x - width / 2, center.y - height / 2, width, height)
    ctx.restore()
  })

  const parkBlocks = [
    [-780, 120, 110, 120],
    [820, -140, 120, 120],
    [160, 740, 180, 90],
    [-150, -870, 180, 85],
    [-820, -720, 130, 120],
    [760, 780, 150, 90]
  ]
  parkBlocks.forEach(([x, z, width, depth]) => drawWorldRect(x, z, width, depth, '#B7D8C7', 0.72))

  drawWorldRect(-820, 760, 140, 90, '#9DD5E8', 0.72)
  drawWorldRect(830, -790, 150, 96, '#9DD5E8', 0.68)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

const makeTerrainTexture = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 1024
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createLinearGradient(0, 0, 1024, 1024)
  gradient.addColorStop(0, '#B8D7C1')
  gradient.addColorStop(0.45, '#D8E8C7')
  gradient.addColorStop(1, '#A9D8CB')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 1024, 1024)

  for (let i = 0; i < 520; i += 1) {
    const x = (i * 97) % 1024
    const y = (i * 151) % 1024
    const width = 18 + (i % 9) * 9
    const height = 10 + (i % 7) * 7
    ctx.save()
    ctx.globalAlpha = 0.08 + (i % 5) * 0.015
    ctx.fillStyle = ['#6EA77B', '#E7F0D4', '#83C0B4', '#A4CB82'][i % 4]
    ctx.translate(x, y)
    ctx.rotate((i % 11) * 0.18)
    ctx.fillRect(-width / 2, -height / 2, width, height)
    ctx.restore()
  }

  ctx.strokeStyle = 'rgba(80,120,95,0.16)'
  ctx.lineWidth = 1
  for (let i = 0; i <= 1024; i += 32) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i, 1024)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, i)
    ctx.lineTo(1024, i)
    ctx.stroke()
  }

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(6, 6)
  texture.anisotropy = 8
  return texture
}

const buildStaticWorld = () => {
  channelPickTargets = []
  createRoamingTerrain()
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(WORLD_SIZE, WORLD_SIZE),
    new THREE.MeshStandardMaterial({
      color: '#E2EDE3',
      map: makeDistrictFloorTexture(),
      roughness: 0.78,
      metalness: 0.01
    })
  )
  floor.rotation.x = -Math.PI / 2
  floor.receiveShadow = true
  scene.add(floor)

  const grid = new THREE.GridHelper(WORLD_SIZE, 88, '#9CAFB8', '#DCE6EA')
  grid.position.y = 0.025
  grid.material.transparent = true
  grid.material.opacity = 0.32
  scene.add(grid)

  addRoad(0, 0, 1900, 18, 0)
  addRoad(0, -330, 1840, 15, 0)
  addRoad(0, 330, 1840, 15, 0)
  addRoad(0, -560, 1720, 14, 0)
  addRoad(-230, 0, 15, 1760, 0)
  addRoad(230, 0, 15, 1760, 0)
  addRoad(-650, 0, 12, 1660, 0)
  addRoad(650, 0, 12, 1660, 0)
  addRoad(-20, -10, 2280, 9, Math.PI / 4.25)
  addRoad(18, -10, 2180, 8, -Math.PI / 4.45)
  addSkyline()
  addHorizonTerrain()
  addOpenWorldDressing()

  CHANNELS.forEach(channel => {
    const zone = new THREE.Mesh(
      new THREE.BoxGeometry(channel.width, 0.12, channel.depth),
      new THREE.MeshStandardMaterial({
        color: channel.color,
        roughness: 0.7,
        transparent: true,
        opacity: 0.24
      })
    )
    zone.position.set(channel.x, 0.045, channel.z)
    zone.receiveShadow = true
    zone.userData.channelId = channel.id
    scene.add(zone)
    channelPickTargets.push(zone)

    const outline = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(channel.width, 0.13, channel.depth)),
      new THREE.LineBasicMaterial({ color: channel.color, transparent: true, opacity: 0.72 })
    )
    outline.position.copy(zone.position)
    scene.add(outline)

    addChannelShell(channel)

    const beacon = new THREE.Mesh(
      new THREE.CylinderGeometry(3.2, 4.4, 8.5, 20),
      new THREE.MeshStandardMaterial({ color: channel.color, roughness: 0.34, metalness: 0.08 })
    )
    beacon.position.set(channel.x, 4.1, channel.z)
    beacon.castShadow = true
    beacon.userData.channelId = channel.id
    scene.add(beacon)
    channelPickTargets.push(beacon)

    addChannelFixtures(channel)

    const label = makeTextSprite(channel.label, {
      background: '#FFFFFF',
      color: '#111827',
      border: channel.color,
      fontSize: 30
    })
    label.scale.multiplyScalar(1.1)
    label.position.set(channel.x, 10.5, channel.z)
    scene.add(label)
  })

  const hub = new THREE.Mesh(
    new THREE.CylinderGeometry(15, 21, 3.2, 40),
    new THREE.MeshStandardMaterial({ color: '#172033', roughness: 0.46, metalness: 0.12 })
  )
  hub.position.set(0, 1.6, 0)
  hub.castShadow = true
  scene.add(hub)

  const hubGlow = new THREE.Mesh(
    new THREE.TorusGeometry(22, 0.22, 8, 72),
    new THREE.MeshBasicMaterial({ color: '#38BDF8', transparent: true, opacity: 0.65 })
  )
  hubGlow.rotation.x = -Math.PI / 2
  hubGlow.position.set(0, 3.4, 0)
  scene.add(hubGlow)

  const hubLabel = makeTextSprite('상품 허브', {
    background: '#111827',
    color: '#FFFFFF',
    border: '#111827',
    fontSize: 30
  })
  hubLabel.scale.multiplyScalar(1.05)
  hubLabel.position.set(0, 9.2, 0)
  scene.add(hubLabel)
}

const createRoamingTerrain = () => {
  const terrain = new THREE.Mesh(
    new THREE.PlaneGeometry(3200, 3200),
    new THREE.MeshStandardMaterial({
      color: '#D9EED6',
      map: makeTerrainTexture(),
      roughness: 0.82,
      metalness: 0.01
    })
  )
  terrain.rotation.x = -Math.PI / 2
  terrain.position.y = -0.06
  terrain.receiveShadow = true
  scene.add(terrain)
  roamingTerrain = terrain

  const grid = new THREE.GridHelper(3200, 80, '#8FB39D', '#CFE2D4')
  grid.position.y = -0.045
  grid.material.transparent = true
  grid.material.opacity = 0.24
  scene.add(grid)
  roamingGrid = grid
  updateRoamingTerrain()
}

const updateRoamingTerrain = () => {
  if (!roamingTerrain || !roamingGrid) return
  const chunkSize = 640
  const x = Math.round(player.x / chunkSize) * chunkSize
  const z = Math.round(player.z / chunkSize) * chunkSize
  roamingTerrain.position.x = x
  roamingTerrain.position.z = z
  roamingGrid.position.x = x
  roamingGrid.position.z = z
}

const addRoad = (x, z, width, depth, rotation = 0) => {
  const road = new THREE.Mesh(
    new THREE.PlaneGeometry(width, depth),
    new THREE.MeshStandardMaterial({ color: '#A7BAC5', roughness: 0.78, metalness: 0.01 })
  )
  road.rotation.x = -Math.PI / 2
  road.rotation.z = rotation
  road.position.set(x, 0.032, z)
  road.receiveShadow = true
  scene.add(road)
  const horizontal = width >= depth
  const curbMaterial = new THREE.MeshStandardMaterial({ color: '#E8F0F4', roughness: 0.72 })
  const curbA = new THREE.Mesh(
    new THREE.BoxGeometry(horizontal ? width : 0.7, 0.18, horizontal ? 0.7 : depth),
    curbMaterial
  )
  const curbB = curbA.clone()
  const offset = (horizontal ? depth : width) / 2 + 0.42
  curbA.position.set(x + (horizontal ? 0 : -offset), 0.12, z + (horizontal ? -offset : 0))
  curbB.position.set(x + (horizontal ? 0 : offset), 0.12, z + (horizontal ? offset : 0))
  curbA.rotation.y = rotation
  curbB.rotation.y = rotation
  curbA.castShadow = true
  curbB.castShadow = true
  curbA.receiveShadow = true
  curbB.receiveShadow = true
  scene.add(curbA, curbB)
  if (Math.abs(rotation) < 0.001) {
    const count = Math.floor((horizontal ? width : depth) / 12)
    for (let i = 0; i < count; i += 1) {
      const offset = -((horizontal ? width : depth) / 2) + 6 + i * 12
      const stripe = new THREE.Mesh(
        new THREE.PlaneGeometry(horizontal ? 3.2 : 0.34, horizontal ? 0.34 : 3.2),
        new THREE.MeshBasicMaterial({ color: '#F8FAFC', transparent: true, opacity: 0.66 })
      )
      stripe.rotation.x = -Math.PI / 2
      stripe.position.set(horizontal ? x + offset : x, 0.041, horizontal ? z : z + offset)
      scene.add(stripe)
    }
  }
}

const addSkyline = () => {
  const colors = ['#BFDBFE', '#A7F3D0', '#FDE68A', '#DDD6FE', '#FECACA', '#BAE6FD']
  for (let i = 0; i < 96; i += 1) {
    const side = i % 4
    const height = 9 + (i % 8) * 2.4
    const width = 9 + (i % 4) * 2.2
    const depth = 7 + (i % 5) * 1.6
    const x = side < 2 ? -980 + (i % 48) * 42 : (side === 2 ? -1020 : 1020)
    const z = side < 2 ? (side === 0 ? -1020 : 1020) : -960 + (i % 48) * 40
    const building = new THREE.Mesh(
      new THREE.BoxGeometry(width, height, depth),
      new THREE.MeshStandardMaterial({ color: colors[i % colors.length], roughness: 0.62, metalness: 0.02 })
    )
    building.position.set(x, height / 2, z)
    building.castShadow = true
    building.receiveShadow = true
    scene.add(building)
    const rows = Math.min(7, Math.floor(height))
    for (let row = 0; row < rows; row += 1) {
      const windowBand = new THREE.Mesh(
        new THREE.BoxGeometry(Math.max(1.1, width - 0.6), 0.07, 0.03),
        new THREE.MeshBasicMaterial({ color: '#FFFFFF', transparent: true, opacity: 0.56 })
      )
      windowBand.position.set(x, 2.2 + row * 2.2, z + (side === 0 ? depth / 2 + 0.04 : -depth / 2 - 0.04))
      scene.add(windowBand)
    }
  }
}

const addHorizonTerrain = () => {
  const hillMaterial = new THREE.MeshStandardMaterial({ color: '#7DB99A', roughness: 0.92 })
  for (let i = 0; i < 34; i += 1) {
    const angle = (i / 34) * Math.PI * 2
    const radius = 1180 + (i % 5) * 26
    const width = 130 + (i % 4) * 38
    const height = 28 + (i % 7) * 8
    const hill = new THREE.Mesh(new THREE.ConeGeometry(width, height, 5), hillMaterial)
    hill.position.set(Math.cos(angle) * radius, height / 2 - 3, Math.sin(angle) * radius)
    hill.rotation.y = -angle
    hill.castShadow = true
    hill.receiveShadow = true
    scene.add(hill)
  }

  const sun = new THREE.Mesh(
    new THREE.CircleGeometry(52, 48),
    new THREE.MeshBasicMaterial({ color: '#FFE8A3', transparent: true, opacity: 0.72, side: THREE.DoubleSide })
  )
  sun.position.set(-420, 360, -1040)
  sun.lookAt(0, 0, 0)
  scene.add(sun)
}

const isInsideChannelArea = (x, z, padding = 5) => {
  return CHANNELS.some(channel => (
    Math.abs(x - channel.x) <= channel.width / 2 + padding &&
    Math.abs(z - channel.z) <= channel.depth / 2 + padding
  ))
}

const addBlockyBuilding = (x, z, width, depth, height, color) => {
  const base = addBox(x, height / 2, z, width, height, depth, color, 0.03)
  const roof = addBox(x, height + 0.14, z, width + 0.35, 0.28, depth + 0.35, '#334155', 0.04)
  const frontZ = z + depth / 2 + 0.016
  const rows = Math.max(1, Math.floor(height / 0.9))
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < Math.max(2, Math.floor(width / 1.4)); col += 1) {
      const window = new THREE.Mesh(
        new THREE.BoxGeometry(0.48, 0.28, 0.025),
        new THREE.MeshBasicMaterial({ color: '#E0F2FE', transparent: true, opacity: 0.76 })
      )
      window.position.set(x - width / 2 + 0.7 + col * 1.15, 0.65 + row * 0.82, frontZ)
      scene.add(window)
    }
  }
  return { base, roof }
}

const addTree = (x, z, scale = 1) => {
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.16 * scale, 0.24 * scale, 1.4 * scale, 8),
    new THREE.MeshStandardMaterial({ color: '#7C4A2D', roughness: 0.82 })
  )
  trunk.position.set(x, 0.7 * scale, z)
  trunk.castShadow = true
  trunk.receiveShadow = true
  scene.add(trunk)

  const canopyMaterial = new THREE.MeshStandardMaterial({
    color: ['#2F8F5B', '#3BA66F', '#277A52'][Math.abs(Math.round(x + z)) % 3],
    roughness: 0.7
  })
  const canopy = new THREE.Mesh(new THREE.DodecahedronGeometry(0.95 * scale, 0), canopyMaterial)
  canopy.position.set(x, 1.65 * scale, z)
  canopy.scale.set(1.05, 0.86, 1.05)
  canopy.castShadow = true
  canopy.receiveShadow = true
  scene.add(canopy)
  const top = new THREE.Mesh(new THREE.ConeGeometry(0.72 * scale, 1.0 * scale, 8), canopyMaterial)
  top.position.set(x, 2.18 * scale, z)
  top.castShadow = true
  scene.add(top)
  return { trunk, canopy }
}

const addLamp = (x, z) => {
  const pole = addBox(x, 1.0, z, 0.12, 2.0, 0.12, '#475569')
  const light = new THREE.Mesh(
    new THREE.BoxGeometry(0.48, 0.28, 0.48),
    new THREE.MeshBasicMaterial({ color: '#FEF3C7', transparent: true, opacity: 0.88 })
  )
  light.position.set(x, 2.12, z)
  scene.add(light)
  return { pole, light }
}

const addWater = (x, z, width, depth) => {
  const water = new THREE.Mesh(
    new THREE.BoxGeometry(width, 0.08, depth),
    new THREE.MeshStandardMaterial({ color: '#67C7E7', roughness: 0.36, metalness: 0.04, transparent: true, opacity: 0.74 })
  )
  water.position.set(x, 0.06, z)
  scene.add(water)
}

const addOpenWorldDressing = () => {
  addWater(-820, 760, 140, 90)
  addWater(830, -790, 150, 96)

  const districtColors = ['#E2E8F0', '#DBEAFE', '#DCFCE7', '#FEF3C7', '#FCE7F3', '#EDE9FE']
  const buildingAnchors = [
    [-740, -160], [-660, 150], [-280, -340], [-250, 280], [230, -270], [300, 280],
    [690, 140], [740, -180], [-780, -580], [730, 670], [-250, 680], [240, -790],
    [-760, 670], [780, -560], [-60, 670], [80, -340], [-620, -20], [630, 30],
    [-140, 400], [150, -490], [-380, -720], [390, 760], [-880, 280], [880, -280],
    [-520, 520], [520, -520], [-920, -20], [920, 40], [20, 900], [-20, -940]
  ]
  buildingAnchors.forEach(([x, z], idx) => {
    if (isInsideChannelArea(x, z, 3)) return
    const width = 16 + (idx % 4) * 5
    const depth = 14 + (idx % 3) * 5
    const height = 8 + (idx % 6) * 4
    addBlockyBuilding(x, z, width, depth, height, districtColors[idx % districtColors.length])
  })

  for (let i = 0; i < 180; i += 1) {
    const x = -980 + (i * 137) % 1960
    const z = -960 + (i * 211) % 1920
    if (Math.abs(x) < 60 && Math.abs(z) < 60) continue
    if (isInsideChannelArea(x, z, 24)) continue
    if (i % 5 === 0) {
      addLamp(x, z)
    } else {
      addTree(x, z, 2.2 + (i % 4) * 0.34)
    }
  }

  const parcelColors = ['#CDE7D5', '#D8E7F0', '#E9E1C6', '#D9D7F0', '#E6D1D1']
  for (let i = 0; i < 130; i += 1) {
    const x = -940 + (i * 97) % 1880
    const z = -910 + (i * 151) % 1820
    if (isInsideChannelArea(x, z, 26)) continue
    const width = 18 + (i % 4) * 8
    const depth = 16 + (i % 3) * 7
    addBox(x, 0.055, z, width, 0.11, depth, parcelColors[i % parcelColors.length])
  }

  CHANNELS.forEach(channel => {
    const color = channel.color
    addBox(channel.x - channel.width / 2 + 7, 1.35, channel.z - channel.depth / 2 + 7, 8, 2.7, 8, color)
    addBox(channel.x + channel.width / 2 - 7, 1.35, channel.z + channel.depth / 2 - 7, 8, 2.7, 8, color)
    for (let i = -1; i <= 1; i += 1) {
      addLamp(channel.x + i * 18, channel.z - channel.depth / 2 - 9)
    }
  })
}

const addBox = (x, y, z, width, height, depth, color, metalness = 0.02) => {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(width, height, depth),
    new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness })
  )
  mesh.position.set(x, y, z)
  mesh.castShadow = true
  mesh.receiveShadow = true
  scene.add(mesh)
  return mesh
}

const makeTransparent = (mesh, opacity) => {
  mesh.material.transparent = true
  mesh.material.opacity = opacity
  return mesh
}

const addChannelShell = (channel) => {
  const { x, z, width, depth, color } = channel
  const base = addBox(x, 0.18, z, width + 16, 0.36, depth + 14, '#F8FAFC')
  base.material.color.lerp(new THREE.Color(color), 0.08)
  const backWall = makeTransparent(addBox(x, 3.2, z - depth / 2 + 2.5, width + 10, 6.4, 1.2, '#F8FAFC'), 0.86)
  const leftWall = makeTransparent(addBox(x - width / 2 - 3, 2.7, z, 1.2, 5.4, depth + 8, '#FFFFFF'), 0.64)
  const rightWall = makeTransparent(addBox(x + width / 2 + 3, 2.7, z, 1.2, 5.4, depth + 8, '#FFFFFF'), 0.64)
  const roof = makeTransparent(addBox(x, 6.55, z - 1, width + 18, 0.5, depth + 16, color, 0.04), 0.42)
  const frontBeam = addBox(x, 5.45, z + depth / 2 + 5, width + 14, 0.38, 0.9, color, 0.05)
  const rearBeam = addBox(x, 5.45, z - depth / 2 - 5, width + 14, 0.34, 0.8, color, 0.05)

  for (let i = -1; i <= 1; i += 1) {
    addBox(x + i * (width / 2 + 2), 2.85, z + depth / 2 + 5, 0.7, 5.2, 0.7, color, 0.04)
    addBox(x + i * (width / 2 + 2), 2.85, z - depth / 2 - 5, 0.55, 5.1, 0.55, '#94A3B8')
  }

  const roleLabelText = {
    official: '홈페이지 확인',
    advisor: '설계 상담',
    community: '후기 검증',
    media: '비교 콘텐츠',
    consult: '견적/청약',
    service: '유지/청구'
  }[channel.id] || channel.label
  const roleLabel = makeTextSprite(roleLabelText, {
    background: '#FFFFFF',
    color: '#111827',
    border: color,
    fontSize: 22
  })
  roleLabel.scale.multiplyScalar(0.82)
  roleLabel.position.set(x, 7.85, z + depth / 2 + 7)
  scene.add(roleLabel)

  return { base, backWall, leftWall, rightWall, roof, frontBeam, rearBeam }
}

const addScreen = (x, z, color, labelText) => {
  const stand = addBox(x, 1.9, z, 0.42, 3.8, 0.42, '#475569')
  const screen = addBox(x, 4.15, z, 7.2, 3.9, 0.3, '#0F172A', 0.08)
  const glow = addBox(x, 4.16, z - 0.18, 6.55, 3.15, 0.1, color, 0.02)
  glow.material.transparent = true
  glow.material.opacity = 0.38
  const label = makeTextSprite(labelText, {
    background: '#FFFFFF',
    color: '#0F172A',
    border: color,
    fontSize: 22
  })
  label.scale.multiplyScalar(0.95)
  label.position.set(x, 7.1, z - 0.2)
  scene.add(label)
  return { stand, screen, glow }
}

const addChannelFixtures = (channel) => {
  const { x, z, color } = channel
  if (channel.id === 'official') {
    addScreen(x - 7, z - 3, color, '약관/FAQ')
    addScreen(x + 6, z + 2, color, '앱 가입')
    for (let i = 0; i < 5; i += 1) {
      addBox(x - 9 + i * 4.2, 0.36, z + 7, 1.35, 0.72, 1.05, '#FFFFFF')
      addBox(x - 9 + i * 4.2, 0.82, z + 7, 0.86, 0.2, 0.72, color)
    }
  } else if (channel.id === 'advisor') {
    for (let row = 0; row < 2; row += 1) {
      for (let i = 0; i < 4; i += 1) {
        const boothX = x - 9 + i * 6
        const boothZ = z - 3 + row * 7
        addBox(boothX, 0.42, boothZ, 3.2, 0.2, 1.5, '#FFFFFF')
        addBox(boothX, 1.03, boothZ - 0.56, 1.65, 1.02, 0.12, color)
        addBox(boothX - 1.2, 0.3, boothZ + 1.35, 0.78, 0.6, 0.78, '#CBD5E1')
        addBox(boothX + 1.2, 0.3, boothZ + 1.35, 0.78, 0.6, 0.78, '#CBD5E1')
      }
    }
  } else if (channel.id === 'community') {
    for (let ring = 0; ring < 2; ring += 1) {
      for (let i = 0; i < 8; i += 1) {
        const angle = (i / 8) * Math.PI * 2
        const radiusX = 5.2 + ring * 4.4
        const radiusZ = 3.9 + ring * 3.2
        addBox(x + Math.cos(angle) * radiusX, 0.32, z + Math.sin(angle) * radiusZ, 1.8, 0.25, 0.56, '#FDE68A')
        if (i % 2 === 0) addTree(x + Math.cos(angle) * (radiusX + 2.2), z + Math.sin(angle) * (radiusZ + 1.8), 0.78)
      }
    }
  } else if (channel.id === 'media') {
    addScreen(x - 5, z - 5, color, 'LIVE 비교')
    addScreen(x + 6, z - 1, color, '전문가 해설')
    addBox(x, 0.42, z + 5.5, 8.8, 0.84, 3.6, '#111827', 0.08)
    addBox(x, 1.05, z + 3.7, 7.4, 0.28, 0.38, color)
    const mast = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.14, 2.4, 12),
      new THREE.MeshStandardMaterial({ color: '#475569', roughness: 0.48 })
    )
    mast.position.set(x + 10, 1.2, z + 7)
    mast.castShadow = true
    scene.add(mast)
    const dish = new THREE.Mesh(
      new THREE.ConeGeometry(0.58, 0.6, 24),
      new THREE.MeshStandardMaterial({ color, roughness: 0.32, metalness: 0.06 })
    )
    dish.position.set(x + 10, 2.55, z + 7)
    dish.rotation.x = Math.PI / 2.8
    scene.add(dish)
  } else if (channel.id === 'consult') {
    addBox(x, 0.68, z, 10.5, 0.62, 3.1, '#FFFFFF')
    addBox(x, 1.12, z - 1.06, 8.6, 0.36, 0.3, color)
    for (let i = -2; i <= 2; i += 1) {
      addBox(x + i * 3.8, 1.38, z + 3.6, 0.1, 1.4, 2.2, '#E2E8F0')
      addBox(x + i * 3.8, 0.32, z + 5.2, 1.2, 0.64, 1.2, '#CBD5E1')
    }
  } else if (channel.id === 'service') {
    addScreen(x + 7, z - 1, color, '청구/유지')
    addScreen(x - 7, z + 3, color, '갱신 안내')
    for (let i = 0; i < 5; i += 1) {
      addBox(x - 10 + i * 5, 0.42, z + 6.2, 2.3, 0.32, 1.2, '#FFFFFF')
      addBox(x - 10 + i * 5, 0.86, z + 5.7, 1.6, 0.18, 0.7, color)
      addBox(x - 10 + i * 5, 0.2, z + 3.8, 0.18, 0.4, 2.1, '#94A3B8')
    }
  }
}

const makeTextSprite = (text, options = {}) => {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  const fontSize = options.fontSize || 26
  context.font = `700 ${fontSize}px system-ui, sans-serif`
  const measured = context.measureText(text)
  canvas.width = Math.min(512, Math.max(140, measured.width + 52))
  canvas.height = 76

  context.font = `700 ${fontSize}px system-ui, sans-serif`
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  drawRoundRect(context, 4, 4, canvas.width - 8, canvas.height - 8, 14, options.background || 'rgba(255,255,255,0.92)')
  if (options.border) {
    context.strokeStyle = options.border
    context.lineWidth = 4
    strokeRoundRect(context, 4, 4, canvas.width - 8, canvas.height - 8, 14)
  }
  context.fillStyle = options.color || '#111827'
  context.fillText(text.length > 18 ? `${text.slice(0, 17)}...` : text, canvas.width / 2, canvas.height / 2)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(canvas.width / 82, canvas.height / 82, 1)
  return sprite
}

const drawRoundRect = (ctx, x, y, width, height, radius, color) => {
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
  ctx.fill()
}

const strokeRoundRect = (ctx, x, y, width, height, radius) => {
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
  ctx.stroke()
}

const makeFaceSprite = (agent) => {
  const canvas = document.createElement('canvas')
  canvas.width = 96
  canvas.height = 96
  const ctx = canvas.getContext('2d')
  const visual = agent.visual
  ctx.clearRect(0, 0, 96, 96)
  ctx.fillStyle = 'rgba(255,255,255,0.88)'
  ctx.beginPath()
  ctx.arc(48, 48, 42, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = agent.color
  ctx.lineWidth = 5
  ctx.stroke()
  ctx.fillStyle = visual.skin
  ctx.beginPath()
  ctx.arc(48, 50, 25, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = visual.hair
  ctx.beginPath()
  ctx.arc(48, 35, 25, Math.PI, Math.PI * 2)
  ctx.fill()
  ctx.fillRect(25, 35, 46, 10)
  ctx.fillStyle = '#111827'
  ctx.beginPath()
  ctx.arc(39, 50, 3, 0, Math.PI * 2)
  ctx.arc(57, 50, 3, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = '#7F1D1D'
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.arc(48, 58, 8, 0.15 * Math.PI, 0.85 * Math.PI)
  ctx.stroke()
  ctx.fillStyle = agent.color
  ctx.fillRect(28, 72, 40, 10)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }))
  sprite.scale.set(0.78, 0.78, 1)
  return sprite
}

const createAgentMeshes = () => {
  clearAgentMeshes()
  agentStates.value.forEach(agent => {
    const group = new THREE.Group()
    group.position.set(agent.x, 0, agent.z)
    group.userData.agentId = agent.id
    group.scale.setScalar(1.1 + (agent.id % 4) * 0.035)

    const visual = agent.visual
    const outfitMaterial = new THREE.MeshStandardMaterial({
      color: visual.outfit,
      roughness: 0.52,
      metalness: 0.03
    })
    const skinMaterial = new THREE.MeshStandardMaterial({ color: visual.skin, roughness: 0.62 })
    const hairMaterial = new THREE.MeshStandardMaterial({ color: visual.hair, roughness: 0.7 })
    const darkMaterial = new THREE.MeshStandardMaterial({ color: '#1F2937', roughness: 0.58 })

    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.34 * visual.width, 0.72 * visual.height, 6, 14), outfitMaterial)
    body.position.y = 1.08 * visual.height
    body.scale.x = visual.width
    body.castShadow = true

    const shoulders = new THREE.Mesh(
      new THREE.BoxGeometry(0.8 * visual.width, 0.16, 0.32),
      outfitMaterial
    )
    shoulders.position.y = 1.42 * visual.height
    shoulders.castShadow = true

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.32 * visual.width, 20, 16),
      skinMaterial
    )
    head.position.y = 1.78 * visual.height
    head.castShadow = true

    const hair = new THREE.Mesh(
      visual.hairStyle === 2
        ? new THREE.ConeGeometry(0.34 * visual.width, 0.28, 18)
        : new THREE.SphereGeometry(0.34 * visual.width, 18, 10),
      hairMaterial
    )
    hair.position.y = visual.hairStyle === 2 ? 2.04 * visual.height : 1.96 * visual.height
    hair.scale.set(1.05, visual.hairStyle === 1 ? 0.38 : 0.48, 1.02)
    hair.castShadow = true

    const eyeMaterial = new THREE.MeshBasicMaterial({ color: '#111827' })
    const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), eyeMaterial)
    leftEye.position.set(-0.105 * visual.width, 1.8 * visual.height, 0.29 * visual.width)
    const rightEye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), eyeMaterial)
    rightEye.position.set(0.105 * visual.width, 1.8 * visual.height, 0.29 * visual.width)
    const mouth = new THREE.Mesh(
      new THREE.BoxGeometry(0.16 * visual.width, 0.018, 0.018),
      new THREE.MeshBasicMaterial({ color: '#7F1D1D' })
    )
    mouth.position.set(0, 1.69 * visual.height, 0.31 * visual.width)

    const leftArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.085, 0.48 * visual.height, 4, 8), outfitMaterial)
    leftArm.position.set(-0.48 * visual.width, 1.06 * visual.height, 0.02)
    leftArm.rotation.z = 0.22
    leftArm.castShadow = true

    const rightArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.085, 0.48 * visual.height, 4, 8), outfitMaterial)
    rightArm.position.set(0.48 * visual.width, 1.06 * visual.height, 0.02)
    rightArm.rotation.z = -0.22
    rightArm.castShadow = true

    const leftHand = new THREE.Mesh(new THREE.SphereGeometry(0.095, 10, 8), skinMaterial)
    leftHand.position.set(-0.56 * visual.width, 0.68 * visual.height, 0.02)
    leftHand.castShadow = true

    const rightHand = new THREE.Mesh(new THREE.SphereGeometry(0.095, 10, 8), skinMaterial)
    rightHand.position.set(0.56 * visual.width, 0.68 * visual.height, 0.02)
    rightHand.castShadow = true

    const leftLeg = new THREE.Mesh(new THREE.CapsuleGeometry(0.1, 0.58 * visual.height, 4, 8), darkMaterial)
    leftLeg.position.set(-0.15 * visual.width, 0.44 * visual.height, 0)
    leftLeg.castShadow = true

    const rightLeg = new THREE.Mesh(new THREE.CapsuleGeometry(0.1, 0.58 * visual.height, 4, 8), darkMaterial)
    rightLeg.position.set(0.15 * visual.width, 0.44 * visual.height, 0)
    rightLeg.castShadow = true

    const leftFoot = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.34), darkMaterial)
    leftFoot.position.set(-0.15 * visual.width, 0.12, 0.12)
    leftFoot.castShadow = true

    const rightFoot = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.34), darkMaterial)
    rightFoot.position.set(0.15 * visual.width, 0.12, 0.12)
    rightFoot.castShadow = true

    const badge = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.1, 0.018),
      new THREE.MeshBasicMaterial({ color: '#FFFFFF' })
    )
    badge.position.set(0.16 * visual.width, 1.25 * visual.height, 0.33)

    const shadow = new THREE.Mesh(
      new THREE.CircleGeometry(0.58 * visual.width, 28),
      new THREE.MeshBasicMaterial({ color: '#0F172A', transparent: true, opacity: 0.13, depthWrite: false })
    )
    shadow.rotation.x = -Math.PI / 2
    shadow.position.y = 0.025

    let accessory = null
    if (visual.accessory) {
      accessory = new THREE.Mesh(
        new THREE.TorusGeometry(0.34 * visual.width, 0.018, 8, 26),
        new THREE.MeshBasicMaterial({ color: '#0F172A' })
      )
      accessory.position.y = 1.8 * visual.height
      accessory.rotation.x = Math.PI / 2
    }

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.58, 0.68, 28),
      new THREE.MeshBasicMaterial({
        color: '#64748B',
        transparent: true,
        opacity: agent.id === selectedAgentId.value ? 0.95 : 0.36,
        side: THREE.DoubleSide
      })
    )
    ring.rotation.x = -Math.PI / 2
    ring.position.y = 0.055

    const label = makeTextSprite(agent.displayName, {
      background: 'rgba(255,255,255,0.94)',
      color: '#111827',
      border: agent.color,
      fontSize: 24
    })
    label.scale.multiplyScalar(0.72)
    label.position.y = 3.02
    label.visible = agent.id < 18 || agent.id === selectedAgentId.value

    const portrait = makeFaceSprite(agent)
    portrait.scale.set(0.92, 0.92, 1)
    portrait.position.y = 2.58
    portrait.visible = agent.id < 18 || agent.id === selectedAgentId.value

    group.add(
      shadow,
      ring,
      leftFoot,
      rightFoot,
      leftLeg,
      rightLeg,
      body,
      shoulders,
      badge,
      leftArm,
      rightArm,
      leftHand,
      rightHand,
      head,
      hair,
      leftEye,
      rightEye,
      mouth,
      portrait,
      label
    )
    if (accessory) group.add(accessory)
    group.traverse(child => {
      child.userData.agentId = agent.id
    })
    scene.add(group)

    agentPickTargets.push(body, head)
    agentMeshes.set(agent.id, { group, body, head, ring, label, portrait, leftArm, rightArm, leftLeg, rightLeg, leftHand, rightHand, bubble: null })
    updateAgentVisual(agent)
  })
}

const createPlayerMesh = () => {
  if (playerMesh) {
    scene.remove(playerMesh)
    disposeObject(playerMesh)
  }
  const group = new THREE.Group()
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: '#111827', roughness: 0.48, metalness: 0.04 })
  const jacketMaterial = new THREE.MeshStandardMaterial({ color: '#0EA5E9', roughness: 0.54 })
  const skinMaterial = new THREE.MeshStandardMaterial({ color: '#F2C9A5', roughness: 0.62 })

  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.36, 0.82, 6, 14), jacketMaterial)
  body.position.y = 1.08
  body.castShadow = true

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.31, 18, 14), skinMaterial)
  head.position.y = 1.78
  head.castShadow = true

  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.08, 0.08), bodyMaterial)
  visor.position.set(0, 1.84, 0.28)

  const leftLeg = new THREE.Mesh(new THREE.CapsuleGeometry(0.095, 0.54, 4, 8), bodyMaterial)
  leftLeg.position.set(-0.14, 0.43, 0)
  const rightLeg = new THREE.Mesh(new THREE.CapsuleGeometry(0.095, 0.54, 4, 8), bodyMaterial)
  rightLeg.position.set(0.14, 0.43, 0)

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.72, 0.86, 30),
    new THREE.MeshBasicMaterial({ color: '#0EA5E9', transparent: true, opacity: 0.82, side: THREE.DoubleSide })
  )
  ring.rotation.x = -Math.PI / 2
  ring.position.y = 0.05

  const label = makeTextSprite('나', {
    background: '#0F172A',
    color: '#FFFFFF',
    border: '#0EA5E9',
    fontSize: 30
  })
  label.position.y = 2.6

  group.add(ring, leftLeg, rightLeg, body, head, visor, label)
  scene.add(group)
  playerMesh = group
  updatePlayerMesh()
}

const updatePlayerMesh = () => {
  if (!playerMesh) return
  playerMesh.position.set(player.x, 0, player.z)
  playerMesh.rotation.y = player.yaw
  playerMesh.visible = !isPlayerMode.value
}

const clearAgentMeshes = () => {
  agentPickTargets = []
  agentMeshes.forEach(({ group }) => {
    scene.remove(group)
    disposeObject(group)
  })
  agentMeshes.clear()
}

const disposeObject = (object) => {
  object.traverse(child => {
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material]
      materials.forEach(material => {
        if (material.map) material.map.dispose()
        material.dispose()
      })
    }
  })
}

const updateAgentVisual = (agent) => {
  const meshData = agentMeshes.get(agent.id)
  if (!meshData) return
  const policyColors = {
    none: '#64748B',
    prospect: '#D97706',
    subscribed: '#059669',
    retained: '#0891B2',
    switched: '#7C3AED',
    cancelled: '#DC2626'
  }
  const stageColor = policyColors[agent.policyState] || ['#64748B', '#2563EB', '#D97706', '#7C3AED', '#059669'][agent.funnelIndex] || '#64748B'
  meshData.ring.material.color.set(stageColor)
  meshData.ring.material.opacity = agent.id === selectedAgentId.value ? 0.96 : 0.4
  meshData.label.visible = agent.id < 18 || agent.id === selectedAgentId.value
  if (meshData.portrait) meshData.portrait.visible = agent.id < 18 || agent.id === selectedAgentId.value
  const intentScale = 1 + agent.intent / 360
  meshData.body.scale.set(agent.visual?.width || 1, intentScale, 1)
}

const updateSelectionVisual = () => {
  agentStates.value.forEach(updateAgentVisual)
}

const showActionBubble = (agent, action) => {
  const meshData = agentMeshes.get(agent.id)
  if (!meshData) return
  if (meshData.bubble) {
    meshData.group.remove(meshData.bubble)
    disposeObject(meshData.bubble)
  }
  const bubble = makeTextSprite(action, {
    background: '#111827',
    color: '#FFFFFF',
    border: '#111827',
    fontSize: 24
  })
  bubble.scale.multiplyScalar(0.72)
  bubble.position.y = 3.45
  meshData.group.add(bubble)
  meshData.bubble = bubble
  window.setTimeout(() => {
    if (meshData.bubble === bubble) {
      meshData.group.remove(bubble)
      disposeObject(bubble)
      meshData.bubble = null
    }
  }, 2200)
}

const showChannelPulse = (channel, color = channel.color) => {
  if (!scene) return
  const pulse = new THREE.Mesh(
    new THREE.RingGeometry(Math.max(channel.width, channel.depth) * 0.46, Math.max(channel.width, channel.depth) * 0.52, 64),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.36,
      side: THREE.DoubleSide,
      depthWrite: false
    })
  )
  pulse.rotation.x = -Math.PI / 2
  pulse.position.set(channel.x, 0.18, channel.z)
  scene.add(pulse)
  window.setTimeout(() => {
    scene.remove(pulse)
    disposeObject(pulse)
  }, 1300)
}

const updateAgents = (dt) => {
  agentStates.value.forEach(agent => {
    const dx = agent.targetX - agent.x
    const dz = agent.targetZ - agent.z
    const distance = Math.hypot(dx, dz)

    if (distance < 0.22) {
      if (agent.targetChannelId) {
        const channel = CHANNELS.find(item => item.id === agent.targetChannelId)
        if (channel) generateAgentEvent(agent, channel)
      }
      pickNextTarget(agent)
      return
    }

    const step = Math.min(distance, agent.speed * dt)
    agent.x += (dx / distance) * step
    agent.z += (dz / distance) * step

    const meshData = agentMeshes.get(agent.id)
    if (meshData) {
      meshData.group.position.set(agent.x, 0, agent.z)
      meshData.group.rotation.y = Math.atan2(dx, dz)
      const stride = Date.now() * 0.009 + agent.id
      const swing = Math.sin(stride) * 0.22
      if (meshData.leftArm) meshData.leftArm.rotation.x = swing
      if (meshData.rightArm) meshData.rightArm.rotation.x = -swing
      if (meshData.leftLeg) meshData.leftLeg.rotation.x = -swing * 0.65
      if (meshData.rightLeg) meshData.rightLeg.rotation.x = swing * 0.65
    }
  })
}

const isMovementKey = (code) => {
  return ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight', 'ShiftLeft', 'ShiftRight'].includes(code)
}

const updatePlayerMovement = (dt) => {
  if (!isPlayerMode.value) return
  let forward = 0
  let strafe = 0
  if (activeKeys.has('KeyW') || activeKeys.has('ArrowUp')) forward += 1
  if (activeKeys.has('KeyS') || activeKeys.has('ArrowDown')) forward -= 1
  if (activeKeys.has('KeyD') || activeKeys.has('ArrowRight')) strafe -= 1
  if (activeKeys.has('KeyA') || activeKeys.has('ArrowLeft')) strafe += 1

  const length = Math.hypot(forward, strafe)
  if (length > 0) {
    player.moveTargetX = null
    player.moveTargetZ = null
    forward /= length
    strafe /= length
    const sprint = activeKeys.has('ShiftLeft') || activeKeys.has('ShiftRight')
    const movementSpeed = player.speed * (sprint ? 1.65 : 1)
    const sin = Math.sin(player.yaw)
    const cos = Math.cos(player.yaw)
    player.x += (sin * forward + cos * strafe) * movementSpeed * dt
    player.z += (cos * forward - sin * strafe) * movementSpeed * dt
  } else if (player.moveTargetX !== null && player.moveTargetZ !== null) {
    const dx = player.moveTargetX - player.x
    const dz = player.moveTargetZ - player.z
    const distance = Math.hypot(dx, dz)
    if (distance < 1.4) {
      player.moveTargetX = null
      player.moveTargetZ = null
    } else {
      const step = Math.min(distance, player.speed * 1.25 * dt)
      player.x += (dx / distance) * step
      player.z += (dz / distance) * step
    }
  }
  updateRoamingTerrain()
  updatePlayerMesh()
  updateCamera()
}

const animate = () => {
  animationFrameId = requestAnimationFrame(animate)
  const frameDt = Math.min(clock.getDelta(), 0.05)
  updatePlayerMovement(frameDt)
  if (isRunning.value) updateAgents(frameDt * speed.value)
  renderer.render(scene, camera)
}

const resizeRenderer = () => {
  if (!sceneHost.value || !renderer || !camera) return
  const rect = sceneHost.value.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return
  camera.aspect = rect.width / rect.height
  camera.updateProjectionMatrix()
  renderer.setSize(rect.width, rect.height, false)
}

const updateCamera = () => {
  if (!camera) return
  if (isPlayerMode.value) {
    camera.position.set(player.x, player.y, player.z)
    const horizontal = Math.cos(player.pitch)
    const lookX = Math.sin(player.yaw) * horizontal
    const lookY = Math.sin(player.pitch)
    const lookZ = Math.cos(player.yaw) * horizontal
    camera.lookAt(player.x + lookX, player.y + lookY, player.z + lookZ)
    return
  }
  const horizontal = Math.cos(orbit.pitch) * orbit.radius
  camera.position.set(
    cameraTarget.x + Math.sin(orbit.yaw) * horizontal,
    cameraTarget.y + Math.sin(orbit.pitch) * orbit.radius,
    cameraTarget.z + Math.cos(orbit.yaw) * horizontal
  )
  camera.lookAt(cameraTarget.x, cameraTarget.y + 0.8, cameraTarget.z)
}

const resolveAgentIdFromEvent = (event) => {
  if (!renderer || !camera || !raycaster) return null
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const intersections = raycaster.intersectObjects(agentPickTargets, true)
  if (!intersections.length) return null
  return intersections[0].object.userData.agentId ?? null
}

const resolveChannelIdFromEvent = (event) => {
  if (!renderer || !camera || !raycaster) return null
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const intersections = raycaster.intersectObjects(channelPickTargets, true)
  if (!intersections.length) return null
  return intersections[0].object.userData.channelId ?? null
}

const resolveGroundPointFromEvent = (event) => {
  if (!renderer || !camera || !raycaster) return null
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  if (!raycaster.ray.intersectPlane(groundPlane, groundPoint)) return null
  return { x: groundPoint.x, z: groundPoint.z }
}

const setPlayerMoveTargetFromEvent = (event) => {
  const point = resolveGroundPointFromEvent(event)
  if (!point) return false
  player.moveTargetX = point.x
  player.moveTargetZ = point.z
  return true
}

const panObservationCamera = (dx, dy) => {
  if (!camera) return
  camera.getWorldDirection(cameraPanForward)
  cameraPanForward.y = 0
  if (cameraPanForward.lengthSq() < 0.0001) {
    cameraPanForward.set(Math.sin(orbit.yaw + Math.PI), 0, Math.cos(orbit.yaw + Math.PI))
  }
  cameraPanForward.normalize()
  cameraPanRight.crossVectors(cameraPanForward, worldUp).normalize()
  const panScale = clamp(orbit.radius * 0.0018, 0.2, 2.7)
  cameraTarget.addScaledVector(cameraPanRight, -dx * panScale)
  cameraTarget.addScaledVector(cameraPanForward, dy * panScale)
}

const handlePointerDown = (event) => {
  sceneHost.value?.focus()
  if (event.button === 0 || event.button === 2) {
    event.preventDefault()
    event.currentTarget?.setPointerCapture?.(event.pointerId)
  }
  pointerState.down = true
  pointerState.moved = false
  pointerState.button = event.button
  pointerState.x = event.clientX
  pointerState.y = event.clientY
  if (sceneHost.value) {
    sceneHost.value.style.cursor = (!isPlayerMode.value && event.button === 0) || event.button === 2 ? 'grabbing' : 'crosshair'
  }
}

const handlePointerMove = (event) => {
  if (pointerState.down) {
    event.preventDefault()
    const dx = event.clientX - pointerState.x
    const dy = event.clientY - pointerState.y
    if (Math.abs(dx) + Math.abs(dy) > 3) pointerState.moved = true
    if (isPlayerMode.value) {
      if (pointerState.button === 0) {
        setPlayerMoveTargetFromEvent(event)
      } else if (pointerState.button === 2) {
        player.yaw -= dx * 0.0042
        player.pitch = clamp(player.pitch - dy * 0.0032, -0.72, 0.54)
      }
    } else if (pointerState.button === 0) {
      panObservationCamera(dx, dy)
    } else if (pointerState.button === 2) {
      orbit.yaw -= dx * 0.006
      orbit.pitch = clamp(orbit.pitch - dy * 0.004, 0.28, 1.08)
    }
    pointerState.x = event.clientX
    pointerState.y = event.clientY
    updateCamera()
    return
  }

  const agentId = resolveAgentIdFromEvent(event)
  const channelId = agentId === null ? resolveChannelIdFromEvent(event) : null
  if (sceneHost.value) sceneHost.value.style.cursor = agentId !== null || channelId !== null ? 'pointer' : (isPlayerMode.value ? 'crosshair' : 'grab')
}

const handlePointerUp = (event) => {
  event.currentTarget?.releasePointerCapture?.(event.pointerId)
  if (pointerState.button === 2 || event.button === 2) {
    pointerState.down = false
    if (sceneHost.value) sceneHost.value.style.cursor = isPlayerMode.value ? 'crosshair' : 'grab'
    return
  }
  if (isPlayerMode.value && pointerState.button === 0) {
    const agentId = resolveAgentIdFromEvent(event)
    if (agentId !== null) {
      focusAgent(agentId)
    } else {
      const channelId = resolveChannelIdFromEvent(event)
      const channel = CHANNELS.find(item => item.id === channelId)
      if (channel) {
        focusChannel(channel)
      } else {
        setPlayerMoveTargetFromEvent(event)
      }
    }
  } else if (!pointerState.moved) {
    const agentId = resolveAgentIdFromEvent(event)
    if (agentId !== null) {
      focusAgent(agentId)
    } else {
      const channelId = resolveChannelIdFromEvent(event)
      const channel = CHANNELS.find(item => item.id === channelId)
      if (channel) focusChannel(channel)
    }
  }
  pointerState.down = false
  if (sceneHost.value) sceneHost.value.style.cursor = isPlayerMode.value ? 'crosshair' : 'grab'
}

const handleContextMenu = (event) => {
  event?.preventDefault?.()
  if (!pointerState.down && sceneHost.value) {
    sceneHost.value.style.cursor = isPlayerMode.value ? 'crosshair' : 'grab'
  }
}

const handlePointerLeave = () => {
  pointerState.down = false
  if (sceneHost.value) sceneHost.value.style.cursor = isPlayerMode.value ? 'crosshair' : 'grab'
}

const handleWheel = (event) => {
  if (isPlayerMode.value) {
    player.speed = clamp(player.speed + (event.deltaY > 0 ? -1 : 1), 8, 22)
    return
  }
  orbit.radius = clamp(orbit.radius + event.deltaY * 0.12, 80, 1400)
  updateCamera()
}

const facePointFromPlayer = (x, z) => {
  player.yaw = Math.atan2(x - player.x, z - player.z)
  player.pitch = -0.04
  updateCamera()
}

const focusAgent = (agentId) => {
  const agent = agentStates.value.find(item => item.id === agentId)
  if (!agent) return
  selectedAgentId.value = agent.id
  if (isPlayerMode.value) {
    facePointFromPlayer(agent.x, agent.z)
    updateSelectionVisual()
    return
  }
  cameraTarget.set(agent.x, 0, agent.z)
  orbit.radius = Math.min(orbit.radius, 120)
  updateCamera()
  updateSelectionVisual()
}

const focusChannel = (channel) => {
  selectedChannelId.value = channel.id
  if (isPlayerMode.value) {
    facePointFromPlayer(channel.x, channel.z)
    return
  }
  cameraTarget.set(channel.x, 0, channel.z)
  orbit.radius = 230
  updateCamera()
}

const togglePlayerMode = () => {
  isPlayerMode.value = !isPlayerMode.value
  activeKeys.clear()
  if (isPlayerMode.value) {
    const target = selectedAgent.value || { x: 0, z: 0 }
    const angle = Math.atan2(target.x - player.x, target.z - player.z)
    player.yaw = Number.isFinite(angle) ? angle : Math.PI
    player.pitch = -0.04
    sceneHost.value?.focus()
    addLog('플레이어 시점으로 전환했습니다')
  } else {
    cameraTarget.set(player.x, 0, player.z)
    orbit.radius = 620
    orbit.pitch = 0.68
    addLog('관전 시점으로 전환했습니다')
  }
  updatePlayerMesh()
  updateCamera()
}

const handleKeyDown = (event) => {
  const tag = event.target?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || event.target?.isContentEditable) return
  if (!isPlayerMode.value || !isMovementKey(event.code)) return
  event.preventDefault()
  activeKeys.add(event.code)
}

const handleKeyUp = (event) => {
  if (!isMovementKey(event.code)) return
  activeKeys.delete(event.code)
}

const setTargetYears = (years) => {
  targetYears.value = years
  if (currentRound.value >= maxRounds.value) currentRound.value = maxRounds.value - 1
  addLog(`보험 가입 시뮬레이션 목표 기간을 ${years}년(${years * weeksPerYear.value}주)로 설정했습니다`)
  updateMetrics()
}

const scrollChatToBottom = () => {
  nextTick(() => {
    const el = chatLogRef.value
    if (!el) return
    el.scrollTop = el.scrollHeight
  })
}

const getRecentUserQuestions = (agent) => {
  return agent.chatMessages
    .filter(message => message.role === 'user')
    .slice(-3)
    .map(message => message.text)
}

const classifyQuestion = (question, agent) => {
  const recent = getRecentUserQuestions(agent).join(' ')
  const text = `${recent} ${question}`.toLowerCase()
  if (/(듣는|듣고|질문|대답|말귀|못 알아|아니|그게 아니라)/.test(text)) return 'repair'
  if (/(팔리|판매|실적|매출|반응|시장|수요|흥행|가입자|문의|상담.*늘|잘 나가)/.test(text)) return 'sales'
  if (/(가입|들까|사야|왜)/.test(text)) return 'join'
  if (/(해지|그만|취소|탈퇴)/.test(text)) return 'cancel'
  if (/(전환|갈아|다른 보험|바꿀)/.test(text)) return 'switch'
  if (/(개인정보|데이터|건강 데이터|연동)/.test(text)) return 'privacy'
  if (/(청구|지급|보험금|보상)/.test(text)) return 'claim'
  return 'general'
}

const buildSalesAnswer = (agent, questionType) => {
  const role = agent.role
  const soldWell = metrics.trust > 56 || metrics.consultRequests > agentStates.value.length * 0.2
  const lead = soldWell
    ? '네, 제 체감으로는 관심과 상담 문의는 확실히 붙고 있습니다'
    : '잘 팔린다고 단정하기보다는 문의는 생기는데 실제 가입 전환은 아직 걸리는 편입니다'
  const sellerView = `현장에서 보면 ${productDisplayName.value}은 암/심혈관 같은 큰 보장에는 반응이 있고, 4050이나 자녀가 있는 고객은 상담까지 오는 비율이 높습니다. 다만 마지막 체결은 월 보험료, 기존 보험 중복, 갱신 보험료 설명에서 갈립니다.`
  const consumerView = `제 주변 기준으로는 건강보험 필요성은 다들 느끼지만 바로 가입하는 사람은 많지 않습니다. 보험료가 납득되고 실제 청구 사례가 보이면 움직이고, 약관이나 개인정보 설명이 모호하면 커뮤니티 후기부터 봅니다.`
  const marketerView = `수치로 보면 인지도는 올라가도 전환 병목은 상담/가입 단계에 있습니다. 메시지는 먹히지만 보험료 부담과 개인정보 고지가 정리되지 않으면 판매량이 안정적으로 늘기 어렵습니다.`
  const view = role === '설계사'
    ? sellerView
    : role === '보험사'
      ? marketerView
      : consumerView
  const repairPrefix = questionType === 'repair'
    ? '맞아요, 방금 답은 질문에서 벗어났습니다. 판매가 잘 되느냐는 질문에 답하면, '
    : ''
  return `${repairPrefix}${lead}. ${view} 그래서 저는 "잘 팔린다"보다 "상담 유입은 좋고, 체결은 가격과 신뢰 설명에서 갈린다"에 가깝게 봅니다. 다음에는 실제 상담 대비 가입 전환율과 해지 신호를 같이 보고 싶습니다.`
}

const buildLocalAgentResponse = (agent, question) => {
  const persona = `${agent.profile.persona || agent.profile.bio || ''}`.replace(/\s+/g, ' ')
  const lower = question.toLowerCase()
  const turn = agent.chatMessages.filter(message => message.role === 'user').length
  const questionType = classifyQuestion(question, agent)
  const concern = agent.priceResistance >= agent.privacyConcern ? '보험료와 실제 보장 체감' : '개인정보 연동 조건'
  const familyFrame = persona.includes('가족') || persona.includes('자녀') || agent.segment.includes('가구')
  const trustFrame = agent.trust >= 58 ? '설명 자체는 어느 정도 믿고 있지만' : '아직 설명을 그대로 믿기는 어렵고'
  const priceFrame = agent.priceResistance >= 60 ? '월 보험료가 지금보다 올라가는 순간 바로 비교표를 다시 볼 것 같습니다' : '보험료가 크게 튀지 않는다면 보장 범위를 먼저 볼 것 같습니다'
  const dataFrame = agent.privacyConcern >= 55 ? '건강 데이터가 보험료 산정에 어떻게 쓰이는지가 제일 걸립니다' : '개인정보는 고지와 철회 방법만 분명하면 큰 장벽은 아닙니다'
  const nextCheck = familyFrame
    ? '가족 보장 공백과 기존 계약 해지 손실을 같이 확인하고 싶습니다'
    : agent.policyState === 'subscribed'
      ? '청구가 실제로 쉬운지와 갱신 보험료가 어떻게 바뀌는지를 확인하고 싶습니다'
      : '제가 내는 보험료 대비 실제 지급 사례를 먼저 확인하고 싶습니다'

  if (questionType === 'sales' || questionType === 'repair') {
    return buildSalesAnswer(agent, questionType)
  }

  if (questionType === 'cancel') {
    return `저는 ${concern}이 계속 흐릿하면 해지를 꽤 현실적으로 봅니다. 지금은 ${agent.policyLabel} 상태라서 이미 들어간 비용도 따지지만, ${trustFrame} 청구 경험이 나쁘면 마음이 빨리 식을 것 같아요. ${turn % 2 === 0 ? priceFrame : dataFrame}. 다음에는 ${nextCheck}.`
  }
  if (questionType === 'switch') {
    return `저라면 단순히 새 상품이 좋아 보인다고 바로 갈아타지는 않습니다. 기존 계약 해지 손실이 작고, 같은 보장에 보험료가 낮거나 청구 절차가 확실히 쉬울 때만 움직일 것 같아요. 제 성향상 ${agent.segment} 기준이 커서 ${familyFrame ? '가족 전체 보장 공백' : '약관 예외와 실제 지급 사례'}를 먼저 봅니다. 다음에는 ${nextCheck}.`
  }
  if (questionType === 'join') {
    return `제가 가입 쪽으로 기우는 건 보장이 좋아 보여서라기보다, 제 상황에서 의료비 리스크가 실제로 커졌다고 느낄 때입니다. 다만 ${priceFrame}, ${dataFrame}. 현재 의향은 ${Math.round(agent.intent)}점이라 아직은 조건부 판단에 가깝습니다. 다음에는 ${nextCheck}.`
  }
  if (questionType === 'privacy') {
    return `저는 개인정보를 약관 맨 아래 문장으로 처리하면 신뢰가 떨어집니다. 어떤 데이터가 들어가고, 철회하면 보장이나 보험료가 어떻게 되는지 따로 보여줘야 납득할 수 있어요. ${dataFrame}. 다음에는 실제 앱 화면에서 철회 경로가 어디 있는지 확인하고 싶습니다.`
  }
  if (questionType === 'claim') {
    return `청구가 쉬운지는 가입 판단에서 꽤 큽니다. 앱에서 서류가 얼마나 줄어드는지, 실제 지급까지 며칠 걸리는지, 거절 사례가 어떤 조건에서 나오는지를 봐야 해요. 그게 명확하면 보험료가 조금 높아도 납득할 수 있지만, 청구가 불편하면 유지가 어렵습니다. 다음에는 실제 청구 성공 사례를 확인하고 싶습니다.`
  }
  const variants = [
    `저는 지금 ${agent.policyLabel} 쪽으로 보고 있지만, 아직 결론이 고정된 건 아닙니다. ${trustFrame} ${concern}을 숫자와 사례로 확인해야 마음이 움직일 것 같아요. ${persona.slice(0, 90)} 이 맥락도 제 판단에 영향을 줍니다. 다음에는 ${nextCheck}.`,
    `제 입장에서는 광고 문구보다 가입 후 손해 볼 가능성이 더 중요합니다. ${priceFrame}. ${dataFrame}. 다음에는 ${nextCheck}.`,
    `지금 제 판단은 신뢰 ${Math.round(agent.trust)}점, 의향 ${Math.round(agent.intent)}점 정도라서 반쯤은 열려 있고 반쯤은 의심하는 상태입니다. ${concern}이 풀리면 상담을 더 들어보겠지만, 모호하면 커뮤니티 후기를 먼저 볼 겁니다. 다음에는 ${nextCheck}.`
  ]
  return variants[turn % variants.length]
}

const extractAgentChatText = (payload) => {
  const root = payload?.data || payload
  const response = root?.response || root?.data?.response || root?.message || root?.content
  return typeof response === 'string' ? response.trim() : ''
}

const buildAgentChatHistory = (agent) => {
  return agent.chatMessages
    .slice(0, -1)
    .slice(-12)
    .map(message => ({
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: message.text
    }))
}

const buildAgentChatRequest = (agent, question) => {
  const channel = CHANNELS.find(item => item.id === agent.targetChannelId)
  return {
    simulation_id: props.simulationId,
    simulation_requirement: props.projectData?.simulation_requirement || '',
    product_name: productDisplayName.value,
    current_time: currentCalendarLabel.value,
    message: question,
    chat_history: buildAgentChatHistory(agent),
    agent: {
      id: agent.profile.user_id ?? agent.id,
      name: agent.displayName,
      username: agent.profile.username,
      source_name: agent.profile.source_name,
      role: agent.role,
      segment: agent.segment,
      bio: agent.profile.bio,
      persona: agent.profile.persona,
      policy_label: agent.policyLabel,
      policy_state: agent.policyState,
      policy_product: agent.policyProduct,
      tenureWeeks: agent.tenureWeeks,
      last_action: agent.lastAction,
      channel: channel?.label || '이동 중',
      awareness: Math.round(agent.awareness),
      trust: Math.round(agent.trust),
      intent: Math.round(agent.intent),
      privacyConcern: Math.round(agent.privacyConcern),
      priceResistance: Math.round(agent.priceResistance),
      metrics: {
        awareness: Math.round(agent.awareness),
        trust: Math.round(agent.trust),
        intent: Math.round(agent.intent),
        privacyConcern: Math.round(agent.privacyConcern),
        priceResistance: Math.round(agent.priceResistance),
        tenureWeeks: agent.tenureWeeks
      }
    }
  }
}

const sendAgentChat = async () => {
  const agent = selectedAgent.value
  const question = chatDraft.value.trim()
  if (!agent || !question || chatBusy.value) return

  agent.chatMessages.push({
    id: `u-${Date.now()}`,
    role: 'user',
    text: question
  })
  chatDraft.value = ''
  chatBusy.value = true
  scrollChatToBottom()

  let answer = ''
  try {
    const request = chatWithSimulationAgent(buildAgentChatRequest(agent, question))
    const timeout = new Promise((_, reject) => {
      window.setTimeout(() => reject(new Error('agent chat timeout')), 22000)
    })
    const response = await Promise.race([request, timeout])
    answer = extractAgentChatText(response)
  } catch (error) {
    addLog(`Agent LLM 대화를 사용할 수 없어 로컬 페르소나 응답으로 전환했습니다: ${error.message}`)
  } finally {
    if (!answer) answer = buildLocalAgentResponse(agent, question)
    agent.chatMessages.push({
      id: `a-${Date.now()}`,
      role: 'assistant',
      text: answer
    })
    chatBusy.value = false
    scrollChatToBottom()
  }
}

const toggleRunning = () => {
  isRunning.value = !isRunning.value
  emit('update-status', isRunning.value ? 'processing' : 'completed')
  addLog(isRunning.value ? '보험 게임 자유행동을 재개했습니다' : '보험 게임 자유행동을 일시정지했습니다')
}

const resetWorld = () => {
  Object.values(channelStats).forEach(stat => {
    stat.visits = 0
    stat.conversations = 0
    stat.blocks = 0
    stat.conversions = 0
  })
  eventFeed.value = []
  currentRound.value = 0
  isRunning.value = true
  const profiles = agentStates.value.map(agent => agent.profile)
  initializeAgentStates(profiles.length ? profiles : buildSeedProfiles())
  if (scene) createAgentMeshes()
  addLog('보험 게임 공간을 초기 상태로 재배치했습니다')
}

const startDecisionTimer = () => {
  decisionTimer = window.setInterval(() => {
    if (isRunning.value) runDecisionTick()
  }, 1300)
}

watch(() => props.graphData, () => {
  if (!profilesLoadedFromApi.value && agentStates.value.length === 0 && scene) {
    const profiles = buildGraphFallbackProfiles()
    if (profiles.length) {
      profileSource.value = `graph ${profiles.length}`
      initializeAgentStates(profiles)
      createAgentMeshes()
      addLog(`그래프 엔티티 ${profiles.length}개를 보험 게임 공간에 배치했습니다`)
    }
  }
})

watch(() => selectedAgent.value?.id, () => {
  scrollChatToBottom()
})

watch(() => selectedAgent.value?.chatMessages?.length, () => {
  scrollChatToBottom()
})

onMounted(async () => {
  emit('update-status', 'processing')
  addLog('보험 시뮬레이션 게임 공간을 초기화합니다')
  await nextTick()
  if (new URLSearchParams(window.location.search).get('view') === 'player') {
    isPlayerMode.value = true
  }
  initThree()
  await Promise.all([loadConfig(), loadProfiles()])
  createAgentMeshes()
  bootstrapInitialEvents()
  animate()
  startDecisionTimer()
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  addLog('3D 보험 시뮬레이션 게임 공간이 준비되었습니다')
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  if (decisionTimer) window.clearInterval(decisionTimer)
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeObserver) resizeObserver.disconnect()
  clearAgentMeshes()
  if (scene) {
    scene.traverse(object => {
      if (!agentMeshes.has(object.userData?.agentId)) {
        if (object.geometry) object.geometry.dispose()
        if (object.material) {
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach(material => {
            if (material.map) material.map.dispose()
            material.dispose()
          })
        }
      }
    })
  }
  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
  }
})
</script>

<style scoped>
.game-space {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #F8FAFC;
  color: #111827;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  overflow: hidden;
}

.top-strip {
  min-height: 84px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(420px, 1.6fr) auto;
  gap: 18px;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
}

.title-group {
  min-width: 0;
}

.eyebrow {
  display: block;
  font-size: 11px;
  font-weight: 800;
  color: #64748B;
  letter-spacing: 0;
  margin-bottom: 5px;
}

h1 {
  font-size: 22px;
  line-height: 1.15;
  margin: 0;
  color: #020617;
  overflow-wrap: anywhere;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(8, minmax(70px, 1fr));
  gap: 8px;
  min-width: 0;
}

.kpi-card {
  border: 1px solid #E5E7EB;
  background: #F8FAFC;
  border-radius: 6px;
  padding: 8px 10px;
  min-width: 0;
}

.kpi-label {
  display: block;
  font-size: 11px;
  color: #64748B;
  font-weight: 700;
  margin-bottom: 4px;
}

.kpi-card strong {
  display: block;
  font-size: 16px;
  line-height: 1;
  color: #111827;
  white-space: nowrap;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

button {
  border: none;
  cursor: pointer;
  font-weight: 800;
  border-radius: 6px;
  transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease;
}

button:active {
  transform: translateY(1px);
}

.ghost-btn,
.primary-btn {
  height: 38px;
  padding: 0 14px;
  font-size: 13px;
  white-space: nowrap;
}

.ghost-btn {
  background: #F1F5F9;
  color: #334155;
  border: 1px solid #E2E8F0;
}

.ghost-btn:hover {
  background: #E2E8F0;
}

.primary-btn {
  background: #111827;
  color: #FFFFFF;
}

.primary-btn:hover {
  background: #000000;
}

.game-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
}

.scene-panel {
  position: relative;
  min-width: 0;
  overflow: hidden;
  background: #DCECF4;
}

.scene-host {
  width: 100%;
  height: 100%;
  cursor: grab;
  touch-action: none;
  outline: none;
}

.scene-host:active {
  cursor: grabbing;
}

.scene-host:focus {
  outline: none;
}

.scene-host :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}

.scene-overlay {
  position: absolute;
  z-index: 2;
  pointer-events: auto;
}

.channel-legend {
  top: 14px;
  left: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: calc(100% - 28px);
}

.channel-chip {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.9);
  color: #1F2937;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
  font-size: 12px;
}

.chip-swatch,
.row-swatch {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex: 0 0 auto;
}

.world-meta {
  left: 14px;
  bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-pill {
  height: 30px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.86);
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 800;
}

.timeline-control {
  right: 14px;
  top: 14px;
  width: min(360px, calc(100% - 28px));
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
  padding: 10px;
}

.timeline-control-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.timeline-control-head span,
.timeline-control-head strong {
  font-size: 12px;
  font-weight: 900;
  color: #0F172A;
}

.timeline-bar {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #E2E8F0;
}

.timeline-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #059669, #0891B2);
}

.timeline-targets {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 8px;
}

.target-btn {
  height: 28px;
  background: #F8FAFC;
  color: #475569;
  border: 1px solid #E2E8F0;
  font-size: 12px;
}

.target-btn.active {
  background: #111827;
  color: #FFFFFF;
  border-color: #111827;
}

.speed-control {
  right: 14px;
  bottom: 14px;
  display: flex;
  gap: 6px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 8px;
  padding: 5px;
}

.speed-btn {
  min-width: 42px;
  height: 30px;
  background: transparent;
  color: #475569;
  font-size: 12px;
}

.mode-btn {
  min-width: 68px;
}

.speed-btn.active {
  background: #111827;
  color: #FFFFFF;
}

.player-reticle {
  left: 50%;
  top: 50%;
  width: 22px;
  height: 22px;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.player-reticle::before,
.player-reticle::after {
  content: '';
  position: absolute;
  background: rgba(15, 23, 42, 0.72);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.62);
}

.player-reticle::before {
  left: 10px;
  top: 2px;
  width: 2px;
  height: 18px;
}

.player-reticle::after {
  left: 2px;
  top: 10px;
  width: 18px;
  height: 2px;
}

.inspector {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  background: #FFFFFF;
  border-left: 1px solid #E5E7EB;
  overflow-y: auto;
}

.inspector-section {
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #FFFFFF;
  padding: 12px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.section-title {
  font-size: 11px;
  font-weight: 900;
  color: #64748B;
}

.section-count {
  font-size: 11px;
  font-weight: 800;
  color: #334155;
  background: #F1F5F9;
  border-radius: 999px;
  padding: 4px 8px;
}

.agent-headline {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.agent-avatar,
.mini-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  overflow: hidden;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
}

.agent-avatar {
  width: 52px;
  height: 52px;
  border-radius: 8px;
}

.agent-avatar img,
.mini-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.agent-headline strong,
.agent-headline span {
  display: block;
  min-width: 0;
}

.agent-headline strong {
  font-size: 15px;
  color: #020617;
  overflow-wrap: anywhere;
}

.agent-headline span {
  margin-top: 3px;
  font-size: 12px;
  color: #64748B;
}

.agent-state-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.state-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #334155;
  font-size: 11px;
  font-weight: 900;
}

.state-pill.policy-subscribed,
.state-pill.policy-retained {
  background: #DCFCE7;
  color: #166534;
}

.state-pill.policy-switched {
  background: #EDE9FE;
  color: #5B21B6;
}

.state-pill.policy-cancelled {
  background: #FEE2E2;
  color: #991B1B;
}

.agent-bio {
  margin: 10px 0;
  font-size: 12px;
  line-height: 1.55;
  color: #475569;
  max-height: 96px;
  overflow: auto;
}

.agent-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.agent-metrics span {
  background: #F8FAFC;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 7px 8px;
  font-size: 12px;
  color: #334155;
  font-weight: 700;
}

.agent-chat {
  margin-top: 10px;
  border-top: 1px solid #E5E7EB;
  padding-top: 10px;
}

.chat-log {
  max-height: 150px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 2px;
  scroll-behavior: smooth;
}

.chat-message {
  display: grid;
  gap: 3px;
}

.chat-message span {
  font-size: 10px;
  font-weight: 900;
  color: #64748B;
}

.chat-message p {
  margin: 0;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 8px 9px;
  color: #334155;
  background: #F8FAFC;
  font-size: 12px;
  line-height: 1.45;
}

.chat-message.user p {
  background: #111827;
  color: #FFFFFF;
  border-color: #111827;
}

.chat-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 56px;
  gap: 6px;
  margin-top: 8px;
}

.chat-form input {
  min-width: 0;
  height: 34px;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 0 9px;
  color: #0F172A;
  background: #FFFFFF;
  font-size: 12px;
}

.chat-form button {
  height: 34px;
  background: #0F172A;
  color: #FFFFFF;
  font-size: 12px;
}

.chat-form button:disabled,
.chat-form input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.agent-history {
  display: grid;
  gap: 7px;
  margin: 10px 0 2px;
}

.history-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #0F172A;
  font-size: 11px;
  font-weight: 900;
}

.history-title strong {
  color: #64748B;
}

.history-line {
  border: 1px solid #E5E7EB;
  border-radius: 7px;
  background: #F8FAFC;
  padding: 8px;
}

.history-line span,
.history-line small {
  display: block;
  color: #64748B;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.35;
}

.history-line p {
  margin: 4px 0;
  color: #0F172A;
  font-size: 12px;
  line-height: 1.45;
}

.empty-agent {
  min-height: 86px;
  display: flex;
  align-items: center;
  color: #94A3B8;
  font-size: 13px;
  line-height: 1.45;
}

.channel-row,
.agent-row {
  width: 100%;
  min-width: 0;
  display: grid;
  align-items: center;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  color: #111827;
}

.channel-row {
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  min-height: 46px;
  padding: 7px 9px;
  margin-top: 6px;
}

.channel-row:hover,
.agent-row:hover,
.agent-row.active {
  background: #F8FAFC;
  border-color: #CBD5E1;
}

.channel-row.active {
  background: #F1F5F9;
  border-color: #94A3B8;
}

.channel-role,
.channel-outcome {
  display: grid;
  gap: 5px;
  border: 1px solid #E5E7EB;
  border-radius: 7px;
  background: #F8FAFC;
  padding: 9px;
  margin-bottom: 9px;
}

.channel-role strong,
.channel-outcome strong {
  color: #0F172A;
  font-size: 12px;
  line-height: 1.35;
}

.channel-detail p,
.channel-role p,
.channel-outcome p,
.summary-actions p,
.summary-lead {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.channel-detail-grid,
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
  margin-top: 10px;
}

.summary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.channel-detail-grid span,
.summary-grid span {
  border: 1px solid #E5E7EB;
  border-radius: 7px;
  background: #F8FAFC;
  padding: 8px;
  min-width: 0;
}

.channel-detail-grid small,
.summary-grid small {
  display: block;
  color: #64748B;
  font-size: 10px;
  font-weight: 900;
  margin-bottom: 4px;
}

.channel-detail-grid strong,
.summary-grid strong {
  display: block;
  color: #0F172A;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.signal-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.signal-list span {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  background: #EEF2FF;
  color: #3730A3;
  font-size: 11px;
  font-weight: 900;
}

.channel-events {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.channel-events p {
  border-left: 3px solid #CBD5E1;
  padding-left: 8px;
}

.channel-events strong,
.channel-events span {
  display: block;
  font-size: 12px;
  line-height: 1.42;
}

.channel-events strong {
  color: #0F172A;
  margin-bottom: 2px;
}

.channel-events span {
  color: #475569;
}

.result-summary {
  border-color: #A7F3D0;
  background: #F0FDF4;
}

.summary-actions {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.summary-actions p {
  border-left: 3px solid #10B981;
  padding-left: 8px;
}

.row-copy,
.row-label,
.agent-row-name {
  min-width: 0;
}

.row-copy {
  display: grid;
  gap: 2px;
}

.row-copy small {
  color: #64748B;
  font-size: 10px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-label,
.agent-row-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.row-count,
.agent-row-funnel {
  color: #64748B;
  font-size: 12px;
  font-weight: 800;
}

.agent-list {
  max-height: 290px;
  overflow: auto;
}

.agent-row {
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  min-height: 38px;
  padding: 6px 8px;
  margin-top: 6px;
}

.mini-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
}

.agent-row-name {
  font-size: 12px;
  font-weight: 800;
}

.event-feed {
  flex: 1;
  min-height: 230px;
}

.event-item {
  border-top: 1px solid #E5E7EB;
  padding: 10px 0;
}

.event-item:first-of-type {
  border-top: none;
}

.event-time {
  display: block;
  margin-bottom: 4px;
  color: #94A3B8;
  font-size: 11px;
  font-weight: 800;
}

.event-item strong {
  display: block;
  color: #020617;
  font-size: 13px;
  margin-bottom: 4px;
  overflow-wrap: anywhere;
}

.event-item p {
  color: #475569;
  font-size: 12px;
  line-height: 1.45;
  margin: 0 0 6px;
}

.event-dialogue {
  color: #111827 !important;
  background: #F8FAFC;
  border: 1px solid #E5E7EB;
  border-radius: 7px;
  padding: 7px 8px;
}

.event-reason {
  color: #64748B !important;
}

.event-tag {
  display: inline-flex;
  color: #334155;
  background: #F1F5F9;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 800;
}

@media (max-width: 1180px) {
  .top-strip {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .top-actions {
    justify-content: flex-end;
  }

  .game-layout {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 1fr) 330px;
  }

  .inspector {
    border-left: none;
    border-top: 1px solid #E5E7EB;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow-y: auto;
  }
}

@media (max-width: 760px) {
  .top-strip {
    padding: 8px 10px;
    gap: 8px;
  }

  h1 {
    font-size: 17px;
    line-height: 1.2;
  }

  .kpi-strip {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .kpi-card {
    flex: 0 0 96px;
    padding: 6px 8px;
  }

  .kpi-label {
    font-size: 10px;
    margin-bottom: 3px;
  }

  .kpi-card strong {
    font-size: 15px;
  }

  .top-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
  }

  .ghost-btn,
  .primary-btn {
    height: 32px;
    padding: 0 8px;
    font-size: 11px;
  }

  .game-layout {
    grid-template-rows: minmax(280px, 1fr) 330px;
  }

  .inspector {
    grid-template-columns: 1fr;
  }

  .channel-legend {
    right: 10px;
    left: 10px;
  }

  .timeline-control {
    top: auto;
    right: 10px;
    left: 10px;
    bottom: 54px;
    width: auto;
  }

  .world-meta {
    display: none;
  }

  .channel-chip {
    height: 30px;
    font-size: 11px;
  }
}
</style>
