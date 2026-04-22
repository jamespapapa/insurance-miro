<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <!-- Step 01: 시뮬레이션 인스턴스 -->
      <div class="step-card" :class="{ 'active': phase === 0, 'completed': phase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">시뮬레이션 인스턴스 초기화</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 0" class="badge success">완료</span>
            <span v-else class="badge processing">초기화</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">
            simulation 인스턴스를 새로 만들고, 시뮬레이션 세계 파라미터 템플릿을 가져옵니다
          </p>

          <div v-if="simulationId" class="info-card">
            <div class="info-row">
              <span class="info-label">Project ID</span>
              <span class="info-value mono">{{ projectData?.project_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Graph ID</span>
              <span class="info-value mono">{{ projectData?.graph_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Simulation ID</span>
              <span class="info-value mono">{{ simulationId }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Task ID</span>
              <span class="info-value mono">{{ taskId || '비동기 작업이 완료되었습니다' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Agent 페르소나 생성 -->
      <div class="step-card" :class="{ 'active': phase === 1, 'completed': phase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">Agent 페르소나 생성</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 1" class="badge success">완료</span>
            <span v-else-if="phase === 1" class="badge processing">{{ prepareProgress }}%</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            컨텍스트를 결합해 도구를 자동 호출하여 지식 그래프에서 엔터티와 관계를 정리하고, 시뮬레이션 개체를 초기화하며, 현실 시드를 기반으로 각자에게 독특한 행동과 기억을 부여합니다
          </p>

          <!-- Profiles Stats -->
          <div v-if="profiles.length > 0" class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ profiles.length }}</span>
              <span class="stat-label">현재 Agent 수</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ expectedTotal || '-' }}</span>
              <span class="stat-label">예상 Agent 총수</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ totalTopicsCount }}</span>
              <span class="stat-label">현실 시드의 현재 연관 토픽 수</span>
            </div>
          </div>

          <!-- Profiles List Preview -->
          <div v-if="profiles.length > 0" class="profiles-preview">
            <div class="preview-header">
              <span class="preview-title">생성된 Agent 페르소나</span>
            </div>
            <div class="profiles-list">
              <div 
                v-for="(profile, idx) in profiles" 
                :key="idx" 
                class="profile-card"
                @click="selectProfile(profile)"
              >
                <div class="profile-header">
                  <span class="profile-realname">{{ profile.username || 'Unknown' }}</span>
                  <span class="profile-username">@{{ profile.name || `agent_${idx}` }}</span>
                </div>
                <div class="profile-meta">
                  <span class="profile-profession">{{ profile.profession || '알 수 없는 직업' }}</span>
                </div>
                <p class="profile-bio">{{ profile.bio || '소개 없음' }}</p>
                <div v-if="profile.interested_topics?.length" class="profile-topics">
                  <span 
                    v-for="topic in profile.interested_topics.slice(0, 3)" 
                    :key="topic" 
                    class="topic-tag"
                  >{{ topic }}</span>
                  <span v-if="profile.interested_topics.length > 3" class="topic-more">
                    +{{ profile.interested_topics.length - 3 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: 양 플랫폼 시뮬레이션 구성 생성 -->
      <div class="step-card" :class="{ 'active': phase === 2, 'completed': phase > 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">양 플랫폼 시뮬레이션 구성 생성</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 2" class="badge success">완료</span>
            <span v-else-if="phase === 2" class="badge processing">생성 중</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            LLM은 시뮬레이션 요구와 현실 시드를 바탕으로 세계 시간 흐름 속도, 추천 알고리즘, 각 개체의 활동 시간대, 발언 빈도, 이벤트 트리거 등 파라미터를 지능적으로 설정합니다
          </p>
          
          <!-- Config Preview -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <!-- 시간 구성 -->
            <div class="config-block">
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-item-label">시뮬레이션 기간</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.total_simulation_hours || '-' }} 시간</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">라운드당 시간</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.minutes_per_round || '-' }} 분</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">총 라운드 수</span>
                  <span class="config-item-value">{{ Math.floor((simulationConfig.time_config?.total_simulation_hours * 60 / simulationConfig.time_config?.minutes_per_round)) || '-' }} 회</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">시간당 활성</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.agents_per_hour_min }}-{{ simulationConfig.time_config?.agents_per_hour_max }}</span>
                </div>
              </div>
              <div class="time-periods">
                <div class="period-item">
                  <span class="period-label">피크 시간대</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.peak_hours?.join(':00, ') }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.peak_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">근무 시간대</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.work_hours?.[0] }}:00-{{ simulationConfig.time_config?.work_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.work_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">아침 시간대</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.morning_hours?.[0] }}:00-{{ simulationConfig.time_config?.morning_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.morning_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">비수 시간대</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.off_peak_hours?.[0] }}:00-{{ simulationConfig.time_config?.off_peak_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.off_peak_activity_multiplier }}</span>
                </div>
              </div>
            </div>

            <!-- Agent 구성 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">Agent 구성</span>
                <span class="config-block-badge">{{ simulationConfig.agent_configs?.length || 0 }} 개</span>
              </div>
              <div class="agents-cards">
                <div 
                  v-for="agent in simulationConfig.agent_configs" 
                  :key="agent.agent_id" 
                  class="agent-card"
                >
                  <!-- 카드 헤더 -->
                  <div class="agent-card-header">
                    <div class="agent-identity">
                      <span class="agent-id">Agent {{ agent.agent_id }}</span>
                      <span class="agent-name">{{ agent.entity_name }}</span>
                    </div>
                    <div class="agent-tags">
                      <span class="agent-type">{{ agent.entity_type }}</span>
                      <span class="agent-stance" :class="'stance-' + agent.stance">{{ agent.stance }}</span>
                    </div>
                  </div>
                  
                  <!-- 활동 타임라인 -->
                  <div class="agent-timeline">
                    <span class="timeline-label">활동 시간대</span>
                    <div class="mini-timeline">
                      <div 
                        v-for="hour in 24" 
                        :key="hour - 1" 
                        class="timeline-hour"
                        :class="{ 'active': agent.active_hours?.includes(hour - 1) }"
                        :title="`${hour - 1}:00`"
                      ></div>
                    </div>
                    <div class="timeline-marks">
                      <span>0</span>
                      <span>6</span>
                      <span>12</span>
                      <span>18</span>
                      <span>24</span>
                    </div>
                  </div>

                  <!-- 행동 파라미터 -->
                  <div class="agent-params">
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">게시/시간</span>
                        <span class="param-value">{{ agent.posts_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">댓글/시간</span>
                        <span class="param-value">{{ agent.comments_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">응답 지연</span>
                        <span class="param-value">{{ agent.response_delay_min }}-{{ agent.response_delay_max }}min</span>
                      </div>
                    </div>
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">활동성</span>
                        <span class="param-value with-bar">
                          <span class="mini-bar" :style="{ width: (agent.activity_level * 100) + '%' }"></span>
                          {{ (agent.activity_level * 100).toFixed(0) }}%
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">감정 성향</span>
                        <span class="param-value" :class="agent.sentiment_bias > 0 ? 'positive' : agent.sentiment_bias < 0 ? 'negative' : 'neutral'">
                          {{ agent.sentiment_bias > 0 ? '+' : '' }}{{ agent.sentiment_bias?.toFixed(1) }}
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">영향력</span>
                        <span class="param-value highlight">{{ agent.influence_weight?.toFixed(1) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 플랫폼 설정 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">추천 알고리즘 설정</span>
              </div>
              <div class="platforms-grid">
                <div v-if="simulationConfig.twitter_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">플랫폼 1: 광장 / 피드</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">최신성 가중치</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">인기 가중치</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">관련성 가중치</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">바이럴 임계값</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">에코 챔버 강도</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="simulationConfig.reddit_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">플랫폼 2: 주제 / 커뮤니티</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">최신성 가중치</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">인기 가중치</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">관련성 가중치</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">바이럴 임계값</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">에코 챔버 강도</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- LLM 설정 추론 -->
            <div v-if="simulationConfig.generation_reasoning" class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">LLM 설정 추론</span>
              </div>
              <div class="reasoning-content">
                <div 
                  v-for="(reason, idx) in simulationConfig.generation_reasoning.split('|').slice(0, 2)" 
                  :key="idx" 
                  class="reasoning-item"
                >
                  <p class="reasoning-text">{{ reason.trim() }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 04: 초기 활성화 오케스트레이션 -->
      <div class="step-card" :class="{ 'active': phase === 3, 'completed': phase > 3 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">초기 활성화 오케스트레이션</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 3" class="badge success">완료됨</span>
            <span v-else-if="phase === 3" class="badge processing">오케스트레이션 중</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            내러티브 방향에 기반하여 초기 활성화 이벤트와 핫 토픽을 자동 생성하고, 시뮬레이션 세계의 초기 상태를 유도합니다
          </p>

          <div v-if="simulationConfig?.event_config" class="orchestration-content">
            <!-- 내러티브 방향 -->
            <div class="narrative-box">
              <span class="box-label narrative-label">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="special-icon">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M16.24 7.76L14.12 14.12L7.76 16.24L9.88 9.88L16.24 7.76Z" fill="url(#paint0_linear)" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <defs>
                    <linearGradient id="paint0_linear" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#FF5722"/>
                      <stop offset="1" stop-color="#FF9800"/>
                    </linearGradient>
                  </defs>
                </svg>
                내러티브 유도 방향
              </span>
              <p class="narrative-text">{{ simulationConfig.event_config.narrative_direction }}</p>
            </div>

            <!-- 핫 토픽 -->
            <div class="topics-section">
              <span class="box-label">초기 핫 토픽</span>
              <div class="hot-topics-grid">
                <span v-for="topic in simulationConfig.event_config.hot_topics" :key="topic" class="hot-topic-tag">
                  # {{ topic }}
                </span>
              </div>
            </div>

            <!-- 초기 게시물 스트림 -->
            <div class="initial-posts-section">
              <span class="box-label">초기 활성화 시퀀스 ({{ simulationConfig.event_config.initial_posts.length }})</span>
              <div class="posts-timeline">
                <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="timeline-item">
                  <div class="timeline-marker"></div>
                  <div class="timeline-content">
                    <div class="post-header">
                      <span class="post-role">{{ post.poster_type }}</span>
                      <span class="post-agent-info">
                        <span class="post-id">Agent {{ post.poster_agent_id }}</span>
                        <span class="post-username">@{{ getAgentUsername(post.poster_agent_id) }}</span>
                      </span>
                    </div>
                    <p class="post-text">{{ post.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 05: 준비 완료 -->
      <div class="step-card" :class="{ 'active': phase === 4 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">05</span>
            <span class="step-title">준비 완료</span>
          </div>
          <div class="step-status">
            <span v-if="phase >= 4" class="badge processing">진행 중</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/start</p>
          <p class="description">시뮬레이션 환경이 준비 완료되어 시뮬레이션을 시작할 수 있습니다</p>

          <div v-if="simulationConfig" class="insurance-preflight">
            <div class="preflight-header">
              <div class="preflight-title-group">
                <span class="preflight-eyebrow">INSURANCE SALES SIMULATION</span>
                <h3 class="preflight-title">신상품 판매 시뮬레이션 작업대</h3>
                <p class="preflight-summary">{{ preflightSummary }}</p>
              </div>
              <div class="preflight-status">
                <span class="status-pulse"></span>
                <span>WORLD READY</span>
              </div>
            </div>

            <div class="preflight-metrics">
              <div class="metric-strip-item">
                <span class="metric-strip-label">상품</span>
                <span class="metric-strip-value">{{ productDisplayName }}</span>
              </div>
              <div class="metric-strip-item">
                <span class="metric-strip-label">Agent</span>
                <span class="metric-strip-value mono">{{ agentSegmentCount }}</span>
              </div>
              <div class="metric-strip-item">
                <span class="metric-strip-label">채널</span>
                <span class="metric-strip-value mono">{{ salesChannels.length }}</span>
              </div>
              <div class="metric-strip-item">
                <span class="metric-strip-label">KPI</span>
                <span class="metric-strip-value mono">{{ preflightKpis.length }}</span>
              </div>
            </div>

            <div class="preflight-layout">
              <section class="preflight-section product-section">
                <div class="section-heading-row">
                  <span class="preflight-section-title">상품 메시지 축</span>
                  <span class="section-chip">DRAFT</span>
                </div>
                <div class="message-axis-list">
                  <div v-for="axis in messageAxes" :key="axis.label" class="message-axis">
                    <span class="axis-label">{{ axis.label }}</span>
                    <span class="axis-value">{{ axis.value }}</span>
                  </div>
                </div>
              </section>

              <section class="preflight-section funnel-section">
                <div class="section-heading-row">
                  <span class="preflight-section-title">판매 Funnel</span>
                  <span class="section-chip">PRE-RUN</span>
                </div>
                <div class="funnel-track">
                  <div v-for="stage in salesFunnelStages" :key="stage.name" class="funnel-stage">
                    <span class="stage-index">{{ stage.index }}</span>
                    <span class="stage-name">{{ stage.name }}</span>
                    <span class="stage-signal">{{ stage.signal }}</span>
                  </div>
                </div>
              </section>
            </div>

            <section class="preflight-section">
              <div class="section-heading-row">
                <span class="preflight-section-title">채널 레이어</span>
                <span class="section-chip">4 LANES</span>
              </div>
              <div class="channel-lanes">
                <div v-for="channel in salesChannels" :key="channel.name" class="channel-lane">
                  <div class="channel-lane-head">
                    <span class="channel-name">{{ channel.name }}</span>
                    <span class="channel-type">{{ channel.type }}</span>
                  </div>
                  <p class="channel-role">{{ channel.role }}</p>
                  <span class="channel-signal">{{ channel.signal }}</span>
                </div>
              </div>
            </section>

            <section class="preflight-section">
              <div class="section-heading-row">
                <span class="preflight-section-title">관측 KPI</span>
                <span class="section-chip">BASELINE</span>
              </div>
              <div class="kpi-grid">
                <div v-for="kpi in preflightKpis" :key="kpi.label" class="kpi-item">
                  <span class="kpi-label">{{ kpi.label }}</span>
                  <span class="kpi-value">{{ kpi.value }}</span>
                  <span class="kpi-desc">{{ kpi.desc }}</span>
                </div>
              </div>
            </section>

            <section class="preflight-section">
              <div class="section-heading-row">
                <span class="preflight-section-title">개입 시나리오 슬롯</span>
                <span class="section-chip">QUEUE</span>
              </div>
              <div class="intervention-row">
                <div v-for="item in interventionSlots" :key="item.time" class="intervention-item">
                  <span class="intervention-time">{{ item.time }}</span>
                  <span class="intervention-name">{{ item.name }}</span>
                  <span class="intervention-target">{{ item.target }}</span>
                </div>
              </div>
            </section>
          </div>
          
          <!-- 시뮬레이션 라운드 수 설정 - 설정 생성이 완료되고 라운드 수가 계산된 후에만 표시 -->
          <div v-if="simulationConfig && autoGeneratedRounds" class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">시뮬레이션 회차 설정</span>
                <span class="section-desc">MiroFish 자동 계획 시뮬레이션은 현실 <span class="desc-highlight">{{ simulationConfig?.time_config?.total_simulation_hours || '-' }}</span> 시간 동안 진행되며, 각 회차는 현실 시간 <span class="desc-highlight">{{ simulationConfig?.time_config?.minutes_per_round || '-' }}</span> 분의 시간 경과를 의미합니다</span>
              </div>
              <label class="switch-control">
                <input type="checkbox" v-model="useCustomRounds">
                <span class="switch-track"></span>
                <span class="switch-label">사용자 지정</span>
              </label>
            </div>
            
            <Transition name="fade" mode="out-in">
              <div v-if="useCustomRounds" class="rounds-content custom" key="custom">
                <div class="slider-display">
                  <div class="slider-main-value">
                    <span class="val-num">{{ customMaxRounds }}</span>
                    <span class="val-unit">회</span>
                  </div>
                  <div class="slider-meta-info">
                    <span>Agent 규모가 100일 경우: 예상 소요 시간 약 {{ Math.round(customMaxRounds * 0.6) }} 분</span>
                  </div>
                </div>

                <div class="range-wrapper">
                  <input 
                    type="range" 
                    v-model.number="customMaxRounds" 
                    min="10" 
                    :max="autoGeneratedRounds"
                    step="5"
                    class="minimal-slider"
                    :style="{ '--percent': ((customMaxRounds - 10) / (autoGeneratedRounds - 10)) * 100 + '%' }"
                  />
                  <div class="range-marks">
                    <span>10</span>
                    <span 
                      class="mark-recommend" 
                      :class="{ active: customMaxRounds === 40 }"
                      @click="customMaxRounds = 40"
                      :style="{ position: 'absolute', left: `calc(${(40 - 10) / (autoGeneratedRounds - 10) * 100}% - 30px)` }"
                    >40 (추천)</span>
                    <span>{{ autoGeneratedRounds }}</span>
                  </div>
                </div>
              </div>
              
              <div v-else class="rounds-content auto" key="auto">
                <div class="auto-info-card">
                  <div class="auto-value">
                    <span class="val-num">{{ autoGeneratedRounds }}</span>
                    <span class="val-unit">회</span>
                  </div>
                  <div class="auto-content">
                    <div class="auto-meta-row">
                      <span class="duration-badge">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        Agent 규모가 100일 경우: 예상 소요 시간 {{ Math.round(autoGeneratedRounds * 0.6) }} 분
                      </span>
                    </div>
                    <div class="auto-desc">
                      <p class="highlight-tip" @click="useCustomRounds = true">첫 실행이라면, ‘사용자 지정 모드’로 전환해 시뮬레이션 회차를 줄이는 것을 강력히 권장합니다. 빠르게 효과를 미리 보고 오류 위험을 낮출 수 있습니다 ➝</p>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <div class="action-group dual">
            <button 
              class="action-btn secondary"
              @click="$emit('go-back')"
            >
              ← 그래프 구축으로 돌아가기
            </button>
            <button 
              class="action-btn primary"
              :disabled="phase < 4"
              @click="handleStartSimulation"
            >
              두 세계 병렬 시뮬레이션 시작 ➝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div v-if="selectedProfile" class="profile-modal-overlay" @click.self="selectedProfile = null">
        <div class="profile-modal">
          <div class="modal-header">
          <div class="modal-header-info">
            <div class="modal-name-row">
              <span class="modal-realname">{{ selectedProfile.username }}</span>
              <span class="modal-username">@{{ selectedProfile.name }}</span>
            </div>
            <span class="modal-profession">{{ selectedProfile.profession }}</span>
          </div>
          <button class="close-btn" @click="selectedProfile = null">×</button>
        </div>
        
        <div class="modal-body">
          <!-- 기본 정보 -->
          <div class="modal-info-grid">
            <div class="info-item">
              <span class="info-label">사건 외현 나이</span>
              <span class="info-value">{{ selectedProfile.age || '-' }} 세</span>
            </div>
            <div class="info-item">
              <span class="info-label">사건 외현 성별</span>
              <span class="info-value">{{ { male: '남', female: '여', other: '기타' }[selectedProfile.gender] || selectedProfile.gender }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">국가/지역</span>
              <span class="info-value">{{ selectedProfile.country || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">사건 외현 MBTI</span>
              <span class="info-value mbti">{{ selectedProfile.mbti || '-' }}</span>
            </div>
          </div>

          <!-- 소개 -->
          <div class="modal-section">
            <span class="section-label">인물 설정 소개</span>
            <p class="section-bio">{{ selectedProfile.bio || '소개 없음' }}</p>
          </div>

          <!-- 관심 주제 -->
          <div class="modal-section" v-if="selectedProfile.interested_topics?.length">
            <span class="section-label">현실 시드 연관 주제</span>
            <div class="topics-grid">
              <span 
                v-for="topic in selectedProfile.interested_topics" 
                :key="topic" 
                class="topic-item"
              >{{ topic }}</span>
            </div>
          </div>

          <!-- 상세 인물 설정 -->
          <div class="modal-section" v-if="selectedProfile.persona">
            <span class="section-label">상세 인물 설정 배경</span>
            
            <!-- 인물 설정 차원 개요 -->
            <div class="persona-dimensions">
              <div class="dimension-card">
                <span class="dim-title">사건 전경 경험</span>
                <span class="dim-desc">이 사건에서의 완전한 행동 궤적</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">행동 패턴 프로파일링</span>
                <span class="dim-desc">경험 정리와 처신 스타일 선호</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">독특한 기억 각인</span>
                <span class="dim-desc">현실 시드를 기반으로 형성된 기억</span>
              </div>
              <div class="dimension-card">
                <span class="dim-title">사회 관계 네트워크</span>
                <span class="dim-desc">개인 연결과 상호작용 그래프</span>
              </div>
            </div>

            <div class="persona-content">
              <p class="section-persona">{{ selectedProfile.persona }}</p>
            </div>
          </div>
        </div>
      </div>
      </div>
    </Transition>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { 
  prepareSimulation, 
  getPrepareStatus, 
  getSimulationProfilesRealtime,
  getSimulationConfig,
  getSimulationConfigRealtime 
} from '../api/simulation'

const props = defineProps({
  simulationId: String,  // 부모 컴포넌트에서 전달
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

// State
const phase = ref(0) // 0: 초기화, 1: 인물 설정 생성, 2: 설정 생성, 3: 완료
const taskId = ref(null)
const prepareProgress = ref(0)
const currentStage = ref('')
const progressMessage = ref('')
const profiles = ref([])
const entityTypes = ref([])
const expectedTotal = ref(null)
const simulationConfig = ref(null)
const selectedProfile = ref(null)
const showProfilesDetail = ref(true)

// 로그 중복 제거: 이전 출력의 핵심 정보를 기록
let lastLoggedMessage = ''
let lastLoggedProfileCount = 0
let lastLoggedConfigStage = ''

// 시뮬레이션 라운드 수 설정
const useCustomRounds = ref(false) // 기본값은 자동 설정 라운드 수 사용
const customMaxRounds = ref(40)   // 기본 추천 40라운드

const salesFunnelStages = [
  { index: '01', name: '인지', signal: '노출/화제화' },
  { index: '02', name: '관심', signal: '보장/보험료 질문' },
  { index: '03', name: '비교', signal: '약관/경쟁상품 검증' },
  { index: '04', name: '상담', signal: '설계사/앱 견적' },
  { index: '05', name: '가입의향', signal: '신뢰/가격 저항' }
]

const salesChannels = [
  {
    name: '공식/디지털',
    type: 'OWNED',
    role: '상품 메시지, 약관 요약, 앱 가입/청구 UX',
    signal: '이해도와 신뢰의 기준선'
  },
  {
    name: '설계사/GA',
    type: 'SALES',
    role: '상담 스크립트, 반론 처리, 가족 보장 설계',
    signal: '상담 전환과 과장 리스크'
  },
  {
    name: '커뮤니티',
    type: 'SOCIAL',
    role: '맘카페, 직장인, 재테크, 보험 커뮤니티 검증',
    signal: '가격 저항과 후기 확산'
  },
  {
    name: '미디어/인플루언서',
    type: 'EARNED',
    role: '출시 프레임, 비교 콘텐츠, 전문가 해설',
    signal: '초기 프레임과 재평가 트리거'
  }
]

const preflightKpis = [
  { label: '인지율', value: '--', desc: '초기 노출 범위' },
  { label: '신뢰 점수', value: '--', desc: '약관/청구/브랜드 반응' },
  { label: '상담 요청', value: '--', desc: '설계사/앱 전환' },
  { label: '가입 의향', value: '--', desc: '가격 저항 반영' },
  { label: '부정 이슈', value: '--', desc: '개인정보/특약 논쟁' },
  { label: '메시지 수정', value: '--', desc: 'FAQ/카드뉴스 필요도' }
]

const interventionSlots = [
  { time: 'D+0', name: '런칭 메시지', target: '공식/디지털' },
  { time: 'D+3', name: 'FAQ 공개', target: '커뮤니티' },
  { time: 'D+7', name: '비교표 배포', target: '설계사/GA' },
  { time: 'D+14', name: '청구 UX 사례', target: '미디어/인플루언서' }
]

const messageAxes = [
  { label: '핵심 보장', value: '암/뇌혈관/심장질환 등 주요 리스크 중심' },
  { label: '가격 저항', value: '생활비 부담과 보장 체감의 균형' },
  { label: '신뢰 장치', value: '약관 요약, 면책/감액, 청구 절차 투명화' },
  { label: '데이터 우려', value: '건강관리 연동과 개인정보 처리 조건' }
]

// Watch stage to update phase
watch(currentStage, (newStage) => {
  if (newStage === 'Agent 페르소나 생성' || newStage === 'generating_profiles') {
    phase.value = 1
  } else if (newStage === '시뮬레이션 설정 생성' || newStage === 'generating_config') {
    phase.value = 2
    // 설정 생성 단계에 진입, 설정 폴링 시작
    if (!configTimer) {
      addLog('양 플랫폼 시뮬레이션 설정 생성을 시작합니다...')
      startConfigPolling()
    }
  } else if (newStage === '시뮬레이션 스크립트 준비' || newStage === 'copying_scripts') {
    phase.value = 2 // 여전히 설정 단계에 속함
  }
})

// 설정에서 자동 생성된 라운드 수 계산(하드코딩된 기본값 미사용)
const autoGeneratedRounds = computed(() => {
  if (!simulationConfig.value?.time_config) {
    return null // 설정이 생성되지 않았을 때 null 반환
  }
  const totalHours = simulationConfig.value.time_config.total_simulation_hours
  const minutesPerRound = simulationConfig.value.time_config.minutes_per_round
  if (!totalHours || !minutesPerRound) {
    return null // 설정 데이터가 불완전할 때 null 반환
  }
  const calculatedRounds = Math.floor((totalHours * 60) / minutesPerRound)
  // 최대 라운드 수가 40(권장값)보다 작지 않도록 하여 슬라이더 범위 이상을 방지
  return Math.max(calculatedRounds, 40)
})

const agentSegmentCount = computed(() => {
  return simulationConfig.value?.agent_configs?.length || profiles.value.length || 0
})

const productDisplayName = computed(() => {
  const source = props.projectData?.simulation_requirement || simulationConfig.value?.simulation_requirement || ''
  const quoted = source.match(/['"‘“]([^'"’”]+)['"’”]/)
  if (quoted?.[1]) return quoted[1]
  return '삼성생명 보험 신상품'
})

const preflightSummary = computed(() => {
  const source = props.projectData?.simulation_requirement || simulationConfig.value?.simulation_requirement || ''
  if (!source) return '가상 세계와 Agent 구성이 생성되었습니다. 판매 채널, Funnel, KPI 기준선을 실행 전에 확인합니다.'
  return source.length > 150 ? `${source.slice(0, 150)}...` : source
})

// Polling timer
let pollTimer = null
let profilesTimer = null
let configTimer = null

// Computed
const displayProfiles = computed(() => {
  if (showProfilesDetail.value) {
    return profiles.value
  }
  return profiles.value.slice(0, 6)
})

// agent_id로 해당 username 가져오기
const getAgentUsername = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    const profile = profiles.value[agentId]
    return profile?.username || `agent_${agentId}`
  }
  return `agent_${agentId}`
}

// 모든 페르소나의 연관 토픽 총합 계산
const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0)
  }, 0)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// 시작 시뮬레이션 버튼 클릭 처리
const handleStartSimulation = () => {
  // 부모 컴포넌트로 전달할 파라미터 구성
  const params = {}
  
  if (useCustomRounds.value) {
    // 사용자 정의 라운드 수, max_rounds 파라미터 전달
    params.maxRounds = customMaxRounds.value
    addLog(`시뮬레이션 시작, 사용자 정의 라운드 수: ${customMaxRounds.value} 라운드`)
  } else {
    // 사용자가 자동 생성 라운드 수를 유지 선택, max_rounds 파라미터를 전달하지 않음
    addLog(`시뮬레이션 시작, 자동 설정 라운드 수 사용: ${autoGeneratedRounds.value} 라운드`)
  }
  
  emit('next-step', params)
}

const truncateBio = (bio) => {
  if (bio.length > 80) {
    return bio.substring(0, 80) + '...'
  }
  return bio
}

const selectProfile = (profile) => {
  selectedProfile.value = profile
}

// 자동으로 시뮬레이션 준비 시작
const startPrepareSimulation = async () => {
  if (!props.simulationId) {
    addLog('오류: simulationId가 없습니다')
    emit('update-status', 'error')
    return
  }
  
  // 1단계 완료 표시, 2단계 시작
  phase.value = 1
  addLog(`시뮬레이션 인스턴스가 생성됨: ${props.simulationId}`)
  addLog('시뮬레이션 환경을 준비 중...')
  emit('update-status', 'processing')
  
  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5
    })
    
    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog('완료된 준비 작업이 이미 있는 것을 감지하여, 바로 사용합니다')
        await loadPreparedData()
        return
      }
      
      taskId.value = res.data.task_id
      addLog(`준비 작업이 시작됨`)
      addLog(`  └─ Task ID: ${res.data.task_id}`)
      
      // prepare 인터페이스 반환값에서 예상 Agent 총수를 즉시 설정
      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count
        addLog(`Zep 그래프에서 ${res.data.expected_entities_count}개의 엔티티를 읽어왔습니다`)
        if (res.data.entity_types && res.data.entity_types.length > 0) {
          addLog(`  └─ 엔티티 유형: ${res.data.entity_types.join(', ')}`)
        }
      }
      
      addLog('준비 진행 상황 폴링을 시작합니다...')
      // 진행 상황 폴링 시작
      startPolling()
      // Profiles 실시간 가져오기 시작
      startProfilesPolling()
    } else {
      addLog(`준비 실패: ${res.error || '알 수 없는 오류'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    addLog(`준비 중 예외 발생: ${err.message}`)
    emit('update-status', 'error')
  }
}

const startPolling = () => {
  pollTimer = setInterval(pollPrepareStatus, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const startProfilesPolling = () => {
  profilesTimer = setInterval(fetchProfilesRealtime, 3000)
}

const stopProfilesPolling = () => {
  if (profilesTimer) {
    clearInterval(profilesTimer)
    profilesTimer = null
  }
}

const pollPrepareStatus = async () => {
  if (!taskId.value && !props.simulationId) return
  
  try {
    const res = await getPrepareStatus({
      task_id: taskId.value,
      simulation_id: props.simulationId
    })
    
    if (res.success && res.data) {
      const data = res.data
      
      // 진행률 업데이트
      prepareProgress.value = data.progress || 0
      progressMessage.value = data.message || ''
      
      // 단계 정보를 파싱하고 상세 로그 출력
      if (data.progress_detail) {
        currentStage.value = data.progress_detail.current_stage_name || ''
        
        // 상세 진행 로그 출력(중복 방지)
        const detail = data.progress_detail
        const logKey = `${detail.current_stage}-${detail.current_item}-${detail.total_items}`
        if (logKey !== lastLoggedMessage && detail.item_description) {
          lastLoggedMessage = logKey
          const stageInfo = `[${detail.stage_index}/${detail.total_stages}]`
          if (detail.total_items > 0) {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.current_item}/${detail.total_items} - ${detail.item_description}`)
          } else {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.item_description}`)
          }
        }
      } else if (data.message) {
        // 메시지에서 단계 추출
        const match = data.message.match(/\[(\d+)\/(\d+)\]\s*([^:]+)/)
        if (match) {
          currentStage.value = match[3].trim()
        }
        // 메시지 로그 출력(중복 방지)
        if (data.message !== lastLoggedMessage) {
          lastLoggedMessage = data.message
          addLog(data.message)
        }
      }
      
      // 완료 여부 확인
      if (data.status === 'completed' || data.status === 'ready' || data.already_prepared) {
        addLog('✓ 준비 작업이 완료되었습니다')
        stopPolling()
        stopProfilesPolling()
        await loadPreparedData()
      } else if (data.status === 'failed') {
        addLog(`✗ 준비 실패: ${data.error || '알 수 없는 오류'}`)
        stopPolling()
        stopProfilesPolling()
      }
    }
  } catch (err) {
    console.warn('상태 폴링 실패:', err)
  }
}

const fetchProfilesRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    
    if (res.success && res.data) {
      const prevCount = profiles.value.length
      profiles.value = res.data.profiles || []
      // API가 유효한 값을 반환했을 때만 업데이트하여, 기존의 유효한 값을 덮어쓰지 않음
      if (res.data.total_expected) {
        expectedTotal.value = res.data.total_expected
      }
      
      // 엔티티 타입 추출
      const types = new Set()
      profiles.value.forEach(p => {
        if (p.entity_type) types.add(p.entity_type)
      })
      entityTypes.value = Array.from(types)
      
      // Profile 생성 진행 로그 출력(수량이 변할 때만)
      const currentCount = profiles.value.length
      if (currentCount > 0 && currentCount !== lastLoggedProfileCount) {
        lastLoggedProfileCount = currentCount
        const total = expectedTotal.value || '?'
        const latestProfile = profiles.value[currentCount - 1]
        const profileName = latestProfile?.name || latestProfile?.username || `Agent_${currentCount}`
        if (currentCount === 1) {
          addLog(`Agent 페르소나 생성을 시작합니다...`)
        }
        addLog(`→ Agent 페르소나 ${currentCount}/${total}: ${profileName} (${latestProfile?.profession || '알 수 없는 직업'})`)
        
        // 모두 생성 완료된 경우
        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(`✓ 총 ${currentCount}개의 Agent 페르소나 생성이 완료되었습니다`)
        }
      }
    }
  } catch (err) {
    console.warn('Profiles 가져오기 실패:', err)
  }
}

// 설정 폴링
const startConfigPolling = () => {
  configTimer = setInterval(fetchConfigRealtime, 2000)
}

const stopConfigPolling = () => {
  if (configTimer) {
    clearInterval(configTimer)
    configTimer = null
  }
}

const fetchConfigRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      // 설정 생성 단계 로그 출력(중복 방지)
      if (data.generation_stage && data.generation_stage !== lastLoggedConfigStage) {
        lastLoggedConfigStage = data.generation_stage
        if (data.generation_stage === 'generating_profiles') {
          addLog('Agent 페르소나 설정을 생성하는 중...')
        } else if (data.generation_stage === 'generating_config') {
          addLog('LLM을 호출하여 시뮬레이션 설정 파라미터를 생성하는 중...')
        }
      }
      
      // 설정이 생성된 경우
      if (data.config_generated && data.config) {
        simulationConfig.value = data.config
        addLog('✓ 시뮬레이션 설정 생성 완료')
        
        // 상세 설정 요약 표시
        if (data.summary) {
          addLog(`  ├─ Agent 수: ${data.summary.total_agents}개`)
          addLog(`  ├─ 시뮬레이션 시간: ${data.summary.simulation_hours}시간`)
          addLog(`  ├─ 초기 게시물: ${data.summary.initial_posts_count}개`)
          addLog(`  ├─ 핫 토픽: ${data.summary.hot_topics_count}개`)
          addLog(`  └─ 플랫폼 설정: Twitter ${data.summary.has_twitter_config ? '✓' : '✗'}, Reddit ${data.summary.has_reddit_config ? '✓' : '✗'}`)
        }
        
        // 시간 설정 상세 표시
        if (data.config.time_config) {
          const tc = data.config.time_config
          addLog(`시간 설정: 라운드당 ${tc.minutes_per_round}분, 총 ${Math.floor((tc.total_simulation_hours * 60) / tc.minutes_per_round)}라운드`)
        }
        
        // 이벤트 설정 표시
        if (data.config.event_config?.narrative_direction) {
          const narrative = data.config.event_config.narrative_direction
          addLog(`내러티브 방향: ${narrative.length > 50 ? narrative.substring(0, 50) + '...' : narrative}`)
        }
        
        stopConfigPolling()
        phase.value = 4
        addLog('✓ 환경 구축이 완료되어 시뮬레이션을 시작할 수 있습니다')
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('Config 가져오기 실패:', err)
  }
}

const loadPreparedData = async () => {
  phase.value = 2
  addLog('기존 설정 데이터를 로드하는 중...')

  // 마지막으로 Profiles를 한 번 가져오기
  await fetchProfilesRealtime()
  addLog(`총 ${profiles.value.length}개의 Agent 페르소나를 로드했습니다`)

  // 설정 가져오기(실시간 인터페이스 사용)
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      if (res.data.config_generated && res.data.config) {
        simulationConfig.value = res.data.config
        addLog('✓ 시뮬레이션 설정 로드 성공')
        
        // 상세 설정 요약 표시
        if (res.data.summary) {
          addLog(`  ├─ Agent 수: ${res.data.summary.total_agents}개`)
          addLog(`  ├─ 시뮬레이션 시간: ${res.data.summary.simulation_hours}시간`)
          addLog(`  └─ 초기 게시물: ${res.data.summary.initial_posts_count}개`)
        }
        
        addLog('✓ 환경 구축이 완료되어 시뮬레이션을 시작할 수 있습니다')
        phase.value = 4
        emit('update-status', 'completed')
      } else {
        // 설정이 아직 생성되지 않았으므로 폴링 시작
        addLog('설정을 생성 중입니다. 폴링을 시작하여 대기합니다...')
        startConfigPolling()
      }
    }
  } catch (err) {
    addLog(`설정 로드 실패: ${err.message}`)
    emit('update-status', 'error')
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

onMounted(() => {
  // 자동으로 준비 프로세스 시작
  if (props.simulationId) {
    addLog('Step2 환경 구축 초기화')
    startPrepareSimulation()
  }
})

onUnmounted(() => {
  stopPolling()
  stopProfilesPolling()
  stopConfigPolling()
})
</script>

<style scoped>
.env-setup-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Step Card */
.step-card {
  background: #FFF;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border: 1px solid #EAEAEA;
  transition: all 0.3s ease;
  position: relative;
}

.step-card.active {
  border-color: #FF5722;
  box-shadow: 0 4px 12px rgba(255, 87, 34, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #E0E0E0;
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: #000;
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.badge {
  font-size: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.success { background: #E8F5E9; color: #2E7D32; }
.badge.processing { background: #FF5722; color: #FFF; }
.badge.pending { background: #F5F5F5; color: #999; }
.badge.accent { background: #E3F2FD; color: #1565C0; }

.card-content {
  /* No extra padding - uses step-card's padding */
}

.api-note {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #999;
  margin-bottom: 8px;
}

.description {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Action Section */
.action-section {
  margin-top: 16px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #000;
  color: #FFF;
}

.action-btn.primary:hover:not(:disabled) {
  opacity: 0.8;
}

.action-btn.secondary {
  background: #F5F5F5;
  color: #333;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #E5E5E5;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-group {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-group.dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.action-group.dual .action-btn {
  width: 100%;
}

/* Info Card */
.info-card {
  background: #F5F5F5;
  border-radius: 6px;
  padding: 16px;
  margin-top: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #E0E0E0;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 12px;
  color: #666;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
}

.info-value.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  background: #F9F9F9;
  padding: 16px;
  border-radius: 6px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #000;
  font-family: 'JetBrains Mono', monospace;
}

.stat-label {
  font-size: 9px;
  color: #999;
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

/* Profiles Preview */
.profiles-preview {
  margin-top: 20px;
  border-top: 1px solid #E5E5E5;
  padding-top: 16px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.profiles-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.profiles-list::-webkit-scrollbar {
  width: 4px;
}

.profiles-list::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.profiles-list::-webkit-scrollbar-thumb:hover {
  background: #CCC;
}

.profile-card {
  background: #FAFAFA;
  border: 1px solid #E5E5E5;
  border-radius: 6px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.profile-card:hover {
  border-color: #999;
  background: #FFF;
}

.profile-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.profile-realname {
  font-size: 14px;
  font-weight: 700;
  color: #000;
}

.profile-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #999;
}

.profile-meta {
  margin-bottom: 8px;
}

.profile-profession {
  font-size: 11px;
  color: #666;
  background: #F0F0F0;
  padding: 2px 8px;
  border-radius: 3px;
}

.profile-bio {
  font-size: 12px;
  color: #444;
  line-height: 1.6;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic-tag {
  font-size: 10px;
  color: #1565C0;
  background: #E3F2FD;
  padding: 2px 8px;
  border-radius: 10px;
}

.topic-more {
  font-size: 10px;
  color: #999;
  padding: 2px 6px;
}

/* Config Preview */
/* Config Detail Panel */
.config-detail-panel {
  margin-top: 16px;
}

.config-block {
  margin-top: 16px;
  border-top: 1px solid #E5E5E5;
  padding-top: 12px;
}

.config-block:first-child {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.config-block-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-block-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: #F1F5F9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 10px;
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.config-item {
  background: #F9F9F9;
  padding: 12px 14px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item-label {
  font-size: 11px;
  color: #94A3B8;
}

.config-item-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

/* Time Periods */
.time-periods {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.period-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #F9F9F9;
  border-radius: 6px;
}

.period-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
  min-width: 70px;
}

.period-hours {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #475569;
  flex: 1;
}

.period-multiplier {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: #6366F1;
  background: #EEF2FF;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Agents Cards */
.agents-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.agents-cards::-webkit-scrollbar {
  width: 4px;
}

.agents-cards::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.agents-cards::-webkit-scrollbar-thumb:hover {
  background: #CCC;
}

.agent-card {
  background: #F9F9F9;
  border: 1px solid #E5E5E5;
  border-radius: 6px;
  padding: 14px;
  transition: all 0.2s ease;
}

.agent-card:hover {
  border-color: #999;
  background: #FFF;
}

/* Agent Card Header */
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F1F5F9;
}

.agent-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.agent-tags {
  display: flex;
  gap: 6px;
}

.agent-type {
  font-size: 10px;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.agent-stance {
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
}

.stance-neutral {
  background: #F1F5F9;
  color: #64748B;
}

.stance-supportive {
  background: #DCFCE7;
  color: #16A34A;
}

.stance-opposing {
  background: #FEE2E2;
  color: #DC2626;
}

.stance-observer {
  background: #FEF3C7;
  color: #D97706;
}

/* Agent Timeline */
.agent-timeline {
  margin-bottom: 14px;
}

.timeline-label {
  display: block;
  font-size: 10px;
  color: #94A3B8;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mini-timeline {
  display: flex;
  gap: 2px;
  height: 16px;
  background: #F8FAFC;
  border-radius: 4px;
  padding: 3px;
}

.timeline-hour {
  flex: 1;
  background: #E2E8F0;
  border-radius: 2px;
  transition: all 0.2s;
}

.timeline-hour.active {
  background: linear-gradient(180deg, #6366F1, #818CF8);
}

.timeline-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: #94A3B8;
}

/* Agent Params */
.agent-params {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.param-item .param-label {
  font-size: 10px;
  color: #94A3B8;
}

.param-item .param-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.param-value.with-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-bar {
  height: 4px;
  background: linear-gradient(90deg, #6366F1, #A855F7);
  border-radius: 2px;
  min-width: 4px;
  max-width: 40px;
}

.param-value.positive {
  color: #16A34A;
}

.param-value.negative {
  color: #DC2626;
}

.param-value.neutral {
  color: #64748B;
}

.param-value.highlight {
  color: #6366F1;
}

/* Platforms Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.platform-card {
  background: #F9F9F9;
  padding: 14px;
  border-radius: 6px;
}

.platform-card-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #E5E5E5;
}

.platform-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.platform-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: 12px;
  color: #64748B;
}

.param-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #1E293B;
}

/* Reasoning Content */
.reasoning-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reasoning-item {
  padding: 12px 14px;
  background: #F9F9F9;
  border-radius: 6px;
}

.reasoning-text {
  font-size: 13px;
  color: #555;
  line-height: 1.7;
  margin: 0;
}

/* Profile Modal */
.profile-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.profile-modal {
  background: #FFF;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background: #FFF;
  border-bottom: 1px solid #F0F0F0;
}

.modal-header-info {
  flex: 1;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.modal-realname {
  font-size: 20px;
  font-weight: 700;
  color: #000;
}

.modal-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #999;
}

.modal-profession {
  font-size: 12px;
  color: #666;
  background: #F5F5F5;
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-block;
  font-weight: 500;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: #999;
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.2s;
  padding: 0;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 기본 정보 그리드 */
.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px 16px;
  margin-bottom: 32px;
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.info-value {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.info-value.mbti {
  font-family: 'JetBrains Mono', monospace;
  color: #FF5722;
}

/* 모듈 영역 */
.modal-section {
  margin-bottom: 28px;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-bio {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  margin: 0;
  padding: 16px;
  background: #F9F9F9;
  border-radius: 6px;
  border-left: 3px solid #E0E0E0;
}

/* 토픽 태그 */
.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-item {
  font-size: 11px;
  color: #1565C0;
  background: #E3F2FD;
  padding: 4px 10px;
  border-radius: 12px;
  transition: all 0.2s;
  border: none;
}

.topic-item:hover {
  background: #BBDEFB;
  color: #0D47A1;
}

/* 상세한 페르소나 */
.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.dimension-card {
  background: #F8F9FA;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #DDD;
  transition: all 0.2s;
}

.dimension-card:hover {
  background: #F0F0F0;
  border-left-color: #999;
}

.dim-title {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #333;
  margin-bottom: 4px;
}

.dim-desc {
  display: block;
  font-size: 10px;
  color: #888;
  line-height: 1.4;
}

.persona-content {
  max-height: none;
  overflow: visible;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.persona-content::-webkit-scrollbar {
  width: 4px;
}

.persona-content::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.section-persona {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
  margin: 0;
  text-align: justify;
}

/* System Logs */
.system-logs {
  background: #000;
  color: #DDD;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid #222;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #888;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px; /* Approx 4 lines visible */
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 2px;
}

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time {
  color: #666;
  min-width: 75px;
}

.log-msg {
  color: #CCC;
  word-break: break-all;
}

/* Spinner */
.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #E5E5E5;
  border-top-color: #FF5722;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
/* Orchestration Content */
.orchestration-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 16px;
}

.box-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.narrative-box {
  background: #FFFFFF;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid #EEF2F6;
  box-shadow: 0 4px 24px rgba(0,0,0,0.03);
  transition: all 0.3s ease;
}

.narrative-box .box-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  font-size: 13px;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  font-weight: 600;
}

.special-icon {
  filter: drop-shadow(0 2px 4px rgba(255, 87, 34, 0.2));
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.narrative-box:hover .special-icon {
  transform: rotate(180deg);
}

.narrative-text {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 14px;
  color: #334155;
  line-height: 1.8;
  margin: 0;
  text-align: justify;
  letter-spacing: 0.01em;
}

.topics-section {
  background: #FFF;
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-topic-tag {
  font-size: 12px;
  color:rgba(255, 86, 34, 0.88);
  background: #FFF3E0;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.hot-topic-more {
  font-size: 11px;
  color: #999;
  padding: 4px 6px;
}

.initial-posts-section {
  border-top: 1px solid #EAEAEA;
  padding-top: 16px;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-left: 8px;
  border-left: 2px solid #F0F0F0;
  margin-top: 12px;
}

.timeline-item {
  position: relative;
  padding-left: 20px;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 14px;
  width: 12px;
  height: 2px;
  background: #DDD;
}

.timeline-content {
  background: #F9F9F9;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #EEE;
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.post-role {
  font-size: 11px;
  font-weight: 700;
  color: #333;
  text-transform: uppercase;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-id,
.post-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #666;
  line-height: 1;
  vertical-align: baseline;
}

.post-username {
  margin-right: 6px;
}

.post-text {
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  margin: 0;
}

/* 보험 판매 시뮬레이션 Preflight */
.insurance-preflight {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #EAEAEA;
}

.preflight-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.preflight-title-group {
  min-width: 0;
  flex: 1;
}

.preflight-eyebrow {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #0F766E;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.preflight-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  line-height: 1.35;
  color: #111827;
}

.preflight-summary {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #64748B;
  word-break: keep-all;
}

.preflight-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #166534;
  background: #ECFDF5;
  border: 1px solid #BBF7D0;
  border-radius: 999px;
  padding: 5px 9px;
}

.status-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22C55E;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.14);
}

.preflight-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
  margin-bottom: 18px;
}

.metric-strip-item {
  min-width: 0;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  padding: 10px 12px;
}

.metric-strip-label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  color: #94A3B8;
  margin-bottom: 4px;
}

.metric-strip-value {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
  overflow-wrap: anywhere;
}

.metric-strip-value.mono {
  font-family: 'JetBrains Mono', monospace;
}

.preflight-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.preflight-section {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #EAEAEA;
}

.preflight-layout .preflight-section {
  margin-top: 0;
}

.section-heading-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.preflight-section-title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.02em;
}

.section-chip {
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-weight: 700;
  color: #475569;
  background: #F1F5F9;
  border-radius: 999px;
  padding: 3px 7px;
}

.message-axis-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-axis {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 9px 0;
  border-bottom: 1px dashed #E2E8F0;
}

.message-axis:last-child {
  border-bottom: none;
}

.axis-label {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
}

.axis-value {
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
  overflow-wrap: anywhere;
}

.funnel-track {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
  gap: 8px;
}

.funnel-stage {
  min-width: 0;
  background: #FAFAFA;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px;
}

.stage-index {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #0F766E;
  margin-bottom: 6px;
}

.stage-name {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 4px;
}

.stage-signal {
  display: block;
  font-size: 10px;
  line-height: 1.4;
  color: #64748B;
}

.channel-lanes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.channel-lane {
  min-width: 0;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
}

.channel-lane-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.channel-name {
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
}

.channel-type {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-weight: 700;
  color: #1D4ED8;
  background: #EFF6FF;
  border-radius: 4px;
  padding: 2px 6px;
}

.channel-role {
  min-height: 38px;
  margin: 0 0 8px 0;
  font-size: 11px;
  line-height: 1.5;
  color: #475569;
}

.channel-signal {
  display: block;
  font-size: 10px;
  color: #7C2D12;
  background: #FFF7ED;
  border-radius: 4px;
  padding: 5px 7px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}

.kpi-item {
  min-width: 0;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px;
  background: #F8FAFC;
}

.kpi-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 6px;
}

.kpi-value {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 4px;
}

.kpi-desc {
  display: block;
  font-size: 10px;
  line-height: 1.4;
  color: #64748B;
}

.intervention-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: 8px;
}

.intervention-item {
  min-width: 0;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px;
  background: #FFFFFF;
}

.intervention-time {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 800;
  color: #BE123C;
  margin-bottom: 5px;
}

.intervention-name {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #1E293B;
  margin-bottom: 5px;
}

.intervention-target {
  display: block;
  font-size: 10px;
  line-height: 1.4;
  color: #64748B;
}

/* 시뮬레이션 라운드 수 설정 스타일 */
.rounds-config-section {
  margin: 24px 0;
  padding-top: 24px;
  border-top: 1px solid #EAEAEA;
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.section-desc {
  font-size: 12px;
  color: #94A3B8;
}

.desc-highlight {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #1E293B;
  background: #F1F5F9;
  padding: 1px 6px;
  border-radius: 4px;
  margin: 0 2px;
}

/* Switch Control */
.switch-control {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: 20px;
  transition: background 0.2s;
}

.switch-control:hover {
  background: #F8FAFC;
}

.switch-control input {
  display: none;
}

.switch-track {
  width: 36px;
  height: 20px;
  background: #E2E8F0;
  border-radius: 10px;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-track::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: #FFF;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  transition: transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-control input:checked + .switch-track {
  background: #000;
}

.switch-control input:checked + .switch-track::after {
  transform: translateX(16px);
}

.switch-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
}

.switch-control input:checked ~ .switch-label {
  color: #1E293B;
}

/* Slider Content */
.rounds-content {
  animation: fadeIn 0.3s ease;
}

.slider-display {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.slider-main-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.val-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: #000;
}

.val-unit {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.slider-meta-info {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #64748B;
  background: #F1F5F9;
  padding: 4px 8px;
  border-radius: 4px;
  margin: 0 2px;
}

.range-wrapper {
  position: relative;
  padding: 0 2px;
}
.minimal-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  background: #E2E8F0;
  border-radius: 2px;
  outline: none;
  background-image: linear-gradient(#000, #000);
  background-size: var(--percent, 0%) 100%;
  background-repeat: no-repeat;
  cursor: pointer;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #FFF;
  border: 2px solid #000;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  transition: transform 0.1s;
  margin-top: -6px; /* Center thumb */
}

.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.minimal-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 2px;
}

.range-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
  position: relative;
}

.mark-recommend {
  cursor: pointer;
  transition: color 0.2s;
  position: relative;
}

.mark-recommend:hover {
  color: #000;
}

.mark-recommend.active {
  color: #000;
  font-weight: 600;
}

.mark-recommend::after {
  content: '';
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 1px;
  height: 4px;
  background: #CBD5E1;
}

/* Auto Info */
.auto-info-card {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #F8FAFC;
  padding: 16px 20px;
  border-radius: 8px;
}

.auto-value {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4px;
  padding-right: 24px;
  border-right: 1px solid #E2E8F0;
}

.auto-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.auto-meta-row {
  display: flex;
  align-items: center;
}

.duration-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #64748B;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 3px 8px;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.auto-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.auto-desc p {
  margin: 0;
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
}

.highlight-tip {
  margin-top: 4px !important;
  font-size: 12px !important;
  color: #000 !important;
  font-weight: 500;
  cursor: pointer;
}

.highlight-tip:hover {
  text-decoration: underline;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .profile-modal {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-leave-active .profile-modal {
  transition: all 0.3s ease-in;
}

.modal-enter-from .profile-modal,
.modal-leave-to .profile-modal {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
