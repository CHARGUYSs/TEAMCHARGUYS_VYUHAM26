import { useEffect, useState } from 'react';
import { Film, Image as ImageIcon, Trash2 } from 'lucide-react';

/** Private family media is streamed with the account token; no public static URLs. */
function PrivateMedia({ item, token }) {
  const isVideo = item.content_type.startsWith('video/');
  const [open, setOpen] = useState(!isVideo);
  const [src, setSrc] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    if (!open || !token) return;
    let cancelled = false;
    let resource = '';
    fetch(`/api/memories/media/${item.id}`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error(`File unavailable (${response.status})`);
        return response.blob();
      })
      .then(blob => {
        if (cancelled) return;
        resource = URL.createObjectURL(blob);
        setSrc(resource);
      })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; if (resource) URL.revokeObjectURL(resource); };
  }, [item.id, token, open]);
  return <div className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white">
    {isVideo ? (src ? <video src={src} controls playsInline preload="metadata" className="max-h-64 w-full bg-slate-950" />
      : <button type="button" onClick={() => setOpen(true)} className="flex min-h-28 w-full flex-col items-center justify-center gap-2 bg-slate-800 p-4 text-white">
        <Film size={24} />{open ? 'Loading video…' : 'Load video securely'}
      </button>)
      : (src ? <img loading="lazy" src={src} alt={item.original_name || 'Saved memory photo'} className="max-h-64 w-full object-contain" />
        : <div className="flex min-h-28 items-center justify-center gap-2 bg-slate-100 p-4 text-slate-500"><ImageIcon size={19} /> Loading photo…</div>)}
    {error && <p role="alert" className="p-2 text-xs text-rose-700">{error}</p>}
    <p className="truncate px-3 py-2 text-xs text-slate-500" title={item.original_name}>{item.original_name}</p>
  </div>;
}

export default function MemoryMediaGallery({ memory, token, onDeleteMedia }) {
  return <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
    {memory.photo_url && !memory.photo_url.includes('default-memory.jpg') &&
      <img loading="lazy" src={memory.photo_url} alt={`Photo: ${memory.title}`} className="max-h-60 w-full rounded-xl bg-slate-100 object-contain" />}
    {(memory.media || []).map(item => <div key={item.id} className="min-w-0">
      <PrivateMedia item={item} token={token} />
      {onDeleteMedia && <button type="button" onClick={() => onDeleteMedia(item)} className="mt-1 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-bold text-rose-700 hover:bg-rose-50">
        <Trash2 size={14} /> Remove file
      </button>}
    </div>)}
  </div>;
}
