import { useCallback, useEffect, useRef } from 'react';
import { useEditorStore } from '@/store/editorStore';

export function useVideoPlayer(videoUrl: string | null) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { setCurrentTime, setIsPlaying, isPlaying, currentTime } = useEditorStore();

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

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isPlaying) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isPlaying]);

  const seekTo = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    setCurrentTime(time);
  }, [setCurrentTime]);

  const togglePlay = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying]);

  return { videoRef, seekTo, togglePlay };
}

export function useKeyboardShortcuts() {
  const { undo, redo, deleteTextOverlay, selectedOverlayId, selectedSegmentId, addTextOverlay } = useEditorStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMeta = e.metaKey || e.ctrlKey;

      if (isMeta && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (isMeta && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      } else if (isMeta && e.key === 'y') {
        e.preventDefault();
        redo();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedOverlayId && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
          e.preventDefault();
          deleteTextOverlay(selectedOverlayId);
        }
      } else if (e.key === 't' && isMeta) {
        e.preventDefault();
        if (selectedSegmentId) {
          addTextOverlay(selectedSegmentId);
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo, deleteTextOverlay, selectedOverlayId, selectedSegmentId, addTextOverlay]);
}