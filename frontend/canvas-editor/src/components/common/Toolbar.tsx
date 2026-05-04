import React, { useCallback } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { formatTime } from '@/utils/canvas';
import { PreviewQuality } from '@/types/editor';

export default function Toolbar() {
  const {
    project,
    isPlaying,
    setIsPlaying,
    undo,
    redo,
    canUndo,
    canRedo,
    selectedOverlayId,
    selectedSegmentId,
    addTextOverlay,
    deleteTextOverlay,
    exportLayerJson,
    previewQuality,
    setPreviewQuality,
    zoom,
    setZoom,
    currentTime,
  } = useEditorStore();

  const handleAddText = useCallback(() => {
    if (selectedSegmentId) {
      addTextOverlay(selectedSegmentId);
    }
  }, [selectedSegmentId, addTextOverlay]);

  const handleDeleteText = useCallback(() => {
    if (selectedOverlayId) {
      deleteTextOverlay(selectedOverlayId);
    }
  }, [selectedOverlayId, deleteTextOverlay]);

  const handleExportJson = useCallback(() => {
    const json = exportLayerJson();
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `layer-model-${project?.id || 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportLayerJson, project?.id]);

  const togglePlay = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying]);

  return (
    <div className="toolbar">
      <div className="flex items-center gap-2">
        {project && (
          <span className="text-sm font-semibold text-canvas-text truncate max-w-48">
            {project.title}
          </span>
        )}
        <span className={`status-badge ${project?.status || 'pending'}`}>
          {project?.status || 'No Project'}
        </span>
      </div>

      <div className="w-px h-6 bg-canvas-border mx-1" />

      <button className="btn btn-ghost btn-sm" onClick={togglePlay} title={isPlaying ? 'Pause' : 'Play'}>
        {isPlaying ? '⏸' : '▶'}
      </button>
      <span className="text-xs text-canvas-text-muted font-mono min-w-20">
        {formatTime(currentTime)}
      </span>

      <div className="w-px h-6 bg-canvas-border mx-1" />

      <button
        className="btn btn-ghost btn-sm"
        onClick={undo}
        disabled={!canUndo()}
        title="Undo (Ctrl+Z)"
      >
        ↩ Undo
      </button>
      <button
        className="btn btn-ghost btn-sm"
        onClick={redo}
        disabled={!canRedo()}
        title="Redo (Ctrl+Shift+Z)"
      >
        ↪ Redo
      </button>

      <div className="w-px h-6 bg-canvas-border mx-1" />

      <button
        className="btn btn-primary btn-sm"
        onClick={handleAddText}
        disabled={!selectedSegmentId}
        title="Add Text Overlay (Ctrl+T)"
      >
        + Text
      </button>
      <button
        className="btn btn-danger btn-sm"
        onClick={handleDeleteText}
        disabled={!selectedOverlayId}
        title="Delete Overlay (Delete)"
      >
        Del
      </button>

      <div className="w-px h-6 bg-canvas-border mx-1" />

      <div className="flex items-center gap-1">
        <label className="text-xs text-canvas-text-muted">Preview:</label>
        <select
          className="control-select"
          style={{ width: 70, padding: '2px 4px', fontSize: 11 }}
          value={previewQuality}
          onChange={(e) => setPreviewQuality(e.target.value as PreviewQuality)}
        >
          <option value="360p">360p</option>
          <option value="480p">480p</option>
          <option value="1080p">1080p</option>
        </select>
      </div>

      <div className="flex items-center gap-1">
        <label className="text-xs text-canvas-text-muted">Zoom:</label>
        <input
          type="range"
          min={0.25}
          max={3}
          step={0.25}
          value={zoom}
          onChange={(e) => setZoom(parseFloat(e.target.value))}
          className="w-16"
        />
        <span className="text-xs text-canvas-text-muted w-8">{Math.round(zoom * 100)}%</span>
      </div>

      <div className="flex-1" />

      <button className="btn btn-ghost btn-sm" onClick={handleExportJson} title="Export layer JSON">
        Export JSON
      </button>
    </div>
  );
}