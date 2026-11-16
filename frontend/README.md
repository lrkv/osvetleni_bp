# Frontend osvětlení kolejiště

Doporučená verze Node.js je řada 24 od 24.11. Podporovaný rozsah je uvedený
v `package.json`; instalace na nepodporovaném Node.js skončí s chybou
`EBADENGINE`. Pro nvm je připravený soubor `.nvmrc` (`nvm use`).

Příkazy spouštějte ve složce `frontend`:

```sh
node --version
npm --version
npm ci
```

`npm ci` použije přesné verze z verzovaného `package-lock.json`. Instalujte i
vývojové závislosti; nepoužívejte `--omit=dev`. Při úmyslné aktualizaci balíčků
použijte `npm install` a aktualizujte společně `package.json` a `package-lock.json`.

## Vývoj

```sh
npm run dev
```

Frontend je dostupný na portu 3000. Adresa backendu se nastavuje v
`public/backend-config.json`; prázdné `backendUrl` používá hostname prohlížeče
s portem `backendPort`.

## Sestavení pro Node.js server

```sh
npm run build
node .output/server/index.mjs
```

## Statické sestavení

```sh
npm run generate
```

Na webový server se nasazuje obsah `.output/public`, včetně podstránek
`mapa` a `udalosti`. Při generování nemusí běžet backend; prohlížeč se k němu
připojí až po otevření stránky. Statický server musí podporovat adresářové
indexy (`/mapa/index.html`, `/udalosti/index.html`).

Po statickém generování nepoužívejte `node .output/server/index.mjs` — tento
způsob spuštění patří k `npm run build`.

Podrobný postup včetně konfigurace backendu je v [návodu nasazení](../NASAZENI.md).
Při selhání pošlete první konkrétní chybu a výstup `node --version` a
`npm --version`; samotné poslední hlášení o neúspěšném příkazu příčinu neukazuje.
