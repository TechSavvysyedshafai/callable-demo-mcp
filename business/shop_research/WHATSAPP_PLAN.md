# WhatsApp Business Platform plan for the shop (Meta MCP)

Source for the tool list and prerequisites: Meta's page "WhatsApp Business Tools MCP" (updated 3 Sep 2026), https://developers.facebook.com/documentation/mcp/whatsapp-business-tools-mcp . Beta, rolling out gradually. Prices and Indian rules were NOT checked: confirm on Meta's pricing page and with a CA/lawyer before sending to a large list.

## Step 0: decide the phone number (do this first)
A number registered on the Cloud API platform usually cannot also run in the normal WhatsApp or WhatsApp Business app (check Meta's current migration/coexistence rules before you register your existing shop number). Safest: get a NEW SIM/number just for the platform and keep the old number for chatting with customers.

## Step 1: Meta accounts (owner does this, ~30 minutes plus waiting)
1. Create or open a Meta Business account at business.facebook.com with your Facebook login. You need admin (MANAGE) access.
2. Create a Meta developer account at developers.facebook.com, then create an app with the "WhatsApp Business Messaging" use case and connect it to your business. You must be admin of the app.
3. Accept the WhatsApp Business Cloud API terms for the business.
4. Add a payment method (business messages are billed).
5. Start Business Verification (Meta will ask for business documents such as GST or Udyam registration and proof of address; what exactly is accepted is Meta's call, check its screen).

## Step 2: connect the tool (owner does the sign-in)
In Claude: Settings > Connectors > Add custom connector.
- Name: WhatsApp Business Tools
- URL: https://mcp.facebook.com/whatsapp_business_tools
Then sign in with your Meta account and pick ONLY the business and app for the shop. You can revoke access later at facebook.com > Settings > Business Integrations.
Tell me "connected". I will first only READ (list businesses, numbers, templates, verification status) and report back. Nothing is sent without your OK on each target.

## Step 3: templates (I draft, Meta approves, usually in minutes to a day)
Only approved templates can start a conversation. {{1}} etc. are blanks filled per customer. Meta may reject vague or pushy text; if so we reword.

Template A: new_stock_update (category: Marketing)
EN: Hi {{1}}, new jeans and T-shirts have arrived at {{2}}, Patna. Try anything on, and swap within 7 days with your bill. Visit us: {{3}}. Reply STOP to stop these messages.
HI: नमस्ते {{1}}, {{2}}, पटना में जींस और टी-शर्ट का नया स्टॉक आ गया है। कुछ भी पहनकर देखें और बिल के साथ 7 दिन में बदलें। पता: {{3}}। ये संदेश बंद करने के लिए STOP लिखें।

Template B: student_offer (Marketing)
EN: Hi {{1}}, students get {{2}} at {{3}} with a valid student ID, until {{4}}. Reply STOP to stop these messages.
HI: नमस्ते {{1}}, {{3}} पर छात्रों को वैध स्टूडेंट आईडी दिखाने पर {{2}} मिलेगा, {{4}} तक। ये संदेश बंद करने के लिए STOP लिखें।

Template C: review_request (Marketing)
EN: Thank you for shopping at {{1}}, {{2}}. If you liked it, please leave a short review: {{3}}. Reply STOP to stop these messages.
HI: {{1}}, {{2}} से खरीदारी के लिए धन्यवाद। अगर आपको अच्छा लगा तो छोटा सा रिव्यू दें: {{3}}। ये संदेश बंद करने के लिए STOP लिखें।

Only promise what is true (the 7-day swap, the student discount). Set the template language correctly (en or hi).

## Step 4: consent (the most important part)
Send marketing messages ONLY to people who agreed. Counter form (print it):
"May we send you offers and new-stock news on WhatsApp? Name: ____ Phone: ____ [ ] Yes. You can reply STOP any time."
Keep the signed forms or a sheet with the date. Do not buy lists. Do not message people who never bought from you or asked for it. Handle every STOP the same day. India's data-protection law (DPDP) may add rules; ask a CA/lawyer.

## Step 5: a small first test
1. Send template A to 3 numbers that belong to you or your family. Check it looks right.
2. Send to 20 customers who gave consent. Count replies and visits ("How did you hear about us?").
3. Review cost and results after 2 weeks before scaling.

## Step 6: weekly routine (about 20 minutes)
- Monday: I draft the week's message and the Google post. You approve.
- Send only 1 message per customer per week at most.
- Log: sent, replies, STOPs, visits, in the tally sheet.

## Safety
- Never paste the system-user token or any password into chat.
- Revoke the connector if you stop using it.
- If Meta blocks or limits the number, stop sending and fix the cause (usually consent or complaints).
