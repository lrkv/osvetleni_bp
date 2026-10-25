# 📖 Dokumentace: railwayXX.yaml

Hlavní konfigurační soubor pro řízení chytrého osvětlení kolejiště. Definuje zapojení světel, jejich chování a logické uspořádání.

## 1. Struktura souboru
Soubor se skládá ze dvou částí:
* **Globální informace:** Hlavička souboru na prvních řádcích (bez pomlček). Obsahuje `nazev_kolejiste`, `umisteni`, `verze` a `poznamka`.
* **Stromová struktura (`skupiny`):** Samotné rozložení světel a jejich sdružování do stanic a budov.

## 2. Typy uzlů (Skupiny vs. Prvky)
Systém automaticky rozpozná typ uzlu podle jeho parametrů:

### 📁 Skupina (Složka)
Logický celek (stanice, budova, ulice). Nevykonává žádnou akci, pouze sdružuje.
* **Poznávací znak:** Obsahuje parametr `polozky`.
* **Parametry:** `nazev`, `poznamka` (volitelné), `polozky` (seznam vnořených prvků/skupin).

### 💡 Koncový prvek (Světlo)
Konkrétní fyzické světlo s hardwarovou adresou.
* **Poznávací znak:** Obsahuje `adresa` a `algoritmus`. **Nemá** `polozky`.
* **Parametry:** `nazev`, `adresa` (např. "0:5"), `algoritmus` (viz níže).

## 3. Podporované algoritmy (`algoritmus`)
Určují chování světla vůči reálnému/modelovému času:
* `"trvale_zapnuto"` - Svítí nepřetržitě (servis, důležitá hradla).
* `"trvale_vypnuto"` - Zhasnuto (nefunkční lampy, prázdné budovy).
* `"domacnost"` - Náhodné rozsvěcování a zhasínání (simulace života).
* `"poulicni_lampa"` - Spíná se při západu slunce, vypíná při východu.
* `"drazni_osvetleni"` - Zapíná 15 minut po západu a vypíná 15 minut před východem slunce; časy bere z `light.sunset` a `light.sunrise` v `backend/config.yaml`.
* `"disco"` - Rychlé střídání stavů (reklama, hospoda, svářeč).

* `"byt"` - Od západu do 21:00 a od 05:00 do východu slunce.
* `"chodba"` - V noci náhodné rozsvícení na 20–30 sekund, mezi nimi pauzy 1–5 minut; každé světlo nezávisle.
* `"prodejna"` - Od 07:00 do 19:00, konec intervalu už je vypnutý.
* `"vyloha"` - Nepřetržitě zapnuto ve dne i v noci.

## 4. Pravidla pro ruční úpravy
1. **Mezery, nikdy tabulátory:** K odsazování používej vždy 2 mezery.
2. **Uvozovky:** Všechny hodnoty (texty, adresy i algoritmy) piš do uvozovek `" "`.
3. **Pomlčky pro seznamy:** Každá nová položka ve skupině musí začínat pomlčkou a mezerou (`- `).