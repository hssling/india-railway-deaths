# ADSI railway deaths: extraction notes

Source: NCRB *Accidental Deaths & Suicides in India* (ADSI) PDFs held locally. The years covered are 2014, 2015 and 2018–2024. The 2016 and 2017 reports are not held.
Regenerate everything with `python -I src/extract_adsi_railway.py`. That run writes `data/railway_state_year.csv`, `data/railway_state_year_wide.csv` and `data/railway_validation_log.txt`.

## Tables and PDF pages used

| Year | PDF | 1A.2 traffic (state) | 1A.12 classification | 1A.13 classification (2024 incidents) | cause table | 1A.9 unmanned crossing |
|---|---|---|---|---|---|---|
| 2014 | downloads_2026_11/adsi_2014_cag.pdf | p151 | p208–209 | – | 1A.13 p210–211 | p191 (cause column) |
| 2015 | downloads_2026_11/adsi_2015_medbox.pdf | p153 | p212–213 | – | 1A.13 p214–215 | p195 |
| 2018 | ncrb/ADSI_2018.pdf | p155 | p214–215 | – | 1A.13 p216–217 | p197 |
| 2019 | ncrb/ADSI_2019.pdf | p153 | p212–213 | – | 1A.13 p214–215 | p195 |
| 2020 | ncrb/ADSI_2020.pdf | p155 | p214–215 | – | 1A.13 p216–217 | p197 |
| 2021 | ncrb/ADSI_2021.pdf | p155 | p214–215 | – | 1A.13 p216–217 | p197 |
| 2022 | ncrb/ADSI_2022.pdf | p155 | p214–215 | – | 1A.13 p216–217 | p197 |
| 2023 | ncrb/ADSI_2023.pdf | p155 | p214–215 | – | 1A.13 p216–217 | p198 |
| 2024 | ncrb/ADSI_2024.pdf | p157 | p216 (Railway Accidents) | p217 (Incidents on Railway Tracks/In Railway Premises) | 1A.14 p218–219 | p199 |

The 2014 and 2015 equivalents carry the same table numbers (1A.12 and 1A.13) as 2018–2023. The 2014 titles read "Distribution of Classification of Railway Accidents" and "Distribution of Railway Accidents by Causes".
National narrative figures come from the executive summary "Traffic Accidents" bullets (p14–17) and the "Fall from trains … (x out of y)" sentence (p15/17). The 2024 Figure 1A.9 pie labels (p154) were also checked.

## Method

- The extraction uses PyMuPDF word coordinates (`page.get_text('words')`). It does not use pdftotext layout mode.
- Columns are anchored on the printed column-number line `(1) (2) (3) …`. Each number token goes to the nearest column-number x-centre, and a token more than 0.6 × column spacing away is rejected.
- Numeric tokens are grouped into rows by y-centre (±2.5 pt). Each label word left of the data zone attaches to the nearest numeric row by y (≤9 pt). This handles names wrapped over two lines, e.g. `D & N HAVELI AND / DAMAN & DIU` (2020+) and the 2024 wrapped names `ANDHRA / PRADESH`, `JAMMU & / KASHMIR`.
- Column-group labels are read from the header words above each Cases/Injured/Died triple and stored exactly as printed, including `Railway Accidents*` in 2023.
- Footer tokens (page number, year) are dropped and logged as `IGNORED`.
- The table and concluded page of each table are joined by row label.

## Validation (see `data/railway_validation_log.txt`)

The run produced 6,939 OK and 3 mismatches. All three mismatches are printed narrative or figure inconsistencies, not extraction errors. No cell was unreadable.

- **Vertical checks, every column of every table and year.** State rows sum to TOTAL (STATES), UT rows sum to TOTAL (UTs), and STATES + UTs equals TOTAL (ALL INDIA). All OK.
- **Horizontal checks, every row and measure.** The categories sum to the printed Total for 1A.2, 1A.12, 2024 1A.13 and the cause table. All OK.
- **Cross-table checks, every state and measure.** All OK:
  - 1A.12 Total = 1A.2 "Railway Accidents"
  - cause-table Total = 1A.12 Total
  - in 2024: 1A.12 = 1A.2 Railway Accidents (all 0), 1A.13 = 1A.2 Incidents, and 1A.14 = 1A.12 + 1A.13
