"""
OASIS Agent Profile 생성기
Zep 그래프의 엔티티를 OASIS 시뮬레이션 플랫폼에 필요한 Agent Profile 형식으로 변환

최적화 개선:
1. Zep 검색 기능을 호출해 노드 정보를 2차로 풍부화
2. 프롬프트 생성을 최적화해 매우 상세한 페르소나를 생성
3. 개인 엔티티와 추상적 집단 엔티티를 구분
"""

import json
import random
import re
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.oasis_profile')
CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff]')
KOREAN_LAST_NAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍",
]
KOREAN_GIVEN_NAMES = [
    "민영", "민호", "서연", "현우", "지은", "도윤", "수진", "민재",
    "하늘", "유진", "태준", "가은", "지훈", "소라", "준호", "나윤",
    "은비", "성민", "지아", "기훈", "다은", "재원", "세희", "우진",
    "예린", "민규", "지호", "윤서", "준영", "혜린",
]


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile 데이터 구조"""
    # 공통 필드
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    
    # 선택 필드 - Reddit 스타일
    karma: int = 1000
    
    # 선택 필드 - Twitter 스타일
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    
    # 추가 페르소나 정보
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    
    # 출처 엔티티 정보
    source_entity_name: Optional[str] = None
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """Reddit 플랫폼 형식으로 변환"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS 라이브러리는 필드명이 username(언더스코어 없음)이어야 함
            "realname": self.name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }
        
        # 추가 페르소나 정보 추가(있는 경우)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        if self.source_entity_name:
            profile["source_entity_name"] = self.source_entity_name
        
        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """Twitter 플랫폼 형식으로 변환"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS 라이브러리는 필드명이 username(언더스코어 없음)이어야 함
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }
        
        # 추가 페르소나 정보
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        if self.source_entity_name:
            profile["source_entity_name"] = self.source_entity_name
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """완전한 딕셔너리 형식으로 변환"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_name": self.source_entity_name,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile 생성기
    
    Zep 그래프의 엔티티를 OASIS 시뮬레이션에 필요한 Agent Profile로 변환
    
    최적화 특성:
    1. Zep 그래프 검색 기능을 호출해 더 풍부한 컨텍스트를 획득
    2. 매우 상세한 페르소나 생성(기본 정보, 직업 경력, 성격 특성, 소셜 미디어 행동 등 포함)
    3. 개인 엔티티와 추상적 집단 엔티티를 구분
    """
    
    # MBTI 타입 리스트
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]
    
    # 흔한 국가 리스트
    COUNTRIES = [
        "한국", "미국", "영국", "일본", "독일", "프랑스",
        "캐나다", "호주", "브라질", "인도"
    ]
    
    # 개인 유형 엔티티(구체적 페르소나를 생성해야 함)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure", 
        "expert", "faculty", "official", "journalist", "activist"
    ]
    
    # 집단/기관 유형 엔티티(집단 대표 페르소나를 생성해야 함)
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo", 
        "mediaoutlet", "company", "institution", "group", "community"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 미설정")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Zep 클라이언트는 풍부한 컨텍스트 검색에 사용
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id
        
        if self.zep_api_key:
            try:
                self.zep_client = Zep(api_key=self.zep_api_key)
            except Exception as e:
                logger.warning(f"Zep 클라이언트 초기화 실패: {e}")
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        Zep 엔티티로부터 OASIS Agent Profile 생성
        
        Args:
            entity: Zep 엔티티 노드
            user_id: 사용자 ID(OASIS 용)
            use_llm: LLM을 사용해 상세 페르소나를 생성할지 여부
            
        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"
        
        # 기본 정보: 그래프 엔티티는 출처로 보존하고, 시뮬레이션 참여자는 한국식 실명으로 생성합니다.
        source_entity_name = entity.name
        name = self._generate_korean_person_name(user_id)
        user_name = self._generate_username(name)
        
        # 컨텍스트 정보 구성
        context = self._build_entity_context(entity)
        
        if use_llm:
            # LLM을 사용해 상세 페르소나 생성
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context,
                source_entity_name=source_entity_name,
            )
        else:
            # 규칙 기반으로 기본 페르소나 생성
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                source_entity_name=source_entity_name,
            )
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=self._normalize_country(profile_data.get("country")),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_name=source_entity_name,
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """사용자명 생성"""
        # 특수문자 제거, 소문자로 변환
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        # 랜덤 접미사를 추가해 중복 방지
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"

    def _generate_korean_person_name(self, user_id: int) -> str:
        """보험 시뮬레이션 Agent에 사용할 한국식 실명 생성"""
        last = KOREAN_LAST_NAMES[user_id % len(KOREAN_LAST_NAMES)]
        given = KOREAN_GIVEN_NAMES[(user_id * 7 + 3) % len(KOREAN_GIVEN_NAMES)]
        return f"{last}{given}"
    
    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Zep 그래프 혼합 검색 기능을 사용해 엔티티 관련 풍부한 정보를 가져옵니다.
        
        Zep에는 내장 혼합 검색 인터페이스가 없으므로 edges와 nodes를 각각 검색한 뒤 결과를 병합해야 합니다.
        병렬 요청을 사용해 동시에 검색하여 효율을 높입니다.
        
        Args:
            entity: 엔티티 노드 객체
            
        Returns:
            facts, node_summaries, context를 포함하는 딕셔너리
        """
        import concurrent.futures
        
        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}
        
        entity_name = entity.name
        
        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }
        
        # 검색을 수행하려면 graph_id가 반드시 필요
        if not self.graph_id:
            logger.debug(f"Zep 검색 건너뜀: graph_id가 설정되지 않음")
            return results
        
        comprehensive_query = f"{entity_name}에 관한 모든 정보、활동、사건、관계 및 배경"
        
        def search_edges():
            """엣지(사실/관계) 검색 - 재시도 메커니즘 포함"""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep 엣지 검색 {attempt + 1}회 실패: {str(e)[:80]}, 재시도 중...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep 엣지 검색이 {max_retries}회 시도 후에도 실패: {e}")
            return None
        
        def search_nodes():
            """노드(엔티티 요약) 검색 - 재시도 메커니즘 포함"""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep 노드 검색 {attempt + 1}번째 실패: {str(e)[:80]}, 재시도 중...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep 노드 검색이 {max_retries}번 시도 후에도 실패: {e}")
            return None
        
        try:
            # edges와 nodes 검색을 병렬로 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)
                
                # 결과 가져오기
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)
            
            # 엣지 검색 결과 처리
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)
            
            # 노드 검색 결과 처리
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity_name:
                        all_summaries.add(f"관련 엔티티: {node.name}")
            results["node_summaries"] = list(all_summaries)
            
            # 종합 컨텍스트 구성
            context_parts = []
            if results["facts"]:
                context_parts.append("사실 정보:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("관련 엔티티:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)
            
            logger.info(f"Zep 혼합 검색 완료: {entity_name}, 사실 {len(results['facts'])}개, 관련 노드 {len(results['node_summaries'])}개 가져옴")
            
        except concurrent.futures.TimeoutError:
            logger.warning(f"Zep 검색 시간 초과 ({entity_name})")
        except Exception as e:
            logger.warning(f"Zep 검색 실패 ({entity_name}): {e}")
        
        return results
    
    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        엔티티의 전체 컨텍스트 정보 구성
        
        포함:
        1. 엔티티 자체의 엣지 정보(사실)
        2. 연관 노드의 상세 정보
        3. Zep 혼합 검색으로 가져온 풍부한 정보
        """
        context_parts = []
        
        # 1. 엔티티 속성 정보 추가
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### 엔티티 속성\n" + "\n".join(attrs))
        
        # 2. 관련 엣지 정보(사실/관계) 추가
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:  # 수량 제한 없음
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")
                
                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (관련 엔티티)")
                    else:
                        relationships.append(f"- (관련 엔티티) --[{edge_name}]--> {entity.name}")
            
            if relationships:
                context_parts.append("### 관련 사실 및 관계\n" + "\n".join(relationships))
        
        # 3. 연관 노드의 상세 정보 추가
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:  # 수량 제한 없음
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")
                
                # 기본 라벨 필터링
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""
                
                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")
            
            if related_info:
                context_parts.append("### 연관 엔티티 정보\n" + "\n".join(related_info))
        
        # 4. Zep 혼합 검색을 사용해 더 풍부한 정보 가져오기
        zep_results = self._search_zep_for_entity(entity)
        
        if zep_results.get("facts"):
            # 중복 제거: 이미 존재하는 사실 제외
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Zep에서 검색된 사실 정보\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        
        if zep_results.get("node_summaries"):
            context_parts.append("### Zep에서 검색된 관련 노드\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))
        
        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """개인 유형 엔티티인지 판단"""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES
    
    def _is_group_entity(self, entity_type: str) -> bool:
        """집단/기관 유형 엔티티인지 판단"""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        source_entity_name: str = ""
    ) -> Dict[str, Any]:
        """
        LLM을 사용해 매우 상세한 페르소나 생성
        
        엔티티 유형에 따라 구분:
        - 개인 엔티티: 구체적인 인물 설정 생성
        - 집단/기관 엔티티: 대표 계정 설정 생성
        """
        
        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context, source_entity_name
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context, source_entity_name
            )

        # 여러 번 생성 시도, 성공하거나 최대 재시도 횟수에 도달할 때까지
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # 재시도할 때마다 온도 낮춤
                    # max_tokens를 설정하지 않아 LLM이 자유롭게 생성하도록 함
                )
                
                content = response.choices[0].message.content
                
                # 잘렸는지 확인（finish_reason이 'stop'이 아님）
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM 출력이 잘림 (attempt {attempt+1}), 수정을 시도...")
                    content = self._fix_truncated_json(content)
                
                # JSON 파싱 시도
                try:
                    result = json.loads(content)
                    
                    # 필수 필드 검증
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name}는 {entity_type}입니다."

                    result = self._normalize_generated_profile(result)
                    result = self._ensure_insurance_specific_profile(result, entity_name, source_entity_name, entity_type)
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON 파싱 실패 (attempt {attempt+1}): {str(je)[:80]}")
                    
                    # JSON 수정 시도
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        result = self._normalize_generated_profile(result)
                        result = self._ensure_insurance_specific_profile(result, entity_name, source_entity_name, entity_type)
                        return result
                    
                    last_error = je
                    
            except Exception as e:
                logger.warning(f"LLM 호출 실패 (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # 지수 백오프
        
        logger.warning(f"LLM 페르소나 생성 실패（{max_attempts}회 시도）: {last_error}, 규칙 기반으로 생성")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes, source_entity_name
        )

    def _normalize_generated_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """생성된 프로필의 언어와 필드를 정규화"""
        normalized = dict(profile)
        if self._profile_contains_chinese(normalized):
            normalized = self._translate_profile_to_korean(normalized)

        normalized["country"] = self._normalize_country(normalized.get("country"))

        if self._profile_contains_chinese(normalized):
            raise ValueError("프로필에 중국어가 남아 있어 한국어 정규화에 실패했습니다")

        return normalized

    def _ensure_insurance_specific_profile(
        self,
        profile: Dict[str, Any],
        person_name: str,
        source_entity_name: str,
        entity_type: str,
    ) -> Dict[str, Any]:
        """LLM 결과가 추상적일 때 보험 가입 행동 명세를 보강"""
        enriched = dict(profile)
        bio = str(enriched.get("bio") or "").strip()
        if not bio.startswith(person_name):
            bio = f"{person_name}는 {source_entity_name or entity_type} 맥락에서 라이프핏 건강보험을 검토하는 참여자입니다. {bio}".strip()
        enriched["bio"] = bio[:260]

        persona = str(enriched.get("persona") or "").strip()
        required_terms = ["보험료", "보장", "약관", "개인정보", "해지", "전환"]
        if len(persona) < 500 or not all(term in persona for term in required_terms[:4]):
            persona = (
                f"{persona} {person_name}는 현재 보유 보험과 라이프핏 건강보험의 월 보험료, 보장범위, 면책/감액 조건, 약관복잡성, 개인정보 연동 범위를 비교해 가입 여부를 결정한다. "
                "가입 전에는 설계사 설명, 공식 FAQ, 커뮤니티 후기, 실제 청구 사례를 교차 검증한다. "
                "가입 후에는 청구 경험이 원활하고 보험료 인상 압박이 낮으면 유지하지만, 보장 실효성이 낮거나 개인정보 활용 조건이 불명확하거나 경쟁상품의 보장 대비 가격이 더 좋으면 특약 조정, 해지 상담, 다른 보험으로 전환하는 행동을 한다."
            ).strip()
        enriched["persona"] = re.sub(r"\s+", " ", persona)

        topics = enriched.get("interested_topics")
        if not isinstance(topics, list):
            topics = []
        for topic in ["건강보험", "보험료", "보장범위", "약관", "개인정보", "보험 해지/전환"]:
            if topic not in topics:
                topics.append(topic)
        enriched["interested_topics"] = topics[:10]

        if not enriched.get("country"):
            enriched["country"] = "한국"
        if not enriched.get("profession"):
            enriched["profession"] = entity_type
        return enriched

    def _profile_contains_chinese(self, value: Any) -> bool:
        """프로필에 중국어 한자가 남아 있는지 확인"""
        if isinstance(value, str):
            return bool(CHINESE_CHAR_PATTERN.search(value))
        if isinstance(value, list):
            return any(self._profile_contains_chinese(item) for item in value)
        if isinstance(value, dict):
            return any(self._profile_contains_chinese(item) for item in value.values())
        return False

    def _translate_profile_to_korean(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """프로필 JSON의 설명 필드를 한국어로 변환"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 JSON 구조를 보존하는 번역기입니다. "
                        "입력 JSON의 사람이 읽는 텍스트 값을 자연스러운 한국어로 번역하세요. "
                        "키 이름과 구조는 절대 바꾸지 마세요. "
                        "age는 정수로 유지하고, gender는 male/female/other 중 하나로 유지하며, "
                        "mbti는 그대로 두세요. 문자열 값에는 이스케이프되지 않은 줄바꿈을 넣지 마세요. "
                        "반드시 유효한 JSON만 반환하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(profile, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        translated = json.loads(response.choices[0].message.content)
        if not isinstance(translated, dict):
            raise ValueError("번역 결과가 JSON 객체가 아닙니다")
        return translated
    
    def _fix_truncated_json(self, content: str) -> str:
        """잘린 JSON 수정（출력이 max_tokens 제한으로 잘림）"""
        import re
        
        # JSON이 잘렸다면 닫히도록 시도
        content = content.strip()
        
        # 닫히지 않은 괄호 계산
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # 닫히지 않은 문자열이 있는지 확인
        # 간단한 검사：마지막 따옴표 뒤에 쉼표나 닫는 괄호가 없으면 문자열이 잘렸을 수 있음
        if content and content[-1] not in '",}]':
            # 문자열 닫기 시도
            content += '"'
        
        # 괄호 닫기
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """손상된 JSON 수정을 시도"""
        import re
        
        # 1. 먼저 잘린 경우를 수정 시도
        content = self._fix_truncated_json(content)
        
        # 2. JSON 부분 추출 시도
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 3. 문자열 내 줄바꿈 문제 처리
            # 모든 문자열 값을 찾아 그 안의 줄바꿈을 치환
            def fix_string_newlines(match):
                s = match.group(0)
                # 문자열 내부의 실제 줄바꿈을 공백으로 치환
                s = s.replace('\n', ' ').replace('\r', ' ')
                # 불필요한 공백 치환
                s = re.sub(r'\s+', ' ', s)
                return s
            
            # JSON 문자열 값 매칭
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)
            
            # 4. 파싱 시도
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. 여전히 실패하면 더 공격적으로 수정 시도
                try:
                    # 모든 제어 문자 제거
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # 연속된 모든 공백 치환
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass
        
        # 6. 내용에서 일부 정보 추출 시도
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)  # 잘렸을 수 있음
        
        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name}는 {entity_type}입니다.")
        
        # 의미 있는 내용을 추출했다면 수정됨으로 표시
        if bio_match or persona_match:
            logger.info(f"손상된 JSON에서 일부 정보를 추출함")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }
        
        # 7. 완전히 실패하면 기본 구조 반환
        logger.warning(f"JSON 수정 실패，기본 구조 반환")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name}는 {entity_type}입니다."
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """시스템 프롬프트 가져오기"""
        base_prompt = (
            "당신은 한국 보험상품 가입/유지 시뮬레이션용 사용자 프로필 생성 전문가입니다. "
            "여론과 보험 가입 행동 시뮬레이션에 사용할 상세하고 현실적인 페르소나를 생성하며, "
            "가능한 한 실제 맥락을 충실히 반영합니다. "
            "이름은 박민영, 이민호처럼 실제 한국 사람 이름 형태로 다루고, "
            "보험료 민감도, 보장범위 판단, 약관 이해도, 개인정보 우려, 가입 후 유지/해지/전환 조건을 반드시 구체화합니다. "
            "반드시 유효한 JSON 형식으로만 반환해야 하며, "
            "모든 문자열 값에는 이스케이프되지 않은 줄바꿈 문자가 포함되면 안 됩니다. "
            "모든 설명은 한국어로 작성하세요."
        )
        return base_prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        source_entity_name: str = ""
    ) -> str:
        """개인 엔터티의 상세 페르소나 프롬프트 구성"""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "없음"
        context_str = context[:3000] if context else "추가 컨텍스트 없음"
        
        return f"""엔터티에 대해 상세한 보험상품 가입 시뮬레이션용 사용자 페르소나를 생성하고, 가능한 한 실제 한국 보험소비자 맥락을 충실히 반영하세요.

시뮬레이션 참여자 이름: {entity_name}
출처 그래프 엔터티: {source_entity_name or entity_name}
엔터티 유형: {entity_type}
엔터티 요약: {entity_summary}
엔터티 속성: {attrs_str}

컨텍스트 정보:
{context_str}

JSON을 생성, 다음 필드를 포함:

1. bio: 소셜 미디어 소개, 200자. 반드시 "{entity_name}"이라는 실제 사람 이름으로 시작
2. persona: 상세 페르소나 설명(2000자의 순수 텍스트), 다음을 포함:
   - 기본 정보(나이, 직업, 학력, 거주지)
   - 보험 명세(현재 보유 보험, 월 보험료 부담 수준, 가족력/건강 리스크, 라이프핏 건강보험 가입/보류/거절 기준)
   - 의사결정 규칙(보험료, 보장범위, 약관복잡성, 개인정보 연동 중 무엇을 가장 민감하게 보는지)
   - 가입 후 행동 규칙(가입한 뒤 유지, 청구 문의, 특약 조정, 해지, 경쟁상품 전환 중 어떤 조건에서 움직이는지)
   - 인물 배경(중요 경험, 사건과의 연관, 사회적 관계)
   - 성격 특성(MBTI 유형, 핵심 성격, 감정 표현 방식)
   - 소셜 미디어 행동(게시 빈도, 콘텐츠 선호, 상호작용 스타일, 언어 특징)
   - 입장/관점(주제에 대한 태도, 분노/감동할 수 있는 내용)
   - 독특한 특징(말버릇, 특이한 경험, 개인 취미)
   - 개인 기억(페르소나의 중요한 부분, 이 개인과 사건의 연관, 사건에서 이미 한 행동과 반응 소개)
3. age: 나이 숫자(반드시 정수)
4. gender: 성별, 반드시 영어: "male" 또는 "female"
5. mbti: MBTI 유형(예: INTJ, ENFP 등)
6. country: 국가(한국어 사용, 예: "한국")
7. profession: 직업
8. interested_topics: 관심 있는 주제 배열

중요:
- 모든 필드 값은 문자열 또는 숫자여야 하며, 줄바꿈을 사용하지 마세요
- persona는 하나의 연속된 글 설명이어야 합니다
- 모든 설명은 한국어를 사용하세요(단 gender 필드는 반드시 영어 male/female)
- 내용은 엔티티 정보와 일치해야 함
- age는 유효한 정수여야 하며, gender는 "male" 또는 "female"이어야 함
- "어떤 이슈에 관심 있는 사용자" 같은 추상 표현으로 끝내지 말고, 보험 가입/유지/해지 행동을 결정할 수 있는 구체 명세를 작성하세요
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        source_entity_name: str = ""
    ) -> str:
        """집단/기관 엔티티의 상세 페르소나 프롬프트를 구성"""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "없음"
        context_str = context[:3000] if context else "추가 컨텍스트 없음"
        
        return f"""기관/집단 엔티티를 대표해서 말하는 한국인 운영자 페르소나를 생성하고, 가능한 한 실제 보험시장 맥락을 충실히 반영하세요.

