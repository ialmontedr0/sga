from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    LOCKED = "LOCKED"


class CatalogStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CourtStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CONFLICT = "CONFLICT"


class IdentifierKind(StrEnum):
    NUC = "NUC"
    PROCESS_NUMBER = "PROCESS_NUMBER"
    SENTENCE = "SENTENCE"


class NumberingScope(StrEnum):
    GLOBAL = "GLOBAL"
    COURT = "COURT"
    BOX_TYPE = "BOX_TYPE"
    YEAR = "YEAR"


class ResetPolicy(StrEnum):
    NEVER = "NEVER"
    YEARLY = "YEARLY"
    PER_SCOPE = "PER_SCOPE"


class RetentionEntityType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    ADMINISTRATIVE_DOCUMENT = "ADMINISTRATIVE_DOCUMENT"
    FILE_ASSET = "FILE_ASSET"


class RetentionDisposition(StrEnum):
    REVIEW = "REVIEW"
    TRANSFER = "TRANSFER"
    DESTROY = "DESTROY"
    PERMANENT = "PERMANENT"


class SettingValueType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class BoxType(StrEnum):
    EXPEDIENTES = "EXPEDIENTES"
    DOCUMENTOS_ADMINISTRATIVOS = "DOCUMENTOS_ADMINISTRATIVOS"


class BoxLifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    VOIDED = "VOIDED"
    DESTROYED = "DESTROYED"


class CustodyStatus(StrEnum):
    IN_PLACE = "IN_PLACE"
    ON_LOAN = "ON_LOAN"
    IN_TRANSIT = "IN_TRANSIT"
    MISSING = "MISSING"
    IN_RECONCILIATION = "IN_RECONCILIATION"
    UNKNOWN = "UNKNOWN"


class LocationPrecision(StrEnum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


class Confidentiality(StrEnum):
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class AreaStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ShelfStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TrayStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PositionStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    RETIRED = "RETIRED"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    VOIDED = "VOIDED"
    DESTROYED = "DESTROYED"


class MovementType(StrEnum):
    ASSIGN = "ASSIGN"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"
    LOAN_PICKUP = "LOAN_PICKUP"
    LOAN_RETURN = "LOAN_RETURN"
    RECONCILIATION = "RECONCILIATION"


class MovementStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class LoanStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class FileStatus(StrEnum):
    PENDING = "PENDING"
    QUARANTINED = "QUARANTINED"
    STORED = "STORED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MISSING = "MISSING"
    CORRUPTED = "CORRUPTED"
    DELETED = "DELETED"


class FileLinkKind(StrEnum):
    PRIMARY = "PRIMARY"
    ANNEX = "ANNEX"
    SOURCE = "SOURCE"
    EVIDENCE = "EVIDENCE"


class ImportKind(StrEnum):
    INVENTORY_TABLE = "INVENTORY_TABLE"
    DOCUMENT_DIGITIZATION = "DOCUMENT_DIGITIZATION"


class ImportStatus(StrEnum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ImportFileStatus(StrEnum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ImportRowStatus(StrEnum):
    PENDING = "PENDING"
    PARSED = "PARSED"
    VALID = "VALID"
    WARNING = "WARNING"
    ERROR = "ERROR"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"


class ImportSourceType(StrEnum):
    CSV = "CSV"
    XLSX = "XLSX"
    PDF = "PDF"
    DOCX = "DOCX"
    TIFF = "TIFF"
    JPEG = "JPEG"
    PNG = "PNG"


class OcrStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    CANCELLED = "CANCELLED"


class InventoryScopeType(StrEnum):
    AREA = "AREA"
    SHELF = "SHELF"
    TRAY = "TRAY"
    POSITION_RANGE = "POSITION_RANGE"
    BOX = "BOX"


class InventoryStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class FindingType(StrEnum):
    MISSING_BOX = "MISSING_BOX"
    UNEXPECTED_BOX = "UNEXPECTED_BOX"
    WRONG_LOCATION = "WRONG_LOCATION"
    UNREGISTERED_BOX = "UNREGISTERED_BOX"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class FindingStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ACCEPTED_DIFFERENCE = "ACCEPTED_DIFFERENCE"
    ESCALATED = "ESCALATED"


class LegalHoldTargetType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    FILE_ASSET = "FILE_ASSET"


class LegalHoldStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class DeletionTargetType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    FILE_ASSET = "FILE_ASSET"


class DeletionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AuditActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    JOB = "JOB"


class AuditResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AuditSource(StrEnum):
    API = "API"
    IMPORT = "IMPORT"
    OCR = "OCR"
    TASK = "TASK"
    SYSTEM = "SYSTEM"
