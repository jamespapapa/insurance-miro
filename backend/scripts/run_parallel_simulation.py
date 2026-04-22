"""
OASIS 2개 플랫폼 병렬 시뮬레이션 프리셋 스크립트
Twitter와 Reddit 시뮬레이션을 동시에 실행하며, 동일한 설정 파일을 읽습니다

기능 특성:
- 2개 플랫폼(Twitter + Reddit) 병렬 시뮬레이션
- 시뮬레이션 완료 후 즉시 환경을 종료하지 않고, 명령 대기 모드로 진입
- IPC를 통해 Interview 명령 수신 지원
- 단일 Agent 인터뷰 및 배치 인터뷰 지원
- 원격 환경 종료 명령 지원

사용 방법:
    python run_parallel_simulation.py --config simulation_config.json
    python run_parallel_simulation.py --config simulation_config.json --no-wait  # 완료 후 즉시 종료
    python run_parallel_simulation.py --config simulation_config.json --twitter-only
    python run_parallel_simulation.py --config simulation_config.json --reddit-only

로그 구조:
    sim_xxx/
    ├── twitter/
    │   └── actions.jsonl    # Twitter 플랫폼 동작 로그
    ├── reddit/
    │   └── actions.jsonl    # Reddit 플랫폼 동작 로그
    ├── simulation.log       # 메인 시뮬레이션 프로세스 로그
    └── run_state.json       # 실행 상태(API 조회용)
"""

# ============================================================
# Windows 인코딩 문제 해결: 모든 import 이전에 UTF-8 인코딩 설정
# 이는 OASIS 서드파티 라이브러리가 파일을 읽을 때 인코딩을 지정하지 않는 문제를 수정하기 위함
# ============================================================
import sys
import os

if sys.platform == 'win32':
    # Python 기본 I/O 인코딩을 UTF-8로 설정
    # 이는 인코딩이 지정되지 않은 모든 open() 호출에 영향을 줍니다
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    
    # 표준 출력 스트림을 UTF-8로 재구성(콘솔에서 중국어 깨짐 해결)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    # 기본 인코딩을 강제로 설정(open() 함수의 기본 인코딩에 영향)
    # 주의: 이는 Python 시작 시 설정해야 하며, 런타임에 설정하면 적용되지 않을 수 있음
    # 그래서 내장 open 함수를 monkey-patch 해야 함
    import builtins
    _original_open = builtins.open
    
    def _utf8_open(file, mode='r', buffering=-1, encoding=None, errors=None, 
                   newline=None, closefd=True, opener=None):
        """
        open() 함수를 래핑하여, 텍스트 모드에서 기본으로 UTF-8 인코딩을 사용
        이는 서드파티 라이브러리(예: OASIS)가 파일을 읽을 때 인코딩을 지정하지 않는 문제를 수정할 수 있음
        """
        # 텍스트 모드(바이너리 아님)이며 인코딩이 지정되지 않은 경우에만 기본 인코딩 설정
        if encoding is None and 'b' not in mode:
            encoding = 'utf-8'
        return _original_open(file, mode, buffering, encoding, errors, 
                              newline, closefd, opener)
    
    builtins.open = _utf8_open

import argparse
import asyncio
import json
import logging
import multiprocessing
import random
import signal
import sqlite3
import warnings
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


# 전역 변수: 시그널 처리용
_shutdown_event = None
_cleanup_done = False

# backend 디렉터리를 경로에 추가
# 스크립트는 고정적으로 backend/scripts/ 디렉터리에 위치
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

# 프로젝트 루트 디렉터리의 .env 파일 로드(LLM_API_KEY 등 설정 포함)
from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
    print(f"환경 설정을 로드했습니다: {_env_file}")
else:
    # backend/.env 로드를 시도
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)
        print(f"환경 설정을 로드했습니다: {_backend_env}")

from llm_runtime import resolve_llm_runtime

class MaxTokensWarningFilter(logging.Filter):
    """camel-ai의 max_tokens 경고를 필터링(우리는 의도적으로 max_tokens를 설정하지 않고 모델이 스스로 결정하게 함)"""
    
    def filter(self, record):
        # max_tokens 경고를 포함한 로그 필터링
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


# 모듈 로드 시 즉시 필터 추가, camel 코드 실행 전 적용 보장
logging.getLogger().addFilter(MaxTokensWarningFilter())


def disable_oasis_logging():
    """
    OASIS 라이브러리의 상세 로그 출력을 비활성화
    OASIS 로그는 너무 장황함(각 agent의 관찰과 동작을 기록) → 우리는 자체 action_logger를 사용
    """
    # OASIS의 모든 로거 비활성화
    oasis_loggers = [
        "social.agent",
        "social.twitter", 
        "social.rec",
        "oasis.env",
        "table",
    ]
    
    for logger_name in oasis_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)  # 치명적 오류만 기록
        logger.handlers.clear()
        logger.propagate = False


def init_logging_for_simulation(simulation_dir: str):
    """
    시뮬레이션 로그 설정 초기화
    
    Args:
        simulation_dir: 시뮬레이션 디렉터리 경로
    """
    # OASIS 상세 로그 비활성화
    disable_oasis_logging()
    
    # 이전 log 디렉터리 정리(존재하는 경우)
    old_log_dir = os.path.join(simulation_dir, "log")
    if os.path.exists(old_log_dir):
        import shutil
        shutil.rmtree(old_log_dir, ignore_errors=True)


from action_logger import SimulationLogManager, PlatformActionLogger

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import (
        ActionType,
        LLMAction,
        ManualAction,
        generate_twitter_agent_graph,
        generate_reddit_agent_graph
    )
except ImportError as e:
    print(f"오류: 의존성이 누락되었습니다 {e}")
    print("먼저 설치하세요: pip install oasis-ai camel-ai")
    sys.exit(1)


