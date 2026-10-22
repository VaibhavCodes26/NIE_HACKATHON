import { useEffect, useRef, useState } from 'react';
import { X, ExternalLink, MapPin } from 'lucide-react';
import Img from './Img';
import { DESTINATIONS, commonsImg, commonsPage } from '../data/destinations';
import { CATEGORIES } from '../data/content';
import { ICONS } from './Discovery';
import { useI18n } from '../i18n';

function Modal({ open, onClose, title, children }) {
  const ref = useRef(null);
  const { t } = useI18n();
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="modal" aria-labelledby="modal-title" onClose={onClose}
            onClick={(e) => e.target === ref.current && onClose()}>
      {open && (
        <div className="modal-in">
          <button className="modal-x" onClick={onClose} aria-label={t('close')}><X size={20} /></button>
          <h2 id="modal-title">{title}</h2>
          {children}
        </div>
      )}
    </dialog>
  );
}

function Plan() {
  const { t } = useI18n();
  const [picked, setPicked] = useState([]);
  const [days, setDays] = useState('plan.d2');
  const [saved, setSaved] = useState(false);
  const toggle = (id) => { setSaved(false); setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id])); };
  return (
    <>
      <p>{t('plan.intro')}</p>
      <form onSubmit={(e) => { e.preventDefault(); setSaved(true); }}>
        <fieldset>
          <legend>{t('plan.interests')}</legend>
          <div className="pills">
            {CATEGORIES.map((c) => (
              <label key={c.id} className={`pill ${picked.includes(c.id) ? 'on' : ''}`}>
                <input type="checkbox" checked={picked.includes(c.id)} onChange={() => toggle(c.id)} />
                {t(`cat.${c.id}.t`)}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>{t('plan.days')}</legend>
          <div className="pills">
            {['plan.d1', 'plan.d2', 'plan.d3'].map((k) => (
              <label key={k} className={`pill ${days === k ? 'on' : ''}`}>
                <input type="radio" name="days" checked={days === k} onChange={() => { setSaved(false); setDays(k); }} />
                {t(k)}
              </label>
            ))}
          </div>
        </fieldset>
        <button className="btn btn-primary" type="submit">{t('plan.submit')}</button>
      </form>
      {saved && (
        <p className="notice" role="status">
          {t('plan.saved')} ({picked.map((id) => t(`cat.${id}.t`)).join(', ') || '—'} · {t(days)})
        </p>
      )}
    </>
  );
}

function Help() {
  const { t } = useI18n();
  return <ul className="help-list">{[1, 2, 3, 4, 5].map((n) => <li key={n}>{t(`help.l${n}`)}</li>)}</ul>;
}

function Destination({ id }) {
  const { t } = useI18n();
  const d = DESTINATIONS.find((x) => x.id === id);
  return (
    <>
      <Img src={commonsImg(d.file, 1000)} alt={d.alt} className="modal-img" label={d.name} />
      <p className="modal-sub"><MapPin size={15} aria-hidden="true" /> {d.location} · <span lang="kn">{d.kn}</span></p>
      <p>{d.description}</p>
      <h3>{t('dest.facts')}</h3>
      <ul className="help-list">{d.details.map((x) => <li key={x}>{x}</li>)}</ul>
      <p className="modal-links">
        <a href={d.more} target="_blank" rel="noreferrer">{t('dest.learn')} <ExternalLink size={14} aria-hidden="true" /></a>
        <a href={commonsPage(d.file)} target="_blank" rel="noreferrer">{t('story.photo')} <ExternalLink size={14} aria-hidden="true" /></a>
      </p>
    </>
  );
}

function Category({ id }) {
  const { t } = useI18n();
  const c = CATEGORIES.find((x) => x.id === id);
  const Icon = ICONS[c.icon];
  return (
    <>
      <p className="modal-sub"><Icon size={18} aria-hidden="true" /> {t(`cat.${id}.s`)}</p>
      <p>{c.intro}</p>
      <h3>{t('cat.places')}</h3>
      <ul className="place-list">
        {c.places.map(([n, note]) => <li key={n}><strong>{n}</strong><span>{note}</span></li>)}
      </ul>
    </>
  );
}

export default function Panels({ panel, onClose }) {
  const { t } = useI18n();
  let title = '', body = null;
  if (panel) {
    if (panel.type === 'plan') { title = t('plan.title'); body = <Plan />; }
    if (panel.type === 'help') { title = t('help.title'); body = <Help />; }
    if (panel.type === 'destination') { title = DESTINATIONS.find((d) => d.id === panel.id).heading; body = <Destination id={panel.id} />; }
    if (panel.type === 'category') { title = t(`cat.${panel.id}.t`); body = <Category id={panel.id} />; }
  }
  return <Modal open={!!panel} onClose={onClose} title={title}>{body}</Modal>;
}
