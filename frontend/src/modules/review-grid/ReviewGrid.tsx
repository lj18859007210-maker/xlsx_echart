import { useCallback, useEffect, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { DraftCellTag, DraftReviewSheet, GridPoint, ReviewSheetSnapshot } from '../../types/review';

type ReviewGridProps = {
  sheet: ReviewSheetSnapshot;
  draftSheet?: DraftReviewSheet | null;
  mode: 'raw' | 'aligned';
  selectedRange?: {
    startRow: number;
    endRow: number;
    startCol: number;
    endCol: number;
  } | null;
  onCellSelect?: (point: GridPoint) => void;
  onLoadMore?: () => void;
  loadingMore?: boolean;
};

const ROW_HEIGHT = 88;
const OVERSCAN = 6;

function getCellTone(role: string, value: string | null, tag: DraftCellTag = 'none') {
  if (tag === 'header') return 'is-header';
  if (tag === 'data') return 'is-data';
  if (modeledEmpty(role, value)) return 'is-empty';
  if (role === 'dimension') return 'is-dimension';
  if (role === 'measure') return 'is-measure';
  return 'is-unknown';
}

function modeledEmpty(role: string, value: string | null) {
  return role === 'empty' || value === null || value === '';
}

function isSelected(
  selectedRange: ReviewGridProps['selectedRange'],
  rowIndex: number,
  colIndex: number,
) {
  if (!selectedRange) return false;
  return (
    rowIndex >= selectedRange.startRow &&
    rowIndex <= selectedRange.endRow &&
    colIndex >= selectedRange.startCol &&
    colIndex <= selectedRange.endCol
  );
}

export function ReviewGrid({
  sheet,
  draftSheet,
  mode,
  selectedRange,
  onCellSelect,
  onLoadMore,
  loadingMore,
}: ReviewGridProps) {
  const values =
    mode === 'raw' ? sheet.grid_snapshot : draftSheet?.alignedGrid ?? sheet.aligned_grid;
  const sourceMap =
    mode === 'raw' ? sheet.address_map : draftSheet?.alignedSourceMap ?? sheet.aligned_source_map;
  const roles =
    mode === 'raw'
      ? values.map((row) => row.map((value) => (value === null ? 'empty' : 'raw')))
      : draftSheet?.alignedRoles ?? sheet.aligned_cell_roles;
  const tags =
    mode === 'raw'
      ? values.map((row) => row.map(() => 'none' as DraftCellTag))
      : draftSheet?.cellTags ?? values.map((row) => row.map(() => 'none' as DraftCellTag));

  const scrollRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: values.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: useCallback(() => ROW_HEIGHT, []),
    overscan: OVERSCAN,
  });

  const virtualItems = virtualizer.getVirtualItems();

  // Trigger loadMore when approaching the end of loaded data
  useEffect(() => {
    if (!onLoadMore || virtualItems.length === 0) return;
    const lastVisible = virtualItems[virtualItems.length - 1];
    if (lastVisible && lastVisible.index >= values.length - OVERSCAN - 2) {
      onLoadMore();
    }
  }, [virtualItems, values.length, onLoadMore]);

  return (
    <div className='review-grid-shell'>
      <div className='review-grid-header'>
        <div>
          <p className='mini-label'>\u7f51\u683c\u89c6\u56fe</p>
          <h3>{mode === 'raw' ? 'Original Grid Snapshot' : 'Aligned Logic Grid'}</h3>
        </div>
        <p className='review-grid-meta'>
          {sheet.row_count} rows \u00b7 {sheet.col_count} cols
        </p>
      </div>

      <div className='review-grid-scroll' ref={scrollRef}>
        <table className='review-grid-table'>
          <tbody
            className='review-grid-tbody'
            style={{ height: virtualizer.getTotalSize() }}
          >
            {virtualItems.map((virtualRow) => {
              const rowIndex = virtualRow.index;
              const row = values[rowIndex];
              if (!row) return null;
              return (
                <tr
                  key={'' + sheet.sheet_id + '-' + rowIndex}
                  className='virtual-tr'
                  data-index={virtualRow.index}
                  ref={virtualizer.measureElement}
                  style={{ transform: '' + 'translateY(' + virtualRow.start + 'px)' }}
                >
                  {row.map((value, colIndex) => {
                    const role = roles[rowIndex]?.[colIndex] ?? 'unknown';
                    const source = sourceMap[rowIndex]?.[colIndex];
                    const tag = tags[rowIndex]?.[colIndex] ?? 'none';
                    return (
                      <td
                        key={'' + rowIndex + '-' + colIndex}
                        className={
                          'review-grid-cell ' +
                          getCellTone(role, value, tag) +
                          (isSelected(selectedRange, rowIndex, colIndex) ? ' is-selected' : '')
                        }
                        onClick={() => onCellSelect?.({ row: rowIndex, col: colIndex })}
                      >
                        <span className='cell-value'>{value ?? '\u00b7'}</span>
                        <span className='cell-meta'>
                          {mode === 'aligned'
                            ? '' + role + (tag !== 'none' ? ' \u00b7 ' + tag : '')
                            : source || 'empty'}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        {loadingMore && (
          <div className='review-grid-loading'>\u52a0\u8f7d\u66f4\u591a...</div>
        )}
      </div>
    </div>
  );
}
