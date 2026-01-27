OData-Endpunkte in der Praxis (SAP Gateway / S/4HANA): Aufbau, $metadata, Filtern, Selektieren, $count und korrektes Paging

OData (Open Data Protocol) ist ein REST-ähnlicher Standard, um Daten über HTTP einheitlich bereitzustellen. In SAP-Kontexten (S/4HANA, SAP Gateway) begegnet dir in der Regel OData V2. Der große Vorteil: Du kannst serverseitig filtern, sortieren, selektieren und paginieren – und damit Datenzugriffe performant, deterministisch und wartbar gestalten.

Dieser Artikel beschreibt den Aufbau eines OData-Endpunkts, erklärt $metadata, zeigt die wichtigsten Query-Optionen ($filter, $select, $orderby, $top, $skip, $count) und behandelt detailliert, warum Sortierung beim Paging nicht optional, sondern zwingend ist, wenn du korrekte Ergebnisse willst.

1) Grundaufbau eines OData-Endpunkts

Ein typischer SAP-OData-Endpunkt sieht so aus:

https://<host>/sap/opu/odata/sap/<SERVICE_NAME>/<ENTITY_SET>


Beispiel (Schema):

Service Root:
.../sap/opu/odata/sap/YY1_Order_V01_CDS/

EntitySet (vergleichbar mit “Tabelle/Collection”):
.../sap/opu/odata/sap/YY1_Order_V01_CDS/YY1_Order_V01

Dazu kommen Query-Optionen als URL-Parameter, z. B.:

.../YY1_Order_V01?$top=10&$format=json

Entity vs. EntitySet vs. EntityType

EntitySet: Menge von Entities (Collection) – z. B. YY1_Order_V01.

Entity: einzelner Datensatz (identifizierbar über Key).

EntityType: das Schema (Properties, Key, Typen), beschrieben in $metadata.

2) $metadata: Dein Vertrag, was der Service wirklich kann

Die wichtigste Ressource jedes OData-Services:

.../sap/opu/odata/sap/<SERVICE>/$metadata


$metadata liefert ein EDMX/XML-Dokument, in dem du u. a. findest:

EntityTypes mit Properties und Datentypen

Keys (Schlüsselspalten)

EntitySets

Capabilities/Restrictions (z. B. „nicht filterbar“, „nicht sortierbar“)

Semantiken (Maße/Währungen/Units)

ggf. Analytics/Aggregation-Vokabular (in SAP häufig relevant)

Warum $metadata so wichtig ist

Validierung: Welche Spalten existieren wirklich? Welche sind Keys?

Funktionalität: Was darfst du filtern/sortieren/selecten?

Interoperabilität: Tools (Power BI, ETL, SDKs) nutzen Metadata, um Abfragen zu generieren.

Praxisbeispiel (aus deiner Metadata-Logik, abstrahiert):

ID ist Key (<Key><PropertyRef Name="ID"/></Key>)

ID kann aber trotzdem als NonFilterable/NonSortable markiert sein (Capabilities).

Wichtig: “Spalte existiert” heißt nicht automatisch “Spalte ist überall nutzbar”. SAP kann z. B. bei analytischen Entitäten $select einschränken, obwohl das Feld vorhanden ist.

3) Ausgabeformat: JSON vs. Atom/XML

SAP Gateway unterstützt typischerweise:

?$format=json (heute üblich)

Atom/XML (historisch)

Beispiel:

.../YY1_Order_V01?$top=10&$format=json

4) Filtern mit $filter (serverseitig)
Grundprinzip

$filter ist eine boolesche Bedingung. OData V2 verwendet Operatoren wie:

Vergleich: eq, ne, gt, ge, lt, le

Logik: and, or, not

Strings/Funktionen (abhängig von Service): startswith, substringof, etc.

Datumsfilter (OData V2 / SAP-typisch)

SAP verwendet häufig datetime'...' bei Edm.DateTime:

$filter=CreationDate ge datetime'2024-09-01T00:00:00' and CreationDate lt datetime'2024-09-02T00:00:00'


Wichtig:

Achte auf Datentyp in $metadata (Edm.DateTime vs. Edm.DateTimeOffset).

Bei DateTimeOffset wird häufig ein Offset erwartet (z. B. ...+00:00), abhängig von Implementierung.

Capabilities beachten

In $metadata kann stehen, dass eine Property nicht filterbar ist. Dann führt $filter auf dieses Feld zu Fehlern (oder wird ignoriert, je nach Gateway-Version/Implementierung). Das ist kein OData-Problem, sondern eine Service-Einschränkung.

5) Spalten auswählen mit $select (Projektion)

Mit $select reduzierst du die Payload (Bandbreite, Parsing, Speicher) und beschleunigst oft den Endpunkt.

Beispiel:

.../YY1_Order_V01?$select=ID,SalesDocument,CreationDate&$top=10&$format=json

Warum kann $select trotz existierender Spalte scheitern?

Gerade in SAP gibt es Endpunkte, die als analytische/aggregierte Entitäten veröffentlicht sind (sap:semantics="aggregate", Analytics-Vokabular). Dort kann $select (oder bestimmte Formen davon) technisch eingeschränkt sein. In solchen Fällen ist ein stabiler Workaround oft:

ohne $select laden und clientseitig reduzieren, oder

einen nicht-analytischen View/Service bereitstellen (Backend-Designfrage).

6) Sortieren mit $orderby – und warum das beim Paging zwingend ist
$orderby

Sortierung definierst du so:

$orderby=CreationDate asc


Mehrere Felder:

$orderby=CreationDate asc, ID asc

Warum Sortierung beim Paging nicht optional ist

Ohne $orderby ist die Reihenfolge der Datensätze nicht definiert. Das ist entscheidend, sobald du Paging machst, also z. B. top/skip oder serverseitige Pagination nutzt.

