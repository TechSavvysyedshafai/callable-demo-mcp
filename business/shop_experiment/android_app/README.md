# Shop Log (Android app, first draft)

A tiny Android app for the shop experiment. It replaces the two Google Sheets with two phone screens:

- **Daily log**: fill at closing time (walk-ins, bills, sales, exchanges, festival day, how buyers found the shop, notes).
- **Lost sale**: fill after each walk-out (item, size, price, what they bought instead, a reason chip, notes).

The columns are the same as `../daily_log_template.csv` and `../lost_sales_template.csv`.
Data stays on the phone, in the app's private storage. "Share all as CSV" sends the whole file as text
(for example to WhatsApp or email) so it can be pasted into the sheet. Nothing is uploaded anywhere.

## Status: NOT BUILT OR TESTED

The code was written in a cloud sandbox that has no Android SDK and cannot reach Google's build servers,
so it has **never been compiled or run**. Expect to fix small build errors on the first try.
Library versions are from late 2024 (Android Gradle Plugin 8.7.3, Kotlin 2.0.21, Compose BOM 2024.10.01);
Android Studio will offer to update them.

The Gradle wrapper files are not included. Android Studio creates them when it opens the project.

## How to run it (on your own computer)

1. Install Android Studio (https://developer.android.com/studio).
2. File > Open, and choose this `android_app` folder. Let it sync.
3. Connect an Android phone with USB debugging on (or start an emulator), then press Run.

## Known limits

- No edit or delete of saved rows yet. Fix mistakes in the sheet after sharing the CSV.
- No backup. If the app is uninstalled, the data is lost, so share the CSV regularly.
- Saved dates use the phone's date.
