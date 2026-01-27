const { useEffect, useMemo, useRef, useState } = React;

const getCookie = (name) => {
  if (!name) return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
};

const setCookie = (name, value, days = 365) => {
  const maxAge = Math.max(0, Math.floor(days * 24 * 60 * 60));
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; SameSite=Lax`;
};

const GA_MEASUREMENT_ID = 'G-GCJS0MM52K';

function trackVirtualPageview({ path, title }) {
  if (typeof gtag !== 'function') return;

  if (title) document.title = title;

  gtag('event', 'page_view', {
    page_location: window.location.origin + path,
    page_path: path,
    page_title: document.title
  });
}

const normalizeLang = (lang) => {
  const code = String(lang || '').trim().toLowerCase();
  if (!code) return '';
  return code.includes('-') ? code.split('-')[0] : code;
};

const pickUiLang = (preferred, supported, fallback) => {
  const p = normalizeLang(preferred);
  if (supported.includes(p)) return p;
  return fallback;
};

const Icon = ({ name, size = 24, className = '' }) => {
  const icon = window.lucide?.icons?.[name];
  if (!icon) return null;
  const svg = icon.toSvg({ width: size, height: size });
  return (
    <span
      className={className}
      style={{ display: 'inline-flex', lineHeight: 0 }}
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

const firstOrNull = (arr) => (Array.isArray(arr) && arr.length ? arr[0] : null);

const AdContainer = ({ type, title = "", className = "" }) => (
  <div className={`bg-slate-50 border-2 border-dashed border-slate-200 rounded-[2rem] flex flex-col items-center justify-center p-6 transition-all hover:border-blue-200 group overflow-hidden ${className}`}>
    <span className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] mb-4 group-hover:text-blue-500 transition-colors">{title}</span>
    <div className="bg-white/50 border border-slate-100 rounded-3xl flex flex-col items-center justify-center text-slate-300 w-full h-full min-h-[100px] shadow-sm p-4">
      <Icon name="layout" size={24} className="mb-2 opacity-20" />
      <span className="font-mono text-[9px] uppercase tracking-widest opacity-40">
        {type === 'sidebar' ? 'Vertical Responsive' : 'Responsive Banner'}
      </span>
    </div>
  </div>
);

const safeCopyText = async (text) => {
  if (!text) return false;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // ignore and fall back
  }

  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textArea);
    return ok;
  } catch {
    return false;
  }
};

const App = () => {
  const [nav, setNav] = useState(null);
  const [navError, setNavError] = useState(null);
  const [viewMode, setViewMode] = useState('docs');
  const [activeContextId, setActiveContextId] = useState(null);
  const [activeLangId, setActiveLangId] = useState(null);
  const [activeItemId, setActiveItemId] = useState(null);
  const [contentHtml, setContentHtml] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [popupItem, setPopupItem] = useState(null);
  const [popupTitle, setPopupTitle] = useState('');
  const [popupHtml, setPopupHtml] = useState('');
  const [isPopupLoading, setIsPopupLoading] = useState(false);
  const currentYear = new Date().getFullYear();

  const initRef = useRef(null);

  const docsContexts = nav?.docs?.contexts ?? [];
  const codeLanguages = nav?.code?.languages ?? [];
  const footerItems = nav?.footer?.items ?? [];

  const i18nCookieName = nav?.i18n?.cookie ?? 'odata_lang';
  const supportedUiLangs = (nav?.i18n?.languages ?? []).map(l => normalizeLang(l.id)).filter(Boolean);
  const defaultUiLang = normalizeLang(nav?.i18n?.default) || 'de';
  const [uiLang, setUiLang] = useState(() => {
    // nav might not be loaded yet; use defaults
    const supported = ['ja', 'pt', 'es', 'fr', 'zh', 'hi', 'de', 'en'];
    const cookie = getCookie('odata_lang');
    const detected = normalizeLang(navigator?.language);
    return pickUiLang(cookie || detected, supported, 'de');
  });

  const uiLanguages = nav?.i18n?.languages ?? [
    { id: 'ja', title: 'JA' },
    { id: 'pt', title: 'PT' },
    { id: 'es', title: 'ES' },
    { id: 'fr', title: 'FR' },
    { id: 'zh', title: 'ZH' },
    { id: 'hi', title: 'HI' },
    { id: 'de', title: 'DE' },
    { id: 'en', title: 'EN' },
  ];

  const activeContext = useMemo(() => {
    if (!docsContexts.length || !activeContextId) return null;
    return docsContexts.find(c => c.id === activeContextId) ?? null;
  }, [docsContexts, activeContextId]);

  const activeLanguage = useMemo(() => {
    if (!codeLanguages.length || !activeLangId) return null;
    return codeLanguages.find(l => l.id === activeLangId) ?? null;
  }, [codeLanguages, activeLangId]);

  const currentGroups = useMemo(() => {
    if (viewMode === 'code') return activeLanguage?.groups ?? [];
    return activeContext?.groups ?? [];
  }, [viewMode, activeContext, activeLanguage]);

  const activeItem = useMemo(() => {
    const items = currentGroups.flatMap(g => g.items ?? []);
    if (!items.length || !activeItemId) return null;
    return items.find(i => i.id === activeItemId) ?? null;
  }, [currentGroups, activeItemId]);

  const lt = (obj) => {
    if (!obj) return '';
    if (obj.titles && typeof obj.titles === 'object') {
      return obj.titles[uiLang] || obj.titles[defaultUiLang] || obj.titles.en || obj.titles.de || obj.title || '';
    }
    return obj.title || '';
  };

  const ll = (key) => {
    const labels = nav?.labels ?? {};
    const entry = labels[key];
    if (!entry) return key;
    return entry[uiLang] || entry[defaultUiLang] || entry.en || entry.de || key;
  };

  const applyTokenReplacements = (html) => {
    const ctxTitle = lt(activeContext);
    const langTitle = lt(activeLanguage);
    return String(html)
      .replaceAll('{{activeContext}}', ctxTitle)
      .replaceAll('{{activeLanguage}}', langTitle)
      .replaceAll('{{uiLang}}', uiLang)
      .replaceAll('{{year}}', String(currentYear));
  };

  const buildLocalizedCandidates = (file) => {
    const base = String(file || '').trim();
    if (!base) return [];

    // If file already ends with _xx.html, don't derive again.
    const alreadyLocalized = /_[a-z]{2}\.html$/i.test(base);
    if (alreadyLocalized) return [base];

    if (/\.html$/i.test(base) && uiLang) {
      const localized = base.replace(/\.html$/i, `_${uiLang}.html`);
      if (localized !== base) return [localized, base];
    }

    return [base];
  };

  const fetchFirstOk = async (files) => {
    const candidates = (files ?? []).filter(Boolean);
    let lastStatus = null;
    for (const f of candidates) {
      const response = await fetch(f, { cache: 'no-store' });
      lastStatus = response.status;
      if (response.ok) {
        return { file: f, text: await response.text() };
      }
    }
    const suffix = lastStatus ? `HTTP ${lastStatus}` : 'Unbekannter Fehler';
    throw new Error(suffix);
  };

  const resolveItemFile = (item) => {
    if (!item) return null;
    const files = item.files;
    if (files && typeof files === 'object') {
      return files[uiLang] || files[defaultUiLang] || files.en || files.de || null;
    }
    return item.file ?? null;
  };

  const loadItem = async (item) => {
    const file = resolveItemFile(item);

    // GA4 & Navigation
    const path = '/' + (item?.id || '');
    const title = lt(item);
    
    if (item?.id) {
        history.pushState({ 
            path, 
            fragmentUrl: file, 
            title, 
            itemId: item.id, 
            init: item.init,
            // Context restoration
            contextId: activeContextId,
            langId: activeLangId,
            viewMode: viewMode 
        }, '', path);
    }
    trackVirtualPageview({ path, title });

    await loadSection(file, item?.id ?? null, item?.init ?? null);
  };

  const runInitHook = () => {
    if (!initRef.current) return;
    const hookName = initRef.current;
    initRef.current = null;

    if (hookName === 'ai_generator') {
      const root = document.getElementById('content-body');
      if (!root) return;

      const urlEl = root.querySelector('[data-ai-url]');
      const langEl = root.querySelector('[data-ai-lang]');
      const authEl = root.querySelector('[data-ai-auth]');
      const verEl = root.querySelector('[data-ai-version]');
      const promptEl = root.querySelector('[data-ai-prompt]');
      const btnEl = root.querySelector('[data-ai-generate]');
      const outEl = root.querySelector('[data-ai-output]');
      const copyEl = root.querySelector('[data-ai-copy]');

      if (!urlEl || !langEl || !authEl || !verEl || !promptEl || !btnEl || !outEl) return;

      const setBusy = (busy) => {
        btnEl.disabled = busy || !urlEl.value;
        btnEl.setAttribute('aria-busy', busy ? 'true' : 'false');
        btnEl.textContent = busy ? 'Gemini berechnet OData-Logik…' : 'Optimierten Code generieren';
      };

      urlEl.addEventListener('input', () => setBusy(false), { passive: true });

      const generate = async () => {
        if (!urlEl.value) return;
        setBusy(true);
        outEl.textContent = '';

        const apiKey = '';
        const systemPrompt = "Du bist ein OData-Experte. Generiere präzisen, gut kommentierten Code für den Zugriff auf eine OData-API. Nutze moderne Best Practices der jeweiligen Sprache. Achte penibel auf die gewählte OData-Version und Auth-Methode.";
        const userQuery = `Generiere Code in ${langEl.value} für die OData-URL: ${urlEl.value}.\nDetails:\n- OData Version: ${verEl.value}\n- Authentifizierung: ${authEl.value}\n- Kontext: ${lt(activeContext)}\n- Zusätzliche Wünsche: ${promptEl.value}\nGib NUR den Code-Block zurück, keine Einleitung. Verwende Platzhalter für Zugangsdaten.`;

        let retries = 0;
        const maxRetries = 5;

        const attemptRequest = async (delayMs) => {
          try {
            const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                contents: [{ parts: [{ text: userQuery }] }],
                systemInstruction: { parts: [{ text: systemPrompt }] }
              })
            });

            if (!response.ok) throw new Error('API Error');

            const result = await response.json();
            const text = result.candidates?.[0]?.content?.parts?.[0]?.text ?? '';
            const cleanedText = String(text).replace(/```[a-z]*\n/g, '').replace(/\n```/g, '');
            outEl.textContent = cleanedText;
            if (copyEl) copyEl.setAttribute('data-copy-text', cleanedText);
          } catch (e) {
            if (retries < maxRetries) {
              retries++;
              const nextDelay = delayMs * 2;
              await new Promise(res => setTimeout(res, nextDelay));
              return attemptRequest(nextDelay);
            }
            outEl.textContent = 'Fehler: Der Code konnte nicht generiert werden. Bitte prüfen Sie Ihre Verbindung oder versuchen Sie es später erneut.';
          }
        };

        await attemptRequest(1000);
        setBusy(false);
      };

      btnEl.addEventListener('click', (e) => {
        e.preventDefault();
        generate();
      });

      setBusy(false);
    }

    if (hookName === 'query_builder') {
      const root = document.getElementById('content-body');
      if (!root) return;

      const baseUrl = root.querySelector('#baseUrl');
      const entitySet = root.querySelector('#entitySet');
      const select = root.querySelector('#select');
      const orderby = root.querySelector('#orderby');
      const top = root.querySelector('#top');
      const skip = root.querySelector('#skip');
      const filterContainer = root.querySelector('#filterContainer');
      const addFilterBtn = root.querySelector('#addFilterBtn');
      const generatedUrl = root.querySelector('#generatedUrl');
      const copyBtn = root.querySelector('#copyBtn');

      if (!generatedUrl) return;

      const updateUrl = () => {
        let url = (baseUrl?.value || '').trim();
        const set = (entitySet?.value || '').trim();
        
        if (url && !url.endsWith('/')) url += '/';
        url += set;

        const params = [];
        const filters = [];
        
        root.querySelectorAll('.filter-row').forEach(row => {
            const field = row.querySelector('.filter-field').value.trim();
            const type = row.querySelector('.filter-type').value;
            const op = row.querySelector('.filter-op').value;
            const val = row.querySelector('.filter-value').value.trim();
            
            if (field && val) {
                let finalVal = val;
                
                switch(type) {
                    case 'string':
                        if (!val.startsWith("'")) finalVal = `'${val}'`;
                        break;
                    case 'datetime':
                        finalVal = `datetime'${val}'`;
                        break;
                    case 'datetimeoffset':
                        finalVal = `datetimeoffset'${val}'`;
                        break;
                    case 'guid':
                        finalVal = `guid'${val}'`;
                        break;
                    // numeric, boolean: keep raw
                }

                if (op === 'startswith' || op === 'substringof') {
                     filters.push(`${op}(${field}, ${finalVal})`);
                } else {
                    filters.push(`${field} ${op} ${finalVal}`);
                }
            }
        });
        
        if (filters.length > 0) {
            params.push('$filter=' + filters.join(' and '));
        }

        if (select?.value) params.push('$select=' + select.value.trim());
        if (orderby?.value) params.push('$orderby=' + orderby.value.trim());
        if (top?.value) params.push('$top=' + top.value.trim());
        if (skip?.value) params.push('$skip=' + skip.value.trim());
        
        const formatVal = root.querySelector('input[name="format"]:checked')?.value || 'json';
        params.push('$format=' + formatVal);

        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        generatedUrl.textContent = url;
        if (copyBtn) copyBtn.setAttribute('data-copy-text', url);
      };

      [baseUrl, entitySet, select, orderby, top, skip].forEach(el => {
          if (el) el.addEventListener('input', updateUrl);
      });

      root.querySelectorAll('input[name="format"]').forEach(radio => {
          radio.addEventListener('change', updateUrl);
      });

      if (addFilterBtn) {
          addFilterBtn.addEventListener('click', () => {
              const div = document.createElement('div');
              div.className = 'flex flex-wrap md:flex-nowrap gap-2 filter-row items-center animate-in fade-in zoom-in-95 duration-200';
              div.innerHTML = `
                 <input type="text" placeholder="Field" class="filter-field flex-1 p-2 border border-slate-300 rounded-md font-mono text-sm min-w-[120px]">
                 <select class="filter-type p-2 border border-slate-300 rounded-md font-mono text-sm bg-white min-w-[100px]">
                     <option value="string">String</option>
                     <option value="numeric">Number</option>
                     <option value="boolean">Boolean</option>
                     <option value="date">Date (v4)</option>
                     <option value="datetime">DateTime</option>
                     <option value="datetimeoffset">DTOffset</option>
                     <option value="guid">GUID</option>
                 </select>
                 <select class="filter-op p-2 border border-slate-300 rounded-md font-mono text-sm bg-white">
                     <option value="eq">eq</option>
                     <option value="ne">ne</option>
                     <option value="gt">gt</option>
                     <option value="ge">ge</option>
                     <option value="lt">lt</option>
                     <option value="le">le</option>
                     <option value="startswith">startswith</option>
                     <option value="substringof">substringof</option>
                 </select>
                 <input type="text" placeholder="Value" class="filter-value flex-1 p-2 border border-slate-300 rounded-md font-mono text-sm min-w-[120px]">
                 <button type="button" class="text-slate-400 hover:text-red-500 px-2 text-xl font-bold leading-none">&times;</button>
              `;
              div.querySelector('button').addEventListener('click', () => {
                  div.remove();
                  updateUrl();
              });
              div.querySelectorAll('input, select').forEach(el => el.addEventListener('input', updateUrl));
              filterContainer.appendChild(div);
          });
      }
      
      updateUrl();
    }
  };

  const loadSection = async (file, itemId, initHook = null) => {
    if (!file) return;
    setIsLoading(true);
    setNavError(null);
    try {
      const candidates = buildLocalizedCandidates(file);
      const { file: usedFile, text } = await fetchFirstOk(candidates);
      const html = applyTokenReplacements(text);
      setActiveItemId(itemId);
      setContentHtml(html);
      initRef.current = initHook;
    } catch (e) {
      setContentHtml(
        `<div class="space-y-2">` +
          `<h2 class="text-2xl font-extrabold text-red-600">${ll('error_loading')}</h2>` +
          `<p class="text-slate-700 text-sm">${ll('file')}: <code>${file}</code></p>` +
        `</div>`
      );
    } finally {
      setIsLoading(false);
    }
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setPopupItem(null);
    setPopupTitle('');
    setPopupHtml('');
  };

  const openPopup = async (item) => {
    const file = resolveItemFile(item);
    if (!file) return;
    setIsPopupOpen(true);
    setPopupItem(item);
    setPopupTitle(lt(item));
    setIsPopupLoading(true);
    setPopupHtml('');
    try {
      const candidates = buildLocalizedCandidates(file);
      const { text } = await fetchFirstOk(candidates);
      const html = applyTokenReplacements(text);
      setPopupHtml(html);
    } catch {
      setPopupHtml(
        `<div class="space-y-2">` +
          `<h2 class="text-2xl font-extrabold text-red-600">${ll('error_loading')}</h2>` +
          `<p class="text-slate-700 text-sm">${ll('file')}: <code>${file}</code></p>` +
        `</div>`
      );
    } finally {
      setIsPopupLoading(false);
    }
  };

  useEffect(() => {
    const onPopState = async (e) => {
        const state = e.state;
        if (!state) return;
        
        if (state.contextId) setActiveContextId(state.contextId);
        if (state.langId) setActiveLangId(state.langId);
        if (state.viewMode) setViewMode(state.viewMode);
        
        if (state.fragmentUrl) {
           trackVirtualPageview({ path: state.path, title: state.title });
           await loadSection(state.fragmentUrl, state.itemId, state.init);
        }
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const response = await fetch('./navigation.json', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setNav(data);

        const firstContext = firstOrNull(data?.docs?.contexts);
        const firstGroup = firstOrNull(firstContext?.groups);
        const firstItem = firstOrNull(firstGroup?.items);
        const firstFile =
          (firstItem?.files && (firstItem.files[uiLang] || firstItem.files[normalizeLang(data?.i18n?.default)] || firstItem.files.de || firstItem.files.en))
          || firstItem?.file
          || null;
        if (firstContext?.id && firstItem?.id && firstFile) {
          setViewMode('docs');
          setActiveContextId(firstContext.id);
          setActiveLangId(null);

          const path = '/' + firstItem.id;
          const title = lt(firstItem);
          
          history.replaceState({ 
             path, 
             fragmentUrl: firstFile, 
             title, 
             itemId: firstItem.id, 
             init: firstItem.init,
             contextId: firstContext.id,
             langId: null,
             viewMode: 'docs'
          }, '', path);
          
          trackVirtualPageview({ path, title });

          await loadSection(firstFile, firstItem.id, firstItem.init ?? null);
        }
      } catch (e) {
        setNavError('navigation.json konnte nicht geladen werden. Bitte Server starten (http://localhost:8000).');
      }
    })();
  }, []);

  useEffect(() => {
    if (!nav) return;
    const supported = supportedUiLangs.length ? supportedUiLangs : ['ja', 'pt', 'es', 'fr', 'zh', 'hi', 'de', 'en'];
    const cookie = getCookie(i18nCookieName);
    const detected = normalizeLang(navigator?.language);
    const next = pickUiLang(cookie || detected, supported, defaultUiLang || 'de');
    setCookie(i18nCookieName, next);
    // Back-compat if cookie name changed
    if (i18nCookieName !== 'odata_lang') setCookie('odata_lang', next);
    if (next !== uiLang) setUiLang(next);
  }, [nav]);

  useEffect(() => {
    runInitHook();
  }, [contentHtml]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') closePopup();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const root = document.getElementById('content-body');
    if (!root) return;

    const onClick = async (e) => {
      const el = e.target?.closest?.('[data-copy-text],[data-copy-target]');
      if (!el) return;

      const explicit = el.getAttribute('data-copy-text');
      if (explicit != null && explicit !== '') {
        await safeCopyText(explicit);
        return;
      }

      const selector = el.getAttribute('data-copy-target');
      if (!selector) return;
      const container = el.closest('[data-copy-scope]') ?? root;
      const target = container.querySelector(selector);
      const text = target?.innerText ?? target?.textContent ?? '';
      await safeCopyText(text);
    };

    root.addEventListener('click', onClick);
    return () => root.removeEventListener('click', onClick);
  }, []);

  const handleContextClick = async (contextId) => {
    const ctx = docsContexts.find(c => c.id === contextId);
    const firstGroup = firstOrNull(ctx?.groups);
    const firstItem = firstOrNull(firstGroup?.items);
    if (!ctx || !firstItem) return;
    setViewMode('docs');
    setActiveContextId(ctx.id);
    setActiveLangId(null);
    await loadItem(firstItem);
  };

  const handleLangClick = async (langId) => {
    const lang = codeLanguages.find(l => l.id === langId);
    const firstGroup = firstOrNull(lang?.groups);
    const firstItem = firstOrNull(firstGroup?.items);
    if (!lang || !firstItem) return;
    setViewMode('code');
    setActiveLangId(lang.id);
    await loadItem(firstItem);
  };

  const setUiLangAndPersist = (lang) => {
    const supported = supportedUiLangs.length ? supportedUiLangs : ['ja', 'pt', 'es', 'fr', 'zh', 'hi', 'de', 'en'];
    const next = pickUiLang(lang, supported, defaultUiLang || 'de');
    setCookie(i18nCookieName, next);
    if (i18nCookieName !== 'odata_lang') setCookie('odata_lang', next);
    setUiLang(next);
  };

  useEffect(() => {
    // When switching UI language, reload current content/popup if possible.
    if (!nav) return;
    if (activeItem) loadItem(activeItem);
    if (isPopupOpen && popupItem) openPopup(popupItem);
  }, [uiLang]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-blue-100">
      {isPopupOpen && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-slate-950/60" onClick={closePopup} />
          <div className="absolute inset-0 p-4 md:p-10 overflow-y-auto">
            <div className="max-w-4xl mx-auto bg-white rounded-[2rem] border border-slate-200 shadow-2xl">
              <div className="flex items-center justify-between gap-4 px-6 md:px-8 py-5 border-b border-slate-100">
                <div className="min-w-0">
                  <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Footer</p>
                  <h2 className="text-lg md:text-xl font-black tracking-tight truncate">{popupTitle}</h2>
                </div>
                <button
                  type="button"
                  onClick={closePopup}
                  className="shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-2xl border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50"
                  aria-label="Popup schließen"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

              <div className="px-6 md:px-10 py-8">
                {isPopupLoading ? (
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Icon name="loader-2" className="animate-spin" size={12} />
                    {ll('loading')}
                  </div>
                ) : (
                  <div dangerouslySetInnerHTML={{ __html: popupHtml }} />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="sticky top-0 z-40 bg-white shadow-sm flex flex-col">
        {/* Top Level: Logo + Lang */}
        <div className="border-b border-slate-200 bg-white z-50">
          <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="bg-blue-600 p-1 rounded-lg shadow-md">
                <Icon name="terminal" size={20} className="text-white" />
              </div>
              <h1 className="font-black text-xl tracking-tight uppercase italic">
                OData <span className="text-blue-600">Guide</span>
              </h1>
            </div>

            <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
              {uiLanguages.map(l => {
                const code = normalizeLang(l.id);
                const active = uiLang === code;
                return (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => setUiLangAndPersist(code)}
                    className={`px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border-2 transition-all whitespace-nowrap ${
                      active
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-transparent text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                    title={`Sprache: ${String(l.title ?? l.id).toUpperCase()}`}
                  >
                    {String(l.title ?? l.id).toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Second Level: Navigation + Ad Grid */}
        <div className="bg-white border-b border-slate-200">
          <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 min-h-[120px]">
            <div className="lg:col-span-8 flex flex-col justify-center gap-3 py-3 pl-4">
              {/* Context Nav */}
              <div className="px-5 py-2 bg-slate-50 border border-slate-100 flex items-center overflow-x-auto no-scrollbar gap-1 rounded-[2rem] lg:mr-8 shadow-sm">
                {docsContexts.map(ctx => (
                  <button
                    key={ctx.id}
                    onClick={() => handleContextClick(ctx.id)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap border-2 ${
                      activeContextId === ctx.id
                      ? 'border-blue-600 bg-blue-600 text-white shadow-md'
                      : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100'
                    }`}
                    title={`internal: ${ctx.id}`}
                  >
                    {lt(ctx)}
                  </button>
                ))}
              </div>
              {/* Programming Nav */}
              <div className="px-5 py-2 bg-slate-900 flex items-center gap-6 overflow-x-auto no-scrollbar rounded-[2rem] lg:mr-8 shadow-lg">
                <div className="flex items-center gap-2 text-blue-400 shrink-0 border-r border-slate-700 pr-4 mr-2 hidden md:flex">
                  <Icon name="laptop" size={18} />
                  <span className="text-[10px] font-black uppercase tracking-widest">{ll('programming')}</span>
                </div>
                <div className="flex items-center gap-1">
                  {codeLanguages.map(lang => (
                    <button
                      key={lang.id}
                      onClick={() => handleLangClick(lang.id)}
                      className={`px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap border-2 ${
                        viewMode === 'code' && activeLangId === lang.id
                        ? (lang.isAi ? 'border-purple-500 bg-purple-500 text-white shadow-purple-900/50' : 'border-blue-500 bg-blue-500 text-white shadow-md')
                        : 'border-transparent text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                      title={`internal: ${lang.id}`}
                    >
                      {lt(lang)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            {/* Ad Section */}
            <div className="lg:col-span-4 hidden lg:flex items-center justify-center border-l border-slate-100 p-4 relative bg-slate-50/30">
              <div className="absolute top-2 right-2">
                <span className="text-[8px] font-black uppercase tracking-widest text-slate-200">{ll('ad_label')}</span>
              </div>
              <div className="w-full h-[80px] bg-gradient-to-r from-slate-50 to-white rounded-2xl border border-slate-100 flex items-center justify-center shadow-sm group cursor-pointer hover:border-blue-100 transition-all">
                <div className="flex items-center gap-3 opacity-30 group-hover:opacity-60 transition-opacity grayscale group-hover:grayscale-0">
                   <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center">
                      <Icon name="layout" size={16} className="text-slate-500" />
                   </div>
                   <div className="flex flex-col">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Leaderboard</span>
                      <span className="text-[9px] font-medium text-slate-400">728 x 90</span>
                   </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-[1600px] mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          <aside className="lg:col-span-2 hidden lg:block sticky top-[220px] h-[calc(100vh-220px)]">
            <nav className="h-full flex flex-col pb-4">
              <div className="overflow-y-auto pr-2">
                <div className="px-3">
                  <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">
                    {viewMode === 'docs' ? ll('documentation') : (activeLanguage?.isAi ? ll('intelligence') : ll('implementation'))}
                  </p>
                  {navError && (
                    <p className="mt-2 text-xs text-red-600 font-semibold">{navError}</p>
                  )}
                </div>

                <div className="space-y-6 mt-6">
                {currentGroups.map(group => (
                  <div key={group.id} className="space-y-1">
                    <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest mb-2 px-3">
                      {lt(group)}
                      <span className="ml-2 text-slate-300">({group.id})</span>
                    </p>

                    {(group.items ?? []).map(item => (
                      <button
                        key={item.id}
                        onClick={() => loadItem(item)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all group ${
                          activeItemId === item.id
                          ? 'bg-white shadow-md border border-slate-200 text-blue-600 scale-[1.02]'
                          : 'text-slate-600 hover:bg-slate-200/50'
                        }`}
                        title={`internal: ${item.id} | file: ${item.file}`}
                      >
                        <span className={`${activeItemId === item.id ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'}`}>
                          <Icon name="chevron-right" size={18} />
                        </span>
                        {lt(item)}
                      </button>
                    ))}
                  </div>
                ))}
                </div>
              </div>

              {(currentGroups.reduce((acc, g) => acc + (g.items?.length || 0), 0) <= 7) && (
                <div className="mt-4 flex-1 min-h-[200px]">
                  <AdContainer type="sidebar" title={ll('ad_label')} className="h-full" />
                </div>
              )}
            </nav>
          </aside>

          <div id="content-panel" className="lg:col-span-7 flex flex-col gap-6">
            <div className="bg-white rounded-[2.5rem] border border-slate-200 p-8 md:p-12 shadow-sm min-h-[600px]">
              {isLoading && (
                <div className="mb-6 text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                  <Icon name="loader-2" className="animate-spin" size={12} />
                  {ll('loading')}
                </div>
              )}

              <div
                id="content-body"
                className="animate-in fade-in slide-in-from-bottom-2 duration-500"
                dangerouslySetInnerHTML={{ __html: contentHtml }}
              />

              <div className="mt-16 pt-10 border-t border-slate-100">
                <div className="bg-amber-50 p-6 rounded-3xl border border-amber-100 flex gap-4">
                  <Icon name="shield-check" className="text-amber-600 shrink-0" size={24} />
                  <p className="text-xs text-amber-900 leading-relaxed font-medium">
                    <strong>{ll('security_note')}:</strong> {ll('security_text')}
                  </p>
                </div>
              </div>
            </div>

            <AdContainer type="content" title={ll('ad_label')} className="w-full min-h-[150px]" />

            <div className="bg-white rounded-[2.5rem] border border-slate-200 overflow-hidden shadow-sm border-t-4 border-t-purple-500 p-8 md:p-12">
               <div className="flex flex-col md:flex-row items-center gap-8">
                  <div className="w-20 h-20 bg-purple-50 rounded-[2rem] flex items-center justify-center text-purple-600 shrink-0">
                    <Icon name="graduation-cap" size={40} />
                  </div>
                  <div className="flex-1 text-center md:text-left">
                     <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
                        <span className="bg-purple-100 text-purple-700 text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-widest italic">{ll('ad_label')}</span>
                     </div>
                     <h3 className="text-2xl font-black text-slate-900 mb-2">OData Masterclass</h3>
                     <p className="text-slate-500 text-sm font-medium">Lernen Sie professionelle API-Entwicklung mit OData von Grund auf.</p>
                  </div>
                  <div className="shrink-0">
                     <button className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-4 rounded-2xl font-black text-sm uppercase tracking-widest transition-all shadow-lg shadow-purple-100 active:scale-95">
                       Kurs Details
                     </button>
                  </div>
               </div>
            </div>

            <AdContainer type="content" title={ll('ad_label')} className="w-full min-h-[150px]" />
          </div>

          <aside className="lg:col-span-3 hidden lg:block sticky top-[220px] h-[calc(100vh-220px)]">
            <div className="flex flex-col h-full pb-6">
              <div className="px-3 mb-6 shrink-0">
                <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">{ll('ad_label')}</p>
              </div>
              <div className="flex-1 bg-white rounded-[2.5rem] border border-slate-200 p-8 shadow-sm flex flex-col items-center justify-center text-center overflow-hidden">
                <div className="w-16 h-16 bg-slate-50 rounded-3xl flex items-center justify-center mb-6 border border-slate-100">
                  <Icon name="layout" size={32} className="text-slate-300" />
                </div>
                <p className="text-xs font-black uppercase tracking-widest text-slate-400">{ll('ad_placeholder')}</p>
                <div className="mt-4 w-12 h-1 bg-blue-100 rounded-full mx-auto" />
                <p className="mt-6 text-[11px] text-slate-400 font-medium leading-relaxed max-w-[160px] mx-auto">
                  {ll('ad_text')}
                </p>
                <a 
                  href="mailto:office@thinkbigger.at?subject=Werbung%20OData%20Guide" 
                  className="mt-10 px-6 py-3 bg-slate-900 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-800 transition-colors"
                >
                  {ll('ad_request')}
                </a>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <footer className="max-w-[1600px] mx-auto px-6 py-8 border-t border-slate-200 mt-12 bg-white/50 rounded-t-[3rem]">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-slate-800">
              <Icon name="terminal" size={18} className="text-blue-600" />
              <span className="font-extrabold text-sm tracking-tight uppercase">ODATA GUIDE</span>
            </div>
            <div className="hidden md:block border-l border-slate-200 h-6" aria-hidden="true" />
            <div className="text-slate-400 text-xs">
              &copy; {currentYear}{' '}
              <a
                className="text-slate-900 font-bold hover:text-slate-700"
                href="https://www.thinkbigger.at/"
                target="_blank"
                rel="noopener noreferrer"
              >
                THINKBIGGER.at
              </a>
            </div>
          </div>

          <nav className="flex items-center gap-6 text-xs">
            {(footerItems.length ? footerItems : [
              { id: 'datenschutz', title: 'Datenschutz', file: 'content/footer/datenschutz.html', popup: 1 },
              { id: 'impressum', title: 'Impressum', file: 'content/footer/impressum.html', popup: 1 },
              { id: 'support', title: 'Support', file: 'content/footer/support.html', popup: 1 },
            ]).map(item => (
              item?.popup
                ? (
                  <button
                    key={item.id}
                    type="button"
                    className="text-slate-400 hover:text-slate-700 uppercase tracking-wide"
                    onClick={() => openPopup(item)}
                    title={`internal: footer.${item.id} | file: ${item.file}`}
                  >
                    {String(lt(item)).toUpperCase()}
                  </button>
                )
                : (
                  <a
                    key={item.id}
                    className="text-slate-400 hover:text-slate-700 uppercase tracking-wide"
                    href={item.href ?? '#'}
                    target={item.target ?? undefined}
                    rel={item.target === '_blank' ? 'noopener noreferrer' : undefined}
                  >
                    {String(lt(item)).toUpperCase()}
                  </a>
                )
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
};

const rootEl = document.getElementById('root');
if (rootEl && window.ReactDOM?.createRoot) {
  const root = ReactDOM.createRoot(rootEl);
  root.render(<App />);
}
