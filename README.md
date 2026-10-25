# Osvětlení kolejiště

Python/FastAPI řídí osvětlení přes MTB Daemon. Nuxt/Vue zobrazuje strom kolejiště
a umožňuje měnit algoritmy jednotlivých světel i celých skupin.

## Spuštění

Python 3.11 nebo novější. Z kořene projektu:

```powershell
python -m pip install -r backend/requirements.txt
python backend/main.py
```

Ve druhém terminálu:

```powershell
cd frontend
npm install
npm run dev
```

Frontend naslouchá na všech rozhraních na portu 3000, backend na portu 8000.
Z jiného zařízení v LAN otevřete například `http://192.168.1.20:3000`, kde
192.168.1.20 je adresa počítače s frontendem. Oba porty musí být dostupné ve firewallu.

## Adresa backendu ve frontendu

Soubor `frontend/public/backend-config.json` se načítá při otevření stránky:

```json
{
  "backendUrl": "",
  "backendPort": 8000
}
```

Prázdné `backendUrl` znamená: použít stejný hostname/IP a HTTP/HTTPS jako má
stránka v prohlížeči, ale port `backendPort`. Při přístupu z LAN se proto
nepoužívá localhost návštěvníka.

Pro backend na jiném zařízení:

```json
{
  "backendUrl": "http://192.168.1.30:8000",
  "backendPort": 8000
}
```

Je-li `backendUrl` vyplněné, `backendPort` se ignoruje. Lze použít i
`https://backend.example.cz/osvetleni/` nebo `/` pro proxy na stejném originu.
WebSocket URL se odvodí automaticky (HTTP → WS, HTTPS → WSS). Stránka přes HTTPS
vyžaduje také HTTPS backend a proxy musí předávat WebSocket upgrade pro `/api/ws`.

Po změně konfigurace stačí znovu načíst stránku. Produkční build kopíruje soubor
do `frontend/.output/public/backend-config.json`; po nasazení upravte tuto
nasazenou kopii nebo nasaďte nový build.

## Nastavení backendu

`backend/config.yaml` obsahuje:

- `light`: časy východu a západu slunce.
- `configurate`: název YAML souboru v `backend/configurate/`.
- `server.host` a `server.port`: rozhraní a port HTTP/WebSocket serveru.
- `server.allowed_origins`: povolené adresy frontendů, včetně protokolu a portu.
- `server.allowed_origin_regex`: výchozí povolení localhostu a privátních IPv4
  LAN adres. Pro přístup přes DNS jméno nebo IPv6 přidejte přesný origin například
  `http://kolejiste.local:3000` do `allowed_origins`.
- `mtb.host`, `mtb.port`, `mtb.timeout`, `mtb.reconnect_delay`: spojení s démonem
  a časové limity v sekundách.

Pravidla originů platí pro HTTP i WebSocket. U oddělených serverů sem patří
adresa **frontendu**, kterou otevírá prohlížeč. Aplikace je určena pro důvěryhodnou
LAN; nemá přihlášení uživatelů. Změna backendové konfigurace vyžaduje restart.

Spouštějte jednu instanci backendu / jeden Uvicorn worker pro jedno kolejiště.
Pro běžné spuštění použijte `python backend/main.py`; alternativně
`uvicorn --app-dir backend web:app --host 0.0.0.0 --port 8000`.
Cesty ke konfiguracím se odvozují od umístění souborů, nikoli pracovního adresáře.

## Komunikace a stav

Backend používá jediný asyncio event loop, bez vlastních pracovních vláken.
Příkazy se zařadí k odeslání a HTTP odpověď 202 se vrací bez čekání na hardware.
Jediná přijímací úloha čte kompletní JSON řádky a páruje odpovědi podle ID.
Čekání na socket uvolňuje event loop. Neodpovídající démon vyvolá timeout
a automatické obnovení spojení.

Pro každý modul je nejvýše jeden nepotvrzený příkaz. Další změny se sloučí
na nejnovější požadovaný stav. Beze změny se potvrzené výstupy neposílají znovu;
po reconnectu se odešle aktuální stav všech spravovaných modulů.
Chyby modulů se zobrazí ve webu a odeslání se zopakuje po nastavené prodlevě.

Časové algoritmy se přepočítávají lokálně každou sekundu. To nevyvolává
pravidelné HTTP dotazy ani nezměněné zprávy: WebSocket posílá počáteční stav
a poté pouze změněný stav. Pomalý klient má omezenou frontu s nejnovějším stavem.
Po odpojení se frontend připojí znovu a dostane aktuální snímek.

Barvy světel označují požadovaný stav podle algoritmu. Stav spojení,
čekající potvrzení a chyby MTB se zobrazují samostatně; potvrzení démona
není fyzické měření svítící lampy. Změny algoritmů zůstávají v paměti
a při restartu se obnoví z YAML.

