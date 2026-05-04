import React, { useRef, useCallback, useMemo } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { formatTime } from '@/utils/canvas';

export default function TimelineScrubber() {
  const { project, selectedSegmentId, currentTime, isPlaying, setIsPlaying, setCurrentTime, setSelectedSegment } =
    useEditorStore();
  const trackRef = useRef<HTMLDivElement>(null);

  const segments = project?.segments ?? [];
  const totalDuration = segments.reduce((sum, s) => sum + s.durationSeconds, 0);

  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!trackRef.current || totalDuration === 0) return;
      const rect = trackRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const ratio = x / rect.width;
      const time = ratio * totalDuration;
      setCurrentTime(Math.max(0, Math.min(totalDuration, time)));
    },
    [totalDuration, setCurrentTime]
  );

  const scrubberPosition = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;

  let accumulatedTime = 0;
  const segmentPositions = segments.map((seg) => {
    const start = accumulatedTime;
    accumulatedTime += seg.durationSeconds;
    return {
      id: seg.id,
      title: seg.title,
      start,
      end: accumulatedTime,
      width: (seg.durationSeconds / totalDuration) * 100,
      left: (start / totalDuration) * 100,
      status: seg.status,
      overlays: seg.textOverlays.length,
    };
  });

  const handlePlayPause = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying]);

  return (
    <div className="bg-canvas-surface border-t border-canvas-border">
      <div className="flex items-center gap-2 px-4 py-1 border-b border-canvas-border">
        <button className="btn btn-ghost btn-sm" onClick={handlePlayPause}>
          {isPlaying ? '⏸' : '▶'}
        </button>
        <span className="text-xs text-canvas-text-muted font-mono">
          {formatTime(currentTime)} / {formatTime(totalDuration)}
        </span>
        <div className="flex-1" />
        <span className="text-xs text-canvas-text-muted">
          {segments.length} segment{segments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div
        ref={trackRef}
        className="timeline-track"
        onClick={handleTrackClick}
        style={{ cursor: 'pointer' }}
      >
        {segmentPositions.map((seg) => (
          <div
            key={seg.id}
            className={`timeline-segment ${seg.id === selectedSegmentId ? 'active' : ''}`}
            style={{
              left: `${seg.left}%`,
              width: `${seg.width}%`,
            }}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedSegment(seg.id);
            }}
            title={`${seg.title} (${seg.start.toFixed(1)}s - ${seg.end.toFixed(1)}s)`}
          >
            <span className="truncate">{seg.title}</span>
            {seg.overlays > 0 && (
              <span className="ml-1 text-xs opacity-60">
                [{seg.overlays}]
              </span>
            )}
          </div>
        ))}

        <div
          className="timeline-scrubber"
          style={{ left: `${scrubberPosition}%` }}
        />
      </div>

      <div className="flex items-center gap-0 px-4 h-5 text-xs text-canvas-text-muted">
        {segmentPositions.map((seg) => (
          <div
            key={seg.id}
            className="truncate px-1"
            style={{ width: `${seg.width}%` }}
          >
            {formatTime(seg.start)}
          </div>
        ))}
        <div className="flex-1 text-right">{formatTime(totalDuration)}</div>
      </div>
    </div>
  );
}