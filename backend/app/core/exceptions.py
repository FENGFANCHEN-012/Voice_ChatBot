from fastapi import HTTPException


class DocumentNotFoundError(HTTPException):
    def __init__(self, doc_id: str):
        super().__init__(status_code=404, detail=f"Document {doc_id} not found")


class SessionNotFoundError(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(status_code=404, detail=f"Session {session_id} not found")


class ProcessingError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
