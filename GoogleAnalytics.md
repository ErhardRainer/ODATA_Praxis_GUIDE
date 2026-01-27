# Google Analytics 4 (GA4) in ODataGuide einrichten (statische HTML + SPA-Fragmente)

## Ziel

Diese Dokumentation beschreibt, wie **Google Analytics 4 (GA4)** für die Website eingerichtet wird und wie die **Measurement ID** (Format `G-XXXXXXXXXX`) ermittelt und anschließend in die **statische SPA-ähnliche Architektur** (eine `index.html` + dynamisches Nachladen von HTML-Fragmenten per JS) eingebaut wird.

Die Anleitung ist so formuliert, dass sie direkt als Repo-Dokumentation (z. B. `docs/analytics/ga4-setup.md`) verwendet werden kann.

---

## Begriffe (kurz)

* **GA4**: aktuelle Generation von Google Analytics (Property-Typ).
* **Account**: oberste Organisationseinheit in Analytics (z. B. „ODataGuide“).
* **Property**: Mess-Container innerhalb eines Accounts (z. B. „ODataGuide Web“).
* **Data stream (Web)**: Quelle der Daten (Website) innerhalb einer Property.
* **Measurement ID**: Kennung des Web-Streams in GA4, z. B. `G-ABC123DEF4`.

---

## 1) GA4-Konto, Property und Web-Stream erstellen

### 1.1 Google Analytics öffnen

1. Mit dem Google-Konto anmelden, das Besitzer des Analytics-Setups sein soll.
2. Google Analytics öffnen.

### 1.2 Account anlegen

1. Unten links **Admin** (Zahnrad) öffnen.
2. In der Spalte **Account** auf **Create account** (Konto erstellen) klicken.
3. **Account Name** vergeben, z. B. `ODataGuide`.
4. Optionen zur Datenfreigabe nach Bedarf wählen.
5. Weiter.

### 1.3 Property anlegen (GA4)

1. Im Assistenten **Create property** (Property erstellen).
2. Property Name vergeben, z. B. `ODataGuide GA4`.
3. **Reporting time zone**: `Europe/Vienna` (oder passend zur Organisation).
4. **Currency**: `EUR`.
5. Weiter / Erstellen.

### 1.4 Web-Data-Stream anlegen

1. In **Admin** zur Spalte **Property** wechseln.
2. Unter **Data collection and modification** → **Data streams** öffnen.
3. **Web** auswählen.
4. Website-URL der **Primärdomain** eintragen (Empfehlung: nur eine Domain als Source of Truth verwenden, z. B. `https://odataguide.com`).
5. Stream Name vergeben, z. B. `odataguide.com`.
6. **Create stream**.

> **Best Practice**: Wenn zusätzlich `odata-guide.com` existiert, sollte diese Domain per **301 Redirect** auf die Primärdomain zeigen. Die GA4-Property sollte primär auf der Canonical-Domain arbeiten.

---

## 2) Measurement ID finden (G-XXXXXXXXXX)

### 2.1 Web-Stream öffnen

1. **Admin** → **Data streams**.
2. Den soeben erstellten **Web-Stream** anklicken.

### 2.2 Measurement ID kopieren

Im Stream-Detailbereich wird angezeigt:

* **Measurement ID**: `G-...`

Diese ID wird für den Einbau benötigt.

---

## 3) GA4 in die statische SPA einbauen

### Architektur-Hinweis

ODataGuide besteht aus:

* einer zentralen `index.html`
* einem zentralen `script.js`
* HTML-Fragmenten, die per `fetch()` geladen und in einen Content-Container injiziert werden

**Wichtig**: Bei SPA-ähnlicher Navigation werden sonst nur der erste Pageview und nicht jeder „virtuelle Seitenwechsel“ sauber gemessen.

### 3.1 Google Tag (gtag.js) in `index.html` einbauen

Füge das folgende Snippet im `<head>` von `index.html` ein (so hoch wie möglich, nach `<meta charset>` ist ok). **Ersetze** `G-XXXXXXXXXX` durch deine Measurement ID.

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('js', new Date());

  // SPA: Pageviews werden bei Navigation manuell gesendet
  gtag('config', 'G-XXXXXXXXXX', { send_page_view: false });
