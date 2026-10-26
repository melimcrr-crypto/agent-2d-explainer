# AGENTS.md — قرارداد کار برای ایجنتها

این فایل برای **عاملهای کدنویس** نوشته شده (Claude Code، Codex، Cursor، Gemini CLI، …).
قبل از تغییر چیزی این را بخوان.

## هدف ریپو

تولید یک ویدیوی آموزشی **۶۰ ثانیهای، فارسی، RTL، ۲بعدی** با یک شخصیت وکتوری،
گویندگی، زیرنویس کارائوکه، موسیقی و تدوین نهایی — **بهصورت کامل در GitHub Actions**.

## قانون طلایی

> `storyboard.json` تک منبع حقیقت است. اگر متن/زمان/رنگی را عوض کردی،
> دوباره `make voice` (فقط آنلاین) و سپس `make render` بزن.
> هیچ تایمینگی را داخل `src/main.py` هاردکد نکن.

## جایی که باید تغییر بدهی

| میخواهی… | برو به |
| --- | --- |
| متن گویندگی / عنوان صحنه / مدت صحنهها عوض شود | `storyboard.json` → `python tools/build_voice.py` → `make render` |
| ظاهر کاراکتر عوض شود | `src/character.py` |
| حرکت چشم/لب/دست عوض شود | `Housha.tick()` در `src/character.py` |
| دیاگرام/پراپ جدید اضافه شود | `src/props.py` + یکی از `sc_*` در `src/main.py` |
| رنگ/فونت/پالت | `storyboard.json` → `palette` و `src/config.py` |
| زیرنویس (استایل ASS) | `ASS_HEADER` در `tools/build_voice.py` |
| موسیقی | `CHORDS` و `build()` در `tools/build_music.py` |
| تدوین نهایی (گرید، داکینگ، LUFS، خروجیها) | `tools/edit.py` |
| دروازهٔ کیفیت | `tools/qa.py` |

## دستورها

```bash
make preview   # سریع: 480p15، بدون vertical/GIF — همیشه اول این را بزن
make render    # کامل: 1080p30، دقیقاً همان چیزی که CI اجرا میکند
make voice     # فقط وقتی narration عوض شده (نیاز به اینترنت)
make offline   # ساخت مجدد voice.wav/ASS/SRT از کلیپهای کامیتشده (آفلاین)
make qa        # فقط QA روی rendered/
```

## بایدها و نبایدها

1. **مدت کل = ۶۰٫۰ ثانیه.** `Beat` در `src/main.py` برای هر صحنه بودجهٔ زمانی
   دارد. عوض کردن `duration` صحنهها بدون عوض کردن `start` صحنههای بعدی،
   تدوین را خراب میکند. جمع `duration`ها و پیوستگی `start`ها را چک کن.
2. **مختصات کاراکتر:** `Housha` یک بار `scale/move_to` میشود و بعد از آن
   `_capture()` مختصات world-space ذخیره میکند. **هرگز** در `tick()` از
   مختصات local استفاده نکن — قطعات کاراکتر از هم جدا میشوند.
3. **چرخش/Scale submobjectها:** `become()` در updater ممنوع (کند و ناپایدار).
   فقط `stretch_to_fit_*` + `move_to` روی anchorهای captureشده.
4. **Updaters و `add/remove`:** داخل updater هیچوقت `self.add()`/`self.remove()`
   نکن (لیست mobjects موقع پیمایش تغییر میکند). فقط یک `Dot` نامرئی بهعنوان
   driver اضافه کن و از `self.renderer.time` بهعنوان ساعت مطلق استفاده کن.
5. **RTL:** متن Manim از Pango رد میشود (reshape دستی نکن). زیرنویس ASS
   حتماً `shaping=complex` میخواهد. Pillow قدیمی (بدون Raqm) متن را دوبار
   برعکس میکند — این پروژه از Pillow برای متن استفاده نمیکند.
6. **TTS:** `edge-tts` کلمات را `WordBoundary` میدهد (واحد `offset` = ۱۰۰ns).
   اگر صدای یک صحنه از بودجه بیشتر شد، `RATE_LADDER` خودکار سریعتر میکند؛
   بهتر است متن را کوتاه کنی تا گوینده عجولهای نشود.
7. **CI آفلاین است.** کلیپهای `assets/audio/voice_*.mp3` و
   `captions/mix.json + words.json` را کامیت کن. اگر کلیپی پاک شد،
   `tools/render.py` شکست میخورد.
8. **توکن/سیکرت:** هیچ کلیدی داخل فایلها، workflow یا git history نگذار.
   CI فقط از `GITHUB_TOKEN` خود گیت هاب برای کامیت خروجیها استفاده میکند.
9. **ffmpeg:** `ffmpeg_binaries()` ابتدا `FFMPEG_BIN`/`FFPROBE_BIN`، بعد سیستم،
   بعد static-ffmpeg را امتحان میکند. برای `ass` حتماً بیلدی لازم است که
   `--enable-libass --enable-libharfbuzz` داشته باشد.

## چکلیست قبل از push

- [ ] `make preview` بدون خطا تمام شد
- [ ] `python tools/qa.py` هیچ FAIL نداد
- [ ] `rendered/caption-check.png` را باز کردی و فارسی درست شِیپ شده
- [ ] `rendered/contact-sheet.png` شش صحنه را نشان میدهد و متنها از کادر بیرون نزدند
- [ ] `storyboard.json` معتبر است (`python -m json.tool storyboard.json`)
- [ ] هیچ فایل `build/` یا توکنی استیج نشده
