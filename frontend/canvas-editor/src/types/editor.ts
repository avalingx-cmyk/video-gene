export type ProjectStatus = 'draft' | 'generating' | 'published' | 'archived' | 'failed';
export type SegmentStatus =
  | 'pending'
  | 'script_ready'
  | 'video_generating'
  | 'video_ready'
  | 'tts_generating'
  | 'tts_ready'
  | 'tts_resync_needed'
  | 'compositing'
  | 'completed'
  | 'failed';
export type TextAnchor = 'top-left' | 'top-center' | 'top-right' | 'center-left' | 'center' | 'center-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
export type TextAnimation = 'none' | 'fade-in' | 'slide-up' | 'slide-down' | 'typewriter' | 'bounce-in';
export type TransitionType = 'none' | 'fade' | 'wipe' | 'slide' | 'dissolve';

export interface TextOverlay {
  id: string;
  segmentId: string;
  text: string;
  fontFamily: string;
  fontSize: number;
  fontColor: string;
  strokeColor: string;
  strokeWidth: number;
  positionX: number;
  positionY: number;
  anchor: TextAnchor;
  startTime: number;
  endTime: number;
  animation: TextAnimation;
}

export interface Segment {
  id: string;
  projectId: string;
  orderIndex: number;
  title: string;
  narrationText: string | null;
  videoPrompt: string;
  durationSeconds: number;
  transition: TransitionType;
  status: SegmentStatus;
  videoUrl: string | null;
  videoLocalPath: string | null;
  actualDurationSeconds: number | null;
  ttsUrl: string | null;
  ttsLocalPath: string | null;
  ttsActualDuration: number | null;
  errorMessage: string | null;
  thumbnailPath: string | null;
  previewPath: string | null;
  textOverlays: TextOverlay[];
  isDeleted: boolean;
  cost: number;
  createdAt: string;
  updatedAt: string;
}

export interface VideoProject {
  id: string;
  userId: string;
  title: string;
  prompt: string;
  style: string;
  resolutionWidth: number;
  resolutionHeight: number;
  status: ProjectStatus;
  outputUrl: string | null;
  errorMessage: string | null;
  publishedAt: string | null;
  isArchived: boolean;
  segments: Segment[];
  createdAt: string;
  updatedAt: string;
}

export interface HistoryEntry {
  id: string;
  timestamp: number;
  type: 'add_overlay' | 'update_overlay' | 'delete_overlay' | 'move_overlay' | 'reorder_segment' | 'update_segment';
  description: string;
  snapshot: string;
}

export type PreviewQuality = '360p' | '480p' | '1080p';

export const PREVIEW_RESOLUTIONS: Record<PreviewQuality, { width: number; height: number; bitrate: string }> = {
  '360p': { width: 216, height: 384, bitrate: '500k' },
  '480p': { width: 288, height: 512, bitrate: '1M' },
  '1080p': { width: 1080, height: 1920, bitrate: '5M' },
};

export const CANVAS_ASPECT_RATIO = 9 / 16;

export const DEFAULT_OVERLAY: Omit<TextOverlay, 'id' | 'segmentId'> = {
  text: 'New Text',
  fontFamily: 'Arial',
  fontSize: 48,
  fontColor: '#FFFFFF',
  strokeColor: '#000000',
  strokeWidth: 2,
  positionX: 0.5,
  positionY: 0.5,
  anchor: 'center',
  startTime: 0,
  endTime: 10,
  animation: 'none',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  script_ready: 'Script Ready',
  video_generating: 'Generating',
  video_ready: 'Video Ready',
  tts_generating: 'TTS Generating',
  tts_ready: 'TTS Ready',
  tts_resync_needed: 'TTS Resync',
  compositing: 'Compositing',
  completed: 'Completed',
  failed: 'Failed',
};