# Twitter 사용 가능 동작(INTERVIEW 제외, INTERVIEW는 ManualAction으로만 수동 트리거 가능)
TWITTER_ACTIONS = [
    ActionType.CREATE_POST,
    ActionType.LIKE_POST,
    ActionType.REPOST,
    ActionType.FOLLOW,
    ActionType.DO_NOTHING,
    ActionType.QUOTE_POST,
]

# Reddit 사용 가능 동작(INTERVIEW 제외, INTERVIEW는 ManualAction으로만 수동 트리거 가능)
REDDIT_ACTIONS = [
    ActionType.LIKE_POST,
    ActionType.DISLIKE_POST,
    ActionType.CREATE_POST,
    ActionType.CREATE_COMMENT,
    ActionType.LIKE_COMMENT,
    ActionType.DISLIKE_COMMENT,
    ActionType.SEARCH_POSTS,
    ActionType.SEARCH_USER,
    ActionType.TREND,
    ActionType.REFRESH,
    ActionType.DO_NOTHING,
    ActionType.FOLLOW,
    ActionType.MUTE,
]


# IPC 관련 상수
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"

class CommandType:
    """명령 타입 상수"""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


class ParallelIPCHandler:
    """
    2개 플랫폼 IPC 명령 처리기

    두 플랫폼의 환경을 관리하고 Interview 명령을 처리
    """
    
    def __init__(
        self,
        simulation_dir: str,
        twitter_env=None,
        twitter_agent_graph=None,
        reddit_env=None,
        reddit_agent_graph=None
    ):
        self.simulation_dir = simulation_dir
        self.twitter_env = twitter_env
        self.twitter_agent_graph = twitter_agent_graph
        self.reddit_env = reddit_env
        self.reddit_agent_graph = reddit_agent_graph
        
        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)
        
        # 디렉터리가 존재하도록 보장
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def update_status(self, status: str):
        """환경 상태 업데이트"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "twitter_available": self.twitter_env is not None,
                "reddit_available": self.reddit_env is not None,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def poll_command(self) -> Optional[Dict[str, Any]]:
        """폴링하여 처리 대기 중인 명령을 가져오기"""
        if not os.path.exists(self.commands_dir):
            return None
        
        # 명령 파일 가져오기(시간순 정렬)
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                command_files.append((filepath, os.path.getmtime(filepath)))
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return None
    
    def send_response(self, command_id: str, status: str, result: Dict = None, error: str = None):
        """응답 전송"""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        
        # 명령 파일 삭제
        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        try:
            os.remove(command_file)
        except OSError:
            pass
    
    def _get_env_and_graph(self, platform: str):
        """
        지정된 플랫폼의 환경과 agent_graph 가져오기
        
        Args:
            platform: 플랫폼 이름 ("twitter" 또는 "reddit")
            
        Returns:
            (env, agent_graph, platform_name) 또는 (None, None, None)
        """
        if platform == "twitter" and self.twitter_env:
            return self.twitter_env, self.twitter_agent_graph, "twitter"
        elif platform == "reddit" and self.reddit_env:
            return self.reddit_env, self.reddit_agent_graph, "reddit"
        else:
            return None, None, None
    
    async def _interview_single_platform(self, agent_id: int, prompt: str, platform: str) -> Dict[str, Any]:
        """
        단일 플랫폼에서 Interview 실행
        
        Returns:
            결과를 포함한 딕셔너리, 또는 error를 포함한 딕셔너리
        """
        env, agent_graph, actual_platform = self._get_env_and_graph(platform)
        
        if not env or not agent_graph:
            return {"platform": platform, "error": f"{platform}플랫폼을 사용할 수 없습니다"}
        
        try:
            agent = agent_graph.get_agent(agent_id)
            interview_action = ManualAction(
                action_type=ActionType.INTERVIEW,
                action_args={"prompt": prompt}
            )
            actions = {agent: interview_action}
            await env.step(actions)
            
            result = self._get_interview_result(agent_id, actual_platform)
            result["platform"] = actual_platform
            return result
            
        except Exception as e:
            return {"platform": platform, "error": str(e)}
    
    async def handle_interview(self, command_id: str, agent_id: int, prompt: str, platform: str = None) -> bool:
        """
        단일 Agent 인터뷰 명령 처리
        
        Args:
            command_id: 명령 ID
            agent_id: Agent ID
            prompt: 인터뷰 질문
            platform: 지정 플랫폼(선택)
                - "twitter": Twitter 플랫폼만 인터뷰
                - "reddit": Reddit 플랫폼만 인터뷰
                - None/미지정: 두 플랫폼을 동시에 인터뷰하고 통합 결과 반환
            
        Returns:
            True는 성공, False는 실패
        """
        # 플랫폼이 지정된 경우 해당 플랫폼만 인터뷰
        if platform in ("twitter", "reddit"):
            result = await self._interview_single_platform(agent_id, prompt, platform)
            
            if "error" in result:
                self.send_response(command_id, "failed", error=result["error"])
                print(f"  Interview실패: agent_id={agent_id}, platform={platform}, error={result['error']}")
                return False
            else:
                self.send_response(command_id, "completed", result=result)
                print(f"  Interview완료: agent_id={agent_id}, platform={platform}")
                return True
        
        # 플랫폼 미지정: 두 플랫폼을 동시에 인터뷰
        if not self.twitter_env and not self.reddit_env:
            self.send_response(command_id, "failed", error="사용 가능한 시뮬레이션 환경이 없습니다")
            return False
        
        results = {
            "agent_id": agent_id,
            "prompt": prompt,
            "platforms": {}
        }
        success_count = 0
        
        # 두 플랫폼 병렬 인터뷰
        tasks = []
        platforms_to_interview = []
        
        if self.twitter_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "twitter"))
            platforms_to_interview.append("twitter")
        
        if self.reddit_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "reddit"))
            platforms_to_interview.append("reddit")
        
        # 병렬 실행
        platform_results = await asyncio.gather(*tasks)
        
        for platform_name, platform_result in zip(platforms_to_interview, platform_results):
            results["platforms"][platform_name] = platform_result
            if "error" not in platform_result:
                success_count += 1
        
        if success_count > 0:
            self.send_response(command_id, "completed", result=results)
            print(f"  Interview완료: agent_id={agent_id}, 성공 플랫폼 수={success_count}/{len(platforms_to_interview)}")
            return True
        else:
            errors = [f"{p}: {r.get('error', '알 수 없는 오류')}" for p, r in results["platforms"].items()]
            self.send_response(command_id, "failed", error="; ".join(errors))
            print(f"  Interview실패: agent_id={agent_id}, 모든 플랫폼이 실패")
            return False
    
    async def handle_batch_interview(self, command_id: str, interviews: List[Dict], platform: str = None) -> bool:
        """
        배치 인터뷰 명령 처리
        
        Args:
            command_id: 명령 ID
            interviews: [{"agent_id": int, "prompt": str, "platform": str(optional)}, ...]
            platform: 기본 플랫폼(각 interview 항목이 덮어쓸 수 있음)
                - "twitter": Twitter 플랫폼만 인터뷰
                - "reddit": Reddit 플랫폼만 인터뷰
                - None/미지정: 각 Agent가 두 플랫폼을 동시에 인터뷰
        """
        # 플랫폼별로 그룹화
        twitter_interviews = []
        reddit_interviews = []
        both_platforms_interviews = []  # 두 플랫폼을 동시에 인터뷰해야 함
        
        for interview in interviews:
            item_platform = interview.get("platform", platform)
            if item_platform == "twitter":
                twitter_interviews.append(interview)
            elif item_platform == "reddit":
                reddit_interviews.append(interview)
            else:
                # 플랫폼 미지정: 두 플랫폼 모두 인터뷰
                both_platforms_interviews.append(interview)
        
        # both_platforms_interviews 를 두 플랫폼으로 분리
        if both_platforms_interviews:
            if self.twitter_env:
                twitter_interviews.extend(both_platforms_interviews)
            if self.reddit_env:
                reddit_interviews.extend(both_platforms_interviews)
        
        results = {}
        
        # Twitter 플랫폼 인터뷰 처리
        if twitter_interviews and self.twitter_env:
            try:
                twitter_actions = {}
                for interview in twitter_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.twitter_agent_graph.get_agent(agent_id)
                        twitter_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  경고: Twitter Agent {agent_id}를 가져올 수 없음: {e}")
                
                if twitter_actions:
                    await self.twitter_env.step(twitter_actions)
                    
                    for interview in twitter_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "twitter")
                        result["platform"] = "twitter"
                        results[f"twitter_{agent_id}"] = result
            except Exception as e:
                print(f"  Twitter 배치 Interview 실패: {e}")
        
        # Reddit 플랫폼 인터뷰 처리
        if reddit_interviews and self.reddit_env:
            try:
                reddit_actions = {}
                for interview in reddit_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.reddit_agent_graph.get_agent(agent_id)
                        reddit_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  경고: Reddit Agent {agent_id}를 가져올 수 없음: {e}")
                
                if reddit_actions:
                    await self.reddit_env.step(reddit_actions)
                    
                    for interview in reddit_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "reddit")
                        result["platform"] = "reddit"
                        results[f"reddit_{agent_id}"] = result
            except Exception as e:
                print(f"  Reddit 배치 Interview 실패: {e}")
        
        if results:
            self.send_response(command_id, "completed", result={
                "interviews_count": len(results),
                "results": results
            })
            print(f"  배치 Interview 완료: {len(results)} 명의 Agent")
            return True
        else:
            self.send_response(command_id, "failed", error="성공한 인터뷰가 없음")
            return False
    
    def _get_interview_result(self, agent_id: int, platform: str) -> Dict[str, Any]:
        """데이터베이스에서 최신 Interview 결과 가져오기"""
        db_path = os.path.join(self.simulation_dir, f"{platform}_simulation.db")
        
        result = {
            "agent_id": agent_id,
            "response": None,
            "timestamp": None
        }
        
        if not os.path.exists(db_path):
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 최신 Interview 기록 조회
            cursor.execute("""
                SELECT user_id, info, created_at
                FROM trace
                WHERE action = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ActionType.INTERVIEW.value, agent_id))
            
            row = cursor.fetchone()
            if row:
                user_id, info_json, created_at = row
                try:
                    info = json.loads(info_json) if info_json else {}
                    result["response"] = info.get("response", info)
                    result["timestamp"] = created_at
                except json.JSONDecodeError:
                    result["response"] = info_json
            
            conn.close()
            
        except Exception as e:
            print(f"  Interview 결과 읽기 실패: {e}")
        
        return result
    
    async def process_commands(self) -> bool:
        """
        처리 대기 중인 모든 명령 처리
        
        Returns:
            True 는 계속 실행, False 는 종료해야 함
        """
        command = self.poll_command()
        if not command:
            return True
        
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})
        
        print(f"\nIPC 명령 수신: {command_type}, id={command_id}")
        
        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", ""),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", []),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.CLOSE_ENV:
            print("환경 종료 명령 수신")
            self.send_response(command_id, "completed", result={"message": "환경이 곧 종료됩니다"})
            return False
        
        else:
            self.send_response(command_id, "failed", error=f"알 수 없는 명령 타입: {command_type}")
            return True