Problem ohne stabile Sortierung

Angenommen, du lädst:

Seite 1: $top=100

Seite 2: $top=100&$skip=100

Wenn sich zwischen diesen Requests Daten ändern (neue Datensätze, Updates, Reorg/Index-Änderungen), kann Folgendes passieren:

Datensätze tauchen doppelt auf (Overlap)

Datensätze werden übersprungen (Gap)

Reihenfolge ist je Request anders (nicht deterministisch)

Korrekte Strategie: Sortiere stabil und eindeutig

Für korrektes Paging brauchst du:

Eine stabile Sortierung (z. B. nach CreationDate)

Eine Eindeutigkeitskomponente als Tie-Breaker (z. B. Key ID)

Best Practice:

$orderby=CreationDate asc, ID asc


Wenn CreationDate gleich ist (häufig!), sorgt ID dafür, dass die Reihenfolge dennoch deterministisch bleibt.

Merksatz: Paging ohne eindeutige Sortierung ist fachlich unzuverlässig – selbst wenn es “meistens funktioniert”.

7) Paging: $top, $skip, server-driven paging und $skiptoken
Client-driven paging (klassisch)

$top=n begrenzt die Anzahl

$skip=n überspringt n Datensätze

Beispiel:

.../YY1_Order_V01?$orderby=CreationDate asc, ID asc&$top=100&$skip=0
.../YY1_Order_V01?$orderby=CreationDate asc, ID asc&$top=100&$skip=100


Risiko: $skip kann bei großen Datenmengen teuer werden (DB muss viel “wegwerfen”). Außerdem bleibt das Problem der Instabilität, wenn die Sortierung nicht eindeutig ist.

Server-driven paging (SAP Gateway häufig)

SAP kann automatisch paginieren und liefert dann einen next link (__next im JSON, je nach Format/Version). Der Client folgt diesem Link.

Typischerweise enthält der Link ein $skiptoken:

.../YY1_Order_V01?$skiptoken=...


Best Practice: Wenn der Server einen __next liefert, immer genau diesem folgen (nicht selbst “weiterrechnen”), weil das Skiptoken serverintern die korrekte Fortsetzung repräsentiert.

8) $count: Wie viele Datensätze gibt es?

In OData V2 existieren in der Praxis zwei verbreitete Varianten:

A) Separater Count-Endpunkt

Viele Services unterstützen:

.../YY1_Order_V01/$count


Optional mit Filter:

.../YY1_Order_V01/$count?$filter=CreationDate ge datetime'2024-09-01T00:00:00'


Das Ergebnis ist meist plain text (Zahl).

B) Inline-Count (OData V2)

Viele SAP-Gateway-Services unterstützen:

.../YY1_Order_V01?$inlinecount=allpages&$top=10


Dann kommt zusätzlich ein Zähler (z. B. __count) im Response. Das ist praktisch für UI/Reporting, kann aber teurer sein als ein eigener Count.

Performance-Hinweis: $count (egal wie) kann sehr teuer sein, wenn der Filter nicht selektiv oder nicht indexfreundlich ist. Im Zweifel: Count gezielt einsetzen und nicht “immer mitladen”.

9) Zusammenspiel: “Richtig” filtern, selektieren und paginieren

Ein typischer, robuster Pattern (OData V2, SAP) sieht so aus:

Selektiv filtern (serverseitig)

Stabile, eindeutige Sortierung

Paging über top/skip oder server-driven next links

$select nur, wenn vom Service unterstützt und sinnvoll

Beispiel (robust):

.../YY1_Order_V01?
$filter=CreationDate ge datetime'2024-09-01T00:00:00' and CreationDate lt datetime'2024-09-02T00:00:00'
&$orderby=CreationDate asc, ID asc
&$select=ID,CreationDate,SalesDocument
&$top=500
&$format=json


Wenn $select in deinem Service (analytische Entität) problematisch ist, dann:

$select weglassen,

Response clientseitig reduzieren,

oder Backend-seitig einen “nicht-analytischen” Endpunkt bereitstellen.

10) Typische Fehlerbilder und Debugging-Checkliste
A) “Property existiert, aber Operation nicht erlaubt”

In $metadata prüfen:

FilterRestrictions / SortRestrictions

sap:filterable="false" / sap:sortable="false"

Bei Analytics/Aggregation: damit rechnen, dass $select/$orderby eingeschränkt sein kann.

B) Paging liefert Duplikate oder Lücken

Prüfen:

Ist $orderby gesetzt?

Ist $orderby eindeutig? (Key als Tie-Breaker enthalten?)

Werden server-driven next links korrekt verfolgt?

C) Performance schlecht trotz Filter

Prüfen:

Filter auf indexgeeigneten Feldern?

Datentypen korrekt (DateTime vs DateTimeOffset)?

$select reduziert Payload?

$count oder $inlinecount unnötig aktiv?

Fazit

Ein OData-Endpunkt ist nicht “nur eine URL”, sondern ein vertraglich beschriebenes Daten-API. Wer $metadata liest, versteht:

welche Daten und Typen existieren,

welche Felder filter-/sortierbar sind,

welche Abfrageoptionen sinnvoll und zulässig sind.

Und der wichtigste Praxis-Punkt: Paging ohne stabile, eindeutige Sortierung ist fachlich nicht korrekt. Sobald du mehrere Seiten abrufst, brauchst du ein deterministisches $orderby – idealerweise ergänzt um den Key.

Wenn du möchtest, kann ich dir ausgehend von deinem konkreten Service (YY1_Order_V01_CDS) ein kleines “Query Cookbook” (Top-Patterns + Anti-Patterns) erstellen – inklusive Varianten für server-driven paging (next link / skiptoken) und Count-Strategien.