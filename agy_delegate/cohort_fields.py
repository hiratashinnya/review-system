"""校正済み cohort protocol 1 の閉じたフィールド集合。"""

PROOF_FIELDS = {"protocol", "created_utc", "expires_utc", "generator_source_sha256",
                "binding", "files", "observations", "account_scope"}
BINDING_HASHES = {"os_sha256", "user_home_sha256", "workspace_wsl_sha256",
                  "workspace_native_sha256", "executable_path_sha256", "executable_sha256"}
BINDING_ENUMS = {"cli_version": "1.4.8", "project_selector": "default-cli-project",
                 "argv_profile": "explicit-project-json-duration-v1"}
OBSERVATIONS = {"global_template_match", "explicit_selector_verified", "project_scope_empty",
                "shared_scope_empty", "relative_cwd_witness", "update_disabled_for_child",
                "admin_gateway_candidate_absent"}
FILE_FIELDS = {"exists", "sha256", "acl_sha256", "owner_sha256"}
MAX_FILE_BYTES = 65536
