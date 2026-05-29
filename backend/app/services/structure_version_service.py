"""Structure version persistence, validation, and confirmation logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.task_record import TaskRecordModel

from .grid_builder import build_sheet_payload, with_header_parsing


# ---------------------------------------------------------------------------
# Version lookup helpers
# ---------------------------------------------------------------------------

def preferred_structure_version(task: TaskRecordModel) -> StructureVersionRecordModel | None:
    """Return the confirmed version with the highest number, or the latest
    version when nothing has been confirmed yet."""
    if not task.structure_versions:
        return None

    confirmed_versions = [v for v in task.structure_versions if v.is_confirmed]
    if confirmed_versions:
        return max(confirmed_versions, key=lambda item: item.version_number)

    return max(task.structure_versions, key=lambda item: item.version_number)


def latest_structure_version(task: TaskRecordModel) -> StructureVersionRecordModel | None:
    """Return the most recent structure version regardless of confirmation."""
    if not task.structure_versions:
        return None

    return max(task.structure_versions, key=lambda item: item.version_number)


# ---------------------------------------------------------------------------
# Snapshot application
# ---------------------------------------------------------------------------

def apply_structure_version(
    sheets_payload: list[dict[str, object]],
    structure_version: StructureVersionRecordModel,
) -> list[dict[str, object]]:
    """Overlay a saved structure version onto the parsed sheet payloads."""
    snapshot_sheets = structure_version.snapshot_json["sheets"]
    snapshot_by_sheet_id = {sheet["sheet_id"]: sheet for sheet in snapshot_sheets}
    updated_payload: list[dict[str, object]] = []

    for sheet_payload in sheets_payload:
        snapshot_sheet = snapshot_by_sheet_id.get(sheet_payload["sheet_id"])
        if snapshot_sheet is None:
            updated_payload.append(sheet_payload)
            continue

        updated_payload.append(
            with_header_parsing(
                {
                    **sheet_payload,
                    "merge_ranges": snapshot_sheet["merge_ranges"],
                    "aligned_grid": snapshot_sheet["aligned_grid"],
                    "aligned_cell_roles": snapshot_sheet["aligned_cell_roles"],
                    "aligned_source_map": snapshot_sheet["aligned_source_map"],
                    "cell_tags": snapshot_sheet["cell_tags"],
                }
            )
        )

    return updated_payload


# ---------------------------------------------------------------------------
# Patch diffing
# ---------------------------------------------------------------------------

def _count_changed_cells(
    base_sheet: dict[str, object],
    new_sheet: dict[str, object],
) -> int:
    changed_cell_count = 0
    row_count = int(new_sheet["row_count"])
    col_count = int(new_sheet["col_count"])

    base_grid = base_sheet["aligned_grid"]
    base_roles = base_sheet["aligned_cell_roles"]
    base_source_map = base_sheet["aligned_source_map"]
    base_tags = base_sheet["cell_tags"]

    new_grid = new_sheet["aligned_grid"]
    new_roles = new_sheet["aligned_cell_roles"]
    new_source_map = new_sheet["aligned_source_map"]
    new_tags = new_sheet["cell_tags"]

    for row_index in range(row_count):
        for col_index in range(col_count):
            if (
                base_grid[row_index][col_index] != new_grid[row_index][col_index]
                or base_roles[row_index][col_index] != new_roles[row_index][col_index]
                or base_source_map[row_index][col_index] != new_source_map[row_index][col_index]
                or base_tags[row_index][col_index] != new_tags[row_index][col_index]
            ):
                changed_cell_count += 1

    return changed_cell_count


def build_patch_summary(
    base_sheets: list[dict[str, object]],
    new_sheets: list[dict[str, object]],
) -> dict[str, object]:
    """Compute which sheets and cells changed between two payload snapshots."""
    base_by_sheet_id = {sheet["sheet_id"]: sheet for sheet in base_sheets}
    changed_sheet_ids: list[int] = []
    changed_cell_count = 0

    for new_sheet in new_sheets:
        base_sheet = base_by_sheet_id.get(new_sheet["sheet_id"])
        if base_sheet is None:
            changed_sheet_ids.append(int(new_sheet["sheet_id"]))
            changed_cell_count += int(new_sheet["row_count"]) * int(new_sheet["col_count"])
            continue

        sheet_changed_cells = _count_changed_cells(base_sheet, new_sheet)
        if base_sheet["merge_ranges"] != new_sheet["merge_ranges"] or sheet_changed_cells > 0:
            changed_sheet_ids.append(int(new_sheet["sheet_id"]))
            changed_cell_count += sheet_changed_cells

    return {
        "sheet_count": len(new_sheets),
        "changed_sheet_ids": changed_sheet_ids,
        "changed_cell_count": changed_cell_count,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_structure_version_payload(
    parsed_sheets: list[dict[str, object]],
    request_sheets: list[dict[str, object]],
) -> None:
    """Raise 400 when the request sheets don't match the parsed task sheets."""
    parsed_by_sheet_id = {int(sheet["sheet_id"]): sheet for sheet in parsed_sheets}
    request_sheet_ids = {int(sheet["sheet_id"]) for sheet in request_sheets}

    if request_sheet_ids != set(parsed_by_sheet_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Structure version sheets do not match parsed task sheets",
        )

    for request_sheet in request_sheets:
        parsed_sheet = parsed_by_sheet_id[int(request_sheet["sheet_id"])]
        row_count = int(request_sheet["row_count"])
        col_count = int(request_sheet["col_count"])
        if row_count != int(parsed_sheet["row_count"]) or col_count != int(parsed_sheet["col_count"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Structure version dimensions do not match parsed task sheets",
            )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def save_structure_version(
    task: TaskRecordModel,
    base_structure_version: int,
    request_sheets: list[dict[str, object]],
    db: Session,
) -> dict[str, object]:
    """Persist a new immutable structure version snapshot."""
    sv_latest = latest_structure_version(task)
    current_editable_version = sv_latest.version_number if sv_latest else 0
    base_sheets = [
        build_sheet_payload(sheet) for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]
    if sv_latest is not None:
        base_sheets = apply_structure_version(base_sheets, sv_latest)

    if current_editable_version != base_structure_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Structure version is out of date",
        )

    validate_structure_version_payload(base_sheets, request_sheets)

    next_version_number = base_structure_version + 1
    patch_summary = build_patch_summary(base_sheets, request_sheets)
    enriched_sheets = [with_header_parsing(dict(s)) for s in request_sheets]
    structure_version = StructureVersionRecordModel(
        task_id=task.id,
        version_number=next_version_number,
        snapshot_json={"sheets": enriched_sheets},
        patch_summary_json=patch_summary,
        is_confirmed=False,
    )
    db.add(structure_version)
    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": next_version_number,
        "patch_summary": patch_summary,
    }


def confirm_structure_version(
    task: TaskRecordModel,
    structure_version: int,
    db: Session,
) -> dict[str, object]:
    """Mark a structure version as confirmed and advance task status."""
    target_version = next(
        (
            version
            for version in task.structure_versions
            if version.version_number == structure_version
        ),
        None,
    )
    if target_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure version not found",
        )

    for version in task.structure_versions:
        version.is_confirmed = version.version_number == structure_version

    task.status = "confirmed"
    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": structure_version,
        "confirmed_structure_version": structure_version,
    }