def load_config(config_path: str) -> Dict[str, Any]:
    """설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 필터링해야 하는 비핵심 동작 타입(이 동작들은 분석 가치가 낮음)
FILTERED_ACTIONS = {'refresh', 'sign_up'}

# 동작 타입 매핑 표(데이터베이스의 이름 -> 표준 이름)
ACTION_TYPE_MAP = {
    'create_post': 'CREATE_POST',
    'like_post': 'LIKE_POST',
    'dislike_post': 'DISLIKE_POST',
    'repost': 'REPOST',
    'quote_post': 'QUOTE_POST',
    'follow': 'FOLLOW',
    'mute': 'MUTE',
    'create_comment': 'CREATE_COMMENT',
    'like_comment': 'LIKE_COMMENT',
    'dislike_comment': 'DISLIKE_COMMENT',
    'search_posts': 'SEARCH_POSTS',
    'search_user': 'SEARCH_USER',
    'trend': 'TREND',
    'do_nothing': 'DO_NOTHING',
    'interview': 'INTERVIEW',
}


def get_agent_names_from_config(config: Dict[str, Any]) -> Dict[int, str]:
    """
    simulation_config 에서 agent_id -> entity_name 매핑 가져오기
    
    이렇게 하면 actions.jsonl 에서 "Agent_0" 같은 코드명이 아니라 실제 엔티티 이름을 표시할 수 있음
    
    Args:
        config: simulation_config.json 의 내용
        
    Returns:
        agent_id -> entity_name 매핑 딕셔너리
    """
    agent_names = {}
    agent_configs = config.get("agent_configs", [])
    
    for agent_config in agent_configs:
        agent_id = agent_config.get("agent_id")
        entity_name = agent_config.get("entity_name", f"Agent_{agent_id}")
        if agent_id is not None:
            agent_names[agent_id] = entity_name
    
    return agent_names


def fetch_new_actions_from_db(
    db_path: str,
    last_rowid: int,
    agent_names: Dict[int, str]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    DB에서 새로운 액션 기록을 가져오고, 완전한 컨텍스트 정보를 보완합니다
    
    Args:
        db_path: DB 파일 경로
        last_rowid: 지난번에 읽은 최대 rowid 값 (created_at 대신 rowid 사용: 플랫폼마다 created_at 형식이 다름)
        agent_names: agent_id -> agent_name 매핑
        
    Returns:
        (actions_list, new_last_rowid)
        - actions_list: 액션 목록. 각 요소는 agent_id, agent_name, action_type, action_args(컨텍스트 정보 포함)를 포함
        - new_last_rowid: 새로운 최대 rowid 값
    """
    actions = []
    new_last_rowid = last_rowid
    
    if not os.path.exists(db_path):
        return actions, new_last_rowid
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # rowid로 처리 완료된 기록을 추적합니다 (rowid는 SQLite 내장 자동증가 필드)
        # 이렇게 하면 created_at 형식 차이 문제를 피할 수 있습니다 (Twitter는 정수, Reddit은 날짜시간 문자열)
        cursor.execute("""
            SELECT rowid, user_id, action, info
            FROM trace
            WHERE rowid > ?
            ORDER BY rowid ASC
        """, (last_rowid,))
        
        for rowid, user_id, action, info_json in cursor.fetchall():
            # 최대 rowid 갱신
            new_last_rowid = rowid
            
            # 핵심이 아닌 액션 필터링
            if action in FILTERED_ACTIONS:
                continue
            
            # 액션 파라미터 파싱
            try:
                action_args = json.loads(info_json) if info_json else {}
            except json.JSONDecodeError:
                action_args = {}
            
            # action_args를 간소화: 핵심 필드만 유지 (전체 내용 유지, 잘라내지 않음)
            simplified_args = {}
            if 'content' in action_args:
                simplified_args['content'] = action_args['content']
            if 'post_id' in action_args:
                simplified_args['post_id'] = action_args['post_id']
            if 'comment_id' in action_args:
                simplified_args['comment_id'] = action_args['comment_id']
            if 'quoted_id' in action_args:
                simplified_args['quoted_id'] = action_args['quoted_id']
            if 'new_post_id' in action_args:
                simplified_args['new_post_id'] = action_args['new_post_id']
            if 'follow_id' in action_args:
                simplified_args['follow_id'] = action_args['follow_id']
            if 'query' in action_args:
                simplified_args['query'] = action_args['query']
            if 'like_id' in action_args:
                simplified_args['like_id'] = action_args['like_id']
            if 'dislike_id' in action_args:
                simplified_args['dislike_id'] = action_args['dislike_id']
            
            # 액션 타입 이름 변환
            action_type = ACTION_TYPE_MAP.get(action, action.upper())
            
            # 컨텍스트 정보 보완 (게시물 내용, 사용자명 등)
            _enrich_action_context(cursor, action_type, simplified_args, agent_names)
            
            actions.append({
                'agent_id': user_id,
                'agent_name': agent_names.get(user_id, f'Agent_{user_id}'),
                'action_type': action_type,
                'action_args': simplified_args,
            })
        
        conn.close()
    except Exception as e:
        print(f"DB 액션 읽기 실패: {e}")
    
    return actions, new_last_rowid


