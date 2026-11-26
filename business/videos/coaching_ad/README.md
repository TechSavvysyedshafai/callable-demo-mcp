# Coaching centre sample ad (20 s, 9:16)

Hook -> our real 3D explainer footage (conic sections, Le Chatelier) -> what the centre offers -> free demo class -> contact card.
Built free with Remotion + the explainer kit (music and sound effects made in code). QA 10/10.

To make it for a real centre: edit the EndCard in `src/Ad.tsx` (name, address, number, logo) and the three feature cards
to match what that centre actually offers (do not keep claims they cannot back up), then:
```
npx remotion render src/index.ts Ad out/silent.mp4 --browser-executable=/opt/pw-browsers/chromium
python3 ../explainer_kit/make.py script.md && python3 ../explainer_kit/qa.py .
```
`node_modules` is a link to the Dadi story project's install (run `npm install` here if it is missing).