- **Narrative checks.** Railway, crossing and (2024) incident cases and deaths in the executive summary match the tables. Fall-from-train cases match for 2014 and 2018–2024; no such sentence was found for 2015.
- **Mismatch 1: 2014 executive summary.** It prints crossing deaths as "1.5% (2,547 deaths)", but 2,547 is the cases figure. Table 1A.2, the cause tables and the p139 narrative ("2,575 deaths") all give 2,575, so the table value is kept.
- **Mismatches 2 and 3: 2024 Figure 1A.9 pie labels.** The figure gives fall-from-train 17,029 and "Explosion/Fire & Others" 5,384 deaths. The tables give 16,845 and 5,568, and every state row agrees with the tables. Both splits sum to 22,413. Table values are kept.

## National totals (printed TOTAL (ALL INDIA))

| Year | Railway cases | injured | **died** | fall-from-train/people on track died | collisions | derailments | explosion/fire | others | crossing cases | **crossing died** | unmanned crossing died (1A.9) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2014 | 28,360 | 3,882 | 25,006 | 14,391 | 99 | 59 | 32 | 10,425 | 2,547 | 2,575 | 836 |
| 2015 | 29,419 | 4,055 | 26,066 | 18,259 | 38 | 67 | 46 | 7,656 | 2,669 | 2,650 | 262 |
| 2018 | 27,643 | 3,431 | 24,545 | 16,702 | 186 | 32 | 43 | 7,582 | 1,481 | 1,507 | 40 |
| 2019 | 27,987 | 3,569 | 24,619 | 18,339 | 42 | 10 | 0 | 6,228 | 1,788 | 1,762 | 47 |
| 2020 | 13,018 | 1,127 | 11,968 | 8,400 | 49 | 160 | 5 | 3,354 | 1,014 | 1,185 | 24 |
| 2021 | 17,993 | 1,852 | 16,431 | 11,036 | 86 | 22 | 0 | 5,287 | 1,550 | 1,807 | 44 |
| 2022 | 23,139 | 2,457 | 20,792 | 15,096 | 0 | 2 | 1 | 5,693 | 2,560 | 2,455 | 13 |
| 2023 | 24,678 | 3,014 | 21,803 | 15,878 | 0 | 14 | 0 | 5,911 | 2,483 | 2,242 | 0 |
| 2024* | 25,397 | 3,136 | 22,413 | 16,845 | 0 | 0 | 0 | 5,568 | 1,892 | 1,888 | 0 |

\*2024 figures are Railway Accidents (0) plus Incidents on Railway Tracks/In Railway Premises (25,397 cases; 22,413 deaths).

The cause tables put 93–99.9% of deaths under "Other Causes" every year. They carry almost no information. For example, 2024 gives 22,406 of 22,413 deaths under "Other Causes".

## Category definitions and changes over time

### 2014–2023

1A.2 splits traffic accidents into Road, Railway, Railway Crossing and Total Traffic.

1A.12 classifies Railway Accidents into five categories plus Total:
- Collisions
- Derailments
- Fall from Train/Collision with People at Tracks
- Explosion/Fire
- Others

The cause table (1A.13) has five causes plus Total:
- Fault of Driver
- Signalmen's Error
- Sabotage by Extremist/Terrorist/Others
- Mechanical Failures (like Poor Design, Track Faults, Bridge/Tunnel Collapse etc.)
- Other Causes

ADSI 2014 notes that the former "Other Railway Accidents" was renamed "Railway Accidents" from the 2014 edition.

### 2024 change

ADSI 2024 splits the former "Railway Accidents" into two traffic-accident sub-heads:

