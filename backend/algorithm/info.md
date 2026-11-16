# Algoritmy osvětlení

Každý algoritmus má vlastní třídu a soubor v této složce. Dědí ze společného
předka `Algorithm` v `base.py`, případně přes `ScheduledAlgorithm`.
`identifier` je označení používané v YAML a API. Metoda `name() -> str` vrací
název zobrazovaný na webu; upravuje se přímo v příslušné třídě.

## Kde se nastavují

- `backend/config/config.yaml`: soubor struktury kolejiště, připojení
  serveru, MTB a hJOP. Klíč `algorithms_file` určuje soubor nastavení algoritmů.
- `backend/config/algorithms.yaml`: časy východu a západu slunce, intervaly
  chodby a rozvrh domácností. Následující popis uvádí současné hodnoty tohoto souboru.
- YAML se strukturou kolejiště: u každého světla klíč `algorithm` vybírá algoritmus,
  například `algorithm: domacnost`. Konkrétní soubor vybírá `layout.file`
  v `config.yaml`.

Konfigurační hodnoty jsou povinné; Python nedoplňuje náhradní nastavení.
Chybějící nebo neznámá položka způsobí chybu při startu s názvem položky.
`end_percent` v rozvrhu domácností je volitelné: bez něj je podíl konstantní.

Po změně YAML souborů restartujte backend. Změna algoritmu přes web se projeví
za běhu; nepřepisuje uloženou YAML konfiguraci.

## Jaký čas se používá

Denní rozvrhy a určení dne/noci používají aktivní modelový čas hJOP.
Pokud je vypnutý, hJOP není dostupné nebo čeká na synchronizaci, používá se
systémový čas počítače s backendem. Zapnutý, ale pozastavený modelový čas
zůstává pozastavený. Web zobrazuje používaný zdroj času.

Délky svícení a pauz chodby i domácností se vždy měří ve **skutečných sekundách**,
nezávisle na zrychlení hJOP. Jejich časovače tedy pokračují i při pauze modelového času.
Výpočty backend provádí přibližně jednou za skutečnou sekundu; přepnutí proto
nemusí nastat přesně na zlomek sekundy.

## Přehled

| Označení v YAML | Název na webu | Třída a soubor | Nastavení v YAML |
|---|---|---|---|
| `trvale_zapnuto` | zapnuto | `AlwaysOn`, `always_on.py` | Nemá vlastní nastavení |
| `trvale_vypnuto` | vypnuto | `AlwaysOff`, `always_off.py` | Nemá vlastní nastavení |
| `domacnost` | Domácnost | `HouseholdLighting`, `household.py` | `household` |
| `poulicni_lampa` | Pouliční lampa | `StreetLamp`, `street_lamp.py` | `sunrise`, `sunset` |
| `drazni_osvetleni` | Drážní osvětlení | `RailwayLighting`, `railway_lighting.py` | `sunrise`, `sunset` |
| `chodba` | Chodba | `CorridorLighting`, `corridor.py` | `sunrise`, `sunset`, `corridor` |
| `prodejna` | Prodejna | `Shop`, `shop.py` | `shop` |
| `vyloha` | Výloha | `ShopWindow`, `shop_window.py` | Nemá vlastní nastavení |
| `minuta` | Minuta | `Minute`, `minute.py` | Střídání je pevné v kódu |

## Trvale zapnuto — `trvale_zapnuto`

Světlo je stále zapnuté. Nezávisí na čase ani na připojení hJOP.
Vlastní parametry v YAML nemá. Výstup pro MTB je `1`.

## Trvale vypnuto — `trvale_vypnuto`

Světlo je stále vypnuté. Nezávisí na čase ani na připojení hJOP.
Vlastní parametry v YAML nemá. Výstup pro MTB je `0`.

## Domácnost — `domacnost`

Řídí společný podíl svítících domácností podle denního rozvrhu. Počítají se
**všechna světla s tímto algoritmem napříč skupinami a moduly MTB**.
Cílový počet je podíl násobený počtem domácností, zaokrouhlený na nejbližší
celé číslo (polovina nahoru). Například při 10 domácnostech a 70 % mají svítit přibližně 7.

Světla se postupně střídají. Každé dostane při rozsvícení náhodnou dobu svícení
mezi nastaveným minimem a maximem. Při poklesu požadovaného podílu může zhasnout
dříve než po vylosované době, ale až po minimální době svícení.
Po zhasnutí musí dodržet minimální pauzu. Přednost při zapínání mají světla,
která byla nejdéle zhasnutá; shody se rozhodují náhodně.

Požadovaný podíl se může dočasně lišit od skutečného kvůli minimální době
svícení, minimální pauze nebo malému počtu světel. Maximální doba zajistí
vystřídání svítících domácností i při neměnném cílovém podílu.

Nastavení v `algorithms.yaml`:

```yaml
household:
  min_on_seconds: 30
  max_on_seconds: 300
  min_off_seconds: 30
  schedule:
    - time: "19:00"
      percent: 70
    - time: "21:00"
      percent: 70
      end_percent: 40
    - time: "23:00"
      percent: 10
```

- `min_on_seconds`: nejkratší automatická doba svícení ve skutečných sekundách.
- `max_on_seconds`: nejdelší automatická doba svícení ve skutečných sekundách.
- `min_off_seconds`: nejkratší pauza před opětovným rozsvícením ve skutečných sekundách.
- `schedule`: denní rozvrh; opakuje se i přes půlnoc.
- `time`: začátek úseku ve formátu `HH:MM`.
- `percent`: požadovaný podíl svítících domácností od začátku úseku.
- `end_percent`: volitelný podíl, ke kterému se hodnota plynule mění až do
  času další položky. Bez něj je podíl v úseku konstantní. Další položka
  začíná vlastní hodnotou `percent`, takže na hranici může nastat skok.

