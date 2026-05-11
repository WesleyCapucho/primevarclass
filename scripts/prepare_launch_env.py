from __future__ import annotations

import argparse
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"


def build_env_text(*, cors_origins: str, job_root: str) -> str:
    api_key = secrets.token_urlsafe(48)
    return "\n".join(
        [
            "# PrimeVarClass production/staging environment.",
            "# Keep this file private. It is intentionally ignored by git.",
            f"PRIMEVARCLASS_API_KEY={api_key}",
            f"PRIMEVARCLASS_JOB_ROOT={job_root}",
            f"PRIMEVARCLASS_CORS_ORIGINS={cors_origins}",
            f"PRIMEVARCLASS_AUDIT_ROOT={job_root}",
            f"PRIMEVARCLASS_PROFILE_ROOT={job_root}",
            f"PRIMEVARCLASS_TEAM_ROOT={job_root}",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a private .env file for PrimeVarClass launch.")
    parser.add_argument("--output", default=str(DEFAULT_ENV_PATH), help="Destination env file. Defaults to .env.")
    parser.add_argument("--cors-origins", default="", help="Comma-separated public frontend origins.")
    parser.add_argument("--job-root", default="/app/primevarclass_job_history", help="Persistent job/audit root.")
    parser.add_argument("--force", action="store_true", help="Overwrite the destination if it already exists.")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.force:
        print(f"{output_path} already exists; use --force only if you want to rotate the launch key.")
        return 2

    output_path.write_text(
        build_env_text(cors_origins=args.cors_origins.strip(), job_root=args.job_root.strip()),
        encoding="utf-8",
    )
    print(f"Private launch env written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
