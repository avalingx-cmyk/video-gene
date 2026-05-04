import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import {
  VideoProject,
  Segment,
  TextOverlay,
  HistoryEntry,
  PreviewQuality,
  DEFAULT_OVERLAY,
  TextAnchor,
  TextAnimation,
  TransitionType,
} from '@/types/editor';
import { projectApi, segmentApi, overlayApi } from '@/utils/api';

const DRAG_SAVE_DELAY_MS = 300;
const pendingOverlaySaves = new Map<string, ReturnType<typeof setTimeout>>();

interface EditorState {
  project: VideoProject | null;
  selectedSegmentId: string | null;
  selectedOverlayId: string | null;
  currentTime: number;
  isPlaying: boolean;
  previewQuality: PreviewQuality;
  zoom: number;

  undoStack: HistoryEntry[];
  redoStack: HistoryEntry[];

  isLoading: boolean;
  error: string | null;
  saving: boolean;
}

interface EditorActions {
  loadProject: (projectId: string) => Promise<void>;
  setSelectedSegment: (segmentId: string | null) => void;
  setSelectedOverlay: (overlayId: string | null) => void;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setPreviewQuality: (quality: PreviewQuality) => void;
  setZoom: (zoom: number) => void;

  addTextOverlay: (segmentId: string, partial?: Partial<TextOverlay>) => void;
  updateTextOverlay: (overlayId: string, updates: Partial<TextOverlay>) => void;
  deleteTextOverlay: (overlayId: string) => void;
  moveTextOverlay: (overlayId: string, positionX: number, positionY: number) => void;

  saveOverlayToServer: (projectId: string, segmentId: string, overlayId: string) => Promise<void>;
  deleteOverlayFromServer: (projectId: string, segmentId: string, overlayId: string) => Promise<void>;

