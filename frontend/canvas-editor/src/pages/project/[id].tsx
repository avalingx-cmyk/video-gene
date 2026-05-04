import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';

const CanvasEditor = dynamic(() => import('@/CanvasEditor'), { ssr: false });

export default function ProjectPage() {
  const router = useRouter();
  const { id } = router.query;

  if (!id || typeof id !== 'string') {
    return (
      <div className="h-screen flex items-center justify-center bg-canvas-bg">
        <div className="text-center">
          <div className="text-canvas-text-muted">Loading project...</div>
        </div>
      </div>
    );
  }

  return (
    <main className="h-screen">
      <CanvasEditor projectId={id} />
    </main>
  );
}