import React, { useEffect } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { useKeyboardShortcuts } from '@/hooks/usePlayer';
import {
  VideoPreview,
  TextOverlayPanel,
  SegmentPanel,
  TimelineScrubber,
  Toolbar,
} from '@/components';

interface CanvasEditorProps {
  projectId?: string;
}

export default function CanvasEditor({ projectId }: CanvasEditorProps) {
  const { project, isLoading, error, loadProject, clearError } = useEditorStore();

  useKeyboardShortcuts();

  useEffect(() => {
    if (projectId) {
      loadProject(projectId);
    }
  }, [projectId, loadProject]);

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-canvas-bg">
        <div className="text-center max-w-md">
          <div className="text-canvas-danger text-lg mb-2">Error</div>
          <div className="text-canvas-text-muted text-sm mb-4">{error}</div>
          <button className="btn btn-primary" onClick={clearError}>
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-canvas-bg">
        <div className="text-canvas-text-muted animate-pulse-slow">
          Loading project...
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-screen flex items-center justify-center bg-canvas-bg">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4 opacity-30">&#9654;</div>
          <h2 className="text-xl text-canvas-text mb-2">Canvas Editor</h2>
          <p className="text-canvas-text-muted text-sm mb-4">
            Select a project to start editing. Pass a <code className="text-canvas-accent">projectId</code> prop to load a project.
          </p>
          <div className="text-xs text-canvas-text-muted">
            API Base: {process.env.NEXT_PUBLIC_API_BASE || 'same origin'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-canvas-bg">
      <Toolbar />
      <div className="flex-1 flex overflow-hidden">
        <div className="sidebar-panel w-56 flex flex-col border-r border-canvas-border">
          <SegmentPanel />
        </div>
        <div className="flex-1 flex flex-col overflow-hidden">
          <VideoPreview />
        </div>
        <div className="sidebar-panel w-72 flex flex-col border-l border-canvas-border">
          <TextOverlayPanel />
        </div>
      </div>
      <TimelineScrubber />
    </div>
  );
}