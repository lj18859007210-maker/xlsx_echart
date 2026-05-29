"""Structure version persistence with compressed diff snapshots.

Dirty-row format (new, compact):
  {
    "base_version": 3,
    "changed_sheets": [{
      "sheet_id": 1,
      "dirty_rows": {"5": {"grid": [...], "roles": [...], "source_map": [...], "tags": [...]}},
      "merge_ranges": [...],
    }]
  }

Full-sheet format (legacy, for backward compatibility):
  {"sheets": [{ "sheet_id": 1, "aligned_grid": [[...]], ...}]}
"""

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

def _is_legacy_snapshot(snapshot_json: dict[str, object]) -> bool:
    """Return True when snapshot_json uses the old full-sheet format."""
    return "sheets" in snapshot_json


def _apply_compressed_snapshot(
    sheets_payload: list[dict[str, object]],
    snapshot_json: dict[str, object],
    db: Session,
) -> list[dict[str, object]]:
    """Apply a compressed (dirty-row) snapshot onto sheet payloads."""
    # First recursively apply base version if any
    base_version_id = snapshot_json.get("base_version")
    if base_version_id is not None:
        base_sv = db.get(StructureVersionRecordModel, int(base_version_id))
        if base_sv is not None:
            sheets_payload = apply_snapshot(sheets_payload, base_sv, db)

    changed_sheets = snapshot_json.get("changed_sheets", [])
    if not isinstance(changed_sheets, list):
        return sheets_payload

    snapshot_by_id: dict[int, dict[str, object]] = {}
    for cs in changed_sheets:
        sid = int(cs.get("sheet_id", 0))
        snapshot_by_id[sid] = cs

    for sheet_payload in sheets_payload:
        sid = int(sheet_payload["sheet_id"])
        cs = snapshot_by_id.get(sid)
        if cs is None:
            continue

        # Apply merge_ranges
        if "merge_ranges" in cs:
            sheet_payload["merge_ranges"] = cs["merge_ranges"]

        # Apply column metadata if present
        for key in ("column_kinds", "column_paths", "dimension_columns", "measure_columns", "header_row_span"):
            if key in cs:
                sheet_payload[key] = cs[key]

        # Overlay dirty rows
        dirty_rows = cs.get("dirty_rows", {})
        if not isinstance(dirty_rows, dict):
            continue

        aligned_grid = sheet_payload.get("aligned_grid", [])
        aligned_roles = sheet_payload.get("aligned_cell_roles", [])
        aligned_source_map = sheet_payload.get("aligned_source_map", [])
        cell_tags = sheet_payload.get("cell_tags", [])

        for row_str, row_data in dirty_rows.items():
            row_idx = int(row_str)
            if isinstance(row_data, dict) and row_idx < len(aligned_grid):
                if "grid" in row_data:
                    aligned_grid[row_idx] = row_data["grid"]
                if "roles" in row_data:
                    aligned_roles[row_idx] = row_data["roles"]
                if "source_map" in row_data:
                    aligned_source_map[row_idx] = row_data["source_map"]
                if "tags" in row_data:
                    cell_tags[row_idx] = row_data["tags"]

    # Re-derive header parsing after overlay
    sheets_payload = [with_header_parsing(sp) for sp in sheets_payload]
    return sheets_payload


def _apply_legacy_snapshot(
    sheets_payload: list[dict[str, object]],
    snapshot_json: dict[str, object],
) -> list[dict[str, object]]:
    """Apply a legacy full-sheet snapshot onto sheet payloads."""
    snapshot_sheets = snapshot_json.get("sheets", [])
    if not isinstance(snapshot_sheets, list):
        return sheets_payload

    snapshot_by_sheet_id = {int(s["sheet_id"]): s for s in snapshot_sheets if isinstance(s, dict)}
    updated_payload: list[dict[str, object]] = []

    for sheet_payload in sheets_payload:
        snapshot_sheet = snapshot_by_sheet_id.get(int(sheet_payload["sheet_id"]))
        if snapshot_sheet is None:
            updated_payload.append(sheet_payload)
            continue

        updated_payload.append(
            with_header_parsing(
                {
                    **sheet_payload,
                    "merge_ranges": snapshot_sheet.get("merge_ranges", []),
                    "aligned_grid": snapshot_sheet.get("aligned_grid", []),
                    "aligned_cell_roles": snapshot_sheet.get("aligned_cell_roles", []),
                    "aligned_source_map": snapshot_sheet.get("aligned_source_map", []),
                    "cell_tags": snapshot_sheet.get("cell_tags", []),
                }
            )
        )

    return updated_payload


def apply_snapshot(
    sheets_payload: list[dict[str, object]],
    structure_version: StructureVersionRecordModel,
    db: Session,
) -> list[dict[str, object]]:
    """Overlay a (possibly compressed) structure version onto parsed sheet payloads."""
    snapshot_json = structure_version.snapshot_json
    if _is_legacy_snapshot(snapshot_json):
        return _apply_legacy_snapshot(sheets_payload, snapshot_json)
    return _apply_compressed_snapshot(sheets_payload, snapshot_json, db)


