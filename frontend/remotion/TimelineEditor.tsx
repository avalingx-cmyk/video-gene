import React, { useState, useEffect, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

export interface SegmentData {
  id: string;
  title: string;
  narration_text: string | null;
  video_prompt: string;
  duration_seconds: number;
  order_index: number;
  status: string;
  video_url: string | null;
  thumbnail_path: string | null;
}

export interface ProjectData {
  id: string;
  title: string;
  prompt: string;
  style: string;
  status: ProjectStatus;
  segments: SegmentData[];
}

export type ProjectStatus = "draft" | "generating" | "published" | "archived" | "failed";

interface TimelineEditorProps {
  projectId: string;
  apiBase?: string;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  script_ready: "Script Ready",
  video_generating: "Generating",
  video_ready: "Video Ready",
  tts_generating: "TTS Generating",
  tts_ready: "TTS Ready",
  tts_resync_needed: "TTS Resync Needed",
  compositing: "Compositing",
  completed: "Completed",
  failed: "Failed",
};

function SegmentCard({ segment }: { segment: SegmentData }) {
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
      className="segment-card"
      {...attributes}
      {...listeners}
    >
      <div className="segment-thumbnail">
        {segment.thumbnail_path ? (
          <img src={segment.thumbnail_path} alt={segment.title} />
        ) : (
          <div className="segment-placeholder" />
        )}
      </div>
      <div className="segment-info">
        <div className="segment-title">{segment.title}</div>
        <div className="segment-meta">
          <span className="segment-duration">{segment.duration_seconds}s</span>
          <span className={`segment-status status-${segment.status}`}>
            {STATUS_LABELS[segment.status] || segment.status}
          </span>
        </div>
        {segment.narration_text && (
          <div className="segment-narration">{segment.narration_text}</div>
        )}
      </div>
    </div>
  );
}

function SortableSegmentList({
  segments,
  onReorder,
}: {
  segments: SegmentData[];
  onReorder: (newSegments: SegmentData[]) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = segments.findIndex((s) => s.id === active.id);
    const newIndex = segments.findIndex((s) => s.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = arrayMove(segments, oldIndex, newIndex);
    onReorder(reordered);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={segments.map((s) => s.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="segment-lane">
          {segments.map((segment) => (
            <SegmentCard key={segment.id} segment={segment} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

export default function TimelineEditor({ projectId, apiBase = "" }: TimelineEditorProps) {
  const [project, setProject] = useState<ProjectData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const fetchProject = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/projects/${projectId}`);
      if (!res.ok) throw new Error(`Failed to fetch project: ${res.statusText}`);
      const data: ProjectData = await res.json();
      setProject(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [projectId, apiBase]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  async function persistReorder(reordered: SegmentData[]) {
    const segmentIds = reordered.map((s) => s.id);
    const res = await fetch(`${apiBase}/api/v1/projects/${projectId}/segments/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segment_ids: segmentIds }),
    });
    if (!res.ok) throw new Error("Failed to persist reorder");
    return res.json();
  }

  async function handleReorder(newSegments: SegmentData[]) {
    setProject((prev) =>
      prev ? { ...prev, segments: newSegments } : prev
    );
    try {
      await persistReorder(newSegments);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reorder failed");
      fetchProject();
    }
  }

  async function handlePublish() {
    setPublishing(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/projects/${projectId}/publish`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Publish failed: ${res.statusText}`);
      await fetchProject();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  async function handleArchive() {
    setArchiving(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/projects/${projectId}/archive`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Archive failed: ${res.statusText}`);
      await fetchProject();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Archive failed");
    } finally {
      setArchiving(false);
    }
  }

  if (loading && !project) return <div className="timeline-loading">Loading project...</div>;
  if (error && !project) return <div className="timeline-error">Error: {error}</div>;
  if (!project) return null;

  return (
    <div className="timeline-editor">
      <div className="timeline-header">
        <h2 className="timeline-title">{project.title}</h2>
        <div className="timeline-actions">
          <button
            className="btn-publish"
            onClick={handlePublish}
            disabled={publishing || project.status === "published"}
          >
            {publishing ? "Publishing..." : "Publish"}
          </button>
          <button
            className="btn-archive"
            onClick={handleArchive}
            disabled={archiving || project.status === "archived"}
          >
            {archiving ? "Archiving..." : "Archive"}
          </button>
        </div>
      </div>

      {error && <div className="timeline-error-banner">{error}</div>}

      <div className="timeline-status">
        Status: <span className={`status-badge ${project.status}`}>{project.status}</span>
      </div>

      <SortableSegmentList
        segments={project.segments}
        onReorder={handleReorder}
      />

      {project.segments.length === 0 && (
        <div className="timeline-empty">No segments yet. Add segments to get started.</div>
      )}
    </div>
  );
}