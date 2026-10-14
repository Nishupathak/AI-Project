import { useState } from "react";
import Icon from "../components/Icon.jsx";
import { run, usePoll } from "../api.js";
import { useToast } from "../toasts.jsx";

export default function Gallery() {
  const [photos] = usePoll("/photos", 3000, []);
  const [open, setOpen] = useState(null);
  const toast = useToast();
  const list = Array.isArray(photos) ? photos : [];

  const snap = async () => {
    try {
      await run("take a photo");
      toast("Snapshot saved");
    } catch {
      toast("Could not reach the robot", "bad");
    }
  };

  return (
    <div className="page">
      <section className="card">
        <div className="card-title-row">
          <h3 className="card-title"><Icon name="image" size={14} /> Snapshots</h3>
          <button className="btn" onClick={snap}><Icon name="camera" size={16} /> Take photo</button>
        </div>
        {list.length === 0 ? (
          <div className="empty big">No snapshots yet. Say “take a photo” or press the button.</div>
        ) : (
          <div className="gallery">
            {list.map((p) => (
              <button key={p.name} className="thumb" onClick={() => setOpen(p)}>
                <img src={p.url} alt={p.name} loading="lazy" />
                <span>{p.name.replace("photo_", "").replace(".jpg", "")}</span>
              </button>
            ))}
          </div>
        )}
      </section>
      {open ? (
        <div className="lightbox" onClick={() => setOpen(null)}>
          <img src={open.url} alt={open.name} />
          <span className="lightbox-name">{open.name} · click anywhere to close</span>
        </div>
      ) : null}
    </div>
  );
}
