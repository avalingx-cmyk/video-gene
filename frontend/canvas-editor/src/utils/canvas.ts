export function normalizeToCanvas(
  normX: number,
  normY: number,
  canvasWidth: number,
  canvasHeight: number,
  anchor: string = 'center'
): { x: number; y: number } {
  let x = normX * canvasWidth;
  let y = normY * canvasHeight;

  switch (anchor) {
    case 'top-left': break;
    case 'top-center': x -= canvasWidth / 2; break;
    case 'top-right': x -= canvasWidth; break;
    case 'center-left': y -= canvasHeight / 2; break;
    case 'center': x -= canvasWidth / 2; y -= canvasHeight / 2; break;
    case 'center-right': x -= canvasWidth; y -= canvasHeight / 2; break;
    case 'bottom-left': y -= canvasHeight; break;
    case 'bottom-center': x -= canvasWidth / 2; y -= canvasHeight; break;
    case 'bottom-right': x -= canvasWidth; y -= canvasHeight; break;
  }

  return { x, y };
}

export function canvasToNormalized(
  canvasX: number,
  canvasY: number,
  canvasWidth: number,
  canvasHeight: number
): { x: number; y: number } {
  return {
    x: Math.max(0, Math.min(1, canvasX / canvasWidth)),
    y: Math.max(0, Math.min(1, canvasY / canvasHeight)),
  };
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 10);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms}`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function computeCanvasSize(
  containerWidth: number,
  containerHeight: number,
  aspectRatio: number
): { width: number; height: number } {
  const containerRatio = containerWidth / containerHeight;
  if (containerRatio > aspectRatio) {
    const height = containerHeight;
    const width = height * aspectRatio;
    return { width, height };
  }
  const width = containerWidth;
  const height = width / aspectRatio;
  return { width, height };
}

export const FONT_LIST = [
  'Arial',
  'Helvetica',
  'Georgia',
  'Times New Roman',
  'Courier New',
  'Verdana',
  'Impact',
  'Comic Sans MS',
  'Trebuchet MS',
  'Palatino Linotype',
];

export const ANIMATION_OPTIONS: { value: string; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'fade-in', label: 'Fade In' },
  { value: 'slide-up', label: 'Slide Up' },
  { value: 'slide-down', label: 'Slide Down' },
  { value: 'typewriter', label: 'Typewriter' },
  { value: 'bounce-in', label: 'Bounce In' },
];

export const ANCHOR_OPTIONS: { value: string; label: string }[] = [
  { value: 'top-left', label: 'Top Left' },
  { value: 'top-center', label: 'Top Center' },
  { value: 'top-right', label: 'Top Right' },
  { value: 'center-left', label: 'Center Left' },
  { value: 'center', label: 'Center' },
  { value: 'center-right', label: 'Center Right' },
  { value: 'bottom-left', label: 'Bottom Left' },
  { value: 'bottom-center', label: 'Bottom Center' },
  { value: 'bottom-right', label: 'Bottom Right' },
];

export const TRANSITION_OPTIONS: { value: string; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'fade', label: 'Fade' },
  { value: 'wipe', label: 'Wipe' },
  { value: 'slide', label: 'Slide' },
  { value: 'dissolve', label: 'Dissolve' },
];