def _enrich_action_context(
    cursor,
    action_type: str,
    action_args: Dict[str, Any],
    agent_names: Dict[int, str]
) -> None:
    """
    액션에 컨텍스트 정보를 보완합니다 (게시물 내용, 사용자명 등)
    
    Args:
        cursor: DB 커서
        action_type: 액션 타입
        action_args: 액션 파라미터 (수정됨)
        agent_names: agent_id -> agent_name 매핑
    """
    try:
        # 게시물 좋아요/싫어요: 게시물 내용과 작성자 보완
        if action_type in ('LIKE_POST', 'DISLIKE_POST'):
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
        
        # 게시물 리포스트: 원문 내용과 작성자 보완
        elif action_type == 'REPOST':
            new_post_id = action_args.get('new_post_id')
            if new_post_id:
                # 리포스트 게시물의 original_post_id는 원문을 가리킵니다
                cursor.execute("""
                    SELECT original_post_id FROM post WHERE post_id = ?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    original_post_id = row[0]
                    original_info = _get_post_info(cursor, original_post_id, agent_names)
                    if original_info:
                        action_args['original_content'] = original_info.get('content', '')
                        action_args['original_author_name'] = original_info.get('author_name', '')
        
        # 게시물 인용: 원문 내용/작성자 및 인용 댓글 보완
        elif action_type == 'QUOTE_POST':
            quoted_id = action_args.get('quoted_id')
            new_post_id = action_args.get('new_post_id')
            
            if quoted_id:
                original_info = _get_post_info(cursor, quoted_id, agent_names)
                if original_info:
                    action_args['original_content'] = original_info.get('content', '')
                    action_args['original_author_name'] = original_info.get('author_name', '')
            
            # 인용 게시물의 댓글 내용(quote_content) 가져오기
            if new_post_id:
                cursor.execute("""
                    SELECT quote_content FROM post WHERE post_id = ?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    action_args['quote_content'] = row[0]
        
        # 사용자 팔로우: 팔로우된 사용자의 이름 보완
        elif action_type == 'FOLLOW':
            follow_id = action_args.get('follow_id')
            if follow_id:
                # follow 테이블에서 followee_id 가져오기
                cursor.execute("""
                    SELECT followee_id FROM follow WHERE follow_id = ?
                """, (follow_id,))
                row = cursor.fetchone()
                if row:
                    followee_id = row[0]
                    target_name = _get_user_name(cursor, followee_id, agent_names)
                    if target_name:
                        action_args['target_user_name'] = target_name
        
        # 사용자 뮤트: 뮤트된 사용자의 이름 보완
        elif action_type == 'MUTE':
            # action_args에서 user_id 또는 target_id 가져오기
            target_id = action_args.get('user_id') or action_args.get('target_id')
            if target_id:
                target_name = _get_user_name(cursor, target_id, agent_names)
                if target_name:
                    action_args['target_user_name'] = target_name
        
        # 댓글 좋아요/싫어요: 댓글 내용과 작성자 보완
        elif action_type in ('LIKE_COMMENT', 'DISLIKE_COMMENT'):
            comment_id = action_args.get('comment_id')
            if comment_id:
                comment_info = _get_comment_info(cursor, comment_id, agent_names)
                if comment_info:
                    action_args['comment_content'] = comment_info.get('content', '')
                    action_args['comment_author_name'] = comment_info.get('author_name', '')
        
        # 댓글 작성: 댓글을 단 게시물 정보 보완
        elif action_type == 'CREATE_COMMENT':
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
    
    except Exception as e:
        # 컨텍스트 보완 실패는 메인 흐름에 영향 없음
        print(f"액션 컨텍스트 보완 실패: {e}")


def _get_post_info(
    cursor,
    post_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    게시물 정보 가져오기
    
    Args:
        cursor: DB 커서
        post_id: 게시물 ID
        agent_names: agent_id -> agent_name 매핑
        
    Returns:
        content와 author_name을 포함한 dict 또는 None
    """
    try:
        cursor.execute("""
            SELECT p.content, p.user_id, u.agent_id
            FROM post p
            LEFT JOIN user u ON p.user_id = u.user_id
            WHERE p.post_id = ?
        """, (post_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # agent_names의 이름을 우선 사용
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # user 테이블에서 이름 가져오기
                cursor.execute("SELECT name, user_name FROM user WHERE user_id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''
            
            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def _get_user_name(
    cursor,
    user_id: int,
    agent_names: Dict[int, str]
) -> Optional[str]:
    """
    사용자 이름 가져오기
    
    Args:
        cursor: 데이터베이스 커서
        user_id: 사용자 ID
        agent_names: agent_id -> agent_name 매핑
        
    Returns:
        사용자 이름 또는 None
    """
    try:
        cursor.execute("""
            SELECT agent_id, name, user_name FROM user WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            agent_id = row[0]
            name = row[1]
            user_name = row[2]
            
            # agent_names의 이름을 우선 사용
            if agent_id is not None and agent_id in agent_names:
                return agent_names[agent_id]
            return name or user_name or ''
    except Exception:
        pass
    return None


def _get_comment_info(
    cursor,
    comment_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    댓글 정보 가져오기
    
    Args:
        cursor: 데이터베이스 커서
        comment_id: 댓글 ID
        agent_names: agent_id -> agent_name 매핑
        
    Returns:
        content와 author_name을 포함하는 딕셔너리 또는 None
    """
    try:
        cursor.execute("""
            SELECT c.content, c.user_id, u.agent_id
            FROM comment c
            LEFT JOIN user u ON c.user_id = u.user_id
            WHERE c.comment_id = ?
        """, (comment_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # agent_names의 이름을 우선 사용
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # user 테이블에서 이름 가져오기
                cursor.execute("SELECT name, user_name FROM user WHERE user_id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''
            
            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def create_model(config: Dict[str, Any], use_boost: bool = False):
    """
    LLM 모델 생성
    """
    runtime = resolve_llm_runtime(config, use_boost=use_boost, logger=print)
    display_url = runtime.base_url[:40] if runtime.base_url else "기본값"
    print(
        f"{runtime.label} model={runtime.model_name}, base_url={display_url}..., "
        f"timeout={runtime.timeout:.0f}s, retries={runtime.max_retries}, "
        f"semaphore={runtime.semaphore}"
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=runtime.model_name,
        api_key=runtime.api_key,
        url=runtime.base_url or None,
        timeout=runtime.timeout,
        max_retries=runtime.max_retries,
    )
    return model, runtime


def get_active_agents_for_round(
    env,
    config: Dict[str, Any],
    current_hour: int,
    round_num: int
) -> List:
    """시간과 구성에 따라 이번 라운드에서 어떤 Agent를 활성화할지 결정"""
    time_config = config.get("time_config", {})
    agent_configs = config.get("agent_configs", [])
    
    base_min = time_config.get("agents_per_hour_min", 5)
    base_max = time_config.get("agents_per_hour_max", 20)
    
    peak_hours = time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22])
    off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])
    
    if current_hour in peak_hours:
        multiplier = time_config.get("peak_activity_multiplier", 1.5)
    elif current_hour in off_peak_hours:
        multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
    else:
        multiplier = 1.0
    
    target_count = int(random.uniform(base_min, base_max) * multiplier)
    
    candidates = []
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)
        active_hours = cfg.get("active_hours", list(range(8, 23)))
        activity_level = cfg.get("activity_level", 0.5)
        
        if current_hour not in active_hours:
            continue
        
        if random.random() < activity_level:
            candidates.append(agent_id)
    
    selected_ids = random.sample(
        candidates, 
        min(target_count, len(candidates))
    ) if candidates else []
    
    active_agents = []
    for agent_id in selected_ids:
        try:
            agent = env.agent_graph.get_agent(agent_id)
            active_agents.append((agent_id, agent))
        except Exception:
            pass
    
    return active_agents


class PlatformSimulation:
    """플랫폼 시뮬레이션 결과 컨테이너"""
    def __init__(self):
        self.env = None
        self.agent_graph = None
        self.total_actions = 0


async def run_twitter_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Twitter 시뮬레이션 실행
    
    Args:
        config: 시뮬레이션 구성
        simulation_dir: 시뮬레이션 디렉터리
        action_logger: 액션 로그 기록기
        main_logger: 메인 로그 관리자
        max_rounds: 최대 시뮬레이션 라운드 수(선택, 너무 긴 시뮬레이션을 잘라내는 용도)
        
    Returns:
        PlatformSimulation: env와 agent_graph를 포함한 결과 객체
    """
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Twitter] {msg}")
        print(f"[Twitter] {msg}")
    
    log_info("초기화...")
    
    # Twitter는 범용 LLM 구성을 사용
    model, llm_runtime = create_model(config, use_boost=False)
    
    # OASIS Twitter는 CSV 형식을 사용
    profile_path = os.path.join(simulation_dir, "twitter_profiles.csv")
    if not os.path.exists(profile_path):
        log_info(f"오류: Profile 파일이 존재하지 않음: {profile_path}")
        return result
    
    result.agent_graph = await generate_twitter_agent_graph(
        profile_path=profile_path,
        model=model,
        available_actions=TWITTER_ACTIONS,
    )
    
    # 구성 파일에서 Agent 실제 이름 매핑을 가져옴(entity_name 사용, 기본 Agent_X가 아님)
    agent_names = get_agent_names_from_config(config)
    # 구성에 특정 agent가 없으면 OASIS의 기본 이름을 사용
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')
    
    db_path = os.path.join(simulation_dir, "twitter_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
        semaphore=llm_runtime.semaphore,
    )
    
    await result.env.reset()
    log_info("환경이 시작됨")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # 데이터베이스에서 마지막으로 처리한 행 번호를 추적(rowid 사용으로 created_at 형식 차이 회피)
    
    # 초기 이벤트 실행
    event_config = config.get("event_config", {})
    initial_posts = event_config.get("initial_posts", [])
    
    # round 0 시작 기록(초기 이벤트 단계)
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0
    
    initial_action_count = 0
    if initial_posts:
        initial_actions = {}
        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            try:
                agent = result.env.agent_graph.get_agent(agent_id)
                initial_actions[agent] = ManualAction(
                    action_type=ActionType.CREATE_POST,
                    action_args={"content": content}
                )
                
                if action_logger:
                    action_logger.log_action(
                        round_num=0,
                        agent_id=agent_id,
                        agent_name=agent_names.get(agent_id, f"Agent_{agent_id}"),
                        action_type="CREATE_POST",
                        action_args={"content": content}
                    )
                    total_actions += 1
                    initial_action_count += 1
            except Exception:
                pass
        
        if initial_actions:
            await result.env.step(initial_actions)
            log_info(f"초기 게시물 {len(initial_actions)}개 게시됨")
    
    # round 0 종료 기록
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # 메인 시뮬레이션 루프
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 72)
    minutes_per_round = time_config.get("minutes_per_round", 30)
    total_rounds = (total_hours * 60) // minutes_per_round
    
    # 최대 라운드 수가 지정되면 잘라냄
    if max_rounds is not None and max_rounds > 0:
        original_rounds = total_rounds
        total_rounds = min(total_rounds, max_rounds)
        if total_rounds < original_rounds:
            log_info(f"라운드 수가 잘림: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
    
    start_time = datetime.now()
    
    for round_num in range(total_rounds):
        # 종료 신호 수신 여부 확인
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"종료 신호를 수신하여 {round_num + 1}번째 라운드에서 시뮬레이션을 중지")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = (simulated_minutes // 60) % 24
        simulated_day = simulated_minutes // (60 * 24) + 1
        
        active_agents = get_active_agents_for_round(
            result.env, config, simulated_hour, round_num
        )
        
        # 활성 agent 유무와 상관없이 round 시작을 기록
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)
        
        if not active_agents:
            # 활성 agent가 없을 때도 round 종료를 기록(actions_count=0)
            if action_logger:
                action_logger.log_round_end(round_num + 1, 0)
            continue
        
        actions = {agent: LLMAction() for _, agent in active_agents}
        await result.env.step(actions)
        
        # 데이터베이스에서 실제 실행된 동작을 가져와 기록
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = 0
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
    
    # 주의: 환경을 닫지 않고, Interview에서 사용하도록 유지
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"시뮬레이션 루프 완료! 소요 시간: {elapsed:.1f}초, 총 동작: {total_actions}")
    
    return result


