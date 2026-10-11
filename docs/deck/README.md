# Deal Desk pitch deck

Builds `docs/Deal-Desk.pptx` (10 slides, Space Grotesk, cream/charcoal/orange).

```
cd docs/deck
npm install
npm run build
```

- Edit slide text, stats and sources in `build.js`.
- `crop-ask.jpg` / `crop-result.jpg` are app screenshots; `shots.py` retakes them from http://localhost:8080/desk/ (needs Python Playwright), then crop them to the middle column.
- To present: drag `Deal-Desk.pptx` into Google Drive and choose File → Save as Google Slides.
