# Instalace a nasazení aplikace Osvětlení kolejiště

Tento návod patří do kořenové složky projektu, vedle složek `backend` a `frontend`.
Příkazy pro Windows zadávejte v PowerShellu. PyCharm není ke spuštění potřeba.

## 1. Co je potřeba

- Python 3.11 nebo novější, dostupný příkazem `python`.
- Node.js 24.11 nebo novější v řadě 24, včetně npm. Tato řada vyhovuje aktuálnímu `package-lock.json`.
- Připojení k internetu při první instalaci knihoven a balíčků.
- Webový prohlížeč na počítači, telefonu nebo tabletu.
- Pro ovládání světel běžící MTB Daemon s připojenými moduly.
- Pro modelový čas běžící panelový server hJOP. Lze jej vypnout a používat systémový čas backendu.

Verze ověřte:

```powershell
python --version
node --version
npm --version
```

MTB Daemon a hJOP jsou samostatné programy. Příkazy pro instalaci knihoven níže je neinstalují.
Backend, frontend, MTB Daemon a hJOP mohou běžet na různých počítačích, pokud se po síti spojí.

## 2. Přenesení projektu

Na cílový počítač přeneste projekt včetně těchto souborů a složek:

```text
osvetleni_bp/
├── backend/                 # Všechny .py, requirements a YAML soubory, včetně podsložek
│   └── configurate/          # Nastavení a struktury kolejišť
│       ├── config.yaml
│       ├── algorithms.yaml
│       └── vystava_test.yaml # Příklad struktury kolejiště
├── frontend/                # Zdrojové soubory, public, package.json a package-lock.json
├── README.md
└── NASAZENI.md
```

Pokud projekt přenášíte přes Git, zahrňte také nově přidané soubory; samotné neuložené lokální změny se nepřenesou.
Nemusíte kopírovat `.venv`, `node_modules`, `__pycache__`, `.nuxt`, `.output` ani `.idea`.
Pro instalaci ze zdrojů je vytvoříte znovu. Virtuální prostředí a `node_modules` nepřenášejte mezi různými systémy.

Otevřete terminál v kořenové složce projektu, například:

```powershell
cd C:\kolejiste\osvetleni_bp
```

## 3. Instalace backendu na Windows

V kořenové složce projektu spusťte:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Příkazy používají Python přímo z virtuálního prostředí, takže není nutná aktivace prostředí ani změna zásad PowerShellu.
`requirements.txt` obsahuje provozní závislosti; jejich další závislosti instaluje pip automaticky.
Verze Python knihoven jsou omezené rozsahy, nikoli uzamčené na jednu přesnou sadu.

## 4. Nastavení backendu a kolejiště

Otevřete `backend/configurate/config.yaml`.

### Struktura kolejiště

```yaml
layout:
  file: "vystava_test.yaml"

algorithms_file: "algorithms.yaml"
```

`layout.file` určuje soubor se skupinami, světly, adresami výstupů a algoritmy.
Cesty jsou relativní vůči `backend/configurate/config.yaml`. Vyberte nebo upravte strukturu odpovídající skutečnému kolejišti.
Časy, intervaly a podíly svítících domácností nastavujte v `backend/configurate/algorithms.yaml`.

### Server aplikace

```yaml
server:
  host: "0.0.0.0"
  port: 8000
```

Toto je jen výřez sekce. Zachovejte také její existující `allowed_origins` a `allowed_origin_regex`.
`0.0.0.0` zpřístupní backend na síťových rozhraních počítače. Pro přístup pouze z tohoto počítače použijte `127.0.0.1`.
Adresa `0.0.0.0` se nepíše do prohlížeče ani jako cílová adresa backendu ve frontendu.

### MTB Daemon

V existující sekci `mtb` nastavte:

```yaml
mtb:
  host: "127.0.0.1"
  port: 3841
  timeout: 5
  reconnect_delay: 3
```

Je-li démon na jiném počítači, nahraďte `127.0.0.1` jeho IP adresou nebo názvem.
`127.0.0.1` i `localhost` zde označují počítač s backendem.

### hJOP

V existující sekci `hjop` nastavte `enabled`, `host` a `port`:

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

Panelový server hJOP musí být zapnutý a dostupný na uvedené adrese.
Pro použití skutečného systémového času backendu nastavte `enabled: false`.
Při nedostupném hJOP aplikace automaticky nepřechází na systémový čas; web ukáže stav spojení.