  updateSegment: (segmentId: string, updates: Partial<Segment>) => void;
  reorderSegments: (segmentIds: string[]) => void;

  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  exportLayerJson: () => object;
  triggerExport: (projectId: string) => Promise<{ taskId: string }>;
  triggerCompose: (projectId: string) => Promise<{ taskId: string; readySegments: number }>;
  clearError: () => void;
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

function pushUndo(state: EditorState, description: string, type: HistoryEntry['type']): Partial<EditorState> {
  if (!state.project) return {};
  const entry: HistoryEntry = {
    id: uuidv4(),
    timestamp: Date.now(),
    type,
    description,
    snapshot: JSON.stringify(state.project),
  };
  return {
    undoStack: [...state.undoStack, entry],
    redoStack: [],
  };
}

function overlaysEqual(a: TextOverlay, b: Partial<TextOverlay>): boolean {
  return (
    a.text === (b.text ?? a.text) &&
    a.fontFamily === (b.fontFamily ?? a.fontFamily) &&
    a.fontSize === (b.fontSize ?? a.fontSize) &&
    a.fontColor === (b.fontColor ?? a.fontColor) &&
    a.strokeColor === (b.strokeColor ?? a.strokeColor) &&
    a.strokeWidth === (b.strokeWidth ?? a.strokeWidth) &&
    Math.abs(a.positionX - (b.positionX ?? a.positionX)) < 0.0001 &&
    Math.abs(a.positionY - (b.positionY ?? a.positionY)) < 0.0001 &&
    a.anchor === (b.anchor ?? a.anchor) &&
    Math.abs(a.startTime - (b.startTime ?? a.startTime)) < 0.001 &&
    Math.abs(a.endTime - (b.endTime ?? a.endTime)) < 0.001 &&
    a.animation === (b.animation ?? a.animation)
  );
}

export const useEditorStore = create<EditorState & EditorActions>((set, get) => ({
  project: null,
  selectedSegmentId: null,
  selectedOverlayId: null,
  currentTime: 0,
  isPlaying: false,
  previewQuality: '360p',
  zoom: 1,
  undoStack: [],
  redoStack: [],
  isLoading: false,
  error: null,
  saving: false,

  loadProject: async (projectId: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await projectApi.get(projectId);
      data.segments.sort((a, b) => a.orderIndex - b.orderIndex);
      const firstSegmentId = data.segments.length > 0 ? data.segments[0].id : null;
      set({
        project: data,
        selectedSegmentId: firstSegmentId,
        selectedOverlayId: null,
        currentTime: 0,
        isPlaying: false,
        undoStack: [],
        redoStack: [],
        isLoading: false,
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Unknown error', isLoading: false });
    }
  },

  setSelectedSegment: (segmentId) => set({ selectedSegmentId: segmentId, selectedOverlayId: null }),
  setSelectedOverlay: (overlayId) => set({ selectedOverlayId: overlayId }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setPreviewQuality: (quality) => set({ previewQuality: quality }),
  setZoom: (zoom) => set({ zoom: Math.max(0.25, Math.min(3, zoom)) }),

  addTextOverlay: (segmentId, partial = {}) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Add text overlay', 'add_overlay');
    const newOverlay: TextOverlay = {
      ...DEFAULT_OVERLAY,
      ...partial,
      id: uuidv4(),
      segmentId,
    };
    const updatedProject = deepClone(state.project);
    const segment = updatedProject.segments.find((s) => s.id === segmentId);
    if (!segment) return;
    segment.textOverlays.push(newOverlay);
    set({ project: updatedProject, selectedOverlayId: newOverlay.id, ...undo });

    if (state.project) {
      overlayApi.create(state.project.id, segmentId, {
        text: newOverlay.text,
        font_family: newOverlay.fontFamily,
        font_size: newOverlay.fontSize,
        font_color: newOverlay.fontColor,
        stroke_color: newOverlay.strokeColor,
        stroke_width: newOverlay.strokeWidth,
        position_x: newOverlay.positionX,
        position_y: newOverlay.positionY,
        anchor: newOverlay.anchor,
        start_time: newOverlay.startTime,
        end_time: newOverlay.endTime,
        animation: newOverlay.animation,
      }).then((saved) => {
        const currentProject = get().project;
        if (!currentProject) return;
        const updated = deepClone(currentProject);
        const seg = updated.segments.find((s) => s.id === segmentId);
        if (!seg) return;
        const idx = seg.textOverlays.findIndex((o) => o.id === newOverlay.id);
        if (idx !== -1) {
          seg.textOverlays[idx] = saved;
        } else {
          seg.textOverlays.push(saved);
        }
        set({ project: updated, selectedOverlayId: saved.id });
      }).catch(() => {});
    }
  },

  updateTextOverlay: (overlayId, updates) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Update overlay', 'update_overlay');
    const updatedProject = deepClone(state.project);
    for (const segment of updatedProject.segments) {
      const overlay = segment.textOverlays.find((o) => o.id === overlayId);
      if (overlay) {
        Object.assign(overlay, updates);
        break;
      }
    }
    set({ project: updatedProject, ...undo });

    if (state.project) {
      const projectId = state.project.id;
      let targetSegmentId: string | null = null;
      for (const seg of state.project.segments) {
        const o = seg.textOverlays.find((o) => o.id === overlayId);
        if (o) { targetSegmentId = seg.id; break; }
      }
      if (targetSegmentId) {
        const apiUpdates: Record<string, unknown> = {};
        if (updates.text !== undefined) apiUpdates['text'] = updates.text;
        if (updates.fontFamily !== undefined) apiUpdates['font_family'] = updates.fontFamily;
        if (updates.fontSize !== undefined) apiUpdates['font_size'] = updates.fontSize;
        if (updates.fontColor !== undefined) apiUpdates['font_color'] = updates.fontColor;
        if (updates.strokeColor !== undefined) apiUpdates['stroke_color'] = updates.strokeColor;
        if (updates.strokeWidth !== undefined) apiUpdates['stroke_width'] = updates.strokeWidth;
        if (updates.positionX !== undefined) apiUpdates['position_x'] = updates.positionX;
        if (updates.positionY !== undefined) apiUpdates['position_y'] = updates.positionY;
        if (updates.anchor !== undefined) apiUpdates['anchor'] = updates.anchor;
        if (updates.startTime !== undefined) apiUpdates['start_time'] = updates.startTime;
        if (updates.endTime !== undefined) apiUpdates['end_time'] = updates.endTime;
        if (updates.animation !== undefined) apiUpdates['animation'] = updates.animation;
        overlayApi.update(projectId, targetSegmentId, overlayId, apiUpdates).catch(() => {});
      }
    }
  },

  deleteTextOverlay: (overlayId) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Delete overlay', 'delete_overlay');
    const updatedProject = deepClone(state.project);
    let targetSegmentId: string | null = null;
    for (const segment of updatedProject.segments) {
      const idx = segment.textOverlays.findIndex((o) => o.id === overlayId);
      if (idx !== -1) {
        targetSegmentId = segment.id;
        segment.textOverlays.splice(idx, 1);
        break;
      }
    }
    set({
      project: updatedProject,
      selectedOverlayId: state.selectedOverlayId === overlayId ? null : state.selectedOverlayId,
      ...undo,
    });

    if (state.project && targetSegmentId) {
      overlayApi.delete(state.project.id, targetSegmentId, overlayId).catch(() => {});
    }
  },

  moveTextOverlay: (overlayId, positionX, positionY) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Move overlay', 'move_overlay');
    const updatedProject = deepClone(state.project);
    for (const segment of updatedProject.segments) {
      const overlay = segment.textOverlays.find((o) => o.id === overlayId);
      if (overlay) {
        overlay.positionX = Math.max(0, Math.min(1, positionX));
        overlay.positionY = Math.max(0, Math.min(1, positionY));
        break;
      }
    }
    set({ project: updatedProject, ...undo });

    if (state.project) {
      const projectId = state.project.id;
      let targetSegmentId: string | null = null;
      for (const seg of state.project.segments) {
        if (seg.textOverlays.find((o) => o.id === overlayId)) {
          targetSegmentId = seg.id;
          break;
        }
      }
      if (targetSegmentId) {
        const segmentId = targetSegmentId;
        const existingTimer = pendingOverlaySaves.get(overlayId);
        if (existingTimer) clearTimeout(existingTimer);
        pendingOverlaySaves.set(overlayId, setTimeout(() => {
          pendingOverlaySaves.delete(overlayId);
          const currentState = get();
          if (!currentState.project) return;
          const currentOverlay = currentState.project.segments
            .flatMap((s) => s.textOverlays)
            .find((o) => o.id === overlayId);
          if (currentOverlay) {
            overlayApi.update(projectId, segmentId, overlayId, {
              position_x: currentOverlay.positionX,
              position_y: currentOverlay.positionY,
            }).catch(() => {});
          }
        }, DRAG_SAVE_DELAY_MS));
      }
    }
  },

  saveOverlayToServer: async (projectId, segmentId, overlayId) => {
    const state = get();
    if (!state.project) return;
    const overlay = state.project.segments
      .flatMap((s) => s.textOverlays)
      .find((o) => o.id === overlayId);
    if (!overlay) return;
    try {
      await overlayApi.update(projectId, segmentId, overlayId, {
        text: overlay.text,
        font_family: overlay.fontFamily,
        font_size: overlay.fontSize,
        font_color: overlay.fontColor,
        stroke_color: overlay.strokeColor,
        stroke_width: overlay.strokeWidth,
        position_x: overlay.positionX,
        position_y: overlay.positionY,
        anchor: overlay.anchor,
        start_time: overlay.startTime,
        end_time: overlay.endTime,
        animation: overlay.animation,
      });
    } catch (e) {
      // silently fail — local state is already updated
    }
  },

  deleteOverlayFromServer: async (projectId, segmentId, overlayId) => {
    try {
      await overlayApi.delete(projectId, segmentId, overlayId);
    } catch (e) {
      // already removed from local state
    }
  },

  updateSegment: (segmentId, updates) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Update segment', 'update_segment');
    const updatedProject = deepClone(state.project);
    const segment = updatedProject.segments.find((s) => s.id === segmentId);
    if (!segment) return;
    Object.assign(segment, updates);
    set({ project: updatedProject, ...undo });

    if (state.project) {
      const apiUpdates: Record<string, unknown> = {};
      if (updates.title !== undefined) apiUpdates['title'] = updates.title;
      if (updates.durationSeconds !== undefined) apiUpdates['duration_seconds'] = updates.durationSeconds;
      if (updates.transition !== undefined) apiUpdates['transition'] = updates.transition;
      segmentApi.update(state.project.id, segmentId, apiUpdates).catch(() => {});
    }
  },

