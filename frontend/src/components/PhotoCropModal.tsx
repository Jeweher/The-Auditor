import { useEffect, useRef, useState } from "react";

const VIEWPORT = 260; // on-screen crop circle size (px)
const EXPORT_SIZE = 400; // exported image resolution (px)

interface Props {
  file: File;
  onCancel: () => void;
  onConfirm: (blob: Blob) => void;
}

export default function PhotoCropModal({ file, onCancel, onConfirm }: Props) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ startX: number; startY: number; startOffset: { x: number; y: number } } | null>(
    null
  );

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setImgUrl(url);
    const img = new Image();
    img.onload = () => setNatural({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (!imgUrl || !natural) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <p className="text-white">Loading image...</p>
      </div>
    );
  }

  const baseScale = Math.max(VIEWPORT / natural.w, VIEWPORT / natural.h);
  const scaleFactor = baseScale * zoom;
  const dispW = natural.w * scaleFactor;
  const dispH = natural.h * scaleFactor;

  function clampFor(sf: number, w: number, h: number, o: { x: number; y: number }) {
    const mx = Math.max(0, (w - VIEWPORT) / 2);
    const my = Math.max(0, (h - VIEWPORT) / 2);
    return { x: Math.min(mx, Math.max(-mx, o.x)), y: Math.min(my, Math.max(-my, o.y)) };
  }

  function handlePointerDown(e: React.PointerEvent) {
    (e.target as Element).setPointerCapture(e.pointerId);
    dragRef.current = { startX: e.clientX, startY: e.clientY, startOffset: offset };
  }
  function handlePointerMove(e: React.PointerEvent) {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    setOffset(clampFor(scaleFactor, dispW, dispH, { x: dragRef.current.startOffset.x + dx, y: dragRef.current.startOffset.y + dy }));
  }
  function handlePointerUp() {
    dragRef.current = null;
  }

  function handleZoomChange(v: number) {
    setZoom(v);
    const sf = baseScale * v;
    setOffset((o) => clampFor(sf, natural.w * sf, natural.h * sf, o));
  }

  function handleConfirm() {
    const dispLeft = (VIEWPORT - dispW) / 2 + offset.x;
    const dispTop = (VIEWPORT - dispH) / 2 + offset.y;
    const sx = -dispLeft / scaleFactor;
    const sy = -dispTop / scaleFactor;
    const sSize = VIEWPORT / scaleFactor;

    const canvas = document.createElement("canvas");
    canvas.width = EXPORT_SIZE;
    canvas.height = EXPORT_SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, sx, sy, sSize, sSize, 0, 0, EXPORT_SIZE, EXPORT_SIZE);
      canvas.toBlob((blob) => blob && onConfirm(blob), "image/jpeg", 0.9);
    };
    img.src = imgUrl;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 dark:bg-slate-800">
        <h2 className="text-center text-lg font-bold text-slate-900 dark:text-white">Adjust your photo</h2>
        <p className="mt-1 text-center text-xs text-slate-500 dark:text-slate-400">
          Drag to reposition, use the slider to zoom.
        </p>

        <div
          className="relative mx-auto mt-5 touch-none overflow-hidden rounded-full border-4 border-brand-500"
          style={{ width: VIEWPORT, height: VIEWPORT, cursor: "grab" }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          <img
            src={imgUrl}
            alt=""
            draggable={false}
            className="pointer-events-none absolute select-none"
            style={{
              width: dispW,
              height: dispH,
              left: (VIEWPORT - dispW) / 2 + offset.x,
              top: (VIEWPORT - dispH) / 2 + offset.y,
            }}
          />
        </div>

        <div className="mt-4 flex items-center gap-3">
          <span className="text-xs text-slate-400">🔍</span>
          <input
            type="range"
            min={1}
            max={3}
            step={0.01}
            value={zoom}
            onChange={(e) => handleZoomChange(Number(e.target.value))}
            className="flex-1 accent-brand-500"
          />
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
          >
            Save photo
          </button>
        </div>
      </div>
    </div>
  );
}