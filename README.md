# Osvětlení kolejiště

Python/FastAPI řídí osvětlení přes MTB Daemon. Nuxt/Vue zobrazuje strom kolejiště
a umožňuje měnit algoritmy jednotlivých světel i celých skupin.

Podrobný postup instalace na nový počítač a spuštění pro běžný provoz je v [NASAZENI.md](NASAZENI.md).

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

`backend/config/config.yaml` obsahuje:

- `layout.file`: cesta k souboru struktury kolejiště.
- `algorithms_file`: cesta k nastavení algoritmů (`backend/config/algorithms.yaml`).
- `hjop`: připojení ke zdroji modelového času.

Cesty jsou relativní vůči `config.yaml`. Používejte aktuální rozdělené konfigurační soubory.

- `server.host` a `server.port`: rozhraní a port HTTP/WebSocket serveru.
- Adresa frontendu se v backendu neomezuje: HTTP povoluje libovolný původ
  (`Access-Control-Allow-Origin: *`) a WebSocket původ nekontroluje.
- `mtb.host`, `mtb.port`, `mtb.timeout`, `mtb.reconnect_delay`: spojení s démonem
  a časové limity v sekundách.

Backend přijímá frontend z libovolného DNS jména, IP adresy a portu.
Seznam povolených adres se nenastavuje.

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
15 minut po `sunset` a vypíná 15 minut před `sunrise` z `backend/config/algorithms.yaml`.
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
přístup z libovolného originu, konfiguraci URL a obnovování spojení frontendu.