def apply_structure_version(
    sheets_payload: list[dict[str, object]],
    structure_version: StructureVersionRecordModel,
) -> list[dict[str, object]]:
    """Public API: Overlay a saved structure version onto parsed sheet payloads.

    Delegates to apply_snapshot; db session is not available here,
    so only single-level (non-recursive) application is used for
    backward-compatible callers like build_task_review.
    """
    return apply_snapshot(sheets_payload, structure_version, None)


# ---------------------------------------------------------------------------
# Patch diffing
# ---------------------------------------------------------------------------

def _compute_dirty_rows(
    base_sheet: dict[str, object],
    new_sheet: dict[str, object],
) -> dict[str, object]:
    """Compute only the changed rows between two sheet payloads."""
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

    dirty_rows: dict[str, object] = {}
    for row_index in range(row_count):
        row_dirty: dict[str, object] = {}
        if base_grid[row_index] != new_grid[row_index]:
            row_dirty["grid"] = new_grid[row_index]
        if base_roles[row_index] != new_roles[row_index]:
            row_dirty["roles"] = new_roles[row_index]
        if base_source_map[row_index] != new_source_map[row_index]:
            row_dirty["source_map"] = new_source_map[row_index]
        if base_tags[row_index] != new_tags[row_index]:
            row_dirty["tags"] = new_tags[row_index]
        if row_dirty:
            dirty_rows[str(row_index)] = row_dirty

    return dirty_rows


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
# Snapshot builder (compressed format)
# ---------------------------------------------------------------------------

