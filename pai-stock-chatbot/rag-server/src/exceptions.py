# rag-server/src/exceptions.py

class RagStackException(Exception):
    """기본 예외 클래스"""
    def __init__(self, message):
        self.message = message

# 클라이언트 측 예외 (4xx)
class ClientException(RagStackException):
    """클라이언트 측 오류"""

class InvalidRequestException(ClientException):
    """클라이언트로부터 잘못된 요청이 왔을 때"""

class AuthorizationException(ClientException):
    """인증 오류"""

class PermissionDeniedException(ClientException):
    """권한이 맞지 않을 때"""

# 서버 측 오류 (5xx)
class ServerException(RagStackException):
    """서버 측 오류"""

class DatabaseException(ServerException):
    """데이터베이스에서 발생한 예외"""

class NotFoundException(DatabaseException):
    """데이터를 찾지 못했을 때"""

# 프로젝트 특화 예외들
class SessionNotFoundException(NotFoundException):
    """세션을 찾을 수 없을 때"""

class ChatbotServiceException(ServerException):
    """챗봇 서비스 오류"""