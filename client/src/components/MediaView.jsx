import { mediaKind, vimeoEmbed, youtubeEmbed } from "../lib/media.js";

// Renderiza el medio según su tipo. Usado en el visor a pantalla completa.
export default function MediaView({ src }) {
  const kind = mediaKind(src);

  if (kind === "none") {
    return <div className="media-empty">Sin medio para esta variante.</div>;
  }

  if (kind === "image") {
    return <img className="media-img" src={src} alt="Demostración del ejercicio" />;
  }

  if (kind === "video") {
    return (
      <video className="media-frame" src={src} controls playsInline preload="metadata">
        Tu navegador no puede reproducir este video.
      </video>
    );
  }

  if (kind === "youtube" || kind === "vimeo") {
    const embed = kind === "youtube" ? youtubeEmbed(src) : vimeoEmbed(src);
    if (embed) {
      return (
        <div className="media-ratio">
          <iframe
            className="media-iframe"
            src={embed}
            title="Video del ejercicio"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      );
    }
  }

  // enlace genérico
  return (
    <a className="btn" href={src} target="_blank" rel="noopener noreferrer">Abrir video ↗</a>
  );
}
