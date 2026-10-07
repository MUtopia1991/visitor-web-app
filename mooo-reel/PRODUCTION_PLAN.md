# مووو؛ یه لقمه، آشتی! — برنامه تولید (Kling 9:16)

خروجی: 1080×1920، ۳۶ ثانیه، ۱۲ شات × ۳ ثانیه. بدون دیالوگ (مثل تام و جری، جهانی). موسیقی بی‌کلام کارتونی ارکسترال. پایان: صدای گاو «مووووو».

## تصمیم‌های تأییدشده
- لیبل اصلی TIFF موجود نیست → مرجع محصول = `refs/product_lid.jpg` + `refs/product_open.jpg` (از شیت محصول).
- روال: ۱) ۱۲ فریم کلیدی عمودی → تأیید ۲) شات ۰۸ آزمون حفظ هویت → تأیید ۳) بقیه شات‌ها ۴) موسیقی + افکت + تدوین.
- صدا: بدون دیالوگ و نریشن؛ فقط افکت‌های کارتونی و «مووو» گاوی در پایان.
- موسیقی: ارکسترال کارتونی بی‌کلام (پیتزیکاتو + کلارینت/فلوت در تعقیب، سکوت در بوکشیدن، تم گرم آشتی، پایان کامل).

## ابزار و تنظیمات
| مرحله | ابزار | تنظیم |
|---|---|---|
| فریم کلیدی | Kling `image_to_image` / `kling-image-v3_0_omni` | `aspect_ratio=9:16`, `img_resolution=2k`, `imageCount=2` |
| ویدیو | Kling `image_to_video` / `kling-video-v3_0_omni` (فریم شروع + در صورت نیاز فریم پایان) | `aspect_ratio=9:16`, `resolution=1080p`, `duration=4` (۱ ثانیه هندل برای تدوین), `enable_audio=false` |
| موسیقی | ElevenLabs Music v2.5 (یا Google Lyria در صورت وجود کلید) | 36s، instrumental |
| افکت و «مووو» | ElevenLabs SFX v2 (یا Google AI Studio در صورت وجود کلید) | |
| تدوین | ffmpeg | 24fps، اصلاح رنگ، تیتر فارسی Vazirmatn، میکس −14 LUFS |

## ترتیب مرجع‌ها در هر فریم کلیدی
- 图片1 = پنل استوری‌بورد همان شات (`refs/panelNN.jpg`) — فقط ترکیب‌بندی و کنش
- 图片2 = شیت شخصیت‌ها (`refs/sheet1_characters`)
- 图片3 = شیت لوکیشن (`refs/sheet2_location`)
- 图片4 = درِ محصول (`refs/product_lid.jpg`) — فقط شات‌هایی که محصول دارند
- 图片5 = ظرف باز (`refs/product_open.jpg`) — فقط شات‌هایی که محصول دارند

### بلوک‌های ثابت پرامپت
**STYLE:** Original 2D hand-drawn cartoon, confident variable-width ink outlines, controlled cel shading, soft gouache painted background, warm morning sunlight, palette of teal, mustard, cream, warm wood and brand green. Full-bleed vertical 9:16 frame, no text, no captions, no panel borders, no watermark.

**FANDOGH:** the mouse from 图片2 — small warm-grey mouse, large round ears with dusty-pink inside, ivory muzzle and belly, small dark nose, thin curved tail, mustard-yellow neck scarf, animal paws.

**POF:** the cat from 图片2 — chubby pear-shaped burnt-orange tabby cat, cream muzzle and belly, expressive eyebrows, small ears, thick striped tail, teal bow tie, animal paws; standing height exactly 3× the mouse.

**MOOO:** the Mooo Labneh tub exactly as in 图片4 and 图片5 — green oval tub, blue Mooo logo with cow, "Labneh / لبنة" label; keep label, colors and proportions unchanged; dense white spreadable labneh.

**LOCATION:** the connected apartment from 图片3 — teal sofa living room on the left, kitchen doorway in the middle, wooden breakfast table by the window on the right.

## شات‌لیست

