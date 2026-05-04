import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { TextOverlay, CANVAS_ASPECT_RATIO } from '@/types/editor';

interface CanvasOverlayProps {
  canvasWidth: number;
  canvasHeight: number;
}

export default function CanvasOverlay({ canvasWidth, canvasHeight }: CanvasOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const {
    project,
    selectedSegmentId,
    selectedOverlayId,
    currentTime,
    zoom,
    setSelectedOverlay,
    moveTextOverlay,
    updateTextOverlay,
  } = useEditorStore();

  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDirection, setResizeDirection] = useState<string | null>(null);

  const selectedSegment = project?.segments.find((s) => s.id === selectedSegmentId);
  const visibleOverlays = selectedSegment?.textOverlays.filter(
    (o) => currentTime >= o.startTime && currentTime <= o.endTime
  ) ?? [];

  const drawOverlays = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !visibleOverlays) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasWidth * dpr;
    canvas.height = canvasHeight * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    for (const overlay of visibleOverlays) {
      const x = overlay.positionX * canvasWidth;
      const y = overlay.positionY * canvasHeight;

      ctx.save();
      ctx.font = `${overlay.fontSize * zoom}px ${overlay.fontFamily}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      if (overlay.strokeWidth > 0) {
        ctx.strokeStyle = overlay.strokeColor;
        ctx.lineWidth = overlay.strokeWidth * zoom;
        ctx.lineJoin = 'round';
        ctx.strokeText(overlay.text, x, y);
      }

      ctx.fillStyle = overlay.fontColor;

      const alpha = computeAnimationAlpha(overlay, currentTime);
      ctx.globalAlpha = alpha;
      ctx.fillText(overlay.text, x, y);
      ctx.restore();
    }
  }, [visibleOverlays, canvasWidth, canvasHeight, currentTime, zoom]);

  useEffect(() => {
    drawOverlays();
  }, [drawOverlays]);

  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas || !selectedSegment) return;
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let clickedOverlay: TextOverlay | null = null;

      const canvasCtx = canvas.getContext('2d');
      if (!canvasCtx) return;

      for (let i = visibleOverlays.length - 1; i >= 0; i--) {
        const overlay = visibleOverlays[i];
        const ox = overlay.positionX * canvasWidth;
        const oy = overlay.positionY * canvasHeight;
        canvasCtx.font = `${overlay.fontSize * zoom}px ${overlay.fontFamily}`;
        const metrics = canvasCtx.measureText(overlay.text);
        const textW = metrics.width;
        const textH = overlay.fontSize * zoom * 1.2;

        if (
          clickX >= ox - textW / 2 - 4 &&
          clickX <= ox + textW / 2 + 4 &&
          clickY >= oy - textH / 2 - 4 &&
          clickY <= oy + textH / 2 + 4
        ) {
          clickedOverlay = overlay;
          break;
        }
      }

      if (clickedOverlay) {
        setSelectedOverlay(clickedOverlay.id);
        setIsDragging(true);
        setDragOffset({
          x: clickX - clickedOverlay.positionX * canvasWidth,
          y: clickY - clickedOverlay.positionY * canvasHeight,
        });
      } else {
        setSelectedOverlay(null);
      }
    },
    [canvasWidth, canvasHeight, visibleOverlays, zoom, selectedSegment, setSelectedOverlay]
  );

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isDragging || !selectedOverlayId) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const normX = (mouseX - dragOffset.x) / canvasWidth;
      const normY = (mouseY - dragOffset.y) / canvasHeight;

      moveTextOverlay(
        selectedOverlayId,
        Math.max(0, Math.min(1, normX)),
        Math.max(0, Math.min(1, normY))
      );
    },
    [isDragging, selectedOverlayId, dragOffset, canvasWidth, canvasHeight, moveTextOverlay]
  );

  const handleCanvasMouseUp = useCallback(() => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeDirection(null);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mouseup', handleCanvasMouseUp);
      return () => window.removeEventListener('mouseup', handleCanvasMouseUp);
    }
  }, [isDragging, handleCanvasMouseUp]);

  const selectedOverlay = visibleOverlays.find((o) => o.id === selectedOverlayId);

  return (
    <div className="canvas-container" style={{ width: canvasWidth, height: canvasHeight }}>
      <canvas
        ref={canvasRef}
        className={isDragging ? 'canvas-overlay interactive' : 'canvas-overlay interactive'}
        style={{
          width: canvasWidth,
          height: canvasHeight,
          position: 'absolute',
          top: 0,
          left: 0,
        }}
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
      />
      {selectedOverlay && (
        <OverlaySelectionBox
          overlay={selectedOverlay}
          canvasWidth={canvasWidth}
          canvasHeight={canvasHeight}
          zoom={zoom}
          onUpdate={updateTextOverlay}
          canvasRef={canvasRef}
        />
      )}
    </div>
  );
}

function computeAnimationAlpha(overlay: TextOverlay, currentTime: number): number {
  if (overlay.animation === 'none') return 1;
  const elapsed = currentTime - overlay.startTime;
  const duration = overlay.endTime - overlay.startTime;
  const fadeDuration = 0.5;
  switch (overlay.animation) {
    case 'fade-in':
      return Math.min(1, elapsed / fadeDuration);
    case 'slide-up':
    case 'slide-down':
    case 'bounce-in':
    case 'typewriter':
      return Math.min(1, elapsed / fadeDuration);
    default:
      return 1;
  }
}

interface OverlaySelectionBoxProps {
  overlay: TextOverlay;
  canvasWidth: number;
  canvasHeight: number;
  zoom: number;
  onUpdate: (id: string, updates: Partial<TextOverlay>) => void;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}

function OverlaySelectionBox({
  overlay,
  canvasWidth,
  canvasHeight,
  zoom,
  onUpdate,
  canvasRef,
}: OverlaySelectionBoxProps) {
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDir, setResizeDir] = useState<string | null>(null);
  const [startFontSize, setStartFontSize] = useState(overlay.fontSize);
  const [startY, setStartY] = useState(0);

  const handleResizeStart = useCallback(
    (e: React.MouseEvent, direction: string) => {
      e.stopPropagation();
      e.preventDefault();
      setIsResizing(true);
      setResizeDir(direction);
      setStartFontSize(overlay.fontSize);
      setStartY(e.clientY);

      const handleMove = (moveEvent: MouseEvent) => {
        const deltaY = moveEvent.clientY - e.clientY;
        let newFontSize = startFontSize;
        if (direction.includes('n') || direction.includes('s') || direction === 'se' || direction === 'ne' || direction === 'sw' || direction === 'nw') {
          const scale = deltaY > 0 ? 1 + deltaY / 200 : 1 + deltaY / 200;
          newFontSize = Math.max(12, Math.min(200, Math.round(startFontSize * scale)));
        }
        onUpdate(overlay.id, { fontSize: newFontSize });
      };

      const handleUp = () => {
        setIsResizing(false);
        setResizeDir(null);
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('mouseup', handleUp);
      };

      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleUp);
    },
    [overlay.id, overlay.fontSize, startFontSize, onUpdate]
  );

  const canvas = canvasRef.current;
  let textWidth = overlay.fontSize * zoom * overlay.text.length * 0.6;
  let textHeight = overlay.fontSize * zoom * 1.4;
  if (canvas) {
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.font = `${overlay.fontSize * zoom}px ${overlay.fontFamily}`;
      const metrics = ctx.measureText(overlay.text);
      textWidth = metrics.width;
      textHeight = overlay.fontSize * zoom * 1.2;
    }
  }

  const boxX = overlay.positionX * canvasWidth - textWidth / 2;
  const boxY = overlay.positionY * canvasHeight - textHeight / 2;

  return (
    <div
      style={{
        position: 'absolute',
        left: boxX,
        top: boxY,
        width: textWidth,
        height: textHeight,
        border: `2px solid #6366f1`,
        pointerEvents: 'auto',
      }}
    >
      <div className="resize-handle nw" onMouseDown={(e) => handleResizeStart(e, 'nw')} />
      <div className="resize-handle ne" onMouseDown={(e) => handleResizeStart(e, 'ne')} />
      <div className="resize-handle sw" onMouseDown={(e) => handleResizeStart(e, 'sw')} />
      <div className="resize-handle se" onMouseDown={(e) => handleResizeStart(e, 'se')} />
    </div>
  );
}