def _build_compressed_snapshot(
    base_sheets: list[dict[str, object]],
    new_sheets: list[dict[str, object]],
    base_version_id: int | None,
) -> dict[str, object]:
    """Build a dirty-row compressed snapshot from base vs new sheets."""
    base_by_id = {int(s["sheet_id"]): s for s in base_sheets}
    changed_sheets: list[dict[str, object]] = []

    for new_sheet in new_sheets:
        sid = int(new_sheet["sheet_id"])
        base_sheet = base_by_id.get(sid)
        if base_sheet is None:
            # New sheet - store all rows
            all_rows: dict[str, object] = {}
            aligned_grid = new_sheet.get("aligned_grid", [])
            aligned_roles = new_sheet.get("aligned_cell_roles", [])
            aligned_source_map = new_sheet.get("aligned_source_map", [])
            cell_tags = new_sheet.get("cell_tags", [])
            for i in range(len(aligned_grid)):
                all_rows[str(i)] = {
                    "grid": aligned_grid[i],
                    "roles": aligned_roles[i] if i < len(aligned_roles) else [],
                    "source_map": aligned_source_map[i] if i < len(aligned_source_map) else [],
                    "tags": cell_tags[i] if i < len(cell_tags) else [],
                }
            changed_sheets.append({
                "sheet_id": sid,
                "dirty_rows": all_rows,
                "merge_ranges": new_sheet.get("merge_ranges", []),
                "column_kinds": new_sheet.get("column_kinds", []),
                "column_paths": new_sheet.get("column_paths", []),
                "dimension_columns": new_sheet.get("dimension_columns", []),
                "measure_columns": new_sheet.get("measure_columns", []),
                "header_row_span": new_sheet.get("header_row_span", 0),
            })
            continue

        dirty_rows = _compute_dirty_rows(base_sheet, new_sheet)
        merge_changed = base_sheet.get("merge_ranges") != new_sheet.get("merge_ranges")

        if dirty_rows or merge_changed:
            changed_sheets.append({
                "sheet_id": sid,
                "dirty_rows": dirty_rows,
                "merge_ranges": new_sheet.get("merge_ranges", []),
            })

            # Always include column metadata when merge_ranges changed
            if merge_changed:
                changed_sheets[-1].update({
                    "column_kinds": new_sheet.get("column_kinds", []),
                    "column_paths": new_sheet.get("column_paths", []),
                    "dimension_columns": new_sheet.get("dimension_columns", []),
                    "measure_columns": new_sheet.get("measure_columns", []),
                    "header_row_span": new_sheet.get("header_row_span", 0),
                })

    return {
        "base_version": base_version_id,
        "changed_sheets": changed_sheets,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_structure_version_payload(
    parsed_sheets: list[dict[str, object]],
    request_sheets: list[dict[str, object]],
) -> None:
    """Raise 400 when the request sheets do not match the parsed task sheets."""
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
# Snapshot expansion (compressed -> full format for downstream services)
# ---------------------------------------------------------------------------

def expand_snapshot_to_sheets(
    db: "Session",
    snapshot_json: dict[str, object],
    task_id: int,
) -> list[dict[str, object]]:
    """Expand a (possibly compressed) snapshot into full-sheet format.

    Always returns a list of dicts with ``aligned_grid``, ``aligned_cell_roles``,
    ``aligned_source_map``, ``cell_tags``, ``merge_ranges``, ``column_kinds``,
    ``column_paths``, ``sheet_id``, and ``sheet_name`` keys.
    """
    if "sheets" in snapshot_json:
        # Legacy full-sheet format
        return list(snapshot_json.get("sheets", []))

    # Compressed format: build base sheets from models, then apply dirty rows
    # First recursively apply base version
    base_version_id = snapshot_json.get("base_version")
    base_sheets: list[dict[str, object]] = []
    if base_version_id is not None:
        base_sv = db.get(StructureVersionRecordModel, int(base_version_id))
        if base_sv is not None:
            base_sheets = expand_snapshot_to_sheets(db, base_sv.snapshot_json, task_id)

    if not base_sheets:
        # No base version - build from parsed sheet models
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.db.models.sheet_record import SheetRecordModel
        from app.db.models.task_record import TaskRecordModel
        from .grid_builder import build_sheet_payload as _bld
        task = db.scalar(
            select(TaskRecordModel)
            .where(TaskRecordModel.id == task_id)
            .options(selectinload(TaskRecordModel.sheets).selectinload(SheetRecordModel.cells))
        )
        if task is not None:
            base_sheets = [_bld(sm) for sm in sorted(task.sheets, key=lambda s: s.sheet_index)]

    # Apply changed_sheets on top
    changed_sheets = snapshot_json.get("changed_sheets", [])
    if not isinstance(changed_sheets, list):
        return base_sheets

    base_by_id: dict[int, dict[str, object]] = {}
    for bs in base_sheets:
        sid = int(bs.get("sheet_id", 0))
        base_by_id[sid] = bs

    for cs in changed_sheets:
        sid = int(cs.get("sheet_id", 0))
        base = base_by_id.get(sid)
        if base is None:
            continue

        # Apply merge_ranges
        if "merge_ranges" in cs:
            base["merge_ranges"] = cs["merge_ranges"]

        # Apply column metadata
        for key in ("column_kinds", "column_paths", "dimension_columns", "measure_columns", "header_row_span"):
            val = cs.get(key)
            if val is not None:
                base[key] = val

        # Overlay dirty rows
        dirty_rows = cs.get("dirty_rows", {})
        if isinstance(dirty_rows, dict):
            aligned_grid = list(base.get("aligned_grid", []))
            aligned_roles = list(base.get("aligned_cell_roles", []))
            aligned_source_map = list(base.get("aligned_source_map", []))
            cell_tags = list(base.get("cell_tags", []))

            for row_str, row_data in dirty_rows.items():
                row_idx = int(row_str)
                if isinstance(row_data, dict) and row_idx < len(aligned_grid):
                    if "grid" in row_data:
                        aligned_grid[row_idx] = row_data["grid"]
                    if "roles" in row_data:
                        aligned_roles[row_idx] = row_data["roles"]
                    if "source_map" in row_data:
                        aligned_source_map[row_idx] = row_data["source_map"]
                    if "tags" in row_data:
                        cell_tags[row_idx] = row_data["tags"]

            base["aligned_grid"] = aligned_grid
            base["aligned_cell_roles"] = aligned_roles
            base["aligned_source_map"] = aligned_source_map
            base["cell_tags"] = cell_tags

    return list(base_by_id.values())


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def save_structure_version(
    task: TaskRecordModel,
    base_structure_version: int,
    request_sheets: list[dict[str, object]],
    db: Session,
) -> dict[str, object]:
    """Persist a new immutable structure version as a compressed diff snapshot."""
    sv_latest = latest_structure_version(task)
    current_editable_version = sv_latest.version_number if sv_latest else 0
    base_sheets = [
        build_sheet_payload(sheet) for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]
    if sv_latest is not None:
        base_sheets = apply_snapshot(base_sheets, sv_latest, db)

    if current_editable_version != base_structure_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Structure version is out of date",
        )

    validate_structure_version_payload(base_sheets, request_sheets)

    next_version_number = base_structure_version + 1
    patch_summary = build_patch_summary(base_sheets, request_sheets)
    enriched_sheets = [with_header_parsing(dict(s)) for s in request_sheets]

    # Build compressed snapshot (dirty rows only)
    base_version_id = sv_latest.id if sv_latest else None
    compressed_snapshot = _build_compressed_snapshot(base_sheets, enriched_sheets, base_version_id)

    structure_version = StructureVersionRecordModel(
        task_id=task.id,
        version_number=next_version_number,
        snapshot_json=compressed_snapshot,
        patch_summary_json=patch_summary,
        is_confirmed=False,
        base_version_id=base_version_id,
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