  reorderSegments: (segmentIds) => {
    const state = get();
    if (!state.project) return;
    const undo = pushUndo(state, 'Reorder segments', 'reorder_segment');
    const updatedProject = deepClone(state.project);
    const reordered = segmentIds
      .map((id) => updatedProject.segments.find((s) => s.id === id))
      .filter(Boolean) as Segment[];
    reordered.forEach((s, i) => {
      s.orderIndex = i;
    });
    updatedProject.segments = reordered;
    set({ project: updatedProject, ...undo });

    if (state.project) {
      segmentApi.reorder(state.project.id, segmentIds).catch(() => {});
    }
  },

  undo: () => {
    const state = get();
    if (state.undoStack.length === 0) return;
    const entry = state.undoStack[state.undoStack.length - 1];
    const currentSnapshot = JSON.stringify(state.project);
    const restoredProject = JSON.parse(entry.snapshot);
    const redoEntry: HistoryEntry = {
      ...entry,
      id: uuidv4(),
      snapshot: currentSnapshot,
    };
    set({
      project: restoredProject,
      undoStack: state.undoStack.slice(0, -1),
      redoStack: [...state.redoStack, redoEntry],
    });
  },

  redo: () => {
    const state = get();
    if (state.redoStack.length === 0) return;
    const entry = state.redoStack[state.redoStack.length - 1];
    const currentSnapshot = JSON.stringify(state.project);
    const restoredProject = JSON.parse(entry.snapshot);
    const undoEntry: HistoryEntry = {
      ...entry,
      id: uuidv4(),
      snapshot: currentSnapshot,
    };
    set({
      project: restoredProject,
      redoStack: state.redoStack.slice(0, -1),
      undoStack: [...state.undoStack, undoEntry],
    });
  },