async def run_reddit_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Reddit 시뮬레이션 실행
    
    Args:
        config: 시뮬레이션 구성
        simulation_dir: 시뮬레이션 디렉터리
        action_logger: 액션 로그 기록기
        main_logger: 메인 로그 관리자
        max_rounds: 최대 시뮬레이션 라운드 수(선택, 너무 긴 시뮬레이션을 잘라내는 용도)
        
    Returns:
        PlatformSimulation: env와 agent_graph를 포함한 결과 객체
    """
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Reddit] {msg}")
        print(f"[Reddit] {msg}")
    
    log_info("초기화...")

    # Reddit 가속 LLM 설정 사용（있으면, 없으면 공용 설정으로 폴백）
    model, llm_runtime = create_model(config, use_boost=True)
    
    profile_path = os.path.join(simulation_dir, "reddit_profiles.json")
    if not os.path.exists(profile_path):
        log_info(f"오류: Profile 파일이 존재하지 않음: {profile_path}")
        return result
    
    result.agent_graph = await generate_reddit_agent_graph(
        profile_path=profile_path,
        model=model,
        available_actions=REDDIT_ACTIONS,
    )
    
    # 구성 파일에서 Agent 실제 이름 매핑 가져오기（기본 Agent_X 대신 entity_name 사용）
    agent_names = get_agent_names_from_config(config)
    # 구성에 특정 agent가 없으면 OASIS 기본 이름 사용
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')
    
    db_path = os.path.join(simulation_dir, "reddit_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
        semaphore=llm_runtime.semaphore,
    )
    
    await result.env.reset()
    log_info("환경이 시작되었습니다")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # DB에서 마지막으로 처리한 행 번호 추적（created_at 형식 차이를 피하기 위해 rowid 사용）
    
    # 초기 이벤트 실행
    event_config = config.get("event_config", {})
    initial_posts = event_config.get("initial_posts", [])
    
    # round 0 시작 기록（초기 이벤트 단계）
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0
    
    initial_action_count = 0
    if initial_posts:
        initial_actions = {}
        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            try:
                agent = result.env.agent_graph.get_agent(agent_id)
                if agent in initial_actions:
                    if not isinstance(initial_actions[agent], list):
                        initial_actions[agent] = [initial_actions[agent]]
                    initial_actions[agent].append(ManualAction(
                        action_type=ActionType.CREATE_POST,
                        action_args={"content": content}
                    ))
                else:
                    initial_actions[agent] = ManualAction(
                        action_type=ActionType.CREATE_POST,
                        action_args={"content": content}
                    )
                
                if action_logger:
                    action_logger.log_action(
                        round_num=0,
                        agent_id=agent_id,
                        agent_name=agent_names.get(agent_id, f"Agent_{agent_id}"),
                        action_type="CREATE_POST",
                        action_args={"content": content}
                    )
                    total_actions += 1
                    initial_action_count += 1
            except Exception:
                pass
        
        if initial_actions:
            await result.env.step(initial_actions)
            log_info(f"초기 게시글 {len(initial_actions)}개를 게시했습니다")
    
    # round 0 종료 기록
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # 메인 시뮬레이션 루프
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 72)
    minutes_per_round = time_config.get("minutes_per_round", 30)
    total_rounds = (total_hours * 60) // minutes_per_round
    
    # 최대 라운드 수가 지정되면 잘라냄
    if max_rounds is not None and max_rounds > 0:
        original_rounds = total_rounds
        total_rounds = min(total_rounds, max_rounds)
        if total_rounds < original_rounds:
            log_info(f"라운드 수가 잘렸습니다: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
    
    start_time = datetime.now()
    
    for round_num in range(total_rounds):
        # 종료 신호를 받았는지 확인
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"종료 신호를 받아 {round_num + 1} 라운드에서 시뮬레이션을 중지합니다")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = (simulated_minutes // 60) % 24
        simulated_day = simulated_minutes // (60 * 24) + 1
        
        active_agents = get_active_agents_for_round(
            result.env, config, simulated_hour, round_num
        )
        
        # 활성 agent 여부와 관계없이 round 시작을 기록
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)
        
        if not active_agents:
            # 활성 agent가 없을 때도 round 종료 기록（actions_count=0）
            if action_logger:
                action_logger.log_round_end(round_num + 1, 0)
            continue
        
        actions = {agent: LLMAction() for _, agent in active_agents}
        await result.env.step(actions)
        
        # DB에서 실제 실행된 동작을 가져와 기록
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = 0
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
    
    # 주의: 환경을 닫지 않고 Interview에서 사용하도록 남겨둠
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"시뮬레이션 루프 완료! 소요 시간: {elapsed:.1f}초, 총 동작: {total_actions}")
    
    return result


async def main():
    parser = argparse.ArgumentParser(description='OASIS 2개 플랫폼 병렬 시뮬레이션')
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='설정 파일 경로 (simulation_config.json)'
    )
    parser.add_argument(
        '--twitter-only',
        action='store_true',
        help='Twitter 시뮬레이션만 실행'
    )
    parser.add_argument(
        '--reddit-only',
        action='store_true',
        help='Reddit 시뮬레이션만 실행'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='최대 시뮬레이션 라운드 수（선택, 너무 긴 시뮬레이션을 자르기 위해）'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='시뮬레이션 완료 후 즉시 환경을 닫고, 명령 대기 모드로 들어가지 않음'
    )
    
    args = parser.parse_args()
    
    # main 함수 시작 시 shutdown 이벤트를 생성하여 프로그램 전체가 종료 신호에 응답하도록 함
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    
    if not os.path.exists(args.config):
        print(f"오류: 설정 파일이 존재하지 않음: {args.config}")
        sys.exit(1)
    
    config = load_config(args.config)
    simulation_dir = os.path.dirname(args.config) or "."
    wait_for_commands = not args.no_wait
    
    # 로그 설정 초기화（OASIS 로그 비활성화, 오래된 파일 정리）
    init_logging_for_simulation(simulation_dir)
    
    # 로그 관리자 생성
    log_manager = SimulationLogManager(simulation_dir)
    twitter_logger = log_manager.get_twitter_logger()
    reddit_logger = log_manager.get_reddit_logger()
    
    log_manager.info("=" * 60)
    log_manager.info("OASIS 양 플랫폼 병렬 시뮬레이션")
    log_manager.info(f"구성 파일: {args.config}")
    log_manager.info(f"시뮬레이션 ID: {config.get('simulation_id', 'unknown')}")
    log_manager.info(f"명령 대기 모드: {'활성화' if wait_for_commands else '비활성화'}")
    log_manager.info("=" * 60)
    
    time_config = config.get("time_config", {})
    total_hours = time_config.get('total_simulation_hours', 72)
    minutes_per_round = time_config.get('minutes_per_round', 30)
    config_total_rounds = (total_hours * 60) // minutes_per_round
    
    log_manager.info(f"시뮬레이션 파라미터:")
    log_manager.info(f"  - 총 시뮬레이션 시간: {total_hours}시간")
    log_manager.info(f"  - 라운드당 시간: {minutes_per_round}분")
    log_manager.info(f"  - 설정 총 라운드 수: {config_total_rounds}")
    if args.max_rounds:
        log_manager.info(f"  - 최대 라운드 제한: {args.max_rounds}")
        if args.max_rounds < config_total_rounds:
            log_manager.info(f"  - 실제 실행 라운드 수: {args.max_rounds} (잘림)")
    log_manager.info(f"  - Agent 수: {len(config.get('agent_configs', []))}")
    
    log_manager.info("로그 구조:")
    log_manager.info(f"  - 메인 로그: simulation.log")
    log_manager.info(f"  - Twitter 액션: twitter/actions.jsonl")
    log_manager.info(f"  - Reddit 액션: reddit/actions.jsonl")
    log_manager.info("=" * 60)
    
    start_time = datetime.now()
    
    # 두 플랫폼의 시뮬레이션 결과 저장
    twitter_result: Optional[PlatformSimulation] = None
    reddit_result: Optional[PlatformSimulation] = None
    
    if args.twitter_only:
        twitter_result = await run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds)
    elif args.reddit_only:
        reddit_result = await run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds)
    else:
        # 병렬 실행(각 플랫폼은 독립적인 로거 사용)
        results = await asyncio.gather(
            run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds),
            run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds),
        )
        twitter_result, reddit_result = results
    
    total_elapsed = (datetime.now() - start_time).total_seconds()
    log_manager.info("=" * 60)
    log_manager.info(f"시뮬레이션 루프 완료! 총 소요 시간: {total_elapsed:.1f}초")
    
    # 명령 대기 모드로 진입할지 여부
    if wait_for_commands:
        log_manager.info("")
        log_manager.info("=" * 60)
        log_manager.info("명령 대기 모드로 진입 - 환경을 계속 실행 상태로 유지")
        log_manager.info("지원 명령: interview, batch_interview, close_env")
        log_manager.info("=" * 60)
        
        # IPC 처리기 생성
        ipc_handler = ParallelIPCHandler(
            simulation_dir=simulation_dir,
            twitter_env=twitter_result.env if twitter_result else None,
            twitter_agent_graph=twitter_result.agent_graph if twitter_result else None,
            reddit_env=reddit_result.env if reddit_result else None,
            reddit_agent_graph=reddit_result.agent_graph if reddit_result else None
        )
        ipc_handler.update_status("alive")
        
        # 명령 대기 루프(전역 _shutdown_event 사용)
        try:
            while not _shutdown_event.is_set():
                should_continue = await ipc_handler.process_commands()
                if not should_continue:
                    break
                # sleep 대신 wait_for 사용, shutdown_event에 응답 가능
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                    break  # 종료 신호 수신
                except asyncio.TimeoutError:
                    pass  # 타임아웃이면 루프 계속
        except KeyboardInterrupt:
            print("\n인터럽트 신호를 받았습니다")
        except asyncio.CancelledError:
            print("\n작업이 취소되었습니다")
        except Exception as e:
            print(f"\n명령 처리 중 오류: {e}")
        
        log_manager.info("\n환경을 종료합니다...")
        ipc_handler.update_status("stopped")
    
    # 환경 종료
    if twitter_result and twitter_result.env:
        await twitter_result.env.close()
        log_manager.info("[Twitter] 환경이 종료되었습니다")
    
    if reddit_result and reddit_result.env:
        await reddit_result.env.close()
        log_manager.info("[Reddit] 환경이 종료되었습니다")
    
    log_manager.info("=" * 60)
    log_manager.info(f"모두 완료!")
    log_manager.info(f"로그 파일:")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'simulation.log')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'twitter', 'actions.jsonl')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'reddit', 'actions.jsonl')}")
    log_manager.info("=" * 60)


def setup_signal_handlers(loop=None):
    """
    시그널 핸들러를 설정하여 SIGTERM/SIGINT 수신 시 올바르게 종료되도록 보장
    
    지속형 시뮬레이션 시나리오: 시뮬레이션 완료 후 종료하지 않고 interview 명령을 대기
    종료 신호를 받으면 다음이 필요:
    1. asyncio 루프에 대기 종료를 알림
    2. 프로그램이 리소스를 정상적으로 정리할 기회 제공(데이터베이스, 환경 등 종료)
    3. 그 다음에 종료
    """
    def signal_handler(signum, frame):
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\n{sig_name} 신호를 받았습니다. 종료 중...")
        
        if not _cleanup_done:
            _cleanup_done = True
            # 이벤트를 설정해 asyncio 루프에 종료를 알림(루프가 리소스를 정리할 기회를 제공)
            if _shutdown_event:
                _shutdown_event.set()
        
        # sys.exit()를 직접 호출하지 말고, asyncio 루프가 정상 종료하며 리소스를 정리하게 함
        # 신호가 반복 수신될 때만 강제 종료
        else:
            print("강제 종료...")
            sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다")
    except SystemExit:
        pass
    finally:
        # multiprocessing 리소스 트래커 정리(종료 시 경고 방지)
        try:
            from multiprocessing import resource_tracker
            resource_tracker._resource_tracker._stop()
        except Exception:
            pass
        print("시뮬레이션 프로세스가 종료되었습니다")
