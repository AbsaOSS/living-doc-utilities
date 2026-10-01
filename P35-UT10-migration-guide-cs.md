# Průvodce migrací: framing pass (P35-UT10)

**Pro koho:** vlastník `living-doc-utilities` a reviewer PR k issue #183; dále autoři navazujících úkolů (`P35-CGH1b1`, `collector-ad`, `toolkit`), kteří čtou výstup parserů.
**Stav k 2026-10-01:** implementováno na větvi `refactor/183-framing-pass`, **necommitnuto**. Tento soubor leží v kořeni `living-doc-utilities` vedle `OPEN_POINTS.md` a do commitu nepatří. `make qa` zelené (970 testů, pokrytí 98,5 %). PR popis je v `living-doc-utilities/pr.md` (neverzovaný soubor).
**Všechny příklady níže** byly spuštěny proti staré verzi (`master`, `216d866`) i proti nové a výstupy jsou skutečné, ne odhadnuté.

## Obsah

- [1. Shrnutí](#1-shrnutí)
- [2. Co znamená „čeká na tvé OK"](#2-co-znamená-čeká-na-tvé-ok)
- [3. Rozhodnutí po skupinách](#3-rozhodnutí-po-skupinách)
- [4. Co se dělo během implementace](#4-co-se-dělo-během-implementace)
- [5. Dopad změn](#5-dopad-změn)
- [6. Staré vs. nové řešení podrobně](#6-staré-vs-nové-řešení-podrobně)
- [7. Příklady pro všechny typy hlaviček](#7-příklady-pro-všechny-typy-hlaviček)
- [8. Otevřené body](#8-otevřené-body)
- [9. Jak změnu ověřit](#9-jak-změnu-ověřit)

---

## 1. Shrnutí

Dřív si hranice (kde začíná a končí hlavička, kde začíná a končí sekce nebo klíč) **každý formát odvozoval dvakrát**: jednou v normalizéru (`normalize.py`) a podruhé v parseru. Obě místa se musela shodnout „ručně". Kde se neshodla, ztrácela se data — často tiše, bez varování. Čtyři známé chyby (blocker z `#176`, `D20`, nezakotvené `*/`, substringové `"LIVING DOC"`) měly jednu společnou příčinu: **predikát čte text řádku, aniž ví, kde ten řádek strukturálně stojí.**

Nově existuje **jeden průchod rámováním (framing pass)** v novém modulu `authoring/framing.py`. Pro každý vstup jednou a podle **pozice** rozhodne, kam který řádek patří. Normalizér i parser pak čtou **ten jeden výsledek**. Žádná hranice se neodvozuje dvakrát a žádná se nehledá podle textu řádku.

Na kanonickém vstupu (golden korpus na canon commitu `b28820e`, všechny vstupy z testové sady) je výstup **bit po bitu stejný**. Rozdíly vznikají jen na nekanonickém vstupu — a ty jsou vypsané v [kapitole 7](#7-příklady-pro-všechny-typy-hlaviček).

## 2. Co znamená „čeká na tvé OK"

Zadání (`P35-UT10-prompt.md`, sekce *Hold behaviour constant*) říká doslova:

> „the only intended output changes are D20's phantom criterion and the `*/` close. If any other output moves, stop and report it rather than updating the expectation."

Při ověřování jsem starý a nový kód porovnal na 60 000 automaticky pozměněných vstupech a našel **další skupiny vstupů, kde se výstup změnil** — nad rámec `D20` a `*/`. Žádná z nich nemění existující test ani golden fixture, všechny jsou na nekanonickém vstupu. Ale zadání výslovně říká „zastav a nahlas". Proto:

- implementace je hotová, ale **necommitnutá**,
- každá skupina je popsaná v `pr.md` (skupiny 3–12) a níže s příklady,
- **rozhodnutí je tvoje**: buď je přijmeš jako záměrné (a PR jde tak, jak je), nebo u konkrétní skupiny řekneš, že chceš staré chování zpět.

Přehled všech skupin (podrobně, s možnostmi a doporučením, v [kapitole 3](#3-rozhodnutí-po-skupinách)):

| # | Skupina | Formát | Mění výstup parseru? | Lze vrátit? | Doporučení |
|---|---|---|---|---|---|
| 1 | `D20`: `AC:` řádek v textu položky | issue body, HTML | ano | — zadáno issue | přijmout |
| 2 | `*/` uzavírá komentář jen na konci řádku | PageObject | ano | — zadáno issue | přijmout |
| 3 | titulek podle pozice | `.feature`, PageObject | ano | ne (AC 2) | přijmout |
| 4 | sekci otevírá jen `##` | issue body, HTML | ano | ne bez porušení AC 1 | přijmout |
| 5 | blok kritéria trvá do další linky | `.feature` | jen text varování | ne bez porušení AC 1 | přijmout |
| 6 | odrážkový klíč s textem na vlastním řádku | `.feature` | ano | ne bez porušení AC 1 | přijmout |
| 7 | tab hned za `#` / ` * ` | `.feature`, PageObject | ano | ne bez porušení AC 1 | přijmout |
| 8 | prázdný řádek bez `#` uvnitř hlavičky | `.feature` | ne (jen `normalize`) | jen výměnou | přijmout |
| 9 | řádek bez ` * ` uvnitř komentáře | PageObject | ano | jen výměnou | přijmout |
| 10 | chybějící / neuzavřený rámec | `.feature`, PageObject | ne (jen `normalize`) | částečně | přijmout |
| 11 | pravidlo 6 jako první fáze | všechny kromě scénářů | ne (jen `normalize`) | ano, levně | přijmout (vrátit jen pro úplnou shodu `normalize`) |
| 12 | `notes:` na cross-reference hlavičce | PageObject | ano | ne bez návratu chyby | přijmout |

## 3. Rozhodnutí po skupinách

Ke každé skupině: co se mění, krátký příklad (výstupy jsou skutečné, ze spuštění staré a nové verze), proč k tomu došlo, jak pravděpodobné to je v praxi, jaké jsou možnosti a moje doporučení. Na konci každé skupiny je místo pro tvoje rozhodnutí. Delší příklady podle typu hlavičky jsou v [kapitole 7](#7-příklady-pro-všechny-typy-hlaviček).

Společný princip: skupiny 4–11 jsou vstupy, na kterých se **starý normalizér a starý parser neshodly** o hranici. Jeden rámec musí zvolit jedno čtení; u 4–11 volí čtení parseru, protože výstup parseru je kontrakt. Když se přesto mění výstup parseru, je to proto, že normalizér teď přepíše řádek, který parser čte (typicky `•` → `-`). Skupina 12 volí čtení normalizéru, protože čtení parseru tam bylo právě tou chybou.

### Skupina 1 — `D20`: `AC:` řádek v textu položky není kritérium

- **Formát:** issue body, HTML markdown (Azure DevOps).
- **Co se mění:** řádek ve tvaru `AC:…`, který je hlouběji než `- ` otevřené položky odrážkového pole (i přes prázdný řádek), je textem té položky. Nevznikne z něj kritérium ani `MALFORMED_AC` a normalizér ho nepřepisuje jako hlavičku kritéria.
- **Příklad:**

  ```markdown
  ## Business Value

  - Parent.
    AC:US-001-01 (v1.0.0 - active)
    - desc here.
  ```

  Dřív: `business_value` drží text **a** vznikne kritérium `US-001-01` („desc here."), bez varování. Teď: jen `business_value`, žádné kritérium.
- **Proč:** zadáno issue (`D20`, AC 3).
- **Pravděpodobnost v praxi:** dnes nízká, dopad vysoký (kritérium, které nikdo nenapsal, ovlivní stav i pokrytí).
- **Možnosti:** žádné — je to cíl úkolu.
- **Doporučení:** přijmout.
- **Rozhodnutí:** zadáno issue, nevyžaduje rozhodnutí.

### Skupina 2 — `*/` uzavírá komentář PageObjectu jen na konci řádku

- **Formát:** PageObject.
- **Co se mění:** komentář hlavičky končí na prvním řádku, který **končí** `*/`. `*/` uprostřed hodnoty ho nekončí; odsazené holé ` *   */` ho končí stejně jako ` */` nebo kanonické `=== */`.
- **Příklad:**

  ```typescript
   * purpose:               Multi-step wizard (see /* legacy */ wizard).
   * page-object:           AccountSetupWizardPage.ts
   * notes:
   *   • Step order is fixed; the review step cannot be skipped.
   *   • The wizard shares one URL with its step files.
  ```

  Dřív: normalizér na `*/` v `purpose` „zavřel" hlavičku, `•` nepřepsal → `notes = []` + `UNPARSED_BULLET_LINE` (obě poznámky ztraceny). Teď: obě poznámky, žádné varování. S odsazeným ` *   */` dřív končila poslední poznámka textem `… files. */`, teď bez něj.
- **Proč:** zadáno issue (AC 4).
- **Pravděpodobnost v praxi:** nízká až střední (`/* … */` v prozaickém textu hodnoty, ručně psané zavření komentáře).
- **Možnosti:** žádné — je to cíl úkolu.
- **Doporučení:** přijmout.
- **Rozhodnutí:** zadáno issue, nevyžaduje rozhodnutí.

### Skupina 3 — titulek se hledá podle pozice

- **Formát:** `.feature` hlavička, PageObject (plná i cross-reference).
- **Co se mění:** titulek je první neprázdný řádek hned za otevírací linkou (`# ===`, `/* ===`). Řádek ve tvaru `LIVING DOC — …` kdekoli jinde — citace v poznámce, řádek nad linkami, za poslední linkou, soubor bez linky — titulkem není:
  - parser vrací `MISSING_ENTITY_ID`, kde dřív vzal id z toho řádku,
  - normalizér na něj neuplatní pravidla 5/5b,
  - v PageObjectu takový řádek za klíči neukončí otevřený klíč, ale je jeho textem.
- **Příklad (nejzávažnější případ):**

  ```typescript
  /* =============================================================================
   * =============================================================================
   * surface_type:          UI
   * notes:
   *   - See the LIVING DOC — FEAT-002 · Breached Password Check banner.
   * ============================================================================= */
  ```

  Dřív: entita **`FEAT-002`** — data PageObjectu se zapsala na cizí Feature. Teď: `MISSING_ENTITY_ID`.
- **Proč:** vyžaduje to AC 2 („the banner title is identified by position, not by matching its text"). Starý parser hledal titulek v bloku a pak „kdekoli v souboru" — přesně ta třída chyby, kterou úkol ruší.
- **Pravděpodobnost v praxi:** nízká; kanon i golden fixtures mají titulek vždy hned za linkou. Dopad nové verze je viditelný (`MISSING_ENTITY_ID`), ne tichý.
- **Možnosti:**
  - A) přijmout;
  - B) vrátit hledání „kdekoli", když na pozici titulek chybí — znovu by text rozhodoval o struktuře a porušilo by to AC 2. Nedoporučuji.
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B vrátit`

### Skupina 4 — v issue body otevírá sekci jen `##`

- **Formát:** issue body, HTML markdown.
- **Co se mění:** parser vždy uznával jen `##`. Starý normalizér ale přepínal kontext na **jakémkoli** nadpisu (`#`, `###`, …) — pod `### Detail` v `## Business Value` přestal přepisovat odrážky, pod `### Status` zmenšoval písmena. Teď oba čtou jen `##`.
- **Příklad:**

  ```markdown
  ## Business Value

  ### Detail

  • Fewer support calls.
  ```

  Dřív: `business_value = []` + `UNPARSED_BULLET_LINE` („### Detail • Fewer support calls."). Teď: `business_value = ["Fewer support calls."]` + `UNPARSED_BULLET_LINE` jen pro „### Detail".

  ```markdown
  ## Description

  foo

  ### Status

  Active
  ```

  Dřív: `narrative = "foo ### Status active"`. Teď: `narrative = "foo ### Status Active"`.
- **Proč:** AC 1 — normalizér a parser čtou tytéž sekce.
- **Pravděpodobnost v praxi:** střední — podnadpisy `###` v těle GitHub issue autoři používají. Dopad je převážně pozitivní (odrážky pod `###` se už neslepí).
- **Možnosti:**
  - A) přijmout;
  - B) normalizér by znovu přepínal kontext na každém nadpisu — dvě různá čtení sekcí, porušuje AC 1;
  - C) i parser by ukončil sekci na každém nadpisu — text pod `###` v odrážkovém poli by nepatřil nikam a ztratil by se.
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B` `[ ] C`

### Skupina 5 — v `.feature` hlavičce trvá blok kritéria do další linky

- **Formát:** `.feature` hlavička.
- **Co se mění:** parser vždy četl blok kritéria od `AC:` hlavičky do další linky `# ===` a klíče v něm nečetl. Starý normalizér řádek `klíč:` v bloku považoval za klíč, blok tím ukončil a třeba zmenšil hodnotu `status:`. Teď blok trvá do linky pro oba.
- **Příklad:**

  ```gherkin
  # acceptance_criteria:
  #   AC:US-001-01 (v1.0.0 - active)
  #     - desc
  #   status: Deprecated
  # =====
  ```

  Dřív (normalize): `#   status: deprecated`. Teď: `#   status: Deprecated`. Výstup parseru (stav, kritérium) je stejný; liší se jen text řádku, který gramatika případně cituje ve varování `UNPARSED_AC_LINE`.
- **Proč:** AC 1.
- **Pravděpodobnost v praxi:** nízká (klíč za kritérii je mimo kanon).
- **Možnosti:**
  - A) přijmout;
  - B) normalizér by klíče v bloku znovu četl — neshoda s parserem, porušuje AC 1;
  - C) i parser by klíče za kritérii četl (např. `notes:` za kritérii by se stal poznámkou entity) — mění výstup parseru a je to otázka kanonu, ne tohoto úkolu.
- **Doporučení:** A (C případně jako samostatné rozhodnutí kanonu).
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B` `[ ] C`

### Skupina 6 — odrážkový klíč s textem na vlastním řádku

- **Formát:** `.feature` hlavička.
- **Co se mění:** `preconditions: text` (nebo `business_value: …`) parser vždy otevřel jako seznam a položky pod ním četl. Starý normalizér ho kvůli textu za dvojtečkou za seznam nepovažoval, takže nepřepsal `•`, `+`, `–` a nesledoval zalomené řádky položek. Teď oba čtou seznam.
- **Příklad:**

  ```gherkin
  # status: active
  # preconditions: The customer is signed in.
  #   + The account is active.
  ```

  Dřív: `preconditions = []` + `UNPARSED_BULLET_LINE`. Teď: `preconditions = ["The account is active."]` + `UNPARSED_BULLET_LINE` jen pro větu na řádku klíče.
- **Proč:** AC 1.
- **Pravděpodobnost v praxi:** nízká až střední; dopad pozitivní (položka se už neztratí).
- **Možnosti:**
  - A) přijmout;
  - B) normalizér by znovu nepřepisoval — neshoda s parserem, porušuje AC 1.
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B vrátit`

### Skupina 7 — tab hned za značkou komentáře

- **Formát:** `.feature` hlavička, PageObject.
- **Co se mění:** pravidlo 6 udělá z `#<tab>x` řádek `# x`. Starý normalizér četl takový řádek s odsazením 1; starý parser (četl normalizovaný text znovu) s odsazením 0 — stejně jako gramatika kritérií. Teď se jedna mezera stane mezerou značky komentáře a odsazení je 0 pro všechny.
- **Příklad:**

  ```gherkin
  # status: active
  # business_value:
  #   - Old accounts carry
  #<TAB>  status: Deprecated
  ```

  Dřív: normalizér řádek považoval za text položky a nezměnil ho; parser ho četl jako klíč → `MALFORMED_STATUS`, stav `None`. Teď: oba ho čtou jako klíč, normalizér ho zmenší → stav `deprecated`, žádné varování.
- **Proč:** AC 1 a shoda s gramatikou kritérií, která normalizovaný text čte stejně.
- **Pravděpodobnost v praxi:** nízká (editor vloží tab místo mezer).
- **Možnosti:**
  - A) přijmout;
  - B) rámec by četl `#<tab>x` s odsazením 1 — neshoda s gramatikou i s tím, jak normalizovaný text přečte kdokoli další; první verze implementace to tak měla a měnila tím výstup parseru jinde (vnořené položky, `MISINDENTED_LINE`).
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B vrátit`

### Skupina 8 — prázdný řádek bez `#` uvnitř `.feature` hlavičky

- **Formát:** `.feature` hlavička.
- **Co se mění:** parser vždy na takovém řádku otevřený klíč zavřel. Starý normalizér řádky bez `#` přeskakoval, takže klíč pro něj pokračoval a odrážky za prázdným řádkem dál přepisoval. Teď prázdný řádek zavírá klíč pro oba.
- **Příklad:**

  ```gherkin
  # business_value:
  #   - a

  #   • b
  ```

  Dřív (normalize): `#   - b`. Teď: `#   • b`. Výstup parseru je v obou verzích stejný — `b` parser nečetl ani dřív.
- **Proč:** AC 1.
- **Pravděpodobnost v praxi:** střední (prázdný řádek v hlavičce se snadno přihodí), dopad jen na text `normalize()`.
- **Možnosti:**
  - A) přijmout — výstup parseru beze změny;
  - B) prázdný řádek bez `#` ignorovat pro oba — klíč by pokračoval přes prázdný řádek a změnil by se výstup parseru (`b` by se nově načetlo).
- **Doporučení:** A. Pokud ale chceš, aby prázdný řádek bez `#` seznam nepřerušil, je to B — rozhodnutí o kanonu, ne o refaktoringu.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B`

### Skupina 9 — řádek bez ` * ` uvnitř komentáře PageObjectu

- **Formát:** PageObject.
- **Co se mění:** parser takový řádek vždy přeskočil a pokračoval v otevřeném klíči. Starý normalizér na něm klíč `notes:` zavřel a další `•` nepřepsal — parser pak `•` připojil k předchozí poznámce. Teď to není řádek hlavičky a nic nezavírá.
- **Příklad:**

  ```typescript
   * notes:
   *   • Step order is fixed; the review step cannot be skipped.
     wrapped without star
   *   • The wizard shares one URL with its step files.
  ```

  Dřív: `notes = ["Step order is fixed; the review step cannot be skipped. • The wizard shares one URL with its step files."]` (slepené). Teď: dvě poznámky.
- **Proč:** AC 1 (čtení parseru).
- **Pravděpodobnost v praxi:** nízká.
- **Možnosti:**
  - A) přijmout;
  - B) řádek bez ` * ` zavírá klíč pro oba (čtení starého normalizéru) — položky za ním by parser zahodil, bez varování.
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B`

### Skupina 10 — chybějící nebo neuzavřený rámec

- **Formát:** `.feature` hlavička (právě jedna linka `# ===`), PageObject (bez `/*` nebo bez `*/`).
- **Co se mění:** parser z takového souboru nikdy nečetl klíče (u PageObjectu vrací `MISSING_ENTITY_ID`). Starý normalizér přesto přepisoval všechny řádky komentáře. Teď mimo rámec nepřepisuje nic kromě titulku `.feature` hlavičky a rámec hlásí `unterminated_frame` / `no_frame`. `.feature` text úplně **bez** linky se dál normalizuje celý (fragmenty z testů a dokumentace fungují beze změny).
- **Příklad:**

  ```gherkin
  # =====
  # LIVING DOC — US-001 - Sample
  # status: Active
  ```

  Dřív (normalize): titulek přepsán, `status: active`. Teď: titulek přepsán, `status: Active` zůstává.
- **Proč:** AC 1 — normalizér nepřepisuje řádky, které žádný parser nečte.
- **Pravděpodobnost v praxi:** nízká (zapomenutá zavírací linka); dopad jen na text `normalize()`.
- **Možnosti:**
  - A) přijmout;
  - B) neuzavřený rámec sahá do `Feature:` / konce souboru pro oba — parser by začal číst klíče z neuzavřené hlavičky (nová data a nová varování; v PageObjectu by se do hlavičky dostal i TypeScript);
  - C) jen normalizér by přepisoval mimo rámec — porušuje „oba čtou totéž".
- **Doporučení:** A. Neuzavřený rámec je teď nahlášený jako strukturální problém, což je pro kontrolu nad parserem (`D18`) užitečnější než tichý přepis.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B` `[ ] C`

### Skupina 11 — pravidlo 6 běží jako první, na každém řádku s textem

- **Formát:** issue body, HTML markdown, `.feature` hlavička, PageObject (scénáře pravidlo 6 v odsazení nemají).
- **Co se mění:** dřív se pravidlo 6 nedostalo na řádky, které walker zpracoval dřív (titulek, linka `# ===`, hodnota v `## Status`); naopak v PageObjectu přepisovalo i řádek jen z mezer. Teď běží na každém řádku s textem a řádek jen z mezer nechává být ve všech formátech.
- **Příklad:**

  ```gherkin
  # =====
  #<TAB>LIVING DOC — US-001 - S
  #<TAB>=====
  ```

  Dřív: titulek přepsán (5b), tab zůstal; linka beze změny. Teď: navíc tab → mezera v titulku i v lince (změny `whitespace`). Podobně `<NBSP>active` pod `## Status` a ` *<TAB>` v PageObjectu (ten teď zůstane).
- **Proč:** tři fáze — pravidlo 6 musí proběhnout dřív, než rámec ví, který řádek je titulek.
- **Pravděpodobnost v praxi:** velmi nízká; výstup parseru se nemění nikdy.
- **Možnosti:**
  - A) přijmout;
  - B) ve fázi 3 vydat titulek, linky a hodnotu `## Status` v původním odsazení a v PageObjectu znovu přepisovat řádky jen z mezer — asi 10 řádků kódu, bez dopadu na parsery, ale zachovává náhodu, ne pravidlo.
