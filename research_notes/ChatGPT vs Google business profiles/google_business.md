# Google Business Profile (GBP), state of play as of 14 Nov 2026

Method note: WebFetch could not reach support.google.com, blog.google, developers.google.com, seroundtable.com or whitespark.ca (DNS blocked in this session). All content below was read through Exa search highlights, which returned the text of those pages. Labels: VERIFIED = Google-owned page text seen in the search result; REPORTED = third party (agency, press, vendor study). Many "published" dates are as shown by Exa; Google help pages carry no date, so "retrieved 14 Nov 2026" applies.

## Cost, verification, eligibility

### Takeaway
GBP is free to create and manage. Verification is mandatory to edit info or see performance data; Google picks the method (phone/SMS, email, live video call, recorded video) and review takes up to 5 business days. Online-only businesses are not eligible.

### Cited Findings
- VERIFIED: "Creating a Business Profile and listing your business on Google is free." (US and India pages) — [Google Business Profile US](https://business.google.com/us/business-profile/); [India](https://business.google.com/in/business-profile/) (retrieved 14 Nov 2026)
- VERIFIED: You must verify to edit business info (name, hours) and interact with customers; verification methods are chosen automatically by Google and cannot be changed; options depend on business type, public info, region, hours; phone/SMS (IVR systems won't receive the code), email, live video call (only in business hours, not for all), video recording. Google recommends video if eligible. Review takes up to 5 business days; instant verification possible via Search Console website verification or bulk verification. — [Verify your business](https://support.google.com/business/answer/7107242?hl=en) (retrieved 14 Nov 2026)
- VERIFIED: Video verification: live, unedited, continuous, at least 30 seconds, recorded and uploaded from a mobile device; must show location, signage with name matching the profile, and proof of management (e.g. cash register, kitchen); service-area businesses show tools/vehicle/documents. Review up to 5 business days; rejected videos get reasons. Online-only businesses (no in-person service) are not eligible for a profile. — [Verify with a video recording](https://support.google.com/business/answer/14271705?hl=en)
- VERIFIED: Performance data is available only for verified profiles. — [Understand performance & insights](https://support.google.com/business/answer/9918094?hl=en)
- REPORTED: A guide says a new option in May 2026 lets Google send the verification code to a WhatsApp number (India-oriented guide; not confirmed on a Google page by me) — via WebSearch result summary of [Hashnode India guide](https://hashnode.com/posts/how-to-add-your-phone-number-to-google-business-profile/6878a33108ff986353c9ab29)
- REPORTED: Birdeye 2025 benchmark: 76% of profiles verified; verified profiles up to 4x more website visits than unverified — [SEOprofy compilation](https://seoprofy.com/blog/local-seo-statistics/)

### Inferences
- "Free" is true for the listing; the real cost is owner time plus paid Google Ads/Local Services Ads if wanted. Indian guides compare it against Justdial paid plans.

### Gaps
- No official verification-failure rate found.

## Features (reviews, posts, products, messaging, bookings, Q&A, insights)

### Takeaway
Core features: reviews with owner replies, posts (Update/Offer/Event), photos/video, products, menus, attributes, action links (order/reserve/book), performance metrics. Two-way chat and call history were removed on 31 Jul 2024; the public Q&A thread is being replaced by a Gemini "Ask" button (Dec 2025).

### Cited Findings
- VERIFIED: Landing page promises orders, reservations, product/stock display and service booking from the profile. — [Google Business Profile US](https://business.google.com/us/business-profile/)
- VERIFIED: Performance metrics: Interactions, Searches (monthly, can take 5 days), Views (unique, once per day), Directions, Calls (call-button clicks), Website clicks, Messages, Bookings (only via a booking provider), Booking clicks (hotels), Products, Menus, Offers. Includes organic and Google Ads. — [Performance help](https://support.google.com/business/answer/9918094?hl=en)
- VERIFIED: As of 31 Jul 2024 chat and call history are gone from Business Profile; customers can still contact via Search/Maps; eligible accounts may get texts or WhatsApp. — [Chat and call history change](https://support.google.com/business/answer/14919056?hl=en)
- VERIFIED: Q&A API discontinued 3 Nov 2025 (announced 15 Sep 2025). — [Q&A API change log](https://developers.google.com/my-business/content/qanda/change-log)
- REPORTED: Google confirmed on 3 Dec 2025 (post by a Google Product Specialist in the help forum) that Q&A is replaced by an AI-powered Ask button in Maps that answers from owner answers and relevant reviews; Q&A launched in Maps in 2017. — [PPC Land, 22 Dec 2025](https://ppc.land/google-quietly-kills-q-a-for-an-ai-button-most-wont-use/). Volunteer Product Expert confirms the "Ask a Question" button and FAQ were removed, 29 Dec 2025 — [Help community thread](https://support.google.com/business/thread/398355862/the-ask-a-question-button-is-gone-from-my-gbp?hl=en)
- REPORTED: Google added 54 new attributes in April 2026 (GMBapi, via SEOprofy) — [SEOprofy](https://seoprofy.com/blog/local-seo-statistics/)
- REPORTED: Whether GBP gets categories: one primary + up to nine additional (Google, via SEOprofy). Photos: Google playbook says 90% of people more likely to visit with photos and 35% more website clicks (Google's own figures, undated origin) — [GBP Best Practices Playbook 2026 (Google PDF)](https://services.google.com/fh/files/helpcenter/services_gbp_best_practices_playbook_2026.pdf)

### Inferences
- Google is shifting from owner-to-customer channels (chat, Q&A) to AI-mediated answers built from profile + reviews.

### Gaps
- Current status of products/posts feature changes in 2026 not separately verified.

## Gemini and AI tools for owners (2025-2026)

### Takeaway
Google now lets owners manage the profile conversationally in Gemini (hours, menus, posts, review replies, insights).

### Cited Findings
- VERIFIED: Google blog 10 Jun 2026: one-tap connection of GBP to Gemini "in the coming weeks"; Gemini can analyze impressions, direction requests, calls, draft review replies, update hours, post updates; "Business notebooks" with proactive alerts. — [Google blog, Gemini features for small businesses](https://blog.google/innovation-and-ai/products/gemini-app/gemini-features-for-businesses/)
- VERIFIED: Help page lists Gemini web app capabilities: edit hours/menus/attributes/links/action links, upload photos by public URL, draft/delete review replies, create/schedule/publish/delete Update, Offer, Event posts, view metrics and search keywords. — [Manage your profile with Gemini](https://support.google.com/business/answer/17142585)

### Inferences
- Owner workload shifts to prompts; this also raises the bar on the accuracy of the underlying profile data.

### Gaps
- Rollout geography (India, Hindi) for the Gemini connection not found.

## API

### Takeaway
GBP APIs exist but are not public: access needs an application, a verified profile active 60+ days and a website.

### Cited Findings
- VERIFIED: Applicants must manage a verified, active GBP for 60+ days and have a website; apply via contact form ("Basic API Access"); quota 0 QPM = not approved, 300 QPM = approved. — [Prerequisites](https://developers.google.com/my-business/content/prereqs)
- VERIFIED: FAQ: requests reviewed within 14 days; APIs include Business Information, Account Management, Verifications, Performance, Place Actions, Notifications, Lodging, plus v4.9 Reviews, Media, LocalPosts, FoodMenus. — [FAQ](https://developers.google.com/my-business/content/faq)
- VERIFIED: Quotas: 300 QPM default for most APIs; edits limited to 10 per minute per profile (cannot be increased). — [Usage limits](https://developers.google.com/my-business/content/limits)
- VERIFIED: Deprecations: Q&A API discontinued 3 Nov 2025; Calls API 30 May 2023; health/insurance attributes 2024. — [Deprecation schedule](https://developers.google.com/my-business/content/sunset-dates)
- VERIFIED: Performance API returns daily metrics time series and monthly search keyword impressions. — [Performance API reference](https://developers.google.com/my-business/reference/performance/rest)

### Gaps
- API pricing: none stated on pages seen (appears free; not explicitly confirmed).

## Reach and usage statistics

### Takeaway
No official count of GBP-using businesses was found. Third-party datasets give scale (18.1M live US listings in Jul 2026) and action splits. Calls and website clicks are falling while direction requests rise in 2026.

### Cited Findings
- REPORTED: Google Maps lists 250 million businesses and places; 2B+ monthly Maps users (Google, 2025, via Searchlab) — [Searchlab](https://searchlab.nl/en/statistics/google-business-profile-statistics-2026)
- REPORTED: Crawlora July 2026 dataset: 18,130,566 live US GBP listings; 39% had no website; only 8.4% had 4.5+ stars and 50+ reviews — [SEOprofy](https://seoprofy.com/blog/local-seo-statistics/)
- REPORTED: US year-over-year, Q2 2026: calls -11.9%, website clicks -12.5%, directions +21.1% (Q1 corrected: calls and clicks -15.8%, directions +31.3%); based on GMBapi data; mobile search impressions -20.1%. — [Search Engine Land, 31 Aug 2026](https://searchengineland.com/calls-clicks-falling-google-maps-destination-486276)
- REPORTED: Diib, 12,996 profiles, Aug-Oct 2026 vs 2025: views +6%, calls -4%, website clicks -4%, directions +1%; Maps views +11%, Search views -5%. — [Diib, 6 Nov 2026](https://diib.com/start/insights/google-business-profile-views-calls/)
- REPORTED: Birdeye 2026: actions split website 47%, directions 38%, calls 15%; impressions per location -53.8% yoy but actions about -5%; 86% of impressions from category (non-brand) searches — [SEO Sandwitch](https://seosandwitch.com/local-pack-ctr-statistics/) (secondary aggregator of Birdeye)
- REPORTED: Dental/medical practice dataset (268-311 practices): GBP produced 55.9% of leads; 80.5% of profile impressions were on Search, 19.5% on Maps; action split directions 39.6%, calls 33.5%, website 26.9% — [TechBullion, 19 Aug 2026](https://techbullion.com/does-local-seo-bring-patients-here-is-what-the-data-says/) (single-vertical, vendor-authored; weak)
- REPORTED: BrightLocal 2026: 52% of consumers start latest local search on Google, 71% use Google at some point; 1 in 5 search directly within map apps (2025). — [BrightLocal local SEO statistics](https://www.brightlocal.com/resources/local-seo-statistics/)
- REPORTED (old): BrightLocal 2019: average profile 1,260 views/month (943 Search, 317 Maps), about 5% of views become an action — [Searchlab](https://searchlab.nl/en/statistics/google-business-profile-statistics-2026). Dated; do not present as current.
- REPORTED: One secondary source claims AI tools rose from 6% to 45% of local discovery and Google fell 83% to 71% (BrightLocal); I could not verify against BrightLocal — [Pinmeto summary](https://www.pinmeto.com/news/brightlocal-local-consumer-review-survey-2026/)

### Inferences
- Falling calls with rising directions suggests Maps is becoming a destination and AI/pack changes remove call buttons.

### Gaps
- No Google-published figure for number of businesses on GBP or share of local queries via Maps/Search. Searchlab's "75% of views from Search" is from 2019.
- SEL/GMBapi sample is small (179 profiles in the earlier analysis; mostly law firms in the Sterling Sky/Jepto set).

## Reviews and ranking factors

### Takeaway
Google states local ranking rests on relevance, distance and prominence; reviews and ratings feed prominence. Rankings cannot be bought. Reviews drive consumer choice per BrightLocal's 2026 survey (1,002 US adults).

### Cited Findings
- VERIFIED: "Local results are mainly based on relevance, distance, and popularity"; prominence includes links and review count; "More reviews and positive ratings can help"; "There's no way to request or pay for a better local ranking." Also advises verification, complete info, replying to reviews, photos. — [Improve local ranking](https://support.google.com/business/answer/7091?hl=en)
- REPORTED: BrightLocal LCRS 2026 (published 11 Feb 2026, 1,002 US adults): 97% read reviews; 85% more likely to use after positive reviews; 77% deterred by negative; 74% only care about last 3 months; 47% won't use a business with under 20 reviews; 89% expect owner replies — [Pinmeto summary](https://www.pinmeto.com/news/brightlocal-local-consumer-review-survey-2026/) (secondary; check against BrightLocal)
- REPORTED: Whitespark 2026 (via Searchlab): GBP signals about 32% and review signals about 20% of local pack ranking weight — [Searchlab](https://searchlab.nl/en/statistics/google-business-profile-statistics-2026)
- REPORTED: Local pack CTR 2026: #1 14.8%, #2 12.6%, #3 11.9% (First Page Sage, 41.2M clicks, Mar-Aug 2026) — [SEO Sandwitch](https://seosandwitch.com/local-pack-ctr-statistics/)
- REPORTED: Top-3 profiles had median 41 photos vs 29 (positions 4-10) in a 2026 Localo analysis of 16,098 profiles (correlation, not causation) — [SEOprofy](https://seoprofy.com/blog/local-seo-statistics/)

### Gaps
- Weighting figures are from vendor surveys, not Google.

## AI Overviews / AI Mode effects on local

### Takeaway
GBP is the data base layer of AI answers, but AI surfaces show fewer businesses and fewer call buttons; calls fall even where rankings hold. Evidence is mixed on how often AI Overviews appear for local queries (depends on query wording and study).

### Cited Findings
- REPORTED: Sterling Sky/Places Scout (Oct 2026): AI local packs seen on about 7% of tracked keywords (mobile, US only); show 1-2 businesses, no call buttons, different businesses vs 3-pack; 5,943 unique businesses vs 18,330 in regular packs (about 32%); 88% of 322 markets had fewer unique businesses. — [Sterling Sky, 26 Oct 2026](https://www.sterlingsky.ca/the-state-of-local-seo-in-2026/); [SEL, 5 Feb 2026](https://searchengineland.com/local-rankings-fine-calls-vanishing-468321)
- REPORTED: Synup Sep 2026 study (53,900 SERPs, 49 categories, 250 US cities): AI Overview on 4% of "near me", 8.6% of "[category] [city]", 27% of "best X in city", 75.4% of "specific need" queries; local pack on 91-97% of pages; most-cited domain is google.com (13,777 times, all GBP viewer links); about 6 in 10 qualified-query AIOs contain business cards with Call/Directions/Website. — [Synup Research](https://synup.com/research/local-serp-study)
- REPORTED: Synup 12,250-search study (week of 22 Sep 2026): 64% of map businesses also named in AI answer; 67% of AI-named businesses were not in the map 3-pack (smaller subset). — [Synup blog](https://synup.com/blog/ai-overviews-vs-local-pack-reporting)
- REPORTED: Whitespark: AI Overviews on 68% of local business queries vs local pack 39% (mixed query set); for pure local-intent queries pack 93%, AIO 15% (540 queries, Houston/Phoenix/Denver) — [SEJ, 22 Jul 2026](https://www.searchenginejournal.com/ai-overviews-now-answer-most-local-searches-how-to-get-your-business-cited/580757/); [SEO Sandwitch](https://seosandwitch.com/local-pack-ctr-statistics/). Note: these two Whitespark framings conflict in headline (68% vs 15%) because of query mix.
- REPORTED: Randomized experiment (Agarwal & Sen, SSRN, Apr 2026, 1,065 users): AI Overviews cut outbound organic clicks 39.8%; AI Mode suggested larger reductions (exploratory). General search, not local-specific. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6513059)
- VERIFIED: AI Mode can check local availability/pricing and, when a business has limited online info, Google can phone businesses on the user's behalf (user can type "don't call"). — [Search Help](https://support.google.com/websearch/answer/17104441?hl=en)

### Inferences
- Complete, consistent GBP data (hours, services, booking links) is the lever for AI inclusion; being in the pack does not guarantee AI mention.

### Gaps
- No official Google statement on how GBP data is weighted in AI Mode found. Vendor studies are US/desktop-heavy.

## Agentic booking and automated calls

### Takeaway
Agentic booking rolled out US-first (Aug-Nov 2025), expanded to UK and reportedly India in Apr 2026; Google also phones businesses for customers (US).

### Cited Findings
- VERIFIED: 17 Nov 2025: restaurant booking in AI Mode rolling out in US without Labs; partners OpenTable, Resy, Tock, Ticketmaster, StubHub, SeatGeek, Vivid Seats, Booksy, Fresha, Vagaro. — [Google blog](https://blog.google/products-and-platforms/products/search/agentic-plans-booking-travel-canvas-ai-mode/)
- REPORTED: Timeline: 21 Aug 2025 launch for AI Ultra Labs; 10 Apr 2026 UK launch; WinBuzzer reportedly says same expansion covered Australia, Canada, Hong Kong, India, New Zealand, Singapore, South Africa (secondary, India restaurants only); 19 May 2026 I/O: expansion to local services, calling for home repair/beauty/pet care "this summer" US; 4 Nov 2026 home-service booking links via Angi, Thumbtack, Housecall Pro, Jobber (SEJ). — [Lumivor, 10 Nov 2026](https://lumivor.com/google-ai-mode-agentic-booking-local-business/)
- REPORTED: Automated calls: help page says Google may call, recorded, no charge, US except Indiana, Louisiana, Minnesota, Montana, Nebraska; limited regions and languages. — [Lumivor citing Google help](https://lumivor.com/google-ai-mode-agentic-booking-local-business/); [PPC Land](https://ppc.land/google-quietly-kills-q-a-for-an-ai-button-most-wont-use/) (started July 2025)
- REPORTED: As of 1 Nov 2026 Google help documents Business Profile booking calls and Gemini "Call for Me"; price-check calls say Google "will not create a booking." — [Cheers.tech tracker](https://www.cheers.tech/geo-academy/ai-agent-tracker-local-service-businesses)

### Gaps
- India-specific availability of calling/booking beyond restaurants not verified; Hindi support not found.

## India, tier-2 cities (Patna-type), languages, Justdial

### Takeaway
GBP is free and available in India, but evidence on tier-2 adoption is anecdotal. Justdial has deep tier-2/3 trust, local-language sales reps and paid lead model; no sourced head-to-head traffic data found.

### Cited Findings
- VERIFIED: India GBP page: free profile. — [business.google.com/in](https://business.google.com/in/business-profile/)
- REPORTED: Justdial reported 51M+ active listings and about 200M unique quarterly visitors in late 2025 (Chamko; original filing not seen) — [Chamko, 13 Oct 2026](https://chamkomarketing.app/guides/justdial-vs-google-business-profile/)
- REPORTED: Justdial costs about Rs 30,000-1,00,000+/year negotiated; same enquiry typically goes to several advertisers; about 12,000 sales staff across 250+ cities; about 70% of revenue from top 11 cities (agency blog, unsourced figures) — [Namo Marketing, 1 Sep 2026](https://namomarketing.com/justdial-vs-google-business-profile-india/)
- REPORTED (opinion): In metros Google Maps has largely displaced Justdial; in tier-2/3 Justdial still trusted; Justdial sells in regional languages while GBP is perceived as English-first — [Jatin Agarwal, 17 Mar 2026](https://thejatinagarwal.in/justdial-more-popular-than-google-indian-small-businesses/). Opinion, no data.
- REPORTED: Biharportal lists GBP and Justdial as key free listing options in Patna (Boring Road, Kankarbagh etc.) — [Biharportal, 10 Dec 2025](https://www.biharportal.com/blog/free-business-listing-sites-in-patna-2025)
- REPORTED: In India, third-party directories (Justdial) are a thick corroboration layer for AI answers; stale Justdial NAP can lower AI confidence; Hindi voice queries differ from transliterated — [Angry Turtle, 2 Aug 2026](https://angryturtle.ai/blog/aeo-india-playbook) (agency opinion)
- REPORTED: Reliance Retail bought 66.95% of Justdial for Rs 3,497 crore in July 2021 — via WebSearch summary of Wikipedia/press; not independently fetched.

### Gaps
- No sourced count of Indian GBP businesses, Maps users in India, or Patna-specific data. Supported GBP interface languages and Hindi AI features not verified. Justdial figures not from filings I read.

## Weaknesses, spam, suspensions, complaints

### Takeaway
Fake reviews and fake listings remain a large problem; enforcement is heavy and owners report opaque suspensions, lost reviews after reinstatement and weak support in 2026.

### Cited Findings
- REPORTED (citing Google): 2025 Maps safety report: over 292M policy-violating reviews blocked/removed, 13M+ fake profiles removed, 79M inaccurate map edits blocked — [Search Engine Roundtable](https://www.seroundtable.com/google-maps-spam-fighting-2025-41176.html); [SEOprofy](https://seoprofy.com/blog/local-seo-statistics/)
- REPORTED: Google's review restrictions can include disabling new reviews, unpublishing existing ones, and a warning shown to consumers; enforcement reportedly escalated April 2026 (agency blogs) — [DAC Group](https://www.dacgroup.com/?p=159133); [Pinmeto](https://www.pinmeto.com/news/google-review-restrictions-stack-repeat-violations-2026/)
- REPORTED: Google confirmed investigating missing reviews and blocked new reviews (July 2026) — [Pinmeto](https://www.pinmeto.com/news/google-reviews-missing-pause-investigation-july-2026/); [TechWyse](https://www.techwyse.com/news/platform-updates/google-business-profile-reviews-missing-investigation-2026)
- REPORTED: Google acknowledged reviews missing after reinstatement, no timeline (24 Aug 2026) — [Search Engine Roundtable](https://www.seroundtable.com/reviews-missing-google-business-profile-reinstatement-41927.html)
- REPORTED: HVAC firm: profile locked 9 months, 100+ reviews removed, claimed $300k-500k loss; reviews restored by week of 10 Aug 2026 — [ACHR News, 18 Aug 2026](https://www.achrnews.com/articles/166572-hvac-contractor-loses-thousands-after-google-suspends-business-profile). Georgia agent suspended since April with no stated reason — [WSB-TV, 14 Aug 2026](https://www.wsbtv.com/news/local/google-suspends-real-estate-businesss-profile-attempts-verify-account-are-met-with-silence/4H3EY4VROVCRVDCRD6ONJFBGYU/)
- REPORTED: Study of 198 help-community suspension threads (3 weeks to 24 Sep 2026): 63% had already failed an appeal; 74% unaware of reason; address change most common trigger among those who said; about 40 more threads about missing reviews after reinstatement — [Azizi Technologies](https://azizitechnologies.co.uk/google-business-profile-suspension-study) (small, non-random sample)
- REPORTED: Owner threads of 340+ and 102 reviews missing after reinstatement; support loops — [Google community thread, 24 Aug 2026](https://support.google.com/business/thread/461995489/missing-340-reviews-after-profile-reinstatement-%E2%80%93-lotus-mindfulness-and-relaxation-services?hl=en); [Local Search Forum, 14 May 2026](https://localsearchforum.com/threads/102-missing-reviews-after-reinstatement-support-falsely-claiming-policy-violation.63222/)
- REPORTED: Other complaints: calls falling despite ranking (Sterling Sky); feature removals (chat 2024, Q&A 2025); AI impression counts cannot be segmented from organic (SEL, Whitespark via WebSearch).

### Inferences
- Enforcement is real but anecdotal evidence of wrongful suspensions is hard to size; no official suspension counts.

### Gaps
- Could not read Google's own maps trust-and-safety blog (blocked); figures come via press.
- No official 2026 suspension statistics.
