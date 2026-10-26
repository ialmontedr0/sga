BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 20261026_0001

CREATE TABLE areas (
    code VARCHAR(16) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(500),
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_areas PRIMARY KEY (id),
    CONSTRAINT ck_areas_code_format CHECK (code ~ '^[A-Z][A-Z0-9-]{0,15}$'),
    CONSTRAINT ck_areas_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_areas_name_not_empty CHECK (length(btrim(name)) > 0)
);

CREATE TABLE courts (
    code_raw VARCHAR NOT NULL,
    code_normalized VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    court_type VARCHAR,
    jurisdiction VARCHAR,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    effective_from DATE,
    effective_to DATE,
    source VARCHAR(64),
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_courts PRIMARY KEY (id),
    CONSTRAINT ck_courts_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_courts_code_normalized CHECK (code_normalized = upper(btrim(code_raw))),
    CONSTRAINT ck_courts_effective_range CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_courts_name_not_empty CHECK (length(btrim(name)) > 0)
);

CREATE INDEX ix_courts_name ON courts (name);

CREATE INDEX ix_courts_status ON courts (status);

CREATE TABLE party_roles (
    code VARCHAR(64) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description VARCHAR(500),
    is_system BOOLEAN DEFAULT false NOT NULL,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_party_roles PRIMARY KEY (id),
    CONSTRAINT ck_party_roles_code_format CHECK (code ~ '^[A-Z][A-Z0-9_]{1,63}$'),
    CONSTRAINT ck_party_roles_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_party_roles_name_not_empty CHECK (length(btrim(name)) > 0),
    CONSTRAINT uq_party_roles_code UNIQUE (code)
);

CREATE TABLE permissions (
    code VARCHAR(100) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_permissions PRIMARY KEY (id),
    CONSTRAINT ck_permissions_code_format CHECK (code ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'),
    CONSTRAINT ck_permissions_name_not_empty CHECK (length(btrim(name)) > 0),
    CONSTRAINT uq_permissions_code UNIQUE (code)
);

CREATE TABLE resolution_types (
    code VARCHAR(32) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description VARCHAR(500),
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_resolution_types PRIMARY KEY (id),
    CONSTRAINT ck_resolution_types_code_format CHECK (code ~ '^[A-Z][A-Z0-9_]{1,31}$'),
    CONSTRAINT ck_resolution_types_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_resolution_types_name_not_empty CHECK (length(btrim(name)) > 0),
    CONSTRAINT uq_resolution_types_code UNIQUE (code)
);

CREATE TABLE roles (
    code VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(500),
    is_system BOOLEAN DEFAULT false NOT NULL,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_roles PRIMARY KEY (id),
    CONSTRAINT ck_roles_code_format CHECK (code ~ '^[A-Z][A-Z0-9_]{1,63}$'),
    CONSTRAINT ck_roles_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_roles_name_not_empty CHECK (length(btrim(name)) > 0),
    CONSTRAINT uq_roles_code UNIQUE (code)
);

CREATE TABLE users (
    username VARCHAR(64) NOT NULL,
    username_normalized VARCHAR(64) NOT NULL,
    email VARCHAR(254),
    email_normalized VARCHAR(254),
    display_name VARCHAR(160) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    must_change_password BOOLEAN DEFAULT true NOT NULL,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    failed_login_count INTEGER DEFAULT 0 NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT ck_users_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'LOCKED')),
    CONSTRAINT ck_users_email_pair CHECK ((email IS NULL AND email_normalized IS NULL) OR (email IS NOT NULL AND email_normalized IS NOT NULL)),
    CONSTRAINT ck_users_email_normalized CHECK (email IS NULL OR email_normalized = lower(btrim(email))),
    CONSTRAINT ck_users_password_hash_not_empty CHECK (length(password_hash) >= 20),
    CONSTRAINT ck_users_username_normalized CHECK (username_normalized = lower(btrim(username))),
    CONSTRAINT uq_users_email_normalized UNIQUE (email_normalized),
    CONSTRAINT uq_users_username_normalized UNIQUE (username_normalized)
);

CREATE INDEX ix_users_display_name ON users (display_name);

CREATE INDEX ix_users_status ON users (status);

