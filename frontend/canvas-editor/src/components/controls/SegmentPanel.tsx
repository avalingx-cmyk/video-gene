import React, { useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useEditorStore } from '@/store/editorStore';
import { formatTime, TRANSITION_OPTIONS } from '@/utils/canvas';
import { STATUS_LABELS, Segment } from '@/types/editor';

function SortableSegmentItem({ segment, isActive, onClick }: { segment: Segment; isActive: boolean; onClick: () => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: segment.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`segment-list-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
      {...attributes}
      {...listeners}
    >
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{segment.title}</div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-canvas-text-muted">
            {segment.durationSeconds}s
          </span>
          <span className={`status-badge ${segment.status}`}>
            {STATUS_LABELS[segment.status] || segment.status}
          </span>
        </div>
      </div>
      <div className="text-xs text-canvas-text-muted">
        {segment.textOverlays.length} overlay{segment.textOverlays.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}

export default function SegmentPanel() {
  const {
    project,
    selectedSegmentId,
    setSelectedSegment,
    updateSegment,
    reorderSegments,
  } = useEditorStore();

  const segments = project?.segments ?? [];
  const selectedSegment = segments.find((s) => s.id === selectedSegmentId);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = segments.findIndex((s) => s.id === active.id);
      const newIndex = segments.findIndex((s) => s.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const reordered = arrayMove(segments, oldIndex, newIndex);
      reorderSegments(reordered.map((s) => s.id));
    },
    [segments, reorderSegments]
  );

  const handleUpdate = useCallback(
    (field: string, value: string | number) => {
      if (!selectedSegmentId) return;
      updateSegment(selectedSegmentId, { [field]: value });
    },
    [selectedSegmentId, updateSegment]
  );

  if (!project) {
    return (
      <div className="p-4 text-canvas-text-muted text-sm">
        Select a project to manage segments
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-canvas-border">
        <h3 className="text-sm font-semibold text-canvas-text">Segments</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={segments.map((s) => s.id)}
            strategy={verticalListSortingStrategy}
          >
            {segments.map((segment) => (
              <SortableSegmentItem
                key={segment.id}
                segment={segment}
                isActive={segment.id === selectedSegmentId}
                onClick={() => setSelectedSegment(segment.id)}
              />
            ))}
          </SortableContext>
        </DndContext>

        {segments.length === 0 && (
          <div className="px-4 py-8 text-center text-canvas-text-muted text-sm">
            No segments yet
          </div>
        )}
      </div>

      {selectedSegment && (
        <SegmentDetailPanel
          segment={selectedSegment}
          onUpdate={handleUpdate}
        />
      )}
    </div>
  );
}

interface SegmentDetailPanelProps {
  segment: Segment;
  onUpdate: (field: string, value: string | number) => void;
}

function SegmentDetailPanel({ segment, onUpdate }: SegmentDetailPanelProps) {
  return (
    <div className="border-t border-canvas-border p-4 space-y-3">
      <h4 className="text-xs font-semibold text-canvas-text-muted uppercase tracking-wider">
        Segment Settings
      </h4>

      <div className="control-group">
        <label className="control-label">Title</label>
        <input
          type="text"
          className="control-input"
          value={segment.title}
          onChange={(e) => onUpdate('title', e.target.value)}
        />
      </div>

      <div className="control-group">
        <label className="control-label">Duration (seconds)</label>
        <input
          type="number"
          className="control-input"
          value={segment.durationSeconds}
          min={1}
          max={60}
          step={0.5}
          onChange={(e) => onUpdate('durationSeconds', parseFloat(e.target.value) || 10)}
        />
      </div>

      <div className="control-group">
        <label className="control-label">Transition</label>
        <select
          className="control-select"
          value={segment.transition}
          onChange={(e) => onUpdate('transition', e.target.value)}
        >
          {TRANSITION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {segment.narrationText && (
        <div className="control-group">
          <label className="control-label">Narration</label>
          <div className="text-xs text-canvas-text bg-canvas-bg rounded p-2 max-h-24 overflow-y-auto">
            {segment.narrationText}
          </div>
        </div>
      )}

      {segment.videoUrl && (
        <div className="control-group">
          <label className="control-label">Video</label>
          <div className="text-xs text-canvas-success break-all">
            {segment.videoUrl}
          </div>
        </div>
      )}
    </div>
  );
}