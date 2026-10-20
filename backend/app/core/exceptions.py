from typing import Any, Dict, Optional


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' was not found.",
            status_code=404,
            details={"entity": entity_name, "id": str(entity_id)},
        )


class InsufficientStockException(AppException):
    def __init__(self, product_id: int, warehouse_id: int, requested: int, available: int):
        super().__init__(
            message=(
                f"Insufficient stock for product ID {product_id} at warehouse ID {warehouse_id}. "
                f"Requested: {requested}, Available: {available}."
            ),
            status_code=409,
            details={
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "requested": requested,
                "available": available,
            },
        )


class InvalidStateTransitionException(AppException):
    def __init__(self, entity_name: str, current_state: str, attempted_state: str):
        super().__init__(
            message=f"Cannot transition {entity_name} from status '{current_state}' to '{attempted_state}'.",
            status_code=422,
            details={
                "entity": entity_name,
                "current_state": current_state,
                "attempted_state": attempted_state,
            },
        )


class UnauthorizedWarehouseAccessException(AppException):
    def __init__(self, user_id: int, warehouse_id: int):
        super().__init__(
            message=f"User ID {user_id} does not have authorized access to warehouse ID {warehouse_id}.",
            status_code=403,
            details={"user_id": user_id, "warehouse_id": warehouse_id},
        )


class DuplicateEntityException(AppException):
    def __init__(self, entity_name: str, field: str, value: Any):
        super().__init__(
            message=f"{entity_name} with {field} '{value}' already exists.",
            status_code=409,
            details={"entity": entity_name, "field": field, "value": str(value)},
        )


class IdempotencyConflictException(AppException):
    def __init__(self, key: str):
        super().__init__(
            message=f"A concurrent request with idempotency key '{key}' is currently being processed.",
            status_code=409,
            details={"idempotency_key": key},
        )


class AuthenticationFailedException(AppException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, status_code=401)


class PermissionDeniedException(AppException):
    def __init__(self, required_permission: str):
        super().__init__(
            message=f"Access denied: missing required permission '{required_permission}'.",
            status_code=403,
            details={"required_permission": required_permission},
        )
