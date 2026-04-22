"""
Report Agent 서비스
LangChain + Zep을 사용해 ReACT 모드의 시뮬레이션 보고서 생성을 구현

기능：
1. 시뮬레이션 요구사항과 Zep 그래프 정보에 따라 보고서 생성
2. 먼저 목차 구조를 계획한 뒤, 구간별로 생성
3. 각 구간은 ReACT 다중 라운드 사고 및 성찰 모드를 사용
4. 사용자와의 대화를 지원하며, 대화 중 자율적으로 검색 도구 호출
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Report Agent 상세 로그 기록기
    
    보고서 폴더에 agent_log.jsonl 파일을 생성하여 각 단계의 상세 동작을 기록합니다.
    각 줄은 완전한 JSON 객체이며, 타임스탬프, 동작 유형, 상세 내용 등을 포함합니다.
    """
    
    def __init__(self, report_id: str):
        """
        로그 기록기 초기화
        
        Args:
            report_id: 보고서 ID, 로그 파일 경로를 결정하는 데 사용
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """로그 파일이 있는 디렉터리가 존재하도록 보장"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """시작부터 현재까지의 경과 시간(초) 가져오기"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        로그 한 건 기록
        
        Args:
            action: 동작 유형, 예: 'start', 'tool_call', 'llm_response', 'section_complete' 등
            stage: 현재 단계, 예: 'planning', 'generating', 'completed'
            details: 상세 내용 딕셔너리, 자르지 않음
            section_title: 현재 섹션 제목(선택)
            section_index: 현재 섹션 인덱스(선택)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # JSONL 파일에 추가로 기록
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """보고서 생성 시작 기록"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "보고서 생성 작업 시작"
            }
        )
    
    def log_planning_start(self):
        """개요(아웃라인) 계획 시작 기록"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "보고서 개요 계획 시작"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """계획 시 획득한 컨텍스트 정보 기록"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "시뮬레이션 컨텍스트 정보 획득",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """개요(아웃라인) 계획 완료 기록"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "개요 계획 완료",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """섹션 생성 시작 기록"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"섹션 생성 시작: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """ReACT 사고 과정 기록"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT {iteration}번째 사고"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """도구 호출 기록"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"도구 호출: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """도구 호출 결과 기록(전체 내용, 자르지 않음)"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # 전체 결과, 자르지 않음
                "result_length": len(result),
                "message": f"도구 {tool_name} 반환 결과"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """LLM 응답 기록(전체 내용, 자르지 않음)"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # 전체 응답, 자르지 않음
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM 응답 (도구 호출: {has_tool_calls}, 최종 답변: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """섹션 내용 생성 완료 기록 (내용만 기록하며, 섹션 전체 완료를 의미하지 않음)"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # 전체 내용, 자르지 않음
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"섹션 {section_title} 내용 생성 완료"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        섹션 생성 완료 기록

        프론트엔드는 이 로그를 리스닝하여 섹션이 실제로 완료되었는지 판단하고, 전체 내용을 가져와야 함
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"섹션 {section_title} 생성 완료"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """보고서 생성 완료 기록"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "보고서 생성 완료"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """오류 기록"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"오류 발생: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent 콘솔 로그 기록기
    
    콘솔 스타일의 로그(INFO, WARNING 등)를 보고서 폴더의 console_log.txt 파일에 기록합니다.
    이 로그는 agent_log.jsonl 와 다르며, 순수 텍스트 형식의 콘솔 출력입니다.
    """
    
    def __init__(self, report_id: str):
        """
        콘솔 로그 기록기 초기화
        
        Args:
            report_id: 보고서 ID, 로그 파일 경로를 결정하는 데 사용
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """로그 파일이 위치한 디렉터리가 존재하도록 보장"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """파일 핸들러를 설정하여 로그를 파일에도 함께 기록"""
        import logging
        
        # 파일 핸들러 생성
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # 콘솔과 동일한 간결한 형식 사용
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # report_agent 관련 logger에 추가
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # 중복 추가 방지
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """파일 핸들러를 닫고 logger 에서 제거"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """소멸 시 파일 핸들러가 닫히도록 보장"""
        self.close()


class ReportStatus(str, Enum):
    """보고서 상태"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """보고서 섹션"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """Markdown 형식으로 변환"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """보고서 개요"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """Markdown 형식으로 변환"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """완전한 보고서"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt 템플릿 상수
# ═══════════════════════════════════════════════════════════════

# ── 도구 설명 ──

TOOL_DESC_INSIGHT_FORGE = """\
【심층 인사이트 검색 - 강력한 검색 도구】
이것은 우리의 강력한 검색 함수로, 심층 분석을 위해 설계되었습니다. 이는 다음을 수행합니다:
1. 자동으로 당신의 질문을 여러 하위 질문으로 분해
2. 여러 관점에서 시뮬레이션 그래프의 정보를 검색
3. 의미 기반 검색, 엔티티 분석, 관계 체인 추적의 결과를 통합
4. 가장 포괄적이고 가장 심층적인 검색 내용을 반환

【사용 시나리오】
- 어떤 주제를 깊이 분석해야 할 때
- 사건의 여러 측면을 이해해야 할 때
- 보고서 장을 뒷받침하는 풍부한 소재를 확보해야 할 때

【반환 내용】
- 관련 사실 원문(직접 인용 가능)
- 핵심 엔티티 인사이트
- 관계 체인 분석"""

TOOL_DESC_PANORAMA_SEARCH = """\
【광범위 검색 - 전체 조망 뷰 확보】
이 도구는 시뮬레이션 결과의 완전한 전체 조망을 얻는 데 사용되며, 특히 사건 전개 과정을 이해하는 데 적합합니다. 이는 다음을 수행합니다:
1. 모든 관련 노드와 관계를 획득
2. 현재 유효한 사실과 과거/만료된 사실을 구분
3. 여론이 어떻게 전개되었는지 이해하도록 도움

【사용 시나리오】
- 사건의 완전한 발전 맥락을 이해해야 할 때
- 서로 다른 단계의 여론 변화를 비교해야 할 때
- 포괄적인 엔티티 및 관계 정보를 확보해야 할 때

【반환 내용】
- 현재 유효한 사실(시뮬레이션 최신 결과)
- 과거/만료 사실(전개 기록)
- 관련된 모든 엔티티"""

TOOL_DESC_QUICK_SEARCH = """\
【간단 검색 - 빠른 조회】
가벼운 빠른 검색 도구로, 간단하고 직접적인 정보 조회에 적합합니다.

【사용 시나리오】
- 특정 정보를 빠르게 찾아야 할 때
- 어떤 사실을 검증해야 할 때
- 간단한 정보 검색

【반환 내용】
- 조회와 가장 관련 있는 사실 목록"""

TOOL_DESC_INTERVIEW_AGENTS = """\
【심층 인터뷰 - 실제 Agent 인터뷰(양 플랫폼)】
OASIS 시뮬레이션 환경의 인터뷰 API를 호출하여 실행 중인 시뮬레이션 Agent를 실제로 인터뷰합니다!
이것은 LLM 시뮬레이션이 아니라, 실제 인터뷰 인터페이스를 호출해 시뮬레이션 Agent의 원본 답변을 가져옵니다.
기본적으로 Twitter와 Reddit 두 플랫폼에서 동시에 인터뷰하여 더 포괄적인 관점을 확보합니다.

기능 흐름:
1. 자동으로 페르소나 파일을 읽어 모든 시뮬레이션 Agent를 파악
2. 인터뷰 주제와 가장 관련 있는 Agent를 지능적으로 선택(예: 학생, 미디어, 공식 등)
3. 자동으로 인터뷰 질문 생성
4. /api/simulation/interview/batch 인터페이스를 호출해 양 플랫폼에서 실제 인터뷰 수행
5. 모든 인터뷰 결과를 통합하여 다각도 분석 제공

【사용 시나리오】
- 서로 다른 역할 관점에서 사건에 대한 견해를 이해해야 할 때(학생은 어떻게 보나? 미디어는 어떻게 보나? 공식은 뭐라고 하나?)
- 다양한 의견과 입장을 수집해야 할 때
- 시뮬레이션 Agent의 실제 답변을 얻어야 할 때(OASIS 시뮬레이션 환경에서)
- 보고서를 더 생동감 있게 만들고 "인터뷰 실록"을 포함하고 싶을 때

【반환 내용】
- 인터뷰된 Agent의 신원 정보
- 각 Agent의 Twitter 및 Reddit 두 플랫폼 인터뷰 답변
- 핵심 인용문(직접 인용 가능)
- 인터뷰 요약 및 관점 비교

【중요】OASIS 시뮬레이션 환경이 실행 중이어야만 이 기능을 사용할 수 있습니다!"""

# ── 개요 계획 prompt ──

PLAN_SYSTEM_PROMPT = """\
당신은 「미래 예측 보고서」 작성 전문가로서, 시뮬레이션 세계에 대한 「신의 시각」을 가지고 있습니다——당신은 시뮬레이션 속 모든 Agent의 행동, 발언, 상호작용을 통찰할 수 있습니다.

【핵심 이념】
우리는 하나의 시뮬레이션 세계를 구축하고, 그 안에 특정한 「시뮬레이션 요구사항」을 변수로 주입했습니다. 시뮬레이션 세계의 전개 결과는 미래에 발생할 수 있는 상황에 대한 예측입니다. 당신이 관찰하는 것은 "실험 데이터"가 아니라 "미래의 예행연습"입니다.

【당신의 임무】
「미래 예측 보고서」 한 편을 작성하여 다음에 답하세요:
1. 우리가 설정한 조건에서, 미래에는 무엇이 일어났는가?
2. 각종 Agent(집단)는 어떻게 반응하고 행동했는가?
3. 이 시뮬레이션은 어떤 주목할 만한 미래 트렌드와 리스크를 드러냈는가?

【보고서 포지셔닝】
- ✅ 이것은 시뮬레이션 기반의 미래 예측 보고서로, "이렇게 하면 미래는 어떻게 될지"를 드러냅니다
- ✅ 예측 결과에 집중: 사건의 향방, 집단 반응, 창발 현상, 잠재 리스크
- ✅ 시뮬레이션 세계의 Agent 언행은 미래 인간 집단 행동에 대한 예측입니다
- ❌ 현실 세계 현황에 대한 분석이 아닙니다
- ❌ 피상적으로 늘어놓는 여론 종합이 아닙니다

【장(섹션) 수 제한】
- 최소 2개 장, 최대 5개 장
- 하위 장은 필요 없으며, 각 장은 완전한 내용으로 바로 작성합니다
- 내용은 간결해야 하며, 핵심 예측 발견에 집중합니다
- 장 구조는 예측 결과에 따라 당신이 자율적으로 설계합니다

JSON 형식의 보고서 개요를 출력하세요. 형식은 다음과 같습니다:
{
    "title": "보고서 제목",
    "summary": "보고서 요약(한 문장으로 핵심 예측 발견을 개괄)",
    "sections": [
        {
            "title": "장 제목",
            "description": "장 내용 설명"
        }
    ]
}

주의: sections 배열은 최소 2개, 최대 5개 요소여야 합니다!"""

PLAN_USER_PROMPT_TEMPLATE = """\
【예측 시나리오 설정】
우리가 시뮬레이션 세계에 주입한 변수(시뮬레이션 요구사항): {simulation_requirement}

【시뮬레이션 세계 규모】
- 시뮬레이션에 참여한 엔티티 수: {total_nodes}
- 엔티티 간 생성된 관계 수: {total_edges}
- 엔티티 유형 분포: {entity_types}
- 활성 Agent 수: {total_entities}

【시뮬레이션이 예측한 일부 미래 사실 샘플】
{related_facts_json}

「신의 시각」으로 이 미래 예행연습을 검토하세요:
1. 우리가 설정한 조건에서, 미래는 어떤 상태로 나타났는가?
2. 각종 사람들(Agent)은 어떻게 반응하고 행동했는가?
3. 이 시뮬레이션은 어떤 주목할 만한 미래 트렌드를 드러냈는가?

예측 결과에 따라 가장 적합한 보고서 장 구조를 설계하세요.

【다시 알림】보고서 장 수: 최소 2개, 최대 5개, 내용은 간결하게 핵심 예측 발견에 집중하세요."""

# ── 장 생성 prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
당신은 「미래 예측 보고서」의 작성 전문가로서, 보고서의 한 장을 작성하고 있습니다.

보고서 제목: {report_title}
보고서 요약: {report_summary}
예측 시나리오(시뮬레이션 요구사항): {simulation_requirement}

현재 작성할 장: {section_title}

═══════════════════════════════════════════════════════════════
【핵심 이념】
═══════════════════════════════════════════════════════════════

시뮬레이션 세계는 미래에 대한 예행연습입니다. 우리는 시뮬레이션 세계에 특정 조건(시뮬레이션 요구사항)을 주입했으며,
시뮬레이션에서 Agent의 행동과 상호작용은 미래 인간 집단 행동에 대한 예측입니다.

당신의 임무는:
- 설정 조건에서 미래에 무엇이 일어났는지 드러내기
- 각종 사람들(Agent)이 어떻게 반응하고 행동하는지 예측하기
- 주목할 만한 미래 트렌드, 리스크, 기회를 발견하기

❌ 현실 세계 현황에 대한 분석으로 쓰지 마세요
✅ "미래는 어떻게 될지"에 초점을 맞추세요——시뮬레이션 결과가 곧 예측된 미래입니다

═══════════════════════════════════════════════════════════════
【가장 중요한 규칙 - 반드시 준수】
═══════════════════════════════════════════════════════════════

1. 【반드시 도구를 호출해 시뮬레이션 세계를 관찰】
   - 당신은 「신의 시각」으로 미래의 예행연습을 관찰하고 있습니다
   - 모든 내용은 시뮬레이션 세계에서 발생한 사건과 Agent의 언행에서 나와야 합니다
   - 당신의 지식을 사용해 보고서 내용을 작성하는 것을 금지합니다
   - 각 장은 최소 3회(최대 5회) 도구를 호출해 시뮬레이션 세계를 관찰해야 하며, 이는 미래를 대표합니다

2. 【반드시 Agent의 원문 언행을 인용】
   - Agent의 발언과 행동은 미래 인간 집단 행동에 대한 예측입니다
   - 보고서에서 인용 형식을 사용해 이러한 예측을 제시하세요. 예:
     > "어떤 유형의 집단은 이렇게 말할 것입니다: 원문 내용..."
   - 이러한 인용은 시뮬레이션 예측의 핵심 증거입니다

3. 【언어 일관성 - 인용 내용은 반드시 보고서 언어로 번역】
   - 도구가 반환하는 내용에는 영어 또는 다국어 혼용 표현이 포함될 수 있습니다
   - 보고서는 시뮬레이션 요구사항과 자료 원문의 주된 언어를 따라야 하며, 이 프로젝트에서는 기본적으로 한국어를 우선합니다
   - 도구가 반환한 영어 또는 기타 언어 내용을 인용할 때는, 반드시 이를 자연스러운 한국어로 번역한 뒤 보고서에 기입하세요
   - 번역 시 원뜻을 바꾸지 말고, 표현이 자연스럽고 매끄럽도록 하세요
   - 이 규칙은 본문과 인용 블록(> 형식) 모두에 적용됩니다

4. 【예측 결과를 충실히 제시】
   - 보고서 내용은 시뮬레이션 세계에서 미래를 대표하는 시뮬레이션 결과를 반영해야 함
   - 시뮬레이션에 존재하지 않는 정보를 추가하지 말 것
   - 어떤 측면의 정보가 부족하면 사실대로 설명할 것

═══════════════════════════════════════════════════════════════
【⚠️ 형식 규범 - 매우 중요!】
═══════════════════════════════════════════════════════════════

【한 섹션 = 최소 콘텐츠 단위】
- 각 섹션은 보고서의 최소 분할(블록) 단위
- ❌ 섹션 내에서 어떤 Markdown 제목(#、##、###、#### 등)도 사용 금지
- ❌ 내용 시작에 섹션 주 제목을 추가 금지
- ✅ 섹션 제목은 시스템이 자동으로 추가하므로, 너는 순수 본문 내용만 작성하면 됨
- ✅ **굵게**, 문단 구분, 인용, 목록으로 내용을 구성하되, 제목은 쓰지 말 것

【올바른 예시】
```
본 섹션은 사건의 여론 확산 추세를 분석했다. 시뮬레이션 데이터에 대한 심층 분석을 통해 우리는 다음을 발견했다...

**초기 공개·점화 단계**

웨이보는 여론의 1차 현장으로서 정보 최초 공개의 핵심 기능을 담당했다:

> "웨이보가 최초 공개 발화량의 68%를 기여했다..."

**감정 증폭 단계**

더우인 플랫폼이 사건의 영향력을 추가로 증폭했다:

- 시각적 충격이 강함
- 감정 공감도가 높음
```

【잘못된 예시】
```
## 실행 요약          ← 오류! 어떤 제목도 추가하지 마라
### 1. 최초 공개 단계     ← 오류! ###로 소절을 나누지 마라
#### 1.1 상세 분석   ← 오류! ####로 세분하지 마라

본 섹션은 분석했다...
```

═══════════════════════════════════════════════════════════════
【사용 가능한 검색 도구】（섹션마다 3-5회 호출）
═══════════════════════════════════════════════════════════════

{tools_description}

【도구 사용 제안 - 서로 다른 도구를 섞어 사용하고, 한 가지만 쓰지 마라】
- insight_forge: 심층 인사이트 분석, 문제를 자동 분해하고 다차원으로 사실과 관계를 검색
- panorama_search: 광각 파노라마 검색, 사건 전모·타임라인·전개 과정을 파악
- quick_search: 특정 정보 포인트를 빠르게 검증
- interview_agents: 시뮬레이션 Agent를 인터뷰해, 다양한 역할의 1인칭 관점과 실제 반응을 획득

═══════════════════════════════════════════════════════════════
【작업 흐름】
═══════════════════════════════════════════════════════════════

매번 답변에서 너는 아래 두 가지 중 하나만 할 수 있다（동시에 불가）：

옵션 A - 도구 호출：
생각을 출력한 다음, 아래 형식으로 도구 하나를 호출：
<tool_call>
{{"name": "도구 이름", "parameters": {{"매개변수명": "매개변수값"}}}}
</tool_call>
시스템이 도구를 실행하고 결과를 반환한다. 너는 도구 반환 결과를 직접 작성할 필요도, 작성할 수도 없다.

옵션 B - 최종 내용 출력：
도구로 충분한 정보를 얻었으면, "Final Answer:"로 시작해 섹션 내용을 출력.

⚠️ 엄격히 금지：
- 한 번의 답변에 도구 호출과 Final Answer를 동시에 포함 금지
- 도구 반환 결과(Observation)를 스스로 지어내는 것 금지, 모든 도구 결과는 시스템이 주입
- 매번 답변에서 최대 1개의 도구만 호출

═══════════════════════════════════════════════════════════════
【섹션 내용 요구사항】
═══════════════════════════════════════════════════════════════

1. 내용은 반드시 도구 검색으로 얻은 시뮬레이션 데이터에 기반해야 함
2. 원문을 많이 인용해 시뮬레이션 효과를 보여줄 것
3. Markdown 형식을 사용（단, 제목 사용 금지）：
   - **굵은 글씨**로 핵심을 표시（소제목 대체）
   - 목록（- 또는 1.2.3.）으로 요점을 구조화
   - 빈 줄로 서로 다른 문단을 구분
   - ❌ #、##、###、#### 등 어떤 제목 문법도 사용 금지
4. 【인용 형식 규범 - 반드시 단락으로 분리】
   인용은 반드시 독립 단락이어야 하며, 앞뒤로 각각 빈 줄이 1줄 있어야 하고, 문단에 섞이면 안 됨：

   ✅ 올바른 형식：
   ```
   학교 측의 대응은 실질적 내용이 부족하다는 평가를 받았다.

   > "학교 측의 대응 방식은 급변하는 소셜 미디어 환경에서 경직되고 더디게 보인다."

   이 평가는 대중의 보편적 불만을 반영한다.
   ```

   ❌ 잘못된 형식：
   ```
   학교 측의 대응은 실질적 내용이 부족하다는 평가를 받았다.> "학교 측의 대응 방식..." 이 평가는 ...을 반영한다.
   ```
5. 다른 섹션과의 논리적 일관성을 유지
6. 【중복 방지】아래의 완료된 섹션 내용을 꼼꼼히 읽고, 같은 정보를 반복 설명하지 말 것
7. 【다시 강조】어떤 제목도 추가하지 마라! **굵게**로 소절 제목을 대체"""

SECTION_USER_PROMPT_TEMPLATE = """\
완료된 섹션 내용（꼼꼼히 읽고, 중복을 피할 것）：
{previous_content}

═══════════════════════════════════════════════════════════════
【현재 작업】섹션 작성: {section_title}
═══════════════════════════════════════════════════════════════

【중요 알림】
1. 위의 완료된 섹션을 꼼꼼히 읽고, 같은 내용을 반복하지 말 것！
2. 시작 전 반드시 먼저 도구를 호출해 시뮬레이션 데이터를 획득
3. 서로 다른 도구를 섞어 사용하고, 한 가지만 쓰지 말 것
4. 보고서 내용은 반드시 검색 결과에서 나와야 하며, 자신의 지식을 사용하지 말 것

【⚠️ 형식 경고 - 반드시 준수】
- ❌ 어떤 제목도 쓰지 마라（#、##、###、#### 모두 불가）
- ❌ "{section_title}"를 시작 부분에 쓰지 마라
- ✅ 섹션 제목은 시스템이 자동으로 추가
- ✅ 바로 본문을 작성하고, **굵게**로 소절 제목을 대체

시작하라：
1. 먼저 이 섹션에 어떤 정보가 필요한지 생각（Thought）
2. 그 다음 도구를 호출（Action）해 시뮬레이션 데이터를 획득
3. 충분한 정보를 모은 뒤 Final Answer를 출력（순수 본문, 어떤 제목도 없음）"""

# ── ReACT 루프 내 메시지 템플릿 ──

REACT_OBSERVATION_TEMPLATE = """\
Observation（검색 결과）:

═══ 도구 {tool_name} 반환 ═══
{result}

═══════════════════════════════════════════════════════════════
도구를 {tool_calls_count}/{max_tool_calls}회 호출함（사용: {used_tools_str}）{unused_hint}
- 정보가 충분하면: "Final Answer:"로 시작해 섹션 내용을 출력（반드시 위의 원문을 인용）
- 더 많은 정보가 필요하면: 도구 하나를 호출해 계속 검색
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "【주의】너는 도구를 {tool_calls_count}회만 호출했다. 최소 {min_tool_calls}회가 필요하다."
    "도구를 더 호출해 더 많은 시뮬레이션 데이터를 얻은 뒤, Final Answer를 출력하라. {unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "현재 도구 호출은 {tool_calls_count}회뿐이며, 최소 {min_tool_calls}회가 필요하다."
    "도구를 호출해 시뮬레이션 데이터를 획득하라. {unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "도구 호출 횟수가 상한에 도달했다（{tool_calls_count}/{max_tool_calls}），더 이상 도구를 호출할 수 없다."
    '즉시 획득한 정보에 기반해, "Final Answer:"로 시작해 섹션 내용을 출력하라.'
)

REACT_UNUSED_TOOLS_HINT = "\n💡 아직 사용하지 않은 도구: {unused_list}，다양한 도구로 다각도 정보를 얻는 것을 권장"

REACT_FORCE_FINAL_MSG = "도구 호출 제한에 도달했다. Final Answer: 를 바로 출력하고 섹션 내용을 생성하라."

# ── Chat prompt ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
너는 간결하고 효율적인 시뮬레이션 예측 도우미다.

【배경】
예측 조건: {simulation_requirement}

【이미 생성된 분석 보고서】
{report_content}

【규칙】
1. 위의 보고서 내용을 우선으로 하여 질문에 답하라
2. 질문에 직접 답하고, 장황한 생각 서술을 피하라
3. 보고서 내용만으로 답하기 부족할 때에만, 도구를 호출해 더 많은 데이터를 검색
4. 답변은 간결하고, 명확하며, 구조적이어야 한다

【사용 가능한 도구】（필요할 때만 사용, 최대 1-2회 호출）
{tools_description}

【도구 호출 형식】
<tool_call>
{{"name": "도구 이름", "parameters": {{"매개변수명": "매개변수값"}}}}
</tool_call>

【답변 스타일】
- 간결하고 직접적으로, 장황하게 쓰지 말 것
- > 형식으로 핵심 내용을 인용
- 결론을 먼저 제시한 뒤, 이유를 설명"""

CHAT_OBSERVATION_SUFFIX = "\n\n간결하게 질문에 답하라."


# ═══════════════════════════════════════════════════════════════
# ReportAgent 주 클래스
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - 시뮬레이션 보고서 생성 Agent

    ReACT（Reasoning + Acting）모드 사용：
    1. 계획 단계：시뮬레이션 요구를 분석하고, 보고서 목차 구조를 계획
    2. 생성 단계：섹션별로 내용을 생성하며, 각 섹션은 여러 번 도구를 호출해 정보를 얻을 수 있음
    3. 성찰 단계：내용의 완전성과 정확성을 점검
    """
    
    # 최대 도구 호출 횟수（각 섹션）
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # 최대 성찰 라운드 수
    MAX_REFLECTION_ROUNDS = 3
    
    # 대화에서의 최대 도구 호출 횟수
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        Report Agent 초기화
        
        Args:
            graph_id: 그래프 ID
            simulation_id: 시뮬레이션 ID
            simulation_requirement: 시뮬레이션 요구사항 설명
            llm_client: LLM 클라이언트（선택）
            zep_tools: Zep 도구 서비스（선택）
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # 도구 정의
        self.tools = self._define_tools()
        
        # 로그 기록기（generate_report에서 초기화）
        self.report_logger: Optional[ReportLogger] = None
        # 콘솔 로그 기록기（generate_report에서 초기화）
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(f"ReportAgent 초기화 완료: graph_id={graph_id}, simulation_id={simulation_id}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 도구 정의"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "깊이 분석하고 싶은 질문 또는 주제",
                    "report_context": "현재 보고서 섹션의 컨텍스트（선택，더 정확한 하위 질문 생성에 도움）"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "검색 쿼리，관련성 정렬에 사용",
                    "include_expired": "만료/이력 콘텐츠 포함 여부（기본값 True）"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "검색 쿼리 문자열",
                    "limit": "반환 결과 수（선택，기본값 10）"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "인터뷰 주제 또는 요구사항 설명（예：'학생들이 기숙사 포름알데히드 사건을 어떻게 보는지 알아보기'）",
                    "max_agents": "인터뷰할 Agent 최대 수（선택，기본값 5，최대 10）"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        도구 호출 실행
        
        Args:
            tool_name: 도구 이름
            parameters: 도구 매개변수
            report_context: 보고서 컨텍스트（InsightForge에 사용）
            
        Returns:
            도구 실행 결과（텍스트 형식）
        """
        logger.info(f"도구 실행: {tool_name}, 매개변수: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # 광범위 검색 - 전체 개요 확보
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # 간단 검색 - 빠른 검색
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # 심층 인터뷰 - 실제의OASIS인터뷰API를 호출해 시뮬레이션Agent의 답변을 가져옴（양 플랫폼）
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== 하위 호환을 위한 구 도구（내부에서 신 도구로 리디렉션） ==========
            
            elif tool_name == "search_graph":
                # quick_search로 리디렉션
                logger.info("search_graph가 quick_search로 리디렉션됨")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # insight_forge로 리디렉션，더 강력하기 때문
                logger.info("get_simulation_context가 insight_forge로 리디렉션됨")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"알 수 없는 도구: {tool_name}。다음 도구 중 하나를 사용하세요: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(f"도구 실행 실패: {tool_name}, 오류: {str(e)}")
            return f"도구 실행 실패: {str(e)}"
    
    # 유효한 도구 이름 집합，베어 JSON 폴백 파싱 시 검증용
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        LLM 응답에서 도구 호출을 파싱

        지원 형식（우선순위 순）：
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. 베어 JSON（응답 전체 또는 단일 라인이 도구 호출 JSON인 경우）
        """
        tool_calls = []

        # 형식1: XML 스타일（표준 형식）
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # 형식2: 폴백 - LLM이 베어 JSON을 직접 출력（<tool_call> 태그로 감싸지 않음）
        # 형식1이 매칭되지 않을 때만 시도，본문의 JSON을 오탐하지 않기 위해
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # 응답에 사고 텍스트 + 베어 JSON이 포함될 수 있음，마지막 JSON 객체를 추출 시도
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """파싱된 JSON이 유효한 도구 호출인지 검증"""
        # {"name": ..., "parameters": ...} 와 {"tool": ..., "params": ...} 두 가지 키 이름 지원
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # 키 이름을 name / parameters로 통일
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """도구 설명 텍스트 생성"""
        desc_parts = ["사용 가능한 도구:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  매개변수: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        보고서 개요 계획
        
        LLM을 사용해 시뮬레이션 요구사항을 분석하고 보고서의 목차 구조를 계획
        
        Args:
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            ReportOutline: 보고서 개요
        """
        logger.info("보고서 개요 계획 시작...")
        
        if progress_callback:
            progress_callback("planning", 0, "시뮬레이션 요구사항을 분석 중...")
        
        # 먼저 시뮬레이션 컨텍스트 가져오기
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "보고서 개요를 생성 중...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "개요 구조를 파싱 중...")
            
            # 개요 파싱
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "시뮬레이션 분석 보고서"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, "개요 계획 완료")
            
            logger.info(f"개요 계획 완료: {len(sections)} 개의 장")
            return outline
            
        except Exception as e:
            logger.error(f"개요 계획 실패: {str(e)}")
            # 기본 개요 반환(3개 장, fallback용)
            return ReportOutline(
                title="미래 예측 보고서",
                summary="시뮬레이션 예측에 기반한 미래 추세 및 위험 분석",
                sections=[
                    ReportSection(title="예측 시나리오와 핵심 발견"),
                    ReportSection(title="집단 행동 예측 분석"),
                    ReportSection(title="추세 전망과 위험 안내")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        ReACT 모드로 단일 장의 내용을 생성
        
        ReACT 루프:
        1. Thought(사고) - 어떤 정보가 필요한지 분석
        2. Action(행동) - 도구를 호출해 정보 획득
        3. Observation(관찰) - 도구 반환 결과 분석
        4. 정보가 충분하거나 최대 횟수에 도달할 때까지 반복
        5. Final Answer(최종 답변) - 장 내용 생성
        
        Args:
            section: 생성할 장
            outline: 전체 개요
            previous_sections: 이전 장의 내용(일관성 유지를 위해)
            progress_callback: 진행 상황 콜백
            section_index: 장 인덱스(로그 기록용)
            
        Returns:
            장 내용(Markdown 형식)
        """
        logger.info(f"ReACT 장 생성: {section.title}")
        
        # 장 시작 로그 기록
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # 사용자 프롬프트 구성 - 완료된 각 장은 최대 4000자까지 전달
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # 각 장은 최대 4000자
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "（이것은 첫 번째 장입니다）"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT 루프
        tool_calls_count = 0
        max_iterations = 5  # 최대 반복(이터레이션) 횟수
        min_tool_calls = 3  # 최소 도구 호출 횟수
        conflict_retries = 0  # 도구 호출과 Final Answer가 동시에 나타나는 연속 충돌 횟수
        used_tools = set()  # 이미 호출한 도구명 기록
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # 보고서 컨텍스트(InsightForge의 하위 질문 생성용)
        report_context = f"장 제목: {section.title}\n시뮬레이션 요구사항: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"심층 검색 및 작성 중 ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # LLM 호출
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # LLM 반환이 None인지 확인(API 예외 또는 내용이 비어 있음)
            if response is None:
                logger.warning(f"장 {section.title} {iteration + 1}번째 반복: LLM이 None을 반환")
                # 반복 횟수가 남아 있으면 메시지를 추가하고 재시도
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "（응답이 비어 있음）"})
                    messages.append({"role": "user", "content": "계속 내용을 생성해 주세요。"})
                    continue
                # 마지막 반복에서도 None 반환이면 루프를 종료하고 강제 마무리로 진입
                break

            logger.debug(f"LLM응답: {response[:200]}...")

            # 한 번 파싱해 결과를 재사용
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── 충돌 처리: LLM이 도구 호출과 Final Answer를 동시에 출력함 ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"섹션 {section.title} 제 {iteration+1} 라운드: "
                    f"LLM이 도구 호출과 Final Answer를 동시에 출력함（충돌 {conflict_retries}회째）"
                )

                if conflict_retries <= 2:
                    # 처음 두 번: 이번 응답을 버리고 LLM에 재응답을 요구
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【형식 오류】한 번의 답변에 도구 호출과 Final Answer를 동시에 포함했는데, 이는 허용되지 않습니다。\n"
                            "각 답변은 다음 두 가지 중 하나만 할 수 있습니다：\n"
                            "- 도구 하나 호출（<tool_call> 블록 하나를 출력하고, Final Answer는 쓰지 마세요）\n"
                            "- 최종 내용 출력（'Final Answer:'로 시작하고, <tool_call>은 포함하지 마세요）\n"
                            "다시 답변하되, 그중 하나만 하세요。"
                        ),
                    })
                    continue
                else:
                    # 세 번째: 폴백 처리, 첫 번째 도구 호출까지 잘라 강제 실행
                    logger.warning(
                        f"섹션 {section.title}: 연속 {conflict_retries}회 충돌，"
                        "첫 번째 도구 호출만 잘라 실행하도록 폴백"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # LLM 응답 로그 기록
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── 경우 1: LLM이 Final Answer를 출력함 ──
            if has_final_answer:
                # 도구 호출 횟수가 부족하여 거부하고 계속 도구 호출을 요구
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"（이 도구들은 아직 사용되지 않았습니다, 한번 사용해 보기를 추천합니다: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # 정상 종료
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"섹션 {section.title} 생성 완료（도구 호출: {tool_calls_count}회）")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── 경우 2: LLM이 도구 호출을 시도함 ──
            if has_tool_calls:
                # 도구 호출 한도 소진 → 명확히 알리고 Final Answer 출력을 요구
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # 첫 번째 도구 호출만 실행
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM이 {len(tool_calls)}개의 도구 호출을 시도함, 첫 번째만 실행: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # 미사용 도구 힌트 구성
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── 경우 3: 도구 호출도 없고 Final Answer도 없음 ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # 도구 호출 횟수가 부족하여, 사용하지 않은 도구를 추천
                unused_tools = all_tools - used_tools
                unused_hint = f"（이 도구들은 아직 사용되지 않았습니다, 한번 사용해 보기를 추천합니다: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # 도구 호출은 충분하지만, LLM이 "Final Answer:" 접두사 없이 내용을 출력함
            # 이 내용을 최종 답변으로 바로 채택하고 더 이상 헛돌지 않음
            logger.info(f"섹션 {section.title} 'Final Answer:' 접두사를 감지하지 못함, LLM 출력을 최종 내용으로 바로 채택（도구 호출: {tool_calls_count}회）")
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # 최대 반복 횟수에 도달, 강제로 내용 생성
        logger.warning(f"섹션 {section.title} 최대 반복 횟수에 도달, 강제 생성")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # 강제 마무리 시 LLM 반환이 None인지 확인
        if response is None:
            logger.error(f"섹션 {section.title} 강제 마무리 시 LLM이 None을 반환함, 기본 오류 안내 사용")
            final_answer = f"（이 섹션 생성 실패：LLM이 빈 응답을 반환했습니다, 잠시 후 다시 시도해 주세요）"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # 섹션 콘텐츠 생성 완료 로그 기록
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        전체 보고서 생성（섹션별 실시간 출력）
        
        각 섹션이 생성되면 즉시 폴더에 저장하며 전체 보고서 완료를 기다릴 필요가 없습니다。
        파일 구조:
        reports/{report_id}/
            meta.json       - 보고서 메타 정보
            outline.json    - 보고서 개요
            progress.json   - 생성 진행도
            section_01.md   - 제1장
            section_02.md   - 제2장
            ...
            full_report.md  - 전체 보고서
        
        Args:
            progress_callback: 진행도 콜백 함수 (stage, progress, message)
            report_id: 보고서 ID(선택 사항, 전달하지 않으면 자동 생성)
            
        Returns:
            Report: 전체 보고서
        """
        import uuid
        
        # report_id를 전달하지 않으면 자동 생성
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # 완료된 장 제목 목록(진행도 추적용)
        completed_section_titles = []
        
        try:
            # 초기화: 보고서 폴더를 생성하고 초기 상태 저장
            ReportManager._ensure_report_folder(report_id)
            
            # 로그 기록기 초기화(구조화 로그 agent_log.jsonl)
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # 콘솔 로그 기록기 초기화(console_log.txt)
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "보고서 초기화 중...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # 단계 1: 개요 계획
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "보고서 개요 계획을 시작합니다...",
                completed_sections=[]
            )
            
            # 계획 시작 로그 기록
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "보고서 개요 계획을 시작합니다...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # 계획 완료 로그 기록
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # 개요를 파일로 저장
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"개요 계획 완료, 총 {len(outline.sections)}개 장",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"개요가 파일에 저장됨: {report_id}/outline.json")
            
            # 단계 2: 장별 생성(장 단위로 저장)
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # 컨텍스트용 내용 저장
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # 진행도 업데이트
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"장 생성 중: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"장 생성 중: {section.title} ({section_num}/{total_sections})"
                    )
                
                # 메인 장 내용 생성
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # 장 저장
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # 장 완료 로그 기록
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"장이 저장됨: {report_id}/section_{section_num:02d}.md")
                
                # 진행도 업데이트
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"장 {section.title} 완료",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # 단계 3: 전체 보고서 조립
            if progress_callback:
                progress_callback("generating", 95, "전체 보고서를 조립 중...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "전체 보고서를 조립 중...",
                completed_sections=completed_section_titles
            )
            
            # ReportManager를 사용해 전체 보고서 조립
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # 총 소요 시간 계산
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # 보고서 완료 로그 기록
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # 최종 보고서 저장
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "보고서 생성 완료",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "보고서 생성 완료")
            
            logger.info(f"보고서 생성 완료: {report_id}")
            
            # 콘솔 로그 기록기 닫기
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"보고서 생성 실패: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # 오류 로그 기록
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # 실패 상태 저장
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"보고서 생성 실패: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # 저장 실패 오류 무시
            
            # 콘솔 로그 기록기 닫기
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Report Agent와 대화
        
        대화 중 Agent는 검색 도구를 자율적으로 호출해 질문에 답할 수 있습니다
        
        Args:
            message: 사용자 메시지
            chat_history: 대화 기록
            
        Returns:
            {
                "response": "Agent 답변",
                "tool_calls": [호출된 도구 목록],
                "sources": [정보 출처]
            }
        """
        logger.info(f"Report Agent 대화: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # 이미 생성된 보고서 내용 가져오기
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # 보고서 길이 제한, 컨텍스트가 너무 길어지는 것을 방지
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [보고서 내용이 잘렸습니다] ..."
        except Exception as e:
            logger.warning(f"보고서 내용 가져오기 실패: {e}")
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "（현재 보고서 없음）",
            tools_description=self._get_tools_description(),
        )

        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        # 이전 대화 추가
        for h in chat_history[-10:]:  # 기록 길이 제한
            messages.append(h)
        
        # 사용자 메시지 추가
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT 루프(간소화 버전)
        tool_calls_made = []
        max_iterations = 2  # 반복 횟수 줄이기
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # 도구 호출 파싱
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # 도구 호출이 없으면 응답을 바로 반환
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # 도구 호출 실행(수량 제한)
            tool_results = []
            for call in tool_calls[:1]:  # 라운드당 최대 1회 도구 호출 실행
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # 결과 길이 제한
                })
                tool_calls_made.append(call)
            
            # 결과를 메시지에 추가
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']}결과]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # 최대 반복에 도달, 최종 응답 가져오기
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # 응답 정리
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    보고서 관리자
    
    보고서의 영구 저장과 검색을 담당
    
    파일 구조(장별 출력):
    reports/
      {report_id}/
        meta.json          - 보고서 메타 정보와 상태
        outline.json       - 보고서 개요
        progress.json      - 생성 진행률
        section_01.md      - 제1장
        section_02.md      - 제2장
        ...
        full_report.md     - 전체 보고서
    """
    
    # 보고서 저장 디렉터리
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """보고서 루트 디렉터리가 존재하도록 보장"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """보고서 폴더 경로 가져오기"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """보고서 폴더가 존재하도록 보장하고 경로를 반환"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """보고서 메타 정보 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """전체 보고서 Markdown 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """개요 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """진행률 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """장 Markdown 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """Agent 로그 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """콘솔 로그 파일 경로 가져오기"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        콘솔 로그 내용 가져오기
        
        이는 보고서 생성 과정의 콘솔 출력 로그(INFO, WARNING 등)이며,
        agent_log.jsonl의 구조화 로그와는 다릅니다.
        
        Args:
            report_id: 보고서 ID
            from_line: 몇 번째 줄부터 읽기(증분 가져오기에 사용, 0은 처음부터를 의미)
            
        Returns:
            {
                "logs": [로그 줄 목록],
                "total_lines": 전체 줄 수,
                "from_line": 시작 줄 번호,
                "has_more": 더 많은 로그가 있는지 여부
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # 원본 로그 라인은 유지하고, 끝의 개행 문자를 제거
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 끝까지 읽음
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        전체 콘솔 로그 가져오기(한 번에 모두 가져오기)
        
        Args:
            report_id: 보고서 ID
            
        Returns:
            로그 라인 리스트
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Agent 로그 내용 가져오기
        
        Args:
            report_id: 보고서 ID
            from_line: 몇 번째 줄부터 읽기 시작할지(증분 조회용, 0은 처음부터)
            
        Returns:
            {
                "logs": [로그 항목 리스트],
                "total_lines": 전체 줄 수,
                "from_line": 시작 줄 번호,
                "has_more": 더 많은 로그가 있는지 여부
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # 파싱에 실패한 라인은 건너뜀
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 끝까지 읽음
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        전체 Agent 로그 가져오기(한 번에 모두 가져오기용)
        
        Args:
            report_id: 보고서 ID
            
        Returns:
            로그 항목 리스트
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        보고서 개요 저장
        
        계획 단계가 완료된 직후 즉시 호출
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"개요가 저장됨: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        단일 장(섹션) 저장

        각 장(섹션) 생성이 끝난 직후 즉시 호출하여, 장(섹션) 단위 출력 구현

        Args:
            report_id: 보고서 ID
            section_index: 장(섹션) 인덱스(1부터 시작)
            section: 장(섹션) 객체

        Returns:
            저장된 파일 경로
        """
        cls._ensure_report_folder(report_id)

        # 섹션 Markdown 내용 구성 - 존재할 수 있는 중복 제목 정리
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # 파일 저장
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"장(섹션)이 저장됨: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        장(섹션) 내용 정리
        
        1. 내용 시작 부분에서 섹션 제목과 중복되는 Markdown 제목 줄 제거
        2. 모든 ### 및 그 이하 레벨의 제목을 굵은 텍스트로 변환
        
        Args:
            content: 원본 내용
            section_title: 섹션 제목
            
        Returns:
            정리된 내용
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Markdown 제목 줄인지 확인
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # 섹션 제목과 중복되는 제목인지 확인(앞 5줄 내 중복은 건너뜀)
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # 모든 레벨의 제목(#, ##, ###, #### 등)을 굵은 글씨로 변환
                # 섹션 제목은 시스템이 추가하므로, 내용에는 어떤 제목도 있으면 안 됨
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # 빈 줄 추가
                continue
            
            # 이전 줄이 건너뛴 제목이고 현재 줄이 비어 있으면, 이것도 건너뜀
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # 시작 부분의 빈 줄 제거
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # 시작 부분의 구분선 제거
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # 동시에 구분선 뒤의 빈 줄 제거
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls,
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        보고서 생성 진행 상황 업데이트
        
        프론트엔드는 progress.json을 읽어 실시간 진행 상황을 가져올 수 있습니다
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """보고서 생성 진행 상황 가져오기"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        생성된 섹션 목록 가져오기
        
        저장된 모든 섹션 파일 정보 반환
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 파일명에서 섹션 인덱스 파싱
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        전체 보고서 조립
        
        저장된 섹션 파일에서 전체 보고서를 조립하고, 제목을 정리합니다
        """
        folder = cls._get_report_folder(report_id)
        
        # 보고서 헤더 구성
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # 순서대로 모든 섹션 파일 읽기
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # 후처리: 전체 보고서의 제목 문제 정리
        md_content = cls._post_process_report(md_content, outline)
        
        # 전체 보고서 저장
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"전체 보고서가 조립되었습니다: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        보고서 내용 후처리
        
        1. 중복된 제목 제거
        2. 보고서 메인 제목(#)과 섹션 제목(##)은 유지하고, 다른 레벨의 제목(###, #### 등)은 제거
        3. 불필요한 빈 줄과 구분선 정리
        
        Args:
            content: 원본 보고서 내용
            outline: 보고서 개요
            
        Returns:
            처리된 내용
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # 개요에 있는 모든 섹션 제목 수집
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 제목 행인지 확인
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 중복 제목인지 확인 (연속 5줄 이내에 동일한 내용의 제목이 나타나는 경우)
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # 중복 제목과 그 뒤의 빈 줄 건너뛰기
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # 제목 레벨 처리:
                # - # (level=1) 보고서 메인 제목만 유지
                # - ## (level=2) 섹션 제목 유지
                # - ### 이하 (level>=3) 굵은 텍스트로 변환
                
                if level == 1:
                    if title == outline.title:
                        # 보고서 메인 제목 유지
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # 섹션 제목이 #를 잘못 사용했으므로 ##로 수정
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # 다른 1레벨 제목은 굵은 텍스트로 변환
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # 섹션 제목 유지
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # 섹션이 아닌 2레벨 제목은 굵은 텍스트로 변환
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### 이하 레벨의 제목은 굵은 텍스트로 변환
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # 제목 바로 뒤에 붙은 구분선 건너뛰기
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # 제목 뒤에는 빈 줄 하나만 유지
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # 연속된 여러 빈 줄 정리 (최대 2개만 유지)
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """보고서 메타정보와 전체 보고서를 저장"""
        cls._ensure_report_folder(report.report_id)
        
        # 메타정보 JSON 저장
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 개요 저장
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # 전체 Markdown 보고서 저장
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"보고서가 저장됨: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """보고서 가져오기"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # 구형 형식 호환: reports 디렉터리 아래에 직접 저장된 파일 확인
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Report 객체 재구성
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # markdown_content가 비어 있으면 full_report.md에서 읽기를 시도
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """시뮬레이션 ID로 보고서 가져오기"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 새 형식: 폴더
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # 구형 형식 호환: JSON 파일
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """보고서 목록"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 새 형식: 폴더
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # 구형 형식 호환: JSON 파일
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # 생성 시간 내림차순
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """보고서 삭제(전체 폴더)"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # 새 형식: 전체 폴더 삭제
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"보고서 폴더가 삭제됨: {report_id}")
            return True
        
        # 구형 형식 호환: 개별 파일 삭제
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
