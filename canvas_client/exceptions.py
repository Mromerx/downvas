class DownVasError(Exception):
    pass


class CanvasAPIError(DownVasError):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class CanvasAuthError(CanvasAPIError):
    pass


class RateLimitError(CanvasAPIError):
    pass


class CourseNotFoundError(CanvasAPIError):
    pass


class CanvasConnectionError(DownVasError):
    pass
