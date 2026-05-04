import dynamic from 'next/dynamic';

const CanvasEditor = dynamic(() => import('@/CanvasEditor'), { ssr: false });

export default function Home() {
  return (
    <main className="h-screen">
      <CanvasEditor />
    </main>
  );
}