시뮬레이션 참여자 이름: {entity_name}
대표/출처 그래프 엔터티: {source_entity_name or entity_name}
엔티티 유형: {entity_type}
엔티티 요약: {entity_summary}
엔티티 속성: {attrs_str}

컨텍스트 정보:
{context_str}

JSON을 생성하고, 다음 필드를 포함하세요:

1. bio: 대표 운영자 소개, 200자. 반드시 "{entity_name}"이라는 실제 사람 이름으로 시작하고, 어떤 기관/집단을 대표하는지 명시
2. persona: 상세 계정 설정 설명(2000자의 순수 텍스트), 반드시 포함:
   - 대표하는 기관/집단 기본 정보(정식 명칭, 기관 성격, 주요 기능)
   - 운영자 개인 배경(직무, 연차, 책임 범위, 의사결정 권한)
   - 보험 명세(라이프핏 건강보험을 어떤 기준으로 홍보/검증/비판하는지, 고객 가입·해지·전환을 어떻게 해석하는지)
   - 가입 후 행동 규칙(민원, 청구 문의, 해지 요청, 경쟁상품 전환 이슈가 발생할 때 어떤 메시지를 내는지)
   - 계정 포지셔닝(계정 유형, 목표 수용자, 핵심 기능)
   - 발언 스타일(언어 특징, 자주 쓰는 표현, 금기 주제)
   - 게시 콘텐츠 특징(콘텐츠 유형, 게시 빈도, 활동 시간대)
   - 입장과 태도(핵심 주제에 대한 공식 입장, 논란 대응 방식)
   - 특별 설명(대표하는 집단 이미지, 운영 습관)
   - 기관 기억(기관 페르소나의 중요한 부분으로, 이 기관과 사건의 연관성, 그리고 사건에서의 기존 행동과 반응을 소개)