- **Doporučení:** A; B jen pokud chceš, aby se `normalize()` mimo zadané skupiny nezměnil vůbec.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B vrátit`

### Skupina 12 — `notes:` na cross-reference hlavičce PageObjectu

- **Formát:** PageObject, cross-reference hlavička.
- **Co se mění:** `notes:` je na cross-reference hlavičce neznámý klíč (dál `IGNORED_AUTHORED_KEY`). Starý parser jeho položky nesledoval, takže zalomený řádek poznámky ve tvaru `route: /b` přečetl jako klíč a **přepsal skutečný `route`**. Starý normalizér je sledoval. Teď jsou zalomené řádky poznámky jejím textem bez ohledu na tvar hlavičky.
- **Příklad:**

  ```typescript
   * parent-feat: FEAT-042
   * route: /a
   * notes:
   *   - a note that wraps
   *     route: /b
  ```

  Dřív: `route = "/b"`. Teď: `route = "/a"`.
- **Proč:** jediná skupina, kde rámec drží čtení normalizéru — čtení parseru bylo samo chybou (text poznámky rozhodoval o klíči, `#168`).
- **Pravděpodobnost v praxi:** velmi nízká.
- **Možnosti:**
  - A) přijmout;
  - B) sledovat položky `notes:` jen na plné hlavičce — rámec by musel znát tvar hlavičky dřív, než ji orámuje (vrátil by se druhý průchod kvůli `parent-feat:`), a vrátila by se chyba s přepsaným `route`.
