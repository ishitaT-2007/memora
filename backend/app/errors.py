from fastapi import Request
from fastapi.responses import JSONResponse


class AccrueError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def accrue_error_handler(_request: Request, exc: AccrueError) -> JSONResponse:
    request_id = getattr(_request.state, "request_id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.code, "message": exc.message, "request_id": request_id},
    )