  canUndo: () => get().undoStack.length > 0,
  canRedo: () => get().redoStack.length > 0,

  exportLayerJson: () => {
    const state = get();
    if (!state.project) return {};
    return {
      projectId: state.project.id,
      resolution: {
        width: state.project.resolutionWidth,
        height: state.project.resolutionHeight,
      },
      segments: state.project.segments.map((seg) => ({
        id: seg.id,
        orderIndex: seg.orderIndex,
        durationSeconds: seg.durationSeconds,
        transition: seg.transition,
        videoUrl: seg.videoUrl,
        ttsUrl: seg.ttsUrl,
        textOverlays: seg.textOverlays.map((overlay) => ({
          id: overlay.id,
          text: overlay.text,
          fontFamily: overlay.fontFamily,
          fontSize: overlay.fontSize,
          fontColor: overlay.fontColor,
          strokeColor: overlay.strokeColor,
          strokeWidth: overlay.strokeWidth,
          positionX: overlay.positionX,
          positionY: overlay.positionY,
          anchor: overlay.anchor,
          startTime: overlay.startTime,
          endTime: overlay.endTime,
          animation: overlay.animation,
        })),
      })),
    };
  },

  triggerExport: async (projectId: string) => {
    const result = await projectApi.exportJson(projectId);
    return { taskId: result.task_id };
  },

  triggerCompose: async (projectId: string) => {
    const result = await projectApi.compose(projectId);
    return { taskId: result.task_id, readySegments: result.ready_segments };
  },

  clearError: () => set({ error: null }),
}));