Podporované algoritmy frontend dostává z backendu. `drazni_osvetleni` zapíná
15 minut po `light.sunset` a vypíná 15 minut před `light.sunrise` z `backend/config.yaml`.
Při hodnotách 20:09 a 5:32 svítí od 20:24 včetně do 05:17 (v 05:17 už je vypnuté).
Interval funguje i přes půlnoc. API neznámé algoritmy odmítá.
Pokud je nepodporovaný algoritmus už v YAML, backend přesto nastartuje: pro tento
výstup použije hodnotu 0 a zobrazí chybu konfigurace ve webu i logu. Podporované
algoritmy ostatních světel fungují dál. Výběrem podporovaného režimu ve webu se
chyba daného světla odstraní; pro trvalou změnu upravte také zdrojový YAML.

## Testy

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests -v
cd frontend
node --test tests/lighting.test.mjs
npm run build
```

Testy používají místní falešný MTB server a neovládají skutečné kolejiště.
Ověřují rozdělené TCP zprávy, pořadí odpovědí, timeouty, reconnect,
slučování změn, API při mlčícím démonu, WebSocket pro více klientů,
CORS/originy, konfiguraci URL a obnovování spojení frontendu.

Specifikace protokolu:
[MTB Daemon TCP JSON](https://github.com/kmzbrnoI/mtb-daemon/blob/master/tcp-protocol/README.md).

Pokud build na Windows skončí chybou EPERM při vytváření výstupních složek,
lze omezit souběžné souborové operace pro daný terminál:

```powershell
$env:UV_THREADPOOL_SIZE = '1'
npm run build
```

## Další algoritmy osvětlení

- `byt`: svítí od západu slunce do 21:00 a od 05:00 do východu slunce.
  Je-li západ až po 21:00 nebo východ už před 05:00, příslušný interval nesvítí.
- `chodba`: mezi západem a východem slunce se pro každé světlo zvlášť střídá
  náhodná pauza 1–5 minut a rozsvícení na 20–30 sekund. První rozsvícení po
  aktivaci v noci také následuje po náhodné pauze. Při východu slunce zhasne
  i případné probíhající rozsvícení. Pauzy lze změnit v `light.chodba.pause_min_seconds`
  a `light.chodba.pause_max_seconds` v `backend/config.yaml` (výchozí 60 a 300).
- `prodejna`: svítí od 07:00 včetně do 19:00; v 19:00 už je vypnutá.
- `vyloha`: svítí nepřetržitě, také v noci.

Východ a západ se berou z `light.sunrise` a `light.sunset`. Časové rozvrhy používají
modelový čas hJOP; při explicitním vypnutí hJOP reálný místní čas backendu. Změna jiného světla ani opakovaný výběr stejného algoritmu chodby
nerestartují její časování. Změna režimu, restart backendu a nová noc založí nový
náhodný průběh. Stav se přepočítává přibližně jednou za sekundu.


## Čas hJOP

V `backend/config.yaml` je spojení s panelovým serverem hJOP:

```yaml
hjop:
  enabled: true
  host: "localhost"
  port: 5896
  timeout: 5
  reconnect_delay: 3
  idle_timeout: 20
  sync_timeout: 240
```

`localhost` označuje počítač s backendem. Je-li hJOP jinde, nastavte jeho IP
nebo hostname. Připojení je asynchronní a pouze čte čas; nemění nastavení hJOP.
Backend přijímá synchronizaci, běh/pauzu a násobitel rychlosti. Mezi zprávami
čas dopočítává podle skutečně uplynulé doby a násobitele.

Web ukazuje **Modelový čas hJOP**, **Zrychlení: například 9×** a stav
běhu, pozastavení nebo spojení. Hodiny se posílají samostatnou WebSocket zprávou
přibližně každou skutečnou sekundu, pokud se změnily. Strom světel se posílá
pouze při změně, frontend neposílá pravidelné HTTP dotazy.

Při výpadku hJOP se poslední čas zastaví a web ukáže odpojení; spojení se obnovuje
automaticky. Bez první synchronizace jsou časově závislé výstupy vypnuté,
trvalé režimy fungují. Neaktivní modelový čas je označen ve webu.
Nedochází k automatickému přepnutí na hodiny počítače. Pro vědomé použití
reálného času nastavte `hjop.enabled: false`: web zobrazí **Reálný čas**,
rychlost **1×** a zdroj „Systémový čas backendu“. Panelový protokol hJOP
poskytuje modelový čas, nikoli čas systémových hodin vzdáleného serveru.

U `chodba` určuje modelový čas den/noc, ale rozsvícení 20–30 sekund a náhodné
pauzy 1–5 minut vždy běží ve **skutečných sekundách**, i při pozastaveném
modelovém čase. Nastavení `light.sunrise` a `light.sunset` zůstává v platnosti.
Po úpravě konfigurace restartujte backend.

Protokol: [hJOP panel server](https://github.com/kmzbrnoI/hJOPserver/wiki/panelServer).