</script>
```

**Warum `send_page_view: false`?**

* In einer klassischen Multi-Page-Site würde GA automatisch pro Seitenaufruf zählen.
* In einer SPA bleibt die Seite „technisch“ gleich; daher senden wir pro Navigation gezielt `page_view`.

---

## 4) Virtuelle Pageviews bei Navigation senden

### 4.1 Zentrale Tracking-Funktion in `script.js`

Füge (oder ergänze) eine zentrale Funktion, die bei jedem Fragmentwechsel aufgerufen wird:

```js
const GA_MEASUREMENT_ID = 'G-XXXXXXXXXX';

function trackVirtualPageview({ path, title }) {
  if (typeof gtag !== 'function') return;

  if (title) document.title = title;

  gtag('event', 'page_view', {
    page_location: window.location.origin + path,
    page_path: path,
    page_title: document.title
  });
}
```

### 4.2 Navigation: URL ändern, Fragment laden, Pageview senden

Vereinfacht sieht eine Navigation in der SPA typischerweise so aus:

```js
async function navigateTo({ path, fragmentUrl, title }) {
  // 1) URL setzen (wichtig für Back/Forward & Analytics)
  history.pushState({ path, fragmentUrl, title }, '', path);

  // 2) Fragment laden und injizieren
  const html = await fetch(fragmentUrl).then(r => r.text());
  document.getElementById('content-panel').innerHTML = html;

  // 3) Analytics: virtuellen Pageview senden
  trackVirtualPageview({ path, title });
}
```

### 4.3 Back/Forward (popstate) ebenfalls tracken

Damit Browser-Navigation korrekt funktioniert und gemessen wird:

```js
window.addEventListener('popstate', async (e) => {
  const state = e.state;
  if (!state) return;

  const html = await fetch(state.fragmentUrl).then(r => r.text());
  document.getElementById('content-panel').innerHTML = html;

  trackVirtualPageview({ path: state.path, title: state.title });
});
```

---

## 5) Optionale Events für Tools (Query Builder, Generatoren, etc.)

Für Interaktionen (Button-Klicks, Generator-Nutzung) können GA4 Events gesendet werden:

```js
function trackEvent(name, params = {}) {
  if (typeof gtag !== 'function') return;
  gtag('event', name, params);
}

// Beispiel: Query Builder
trackEvent('query_builder_generate', {
  platform: 'sap',
  odata_version: 'v4'
});
```

---

## 6) Verifikation (funktioniert das Tracking?)

### 6.1 Realtime-Report

1. Seite im Browser öffnen.
2. In GA4: **Reports** → **Realtime**.
3. Auf der Website zwischen mehreren „Seiten“ navigieren.
4. Prüfen, ob mehrere Pageviews / unterschiedliche `page_path`-Werte ankommen.

### 6.2 Typische Fehlerbilder

* **Nur 1 Pageview**: `send_page_view:false` fehlt oder `trackVirtualPageview()` wird nicht aufgerufen.
* **Falsche URLs**: `path` / `history.pushState` nicht konsistent.
* **Kein Tracking**: `gtag` wird nicht geladen (z. B. Blocker/Consent) oder falsche Measurement ID.

---

## 7) Consent / DSGVO (EU) – Kurznotiz für die Umsetzung

Diese Repo-Doku beschreibt den technischen Einbau. Für EU-Compliance gilt in der Praxis:

* GA4 sollte erst nach entsprechender Einwilligung (CMP/Consent) aktiv Daten senden.

**Empfehlung im Projekt**: Consent-Implementierung als eigenes Dokument (z. B. `docs/privacy/consent.md`) pflegen, damit Analytics/Ads sauber getrennt dokumentiert sind.

---

## 8) Checkliste (Einbau abgeschlossen)

* [ ] GA4 Account erstellt
* [ ] GA4 Property erstellt
* [ ] Web Data Stream erstellt
* [ ] Measurement ID (`G-...`) dokumentiert
* [ ] gtag.js Snippet in `index.html` eingebaut
* [ ] `send_page_view:false` gesetzt
* [ ] `trackVirtualPageview()` bei jeder Navigation integriert
* [ ] `popstate` Handling integriert
* [ ] Realtime-Test erfolgreich

---

## Anhang: Empfohlene Repo-Dateien

* `docs/analytics/ga4-setup.md` (dieses Dokument)
* `docs/privacy/consent.md` (Consent/CMP/DSGVO Umsetzung)
* `src/script.js` (Navigation + Tracking)
* `index.html` (globales GA Snippet)
