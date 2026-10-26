from __future__ import annotations

from judicial_archive.modules.administrative_documents import (
    models as administrative_documents_models,
)
from judicial_archive.modules.audit import models as audit_models
from judicial_archive.modules.auth import models as auth_models
from judicial_archive.modules.boxes import models as boxes_models
from judicial_archive.modules.case_files import models as case_files_models
from judicial_archive.modules.courts import models as courts_models
from judicial_archive.modules.files import models as files_models
from judicial_archive.modules.imports import models as imports_models
from judicial_archive.modules.inventory import models as inventory_models
from judicial_archive.modules.jobs import models as jobs_models
from judicial_archive.modules.loans import models as loans_models
from judicial_archive.modules.locations import models as locations_models
from judicial_archive.modules.ocr import models as ocr_models
from judicial_archive.modules.qr import models as qr_models
from judicial_archive.modules.retention import models as retention_models
from judicial_archive.modules.users import models as users_models

__all__ = [
    "administrative_documents_models",
    "audit_models",
    "auth_models",
    "boxes_models",
    "case_files_models",
    "courts_models",
    "files_models",
    "imports_models",
    "inventory_models",
    "jobs_models",
    "loans_models",
    "locations_models",
    "ocr_models",
    "qr_models",
    "retention_models",
    "users_models",
]