Po změně backendových YAML souborů restartujte backend.
Před prvním spuštěním zkontrolujte adresy světel: po připojení k MTB backend začne odesílat jejich požadované stavy.

## 5. Nastavení adresy backendu ve frontendu

Upravte `frontend/public/backend-config.json` ještě před sestavením frontendu.

Pokud frontend a backend běží na stejném počítači:

```json
{
  "backendUrl": "",
  "backendPort": 8000
}
```

Prázdná adresa použije hostname/IP a protokol stránky otevřené v prohlížeči, ale nastaví port 8000.
Díky tomu funguje přístup i z jiného zařízení v LAN.

Pokud backend běží na jiném počítači:

```json
{
  "backendUrl": "http://192.168.1.30:8000",
  "backendPort": 8000
}
```

IP nahraďte adresou počítače s backendem. Vyplněné `backendUrl` má přednost; `backendPort` se potom ignoruje.
Pro přístup z telefonu nepoužívejte `localhost`: prohlížeč by hledal backend v telefonu.
WebSocket se odvodí z této adresy automaticky.

## 6. Instalace a sestavení frontendu

Z kořenové složky projektu:

```powershell
cd frontend
npm ci
npm run build
```

`npm ci` instaluje balíčky podle `package-lock.json`, který přeneste společně s `package.json`.
Pro sestavení jsou potřebné i vývojové závislosti, proto při této instalaci nepoužívejte `--omit=dev`.
Výsledek je ve složce `frontend/.output`.

Pokud na Windows sestavení skončí chybou `EPERM`, zkuste v témže terminálu:

```powershell
$env:UV_THREADPOOL_SIZE = '1'
npm run build
```

Sestavení zkopíruje konfiguraci adresy backendu do `.output/public/backend-config.json`.
Po nasazení lze upravit přímo tuto kopii a obnovit stránku; další sestavení ji opět nahradí verzí ze složky `public`.

## 7. Spuštění pro běžný provoz

Otevřete dva terminály. Oba procesy musí zůstat spuštěné.

**První terminál — backend, z kořenové složky projektu:**

```powershell
.\.venv\Scripts\python.exe backend/main.py
```

**Druhý terminál — frontend, ze složky `frontend`:**

```powershell
$env:HOST = '0.0.0.0'
$env:PORT = '3000'
node .output/server/index.mjs
```

Explicitní `HOST` zpřístupní frontend také v LAN. Port lze změnit, ale je nutné tomu přizpůsobit adresu v prohlížeči a případně povolené originy backendu.

Na tomto počítači otevřete:

```text
http://localhost:3000
```

Na jiném zařízení ve stejné síti například:

```text
http://192.168.1.20:3000
```

IP nahraďte adresou počítače s frontendem. Na Windows ji zjistíte příkazem `ipconfig` jako IPv4 adresu aktivního síťového adaptéru.
Procesy ukončíte v jejich terminálech pomocí `Ctrl+C`.
Pro jedno kolejiště spouštějte jedinou instanci backendu, s jedním Uvicorn workerem.

## 8. Síť, firewall a oddělené servery

Povolte potřebná spojení v používané privátní síti:

| Port TCP | Na kterém počítači | Kdo se připojuje |
|---|---|---|
| 3000 | Frontend | Prohlížeče uživatelů |
| 8000 | Backend | Prohlížeče uživatelů — HTTP i WebSocket |
| 3841 | MTB Daemon | Backend |
| 5896 | hJOP | Backend, pokud je hJOP zapnuté |

Porty odpovídají výchozím hodnotám; při vlastní konfiguraci použijte své hodnoty.
Prohlížeč se připojuje přímo k backendu, takže nestačí zpřístupnit jen frontend.

V `server.allowed_origins` backendu povolujte adresu **frontendu**, včetně protokolu a portu.
Dodaný `allowed_origin_regex` povoluje běžné privátní IPv4 adresy LAN a localhost.
Při použití vlastního DNS názvu přidejte do seznamu například `http://kolejiste.local:3000`.

Při použití HTTPS musí být dostupný i HTTPS backend; WebSocket potom používá WSS.
Pokud provozujete aplikaci za reverzní proxy, musí předávat také WebSocket spojení `/api/ws`.
Aplikace nemá přihlášení uživatelů a je určená pro důvěryhodnou LAN.

