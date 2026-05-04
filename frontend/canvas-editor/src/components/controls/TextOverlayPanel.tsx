import React, { useCallback, useMemo } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { formatTime, TRANSITION_OPTIONS } from '@/utils/canvas';
import { Segment } from '@/types/editor';

export default function TextOverlayPanel() {
  const {
    project,
    selectedSegmentId,
    selectedOverlayId,
    addTextOverlay,
    updateTextOverlay,
    deleteTextOverlay,
  } = useEditorStore();

  const segment = project?.segments.find((s) => s.id === selectedSegmentId);
  const overlay = segment?.textOverlays.find((o) => o.id === selectedOverlayId);

  const handleAddOverlay = useCallback(() => {
    if (!selectedSegmentId) return;
    addTextOverlay(selectedSegmentId);
  }, [selectedSegmentId, addTextOverlay]);

  const handleUpdate = useCallback(
    (field: string, value: string | number) => {
      if (!overlay) return;
      updateTextOverlay(overlay.id, { [field]: value });
    },
    [overlay, updateTextOverlay]
  );

  const handleDelete = useCallback(() => {
    if (!overlay) return;
    deleteTextOverlay(overlay.id);
  }, [overlay, deleteTextOverlay]);

  if (!segment) {
    return (
      <div className="p-4 text-canvas-text-muted text-sm">
        Select a segment to manage text overlays
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-canvas-border">
        <h3 className="text-sm font-semibold text-canvas-text">Text Overlays</h3>
        <button className="btn btn-primary btn-sm" onClick={handleAddOverlay}>
          + Add Text
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <OverlayList
          overlays={segment.textOverlays}
          selectedOverlayId={selectedOverlayId}
          currentTime={useEditorStore.getState().currentTime}
        />

        {overlay && (
          <OverlayEditor
            overlay={overlay}
            segmentDuration={segment.durationSeconds}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        )}
      </div>
    </div>
  );
}

interface OverlayListProps {
  overlays: import('@/types/editor').TextOverlay[];
  selectedOverlayId: string | null;
  currentTime: number;
}

function OverlayList({ overlays, selectedOverlayId, currentTime }: OverlayListProps) {
  const { setSelectedOverlay } = useEditorStore();

  return (
    <div className="border-b border-canvas-border">
      {overlays.length === 0 && (
        <div className="px-4 py-3 text-xs text-canvas-text-muted">
          No text overlays. Click + Add Text to create one.
        </div>
      )}
      {overlays.map((o) => {
        const isVisible = currentTime >= o.startTime && currentTime <= o.endTime;
        return (
          <div
            key={o.id}
            className={`overlay-list-item ${o.id === selectedOverlayId ? 'active' : ''}`}
            onClick={() => setSelectedOverlay(o.id)}
          >
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: isVisible ? '#22c55e' : '#666' }}
            />
            <span className="flex-1 truncate">{o.text}</span>
            <span className="text-xs text-canvas-text-muted">
              {formatTime(o.startTime)} - {formatTime(o.endTime)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

interface OverlayEditorProps {
  overlay: import('@/types/editor').TextOverlay;
  segmentDuration: number;
  onUpdate: (field: string, value: string | number) => void;
  onDelete: () => void;
}

function OverlayEditor({ overlay, segmentDuration, onUpdate, onDelete }: OverlayEditorProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-canvas-text-muted uppercase tracking-wider">
          Properties
        </h4>
        <button className="btn btn-danger btn-sm" onClick={onDelete}>
          Delete
        </button>
      </div>

      <div className="control-group">
        <label className="control-label">Text Content</label>
        <textarea
          className="control-input"
          rows={3}
          value={overlay.text}
          onChange={(e) => onUpdate('text', e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="control-group">
          <label className="control-label">Font Family</label>
          <select
            className="control-select"
            value={overlay.fontFamily}
            onChange={(e) => onUpdate('fontFamily', e.target.value)}
          >
            {['Arial', 'Helvetica', 'Georgia', 'Times New Roman', 'Courier New', 'Verdana', 'Impact', 'Trebuchet MS'].map(
              (f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              )
            )}
          </select>
        </div>
        <div className="control-group">
          <label className="control-label">Font Size</label>
          <input
            type="number"
            className="control-input"
            value={overlay.fontSize}
            min={12}
            max={200}
            onChange={(e) => onUpdate('fontSize', parseInt(e.target.value) || 12)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="control-group">
          <label className="control-label">Font Color</label>
          <div className="flex items-center gap-2">
            <div className="color-swatch" style={{ background: overlay.fontColor }}>
              <input
                type="color"
                value={overlay.fontColor}
                onChange={(e) => onUpdate('fontColor', e.target.value)}
              />
            </div>
            <input
              type="text"
              className="control-input"
              value={overlay.fontColor}
              onChange={(e) => onUpdate('fontColor', e.target.value)}
            />
          </div>
        </div>
        <div className="control-group">
          <label className="control-label">Stroke Color</label>
          <div className="flex items-center gap-2">
            <div className="color-swatch" style={{ background: overlay.strokeColor }}>
              <input
                type="color"
                value={overlay.strokeColor}
                onChange={(e) => onUpdate('strokeColor', e.target.value)}
              />
            </div>
            <input
              type="text"
              className="control-input"
              value={overlay.strokeColor}
              onChange={(e) => onUpdate('strokeColor', e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="control-group">
        <label className="control-label">Stroke Width: {overlay.strokeWidth}px</label>
        <input
          type="range"
          min={0}
          max={10}
          step={1}
          value={overlay.strokeWidth}
          onChange={(e) => onUpdate('strokeWidth', parseInt(e.target.value))}
          className="w-full"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="control-group">
          <label className="control-label">Position X: {overlay.positionX.toFixed(3)}</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={overlay.positionX}
            onChange={(e) => onUpdate('positionX', parseFloat(e.target.value))}
            className="w-full"
          />
        </div>
        <div className="control-group">
          <label className="control-label">Position Y: {overlay.positionY.toFixed(3)}</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={overlay.positionY}
            onChange={(e) => onUpdate('positionY', parseFloat(e.target.value))}
            className="w-full"
          />
        </div>
      </div>

      <div className="control-group">
        <label className="control-label">Anchor Point</label>
        <select
          className="control-select"
          value={overlay.anchor}
          onChange={(e) => onUpdate('anchor', e.target.value)}
        >
          <option value="top-left">Top Left</option>
          <option value="top-center">Top Center</option>
          <option value="top-right">Top Right</option>
          <option value="center-left">Center Left</option>
          <option value="center">Center</option>
          <option value="center-right">Center Right</option>
          <option value="bottom-left">Bottom Left</option>
          <option value="bottom-center">Bottom Center</option>
          <option value="bottom-right">Bottom Right</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="control-group">
          <label className="control-label">Start Time (s)</label>
          <input
            type="number"
            className="control-input"
            value={overlay.startTime}
            min={0}
            max={segmentDuration}
            step={0.1}
            onChange={(e) => onUpdate('startTime', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div className="control-group">
          <label className="control-label">End Time (s)</label>
          <input
            type="number"
            className="control-input"
            value={overlay.endTime}
            min={0}
            max={segmentDuration}
            step={0.1}
            onChange={(e) => onUpdate('endTime', parseFloat(e.target.value) || 0)}
          />
        </div>
      </div>

      <div className="control-group">
        <label className="control-label">Animation</label>
        <select
          className="control-select"
          value={overlay.animation}
          onChange={(e) => onUpdate('animation', e.target.value)}
        >
          <option value="none">None</option>
          <option value="fade-in">Fade In</option>
          <option value="slide-up">Slide Up</option>
          <option value="slide-down">Slide Down</option>
          <option value="typewriter">Typewriter</option>
          <option value="bounce-in">Bounce In</option>
        </select>
      </div>
    </div>
  );
}