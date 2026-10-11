const pptxgen = require("pptxgenjs");
const QR = require("qrcode");
const path = require("path");
const D = __dirname;
const img = f => path.join(D, f);

const BG = "F1EBDF", INK = "26231F", ACC = "FF7A2F", QUIET = "5F5A52", FAINT = "9A9387", WHITE = "FFFFFF", TINT = "FAF6EE", PEACH = "FFF3EA";
const F = "Space Grotesk";
const URL = "https://deal-desk-production-7983.up.railway.app";

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.title = "Deal Desk";
  pres.theme = { headFontFace: F, bodyFontFace: F };

  const shadow = () => ({ type: "outer", color: "26231F", opacity: 0.12, blur: 12, offset: 3, angle: 90 });
  const title = (s, t, color = INK) => s.addText(t, { x: 0.5, y: 0.35, w: 9, h: 0.9, fontFace: F, fontSize: 28, bold: true, color, valign: "top", margin: 0, isTextBox: true });
  const eyebrow = (s, t) => s.addText(t.toUpperCase(), { x: 0.5, y: 0.12, w: 9, h: 0.25, fontFace: F, fontSize: 10, bold: true, color: ACC, charSpacing: 2, margin: 0, isTextBox: true });
  const source = (s, t, color = FAINT) => s.addText(t, { x: 0.5, y: 5.2, w: 9, h: 0.3, fontFace: F, fontSize: 9, color, margin: 0, valign: "bottom", isTextBox: true });
  const card = (s, x, y, w, h, fill = WHITE) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.18, fill: { color: fill }, line: { color: fill }, shadow: shadow() });

  // 1. Title
  let s = pres.addSlide(); s.background = { color: BG };
  s.addImage({ path: img("bull-s.png"), x: 5.6, y: 1.05, w: 3.9, h: 3.9 * 555 / 820 });
  s.addText("DEAL DESK", { x: 0.6, y: 1.35, w: 5.2, h: 0.9, fontFace: F, fontSize: 48, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("Ask a senior about a live deal.\nNobody knows it was you.", { x: 0.6, y: 2.3, w: 5.0, h: 1.0, fontFace: F, fontSize: 20, color: QUIET, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 3.65, w: 2.6, h: 0.45, rectRadius: 0.22, fill: { color: ACC }, line: { color: ACC } });
  s.addText("Live demo inside", { x: 0.6, y: 3.65, w: 2.6, h: 0.45, fontFace: F, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText("Talk to Users hackathon · San Francisco · Oct 10, 2026", { x: 0.6, y: 4.85, w: 6, h: 0.3, fontFace: F, fontSize: 11, color: FAINT, margin: 0, isTextBox: true });

  // 2. Big number (dark)
  s = pres.addSlide(); s.background = { color: INK };
  eyebrow(s, "The problem");
  title(s, "Most acquisitions miss the goals the buyer set for them", WHITE);
  s.addText("70–75%", { x: 0.5, y: 1.55, w: 6, h: 1.5, fontFace: F, fontSize: 96, bold: true, color: ACC, margin: 0, isTextBox: true });
  s.addText("of acquisitions fail to deliver their stated goals, across roughly 40,000 deals over 40 years¹", { x: 0.5, y: 3.1, w: 5.4, h: 0.8, fontFace: F, fontSize: 16, color: "E9E3D7", margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.3, y: 1.6, w: 3.2, h: 2.4, rectRadius: 0.18, fill: { color: "3A3631" }, line: { color: "3A3631" } });
  s.addText([
    { text: "The people closest to the work", options: { bold: true, color: WHITE, breakLine: true } },
    { text: "Analysts and associates build the models and read the documents, and they are the least likely to ask when something looks wrong.", options: { color: "D9D2C5" } },
  ], { x: 6.5, y: 1.75, w: 2.85, h: 2.1, fontFace: F, fontSize: 13, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 6 });
  source(s, "¹ Baruch Lev and Feng Gu, analysis of ~40,000 acquisitions, reported in Fortune, Nov 2024.", "8C857A");

  // 3. Chart: who feels awkward asking
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "Why people stay quiet");
  title(s, "Young staff are almost 3x as likely to feel awkward asking for help");
  card(s, 0.5, 1.35, 5.4, 3.65);
  s.addChart(pres.charts.BAR, [{ name: "Feel awkward asking for help", labels: ["Age 18–24", "Age 45–54"], values: [39, 14] }], {
    x: 0.7, y: 1.5, w: 5.0, h: 3.35, barDir: "col", chartColors: [ACC, "C9C1B3"], varyColors: true,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0\"%\"", dataLabelFontSize: 18, dataLabelFontBold: true, dataLabelColor: INK, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: QUIET, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 80, valAxisMaxVal: 50, valAxisMinVal: 0,
    showTitle: true, title: "Feel awkward asking their boss for help¹", titleFontSize: 12, titleColor: QUIET, titleFontFace: "+mn-lt",
  });
  card(s, 6.2, 1.35, 3.3, 1.7);
  s.addText([{ text: "26%", options: { fontSize: 36, bold: true, color: ACC, breakLine: true } },
             { text: "of leaders make their teams feel safe to speak up²", options: { fontSize: 13, color: INK } }],
    { x: 6.4, y: 1.45, w: 2.95, h: 1.5, fontFace: F, valign: "top", margin: 0, isTextBox: true });
  card(s, 6.2, 3.3, 3.3, 1.7);
  s.addText([{ text: "#1", options: { fontSize: 36, bold: true, color: ACC, breakLine: true } },
             { text: "Feeling safe to speak up was the top trait of Google's best teams, out of 180 studied³", options: { fontSize: 13, color: INK } }],
    { x: 6.4, y: 3.4, w: 2.95, h: 1.5, fontFace: F, valign: "top", margin: 0, isTextBox: true });
  source(s, "¹ UK workplace survey, 2012 (BHP). ² McKinsey Global Survey, 2021. ³ Google Project Aristotle, 2012–2014.");

  // 4. $2.5B
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "What bankers do instead");
  title(s, "Bankers already go around official channels, and regulators fine them");
  s.addText("$2.5B+", { x: 0.5, y: 1.55, w: 4.6, h: 1.3, fontFace: F, fontSize: 80, bold: true, color: ACC, margin: 0, isTextBox: true });
  s.addText("in SEC and CFTC fines since Dec 2021 for work talk on WhatsApp and texts that firms never recorded¹", { x: 0.5, y: 2.9, w: 4.4, h: 0.9, fontFace: F, fontSize: 15, color: INK, margin: 0, isTextBox: true });
  card(s, 5.4, 1.5, 4.1, 3.4);
  const rows = [["30+ firms fined", "including JPMorgan, Goldman Sachs and Citi"], ["Private chats are where the real questions go", "because they feel safe"], ["Deal Desk keeps the safety", "and adds a sealed record for compliance"]];
  rows.forEach(([a, b], i) => {
    const y = 1.75 + i * 1.0;
    s.addShape(pres.shapes.OVAL, { x: 5.65, y, w: 0.42, h: 0.42, fill: { color: i === 2 ? ACC : INK }, line: { color: i === 2 ? ACC : INK } });
    s.addText(String(i + 1), { x: 5.65, y, w: 0.42, h: 0.42, fontFace: F, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { color: QUIET } }], { x: 6.25, y: y - 0.06, w: 3.1, h: 0.85, fontFace: F, fontSize: 13, color: INK, valign: "top", margin: 0, isTextBox: true });
  });
  source(s, "¹ InvestmentNews and Bloomberg reporting on SEC/CFTC recordkeeping settlements, Dec 2021 – Aug 2023.");

  // 5. How it works (flow)
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "How it works");
  title(s, "A junior asks, two matched seniors answer, and identities stay hidden");
  const steps = [["Attach a deal", "Pick it from the firm's deal database, with its files"], ["Names become codenames", "“Northwind” becomes “Project Falcon (Buyer)” before anyone reads it"], ["Routed to 2 seniors", "Matched by deal type and sector"], ["Answer comes back", "Bottom line, their words, why, and what to watch"]];
  const W = 2.0, G = 0.33;
  steps.forEach(([a, b], i) => {
    const x = 0.5 + i * (W + G);
    card(s, x, 1.55, W, 2.55, i === 1 ? PEACH : WHITE);
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 1.75, w: 0.5, h: 0.5, fill: { color: ACC }, line: { color: ACC } });
    s.addText(String(i + 1), { x: x + 0.2, y: 1.75, w: 0.5, h: 0.5, fontFace: F, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: a, options: { bold: true, fontSize: 15, breakLine: true } }, { text: b, options: { fontSize: 12, color: QUIET } }], { x: x + 0.2, y: 2.4, w: W - 0.4, h: 1.6, fontFace: F, color: INK, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 4 });
    if (i < 3) s.addText("→", { x: x + W, y: 2.55, w: G, h: 0.5, fontFace: F, fontSize: 18, bold: true, color: ACC, align: "center", valign: "middle", margin: 0, isTextBox: true });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 4.35, w: 9, h: 0.6, rectRadius: 0.18, fill: { color: INK }, line: { color: INK } });
  s.addText([{ text: "Everyone sees only an anonymous handle and a level.  ", options: { color: WHITE, bold: true } }, { text: "Compliance keeps a sealed copy it can open if regulators ask.", options: { color: "D9D2C5" } }],
    { x: 0.75, y: 4.35, w: 8.6, h: 0.6, fontFace: F, fontSize: 13, valign: "middle", margin: 0, isTextBox: true });

  // 6. Screenshot: ask
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "The product");
  title(s, "A junior attaches the deal and asks in plain words");
  const aw = 5.1, ah = aw * 1155 / 1635;
  s.addImage({ path: img("crop-ask.jpg"), x: 0.5, y: 1.55, w: aw, h: ah, rounding: false, shadow: shadow() });
  s.addText([
    { text: "Deal database", options: { bold: true, breakLine: true } }, { text: "10 deals: mergers, LBOs, spin-offs, hostile bids, earnings events", options: { color: QUIET, breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "Files come along", options: { bold: true, breakLine: true } }, { text: "Term sheet, model notes, timeline, or the junior's own file", options: { color: QUIET, breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "The junior sees what seniors will see", options: { bold: true, breakLine: true } }, { text: "An anonymous handle and level, never a name", options: { color: QUIET } },
  ], { x: 6.0, y: 1.6, w: 3.5, h: 3.5, fontFace: F, fontSize: 13, color: INK, valign: "top", margin: 0, isTextBox: true });

  // 7. Screenshot: result
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "The answer");
  title(s, "Seniors reply in plain words, and the junior gets a structured answer");
  const rh = 3.85, rw = rh * 1635 / 1395;
  s.addImage({ path: img("crop-result.jpg"), x: 9.5 - rw, y: 1.45, w: (rh - 0.1) * 1635 / 1395, h: rh - 0.1, shadow: shadow() });
  s.addText([
    { text: "Formatted like a Sense AI result", options: { bold: true, breakLine: true } }, { text: "Bottom line, quotes, why, watch-outs", options: { color: QUIET, breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "Seniors write normally", options: { bold: true, breakLine: true } }, { text: "Claude turns a quick reply into a clear answer", options: { color: QUIET, breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "Two views per question", options: { bold: true, breakLine: true } }, { text: "A summary shows where the seniors agree", options: { color: QUIET } },
  ], { x: 0.5, y: 1.55, w: 3.6, h: 3.6, fontFace: F, fontSize: 13, color: INK, valign: "top", margin: 0, isTextBox: true });

  // 8. People already use anonymity
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "Demand");
  title(s, "Professionals already use anonymous channels at work");
  const stats = [["7M+", "verified professionals use Blind, an anonymous work app most popular in tech, finance and consulting¹"], ["53%", "of 28,747 professionals say waiting on answers interrupts their work²"], ["49%", "often answer questions they have already answered before²"]];
  stats.forEach(([n, t], i) => {
    const x = 0.5 + i * 3.1;
    card(s, x, 1.55, 2.8, 3.1);
    s.addText(n, { x: x + 0.25, y: 1.8, w: 2.3, h: 0.9, fontFace: F, fontSize: 44, bold: true, color: ACC, margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.25, y: 2.8, w: 2.3, h: 1.7, fontFace: F, fontSize: 13, color: INK, valign: "top", margin: 0, isTextBox: true });
  });
  source(s, "¹ Blind company blog; Fortune, Apr 2022. ² Stack Overflow Developer Survey 2024, professional developers.");

  // 9. Tester quotes (real, from our Sense AI interview)
  s = pres.addSlide(); s.background = { color: BG };
  eyebrow(s, "What testers told us");
  title(s, "Finance testers worry about names leaking and about IT approval");
  card(s, 0.5, 1.45, 4.35, 2.4);
  s.addText([{ text: "“It was mentioning names, and it's not supposed to mention names in that summary.”", options: { italic: true, fontSize: 16, breakLine: true } },
             { text: "Tester, on an AI summary at work", options: { fontSize: 11, color: QUIET } }], { x: 0.75, y: 1.65, w: 3.85, h: 2.05, fontFace: F, color: INK, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 10 });
  card(s, 5.15, 1.45, 4.35, 2.4);
  s.addText([{ text: "“to use a new application or artificial intelligence, they have to go through IT. And IT has to approve it”", options: { italic: true, fontSize: 16, breakLine: true } },
             { text: "Same tester, on adopting new tools", options: { fontSize: 11, color: QUIET } }], { x: 5.4, y: 1.65, w: 3.85, h: 2.05, fontFace: F, color: INK, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 10 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 4.1, w: 9, h: 0.85, rectRadius: 0.18, fill: { color: PEACH }, line: { color: PEACH } });
  s.addText([{ text: "What we built in response: ", options: { bold: true } }, { text: "client names become codenames before any senior reads a question, and Deal Desk runs inside the bank with a sealed record for compliance." }],
    { x: 0.75, y: 4.1, w: 8.5, h: 0.85, fontFace: F, fontSize: 13, color: INK, valign: "middle", margin: 0, isTextBox: true });
  source(s, "Sense AI phone interview with a finance tester, Oct 10, 2026.");

  // 10. Close (dark) with QR
  s = pres.addSlide(); s.background = { color: INK };
  const qr = await QR.toDataURL(URL, { margin: 1, width: 600, color: { dark: "#26231F", light: "#FFFFFF" } });
  s.addText("TRY IT NOW", { x: 0.6, y: 1.2, w: 5.5, h: 0.8, fontFace: F, fontSize: 40, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Log in as a junior in one tab and a senior in another. Ask, answer, and watch the result come back.", { x: 0.6, y: 2.1, w: 5.2, h: 0.9, fontFace: F, fontSize: 16, color: "D9D2C5", margin: 0, isTextBox: true });
  s.addText("deal-desk-production-7983.up.railway.app", { x: 0.6, y: 3.25, w: 5.6, h: 0.4, fontFace: F, fontSize: 14, bold: true, color: ACC, margin: 0, isTextBox: true, hyperlink: { url: URL } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.6, y: 1.05, w: 2.9, h: 2.9, rectRadius: 0.18, fill: { color: WHITE }, line: { color: WHITE } });
  s.addImage({ data: qr.replace("data:", ""), x: 6.8, y: 1.25, w: 2.5, h: 2.5 });
  s.addText("Scan to open Deal Desk", { x: 6.6, y: 4.1, w: 2.9, h: 0.3, fontFace: F, fontSize: 11, color: "D9D2C5", align: "center", margin: 0, isTextBox: true });

  await pres.writeFile({ fileName: path.join(D, "..", "Deal-Desk.pptx") });
  console.log("written");
})();