| # | زمان | فریم کلیدی (keyframe prompt — بعد از STYLE و بلوک‌ها) | حرکت (video prompt) | صدا |
|---|---|---|---|---|
| 01 | 0–3 | Recompose 图片1 vertically. Low wide angle on the living-room wooden floor and mustard rug. FANDOGH sprints screen-left→right in the lower third hugging a yellow cheese wedge with both paws, glancing back. POF leaps behind him in the upper half, angry comic face, dust puffs. Teal sofa in background. | Fast tracking chase left→right, mouse runs on 1s, cat bounds heavily behind, mouse glances back, whiskers nearly catch the cheese. Camera follows. | ضرب شروع، قدم ریز موش، قدم بم گربه |
| 02 | 3–6 | Low angle under the low wooden coffee table. FANDOGH zips under it holding the cheese; POF's belly is squeezed under the table edge, eyes bulging; cushions and magazines flying. | Mouse zips through; cat's belly gets stuck under the table edge, he squeezes, pops out with a boing; magazines and a cushion spin in the air. Furniture stays still. | «بویینگ» فنری |
| 03 | 6–9 | Near the kitchen doorway. A thin golden aroma ribbon curls to FANDOGH's nose; he brakes hard, feet planted, body leaning forward, cheese still in paws. POF blurred far behind. | Mouse slams the brakes, body overshoots half a step and snaps back, nose twitches twice following the golden aroma curl. | ترمز + قطع موسیقی، نیم‌ثانیه سکوت، دو بوکشیدن |
| 04 | 9–12 | Kitchen side, breakfast table in background. FANDOGH floats slightly off the floor following the golden aroma ribbon, eyes half-closed, tiny blissful smile, cheese in paws. | Mouse drifts dreamily forward on the aroma ribbon, nose leading, toes off the floor. Slow gentle camera drift. | فلوت/کلارینت، «هوم؟» |
| 05 | 12–15 | Breakfast table tabletop close-up: open MOOO tub with smooth white labneh in front, lid leaning behind facing camera, bread basket, tea glass, olives, cucumber and tomato. FANDOGH peeks over the table edge, eyes wide with delight. | Slow push-in on the product; mouse's head rises over the table edge, eyes sparkle; aroma curl rises from the labneh. Product label stays sharp and unchanged. | موسیقی روشن و گرم |
| 06 | 15–18 | Over-the-shoulder from behind FANDOGH on the table. He has just tossed the cheese backwards; the cheese wedge is stuck flat on POF's face; POF's eyes cross toward it, teal bow tie visible. | Mouse flicks the cheese over his shoulder; it lands softly on the cat's snout with a soft plop; cat freezes, eyes cross to look at it. No injury. | «پلپ» نرم، مکث، غرغر |
| 07 | 18–21 | FANDOGH mid-leap from a wooden chair onto the breakfast table toward bread and the MOOO tub; POF behind the table holding the cheese he just peeled off his face, grumpy. | Mouse springs from the chair onto the table in an arc; behind, the cat peels the cheese off his face and sets it aside. | پرش |
| 08 | 21–24 | On the table: FANDOGH turns and holds up a small piece of bread spread with white labneh toward POF; POF seated at the table, paw raised to grab, frozen mid-air, eyes moving from mouse to the bite. MOOO tub in foreground. | Cat's paw rises to grab, mouse spins and offers the bread bite; the paw freezes in mid-air; the cat's eyes shift from the mouse to the bite. | — |
| 09 | 24–27 | Close-up POF seated at the table taking a bite of the bread with labneh; eyes closed in bliss, eyebrows up, small dab of white labneh at the corner of his mouth; FANDOGH watching hopefully. | Cat hesitantly takes the bite, chews; eyebrows lift, eyes close, a big happy smile spreads, shoulders relax. | گاز + «ممم»، تم آشتی |
| 10 | 27–30 | POF on the chair, FANDOGH standing on the table, each eating their own bread with labneh, both laughing; MOOO tub and lid in front of frame. | Both chew and laugh; mouse points to the white dab at the corner of the cat's mouth; both giggle. Products stay still. | خنده |
| 11 | 30–33 | POF places a small wooden sign on the table showing a crossed-out cat-chasing-mouse pictogram (no words), holding his bread in the other paw; FANDOGH raises an eyebrow and nods; MOOO tub in front. | Cat sets the sign down with a tap; mouse raises an eyebrow and gives a satisfied nod. | تق تابلو + ضرب طنز |
| 12 | 33–36 | Product hero: open MOOO tub and lid large in the lower 60% of frame, bread with labneh in front, daisies; both friends smiling softly in the blurred background. Leave clean space at the top third for the Persian title. | Very slow push-in on the product; friends smile in soft focus; gentle light shimmer. Label stays sharp and unchanged. | پایان ملودی + «مووووو» گاوی |

نکات کنترلی هر شات: یک کنش اصلی؛ مبلمان ثابت؛ پنجه هیچ‌وقت داخل ظرف نمی‌رود؛ لبنه کش نمی‌آید؛ رشته طلایی = عطر، نه بخار؛ شخصیت سوم نداریم.

## تدوین
- برش هر کلیپ ۴ ثانیه‌ای به ۳ ثانیه (بهترین بخش)، کات روی ضرب، جهت حرکت چپ→راست حفظ شود.
- شات ۰۵ و ۱۲: در صورت تغییر لیبل، لایه ثابت لیبل از `product_lid.jpg` با ماسک روی ظرف کامپوزیت شود.
- تیتر شات ۱۲: «مووو؛ یه لقمه، آشتی!» با فونت Vazirmatn، در محدوده امن اینستاگرام (بالای ۲۵۰px و پایین ۴۰۰px خالی).
- ضرب‌های اصلی: گیرکردن گربه (~4s)، ترمز (~6.5s)، پلپ پنیر (~16s)، اولین گاز (~25s)، تق تابلو (~31s)، مووو (~34s).
- میکس: موسیقی −16dB زیر افکت‌ها، لودنس نهایی −14 LUFS، فید ۰٫۵ ثانیه آخر.
