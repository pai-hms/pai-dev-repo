# rag-server/src/exceptions.py

class RagStackException(Exception):
    def __init__(self, message):
        self.message = message

# 클라이언트 측 예외 (4xx)
class ClientException(RagStackException):
    """클라이언트 측 오류"""

class AuthorizationException(ClientException):
    """인증 오류"""

class InvalidRequestException(ClientException):
    """클라이언트로부터 잘못된 요청 왔을 때"""

class InvalidTokenException(AuthorizationException):
    """유효하지 않은 정보가 들어왔을 때"""

class InvalidUserException(ClientException):
    """삭제 등의 이유로 유효하지 않은 유저일 때"""

class NotExistUserException(ClientException):
    """사용자가 존재하지 않을 때"""

class WrongPasswordException(ClientException):
    """비밀번호가 잘못 되었을 때"""

class PermissionDeniedException(ClientException):
    """권한 맞지 않을 때 ( 어드민 / 매니저 / 일반 유저 )"""

class ExpiredTokenException(InvalidTokenException):
    """만료된 토큰"""

class FileTypeException(ClientException):
    """파일 형식 오류"""

class UnsupportedModelException(ClientException):
    """지원하지 않는 모델 예외처리"""

class InvalidApiKeyException(ClientException):
    """유효하지 않은 API 키"""

# 서버 측 오류 (5xx)
class ServerException(RagStackException):
    """서버 측 오류"""

class ModelNotFoundException(ServerException):
    """LLM 모델을 찾지 못했을 때"""

class StorageException(ServerException):
    """스토리지 오류"""

class InvalidStatusUpdateException(ServerException):
    """상태 업데이트 오류"""

class DatabaseException(ServerException):
    """데이터 베이스에서 발생한 Exception"""

class ElasticsearchException(ServerException):
    """Elasticsearch에서 발생한 Exception"""

class NotImplementedException(ServerException):
    """구현되지 않은 기능을 호출했을 때"""

class NotFoundException(DatabaseException):
    """데이터를 찾지 못했을 때"""

class DBIntegrityException(DatabaseException):
    """데이터베이스 무결성 오류"""

class AlreadyExistsException(DatabaseException):
    """이미 존재한 경우"""

class EmbeddingException(ServerException):
    """임베딩 과정 중  예외 발생"""

class CustomLLMException(ServerException):
    """Custom LLM 예외"""

class NotFoundServiceConfigException(ServerException):
    """서비스 설정 조회 오류"""
    
class KnowledgeManagementException(ServerException):
    """지식 관리 오류"""

class InvalidKnowledgeFileStatusException(ServerException):
    """수정/재시도가 허용되지 않는 상태일 때 발생"""

# 워커 오류
class WorkerException(ServerException):
    """워커 오류"""

class CsvParsingException(WorkerException):
    """CSV 파싱 오류"""

class PdfParsingException(WorkerException):
    """PDF 파싱 오류"""

class UnstructedProcessorException(WorkerException):
    """비정형 데이터 처리 과정 오류"""

class StructedProcessorException(WorkerException):
    """정형 데이터 처리 과정 오류"""

# 프로젝트 특화 예외들
class SessionNotFoundException(NotFoundException):
    """세션을 찾을 수 없을 때"""

class ChatbotServiceException(ServerException):
    """챗봇 서비스 오류"""

class StreamingException(ServerException):
    """스트리밍 처리 오류"""