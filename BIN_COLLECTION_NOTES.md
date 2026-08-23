# Waltham Forest bin collection dates - notes for a future standalone script

This was previously built as a feature of this app (a headless-browser scrape
that overlaid bin collection dates onto the magic mirror's calendar view) but
was removed because maintaining a Playwright/Chromium dependency inside this
app wasn't worth it for what it did. These are the findings from that work,
kept so a future **standalone** script (not part of this app) can pick the
problem up without re-doing the investigation.

The old implementation lived at `src/components/bin_collection/` and was
wired into `components/google_calendar/component.py`; it existed at commit
`7e32a5c` ("Refactor weather sparkline rendering and update dependencies" -
despite the name, that commit also added the bin collection feature) and
was removed in the very next commit, `dece548`. Run
`git show 7e32a5c:src/components/bin_collection/scraper.py` (and the
sibling `data.py`/`constants.py` in the same commit) for the full working
reference implementation of everything described below, including the
Playwright automation code itself.

## The goal (if built as a standalone script)

A script, run on its own schedule (cron/systemd timer, not part of this
app), that fetches the next bin collection dates for a specific address and
**writes them as events directly to a Google Calendar** - unlike the removed
app feature, which only overlaid dates onto the dashboard's own view without
touching the real calendar. Writing to Google Calendar needs the calendar
write scope (`https://www.googleapis.com/auth/calendar` - this app's
existing `google_calendar` component only requests `calendar.readonly`, see
`src/components/google_calendar/data.py`), a separate OAuth credential/token
flow from this app's, and its own idempotency: track which dates have
already been written (e.g. a small local state file keyed by date) so
re-running the script every few days doesn't create duplicate events.

## Why this isn't a simple API call

Waltham Forest Council's "Find My Bin Collection Dates" tool is an
AchieveForms/Firmstep form, not a documented API:

```
https://portal.walthamforest.gov.uk/AchieveForms/?mode=fill&consentMessage=yes&form_uri=sandbox-publish://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393/AF-Stage-8bf39bf9-5391-4c24-857f-0dc2025c67f4/definition.json&process=1&process_uri=sandbox-processes://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393&process_id=AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393
```

Under the hood, the form's own JavaScript calls a backend endpoint:

```
POST https://portal.walthamforest.gov.uk/apibroker/runLookup?id=<lookup-id>&sid=<session-id>...
```

with a large JSON body describing the full current form state. The specific
lookup that actually returns collection dates is `id=5e208cda0d0a0`, which
internally calls out to a third-party waste-management backend ("Whitespace
Work Software") using tokens `{whitespaceLiveURL}`, `{whitespaceUsername}`,
`{whitespacePassword}`, `{case_ref}`, `{db_id}`, `{inputUPRN}`.

The blocker: `sid`, `csrf_token`, and `case_ref` are **not present in the
static HTML** - they're only minted by the page's own JavaScript as it loads
(confirmed by fetching the page fresh and inspecting the HTML/cookies - no
token appeared anywhere static). There's no way to reach `runLookup`
directly with plain HTTP requests; it requires actually running the page's
JS, i.e. a real (or headless) browser.

## The approach that worked mechanically: Playwright

Drive a headless Chromium through the same steps a person would, then read
the result directly out of the page's own form fields rather than scraping
rendered text. This was validated end-to-end mechanically (form fields
found and filled correctly); the very last step (reading a successful
result) hit a `siteCollectionsSuccessFlag: false` from the council's own
backend during testing, most likely due to rate-limiting from repeated
manual API testing done earlier in that session from the same sandbox IP -
not a bug in the automation itself. It's not been proven to complete
successfully end-to-end from a real, non-flagged network.

Steps (all field ids confirmed against the real rendered form):

1. `page.goto(FORM_URL, wait_until="networkidle")`
2. The real form lives inside an iframe: `page.frame_locator("#fillform-frame-1")`
3. Fill the postcode: `frame.locator("#postcode_search").fill(postcode)`, then
   `.press("Tab")` to trigger the postcode lookup.
4. Wait for the address `<select>` to populate:
   `frame.locator("#YourAddress option", has_text=address_text)`. The
   dropdown is presented via **select2**, which hides the real `<select>`
   (`display: none`), so:
   - Wait with `state="attached"`, not the default `"visible"` (it never
     becomes visible).
   - Call `select_option(..., force=True)` - otherwise Playwright refuses to
     act on a non-visible element. Acting on the underlying `<select>`
     directly still fires the native `change` event the form's JS listens
     on, same as if the select2 UI had been clicked.
5. Selecting the address triggers the actual collection-dates lookup.
   Poll `frame.locator("#siteCollectionsSuccessFlag").input_value()` until
   it equals `"true"` (or time out - ~30s is a reasonable budget based on
   the ~4.5s the backend integration itself measured as taking in one
   direct test).
6. Read the result straight out of the field the site populates:
   `frame.locator("#binCollectionHTML").input_value()`. This is a hidden
   `<textarea>`'s live value (not rendered visible text), formatted like:
   ```html
   <div class="col-sm-3 col-md-3" style="text-align: center;">
       <h5>Food Waste Collection Service</h5>
       <img src="..." alt="Food Waste Collection Service" />
       <p>First collection: <br /><b>Tuesday 25 August<b></p>
   </div>
   ```
   Parse with a regex like `<h5>([^<]+)</h5>.*?<b>([^<]+)<b>` (DOTALL) to
   get `(service_name, date_text)` pairs.

## Parsing the result

- Dates are given with no year (e.g. "Tuesday 25 August") - infer the year
  by picking the nearest occurrence on or after "today" (try this year,
  then next year, take whichever is `>= today`).
- The site only ever returns the **next** collection date per waste stream,
  not a recurring schedule - so there are at most ~4 dates per scrape (one
  per category), not a calendar's worth.
- Category short names (BBC/council's own service names -> short label):
  - contains "food" -> **Food**
  - contains "garden" -> **Garden**
  - contains "recycling" -> **Recycling**
  - anything else (e.g. "Domestic Waste Collection Service") -> **Refuse**
- Merge same-date collections into a single calendar entry using these short
  names (e.g. "Food, Recycling, Refuse" on one date, "Garden" on another) -
  this was a specific requirement from the original feature request.

## Known-good values for this address

- Postcode: `E4 9RH`
- Address (must match the site's own picker text exactly): `24 Forest Glade, Chingford`
- UPRN (stable, from a captured real request - could be used as a shortcut
  if the postcode/address picker step ever proves unreliable, though it
  wasn't used this way in the removed implementation): `100022543098`

## Caution: don't hammer the live site

The council's backend appears to rate-limit or otherwise flag an IP after
repeated automated requests in a short window (this is what's suspected to
have caused the final validation failure during development). A standalone
script should:
- Run infrequently (every 3 days is plenty, since only the *next* date per
  stream is ever available anyway).
- Not be used as a manual testing target repeatedly in a short session -
  space out any debugging attempts.
