# myTrack plans page

`/mytrack/plans/` renders `website/plans.json`: the myTrack tiers, their functions and the rules between functions
(for example the Savings finder needs the station directory and a card function). The page script
(`static/js/plans.js`) reads those rules from the page, so it needs no other data.

The file is an export of myTrack's own catalogue, so the website and the app never disagree. To refresh it after
tiers, prices or functions change in myTrack (Admin, Tiers):

```bash
curl -fsSL https://fleet.mharetech.co.za/plans/catalogue.json -o website/plans.json
git add website/plans.json && git commit -m "Plans: refresh from myTrack"
```

then deploy as usual (`git pull` on the server, restart). Prices are whatever staff typed on the tier in myTrack;
a tier with no price shows "On request".