- **'Railway Accidents'** (Table 1A.12, "Classification-wise Distribution of Railway Accidents"). Its columns are Collisions, Derailments and Explosion/Fire, plus Total. There is no Fall or Others column. **Every state prints 0** cases, injured and died.
- **'Incidents on Railway Tracks/In Railway Premises'** (new Table 1A.13). Its columns are Fall from Train/Collision with People at Tracks and Others, plus Total. It has 25,397 cases, 3,136 injured and 22,413 deaths, of which 19,416 cases and 16,845 deaths are fall-from-train.
- 1A.2 gains a column, giving Road, Railway Accidents, Incidents on Railway Tracks/In Railway Premises, Railway Crossing and Total Traffic.
- The cause table moves to 1A.14 and covers both heads.
- The executive summary reads: "Zero (0) 'Railway Accidents', 25,397 'Incidents on Railway Tracks/In Railway Premises'".
- ADSI 2024's year-on-year table (p47) re-states 2023 as 1 Railway Accident plus 24,677 Incidents, against the 24,678 Railway Accidents printed in ADSI 2023.

In practice the 2024 "Incidents" head contains what was previously almost all of "Railway Accidents". **The time-consistent series is 1A.12 Total plus 1A.13 Total**, which is what `railway_total_*` in the wide file uses. Collisions and derailments, including real 2024 train crashes, appear in neither 2024 head. They were already near zero in 2022–2023.

## State units

- `state_printed` is kept exactly as printed. `state_canonical` maps to current names.
- D & N Haveli and Daman & Diu are printed separately before 2020. Both map to "Dadra & Nagar Haveli and Daman & Diu" and are summed in the wide file. All their values are 0.
- Jammu & Kashmir before 2020 is the former State, which included Ladakh. From 2020 J&K and Ladakh are separate UTs, and J&K moves to the UT block. `state_panel` in the wide file merges them into "Jammu & Kashmir incl. Ladakh" for a time-consistent unit.
- Delhi is printed "DELHI (UT)". 2019 prints "A & NISLANDS". 2023 prints "ODISHA*". All are mapped.

## Data caveats (values validated and kept as printed; flagged in the wide `notes` column)

1. **Odisha 2023 = 0.** The footnote reads "Clarification on 'Railway Accidents' data is pending from Odisha". The June 2023 Balasore triple-train collision is therefore missing, and 2023 shows collisions = 0. Odisha 2022 is also low (27 deaths, against 280–446 in 2018–21).
2. **Karnataka prints 0 railway deaths in every year 2018–2024.** It printed 25 in 2014 and 891 in 2015. Karnataka railway deaths are effectively unreported in ADSI.
3. **Probable misfiling between railway and railway-crossing heads:**
   - Telangana 2014: 3 railway deaths against 1,070 crossing deaths.
   - Haryana 2015: 1 railway death against 1,286 crossing deaths.
   - Bihar 2014: 604 railway against 485 crossing; in 2015 it was 1,891 against 16.
   - Andhra Pradesh 2015: 268 crossing deaths, against ≤4 in other years.
4. **Fall/Others split depends on reporting practice.** Delhi and West Bengal put almost all deaths in "Others" (e.g. WB 2024: 2,054 of 2,091), and Haryana 2014, Assam 2014 and Telangana 2015 put 100% there. Use total railway deaths as the primary outcome. The fall-from-train share is not comparable across states.
5. **Unmanned railway crossing (Table 1A.9) is not a clean subset of 1A.2 Railway Crossing.**
   - In 2014 it is a road-accident "cause" column; the 1A.8 total of 451,707 is 450,898 road accidents plus 809 unmanned.
   - In 2015+ it is a separate block added to road accidents in a "Grand Total".
   - The 2015 footnote says Tamil Nadu, Maharashtra, Assam and Bihar did not include unmanned crossings in "Railway Crossing Accidents".
   - Assam 2014 prints 654 unmanned deaths against 11 crossing deaths.
   - Keep it as a separate series and never add it to crossing deaths. Indian Railways reports that unmanned level crossings on broad gauge were eliminated around 2019, and the column is 0 from 2023.
6. **2020–2021 are COVID-affected.** Passenger services were suspended or curtailed, and 2020 has 11,968 deaths.
7. **2016–2017 are missing** from the panel because those PDFs are not held.
8. City-wise pages of 1A.2 (53 mega-cities) were not extracted.
