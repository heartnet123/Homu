class AppError(Exception):
    status_code = 400
    public_message = "Request could not be completed."
    stage: str | None = None
    error_code: str = "app_error"
    retryable: bool = False

    def __init__(self, message: str | None = None, *, stage: str | None = None, error_code: str | None = None, retryable: bool | None = None):
        super().__init__(message or self.public_message)
        if message:
            self.public_message = message
        if stage is not None:
            self.stage = stage
        if error_code is not None:
            self.error_code = error_code
        if retryable is not None:
            self.retryable = retryable


class BadRequestError(AppError):
    status_code = 400
    public_message = "Invalid request."
    error_code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    public_message = "Resource not found."
    error_code = "not_found"


class ConfigurationError(AppError):
    status_code = 500
    public_message = "Server configuration is incomplete."
    error_code = "configuration_error"


class ExternalServiceError(AppError):
    status_code = 502
    public_message = "Upstream service request failed."
    error_code = "external_service_error"
    retryable = True


class PipelineStageError(AppError):
    status_code = 500
    error_code = "pipeline_stage_error"

    def __init__(self, message: str, *, stage: str, error_code: str | None = None, retryable: bool | None = None):
        super().__init__(message, stage=stage, error_code=error_code or self.error_code, retryable=retryable)
