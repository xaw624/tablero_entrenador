export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirmar", onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div className="backdrop" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        {title && <div className="block-title" style={{ marginTop: 0 }}>{title}</div>}
        <p className="muted" style={{ marginTop: 0 }}>{message}</p>
        <div className="row between" style={{ marginTop: 14 }}>
          <button className="btn ghost" onClick={onCancel}>Cancelar</button>
          <button className="btn" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
