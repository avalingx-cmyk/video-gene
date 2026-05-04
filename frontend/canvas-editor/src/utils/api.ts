const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

import {
  VideoProject,
  Segment,
  TextOverlay,
  ProjectStatus,
  SegmentStatus,
} from '@/types/editor';

interface ApiTextOverlay {
  id: string;
  segment_id: string;
  text: string;
  font_family: string;
  font_size: number;
  font_color: string;
  stroke_color: string;
  stroke_width: number;
  position_x: number;
  position_y: number;
  anchor: string;
  start_time: number;
  end_time: number;
  animation: string;
  created_at: string;
  updated_at: string;
}

interface ApiSegment {
  id: string;
  project_id: string;
  order_index: number;
  title: string;
  narration_text: string | null;
  video_prompt: string;
  duration_seconds: number;
  transition: string;
  status: string;
  video_url: string | null;
  video_local_path: string | null;
  actual_duration_seconds: number | null;
  tts_url: string | null;
  tts_local_path: string | null;
  tts_actual_duration: number | null;
  error_message: string | null;
  thumbnail_path: string | null;
  preview_path: string | null;
  text_overlays: ApiTextOverlay[];
  is_deleted: boolean;
  cost: number;
  created_at: string;
  updated_at: string;
}

interface ApiProject {
  id: string;
  user_id: string;
  title: string;
  prompt: string;
  style: string;
  resolution_width: number;
  resolution_height: number;
  status: string;
  output_url: string | null;
  error_message: string | null;
  segments: ApiSegment[];
  published_at: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

function mapOverlay(o: ApiTextOverlay): TextOverlay {
  return {
    id: o.id,
    segmentId: o.segment_id,
    text: o.text,
    fontFamily: o.font_family,
    fontSize: o.font_size,
    fontColor: o.font_color,
    strokeColor: o.stroke_color,
    strokeWidth: o.stroke_width,
    positionX: o.position_x,
    positionY: o.position_y,
    anchor: o.anchor as TextOverlay['anchor'],
    startTime: o.start_time,
    endTime: o.end_time,
    animation: o.animation as TextOverlay['animation'],
  };
}

function mapSegment(s: ApiSegment): Segment {
  return {
    id: s.id,
    projectId: s.project_id,
    orderIndex: s.order_index,
    title: s.title,
    narrationText: s.narration_text,
    videoPrompt: s.video_prompt,
    durationSeconds: s.duration_seconds,
    transition: s.transition as Segment['transition'],
    status: s.status as SegmentStatus,
    videoUrl: s.video_url,
    videoLocalPath: s.video_local_path,
    actualDurationSeconds: s.actual_duration_seconds,
    ttsUrl: s.tts_url,
    ttsLocalPath: s.tts_local_path,
    ttsActualDuration: s.tts_actual_duration,
    errorMessage: s.error_message,
    thumbnailPath: s.thumbnail_path,
    previewPath: s.preview_path,
    textOverlays: (s.text_overlays || []).map(mapOverlay),
    isDeleted: s.is_deleted,
    cost: s.cost,
    createdAt: s.created_at,
    updatedAt: s.updated_at,
  };
}

function mapProject(p: ApiProject): VideoProject {
  return {
    id: p.id,
    userId: p.user_id,
    title: p.title,
    prompt: p.prompt,
    style: p.style,
    resolutionWidth: p.resolution_width,
    resolutionHeight: p.resolution_height,
    status: p.status as ProjectStatus,
    outputUrl: p.output_url,
    errorMessage: p.error_message,
    publishedAt: p.published_at,
    isArchived: p.is_archived,
    segments: (p.segments || []).map(mapSegment),
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  };
}

// Project API
export const projectApi = {
  get: (projectId: string) =>
    apiFetch<ApiProject>(`/api/v1/projects/${projectId}`).then(mapProject),

  create: (data: { title: string; prompt: string; style?: string }) =>
    apiFetch<ApiProject>('/api/v1/projects/', {
      method: 'POST',
      body: JSON.stringify(data),
    }).then(mapProject),

  exportJson: (projectId: string) =>
    apiFetch<{ project_id: string; task_id: string; status: string }>(
      `/api/v1/projects/${projectId}/export`,
      { method: 'POST' }
    ),

  compose: (projectId: string) =>
    apiFetch<{ task_id: string; project_id: string; status: string; ready_segments: number }>(
      `/api/v1/projects/${projectId}/compose`,
      { method: 'POST' }
    ),
};

// Segment API
export const segmentApi = {
  list: (projectId: string, offset = 0, limit = 50) =>
    apiFetch<{ segments: ApiSegment[]; total: number }>(
      `/api/v1/projects/${projectId}/segments/?offset=${offset}&limit=${limit}`
    ).then((r) => ({
      segments: r.segments.map(mapSegment),
      total: r.total,
    })),

  create: (projectId: string, data: { title: string; video_prompt: string; narration_text?: string; duration_seconds?: number; transition?: string }) =>
    apiFetch<ApiSegment>(`/api/v1/projects/${projectId}/segments/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }).then(mapSegment),

  update: (projectId: string, segmentId: string, data: Record<string, unknown>) =>
    apiFetch<ApiSegment>(`/api/v1/projects/${projectId}/segments/${segmentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }).then(mapSegment),

  delete: (projectId: string, segmentId: string) =>
    apiFetch<void>(`/api/v1/projects/${projectId}/segments/${segmentId}`, {
      method: 'DELETE',
    }),

  reorder: (projectId: string, segmentIds: string[]) =>
    apiFetch<void>(`/api/v1/projects/${projectId}/segments/reorder`, {
      method: 'POST',
      body: JSON.stringify({ segment_ids: segmentIds }),
    }),

  status: (segmentId: string) =>
    apiFetch<{ id: string; status: string; video_url: string | null }>(
      `/api/v1/segments/${segmentId}/status`
    ),
};

// Overlay API
export const overlayApi = {
  list: (projectId: string, segmentId: string) =>
    apiFetch<ApiTextOverlay[]>(
      `/api/v1/projects/${projectId}/segments/${segmentId}/overlays/`
    ).then((list) => list.map(mapOverlay)),

  create: (projectId: string, segmentId: string, data: {
    text: string;
    font_family?: string;
    font_size?: number;
    font_color?: string;
    stroke_color?: string;
    stroke_width?: number;
    position_x?: number;
    position_y?: number;
    anchor?: string;
    start_time?: number;
    end_time?: number;
    animation?: string;
  }) =>
    apiFetch<ApiTextOverlay>(
      `/api/v1/projects/${projectId}/segments/${segmentId}/overlays/`,
      { method: 'POST', body: JSON.stringify(data) }
    ).then(mapOverlay),

  update: (projectId: string, segmentId: string, overlayId: string, data: Record<string, unknown>) =>
    apiFetch<ApiTextOverlay>(
      `/api/v1/projects/${projectId}/segments/${segmentId}/overlays/${overlayId}`,
      { method: 'PUT', body: JSON.stringify(data) }
    ).then(mapOverlay),

  delete: (projectId: string, segmentId: string, overlayId: string) =>
    apiFetch<void>(
      `/api/v1/projects/${projectId}/segments/${segmentId}/overlays/${overlayId}`,
      { method: 'DELETE' }
    ),
};