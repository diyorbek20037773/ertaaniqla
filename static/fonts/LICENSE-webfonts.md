# Webfont licences

All families are licensed under the **SIL Open Font License 1.1** (OFL), which permits
self-hosting, subsetting and redistribution with the software.

| File | Family | Copyright | Source |
|---|---|---|---|
| `AlbertSans-var-latin.woff2`, `AlbertSans-var-latin-ext.woff2`, `AlbertSans-var-italic-latin.woff2`, `AlbertSans-var-italic-latin-ext.woff2` | Albert Sans (variable, 100–900) | © 2021 The Albert Sans Project Authors (https://github.com/usemodify/albert-sans) | Google Fonts, `fonts.gstatic.com/s/albertsans/v4/` |
| `Manrope-var-cyrillic.woff2`, `Manrope-var-cyrillic-ext.woff2` | Manrope (variable, 200–800) | © 2018 The Manrope Project Authors (https://github.com/sharanda/manrope) | Google Fonts, `fonts.gstatic.com/s/manrope/v20/` |
| `InstrumentSerif-latin.woff2`, `InstrumentSerif-latin-ext.woff2`, `InstrumentSerif-italic-latin.woff2`, `InstrumentSerif-italic-latin-ext.woff2` | Instrument Serif (400, roman + italic) | © 2022 The Instrument Serif Project Authors (https://github.com/Instrument/instrument-serif) | npm `@fontsource/instrument-serif` 5.3.0 |
| `PlayfairDisplay-var-{latin,latin-ext,cyrillic}.woff2`, `PlayfairDisplay-var-italic-{latin,latin-ext,cyrillic}.woff2` | Playfair Display (variable, 400–900) | © 2017 The Playfair Display Project Authors (https://github.com/clauseggers/Playfair-Display) | npm `@fontsource-variable/playfair-display` 5.3.0 |

Albert Sans ships no Cyrillic glyphs; Manrope covers the Cyrillic `unicode-range` for `ru` and
`uz_Cyrl` (ADR-0006, D-058). The final design (D-081) sets headings in serifs: Instrument Serif
(Latin only) with Playfair Display for Cyrillic, and Playfair Display for the landing hero. Files are the upstream Google Fonts subsets, unmodified.

The OFL text: https://openfontlicense.org/open-font-license-official-text/

`DejaVuSans*.ttf` in this directory is unrelated (server-side OG/story image rendering) and keeps
its own `LICENSE` file.
