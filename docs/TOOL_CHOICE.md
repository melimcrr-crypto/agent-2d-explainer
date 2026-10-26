# چرا Manim؟ (و چرا بقیه را انتخاب نکردیم)

تاریخ بررسی: ۲۶ اکتبر ۲۰۲۶. ستارهها و مجوزها با GitHub REST API همان روز گرفته شدهاند.

## مسئله

سه قید سخت داشتیم:

1. **شخصیت ۲بعدی واقعی** — نه اسلایدشو. یعنی پلک زدن، نگاه کردن، لب خواندن،
   تکان خوردن دست و بدن.
2. **رندر توی GitHub Actions** — یعنی headless، قطعی (deterministic)، بدون
   نیاز به GPU یا سرویس پولی.
3. **فارسی/RTL** — شِیپینگ صحیح متن، زیرنویس، و گویندگی فارسی.

قید چهارم هم مهم بود: **عامل باید بتواند کدش را بنویسد** (agent-authorable).

## جدول مقایسه

| ابزار | ستاره | مجوز | شخصیت ۲بعدی | رندر CI | RTL | نتیجه |
| --- | --- | --- | --- | --- | --- | --- |
| **[Manim Community](https://github.com/ManimCommunity/manim)** | ۴۱٫۹k | **MIT** | ✅ وکتور، فریمبهفریم | ✅ عالی، Cairo، بدون مرورگر | ✅ Pango | **انتخاب شد** |
| [3b1b/manim (ManimGL)](https://github.com/3b1b/manim) | ۹۵٫۷k | MIT | ✅ | ⚠️ نیاز به OpenGL | ✅ Pango | برای شروع سنگینتر |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | ۷۳k | Apache-2.0 | ✅ HTML/SVG/GSAP/Lottie | ⚠️ Node 22+ و Chromium | ✅ CSS `dir=rtl` | نزدیکترین رقیب |
| [Remotion](https://github.com/remotion-dev/remotion) | ۶۷٫۹k | source-available | ✅ React | ⚠️ bundler + Chrome | ✅ | مجوز تجاری بالای ۳ نفر |
| [Revideo](https://github.com/midrender/revideo) | ۴٫۱k | MIT | ✅ TS generator | ✅ headless | ✅ | عالی، ولی شخصیتسازی دستی |
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | ۱۹٫۵k | MIT | ✅ generator | ❌ ادیتور تعاملی | ✅ | آخرین ریلیز پایدار ۲۰۲۴ |
| [Rive](https://rive.app/) + [rive-wasm](https://github.com/rive-app/rive-wasm) | ۱k | MIT (runtime) | ✅✅ حرفهایترین ریگینگ | ⚠️ ویرایشگر اختصاصی | ✅ | عالی ولی وابسته به ابزار بسته |
| [RaveAnima](https://github.com/vibecoderkz/raveanima) | ۱ | MIT | ✅ MCP + CLI | ⚠️ خیلی تازه | ? | آلفا، ریسک بالا |
| [Fanimate](https://github.com/toonittmedia/fanimate) | ۳ | Apache-2.0 | ✅ ریگ استخوانی | ⚠️ دسکتاپ Tauri | ? | alpha |
| [Lottie / lottie-web](https://github.com/airbnb/lottie-web) | ۳۲k | MIT | ✅ فقط پخش انیمیشن آماده | ✅ | ✅ | نیاز به ساخت انیمیشن در جای دیگر |
| [FFCreator](https://github.com/tnfe/FFCreator) | ۳٫۲k | MIT | ❌ اسلایدشو | ✅ | ⚠️ | آخرین کامیت ۲۰۲۴ |
| [Editly](https://github.com/mifi/editly) | ۵٫۶k | MIT | ❌ تدوین اعلامی | ✅ | ⚠️ | آخرین push مه ۲۰۲۵ |

## چرا Manim برنده شد

- **واقعاً وکتور و فریمبهفریم است.** `Housha` یک `VGroup` از دایرهها و
  مستطیلهای گرد است که با `stretch_to_fit_*`، `put_start_and_end_on` و
  `move_to` هر فریم بهروز میشود. این همان کاری است که After Effects میکند،
  منتها با کد و بدون کروم.
- **Pango شِیپینگ فارسی را خودش انجام میدهد.** بعد از `register_font()`
  دیگر نیازی به `arabic-reshaper` / `python-bidi` در لایهٔ انیمیشن نیست.
- **Cairo در CI بدون GPU کار میکند.** رندر ۶۰ ثانیه ۱۰۸۰p30 روی `ubuntu-22.04`
  فقط به Cairo/Pango و FFmpeg نیاز دارد. نمونهٔ موفق CI:
  [Pratyush061/manim-animations](https://github.com/Pratyush061/manim-animations).
- **MIT** — برخلاف Remotion (source-available) و Rive (ویرایشگر بسته).
- **بیشترین «قابلیت نوشته شدن توسط LLM»** را دارد؛
  [animate-anything](https://github.com/mdagnolops/animate-anything) دقیقاً
  روی همین ویژگی یک مهارت عامل ساخته است.
- **ساعت مطلق** (`self.renderer.time`) در اختیار ماست، برای همسانسازی لب
  با کلمات واقعی TTS.

## چرا HyperFrames را کنار گذاشتیم

HyperFrames از خیلی جهات جذابتر است: HTML/CSS بنویس، GSAP/Lottie/Three.js
را مستقیماً بگیر، مهارت رسمی برای Claude Code/Codex/Cursor دارد، Apache-2.0
است. اما:

- رندرش به **Node 22+ و headless Chrome** نیاز دارد (در CI یعنی `playwright
  install chromium` و ~۳۰۰MB اضافی).
- قطعیت بایت به بایت فقط در «Linux BeginFrame mode» تضمین شده.
- محدودیتهای سختی روی انیمیشن دارد (`paused: true`، بدون `Math.random`،
  بدون `repeat: -1`) که باید توی HTML رعایت شود.

[مقایسهٔ رسمی](https://github.com/heygen-com/hyperframes) ·
[مقایسهٔ ۲۰۲۶](https://snapcn.dev/remotion-alternatives)

**نتیجه:** برای ویدیوهای مارکتینگ/UI و تیمی که از قبل React/HTML کار میکند،
HyperFrames انتخاب اول است. ولی برای **یک انیمیشن آموزشی شخصیتمحور که باید
توی CI بدون مرورگر رندر شود**، Manim سادهتر و قابلاعتمادتر است. معماری
این ریپو طوری نوشته شده که اگر خواستی لایهٔ `src/` را با HyperFrames عوض
کنی، `tools/edit.py` و `build_voice.py` دستنخورده میمانند.

## لایهٔ تدوین: چرا `ffmpeg-skill`

[kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (MIT، آخرین
push اکتبر ۲۰۲۶) تنها ابزار تدوینی است که **مخصوص عاملها** طراحی شده: ۴۲ ابزار
typed، قرارداد ماشینخوان، `probe → dry-run/plan → render → verify`، و
`check.py` بهعنوان دروازهٔ تحویل پلتفرم. ما از فلسفهٔ آن در `tools/edit.py`
و `tools/qa.py` استفاده کردیم، و `check.py` واقعیاش را توی CI صدا میزنیم
(مرحلهٔ «Install the delivery-gate tool»).

سایر گزینههای بررسیشده: [veedstudio/open-edit](https://github.com/veedstudio/open-edit)
(Apache-2.0، خوب ولی GUIless و متمرکز بر ترنسکریپت)،
[KyaniteLabs/kinocut](https://github.com/KyaniteLabs/kinocut) (MCP محافظتشدها)،
[video-audio-mcp](https://github.com/misbahsy/video-audio-mcp) (سادهتر).

## صدا: چرا edge-tts

| گزینه | مزیت | عیب |
| --- | --- | --- |
| **edge-tts** | رایگان، بدون کلید، `fa-IR-DilaraNeural`، و مهمتر **WordBoundary** | آنلاین (ma کلیپها را کامیت میکنیم) |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) + `fa_IR` | آفلاین و قطعی | GPL-3، مدل ~۶۰MB، بدون word boundary |
| ElevenLabs / MiniMax MCP | کیفیت عالی | پولی، نیاز به کلید |
| Coqui TTS | قدیمی | آرشیوشده |

چون `WordBoundary` به ما **زمان تک تک کلمات** را میدهد، هم زیرنویس
کارائوکهای دقیق میسازیم و هم دهان شخصیت را با صدا سینک میکنیم. برای همین
edge-tts انتخاب شد و خروجیاش کامیت میشود تا CI کاملاً آفلاین باشد.

منابع بیشتر: [awesome-ai-video-editing](https://github.com/zealous1/awesome-ai-video-editing) ·
[awesome-video-agents](https://github.com/PhiloLabs/awesome-video-agents) ·
[animate-anything](https://github.com/mdagnolops/animate-anything)