CREATE TABLE audit_events (
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    actor_type VARCHAR(16) NOT NULL,
    actor_user_id UUID,
    actor_label VARCHAR(160),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID,
    before_data JSONB,
    after_data JSONB,
    metadata JSONB,
    request_id VARCHAR(128),
    correlation_id VARCHAR(128),
    ip_address INET,
    user_agent VARCHAR(512),
    source VARCHAR(16) NOT NULL,
    result VARCHAR(16) NOT NULL,
    error_code VARCHAR(64),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_audit_events PRIMARY KEY (id),
    CONSTRAINT ck_audit_events_user_actor CHECK (actor_type <> 'USER' OR actor_user_id IS NOT NULL),
    CONSTRAINT ck_audit_events_actor_type CHECK (actor_type IN ('USER', 'SYSTEM', 'JOB')),
    CONSTRAINT ck_audit_events_after_object CHECK (after_data IS NULL OR jsonb_typeof(after_data) = 'object'),
    CONSTRAINT ck_audit_events_before_object CHECK (before_data IS NULL OR jsonb_typeof(before_data) = 'object'),
    CONSTRAINT ck_audit_events_metadata_object CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object'),
    CONSTRAINT ck_audit_events_result CHECK (result IN ('SUCCESS', 'FAILURE')),
    CONSTRAINT ck_audit_events_source CHECK (source IN ('API', 'IMPORT', 'OCR', 'TASK', 'SYSTEM')),
    CONSTRAINT ck_audit_events_action_not_empty CHECK (length(btrim(action)) > 0),
    CONSTRAINT fk_audit_events_actor_user_id_users FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_audit_events_actor ON audit_events (actor_user_id, occurred_at);

CREATE INDEX ix_audit_events_entity ON audit_events (entity_type, entity_id, occurred_at);

CREATE INDEX ix_audit_events_occurred_at ON audit_events (occurred_at);

CREATE INDEX ix_audit_events_request_id ON audit_events (request_id);

CREATE TABLE file_assets (
    sha256 VARCHAR(64) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(160) NOT NULL,
    size_bytes BIGINT NOT NULL,
    page_count INTEGER,
    status VARCHAR(16) DEFAULT 'PENDING' NOT NULL,
    metadata JSONB,
    created_by UUID,
    stored_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_file_assets PRIMARY KEY (id),
    CONSTRAINT ck_file_assets_metadata_object CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object'),
    CONSTRAINT ck_file_assets_sha256_format CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_file_assets_deleted_status CHECK (status <> 'DELETED' OR deleted_at IS NOT NULL),
    CONSTRAINT ck_file_assets_status CHECK (status IN ('PENDING', 'QUARANTINED', 'STORED', 'VERIFIED', 'REJECTED', 'MISSING', 'CORRUPTED', 'DELETED')),
    CONSTRAINT ck_file_assets_deleted_actor CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL),
    CONSTRAINT ck_file_assets_original_name_not_empty CHECK (length(btrim(original_name)) > 0),
    CONSTRAINT ck_file_assets_storage_key_not_empty CHECK (length(btrim(storage_key)) > 0),
    CONSTRAINT ck_file_assets_page_count CHECK (page_count IS NULL OR page_count > 0),
    CONSTRAINT ck_file_assets_size_non_negative CHECK (size_bytes >= 0),
    CONSTRAINT fk_file_assets_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_file_assets_deleted_by_users FOREIGN KEY(deleted_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_file_assets_storage_key UNIQUE (storage_key)
);

CREATE INDEX ix_file_assets_sha256 ON file_assets (sha256);

CREATE INDEX ix_file_assets_status ON file_assets (status);

CREATE TABLE identifier_format_profiles (
    court_id UUID NOT NULL,
    identifier_kind VARCHAR(32) NOT NULL,
    pattern VARCHAR(255),
    tokens JSONB,
    examples JSONB,
    rejects JSONB,
    strict BOOLEAN DEFAULT false NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    effective_from DATE DEFAULT CURRENT_DATE NOT NULL,
    effective_to DATE,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_identifier_format_profiles PRIMARY KEY (id),
    CONSTRAINT ck_identifier_format_profiles_examples_array CHECK (examples IS NULL OR jsonb_typeof(examples) = 'array'),
    CONSTRAINT ck_identifier_format_profiles_kind CHECK (identifier_kind IN ('NUC', 'PROCESS_NUMBER', 'SENTENCE')),
    CONSTRAINT ck_identifier_format_profiles_rejects_array CHECK (rejects IS NULL OR jsonb_typeof(rejects) = 'array'),
    CONSTRAINT ck_identifier_format_profiles_effective_range CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_identifier_format_profiles_strict_pattern CHECK (strict = false OR pattern IS NOT NULL),
    CONSTRAINT fk_identifier_format_profiles_court_id_courts FOREIGN KEY(court_id) REFERENCES courts (id) ON DELETE RESTRICT
);

CREATE INDEX ix_identifier_format_profiles_court_kind ON identifier_format_profiles (court_id, identifier_kind);

CREATE UNIQUE INDEX uq_identifier_format_profiles_active ON identifier_format_profiles (court_id, identifier_kind) WHERE is_active;

CREATE TABLE import_batches (
    import_kind VARCHAR(32) NOT NULL,
    source_type VARCHAR(16) NOT NULL,
    status VARCHAR(24) DEFAULT 'DRAFT' NOT NULL,
    idempotency_key VARCHAR(128),
    original_filename VARCHAR(255),
    sha256 VARCHAR(64),
    total_files INTEGER DEFAULT 0 NOT NULL,
    processed_files INTEGER DEFAULT 0 NOT NULL,
    total_rows INTEGER DEFAULT 0 NOT NULL,
    valid_rows INTEGER DEFAULT 0 NOT NULL,
    warning_rows INTEGER DEFAULT 0 NOT NULL,
    error_rows INTEGER DEFAULT 0 NOT NULL,
    created_by UUID,
    reviewed_by UUID,
    approved_by UUID,
    applied_by UUID,
    approval_exception_reason VARCHAR(500),
    submitted_at TIMESTAMP WITH TIME ZONE,
    applied_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_reason VARCHAR(1000),
    notes VARCHAR(2000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_import_batches PRIMARY KEY (id),
    CONSTRAINT ck_import_batches_kind CHECK (import_kind IN ('INVENTORY_TABLE', 'DOCUMENT_DIGITIZATION')),
    CONSTRAINT ck_import_batches_source CHECK (source_type IN ('CSV', 'XLSX', 'PDF', 'DOCX', 'TIFF', 'JPEG', 'PNG')),
    CONSTRAINT ck_import_batches_applied_fields CHECK (status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)),
    CONSTRAINT ck_import_batches_failure_reason CHECK (status <> 'FAILED' OR (failure_reason IS NOT NULL AND length(btrim(failure_reason)) > 0)),
    CONSTRAINT ck_import_batches_status CHECK (status IN ('DRAFT', 'UPLOADED', 'PROCESSING', 'REVIEW_REQUIRED', 'READY', 'APPLYING', 'APPLIED', 'FAILED', 'CANCELLED')),
    CONSTRAINT ck_import_batches_ready_without_errors CHECK (status NOT IN ('READY', 'APPLYING', 'APPLIED') OR error_rows = 0),
    CONSTRAINT ck_import_batches_separation CHECK (approved_by IS NULL OR created_by IS NULL OR approved_by <> created_by OR (approval_exception_reason IS NOT NULL AND length(btrim(approval_exception_reason)) > 0)),
    CONSTRAINT ck_import_batches_idempotency_key CHECK (idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0),
    CONSTRAINT ck_import_batches_processed_files CHECK (processed_files <= total_files),
    CONSTRAINT ck_import_batches_non_negative_counts CHECK (total_files >= 0 AND processed_files >= 0 AND total_rows >= 0 AND valid_rows >= 0 AND warning_rows >= 0 AND error_rows >= 0),
    CONSTRAINT ck_import_batches_row_counts CHECK (valid_rows + warning_rows + error_rows <= total_rows),
    CONSTRAINT fk_import_batches_applied_by_users FOREIGN KEY(applied_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_batches_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_batches_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_batches_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_import_batches_created_at ON import_batches (created_at);

CREATE INDEX ix_import_batches_status ON import_batches (status);

CREATE UNIQUE INDEX uq_import_batches_idempotency ON import_batches (created_by, idempotency_key) WHERE idempotency_key IS NOT NULL AND created_by IS NOT NULL;

CREATE TABLE loans (
    status VARCHAR(16) DEFAULT 'REQUESTED' NOT NULL,
    purpose VARCHAR(1000) NOT NULL,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    delivered_by UUID,
    delivered_at TIMESTAMP WITH TIME ZONE,
    due_at TIMESTAMP WITH TIME ZONE,
    returned_by UUID,
    returned_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID,
    cancellation_reason VARCHAR(500),
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID,
    rejection_reason VARCHAR(500),
    approval_exception_reason VARCHAR(500),
    notes VARCHAR(2000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_loans PRIMARY KEY (id),
    CONSTRAINT ck_loans_cancellation_fields CHECK (status <> 'CANCELLED' OR (cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL AND length(btrim(cancellation_reason)) > 0)),
    CONSTRAINT ck_loans_rejection_fields CHECK (status <> 'REJECTED' OR (rejected_at IS NOT NULL AND rejection_reason IS NOT NULL AND length(btrim(rejection_reason)) > 0)),
    CONSTRAINT ck_loans_return_fields CHECK (status <> 'RETURNED' OR (returned_at IS NOT NULL AND returned_by IS NOT NULL)),
    CONSTRAINT ck_loans_status CHECK (status IN ('REQUESTED', 'APPROVED', 'DELIVERED', 'RETURNED', 'CANCELLED', 'REJECTED')),
    CONSTRAINT ck_loans_approval_fields CHECK (status NOT IN ('APPROVED', 'DELIVERED', 'RETURNED') OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)),
    CONSTRAINT ck_loans_delivery_fields CHECK (status NOT IN ('DELIVERED', 'RETURNED') OR (delivered_at IS NOT NULL AND delivered_by IS NOT NULL)),
    CONSTRAINT ck_loans_approval_after_request CHECK (approved_at IS NULL OR approved_at >= requested_at),
    CONSTRAINT ck_loans_approval_separation CHECK (approved_by IS NULL OR requested_by IS NULL OR approved_by <> requested_by OR (approval_exception_reason IS NOT NULL AND length(btrim(approval_exception_reason)) > 0)),
    CONSTRAINT ck_loans_due_after_delivery CHECK (due_at IS NULL OR delivered_at IS NULL OR due_at >= delivered_at),
    CONSTRAINT ck_loans_purpose_not_empty CHECK (length(btrim(purpose)) > 0),
    CONSTRAINT ck_loans_return_after_delivery CHECK (returned_at IS NULL OR delivered_at IS NULL OR returned_at >= delivered_at),
    CONSTRAINT fk_loans_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_cancelled_by_users FOREIGN KEY(cancelled_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_delivered_by_users FOREIGN KEY(delivered_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_rejected_by_users FOREIGN KEY(rejected_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_requested_by_users FOREIGN KEY(requested_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_returned_by_users FOREIGN KEY(returned_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_loans_due_at ON loans (due_at);

CREATE INDEX ix_loans_requested_at ON loans (requested_at);

CREATE INDEX ix_loans_status ON loans (status);

CREATE TABLE numbering_policies (
    code VARCHAR(64) NOT NULL,
    description VARCHAR(500),
    scope VARCHAR(16) NOT NULL,
    court_id UUID,
    box_type VARCHAR(40),
    year INTEGER,
    sequence_name VARCHAR(63) NOT NULL,
    prefix VARCHAR(32),
    suffix VARCHAR(32),
    padding INTEGER DEFAULT 0 NOT NULL,
    start_value INTEGER NOT NULL,
    step INTEGER DEFAULT 1 NOT NULL,
    reset_policy VARCHAR(16) DEFAULT 'NEVER' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    effective_from DATE DEFAULT CURRENT_DATE NOT NULL,
    effective_to DATE,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_numbering_policies PRIMARY KEY (id),
    CONSTRAINT ck_numbering_policies_scope_columns CHECK (((scope = 'GLOBAL' AND court_id IS NULL AND box_type IS NULL AND year IS NULL) OR (scope = 'COURT' AND court_id IS NOT NULL AND box_type IS NULL AND year IS NULL) OR (scope = 'BOX_TYPE' AND court_id IS NULL AND box_type IS NOT NULL AND year IS NULL) OR (scope = 'YEAR' AND court_id IS NULL AND box_type IS NULL AND year IS NOT NULL))),
    CONSTRAINT ck_numbering_policies_box_type CHECK (box_type IN ('EXPEDIENTES', 'DOCUMENTOS_ADMINISTRATIVOS')),
    CONSTRAINT ck_numbering_policies_reset CHECK (reset_policy IN ('NEVER', 'YEARLY', 'PER_SCOPE')),
    CONSTRAINT ck_numbering_policies_scope CHECK (scope IN ('GLOBAL', 'COURT', 'BOX_TYPE', 'YEAR')),
    CONSTRAINT ck_numbering_policies_effective_range CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_numbering_policies_sequence_name CHECK (length(btrim(sequence_name)) > 0),
    CONSTRAINT ck_numbering_policies_padding CHECK (padding BETWEEN 0 AND 12),
    CONSTRAINT ck_numbering_policies_start_value CHECK (start_value > 0),
    CONSTRAINT ck_numbering_policies_step CHECK (step > 0),
    CONSTRAINT fk_numbering_policies_court_id_courts FOREIGN KEY(court_id) REFERENCES courts (id) ON DELETE RESTRICT,
    CONSTRAINT uq_numbering_policies_code UNIQUE (code),
    CONSTRAINT uq_numbering_policies_sequence_name UNIQUE (sequence_name)
);

CREATE UNIQUE INDEX uq_numbering_policies_active_box_type ON numbering_policies (box_type) WHERE is_active AND scope = 'BOX_TYPE';

CREATE UNIQUE INDEX uq_numbering_policies_active_court ON numbering_policies (court_id) WHERE is_active AND scope = 'COURT';

CREATE UNIQUE INDEX uq_numbering_policies_active_global ON numbering_policies (scope) WHERE is_active AND scope = 'GLOBAL';

CREATE UNIQUE INDEX uq_numbering_policies_active_year ON numbering_policies (year) WHERE is_active AND scope = 'YEAR';

CREATE TABLE persons (
    display_name VARCHAR(300) NOT NULL,
    normalized_name VARCHAR(300) NOT NULL,
    aliases JSONB,
    identification_type VARCHAR(32),
    identification_number VARCHAR(64),
    birth_year INTEGER,
    birth_month INTEGER,
    birth_day INTEGER,
    notes VARCHAR(2000),
    created_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_persons PRIMARY KEY (id),
    CONSTRAINT ck_persons_aliases_array CHECK (aliases IS NULL OR jsonb_typeof(aliases) = 'array'),
    CONSTRAINT ck_persons_birth_day_range CHECK (birth_day IS NULL OR birth_day BETWEEN 1 AND 31),
    CONSTRAINT ck_persons_birth_day_requires_month CHECK (birth_day IS NULL OR birth_month IS NOT NULL),
    CONSTRAINT ck_persons_birth_month_range CHECK (birth_month IS NULL OR birth_month BETWEEN 1 AND 12),
    CONSTRAINT ck_persons_birth_month_requires_year CHECK (birth_month IS NULL OR birth_year IS NOT NULL),
    CONSTRAINT ck_persons_birth_year_range CHECK (birth_year IS NULL OR birth_year BETWEEN 1 AND 9999),
    CONSTRAINT ck_persons_deleted_actor CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL),
    CONSTRAINT ck_persons_display_name_not_empty CHECK (length(btrim(display_name)) > 0),
    CONSTRAINT ck_persons_normalized_name_not_empty CHECK (length(btrim(normalized_name)) > 0),
    CONSTRAINT fk_persons_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_persons_deleted_by_users FOREIGN KEY(deleted_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_persons_identification ON persons (identification_number);

CREATE INDEX ix_persons_normalized_name ON persons (normalized_name);

CREATE TABLE retention_policies (
    code VARCHAR(64) NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    court_id UUID,
    box_type VARCHAR(40),
    retention_months INTEGER,
    disposition VARCHAR(16) NOT NULL,
    legal_basis VARCHAR(1000) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    effective_from DATE DEFAULT CURRENT_DATE NOT NULL,
    effective_to DATE,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_retention_policies PRIMARY KEY (id),
    CONSTRAINT ck_retention_policies_box_type CHECK (box_type IN ('EXPEDIENTES', 'DOCUMENTOS_ADMINISTRATIVOS')),
    CONSTRAINT ck_retention_policies_disposition CHECK (disposition IN ('REVIEW', 'TRANSFER', 'DESTROY', 'PERMANENT')),
    CONSTRAINT ck_retention_policies_entity_type CHECK (entity_type IN ('BOX', 'CASE_FILE', 'ADMINISTRATIVE_DOCUMENT', 'FILE_ASSET')),
    CONSTRAINT ck_retention_policies_effective_range CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_retention_policies_active_legal_basis CHECK (is_active = false OR length(btrim(legal_basis)) > 0),
    CONSTRAINT ck_retention_policies_months CHECK (retention_months IS NULL OR retention_months > 0),
    CONSTRAINT fk_retention_policies_court_id_courts FOREIGN KEY(court_id) REFERENCES courts (id) ON DELETE RESTRICT,
    CONSTRAINT uq_retention_policies_code UNIQUE (code)
);

CREATE INDEX ix_retention_policies_lookup ON retention_policies (entity_type, court_id, box_type, is_active);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    granted_by UUID,
    CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permissions_granted_by_users FOREIGN KEY(granted_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE INDEX ix_role_permissions_permission_id ON role_permissions (permission_id);

CREATE TABLE shelves (
    area_id UUID NOT NULL,
    code VARCHAR(16) NOT NULL,
    name VARCHAR(120),
    levels INTEGER,
    positions_per_level INTEGER,
    capacity_positions INTEGER GENERATED ALWAYS AS (levels * positions_per_level) STORED,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_shelves PRIMARY KEY (id),
    CONSTRAINT ck_shelves_code_format CHECK (code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'),
    CONSTRAINT ck_shelves_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_shelves_capacity_pair CHECK ((levels IS NULL AND positions_per_level IS NULL) OR (levels IS NOT NULL AND positions_per_level IS NOT NULL)),
    CONSTRAINT ck_shelves_levels_positive CHECK (levels IS NULL OR levels > 0),
    CONSTRAINT ck_shelves_positions_positive CHECK (positions_per_level IS NULL OR positions_per_level > 0),
    CONSTRAINT fk_shelves_area_id_areas FOREIGN KEY(area_id) REFERENCES areas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_shelves_area_code UNIQUE (area_id, code)
);

CREATE INDEX ix_shelves_area_id ON shelves (area_id);

CREATE TABLE system_settings (
    key VARCHAR(128) NOT NULL,
    value JSONB NOT NULL,
    value_type VARCHAR(16) NOT NULL,
    description VARCHAR(500) NOT NULL,
    updated_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_system_settings PRIMARY KEY (id),
    CONSTRAINT ck_system_settings_value_matches_type CHECK (((value_type = 'STRING' AND jsonb_typeof(value) = 'string') OR (value_type = 'INTEGER' AND jsonb_typeof(value) = 'number') OR (value_type = 'BOOLEAN' AND jsonb_typeof(value) = 'boolean') OR (value_type = 'JSON' AND jsonb_typeof(value) IN ('object', 'array')))),
    CONSTRAINT ck_system_settings_key_format CHECK (key ~ '^[a-z][a-z0-9_.-]{2,127}$'),
    CONSTRAINT ck_system_settings_value_type CHECK (value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'JSON')),
    CONSTRAINT ck_system_settings_description_not_empty CHECK (length(btrim(description)) > 0),
    CONSTRAINT fk_system_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_system_settings_key UNIQUE (key)
);

CREATE TABLE task_jobs (
    job_type VARCHAR(80) NOT NULL,
    status VARCHAR(24) DEFAULT 'PENDING' NOT NULL,
    priority INTEGER DEFAULT 0 NOT NULL,
    payload JSONB,
    result JSONB,
    error JSONB,
    progress INTEGER,
    attempts INTEGER DEFAULT 0 NOT NULL,
    max_attempts INTEGER DEFAULT 3 NOT NULL,
    idempotency_key VARCHAR(128),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_task_jobs PRIMARY KEY (id),
    CONSTRAINT ck_task_jobs_error_object CHECK (error IS NULL OR jsonb_typeof(error) = 'object'),
    CONSTRAINT ck_task_jobs_payload_object CHECK (payload IS NULL OR jsonb_typeof(payload) = 'object'),
    CONSTRAINT ck_task_jobs_result_object CHECK (result IS NULL OR jsonb_typeof(result) = 'object'),
    CONSTRAINT ck_task_jobs_failed_error CHECK (status <> 'FAILED' OR error IS NOT NULL),
    CONSTRAINT ck_task_jobs_succeeded_finished CHECK (status <> 'SUCCEEDED' OR finished_at IS NOT NULL),
    CONSTRAINT ck_task_jobs_status CHECK (status IN ('PENDING', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'RETRY_SCHEDULED', 'CANCELLED')),
    CONSTRAINT ck_task_jobs_attempts CHECK (attempts >= 0 AND max_attempts > 0 AND attempts <= max_attempts),
    CONSTRAINT ck_task_jobs_idempotency_key CHECK (idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0),
    CONSTRAINT ck_task_jobs_progress CHECK (progress IS NULL OR (progress >= 0 AND progress <= 100)),
    CONSTRAINT fk_task_jobs_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_task_jobs_queue ON task_jobs (status, scheduled_at);

CREATE INDEX ix_task_jobs_type ON task_jobs (job_type);

CREATE UNIQUE INDEX uq_task_jobs_idempotency ON task_jobs (job_type, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    assigned_by UUID,
    CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_user_roles_role_id ON user_roles (role_id);

CREATE TABLE user_sessions (
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    csrf_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    absolute_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent VARCHAR(512),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_user_sessions PRIMARY KEY (id),
    CONSTRAINT ck_user_sessions_expiry_after_creation CHECK (absolute_expires_at > created_at),
    CONSTRAINT ck_user_sessions_last_seen_after_creation CHECK (last_seen_at IS NULL OR last_seen_at >= created_at),
    CONSTRAINT ck_user_sessions_token_hash_not_empty CHECK (length(token_hash) > 0),
    CONSTRAINT ck_user_sessions_revoked_after_creation CHECK (revoked_at IS NULL OR revoked_at >= created_at),
    CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_user_sessions_token_hash UNIQUE (token_hash)
);

CREATE INDEX id_user_sessions_active_user ON user_sessions (user_id) WHERE revoked_at IS NULL;

CREATE INDEX ix_user_sessions_expires_at ON user_sessions (absolute_expires_at);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE TABLE import_files (
    batch_id UUID NOT NULL,
    file_asset_id UUID NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    source_type VARCHAR(16) NOT NULL,
    status VARCHAR(24) DEFAULT 'PENDING' NOT NULL,
    page_count INTEGER,
    rows_extracted INTEGER DEFAULT 0 NOT NULL,
    error JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_import_files PRIMARY KEY (id),
    CONSTRAINT ck_import_files_error_object CHECK (error IS NULL OR jsonb_typeof(error) = 'object'),
    CONSTRAINT ck_import_files_source CHECK (source_type IN ('CSV', 'XLSX', 'PDF', 'DOCX', 'TIFF', 'JPEG', 'PNG')),
    CONSTRAINT ck_import_files_extracted_at CHECK (status <> 'EXTRACTED' OR extracted_at IS NOT NULL),
    CONSTRAINT ck_import_files_failed_error CHECK (status <> 'FAILED' OR error IS NOT NULL),
    CONSTRAINT ck_import_files_status CHECK (status IN ('PENDING', 'EXTRACTING', 'EXTRACTED', 'REVIEW_REQUIRED', 'FAILED', 'SKIPPED')),
    CONSTRAINT ck_import_files_page_count CHECK (page_count IS NULL OR page_count > 0),
    CONSTRAINT ck_import_files_rows_extracted CHECK (rows_extracted >= 0),
    CONSTRAINT fk_import_files_batch_id_import_batches FOREIGN KEY(batch_id) REFERENCES import_batches (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_files_file_asset_id_file_assets FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_files_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_import_files_batch_asset UNIQUE (batch_id, file_asset_id),
    CONSTRAINT uq_import_files_id_batch UNIQUE (id, batch_id)
);

CREATE INDEX ix_import_files_batch_id ON import_files (batch_id);

CREATE INDEX ix_import_files_status ON import_files (status);

CREATE TABLE trays (
    shelf_id UUID NOT NULL,
    code VARCHAR(16) NOT NULL,
    name VARCHAR(120),
    position_count INTEGER,
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_trays PRIMARY KEY (id),
    CONSTRAINT ck_trays_code_format CHECK (code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'),
    CONSTRAINT ck_trays_status CHECK (status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_trays_position_count CHECK (position_count IS NULL OR position_count > 0),
    CONSTRAINT fk_trays_shelf_id_shelves FOREIGN KEY(shelf_id) REFERENCES shelves (id) ON DELETE RESTRICT,
    CONSTRAINT uq_trays_shelf_code UNIQUE (shelf_id, code)
);

CREATE INDEX ix_trays_shelf_id ON trays (shelf_id);

CREATE TABLE ocr_results (
    file_asset_id UUID NOT NULL,
    import_file_id UUID,
    engine_name VARCHAR(80) NOT NULL,
    engine_version VARCHAR(40),
    status VARCHAR(24) DEFAULT 'PENDING' NOT NULL,
    text VARCHAR,
    confidence NUMERIC(5, 4),
    page_number INTEGER,
    metadata JSONB,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_ocr_results PRIMARY KEY (id),
    CONSTRAINT ck_ocr_results_metadata_object CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object'),
    CONSTRAINT ck_ocr_results_accepted_fields CHECK (status <> 'ACCEPTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)),
    CONSTRAINT ck_ocr_results_rejected_fields CHECK (status <> 'REJECTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)),
    CONSTRAINT ck_ocr_results_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REVIEW_REQUIRED', 'ACCEPTED', 'REJECTED')),
    CONSTRAINT ck_ocr_results_completed_text CHECK (status NOT IN ('COMPLETED', 'ACCEPTED', 'REVIEW_REQUIRED') OR text IS NOT NULL),
    CONSTRAINT ck_ocr_results_confidence_range CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT fk_ocr_results_file_asset_id_file_assets FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ocr_results_import_file_id_import_files FOREIGN KEY(import_file_id) REFERENCES import_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ocr_results_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_ocr_results_file_asset ON ocr_results (file_asset_id);

CREATE INDEX ix_ocr_results_import_file ON ocr_results (import_file_id);

CREATE INDEX ix_ocr_results_status ON ocr_results (status);

CREATE TABLE positions (
    tray_id UUID NOT NULL,
    code VARCHAR(32) NOT NULL,
    label VARCHAR(80) NOT NULL,
    status VARCHAR(16) DEFAULT 'AVAILABLE' NOT NULL,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_positions PRIMARY KEY (id),
    CONSTRAINT ck_positions_status CHECK (status IN ('AVAILABLE', 'BLOCKED', 'RETIRED')),
    CONSTRAINT ck_positions_code_not_empty CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_positions_label_not_empty CHECK (length(btrim(label)) > 0),
    CONSTRAINT fk_positions_tray_id_trays FOREIGN KEY(tray_id) REFERENCES trays (id) ON DELETE RESTRICT,
    CONSTRAINT uq_positions_tray_code UNIQUE (tray_id, code)
);

CREATE INDEX ix_positions_status ON positions (status);

CREATE INDEX ix_positions_tray_id ON positions (tray_id);

CREATE TABLE boxes (
    court_id UUID NOT NULL,
    year INTEGER NOT NULL,
    box_type VARCHAR(40) DEFAULT 'EXPEDIENTES' NOT NULL,
    visible_number VARCHAR(32) NOT NULL,
    numbering_policy_id UUID,
    description VARCHAR(500),
    confidentiality VARCHAR(16) DEFAULT 'INTERNAL' NOT NULL,
    lifecycle_status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    custody_status VARCHAR(24) DEFAULT 'UNKNOWN' NOT NULL,
    current_position_id UUID,
    location_precision VARCHAR(16) GENERATED ALWAYS AS (CASE WHEN current_position_id IS NULL THEN 'UNKNOWN' WHEN custody_status = 'IN_PLACE' THEN 'CONFIRMED' ELSE 'PENDING' END) STORED NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    archived_by UUID,
    archive_reason VARCHAR(500),
    voided_at TIMESTAMP WITH TIME ZONE,
    voided_by UUID,
    void_reason VARCHAR(500),
    destroyed_at TIMESTAMP WITH TIME ZONE,
    destroyed_by UUID,
    destruction_reason VARCHAR(500),
    created_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_boxes PRIMARY KEY (id),
    CONSTRAINT ck_boxes_custody_position CHECK (((custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') AND current_position_id IS NOT NULL) OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION') AND current_position_id IS NULL))),
    CONSTRAINT ck_boxes_box_type CHECK (box_type IN ('EXPEDIENTES', 'DOCUMENTOS_ADMINISTRATIVOS')),
    CONSTRAINT ck_boxes_confidentiality CHECK (confidentiality IN ('INTERNAL', 'RESTRICTED', 'CONFIDENTIAL')),
    CONSTRAINT ck_boxes_custody_status CHECK (custody_status IN ('IN_PLACE', 'ON_LOAN', 'IN_TRANSIT', 'MISSING', 'IN_RECONCILIATION', 'UNKNOWN')),
    CONSTRAINT ck_boxes_archived_at CHECK (lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL),
    CONSTRAINT ck_boxes_destroyed_without_position CHECK (lifecycle_status <> 'DESTROYED' OR current_position_id IS NULL),
    CONSTRAINT ck_boxes_destroyed_at CHECK (lifecycle_status <> 'DESTROYED' OR destroyed_at IS NOT NULL),
    CONSTRAINT ck_boxes_voided_at CHECK (lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL),
    CONSTRAINT ck_boxes_lifecycle_status CHECK (lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'VOIDED', 'DESTROYED')),
    CONSTRAINT ck_boxes_location_precision CHECK (location_precision IN ('CONFIRMED', 'PENDING', 'UNKNOWN')),
    CONSTRAINT ck_boxes_visible_number_not_empty CHECK (length(btrim(visible_number)) > 0),
    CONSTRAINT ck_boxes_year_range CHECK (year BETWEEN 1 AND 9999),
    CONSTRAINT fk_boxes_archived_by_users FOREIGN KEY(archived_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_court_id_courts FOREIGN KEY(court_id) REFERENCES courts (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_current_position_id_positions FOREIGN KEY(current_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_destroyed_by_users FOREIGN KEY(destroyed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_numbering_policy_id_numbering_policies FOREIGN KEY(numbering_policy_id) REFERENCES numbering_policies (id) ON DELETE RESTRICT,
    CONSTRAINT fk_boxes_voided_by_users FOREIGN KEY(voided_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_boxes_id_box_type UNIQUE (id, box_type),
    CONSTRAINT uq_boxes_visible_number UNIQUE (visible_number)
);

CREATE INDEX ix_boxes_court_year_type ON boxes (court_id, year, box_type);

CREATE INDEX ix_boxes_custody_status ON boxes (custody_status);

CREATE INDEX ix_boxes_lifecycle_status ON boxes (lifecycle_status);

CREATE UNIQUE INDEX uq_boxes_current_position_occupied ON boxes (current_position_id) WHERE custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') AND current_position_id IS NOT NULL;

CREATE TABLE position_blocks (
    shelf_id UUID NOT NULL,
    start_position_id UUID NOT NULL,
    end_position_id UUID NOT NULL,
    first_position_number INTEGER NOT NULL,
    last_position_number INTEGER NOT NULL,
    reason VARCHAR(500) NOT NULL,
    blocked_by UUID,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_position_blocks PRIMARY KEY (id),
    CONSTRAINT ck_position_blocks_cancel_after_creation CHECK (cancelled_at IS NULL OR cancelled_at >= created_at),
    CONSTRAINT ck_position_blocks_first_number CHECK (first_position_number > 0),
    CONSTRAINT ck_position_blocks_range CHECK (last_position_number >= first_position_number),
    CONSTRAINT ck_position_blocks_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT fk_position_blocks_blocked_by_users FOREIGN KEY(blocked_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_blocks_cancelled_by_users FOREIGN KEY(cancelled_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_blocks_end_position_id_positions FOREIGN KEY(end_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_blocks_shelf_id_shelves FOREIGN KEY(shelf_id) REFERENCES shelves (id) ON DELETE RESTRICT,
    CONSTRAINT fk_position_blocks_start_position_id_positions FOREIGN KEY(start_position_id) REFERENCES positions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_position_blocks_shelf_active ON position_blocks (shelf_id, start_position_id, end_position_id);

CREATE TABLE administrative_documents (
    box_id UUID NOT NULL,
    box_type VARCHAR(40) DEFAULT 'DOCUMENTOS_ADMINISTRATIVOS' NOT NULL,
    title VARCHAR(300) NOT NULL,
    document_type VARCHAR(80),
    document_year INTEGER NOT NULL,
    document_month INTEGER,
    document_day INTEGER,
    description VARCHAR(1000),
    verification_status VARCHAR(16) DEFAULT 'PENDING' NOT NULL,
    confidentiality VARCHAR(16) DEFAULT 'INTERNAL' NOT NULL,
    lifecycle_status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    source VARCHAR(32),
    notes VARCHAR(2000),
    created_by UUID,
    archived_at TIMESTAMP WITH TIME ZONE,
    archived_by UUID,
    archive_reason VARCHAR(500),
    voided_at TIMESTAMP WITH TIME ZONE,
    voided_by UUID,
    void_reason VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_administrative_documents PRIMARY KEY (id),
    CONSTRAINT ck_admin_documents_box_type_admin CHECK (box_type = 'DOCUMENTOS_ADMINISTRATIVOS'),
    CONSTRAINT ck_admin_documents_box_type CHECK (box_type IN ('EXPEDIENTES', 'DOCUMENTOS_ADMINISTRATIVOS')),
    CONSTRAINT ck_admin_documents_confidentiality CHECK (confidentiality IN ('INTERNAL', 'RESTRICTED', 'CONFIDENTIAL')),
    CONSTRAINT ck_admin_documents_archived_at CHECK (lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL),
    CONSTRAINT ck_admin_documents_voided_at CHECK (lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL),
    CONSTRAINT ck_admin_documents_lifecycle CHECK (lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'VOIDED', 'DESTROYED')),
    CONSTRAINT ck_admin_documents_verification CHECK (verification_status IN ('PENDING', 'CONFIRMED', 'CONFLICT')),
    CONSTRAINT ck_admin_documents_deleted_actor CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL),
    CONSTRAINT ck_admin_documents_day_range CHECK (document_day IS NULL OR document_day BETWEEN 1 AND 31),
    CONSTRAINT ck_admin_documents_day_requires_month CHECK (document_day IS NULL OR document_month IS NOT NULL),
    CONSTRAINT ck_admin_documents_month_range CHECK (document_month IS NULL OR document_month BETWEEN 1 AND 12),
    CONSTRAINT ck_admin_documents_year_range CHECK (document_year BETWEEN 1 AND 9999),
    CONSTRAINT ck_admin_documents_title_not_empty CHECK (length(btrim(title)) > 0),
    CONSTRAINT fk_administrative_documents_archived_by_users FOREIGN KEY(archived_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_administrative_documents_box_type FOREIGN KEY(box_id, box_type) REFERENCES boxes (id, box_type) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_administrative_documents_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_administrative_documents_deleted_by_users FOREIGN KEY(deleted_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_administrative_documents_voided_by_users FOREIGN KEY(voided_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_admin_documents_box_id ON administrative_documents (box_id);

CREATE INDEX ix_admin_documents_lifecycle ON administrative_documents (lifecycle_status);

CREATE INDEX ix_admin_documents_year ON administrative_documents (document_year);

CREATE TABLE box_labels (
    box_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    issued_by UUID,
    printed_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by UUID,
    revoke_reason VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_box_labels PRIMARY KEY (id),
    CONSTRAINT ck_box_labels_token_hash_not_empty CHECK (length(token_hash) > 0),
    CONSTRAINT ck_box_labels_revoked_after_issue CHECK (revoked_at IS NULL OR revoked_at >= issued_at),
    CONSTRAINT fk_box_labels_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_labels_issued_by_users FOREIGN KEY(issued_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_labels_revoked_by_users FOREIGN KEY(revoked_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_box_labels_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_box_labels_box_active ON box_labels (box_id) WHERE revoked_at IS NULL;

CREATE TABLE box_movements (
    box_id UUID NOT NULL,
    movement_type VARCHAR(24) NOT NULL,
    movement_status VARCHAR(16) DEFAULT 'PLANNED' NOT NULL,
    from_position_id UUID,
    to_position_id UUID,
    loan_id UUID,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    reason VARCHAR(500) NOT NULL,
    performed_by UUID,
    notes VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_box_movements PRIMARY KEY (id),
    CONSTRAINT ck_box_movements_cancelled_at CHECK (movement_status <> 'CANCELLED' OR cancelled_at IS NOT NULL),
    CONSTRAINT ck_box_movements_completed_at CHECK (movement_status <> 'COMPLETED' OR completed_at IS NOT NULL),
    CONSTRAINT ck_box_movements_status CHECK (movement_status IN ('PLANNED', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT ck_box_movements_type CHECK (movement_type IN ('ASSIGN', 'TRANSFER', 'RETURN', 'LOAN_PICKUP', 'LOAN_RETURN', 'RECONCILIATION')),
    CONSTRAINT ck_box_movements_position_change CHECK (from_position_id IS NULL OR to_position_id IS NULL OR from_position_id <> to_position_id),
    CONSTRAINT ck_box_movements_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT fk_box_movements_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_movements_from_position_id_positions FOREIGN KEY(from_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_movements_loan_id_loans FOREIGN KEY(loan_id) REFERENCES loans (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_movements_performed_by_users FOREIGN KEY(performed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_movements_to_position_id_positions FOREIGN KEY(to_position_id) REFERENCES positions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_box_movements_box ON box_movements (box_id, occurred_at);

CREATE INDEX ix_box_movements_status ON box_movements (movement_status);

CREATE TABLE box_number_history (
    box_id UUID NOT NULL,
    previous_number VARCHAR(32),
    new_number VARCHAR(32) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    changed_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_box_number_history PRIMARY KEY (id),
    CONSTRAINT ck_box_number_history_new_number_not_empty CHECK (length(btrim(new_number)) > 0),
    CONSTRAINT ck_box_number_history_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT ck_box_number_history_previous_number_not_empty CHECK (previous_number IS NULL OR length(btrim(previous_number)) > 0),
    CONSTRAINT ck_box_number_history_changed CHECK (previous_number IS NULL OR previous_number <> new_number),
    CONSTRAINT fk_box_number_history_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_box_number_history_changed_by_users FOREIGN KEY(changed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_box_number_history_box_id ON box_number_history (box_id, changed_at);

CREATE TABLE case_files (
    court_id UUID NOT NULL,
    box_id UUID,
    box_type VARCHAR(40) DEFAULT 'EXPEDIENTES' NOT NULL,
    nuc_raw VARCHAR(100) NOT NULL,
    nuc_normalized VARCHAR(100) NOT NULL,
    nuc_suffix5 VARCHAR(5) GENERATED ALWAYS AS (right(nuc_normalized, 5)) STORED NOT NULL,
    year INTEGER NOT NULL,
    entry_year INTEGER,
    entry_month INTEGER,
    entry_day INTEGER,
    entry_precision VARCHAR(16) DEFAULT 'UNKNOWN' NOT NULL,
    sentence_year INTEGER,
    sentence_month INTEGER,
    sentence_day INTEGER,
    sentence_precision VARCHAR(16) DEFAULT 'UNKNOWN' NOT NULL,
    resolution_type_id UUID,
    resolution_number VARCHAR(100),
    judge_name VARCHAR(200),
    court_name_raw VARCHAR(200),
    description VARCHAR(1000),
    verification_status VARCHAR(16) DEFAULT 'PENDING' NOT NULL,
    confidentiality VARCHAR(16) DEFAULT 'INTERNAL' NOT NULL,
    lifecycle_status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    source VARCHAR(32),
    notes VARCHAR(2000),
    created_by UUID,
    archived_at TIMESTAMP WITH TIME ZONE,
    archived_by UUID,
    archive_reason VARCHAR(500),
    voided_at TIMESTAMP WITH TIME ZONE,
    voided_by UUID,
    void_reason VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_case_files PRIMARY KEY (id),
    CONSTRAINT ck_case_files_entry_shape CHECK (((entry_precision = 'UNKNOWN' AND entry_year IS NULL AND entry_month IS NULL AND entry_day IS NULL) OR (entry_precision = 'YEAR' AND entry_year IS NOT NULL AND entry_month IS NULL AND entry_day IS NULL) OR (entry_precision = 'MONTH' AND entry_year IS NOT NULL AND entry_month IS NOT NULL AND entry_day IS NULL) OR (entry_precision = 'DAY' AND entry_year IS NOT NULL AND entry_month IS NOT NULL AND entry_day IS NOT NULL))),
    CONSTRAINT ck_case_files_sentence_shape CHECK (((sentence_precision = 'UNKNOWN' AND sentence_year IS NULL AND sentence_month IS NULL AND sentence_day IS NULL) OR (sentence_precision = 'YEAR' AND sentence_year IS NOT NULL AND sentence_month IS NULL AND sentence_day IS NULL) OR (sentence_precision = 'MONTH' AND sentence_year IS NOT NULL AND sentence_month IS NOT NULL AND sentence_day IS NULL) OR (sentence_precision = 'DAY' AND sentence_year IS NOT NULL AND sentence_month IS NOT NULL AND sentence_day IS NOT NULL))),
    CONSTRAINT ck_case_files_box_type_consistency CHECK (box_id IS NULL OR box_type = 'EXPEDIENTES'),
    CONSTRAINT ck_case_files_box_type_expedientes CHECK (box_type = 'EXPEDIENTES'),
    CONSTRAINT ck_case_files_box_type CHECK (box_type IN ('EXPEDIENTES', 'DOCUMENTOS_ADMINISTRATIVOS')),
    CONSTRAINT ck_case_files_confidentiality CHECK (confidentiality IN ('INTERNAL', 'RESTRICTED', 'CONFIDENTIAL')),
    CONSTRAINT ck_case_files_entry_precision CHECK (entry_precision IN ('UNKNOWN', 'YEAR', 'MONTH', 'DAY')),
    CONSTRAINT ck_case_files_archived_at CHECK (lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL),
    CONSTRAINT ck_case_files_voided_at CHECK (lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL),
    CONSTRAINT ck_case_files_lifecycle CHECK (lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'VOIDED', 'DESTROYED')),
    CONSTRAINT ck_case_files_sentence_precision CHECK (sentence_precision IN ('UNKNOWN', 'YEAR', 'MONTH', 'DAY')),
    CONSTRAINT ck_case_files_verification CHECK (verification_status IN ('PENDING', 'CONFIRMED', 'CONFLICT')),
    CONSTRAINT ck_case_files_entry_ranges CHECK ((entry_year IS NULL OR entry_year BETWEEN 1 AND 9999) AND (entry_month IS NULL OR entry_month BETWEEN 1 AND 12) AND (entry_day IS NULL OR entry_day BETWEEN 1 AND 31)),
    CONSTRAINT ck_case_files_sentence_ranges CHECK ((sentence_year IS NULL OR sentence_year BETWEEN 1 AND 9999) AND (sentence_month IS NULL OR sentence_month BETWEEN 1 AND 12) AND (sentence_day IS NULL OR sentence_day BETWEEN 1 AND 31)),
    CONSTRAINT ck_case_files_deleted_actor CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL),
    CONSTRAINT ck_case_files_nuc_normalized_not_empty CHECK (length(btrim(nuc_normalized)) > 0),
    CONSTRAINT ck_case_files_nuc_raw_not_empty CHECK (length(btrim(nuc_raw)) > 0),
    CONSTRAINT ck_case_files_year_range CHECK (year BETWEEN 1 AND 9999),
    CONSTRAINT fk_case_files_archived_by_users FOREIGN KEY(archived_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_files_box_type FOREIGN KEY(box_id, box_type) REFERENCES boxes (id, box_type) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_case_files_court_id_courts FOREIGN KEY(court_id) REFERENCES courts (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_files_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_files_deleted_by_users FOREIGN KEY(deleted_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_files_resolution_type_id_resolution_types FOREIGN KEY(resolution_type_id) REFERENCES resolution_types (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_files_voided_by_users FOREIGN KEY(voided_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_case_files_box_id ON case_files (box_id);

CREATE INDEX ix_case_files_court_nuc ON case_files (court_id, nuc_normalized);

CREATE INDEX ix_case_files_lifecycle ON case_files (lifecycle_status);

CREATE INDEX ix_case_files_nuc_suffix5 ON case_files (nuc_suffix5);

CREATE INDEX ix_case_files_verification ON case_files (verification_status);

CREATE INDEX ix_case_files_year ON case_files (year);

CREATE TABLE inventory_sessions (
    code VARCHAR(64) NOT NULL,
    scope_type VARCHAR(24) NOT NULL,
    area_id UUID,
    shelf_id UUID,
    tray_id UUID,
    start_position_id UUID,
    end_position_id UUID,
    box_id UUID,
    status VARCHAR(16) DEFAULT 'DRAFT' NOT NULL,
    responsible_id UUID NOT NULL,
    expected_count INTEGER DEFAULT 0 NOT NULL,
    scanned_count INTEGER DEFAULT 0 NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    closed_by UUID,
    summary JSONB,
    notes VARCHAR(2000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_inventory_sessions PRIMARY KEY (id),
    CONSTRAINT ck_inventory_sessions_scope_columns CHECK (((scope_type = 'AREA' AND area_id IS NOT NULL AND shelf_id IS NULL AND tray_id IS NULL AND start_position_id IS NULL AND end_position_id IS NULL AND box_id IS NULL) OR (scope_type = 'SHELF' AND area_id IS NULL AND shelf_id IS NOT NULL AND tray_id IS NULL AND start_position_id IS NULL AND end_position_id IS NULL AND box_id IS NULL) OR (scope_type = 'TRAY' AND area_id IS NULL AND shelf_id IS NULL AND tray_id IS NOT NULL AND start_position_id IS NULL AND end_position_id IS NULL AND box_id IS NULL) OR (scope_type = 'POSITION_RANGE' AND area_id IS NULL AND shelf_id IS NULL AND tray_id IS NULL AND start_position_id IS NOT NULL AND end_position_id IS NOT NULL AND box_id IS NULL) OR (scope_type = 'BOX' AND area_id IS NULL AND shelf_id IS NULL AND tray_id IS NULL AND start_position_id IS NULL AND end_position_id IS NULL AND box_id IS NOT NULL))),
    CONSTRAINT ck_inventory_sessions_scope_type CHECK (scope_type IN ('AREA', 'SHELF', 'TRAY', 'POSITION_RANGE', 'BOX')),
    CONSTRAINT ck_inventory_sessions_closed_at CHECK (status <> 'CLOSED' OR closed_at IS NOT NULL),
    CONSTRAINT ck_inventory_sessions_status CHECK (status IN ('DRAFT', 'IN_PROGRESS', 'PAUSED', 'CLOSED', 'CANCELLED')),
    CONSTRAINT ck_inventory_sessions_summary_object CHECK (summary IS NULL OR jsonb_typeof(summary) = 'object'),
    CONSTRAINT ck_inventory_sessions_code_not_empty CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_inventory_sessions_counts CHECK (scanned_count >= 0 AND expected_count >= 0),
    CONSTRAINT fk_inventory_sessions_area_id_areas FOREIGN KEY(area_id) REFERENCES areas (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_closed_by_users FOREIGN KEY(closed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_end_position_id_positions FOREIGN KEY(end_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_responsible_id_users FOREIGN KEY(responsible_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_shelf_id_shelves FOREIGN KEY(shelf_id) REFERENCES shelves (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_start_position_id_positions FOREIGN KEY(start_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_sessions_tray_id_trays FOREIGN KEY(tray_id) REFERENCES trays (id) ON DELETE RESTRICT,
    CONSTRAINT uq_inventory_sessions_code UNIQUE (code)
);

CREATE INDEX ix_inventory_sessions_scope ON inventory_sessions (scope_type);

CREATE INDEX ix_inventory_sessions_status ON inventory_sessions (status);

CREATE TABLE case_file_identifier_history (
    case_file_id UUID NOT NULL,
    identifier_kind VARCHAR(32) NOT NULL,
    value_raw VARCHAR(100) NOT NULL,
    value_normalized VARCHAR(100) NOT NULL,
    is_primary BOOLEAN DEFAULT false NOT NULL,
    reason VARCHAR(500) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    changed_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_case_file_identifier_history PRIMARY KEY (id),
    CONSTRAINT ck_case_identifier_kind CHECK (identifier_kind IN ('NUC', 'PROCESS_NUMBER', 'SENTENCE')),
    CONSTRAINT ck_case_identifier_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT ck_case_identifier_normalized_not_empty CHECK (length(btrim(value_normalized)) > 0),
    CONSTRAINT ck_case_identifier_raw_not_empty CHECK (length(btrim(value_raw)) > 0),
    CONSTRAINT fk_case_file_identifier_history_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_file_identifier_history_changed_by_users FOREIGN KEY(changed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_case_file_identifier_case ON case_file_identifier_history (case_file_id, changed_at);

CREATE INDEX ix_case_file_identifier_lookup ON case_file_identifier_history (identifier_kind, value_normalized);

CREATE TABLE case_parties (
    case_file_id UUID NOT NULL,
    person_id UUID NOT NULL,
    party_role_id UUID NOT NULL,
    is_primary BOOLEAN DEFAULT false NOT NULL,
    notes VARCHAR(1000),
    created_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_case_parties PRIMARY KEY (id),
    CONSTRAINT ck_case_parties_notes_not_blank CHECK (length(btrim(notes)) > 0 OR notes IS NULL),
    CONSTRAINT fk_case_parties_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE CASCADE,
    CONSTRAINT fk_case_parties_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_parties_party_role_id_party_roles FOREIGN KEY(party_role_id) REFERENCES party_roles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_parties_person_id_persons FOREIGN KEY(person_id) REFERENCES persons (id) ON DELETE RESTRICT
);

CREATE INDEX ix_case_parties_case_file_id ON case_parties (case_file_id);

CREATE INDEX ix_case_parties_person_id ON case_parties (person_id);

CREATE TABLE deletion_requests (
    target_type VARCHAR(16) NOT NULL,
    box_id UUID,
    case_file_id UUID,
    file_asset_id UUID,
    status VARCHAR(24) DEFAULT 'REQUESTED' NOT NULL,
    reason VARCHAR(1000) NOT NULL,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    executed_by UUID,
    executed_at TIMESTAMP WITH TIME ZONE,
    evidence_file_id UUID,
    execution_result JSONB,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID,
    rejection_reason VARCHAR(1000),
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID,
    cancellation_reason VARCHAR(1000),
    notes VARCHAR(2000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_deletion_requests PRIMARY KEY (id),
    CONSTRAINT ck_deletion_requests_one_target CHECK (((target_type = 'BOX' AND box_id IS NOT NULL AND case_file_id IS NULL AND file_asset_id IS NULL) OR (target_type = 'CASE_FILE' AND box_id IS NULL AND case_file_id IS NOT NULL AND file_asset_id IS NULL) OR (target_type = 'FILE_ASSET' AND box_id IS NULL AND case_file_id IS NULL AND file_asset_id IS NOT NULL))),
    CONSTRAINT ck_deletion_requests_result_object CHECK (execution_result IS NULL OR jsonb_typeof(execution_result) = 'object'),
    CONSTRAINT ck_deletion_requests_cancellation_fields CHECK (status <> 'CANCELLED' OR (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL AND cancellation_reason IS NOT NULL AND length(btrim(cancellation_reason)) > 0)),
    CONSTRAINT ck_deletion_requests_completion_fields CHECK (status <> 'COMPLETED' OR (executed_at IS NOT NULL AND executed_by IS NOT NULL AND evidence_file_id IS NOT NULL)),
    CONSTRAINT ck_deletion_requests_rejection_fields CHECK (status <> 'REJECTED' OR (rejected_at IS NOT NULL AND rejected_by IS NOT NULL AND rejection_reason IS NOT NULL AND length(btrim(rejection_reason)) > 0)),
    CONSTRAINT ck_deletion_requests_status CHECK (status IN ('REQUESTED', 'UNDER_REVIEW', 'REJECTED', 'APPROVED', 'SCHEDULED', 'EXECUTING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    CONSTRAINT ck_deletion_requests_approval_fields CHECK (status NOT IN ('APPROVED', 'SCHEDULED', 'EXECUTING', 'COMPLETED') OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)),
    CONSTRAINT ck_deletion_requests_review_fields CHECK (status NOT IN ('UNDER_REVIEW', 'APPROVED', 'SCHEDULED', 'EXECUTING', 'COMPLETED', 'FAILED') OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)),
    CONSTRAINT ck_deletion_requests_target_type CHECK (target_type IN ('BOX', 'CASE_FILE', 'FILE_ASSET')),
    CONSTRAINT ck_deletion_requests_approver_separation CHECK (approved_by IS NULL OR approved_by <> requested_by),
    CONSTRAINT ck_deletion_requests_execution_after_approval CHECK (executed_at IS NULL OR approved_at IS NULL OR executed_at >= approved_at),
    CONSTRAINT ck_deletion_requests_executor_separation CHECK (executed_by IS NULL OR executed_by <> requested_by),
    CONSTRAINT ck_deletion_requests_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT fk_deletion_requests_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_cancelled_by_users FOREIGN KEY(cancelled_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_evidence_file_id_file_assets FOREIGN KEY(evidence_file_id) REFERENCES file_assets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_executed_by_users FOREIGN KEY(executed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_file_asset_id_file_assets FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_rejected_by_users FOREIGN KEY(rejected_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_requested_by_users FOREIGN KEY(requested_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deletion_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_deletion_requests_box_active ON deletion_requests (box_id) WHERE box_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED');

CREATE INDEX ix_deletion_requests_case_active ON deletion_requests (case_file_id) WHERE case_file_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED');

CREATE INDEX ix_deletion_requests_file_active ON deletion_requests (file_asset_id) WHERE file_asset_id IS NOT NULL AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED');

CREATE INDEX ix_deletion_requests_status ON deletion_requests (status);

CREATE TABLE file_attachments (
    file_asset_id UUID NOT NULL,
    case_file_id UUID,
    administrative_document_id UUID,
    link_kind VARCHAR(16) NOT NULL,
    is_primary BOOLEAN DEFAULT false NOT NULL,
    created_by UUID,
    detached_at TIMESTAMP WITH TIME ZONE,
    detached_by UUID,
    detached_reason VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_file_attachments PRIMARY KEY (id),
    CONSTRAINT ck_file_attachments_link_kind CHECK (link_kind IN ('PRIMARY', 'ANNEX', 'SOURCE', 'EVIDENCE')),
    CONSTRAINT ck_file_attachments_one_target CHECK (((case_file_id IS NOT NULL AND administrative_document_id IS NULL) OR (case_file_id IS NULL AND administrative_document_id IS NOT NULL))),
    CONSTRAINT ck_file_attachments_detached_reason CHECK (detached_at IS NULL OR (detached_reason IS NOT NULL AND length(btrim(detached_reason)) > 0)),
    CONSTRAINT ck_file_attachments_primary_not_detached CHECK (is_primary = false OR detached_at IS NULL),
    CONSTRAINT fk_file_attachments_administrative_document_id_administ_f13e FOREIGN KEY(administrative_document_id) REFERENCES administrative_documents (id) ON DELETE RESTRICT,
    CONSTRAINT fk_file_attachments_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_file_attachments_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_file_attachments_detached_by_users FOREIGN KEY(detached_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_file_attachments_file_asset_id_file_assets FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
);

CREATE INDEX ix_file_attachments_admin_document ON file_attachments (administrative_document_id);

CREATE INDEX ix_file_attachments_case_file ON file_attachments (case_file_id);

CREATE INDEX ix_file_attachments_file_asset ON file_attachments (file_asset_id);

CREATE UNIQUE INDEX uq_file_attachments_admin_primary ON file_attachments (administrative_document_id) WHERE is_primary AND detached_at IS NULL AND administrative_document_id IS NOT NULL;

CREATE UNIQUE INDEX uq_file_attachments_case_primary ON file_attachments (case_file_id) WHERE is_primary AND detached_at IS NULL AND case_file_id IS NOT NULL;

CREATE TABLE import_rows (
    batch_id UUID NOT NULL,
    import_file_id UUID NOT NULL,
    row_number INTEGER NOT NULL,
    raw_data JSONB,
    normalized_data JSONB,
    status VARCHAR(16) DEFAULT 'PENDING' NOT NULL,
    errors JSONB,
    warnings JSONB,
    target_box_id UUID,
    target_case_file_id UUID,
    target_administrative_document_id UUID,
    reviewed_by UUID,
    applied_at TIMESTAMP WITH TIME ZONE,
    applied_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_import_rows PRIMARY KEY (id),
    CONSTRAINT ck_import_rows_errors_array CHECK (errors IS NULL OR jsonb_typeof(errors) = 'array'),
    CONSTRAINT ck_import_rows_normalized_object CHECK (normalized_data IS NULL OR jsonb_typeof(normalized_data) = 'object'),
    CONSTRAINT ck_import_rows_raw_object CHECK (raw_data IS NULL OR jsonb_typeof(raw_data) = 'object'),
    CONSTRAINT ck_import_rows_applied_target CHECK (status <> 'APPLIED' OR ((target_box_id IS NOT NULL)::int + (target_case_file_id IS NOT NULL)::int + (target_administrative_document_id IS NOT NULL)::int) = 1),
    CONSTRAINT ck_import_rows_applied_fields CHECK (status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)),
    CONSTRAINT ck_import_rows_error_details CHECK (status <> 'ERROR' OR errors IS NOT NULL),
    CONSTRAINT ck_import_rows_status CHECK (status IN ('PENDING', 'PARSED', 'VALID', 'WARNING', 'ERROR', 'APPROVED', 'APPLIED', 'SKIPPED')),
    CONSTRAINT ck_import_rows_warnings_array CHECK (warnings IS NULL OR jsonb_typeof(warnings) = 'array'),
    CONSTRAINT ck_import_rows_at_most_one_target CHECK (((target_box_id IS NOT NULL)::int + (target_case_file_id IS NOT NULL)::int + (target_administrative_document_id IS NOT NULL)::int) <= 1),
    CONSTRAINT ck_import_rows_row_number CHECK (row_number > 0),
    CONSTRAINT fk_import_rows_applied_by_users FOREIGN KEY(applied_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_rows_file_batch FOREIGN KEY(import_file_id, batch_id) REFERENCES import_files (id, batch_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_import_rows_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_rows_target_administrative_document_id_admini_35c9 FOREIGN KEY(target_administrative_document_id) REFERENCES administrative_documents (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_rows_target_box_id_boxes FOREIGN KEY(target_box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_import_rows_target_case_file_id_case_files FOREIGN KEY(target_case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT uq_import_rows_file_row UNIQUE (import_file_id, row_number)
);

CREATE INDEX ix_import_rows_batch_id ON import_rows (batch_id);

CREATE INDEX ix_import_rows_import_file_id ON import_rows (import_file_id);

CREATE INDEX ix_import_rows_status ON import_rows (status);

CREATE TABLE inventory_findings (
    session_id UUID NOT NULL,
    finding_type VARCHAR(32) NOT NULL,
    finding_status VARCHAR(24) DEFAULT 'OPEN' NOT NULL,
    box_id UUID,
    expected_position_id UUID,
    observed_position_id UUID,
    expected_data JSONB,
    observed_data JSONB,
    resolution VARCHAR(1000),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID,
    created_by UUID,
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_inventory_findings PRIMARY KEY (id),
    CONSTRAINT ck_inventory_findings_expected_object CHECK (expected_data IS NULL OR jsonb_typeof(expected_data) = 'object'),
    CONSTRAINT ck_inventory_findings_status CHECK (finding_status IN ('OPEN', 'RESOLVED', 'ACCEPTED_DIFFERENCE', 'ESCALATED')),
    CONSTRAINT ck_inventory_findings_resolution_fields CHECK (finding_status NOT IN ('RESOLVED', 'ACCEPTED_DIFFERENCE') OR (resolution IS NOT NULL AND length(btrim(resolution)) > 0 AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)),
    CONSTRAINT ck_inventory_findings_type CHECK (finding_type IN ('MISSING_BOX', 'UNEXPECTED_BOX', 'WRONG_LOCATION', 'UNREGISTERED_BOX', 'DUPLICATE', 'OTHER')),
    CONSTRAINT ck_inventory_findings_observed_object CHECK (observed_data IS NULL OR jsonb_typeof(observed_data) = 'object'),
    CONSTRAINT fk_inventory_findings_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_findings_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_findings_expected_position_id_positions FOREIGN KEY(expected_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_findings_observed_position_id_positions FOREIGN KEY(observed_position_id) REFERENCES positions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_findings_resolved_by_users FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_findings_session_id_inventory_sessions FOREIGN KEY(session_id) REFERENCES inventory_sessions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_inventory_findings_box ON inventory_findings (box_id);

CREATE INDEX ix_inventory_findings_session ON inventory_findings (session_id, finding_status);

CREATE TABLE legal_holds (
    target_type VARCHAR(16) NOT NULL,
    box_id UUID,
    case_file_id UUID,
    file_asset_id UUID,
    reason VARCHAR(1000) NOT NULL,
    legal_basis VARCHAR(1000),
    status VARCHAR(16) DEFAULT 'ACTIVE' NOT NULL,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL,
    released_at TIMESTAMP WITH TIME ZONE,
    released_by UUID,
    release_reason VARCHAR(1000),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT pk_legal_holds PRIMARY KEY (id),
    CONSTRAINT ck_legal_holds_one_target CHECK (((target_type = 'BOX' AND box_id IS NOT NULL AND case_file_id IS NULL AND file_asset_id IS NULL) OR (target_type = 'CASE_FILE' AND box_id IS NULL AND case_file_id IS NOT NULL AND file_asset_id IS NULL) OR (target_type = 'FILE_ASSET' AND box_id IS NULL AND case_file_id IS NULL AND file_asset_id IS NOT NULL))),
    CONSTRAINT ck_legal_holds_release_fields CHECK (status <> 'RELEASED' OR (released_at IS NOT NULL AND released_by IS NOT NULL AND release_reason IS NOT NULL AND length(btrim(release_reason)) > 0)),
    CONSTRAINT ck_legal_holds_status CHECK (status IN ('ACTIVE', 'RELEASED')),
    CONSTRAINT ck_legal_holds_target_type CHECK (target_type IN ('BOX', 'CASE_FILE', 'FILE_ASSET')),
    CONSTRAINT ck_legal_holds_effective_range CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_legal_holds_reason_not_empty CHECK (length(btrim(reason)) > 0),
    CONSTRAINT fk_legal_holds_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_legal_holds_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_legal_holds_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_legal_holds_file_asset_id_file_assets FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_legal_holds_released_by_users FOREIGN KEY(released_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_legal_holds_box_active ON legal_holds (box_id) WHERE status = 'ACTIVE' AND box_id IS NOT NULL;

CREATE INDEX ix_legal_holds_case_active ON legal_holds (case_file_id) WHERE status = 'ACTIVE' AND case_file_id IS NOT NULL;

CREATE INDEX ix_legal_holds_file_active ON legal_holds (file_asset_id) WHERE status = 'ACTIVE' AND file_asset_id IS NOT NULL;

CREATE TABLE loan_items (
    loan_id UUID NOT NULL,
    box_id UUID,
    case_file_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    released_at TIMESTAMP WITH TIME ZONE,
    release_reason VARCHAR(500),
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT pk_loan_items PRIMARY KEY (id),
    CONSTRAINT ck_loan_items_one_target CHECK (((box_id IS NOT NULL AND case_file_id IS NULL) OR (box_id IS NULL AND case_file_id IS NOT NULL))),
    CONSTRAINT ck_loan_items_release_reason CHECK (released_at IS NULL OR (release_reason IS NOT NULL AND length(btrim(release_reason)) > 0)),
    CONSTRAINT ck_loan_items_release_after_creation CHECK (released_at IS NULL OR released_at >= created_at),
    CONSTRAINT fk_loan_items_box_id_boxes FOREIGN KEY(box_id) REFERENCES boxes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loan_items_case_file_id_case_files FOREIGN KEY(case_file_id) REFERENCES case_files (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loan_items_loan_id_loans FOREIGN KEY(loan_id) REFERENCES loans (id) ON DELETE RESTRICT
);

CREATE INDEX ix_loan_items_loan_id ON loan_items (loan_id);

CREATE UNIQUE INDEX uq_loan_items_open_box ON loan_items (box_id) WHERE released_at IS NULL AND box_id IS NOT NULL;

CREATE UNIQUE INDEX uq_loan_items_open_case ON loan_items (case_file_id) WHERE released_at IS NULL AND case_file_id IS NOT NULL;

CREATE SEQUENCE box_visible_number_seq AS BIGINT INCREMENT BY 1 MINVALUE 1 START WITH 4402 CACHE 1 NO CYCLE;

CREATE OR REPLACE FUNCTION sga_set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$;;

CREATE OR REPLACE FUNCTION sga_audit_append_only
        ()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events es append-only'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;;

CREATE OR REPLACE FUNCTION
        sga_guard_box_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.box_type IS DISTINCT FROM NEW.box_type
               OR OLD.court_id IS DISTINCT FROM NEW.court_id
               OR OLD.year IS DISTINCT FROM NEW.year
            THEN
                IF EXISTS (SELECT 1 FROM case_files WHERE box_id = OLD.id)
                   OR EXISTS (
                       SELECT 1 FROM administrative_documents
                       WHERE box_id = OLD.id
                   )
                THEN
                    RAISE EXCEPTION
                        'No se puede cambiar tribunal, año o tipo de una caja con contenido'
                        USING ERRCODE = 'integrity_constraint_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;;

CREATE TRIGGER trg_roles _set_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_permissions _set_updated_at BEFORE UPDATE ON permissions FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_users _set_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_courts _set_updated_at BEFORE UPDATE ON courts FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_identifier_format_profiles _set_updated_at BEFORE UPDATE ON identifier_format_profiles FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_resolution_types _set_updated_at BEFORE UPDATE ON resolution_types FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_numbering_policies _set_updated_at BEFORE UPDATE ON numbering_policies FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_retention_policies _set_updated_at BEFORE UPDATE ON retention_policies FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_system_settings _set_updated_at BEFORE UPDATE ON system_settings FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_party_roles _set_updated_at BEFORE UPDATE ON party_roles FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_areas _set_updated_at BEFORE UPDATE ON areas FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_shelves _set_updated_at BEFORE UPDATE ON shelves FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_trays _set_updated_at BEFORE UPDATE ON trays FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_positions _set_updated_at BEFORE UPDATE ON positions FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_position_blocks _set_updated_at BEFORE UPDATE ON position_blocks FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_boxes _set_updated_at BEFORE UPDATE ON boxes FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_box_movements _set_updated_at BEFORE UPDATE ON box_movements FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_case_files _set_updated_at BEFORE UPDATE ON case_files FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_persons _set_updated_at BEFORE UPDATE ON persons FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_case_parties _set_updated_at BEFORE UPDATE ON case_parties FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_administrative_documents _set_updated_at BEFORE UPDATE ON administrative_documents FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_file_assets _set_updated_at BEFORE UPDATE ON file_assets FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_file_attachments _set_updated_at BEFORE UPDATE ON file_attachments FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_import_batches _set_updated_at BEFORE UPDATE ON import_batches FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_import_files _set_updated_at BEFORE UPDATE ON import_files FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_ocr_results _set_updated_at BEFORE UPDATE ON ocr_results FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_task_jobs _set_updated_at BEFORE UPDATE ON task_jobs FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_loans _set_updated_at BEFORE UPDATE ON loans FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_inventory_sessions _set_updated_at BEFORE UPDATE ON inventory_sessions FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_inventory_findings _set_updated_at BEFORE UPDATE ON inventory_findings FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_legal_holds _set_updated_at BEFORE UPDATE ON legal_holds FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_deletion_requests _set_updated_at BEFORE UPDATE ON deletion_requests FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at();

CREATE TRIGGER trg_audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION sga_audit_append_only();

CREATE TRIGGER trg_audit_events_no_truncate BEFORE TRUNCATE ON audit_events FOR EACH STATEMENT EXECUTE FUNCTION sga_audit_append_only();

CREATE TRIGGER trg_boxes_identity_guard BEFORE UPDATE ON boxes FOR EACH ROW EXECUTE FUNCTION sga_guard_box_identity();

INSERT INTO alembic_version (version_num) VALUES ('20261026_0001') RETURNING alembic_version.version_num;

COMMIT;
