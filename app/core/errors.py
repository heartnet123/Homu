class AppError(Exception):
    status_code = 400
    public_message = "Request could not be completed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        if message:
            self.public_message = message


class BadRequestError(AppError):
    status_code = 400
    public_message = "Invalid request."


class NotFoundError(AppError):
    status_code = 404
    public_message = "Resource not found."


class ConfigurationError(AppError):
    status_code = 500
    public_message = "Server configuration is incomplete."


class ExternalServiceError(AppError):
    status_code = 502
    public_message = "Upstream service request failed."
