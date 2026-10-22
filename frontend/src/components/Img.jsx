import { useState } from 'react';
import { ImageOff } from 'lucide-react';

// Image with graceful fallback: never shows a broken-image icon or an empty black box.
export default function Img({ src, alt, className = '', eager = false, label = 'Photo unavailable' }) {
  const [failed, setFailed] = useState(!src);
  if (failed) {
    return (
      <div className={`img-fallback ${className}`} role="img" aria-label={alt}>
        <ImageOff size={22} aria-hidden="true" />
        <span>{label}</span>
      </div>
    );
  }
  return (
    <img
      src={src} alt={alt} className={className}
      loading={eager ? 'eager' : 'lazy'} decoding="async"
      onError={() => setFailed(true)}
    />
  );
}
