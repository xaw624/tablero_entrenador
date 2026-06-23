// Detección del tipo de medio a partir de la cadena (ruta subida o URL externa).

export function mediaKind(src) {
  if (!src) return "none";
  const s = src.trim();
  if (s === "") return "none";
  const low = s.toLowerCase();

  if (/youtube\.com\/watch|youtu\.be\/|youtube\.com\/shorts\//.test(low)) return "youtube";
  if (/vimeo\.com\//.test(low)) return "vimeo";
  if (/\.(mp4|webm|ogg|mov)(\?.*)?$/.test(low)) return "video";
  if (/\.(jpg|jpeg|png|gif|webp|avif|svg)(\?.*)?$/.test(low)) return "image";
  // rutas subidas siempre tienen extensión de imagen (validado en backend)
  if (low.startsWith("/media/")) return "image";
  return "link";
}

export function youtubeEmbed(src) {
  const m = src.match(/(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]{11})/);
  return m ? `https://www.youtube.com/embed/${m[1]}` : null;
}

export function vimeoEmbed(src) {
  const m = src.match(/vimeo\.com\/(\d+)/);
  return m ? `https://player.vimeo.com/video/${m[1]}` : null;
}

export function hasMedia(src) {
  return mediaKind(src) !== "none";
}
