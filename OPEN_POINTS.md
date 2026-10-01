# Otevřené body — P35-UT10 (framing pass, issue #183)

Stav k 2026-10-01, 22:05.

> **Aktualizace 22:05:** commit `1230899` („#183: one framing pass decides every boundary before parsing") je hotový a **pushnutý** na `origin/refactor/183-framing-pass`. Kroky 5 (commit) a půlka kroku 6 (push) níže jsou tím splněné; PR zatím otevřený není.
> Commit obsahuje záměrně i `OPEN_POINTS.md`, `P35-UT10-migration-guide-cs.md` a `pr.md`, aby byly k dispozici na jiném počítači. Před merge je odstranit (bod **O12**).

## Kde co je

| Co | Kde |
|---|---|
| kód | větev `refactor/183-framing-pass`, commit `1230899` na `216d866`, pushnuto na `origin` |
| průvodce (česky, se všemi skupinami a příklady) | `P35-UT10-migration-guide-cs.md` v kořeni tohoto repa (v commitu `1230899`) |
| záloha (patch commitu + archiv souborů) | `../living-doc/specs/liv-doc-spec/issues/P35-UT10-backup-2026-10-01/` |
| commit message | `../living-doc/specs/liv-doc-spec/issues/P35-UT10-commit-message.txt` |
| PR popis | `pr.md` v kořeni tohoto repa (neverzovaný) |
| dluh | `../living-doc/specs/liv-doc-spec/debt.md` — `D20` smazán + poznámka *Closed 2026-10-01*, nový řádek `D22` |
| diferenciální aparát (starý vs. nový kód) | `../living-doc/specs/liv-doc-spec/issues/P35-UT10-differential/` |

Složka `living-doc/specs/` je gitignorovaná — všechno v ní je jen lokálně.

Změněné soubory v tomto repu:

- upravené: `living_doc_utilities/authoring/{__init__,ac_grammar,feature_header,identity,issue_body,normalize,page_object,scenario}.py`, `docs/api.md`, `docs/authoring.md`, `docs/authoring/normalisation.md`, `docs/authoring/parsers.md`
- nové: `living_doc_utilities/authoring/framing.py`, `tests/authoring/test_framing.py`
- **nepatří do commitu:** `pr.md`, `OPEN_POINTS.md`, `P35-UT10-migration-guide-cs.md`, `.claude/settings.json` (povolení odkliknutá během session)

## Co je hotové

- [x] framing pass (`framing.py`) pro všechny čtyři formáty; normalizér i parsery čtou jeden rámec
- [x] `D20` opraven a otestován na přesném vstupu z `debt.md`
- [x] uzavření komentáře `*/` rozpoznáno na jednom místě
- [x] titulek podle pozice; `is_living_doc_title` a guard z `#176` smazány
- [x] žádný regex přes všechny klíče v hlavičkových parserech
- [x] 938 existujících testů beze změny + 32 nových; golden korpus na `b28820e` beze změny
- [x] dokumentace (`normalisation.md`, `parsers.md`, `authoring.md`, `api.md`)
- [x] `make qa` zelené (Pylint 9.93 / 9.94, mypy, deptry, pokrytí 98,5 %)
- [x] `pr.md`, commit message, průvodce, `debt.md`

## Zítra, v tomto pořadí

### 1. Rozhodnout skupiny 3–12

Průvodce, **kapitola 3 „Rozhodnutí po skupinách"**: ke každé skupině příklad dřív/teď, možnosti a zaškrtávátko. Moje doporučení je u všech „A — přijmout".

| # | Skupina | Doporučení | Lze vrátit? |
|---|---|---|---|
| 3 | titulek podle pozice | přijmout | ne (AC 2) |
| 4 | v issue body otevírá sekci jen `##` | přijmout | ne bez porušení AC 1 |
| 5 | blok kritéria v `.feature` trvá do další linky | přijmout | ne bez porušení AC 1 |
| 6 | odrážkový klíč s textem na vlastním řádku | přijmout | ne bez porušení AC 1 |
| 7 | tab hned za `#` / ` * ` | přijmout | ne bez porušení AC 1 |
| 8 | prázdný řádek bez `#` v `.feature` hlavičce | přijmout | jen výměnou |
| 9 | řádek bez ` * ` v komentáři PageObjectu | přijmout | jen výměnou |
| 10 | chybějící / neuzavřený rámec | přijmout | částečně |
| 11 | pravidlo 6 jako první fáze | přijmout | ano, levně (~10 řádků) |
| 12 | `notes:` na cross-reference hlavičce | přijmout | ne bez návratu chyby |

### 2. Když se některá skupina vrací

1. Úprava v `framing.py` (rámec) nebo v `normalize.py` (fáze 3) — kde přesně, píše průvodce u dané skupiny.
2. Test do `tests/authoring/test_framing.py`.
3. Ověřit:

   ```shell
   make qa
   cd ../living-doc/specs/liv-doc-spec/issues/P35-UT10-differential
   python3 differential.py --base-only --show 0     # musí být všude 0
   python3 differential.py --mutations 20000 --show 0
   python3 minimize.py page_object 20               # minimální rozdíly pro daný parser
   ```

4. Opravit seznam skupin v `pr.md` (§ Intended output changes), v průvodci a případně v commit message.

### 3. Doplnit testy pro skupiny 8–12 (pokud je přijmeš)

`test_framing.py` pokrývá skupiny 1–7. Skupiny 8–12 jsou ověřené jen diferenciálním během. Asi pět krátkých testů, vstupy jsou v průvodci (kapitola 3) i v `P35-UT10-differential/examples.json` (příklady `08`, `09`, `10`, `10b`, `11`, `11b`, `11c`, `14`). Potom upravit větu v `pr.md` „The tests pin 1–3, 4–7…".

### 4. Kontrola před commitem (volitelně)

Skill `/verify-pr-ready` projde akceptační kritéria proti kódu a spustí QA.

### 5. Commit

```shell
cd /Users/admin/repos/AbsaOSS/living-doc-utilities
git switch refactor/183-framing-pass
git add living_doc_utilities/authoring/ tests/authoring/test_framing.py docs/
git status --short    # pr.md, OPEN_POINTS.md, P35-UT10-migration-guide-cs.md a .claude/settings.json zůstávají nestagované
git commit -F ../living-doc/specs/liv-doc-spec/issues/P35-UT10-commit-message.txt
```

Commit message končí řádkem `Co-Authored-By: Claude …` — pokud ho nechceš, smaž ho v souboru předem.

### 6. Push a PR

- push větve, PR proti `master`, tělo z `pr.md` (obsahuje `## Framework`, `Closes #183` a seznam skupin)
- po merge: tag `v0.5.0` řežeš ty; další úkol je `P35-CGH1b1` (první konzument `0.5.0`)

## Otevřené body

| # | Bod | Co s tím | Kdy |
|---|---|---|---|
| O1 | **Rozhodnutí o skupinách 3–12** | krok 1 výše | před commitem |
| O2 | **Testy pro skupiny 8–12** chybí | krok 3 výše | před commitem, pokud je přijmeš |
| O3 | **`D22` — pád na prázdném bloku kritéria.** `### AC:US-001-01 (v1.0.0 - active)` jako poslední řádek (nic pod ním) shodí `parse_issue_body` i `parse_feature_header` (`ValueError: zip() argument 2 is longer than argument 1` v `ac_grammar._parse_extensions`). Existuje i na `master`; porušuje „parsery nikdy nepadají". | oprava je jednořádková + test, ale mění výstup → samostatný úkol, nejpozději `P35-CGH1b2`; zapsáno v `debt.md` jako `D22` | po tomto PR |
| O4 | **`D19` — „one-site change" platí jen částečně.** Vnoření v issue body se teď čte ve `framing.py::frame_issue_body` (co je text položky) a v `issue_body.py::_read_bullets` (jak se text skládá). Řádek `D19` jsem neupravoval. | upřesnit text `D19` v `debt.md`, nebo nechat do rozhodnutí `D19` | kdykoli |
| O5 | **`AC:` na úrovni položky v odrážkovém poli** je dál zároveň textem položky **i** kritériem (`- Parent.` a hned pod ním `AC:US-001-01 (…)` bez odsazení). `D20` řeší jen zalomený (hlubší) řádek. | rozhodnout, zda zapsat jako nový řádek `debt.md` | kdykoli |
| O6 | **Klíč na zavíracím řádku si nechává `*/` v hodnotě** (` * route: /setup */` → `route = "/setup */"`). Stejné jako na `master`. | odříznout `*/` by byla změna výstupu → případně samostatný úkol | kdykoli |
| O7 | **Zastaralý docstring** v `tests/authoring/test_notes.py:667` jmenuje smazané `po_section_break`. Neupraveno, protože existující testy měly zůstat beze změny. | opravit jedno slovo v docstringu (chování testu se nemění), nebo nechat na později | kdykoli |
| O8 | **Strukturální problémy rámce nikdo nekonzumuje** (`normalize_framed(...)[1].problems`: `no_frame`, `unterminated_frame`, `key_outside_frame`). | počítá s nimi kontrola nad parserem (`D18`, `D21`) | s `D18` / `D21` |
| O9 | **Ostatní soubory ve `specs/` zmiňují `D20`** jako otevřený (tasklist, drafty issue). Upraven byl jen `debt.md`. | aktualizovat tasklist (`P35-UT10` hotovo, `D20` uzavřen) po merge | po merge |
| O10 | **Prázdný Claude Docs dokument** „Průvodce migrací: framing pass (P35-UT10)" (`https://claude.ai/artifact/FPkhF3apoz6dQzpjxKvsjZ`) vznikl omylem, než padlo rozhodnutí pro lokální soubor. Je prázdný a soukromý. | řekni, a smažu ho | kdykoli |
| O11 | **Skupina 12 chyběla v první verzi `pr.md`** — doplněna. Při další revizi `pr.md` zkontrolovat, že seznam skupin sedí s průvodcem (1–12). | kontrola | před PR |
| O12 | **Odstranit pracovní soubory z větve.** `OPEN_POINTS.md`, `P35-UT10-migration-guide-cs.md` a `pr.md` jsou v commitu `1230899` záměrně, kvůli práci na jiném počítači. Před merge je z větve odstranit: `git rm --cached OPEN_POINTS.md P35-UT10-migration-guide-cs.md pr.md` a commit (soubory zůstanou na disku). | ty | před merge |
| O13 | Pokud se po rozhodnutí o skupinách 3–12 mění kód, bude to **další commit** (ne nový) — commit message v `P35-UT10-commit-message.txt` už je použitá. | — | po rozhodnutí O1 |

## Rychlá orientace v návrhu

- `framing.py` — řádkový model (`IndentedLine`, `BulletItemTracker`), role řádků (`Role`), rámec (`Frame`, `FramedLine`, `Section`, `Problem`) a čtyři framery `frame_issue_body`, `frame_feature_header`, `frame_page_object`, `frame_scenario_file`.
- `normalize.py` — `normalize_framed()`: fáze 1 `_prepare` (pravidlo 6) → framer → fáze 3 `_rewrite_markdown` / `_rewrite_feature_header` / `_rewrite_page_object` / `_rewrite_scenario_file`. `normalize()` vrací jen `NormalizedSource`.
- parsery — `sections(frame)` pro sekce a klíče, `frame.title` pro titulek, `criteria_text(frame, …)` pro vstup gramatiky kritérií.