## 9. Jak ověřit správné spuštění

1. Backend vypíše úspěšné spuštění Uvicornu a neukončí se chybou.
2. Web načte správné kolejiště a zobrazí skupiny i světla.
3. Na horní liště je správný zdroj času a případně rychlost hJOP.
4. Stav MTB ukazuje připojení a potvrzení výstupů. Při odpojení web zobrazí upozornění.
5. Z telefonu připojeného do stejné LAN lze otevřít IP adresu frontendu.
6. Stránky Seznam, Mapa a Budoucí události dostávají aktualizace.

Barva světla ukazuje požadovaný stav algoritmu, nikoli fyzické měření žárovky.
Změny algoritmů přes web jsou v paměti; po restartu se znovu načte struktura z YAML.
Trvalou změnu proveďte také v příslušném souboru kolejiště.

## 10. Aktualizace a opakované spuštění

Při běžném opětovném spuštění stačí příkazy z části 7. Instalaci a sestavení neopakujte při každém startu.

Při aktualizaci projektu:

1. Zálohujte vlastní konfigurace a soubory kolejiště.
2. Zastavte backend i frontend.
3. Nahraďte zdrojové soubory novou verzí a zkontrolujte vlastní konfigurace.
4. V kořeni spusťte znovu instalaci z `backend/requirements.txt`.
5. Ve složce `frontend` spusťte `npm ci` a `npm run build`.
6. Zkontrolujte nasazený `backend-config.json` a spusťte oba procesy.

Automatické spuštění po zapnutí počítače není v projektu nastavené.
Ve Windows lze později vytvořit samostatné úlohy pro backend a frontend v Plánovači úloh.

## 11. Vývoj a testy

Pro vývoj frontendu lze místo sestavení a produkčního spuštění použít ze složky `frontend`:

```powershell
npm run dev
```

Pro testy backendu, z kořenové složky:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Pro testy frontendu, ze složky `frontend`:

```powershell
node --test tests/lighting.test.mjs tests/eventGroups.test.mjs
```

Backendové testy používají lokální testovací servery; neovládají skutečné kolejiště.

## 12. Linux a macOS

Aplikační kód používá běžné síťové rozhraní a relativní cesty. Tyto systémy však zatím nebyly pro tento projekt ověřené.
Instalační a spouštěcí příkazy se liší od Windows:

```bash
# Z kořenové složky projektu
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python backend/main.py
```

Ve druhém terminálu:

```bash
cd frontend
npm ci
npm run build
HOST=0.0.0.0 PORT=3000 node .output/server/index.mjs
```

Dostupnost MTB Daemona, hJOP, případných ovladačů a hardwaru řešte pro daný systém zvlášť; mohou také běžet na jiném počítači.

## 13. Nejčastější potíže

| Problém | Co zkontrolovat |
|---|---|
| Příkaz `python`, `node` nebo `npm` není rozpoznán | Instalaci programu a jeho dostupnost v PATH; po instalaci otevřete nový terminál. |
| `ModuleNotFoundError` | Backend spouštějte Pythonem z `.venv` a nainstalujte `backend/requirements.txt` do stejného prostředí. |
| Web funguje na počítači, ale ne v telefonu | IP adresu, stejnou LAN, naslouchání na `0.0.0.0` a firewall. |
| Frontend se načte, backend je odpojený | Adresu v nasazeném `backend-config.json`, dostupnost portu 8000 a povolené originy. |
| Spojení s MTB nebo hJOP bylo odmítnuto | Zda cílový program běží, správný host/port, firewall a zda `localhost` skutečně označuje správný počítač. |
| Modelový čas stojí | Stav spojení, synchronizaci a běh modelového času v hJOP. Pro systémový čas nastavte `hjop.enabled: false` a restartujte backend. |
| Port je již obsazený | Zda už neběží druhá instance; ukončete ji nebo zvolte jiný port. |
| Po změně nastavení se nic nezměnilo | Backendové YAML vyžadují restart. Adresu backendu měňte také v nasazené kopii JSON a obnovte stránku. |
| `npm ci` hlásí nepodporovaný Node.js | Ověřte verzi; použijte například řadu Node.js 24 od 24.11. |
