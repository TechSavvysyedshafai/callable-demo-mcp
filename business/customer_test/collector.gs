/**
 * Free collector for the landing page, using Google Sheets + Apps Script. No outside servers.
 * Setup (about 10 minutes, you do it signed in to your own Google account):
 * 1. Create a Google Sheet. Add two tabs named exactly: events  and  signups.
 *    events header row:  date | channel | event | price_choice
 *    signups header row: date | channel | name | phone | shop | city | problem | consent | consent_source
 * 2. In the Sheet: Extensions > Apps Script. Paste this file. Save.
 * 3. Deploy > New deployment > type "Web app". Execute as: Me. Who has access: Anyone. Deploy and copy the Web app URL.
 * 4. Paste that URL into FORM_ENDPOINT inside landing/index.html.
 * 5. To analyse: File > Download > CSV of the events tab, then: python3 funnel.py events.csv
 * Keep the signups tab private. It holds phone numbers. Only message people whose consent column says yes.
 */
function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ev = ss.getSheetByName("events");
  ev.appendRow([data.date, data.channel || "", data.event, data.price_choice || ""]);
  if (data.event === "signup" && data.consent === "yes") {
    ss.getSheetByName("signups").appendRow([data.date, data.channel || "", data.name || "", data.phone || "",
      data.shop || "", data.city || "", data.problem || "", data.consent, data.consent_source || ""]);
  }
  return ContentService.createTextOutput("ok");
}