Časy musí být unikátní a rozvrh nesmí být prázdný. Procenta musí být v rozsahu
0–100. Délky musí být kladné a minimum svícení nesmí překročit maximum.
`schedule` je povinné. Při chybějícím nebo chybném nastavení se backend nespustí.

Současný úplný rozvrh:

| Interval | Cílový podíl |
|---|---|
| 04:00–05:00 | Plynule z 10 % na 50 % |
| 05:00–06:00 | 70 % |
| 06:00–08:00 | 50 % |
| 08:00–19:00 | 5 % |
| 19:00–21:00 | 70 % |
| 21:00–23:00 | Plynule ze 70 % na 40 % |
| 23:00–04:00 | 10 % |

Omezení délky svícení platí pro automatický běh domácnosti. Ruční změna
algoritmu světla může jeho aktuální cyklus přerušit.

## Pouliční lampa — `poulicni_lampa`

Rozsvítí se **1 hodinu před západem slunce** a svítí do **1 hodiny po východu
slunce**. Ranní hranice je v kódu zahrnuta, takže vypne až po jejím překročení.

Používá společné hodnoty `sunrise` a `sunset` z `algorithms.yaml`.
Při současných hodnotách `sunrise: "5:32"` a `sunset: "20:09"` svítí od 19:09
do 06:32 včetně. Posuny o jednu hodinu jsou pevné v `street_lamp.py`.

## Drážní osvětlení — `drazni_osvetleni`

Rozsvítí se **15 minut po západu slunce** a zhasne **15 minut před východem
slunce**. Okamžik rozsvícení je zahrnutý, okamžik zhasnutí už ne.
Funguje i tehdy, když posun západu nebo východu překročí půlnoc.

Používá společné `sunrise` a `sunset`. Při současných hodnotách svítí od 20:24
do 05:17. Posuny o 15 minut jsou pevné v `railway_lighting.py`.

## Chodba — `chodba`

Ve dne je zhasnutá. Noc začíná v `sunset` včetně a končí v `sunrise`, kdy světlo
zhasne i před vypršením vylosované doby svícení.

Na začátku noci nebo při prvním výpočtu v noci nejprve vylosuje pauzu.
Potom opakovaně střídá náhodnou dobu svícení a náhodnou pauzu.
Každé světlo má samostatnou instanci a vlastní časovač.

Nastavení v `algorithms.yaml`:

```yaml
corridor:
  min_on_seconds: 20
  max_on_seconds: 30
  pause_min_seconds: 60
  pause_max_seconds: 300
```

- `min_on_seconds`, `max_on_seconds`: meze délky jednoho rozsvícení.
- `pause_min_seconds`, `pause_max_seconds`: meze pauzy mezi rozsvíceními.

Všechny hodnoty jsou skutečné sekundy, musí být kladná celá čísla a každé
minimum musí být nejvýše příslušné maximum. Náhodný výběr zahrnuje obě meze.
Určení noci používá společné `sunrise` a `sunset`.

## Prodejna — `prodejna`

Svítí každý den od nastaveného času otevření včetně do času zavření, kdy zhasne.
Mimo tento interval je vypnutá. Časy se řídí používaným časem aplikace.

Nastavení v `algorithms.yaml`:

```yaml
shop:
  opening_time: "07:00"
  closing_time: "19:00"
```

- `opening_time`: čas rozsvícení ve formátu `HH:MM`.
- `closing_time`: čas zhasnutí ve formátu `HH:MM`.

Oba časy jsou povinné. V dodané konfiguraci jsou 07:00 a 19:00. Musí být různé a v rozsahu
00:00–23:59. Pokud je zavírací čas dřívější než otevírací, interval pokračuje
přes půlnoc (například 22:00–02:00). Stejné nastavení platí i pro budoucí události.
Po změně souboru restartujte backend.

## Výloha — `vyloha`

Svítí nepřetržitě celý den i noc. Chová se stejně jako `trvale_zapnuto`,
ale má vlastní označení a název pro web. Vlastní parametry v YAML nemá.

## Minuta — `minuta`

V **lichou minutu svítí**, v **sudou minutu je zhasnutá**. Stav platí po celou
minutu. Například ve 12:01 svítí, ve 12:02 nesvítí a ve 12:03 opět svítí.
Řídí se používaným časem aplikace, tedy případně zrychleným časem hJOP.
Vlastní parametry v YAML nemá.

## Budoucí události a názvy

Předpověď událostí je součástí tříd algoritmů. U prodejny, pouliční lampy,
drážního osvětlení a minuty lze vypočítat konkrétní další přechody.
U chodby je známý nejbližší již vylosovaný přechod; další náhodné intervaly
se dopředu nelosují. U domácnosti je u svítícího světla znám nejzazší čas
zhasnutí, skutečné zhasnutí může nastat dříve při snížení podílu.
Budoucí rozsvícení domácnosti předem určeno není.
Trvalé režimy žádnou automatickou změnu neplánují.

Chcete-li změnit pouze popisek na webu, upravte `name()` v dané třídě.
Změna `identifier` by vyžadovala také změnu označení v konfiguracích.
Registr všech tříd je v `__init__.py`.
