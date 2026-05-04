import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { computeCanvasSize } from '@/utils/canvas';
import { CANVAS_ASPECT_RATIO } from '@/types/editor';
import CanvasOverlay from './CanvasOverlay';

export default function VideoPreview() {
  const { project, selectedSegmentId, isPlaying, previewQuality, zoom } = useEditorStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 360, height: 640 });
  const { setCurrentTime, setIsPlaying } = useEditorStore();

  const selectedSegment = project?.segments.find((s) => s.id === selectedSegmentId);

  useEffect(() => {
    const updateSize = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const size = computeCanvasSize(rect.width, rect.height, CANVAS_ASPECT_RATIO);
      setCanvasSize({ width: size.width * zoom, height: size.height * zoom });
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [zoom]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !selectedSegment?.videoUrl) return;

    if (isPlaying) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isPlaying, selectedSegment?.videoUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };
    const handleEnded = () => {
      setIsPlaying(false);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('ended', handleEnded);
    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('ended', handleEnded);
    };
  }, [setCurrentTime, setIsPlaying]);

  const previewWidth = previewQuality === '360p' ? 216 : previewQuality === '480p' ? 288 : 1080;
  const videoSrc = selectedSegment?.videoUrl || selectedSegment?.previewPath || '';

  return (
    <div
      ref={containerRef}
      className="flex-1 flex items-center justify-center bg-black relative overflow-hidden"
      style={{ minHeight: 0 }}
    >
      <div
        className="relative"
        style={{ width: canvasSize.width, height: canvasSize.height }}
      >
        {videoSrc ? (
          <video
            ref={videoRef}
            src={videoSrc}
            className="absolute inset-0 w-full h-full object-contain"
            style={{ width: canvasSize.width, height: canvasSize.height }}
            muted={false}
            playsInline
            preload="auto"
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center text-canvas-text-muted text-sm"
            style={{
              width: canvasSize.width,
              height: canvasSize.height,
              background: '#111',
            }}
          >
            <div className="text-center">
              <div className="text-4xl mb-2 opacity-50">&#9654;</div>
              <div>No video source</div>
              {selectedSegment && (
                <div className="text-xs mt-1">{selectedSegment.status}</div>
              )}
            </div>
          </div>
        )}
        <CanvasOverlay canvasWidth={canvasSize.width} canvasHeight={canvasSize.height} />
      </div>
    </div>
  );
}