3. age: 고정으로 30 입력(기관 계정의 가상 나이)
4. gender: 고정으로 "other" 입력(기관 계정은 other로 비개인을 표시)
5. mbti: 계정 스타일을 설명하는 MBTI 유형, 예: ISTJ는 엄격하고 보수적임을 의미
6. country: 국가(한국어 사용, 예: "한국")
7. profession: 기관 기능 설명
8. interested_topics: 관심 분야 배열

중요:
- 모든 필드 값은 문자열 또는 숫자여야 하며, null 값은 허용되지 않음
- persona는 하나의 일관된 문단 텍스트 설명이어야 하며, 줄바꿈 문자를 사용하지 말 것
- 모든 설명은 한국어를 사용할 것(단, gender 필드는 영어 "other"여야 함)
- age는 정수 30이어야 하고, gender는 문자열 "other"여야 함
- 기관 계정의 발언은 그 신분 포지셔닝에 부합해야 함
- 무의미한 추상 설명 대신 보험 가입/유지/해지/전환 판단에 쓰일 행동 조건을 구체적으로 작성하세요"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        source_entity_name: str = ""
    ) -> Dict[str, Any]:
        """규칙을 사용해 기본 페르소나 생성"""
        
        # 엔티티 유형에 따라 서로 다른 페르소나 생성
        entity_type_lower = entity_type.lower()
        source_label = source_entity_name or entity_type
        age = random.randint(28, 56)
        gender = random.choice(["male", "female"])
        mbti = random.choice(self.MBTI_TYPES)

        def insurance_persona(profession: str, stance: str, topics: List[str]) -> Dict[str, Any]:
            monthly_budget = random.choice(["월 8만원 이하", "월 10만원 안팎", "월 15만원까지", "기존 보험 포함 월 20만원 이하"])
            current_cover = random.choice(["실손보험만 보유", "암보험 1건과 실손보험 보유", "부모님 권유로 가입한 오래된 건강보험 보유", "기존 보험이 거의 없음"])
            risk = random.choice(["가족력 때문에 암 보장을 중시", "심혈관/뇌혈관 보장을 우선 확인", "자녀 의료비와 가족 보장을 함께 고려", "갱신 보험료와 청구 거절 가능성을 걱정"])
            decision = random.choice(["약관 예외가 많으면 가입하지 않음", "보험료 대비 보장 범위가 명확하면 가입", "설계사 설명보다 커뮤니티 후기와 실제 청구 사례를 더 신뢰", "개인정보 연동 범위가 불명확하면 보류"])
            after = random.choice(["가입 뒤 1년 안에 보험료 인상이나 청구 불편을 느끼면 해지 상담을 요청", "가입 뒤 청구 경험이 좋으면 유지하고 가족 특약을 검토", "경쟁상품이 같은 보장에 더 저렴하면 갈아타기를 검토", "개인정보 연동 조건이 바뀌면 데이터 제공을 철회하고 유지 여부를 재검토"])
            bio = f"{entity_name}는 {profession}이며 {source_label} 맥락에서 라이프핏 건강보험을 검토하는 현실적인 보험 소비자/채널 참여자입니다."
            persona = (
                f"{entity_name}는 {age}세 한국 거주자로 {profession} 역할을 가진다. "
                f"현재 보험 상태는 {current_cover}이고, 보험료 허용선은 {monthly_budget}이다. "
                f"건강 리스크는 {risk}이며 라이프핏 건강보험에 대해서는 {stance}. "
                f"가입 판단 기준은 {decision}이고, 약관복잡성·보험료·보장범위·개인정보 연동 중 무엇이 실제 손해로 이어질지를 따진다. "
                f"소셜 채널에서는 비교표, 실제 후기, 설계사 설명의 빈틈을 확인한 뒤 신중하게 반응한다. "
                f"가입 후 행동 규칙은 {after}이다. "
                f"말투는 구체적인 숫자와 사례를 요구하는 편이며, 모호한 홍보 문구보다 청구 절차와 면책 조건을 중시한다."
            )
            return {
                "bio": bio,
                "persona": persona,
                "age": age,
                "gender": gender,
                "mbti": mbti,
                "country": "한국",
                "profession": profession,
                "interested_topics": topics,
            }
        
        if entity_type_lower in ["student", "alumni"]:
            return insurance_persona("2030 예비 가입자", "보험료 부담 때문에 가입 전 비교가 길어지는 편", ["보험료", "청년 건강관리", "커뮤니티 후기"])
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return insurance_persona(entity_attributes.get("occupation", "보험/금융 전문가"), "상품 구조와 소비자 보호 장치를 분석적으로 검토하는 편", ["보험상품", "소비자 보호", "약관"])
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return insurance_persona("보험 전문 기자/콘텐츠 운영자", "출시 홍보보다 보험료·보장 실효성·개인정보 쟁점을 우선 기사화하는 편", ["보험 뉴스", "소비자 이슈", "개인정보"])
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return insurance_persona("보험사/기관 커뮤니케이션 담당자", "민원 확산을 줄이기 위해 약관 요약과 청구 절차를 보수적으로 설명하는 편", ["보험 민원", "약관 안내", "채널 운영"])
        
        else:
            # 기본 페르소나
            return insurance_persona(entity_attributes.get("occupation", entity_type), "출시 초기에는 관심을 보이지만 실제 가입 전 검증을 요구하는 편", ["건강보험", "보험료", "보장범위", "청구 경험"])
    
    def set_graph_id(self, graph_id: str):
        """Zep 검색을 위해 그래프 ID 설정"""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        엔티티로부터 Agent Profile을 일괄 생성（병렬 생성 지원）
        
        Args:
            entities: 엔티티 목록
            use_llm: LLM을 사용해 상세 페르소나를 생성할지 여부
            progress_callback: 진행률 콜백 함수 (current, total, message)
            graph_id: 그래프 ID, Zep 검색을 통해 더 풍부한 컨텍스트를 얻는 데 사용
            parallel_count: 병렬 생성 수, 기본 5
            realtime_output_path: 실시간으로 쓰는 파일 경로（제공되면, 하나 생성할 때마다 한 번씩 기록）
            output_platform: 출력 플랫폼 형식 ("reddit" 또는 "twitter")
            
        Returns:
            Agent Profile 목록
        """
        import concurrent.futures
        from threading import Lock
        
        # Zep 검색을 위해 graph_id 설정
        if graph_id:
            self.graph_id = graph_id
        
        total = len(entities)
        profiles = [None] * total  # 리스트를 미리 할당해 순서 유지
        completed_count = [0]  # 클로저에서 수정할 수 있도록 리스트 사용
        lock = Lock()
        
        # 실시간으로 파일에 쓰기 위한 보조 함수
        def save_profiles_realtime():
            """생성된 profiles를 실시간으로 파일에 저장"""
            if not realtime_output_path:
                return
            
            with lock:
                # 생성된 profiles만 필터링
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return
                
                try:
                    if output_platform == "reddit":
                        # Reddit JSON 형식
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV 형식
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"profiles 실시간 저장 실패: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """단일 profile 생성 작업 함수"""
            entity_type = entity.get_entity_type() or "Entity"
            
            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )
                
                # 생성된 페르소나를 실시간으로 콘솔과 로그에 출력
                self._print_generated_profile(entity.name, entity_type, profile)
                
                return idx, profile, None
                
            except Exception as e:
                logger.error(f"엔티티 {entity.name}의 페르소나 생성 실패: {str(e)}")
                # 기본 profile 생성
                fallback_name = self._generate_korean_person_name(idx)
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(fallback_name),
                    name=fallback_name,
                    bio=f"{fallback_name}는 {entity.name} 맥락을 대표하는 보험 시뮬레이션 참여자입니다.",
                    persona=(
                        entity.summary or
                        f"{fallback_name}는 라이프핏 건강보험의 보험료, 보장범위, 약관복잡성, 개인정보 연동 조건을 비교해 가입 여부를 판단합니다. "
                        "가입 후에는 청구 경험, 보험료 갱신, 경쟁상품 조건에 따라 유지·해지·전환 행동을 보입니다."
                    ),
                    source_entity_name=entity.name,
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)
        
        logger.info(f"{total}개의 Agent 페르소나 병렬 생성을 시작합니다(병렬 수: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Agent 페르소나 생성 시작 - 총 {total}개 엔티티, 병렬 수: {parallel_count}")
        print(f"{'='*60}\n")
        
        # 스레드 풀을 사용해 병렬 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # 모든 작업 제출
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"
                
                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile
                    
                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]
                    
                    # 파일에 실시간으로 기록
                    save_profiles_realtime()
                    
                    if progress_callback:
                        progress_callback(
                            current, 
                            total, 
                            f"완료 {current}/{total}: {entity.name}（{entity_type}）"
                        )
                    
                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} 예비 페르소나 사용: {error}")
                    else:
                        logger.info(f"[{current}/{total}] 페르소나 생성 성공: {entity.name} ({entity_type})")
                        
                except Exception as e:
                    logger.error(f"엔티티 {entity.name} 처리 중 예외 발생: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(self._generate_korean_person_name(idx)),
                        name=self._generate_korean_person_name(idx),
                        bio=f"{self._generate_korean_person_name(idx)}는 {entity.name} 맥락을 대표하는 보험 시뮬레이션 참여자입니다.",
                        persona=entity.summary or "라이프핏 건강보험의 가입·유지·해지·전환 조건을 구체적으로 비교하는 참여자입니다.",
                        source_entity_name=entity.name,
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # 파일에 실시간으로 기록(예비 페르소나라도)
                    save_profiles_realtime()
        
        print(f"\n{'='*60}")
        print(f"페르소나 생성 완료! 총 {len([p for p in profiles if p])}개의 Agent 생성")
        print(f"{'='*60}\n")
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """생성된 페르소나를 실시간으로 콘솔에 출력(전체 내용, 생략 없음)"""
        separator = "-" * 70
        
        # 전체 출력 내용 구성(생략 없음)
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else '없음'
        
        output_lines = [
            f"\n{separator}",
            f"[생성됨] {entity_name} ({entity_type})",
            f"{separator}",
            f"사용자명: {profile.user_name}",
            f"",
            f"【소개】",
            f"{profile.bio}",
            f"",
            f"【상세 페르소나】",
            f"{profile.persona}",
            f"",
            f"【기본 속성】",
            f"나이: {profile.age} | 성별: {profile.gender} | MBTI: {profile.mbti}",
            f"직업: {profile.profession} | 국가: {profile.country}",
            f"관심 주제: {topics_str}",
            separator
        ]
        
        output = "\n".join(output_lines)
        
        # 콘솔에만 출력(중복 방지, logger는 전체 내용을 더 이상 출력하지 않음)
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Profile을 파일로 저장(플랫폼에 따라 올바른 형식 선택)
        
        OASIS 플랫폼 형식 요구사항:
        - Twitter: CSV 형식
        - Reddit: JSON 형식
        
        Args:
            profiles: Profile 목록
            file_path: 파일 경로
            platform: 플랫폼 유형 ("reddit" 또는 "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Twitter Profile을 CSV 형식으로 저장(OASIS 공식 요구사항 준수)
        
        OASIS Twitter에서 요구하는 CSV 필드:
        - user_id: 사용자 ID(CSV 순서 기준으로 0부터 시작)
        - name: 사용자의 실제 이름
        - username: 시스템의 사용자명
        - user_char: 상세 페르소나 설명(LLM 시스템 프롬프트에 주입되어 Agent 행동을 안내)
        - description: 짧은 공개 소개(사용자 프로필 페이지에 표시)
        
        user_char vs description 차이:
        - user_char: 내부용, LLM 시스템 프롬프트로 Agent가 어떻게 생각하고 행동할지 결정
        - description: 외부 표시용, 다른 사용자가 볼 수 있는 소개
        """
        import csv
        
        # 파일 확장자가 .csv 인지 확인
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # OASIS에서 요구하는 헤더 작성
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)
            
            # 데이터 행 작성
            for idx, profile in enumerate(profiles):
                # user_char: 완전한 페르소나（bio + persona）, LLM 시스템 프롬프트에 사용
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # 줄바꿈 문자 처리（CSV에서는 공백으로 대체）
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')
                
                # description: 짧은 소개, 외부 표시용
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')
                
                row = [
                    idx,                    # user_id: 0부터 시작하는 순번 ID
                    profile.name,           # name: 실명
                    profile.user_name,      # username: 사용자명
                    user_char,              # user_char: 완전한 페르소나（내부 LLM 사용）
                    description             # description: 짧은 소개（외부 표시）
                ]
                writer.writerow(row)
        
        logger.info(f"Twitter Profile {len(profiles)}개를 {file_path}에 저장했습니다 (OASIS CSV 형식)")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        gender 필드를 OASIS에서 요구하는 영문 형식으로 표준화
        
        OASIS 요구 사항: male, female, other
        """
        if not gender:
            return "other"
        
        gender_lower = gender.lower().strip()
        
        # 입력값 표준화 매핑
        gender_map = {
            "남": "male",
            "여": "female",
            "기관": "other",
            "기타": "other",
            # 영어는 이미 존재
            "male": "male",
            "female": "female",
            "other": "other",
        }
        
        return gender_map.get(gender_lower, "other")

    def _normalize_country(self, country: Optional[str]) -> str:
        """국가명을 한국어 표기로 표준화"""
        if not country:
            return "한국"

        country_map = {
            "korea": "한국",
            "south korea": "한국",
            "republic of korea": "한국",
            "대한민국": "한국",
            "한국": "한국",
            "china": "중국",
            "중국": "중국",
            "\u4e2d\u56fd": "중국",
            "japan": "일본",
            "일본": "일본",
            "\u65e5\u672c": "일본",
            "us": "미국",
            "usa": "미국",
            "united states": "미국",
            "미국": "미국",
            "uk": "영국",
            "united kingdom": "영국",
            "영국": "영국",
        }
        return country_map.get(country.strip().lower(), country.strip())
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Reddit Profile을 JSON 형식으로 저장
        
        to_reddit_format()과 동일한 형식을 사용하여 OASIS가 올바르게 읽을 수 있도록 합니다.
        user_id 필드를 반드시 포함해야 하며, 이는 OASIS agent_graph.get_agent() 매칭의 핵심입니다!
        
        필수 필드：
        - user_id: 사용자 ID（정수, initial_posts 내의 poster_agent_id와 매칭용）
        - username: 사용자명
        - name: 표시 이름
        - bio: 소개
        - persona: 상세 페르소나
        - age: 나이（정수）
        - gender: "male", "female", 또는 "other"
        - mbti: MBTI 유형
        - country: 국가
        """
        data = []
        for idx, profile in enumerate(profiles):
            # to_reddit_format()과 동일한 형식 사용
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,  # 핵심：user_id를 반드시 포함
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # OASIS 필수 필드 - 모두 기본값이 있도록 보장
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": self._normalize_country(profile.country),
            }
            
            # 선택 필드
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics
            
            data.append(item)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Reddit Profile {len(profiles)}개를 {file_path}에 저장했습니다 (JSON 형식, user_id 필드 포함)")
    
    # 이전 메서드명을 별칭으로 유지하여 하위 호환성 유지
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[폐기됨] save_profiles() 메서드를 사용하세요"""
        logger.warning("save_profiles_to_json은 폐기되었습니다. save_profiles 메서드를 사용하세요")
        self.save_profiles(profiles, file_path, platform)