Specifikace protokolu:
[MTB Daemon TCP JSON](https://github.com/kmzbrnoI/mtb-daemon/blob/master/tcp-protocol/README.md).

Pokud build na Windows skončí chybou EPERM při vytváření výstupních složek,
lze omezit souběžné souborové operace pro daný terminál:

```powershell
$env:UV_THREADPOOL_SIZE = '1'
npm run build
```

## Další algoritmy osvětlení

- `domacnost`: společně řídí podíl rozsvícených domácností podle denního rozvrhu níže.
- `chodba`: mezi západem a východem slunce se pro každé světlo zvlášť střídá
  náhodná pauza 1–5 minut a rozsvícení na 20–30 sekund. První rozsvícení po
  aktivaci v noci také následuje po náhodné pauze. Při východu slunce zhasne
  i případné probíhající rozsvícení. Pauzy lze změnit v `corridor.pause_min_seconds`
  a `corridor.pause_max_seconds` v `backend/config/algorithms.yaml` (výchozí 60 a 300).
- `prodejna`: svítí od `shop.opening_time` včetně do `shop.closing_time`
  v `backend/config/algorithms.yaml` (výchozí 07:00–19:00). Podporuje i interval přes půlnoc.
- `vyloha`: svítí nepřetržitě, také v noci.

Východ a západ se berou z `sunrise` a `sunset`. Časové rozvrhy používají
modelový čas hJOP; při nedostupném či vypnutém modelovém čase místní systémový čas backendu. Změna jiného světla ani opakovaný výběr stejného algoritmu chodby
nerestartují její časování. Změna režimu, restart backendu a nová noc založí nový
náhodný průběh. Stav se přepočítává přibližně jednou za sekundu.


## Čas hJOP

V `backend/config/config.yaml` je spojení s panelovým serverem hJOP:

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

Při výpadku hJOP, čekání na synchronizaci nebo vypnutém modelovém čase se
používá systémový čas backendu. Po obnovení aktivního modelového času se aplikace
automaticky vrátí k hJOP. Zapnutý, ale pozastavený modelový čas zůstává pozastavený.
Web vždy ukazuje zdroj času, rychlost a důvod případného přepnutí.
`hjop.enabled: false` vynutí systémový čas backendu.
Protokol `MOD-CAS` neposkytuje systémové hodiny vzdáleného serveru hJOP;
při vypnutém modelovém čase se proto nepoužívá jeho poslední modelová hodnota.

U `chodba` určuje modelový čas den/noc, ale rozsvícení 20–30 sekund a náhodné
pauzy 1–5 minut vždy běží ve **skutečných sekundách**, i při pozastaveném
modelovém čase. Nastavení `sunrise` a `sunset` zůstává v platnosti.
Po úpravě konfigurace restartujte backend.

Protokol: [hJOP panel server](https://github.com/kmzbrnoI/hJOPserver/wiki/panelServer).


## Domácnosti

Algoritmus `domacnost` řídí všechna takto označená světla společně napříč domy,
skupinami i MTB moduly. Ostatní algoritmy se do počtu domácností nezahrnují.
Na webu se zobrazuje jako **Domácnost**. Dřívější `byt` byl odstraněn
z implementace i nabídky a ve všech dodaných YAML nahrazen za `domacnost`.

| Čas | Cílový podíl rozsvícených domácností |
|---|---|
| 19:00–21:00 | 70 % |
| 21:00–23:00 | Plynulý pokles ze 70 % na 40 % |
| 23:00–04:00 | 10 % |
| 04:00–05:00 | Plynulý růst z 10 % na 50 % |
| 05:00–06:00 | 70 % |
| 06:00–08:00 | 50 % |
| 08:00–19:00 | 5 % |

Čas rozvrhu pochází z hJOP, případně ze systémových hodin, pokud je hJOP vypnuté
v konfiguraci. Rozvrh domácností nezávisí na východu a západu slunce.
Ve 23:00 se cíl změní ze 40 % na 10 %, v 05:00 z 50 % na 70 %.

V `backend/config/algorithms.yaml`:

```yaml
household:
  min_on_seconds: 30
  max_on_seconds: 300
  min_off_seconds: 30
```

Doba každého rozsvícení se náhodně vybírá mezi minimem a maximem.
Všechny tři doby používají skutečné sekundy, také při zrychleném nebo pozastaveném
modelovém čase. Po zhasnutí se stejné světlo nesmí zapnout alespoň 30 sekund.
Časování probíhá v existující sekundové smyčce backendu, přepnutí tedy může
nastat až na následujícím přepočtu (běžně do jedné sekundy).

Počet světel se zaokrouhluje na nejbližší celé číslo (polovina nahoru).
Například 13 domácností: při 70 % je cíl 9 světel, při 5 % jedno světlo;
u tří domácností znamená 5 % cíl nula světel.
Minimální doba svícení a zhasnutí má přednost před okamžitým dosažením procenta.
Při poklesu cíle se proto právě rozsvícená světla nezhasnou před uplynutím minima.
Při vypršení doby svícení se zhasne vždy; není-li zatím dost způsobilých náhrad,
bude podíl dočasně nižší. Krátké svícení s dlouhými pauzami může znemožnit
udržování vysokého podílu i dlouhodobě.

Nová světla se vybírají přednostně z těch, která byla nejdéle zhasnutá;
při shodě náhodně. Opětovný výběr stejného algoritmu ani změna jiného světla
nerestartuje probíhající intervaly. Ruční změna na jiný algoritmus se provede
okamžitě a časování domácnosti pro dané světlo zruší. Restart backendu časování
vytvoří znovu. Před první synchronizací hJOP se domácnosti řídí systémovým časem backendu.


Rozvrh lze měnit v `household.schedule` v `backend/config/algorithms.yaml`.
Každá položka obsahuje `time: "HH:MM"` a `percent: 0–100`.
Podíl platí od daného času do další položky; poslední interval pokračuje přes půlnoc
k prvnímu času. Položky se řadí podle času automaticky, časy se nesmějí opakovat.
Volitelné `end_percent` určuje plynulý přechod z `percent` na tuto hodnotu během
celého intervalu. Bez `end_percent` je podíl po celý interval konstantní.
Například `time: "21:00", percent: 70, end_percent: 40` před položkou ve 23:00
znamená pokles ze 70 % na 40 % během dvou hodin. Ve 23:00 začne platit procento
z nové položky (aktuálně 10 %). Změna rozvrhu vyžaduje restart backendu.

Nastavení chodby je v `backend/config/algorithms.yaml` pod anglickým klíčem `corridor`.
`min_on_seconds` a `max_on_seconds` nastavují délku svícení (výchozí 20–30 s);
`pause_min_seconds` a `pause_max_seconds` délku pauzy. Vše ve skutečných sekundách.
Identifikátor algoritmu ve struktuře kolejiště zůstává `chodba`, na webu „Chodba“.

### Budoucí události

Stránka `/udalosti` zobrazuje změny od nejbližší, včetně času, světla, skupiny a algoritmu.
Denní rozvrhy ukazuje na 24 hodin času kolejiště dopředu. Odpočty jsou ve skutečném čase
při aktuální rychlosti hJOP; při zastaveném modelovém čase čekají za skutečnými časovači.
U chodby je známá nejbližší již vylosovaná změna (východ slunce ji může zrušit).
U domácnosti se zobrazuje nejzazší zhasnutí; pokles cílového podílu může způsobit dřívější
zhasnutí. Další náhodné rozsvícení ještě není určeno a je uvedeno zvlášť.
Přehled plán nijak neovlivňuje. Události přicházejí stejným WebSocketem jako stav,
bez pollování; aktualizují se při přepočtu plánu. Změna algoritmu nebo času hJOP plán změní.
Zobrazený čas je plán změny požadovaného stavu, nikoli potvrzení sepnutí hardwaru.

Algoritmus `minuta` (na webu „Minuta“) svítí v liché minutě a zhasíná v sudé minutě
času kolejiště, včetně přechodu 23:59 → 00:00. Události ukazují jeho dvě nejbližší změny.
Současné události sdílejí jeden odpočet a světla se řadí vedle sebe. U skutečných
časovačů se čas hJOP odhaduje podle aktuální rychlosti; při pozastavení není předpovídán.


## Struktura algoritmů

Každý algoritmus má vlastní soubor a třídu ve složce `backend/algorithm/`.
Společným abstraktním předkem je `Algorithm` v `base.py`:

- `identifier` je původní označení v YAML a API, například `drazni_osvetleni`.
- `name() -> str` vrací název pro web. Název upravujte přímo v dané třídě.
- `compute(now, sunrise, sunset, *, item_id=None) -> int` vypočítá výstup MTB.
- `forecast(...)` vrací budoucí události bez změny časovačů nebo losování.
- `prepare(item_ids, now)` připraví společný stav před výpočtem jednotlivých světel.

Časově plánované algoritmy dědí z `ScheduledAlgorithm`, který je potomkem
`Algorithm` a poskytuje společnou předpověď přechodů. Konkrétní časy přechodů
jsou definované v třídách jednotlivých algoritmů.

| Soubor | Třída | Identifikátor |
|---|---|---|
| `always_on.py` | `AlwaysOn` | `trvale_zapnuto` |
| `always_off.py` | `AlwaysOff` | `trvale_vypnuto` |
| `household.py` | `HouseholdLighting` | `domacnost` |
| `street_lamp.py` | `StreetLamp` | `poulicni_lampa` |
| `railway_lighting.py` | `RailwayLighting` | `drazni_osvetleni` |
| `corridor.py` | `CorridorLighting` | `chodba` |
| `shop.py` | `Shop` | `prodejna` |
| `shop_window.py` | `ShopWindow` | `vyloha` |
| `minute.py` | `Minute` | `minuta` |

Registr tříd je v `backend/algorithm/__init__.py`; názvy pro web se z něj odvozují
voláním `name()`. Novou třídu přidejte do `ALGORITHM_CLASSES`.
Domácnosti používají jednu společnou instanci (`shared = True`), aby se podíl
počítal přes všechna světla. Chodby mají každá svou instanci a časovač.
`backend/algorithms.py` slouží pouze jako kompatibilní rozhraní pro starší volání;
vlastní pravidla jsou ve třídách.


## Kontrola konfigurace při startu

Hodnoty nastavení jsou uvedené v `backend/config/config.yaml` a souboru
určeném klíčem `algorithms_file` (standardně `algorithms.yaml`). Python
nedoplňuje náhradní hodnoty. Všechny sekce a jejich položky v dodaných souborech
jsou povinné; výjimkou je `end_percent` u položky rozvrhu domácností, jehož
vynechání znamená konstantní podíl. Sekce `server` obsahuje pouze `host` a `port`.

Při chybějící hodnotě, neznámém názvu položky nebo neplatném typu se backend
nespustí a chyba uvede příslušnou položku. Například překlep
`pause_min_second` místo `pause_min_seconds` vyvolá chybu konfigurace.
Kontrolují se také porty, kladné časové limity, intervaly a denní rozvrhy.
Starší sloučená konfigurace s klíči `light` nebo `configurate` a českou sekcí
`chodba` se již nenačítá; použijte aktuální rozdělené soubory.
Ani při `hjop.enabled: false` nevynechávejte ostatní položky sekce `hjop`.


Nastavení externích připojení představují neměnné datové třídy `HjopConfig`
a `MtbConfig` v `backend/connection_config.py`. Obě mají typované povinné
položky a ověřují své hodnoty. `HjopClock(config, on_change=...)` a
`DaemonClient(config, on_change=...)` dostávají pouze svou sekci konfigurace.
Callback `on_change` propojuje aplikaci a do YAML nepatří. Formát konfiguračních
souborů se tím nemění.


## Automatické rozpoznání MTB modulů

Před nastavením výstupů se backend démona asynchronně dotáže příkazem `module`
na typ příslušného modulu. Po obnovení spojení se typ zjistí znovu.
Podle typu použije formát MTB-UNI / MTB-UNIS (objekt s `type` a `value`),
nebo MTB-LED (přímo `true` / `false`). V jedné konfiguraci mohou být oba typy.
Neznámému typu se žádné výstupy neposílají a web zobrazí chybu.
Kontroluje se i rozsah čísel výstupů: UNI 0–15, UNIS 0–27, LED 0–31.

Softwarové blikání není implementované. Algoritmus `disco` byl odstraněn;
jeho původní výskyty v dodaných YAML byly nahrazené `trvale_zapnuto`.
Po aktualizaci restartujte backend. Externí kopie YAML upravte stejným způsobem.


Při aktualizaci starší konfigurace odstraňte ze sekce `server` položky
`allowed_origins` a `allowed_origin_regex`; už se nepoužívají. Potom restartujte
backend. Kontrola neznámých konfiguračních položek zůstává zapnutá.
