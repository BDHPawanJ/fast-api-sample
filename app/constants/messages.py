"""Centralized API messages and HTTP status code constants."""


class APIMessages:
    """
    String constants for API success and error messages.

    Attributes:
        OPERATION_SUCCESS: Generic success message.
        CREATED: Generic created message.
        UPDATED: Generic updated message.
        DELETED: Generic deleted message.
        RETRIEVED: Generic retrieved message.
    """

    OPERATION_SUCCESS = "Operation completed successfully"
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"
    RETRIEVED = "Resource retrieved successfully"

    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"
    REGISTRATION_SUCCESS = "Registration successful"
    TOKEN_REFRESHED = "Token refreshed successfully"
    PASSWORD_CHANGED = "Password changed successfully"

    INVALID_CREDENTIALS = "Invalid email or password"
    UNAUTHORIZED = "Authentication required"
    TOKEN_EXPIRED = "Token has expired"
    TOKEN_INVALID = "Invalid token"
    INSUFFICIENT_PERMISSIONS = "Insufficient permissions"
    EMAIL_ALREADY_EXISTS = "Email already registered"
    USER_INACTIVE = "User account is inactive"

    VALIDATION_ERROR = "Validation error"
    INVALID_INPUT = "Invalid input data"
    MISSING_REQUIRED_FIELD = "Missing required field"

    RESOURCE_NOT_FOUND = "Resource not found"
    PRODUCT_NOT_FOUND = "Product not found"
    USER_NOT_FOUND = "User not found"

    INTERNAL_ERROR = "Internal server error"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"
    DATABASE_ERROR = "Database operation failed"

    PRODUCT_CREATED = "Product created successfully"
    PRODUCT_UPDATED = "Product updated successfully"
    PRODUCT_DELETED = "Product deleted successfully"
    PRODUCTS_RETRIEVED = "Products retrieved successfully"

    APPLICATION_HEALTHY = "Application is healthy"
    DATABASE_HEALTHY = "Database is healthy"
    SYSTEM_STATUS = "System status: {status}"


class HTTPStatusCodes:
    """
    HTTP status code constants used across the application.

    Attributes:
        OK: 200 HTTP OK.
        CREATED: 201 HTTP Created.
        BAD_REQUEST: 400 HTTP Bad Request.
        INTERNAL_SERVER_ERROR: 500 HTTP Internal Server Error.
    """

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