- **Doporučení:** A.
- **Rozhodnutí:** `[ ] A přijmout` `[ ] B vrátit`

## 4. Co se dělo během implementace

1. **Kontrola závislostí.** Větev `refactor/183-framing-pass` už existovala a stála na `origin/master` (`216d866`), kde je `P35-UT11` (#182) i `P35-UT5b` (#180) — obě povinné závislosti tedy splněny.
2. **Čtení kódu.** Sedm stavových automatů nad čtyřmi formáty: `_normalize_markdown`, `_normalize_feature_header`, `_normalize_page_object`, `_normalize_scenario_file` a parsery `_split_h2_sections`, `feature_header._parse_keys`, `page_object._parse_keys`. Při čtení se ukázalo, že se normalizér a parser neliší jen ve čtyřech zapsaných chybách, ale v řadě dalších okrajových případů (viz kapitola 7).
3. **Návrh.** Tři fáze; nový modul `framing.py` jako nejnižší vrstva (řádkový model `IndentedLine`, `BulletItemTracker`, role řádků, framery). Kvůli cyklickým importům zůstalo pravidlo 6 a `compute_fence_flags` v `normalize.py` (fáze 1) a framing dostává už připravené řádky.
4. **Měřicí aparát dřív než změna.** Než se sáhlo na kód:
   - snímek starého balíčku do pracovního adresáře (přejmenované importy `old_ldu`),
   - pytest plugin, který zaznamenal **každé** volání `normalize` / `parse_*` z testové sady (234 unikátních vstupů),
   - diferenciální skript: starý vs. nový kód nad těmito vstupy, golden korpusem a náhodně pozměněnými variantami (vložené `AC:` řádky, `•` místo `-`, taby, `*/` v hodnotách, citované titulky…),
   - minimalizátor, který každý rozdíl zmenší na nejmenší vstup se stejným druhem rozdílu.
5. **První implementace.** Framing + přepsaný `normalize.py` + parsery. Spadlo 35 testů — jedna překlepová chyba v `_read_keys` a zastaralé kotvy v dokumentaci. Po opravě všechny testy prošly beze změny.
6. **Diferenciální běh (20 000 mutací)** odhalil, kde nový návrh mění výstup zbytečně, a vedl ke čtyřem opravám návrhu:
   - **titulek bez titulku:** když hlavička titulek nemá, pozičně „titulkem" je jiný řádek (např. `AC:US-001-09 …`) a pravidla 5/5b z něj dělala `AC:US-001 · 09`. Oprava: pravidla 5/5b se na pozičním titulku uplatní, jen když řádek nese `LIVING DOC`;
   - **tab hned za `#`:** pravidlo 6 udělá z `#<tab>- a` řádek `# - a`. Starý normalizér ho četl s odsazením 1, starý parser (který znovu četl normalizovaný text) s odsazením 0 — a stejně ho čte i gramatika kritérií. Oprava: po pravidle 6 se jedna mezera přesune do značky komentáře, takže rámec vidí totéž co všichni ostatní čtenáři;
   - **klíč na zavíracím řádku** (` * route: /setup */`): první verze ho zahodila jako „pravidlo". Oprava: zavírací řádek ukončí rámec, ale co nese před `*/`, se čte jako běžný řádek hlavičky;
   - **hlubší `=====` uvnitř položky klíče** zůstává textem položky (jako ve starém parseru); v bloku kritérií ho ukončí.
7. **Nalezen pád (`D22`).** Hlavička kritéria, pod kterou nic není, shodí `parse_issue_body` i `parse_feature_header` (`ValueError` v `ac_grammar._parse_extensions`). Existuje i na `master`; oprava by měnila výstup, takže je zaparkovaná v `debt.md`.
8. **Testy, dokumentace, dluh.** 32 nových testů v `tests/authoring/test_framing.py`; `docs/authoring/normalisation.md` a `parsers.md` popisují tři fáze; `docs/api.md` uvádí nový modul; `D20` uzavřen v `debt.md`, přidán `D22`.
9. **Druhý běh (40 000 mutací, jiný seed)** našel ještě skupinu 12 (poznámky na cross-reference hlavičce PageObjectu), doplněno do `pr.md`.

## 5. Dopad změn

### 5.1 API knihovny

| Co | Změna |
|---|---|
| `normalize()`, `parse_issue_body()`, `parse_feature_header()`, `parse_page_object()`, `parse_scenarios()`, `parse_acceptance_criteria()`, `extract_living_doc_title()` | signatura beze změny |
| `normalize.normalize_framed()` | **nové** — vrací `(NormalizedSource, Frame)` |
| modul `authoring.framing` | **nový** — `Frame`, `FramedLine`, `Role`, `Section`, `sections()`, `criteria_text()`, `Problem` a druhy problémů `NO_FRAME`, `UNTERMINATED_FRAME`, `KEY_OUTSIDE_FRAME` |
| `identity.is_living_doc_title` | **odstraněno** (nebylo v `docs/api.md` jako veřejné) |
| interní funkce (`po_section_break`, `_normalize_*`, `_parse_keys`, `_split_h2_sections`, `_extract_header_block`, …) | odstraněny; seznam s čísly řádků je v `pr.md` |
| `IndentedLine`, `indented`, `BulletItemTracker` | přesunuty z `normalize.py` do `framing.py` beze změny chování |
| kontrakty, JSON schémata, kódy varování (`ALL_CODES`) | **beze změny** |
| verze | zůstává `0.5.0` (`DEC-41`); tag `v0.5.0` řeže vlastník po merge |

### 5.2 Navazující komponenty (`collector-gh`, `collector-ad`, `toolkit`)

- Porovnávají své parsery s golden fixtures — ty dávají **identický** výstup. Žádná akce není potřeba.
- Na nekanonickém vstupu mohou vidět rozdíly z kapitoly 7. Nejpravděpodobnější v praxi: `D20` (už žádné fantomové kritérium) a poznámky / klíče s `*/` v PageObjectu.
- Pokud chtějí strukturální diagnostiku (žádný rámec, neuzavřený rámec, klíč mimo rámec), je dostupná přes `normalize_framed(...)[1].problems`. Parsery ji **nevydávají jako varování** — to by byla změna výstupu i kontraktu.

### 5.3 Autoři living-doc vstupů

- Odsazení dál znamená totéž (`DEC-44`, `DEC-45` platí beze změny).
- Nově platí: text řádku nikdy nerozhoduje o hranici. Poznámka smí citovat celý titulek, `status:`, `parent-feat:`, `AC:…` nebo `*/` a pořád je to jen text poznámky.
- Titulek banneru musí být řádek hned za otevírací linkou (`# ===` / `/* ===`). Jinde ho parser nenajde.

### 5.4 Velikost kódu

| Soubor | Dřív | Teď |
|---|---|---|
| `normalize.py` | 734 | 592 |
| `feature_header.py` | 212 | 138 |
| `page_object.py` | 276 | 211 |
| `issue_body.py` | 383 | 368 |
| `scenario.py` | 114 | 107 |
| `identity.py` | 70 | 61 |
| `framing.py` (nový) | — | 435 |

Čistě asi +120 řádků. Přínos není v počtu řádků (zadání to tak samo očekává), ale v tom, že hranice se rozhoduje na jednom místě a celá třída chyb přestala být možná.

## 6. Staré vs. nové řešení podrobně

### 6.1 Staré řešení: „normalizuj, pak znovu parsuj"

```
text ──► normalize()                         ──► text ──► parser
         každý formát vlastní stavový automat         parser znovu hledá hranice
         (current_section, seen_title,                (vlastní regexy klíčů, vlastní
          in_bullet_key, header_closed, …)             hledání banneru, vlastní konec)
```

| Formát | Jak hranice hledal normalizér | Jak je hledal parser |
|---|---|---|
| issue body | `current_section` = slug **jakéhokoli** nadpisu (`#`…`######`); `in_ac_block` od `AC:` do dalšího nadpisu | jen nadpisy přesně `##` mimo fence (`_split_h2_sections`); kritéria hledá gramatika v **celém** textu |
| `.feature` hlavička | všechny řádky začínající `#` v celém souboru; titulek = první řádek obsahující podřetězec `LIVING DOC`; klíče dvěma regexy (`key:` / `key: value`) | blok mezi první a poslední `# ===` nad `Feature:`; titulek = první `LIVING DOC — …` v bloku, **jinak kdekoli v souboru**; klíče regexem ze všech známých klíčů; od prvního `AC:` až po `====` žádné klíče |
| PageObject | všechny řádky ` * ` v souboru; `header_closed` po prvním výskytu `*/` **kdekoli v řádku** (i uvnitř hodnoty); konec klíče přes `po_section_break` včetně textového testu na titulek | první `/* … */`, konec na řádku **končícím** `*/`; klíče regexem ze známých klíčů; druhý „probe" průchod kvůli `parent-feat:` |
| scénáře | jen řádky `# AC:` | `Feature:` / `Background:` / `Scenario:` / tagy |

Čtyři zaznamenané chyby z této architektury:

1. `is_living_doc_title` bez hlídání otevřené položky → poznámka citující titulek zavřela seznam a **všechny poznámky zmizely bez varování** (opraveno v `#176` záplatou).
2. `D20` — `AC:` řádek zalomený v položce issue body se stal kritériem, které nikdo nenapsal.
3. Nezakotvené `"*/" in raw` v normalizéru vs. zakotvené `.*\*/\s*$` v parseru.
4. Podřetězec `"LIVING DOC" in content` — stejná chyba jako 1 v jiné variantě.

### 6.2 Nové řešení: tři fáze

```
text ──► fáze 1: pravidlo 6       ──► fáze 2: framing        ──► fáze 3: ostatní pravidla ──► Frame
         (odsazení na mezery,          (kam patří každý řádek)     podle sekce řádku             │
          řádek po řádku)                                                                      ├─► normalize(): text + změny
                                                                                               └─► parser: sections(frame)
```

1. **Fáze 1 — pravidlo 6** (`normalize.py::_prepare`): oddělí značku komentáře (`# `, ` * `), převede taby / NBSP v odsazení na mezery. Netýká se fence bloků, řádků, které nejsou komentářem formátu (Gherkin, TypeScript), a řádků jen z mezer.
2. **Fáze 2 — rámec** (`framing.py`): pro každý řádek určí
   - `role`: `OUTSIDE`, `CODE`, `BLANK`, `RULE`, `TITLE`, `HEADING`, `SUBHEADING`, `KEY`, `TAG`, `COMMENT`, `TEXT`,
   - `section`: slug nadpisu `##`, název klíče, nebo klíčové slovo Gherkinu,
   - `item_text`: řádek je hlouběji než značka otevřené položky,
   - `criterion`: řádek patří do bloku kritéria,
   - a sesbírá strukturální problémy (`Problem`).
3. **Fáze 3** (`normalize.py::_rewrite_*`): pravidla 1, 2, 3, 4, 5, 5b, 7 podle role a sekce — žádné vlastní příznaky. Parsery čtou `sections(frame)`, `frame.title` a `criteria_text(frame, …)`.

Ukázka, co rámec obsahuje pro `.feature` hlavičku (výstup nové verze):

```
řádek                                         role     section              item crit
'# ====='                                     RULE     None                  0    0
'# LIVING DOC — US-001 · Sample'              TITLE    None                  0    0   ← přepsáno z „US-001 - Sample"
'# ====='                                     RULE     None                  0    0
'# status: active'                            KEY      status                0    0   ← „Active" → „active"
'# business_value:'                           KEY      business_value        0    0
'#   - Old accounts carry'                    TEXT     business_value        0    0   ← „•" → „-"
'#     status: deprecated until verified.'    TEXT     business_value        1    0   ← text položky, žádný klíč
'#'                                           BLANK    None                  0    0
'# acceptance_criteria:'                      KEY      acceptance_criteria   0    0
'#   AC:US-001-01 (v1.0.0 - active)'          TEXT     None                  0    1   ← „(v1.0 – Active)" přepsáno
'#     - desc'                                TEXT     None                  0    1
'# ====='                                     RULE     None                  0    0
'Feature: Sample'                             OUTSIDE  None                  0    0
```

A pro issue body (`D20`):

```
'## Business Value'                    HEADING  business_value       item=0 crit=0
'- Parent.'                            TEXT     business_value       item=0 crit=0
'  AC:US-001-01 (v1.0.0 - active)'     TEXT     business_value       item=1 crit=0   ← text položky → gramatika ho nevidí
'  - desc here.'                       TEXT     business_value       item=1 crit=0
'## Acceptance Criteria'               HEADING  acceptance_criteria  item=0 crit=0
'### AC:US-001-02 (v1.0.0 - active)'   TEXT     acceptance_criteria  item=0 crit=1   ← skutečné kritérium
'- d'                                  TEXT     acceptance_criteria  item=0 crit=1
```

### 6.3 Pravidla rámce podle formátu

| Rozhodnutí | Issue body / HTML markdown | `.feature` hlavička | PageObject | Scénáře |
|---|---|---|---|---|
| začátek / konec rámce | celý text | první až poslední `# ===` nad `Feature:`; bez linky = všechny `#` řádky (fragment) | první `/*` až první řádek **končící** `*/` | celý text |
| titulek | — | první neprázdný řádek po otevírací lince | první neprázdný řádek po `/*` | — |
| sekce | jen `##` mimo fence; `###` a jiné nadpisy jsou obsah sekce | řádek `klíč:` (tvar `[a-zA-Z_][a-zA-Z0-9_]*:`) | řádek `klíč:` (tvar `[a-zA-Z][a-zA-Z0-9_-]*\s*:`) | `Feature:`, `Background:`, `Scenario:` / `Scenario Outline:` |
| konec sekce | další `##` | prázdný řádek, linka `===`, `AC:` hlavička, další klíč | prázdný řádek, `===`, další klíč, zavírací řádek | další klíčové slovo |
| text položky | v odrážkové sekci, mimo blok kritéria; **prázdný řádek položku nezavírá** (Markdown) | v odrážkovém klíči i v bloku kritéria; prázdný řádek položku zavírá | v klíči `notes:`, na plné i cross-reference hlavičce | — |
| blok kritéria | od `AC:` hlavičky do dalšího nadpisu | od `AC:` hlavičky do další linky `===`; uvnitř se nečtou klíče | — | — |
| strukturální problémy | žádné | `no_frame`, `unterminated_frame`, `key_outside_frame` | `no_frame`, `unterminated_frame` | žádné |

## 7. Příklady pro všechny typy hlaviček

Formát příkladů: **vstup**, pak **dřív** a **teď**. Kde je napsáno „beze změny", výstupy jsou totožné. Číslo skupiny odpovídá `pr.md`.

### 7.1 Issue body (GitHub)

**Kanonický vstup — beze změny**

```markdown
## Description

As a customer, I can sign in.

## Status

active

## Business Value

- Registered customers reach their account.
  - Returning users convert.

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.
```

Výsledek (dřív i teď): `business_value = ["Registered customers reach their account.\n  - Returning users convert."]`, jedno kritérium `US-001-01`, stav `active`, žádné varování.

**Skupina 1 — `D20`: `AC:` řádek zalomený v položce** (přesný vstup z `debt.md`)

```markdown
## Description

d

## Status

active

## Business Value

- Parent.
  AC:US-001-01 (v1.0.0 - active)
  - desc here.
```

- **Dřív:** `business_value = ["Parent. AC:US-001-01 (v1.0.0 - active)\n  - desc here."]` **a navíc** kritérium `US-001-01` s popisem `desc here.` — nikdo ho nenapsal, bez varování.
- **Teď:** stejné `business_value`, **žádné kritérium**, žádné varování.

**Skupina 1 — `D20` přes prázdný řádek** (Markdown položku prázdným řádkem nezavírá)

```markdown
## Business Value

- Parent.

  AC:US-001-01 (v1.0.0 - active)
  - desc here.
```

- **Dřív:** fantomové kritérium `US-001-01`.
- **Teď:** žádné kritérium.

**Skupina 1 — `D20` jako poslední řádek těla**

```markdown
## Business Value

- Parent.
  AC:US-001-01 (v1.0.0 - active)
```

- **Dřív:** `ValueError: zip() argument 2 is longer than argument 1` (pád, viz `D22`).
- **Teď:** `business_value = ["Parent. AC:US-001-01 (v1.0.0 - active)"]`, žádné kritérium.

**Skupina 1 — `D20` v normalizéru**

```markdown
## Business Value

- Parent.
  AC:US-001-01 (V1.0 – Active) — inline
```

- **Dřív:** řádek přepsán na `  AC:US-001-01 (v1.0.0 - active)` a navíc vložen nový řádek `- inline` (pravidla 2, 3, 4, 7).
- **Teď:** řádek zůstává, jak ho autor napsal — je to text položky; žádná změna.

**`AC:` hlavička na úrovni položky — beze změny** (není to `D20`; viz [otevřené body](#8-otevřené-body))

```markdown
## Business Value

- Parent.
AC:US-001-01 (v1.0.0 - active)
- desc
```

Dřív i teď: `business_value = ["Parent. AC:US-001-01 (v1.0.0 - active)", "desc"]` **a** kritérium `US-001-01` s popisem `desc`.

**Skupina 4 — nadpis `###` uvnitř `## Business Value`**

```markdown
## Business Value

### Detail

• Fewer support calls.
```

- **Dřív:** normalizér na `###` přepnul sekci, `•` nepřepsal; parser položku nenašel → `business_value = []`, `UNPARSED_BULLET_LINE` s textem `### Detail • Fewer support calls.`
- **Teď:** `•` → `-`; `business_value = ["Fewer support calls."]`, `UNPARSED_BULLET_LINE` jen pro `### Detail`.

**Skupina 4 — `### Status` mimo `## Status`**

```markdown
## Description

foo

### Status

Active
```

- **Dřív:** `narrative = "foo ### Status active"` (normalizér `Active` zmenšil, protože `### Status` považoval za sekci stavu).
- **Teď:** `narrative = "foo ### Status Active"` — `###` sekci neotevírá, pravidlo 3 se neuplatní.

**Skupina 11 — NBSP v hodnotě `## Status`**

```markdown
## Status

<NBSP>active
```

- **Dřív:** řádek beze změny (pravidlo 6 se v sekci stavu neuplatnilo).
- **Teď:** NBSP → mezera, zapsáno jako změna `whitespace`. Výsledný stav je v obou případech `active`.

### 7.2 HTML markdown (Azure DevOps)

`HTML_MARKDOWN` sdílí rámec i pravidla s issue body, takže platí vše z 6.1. Příklad `D20` po převodu z HTML:

```markdown
## Business Value

- Parent.
  AC:US-001-01 (V1.0 – Active)
```

- **Dřív:** řádek přepsán na `  AC:US-001-01 (v1.0.0 - active)` (pravidla 2, 3, 4).
- **Teď:** beze změny — text položky.

### 7.3 `.feature` hlavička (User Story a Functionality)

**Kanonický vstup User Story — beze změny**

```gherkin
# =====
# LIVING DOC — US-001 · Customer Login
# =====
# status:          active
# business_value:
#   - Registered customers reach their account, so returning users
#     convert without friction.
# notes:
#   - See the LIVING DOC — FEAT-002 · Breached Password Check banner.
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - Valid credentials land on the dashboard.
#     preconditions:
#       - An account exists.
# =====

@US_ID:US-001
Feature: Customer Login
```

Dřív i teď: `US-001`, `active`, jedna položka `business_value`, poznámka citující cizí titulek zůstává poznámkou, kritérium s `preconditions = ["An account exists."]`, žádné varování.

**Kanonický vstup Functionality — beze změny**

```gherkin
# =====
# LIVING DOC — FUNC-001 · Login Page - Validate Password Strength
# =====
# status:    active
# parent:    FEAT-001
# func_type: field_validation
# rationale:
#   - Checked client-side for immediate feedback.
# =====

Feature: Validate Password Strength
```

Dřív i teď: `parent = "FEAT-001"`, `func_type = "field_validation"`, `rationale = "Checked client-side for immediate feedback."`.

**Skupina 3 — hlavička bez titulku, položka cituje tvar titulku**

```gherkin
# =====
# =====
# business_value:
#   - LIVING DOC — US-009 · Quoted
# =====

Feature: S
```

- **Dřív:** entita `US-009` s titulkem `US-009 · Quoted` — **id vzaté z textu položky**.
- **Teď:** `None` + `MISSING_ENTITY_ID` (titulek za otevírací linkou chybí).

**Skupina 3 — titulek nad linkami**

```gherkin
# LIVING DOC — US-001 · Sample
# =====
# status: active
# =====

Feature: S
```

- **Dřív:** entita `US-001`, stav `active` (titulek nalezen „kdekoli v souboru").
- **Teď:** `MISSING_ENTITY_ID` — titulek musí být řádek hned za otevírací linkou.

**Skupina 3 — fragment bez linky (jen normalizace)**

```gherkin
# LIVING DOC — US-001 - Customer Login
```

- **Dřív:** přepsáno na `# LIVING DOC — US-001 · Customer Login` (pravidlo 5b).
- **Teď:** beze změny — bez linky nemá hlavička titulek.

**Skupina 5 — `status:` uvnitř bloku kritéria**

```gherkin
# =====
# LIVING DOC — US-001 · Sample
# =====
# acceptance_criteria:
#   AC:US-001-01 (v1.0.0 - active)
#     - desc
#   status: Deprecated
# =====
```

- **Dřív (normalize):** `#   status: deprecated` — normalizér řádek považoval za klíč, ač ho parser nikdy jako klíč nečetl.
- **Teď:** `#   status: Deprecated` — blok kritéria trvá do další linky, klíče se v něm nečtou. Výstup parseru (stav, kritérium, varování `MISINDENTED_LINE`) je v obou verzích stejný.

**Skupina 6 — odrážkový klíč s textem na vlastním řádku**

```gherkin
# =====
# LIVING DOC — US-001 · Sample
# =====
# status: active
# preconditions: The customer is signed in.
#   + The account is active.
# =====
```

- **Dřív:** normalizér `preconditions: …` nepovažoval za seznam, `+` nepřepsal → `preconditions = []`, `UNPARSED_BULLET_LINE`.
- **Teď:** `+` → `-` → `preconditions = ["The account is active."]`; `UNPARSED_BULLET_LINE` zůstává pro větu na řádku klíče.

**Skupina 7 — tab hned za `#`**

```gherkin
# =====
# LIVING DOC — US-001 · Sample
# =====
# status: active
# business_value:
#   - Old accounts carry
#<TAB>  status: Deprecated
# =====
```

- **Dřív:** normalizér četl řádek jako text položky (odsazení 3) a nezměnil ho; parser po normalizaci četl `#   status: Deprecated` (odsazení 2) jako klíč → `MALFORMED_STATUS`, stav `None`.
- **Teď:** oba čtou odsazení 2 → klíč `status`, normalizér ho zmenší → stav `deprecated`, žádné varování.

Vnořená položka s tabem za `#` (`#<TAB>  - Returning users convert.` a pod ní `#   - Support calls drop.`) dává dřív i teď dvě položky — tady se nic nemění.

**Skupina 8 — prázdný řádek bez `#` uvnitř hlavičky (jen normalizace)**

```gherkin
# =====
# LIVING DOC — US-001 · Sample
# =====
# business_value:
#   - a

#   • b
# =====
```

- **Dřív:** normalizér prázdný řádek ignoroval a `•` přepsal na `-`; parser ale na prázdném řádku klíč zavřel a `b` nečetl.
- **Teď:** prázdný řádek zavírá klíč pro oba; `•` zůstává. Výstup parseru je stejný.

**Skupina 10 — jediná linka `# =====` (neuzavřený rámec)**

```gherkin
# =====
# LIVING DOC — US-001 - Sample
# status: Active
```

- **Dřív (normalize):** titulek přepsán, `status: Active` → `status: active`.
- **Teď:** titulek přepsán, `status: Active` zůstává — řádek je mimo rámec a parser ho nikdy nečetl. Rámec hlásí `unterminated_frame`.

**Fragment bez linky — beze změny** (to používají testovací případy normalizace)

```gherkin
# status:          In Review
# rationale:
#   * Checked client-side.
```

Dřív i teď: `# status:          in_review` a `#   - Checked client-side.`.

**Skupina 11 — tab v titulku a v lince**

```gherkin
# =====
#<TAB>LIVING DOC — US-001 - S
#<TAB>=====
```

- **Dřív:** titulek přepsán, tab zůstal; linka beze změny.
- **Teď:** tab → mezera v titulku i v lince (pravidlo 6 běží na každém řádku s textem jako první).

### 7.4 PageObject — plná hlavička

**Kanonický vstup — beze změny**

```typescript
/* =====
 * LIVING DOC — FEAT-001 · Login Page
 * =====
 * surface_type:          UI
 * route:                 /login
 * owners:                Identity Team
 * purpose:               The screen where a customer signs in.
 * user_stories:          US-001
 * functionalities:       FUNC-001, FUNC-002
 * page-object:           LoginPage.ts
 * notes:
 *   - Status: deprecated? No - this note is free text.
 * ===== */

export class LoginPage {
  /**
   * route: /not-a-header-key
   */
}
```

Dřív i teď: entita `FEAT-001`, `route = "/login"`, poznámka zůstává volným textem, JSDoc `route:` se nečte.

Následující příklady vycházejí z této hlavičky:

```typescript
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard
 * =============================================================================
 * surface_type:          UI
 * purpose:               Multi-step wizard for creating a new account.
 * page-object:           AccountSetupWizardPage.ts
 * notes:
 *   • Step order is fixed; the review step cannot be skipped.
 *   • The wizard shares one URL with its step files.
 * ============================================================================= */
```

**Skupina 2 — `*/` uvnitř hodnoty**

```typescript
 * purpose:               Multi-step wizard for creating a new account (see /* legacy */ wizard).
```

- **Dřív:** normalizér na prvním `*/` „zavřel" hlavičku → `•` nepřepsány → `notes = []`, `UNPARSED_BULLET_LINE` — **obě poznámky ztraceny**.
- **Teď:** `*/` uprostřed řádku hlavičku nezavírá → `•` → `-` → obě poznámky, žádné varování.

**Skupina 2 — odsazené holé zavření**

```typescript
 *   • The wizard shares one URL with its step files.
 *   */
```

- **Dřív:** `notes[1] = "The wizard shares one URL with its step files. */"` — zavírací značka se stala textem poznámky.
- **Teď:** `notes[1] = "The wizard shares one URL with its step files."`

**Holé ` */` a klíč na zavíracím řádku — beze změny**

```typescript
 *   • The wizard shares one URL with its step files.
 */
```

Dřív i teď obě poznámky bez varování.

```typescript
 *   • The wizard shares one URL with its step files.
 * route: /setup */
```

Dřív i teď `route = "/setup */"` — viz [otevřené body](#8-otevřené-body).

**Skupina 3 — banner bez titulku, poznámka cituje cizí titulek**

```typescript
/* =============================================================================
 * =============================================================================
 * surface_type:          UI
 * purpose:               Multi-step wizard for creating a new account.
 * page-object:           AccountSetupWizardPage.ts
 * notes:
 *   - See the LIVING DOC — FEAT-002 · Breached Password Check banner.
 *   • The wizard shares one URL with its step files.
 * ============================================================================= */
```

- **Dřív:** vznikla entita **`FEAT-002`** s titulkem `FEAT-002 · Breached Password Check banner.` a poznámky se slepily do jedné — data se zapsala na cizí Feature.
- **Teď:** `None` + `MISSING_ENTITY_ID`.

Stejná poznámka v hlavičce **s** titulkem: dřív i teď entita `FEAT-042`, dvě poznámky.

**Skupina 3 — řádek s tvarem titulku za klíči**

```typescript
 * page-object:           AccountSetupWizardPage.ts
 * LIVING DOC — FEAT-002 · Quoted
```

- **Dřív:** řádek ukončil klíč (textový test na titulek) → `page_object = "AccountSetupWizardPage.ts"`.
- **Teď:** text řádku o hranici nerozhoduje → řádek pokračuje hodnotou: `page_object = "AccountSetupWizardPage.ts LIVING DOC — FEAT-002 · Quoted"`.

**Skupina 9 — řádek bez ` * ` uvnitř komentáře**

```typescript
 *   • Step order is fixed; the review step cannot be skipped.
   wrapped without star
 *   • The wizard shares one URL with its step files.
```

- **Dřív:** normalizér na tom řádku `notes:` zavřel a druhé `•` nepřepsal; parser řádek přeskočil a `•` připojil k první poznámce → jedna slepená poznámka.
- **Teď:** řádek bez ` * ` není řádek hlavičky a nic nezavírá → dvě poznámky.

**Skupina 10 — komentář bez `*/` (jen normalizace)**

```typescript
/* ===
 * LIVING DOC — FEAT-001: Login
 * notes:
 *   • a
```

- **Dřív:** titulek → `FEAT-001 · Login`, `•` → `-`.
- **Teď:** beze změny; rámec hlásí `unterminated_frame`. Parser dřív i teď vrací `MISSING_ENTITY_ID`.

**Skupina 11 — prázdný řádek hlavičky s tabem**

```typescript
 *<TAB>
```

- **Dřív:** přepsán na ` * ` (změna `whitespace`).
- **Teď:** řádek jen z mezer zůstává, jak je, ve všech formátech.

### 7.5 PageObject — cross-reference hlavička

**Kanonický vstup — beze změny**

```typescript
/* =====
 * LIVING DOC — FEAT-042 · Account Setup Wizard  [cross-reference]
 * =====
 * This file implements Step 1 (Profile).
 *
 * parent-feat:     FEAT-042
 * route:           /app/accounts/setup
 * owners:          Platform Team
 * functionalities: FUNC-005
 * purpose:         Step 1 (Profile) - user profile fields.
 * page-object:     AccountSetupWizardProfilePage.ts
 * ===== */
```

Dřív i teď: `parent_feat = "FEAT-042"`, nesamostatná stránka, úvodní prozaické řádky se ignorují, žádné varování.

**Skupina 12 — zalomená poznámka na cross-reference hlavičce**

```typescript
/* ===
 * LIVING DOC — FEAT-042 · W [cross-reference]
 * ===
 * parent-feat: FEAT-042
 * route: /a
 * notes:
 *   - a note that wraps
 *     route: /b
 * === */
```

- **Dřív:** `notes:` je na cross-reference hlavičce neznámý klíč, parser jeho položky nesledoval a zalomený řádek `route: /b` přečetl jako klíč → **`route = "/b"`** (přepsal skutečnou hodnotu).
- **Teď:** `route = "/a"`; `notes:` dál hlásí `IGNORED_AUTHORED_KEY`. Tady rámec drží čtení starého normalizéru, protože čtení parseru byla ta chyba.

### 7.6 Soubor scénářů (Gherkin) — beze změny

```gherkin
@US_ID:US-001
Feature: Login

  # AC:US-001-01 (v1.0 – Active) — valid credentials
  @AC:US-001-01
  Scenario: Sign in
    Given x

  @AC:US-001-02
  Rule: r
  Scenario: Other
```

Dřív i teď: scénář `Sign in` s odkazem na `US-001-01`; scénář `Other` bez odkazu (tag `@AC:US-001-02` zahodil řádek `Rule:`). Normalizace: `# AC:US-001-01 (v1.0.0 - active) - valid credentials`. Rozdíl je jen vnitřní: parser čte role z rámce (`HEADING` se sekcí `Feature` / `Background` / `Scenario`, `TAG`, `COMMENT`) místo vlastních regexů.

### 7.7 Strukturální problémy rámce

| Vstup | Formát | `frame.problems` |
|---|---|---|
| `# status: active` | `.feature` | `[Problem("no_frame", 1)]` |
| `\n# ===\n# LIVING DOC — US-1 · S` | `.feature` | `[Problem("unterminated_frame", 2)]` |
| `export class P {}` | PageObject | `[Problem("no_frame", 1)]` |
| `// x\n/* ===\n * LIVING DOC — FEAT-1 · S` | PageObject | `[Problem("unterminated_frame", 2)]` |
| `# ===\n# LIVING DOC — US-1 · S\n# ===\n# status: active\n\nFeature: S` | `.feature` | `[Problem("key_outside_frame", 4)]` |
| golden korpus (všechny tři formáty) | — | `[]` |

Parsery tyto problémy **nevydávají jako varování** — jsou připravené pro kontrolu nad parserem (`D18`, `D21`).

## 8. Otevřené body

| # | Bod | Kdo / kdy | Kde |
|---|---|---|---|
| 1 | **Rozhodnout o skupinách 3–12** (přijmout, nebo vrátit konkrétní skupinu — viz [kapitola 3](#3-rozhodnutí-po-skupinách)). | vlastník, před commitem | `pr.md` § Intended output changes |
| 2 | **Commit a PR** — nic není commitnuto ani pushnuto. Připravená commit message je v `../living-doc/specs/liv-doc-spec/issues/P35-UT10-commit-message.txt`; postup krok za krokem je v `OPEN_POINTS.md` vedle tohoto průvodce. `pr.md` je neverzovaný soubor v kořeni repa a nemá se commitovat. | vlastník | větev `refactor/183-framing-pass` |
| 3 | **Tag `v0.5.0`** po merge (tento úkol ho přebírá od `P35-UT5b`); další je `P35-CGH1b1`. | vlastník, po merge | — |
| 4 | **`D22` — pád na prázdném bloku kritéria.** `### AC:… ` bez řádku pod sebou shodí `parse_issue_body` / `parse_feature_header` (`ValueError`), i na `master`. Oprava je jednořádková v `ac_grammar._parse_extensions`, ale mění výstup. | nový úkol, nejpozději `P35-CGH1b2` | `debt.md` řádek `D22` |
| 5 | **`D19` — tvrzení „one-site change" platí jen částečně.** Vnoření v issue body se teď čte na dvou místech: `framing.py::frame_issue_body` (co je text položky) a `issue_body.py::_read_bullets` (jak se text skládá). Normalizér ho už nenese. Řádek `D19` jsem neupravoval. | vlastník při rozhodnutí `D19` | `debt.md` řádek `D19` |
| 6 | **`AC:` na úrovni položky v odrážkovém poli** (příklad v 6.1) je dál zároveň textem položky **i** kritériem. `D20` se týká jen zalomeného (hlubšího) řádku, takže to zůstalo beze změny. Bratranec `D20` — stojí za rozhodnutí, zda zapsat do `debt.md`. | vlastník | — |
| 7 | **Klíč na zavíracím řádku si nechává `*/` v hodnotě** (`route = "/setup */"`). Beze změny proti `master`; správnější by bylo `*/` odříznout, ale to je změna výstupu. | vlastník | — |
| 8 | **Zastaralý docstring v existujícím testu** `tests/authoring/test_notes.py:667` jmenuje smazané `po_section_break`. Neupraveno, protože existující testy měly zůstat beze změny. | drobnost, kdykoli | — |
| 9 | **Strukturální problémy nikdo nekonzumuje.** `Frame.problems` existují a jsou otestované, ale čeká se na kontrolu nad parserem. | `D18` / `D21` | — |
| 10 | **`debt.md` je jen lokálně** — `specs/` je v `living-doc` gitignorovaný. Ostatní soubory ve `specs/`, které zmiňují `D20` (tasklist, issue drafty), jsem neupravoval. | vlastník | `specs/liv-doc-spec/` |
| 11 | **`.claude/settings.json` je změněný** — jsou to povolení, která jsi v této session odklikl, ne moje úprava. Do commitu nepatří. | vlastník | `living-doc-utilities/.claude/settings.json` |
| 12 | **Diferenciální aparát** (`differential.py`, `minimize.py`, `examples.py`, snímek staré verze `old_ldu`) je zkopírovaný do `../living-doc/specs/liv-doc-spec/issues/P35-UT10-differential/`; spouští se odtamtud. Po vrácení kterékoli skupiny ho spusť znovu. | vlastník | `specs/liv-doc-spec/issues/P35-UT10-differential/` |
| 13 | **Prázdný Claude Docs dokument** „Průvodce migrací: framing pass (P35-UT10)" vznikl omylem, než jsi napsal, že chceš lokální soubor. Je prázdný a soukromý; smažu ho, když řekneš. | vlastník | claude.ai |

## 9. Jak změnu ověřit

```shell
cd living-doc-utilities
git switch refactor/183-framing-pass
make qa                                          # celý gate, jako v CI
python3 -m pytest -q tests/authoring/test_framing.py   # 32 nových testů
python3 -m pytest -q tests/authoring/golden/     # golden korpus na b28820e
```

Přesný vstup z `D20`:

```shell
python3 -c 'from living_doc_utilities.authoring.issue_body import parse_issue_body as p
e, w = p("## Description\n\nd\n\n## Status\n\nactive\n\n## Business Value\n\n- Parent.\n  AC:US-001-01 (v1.0.0 - active)\n  - desc here.\n", "US-001 · S", "DocumentedUserStory")
print(e.business_value, e.acceptance_criteria, w)'
# ['Parent. AC:US-001-01 (v1.0.0 - active)\n  - desc here.'] [] []
```

Jak vypadá rámec pro libovolný vstup:

```shell
python3 -c 'from living_doc_utilities.authoring.normalize import normalize_framed, SourceFormat
_, f = normalize_framed(open("LoginPage.ts").read(), SourceFormat.PAGE_OBJECT, "DocumentedFeature")
for l in f.lines: print(repr(l.rendered), l.role.name, l.section, l.item_text, l.criterion)
print(f.problems)'
```
