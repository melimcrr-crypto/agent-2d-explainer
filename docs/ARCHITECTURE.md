# معماری خط لوله

```
                          ┌──────────────────────────┐
                          │     storyboard.json      │  تک منبع حقیقت
                          │  ۶ صحنه · 60.0s · پالت   │
                          └────────────┬─────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌────────────────┐          ┌────────────────────┐        ┌────────────────────┐
│ tools/         │          │ tools/             │        │ src/main.py        │
│ build_voice.py │          │ build_music.py     │        │ (Manim CE)         │
│                │          │                    │        │                    │
│ edge-tts       │          │ numpy:             │        │ ExplainerScene     │
│ fa-IR-Dilara   │          │  Am7-F-G-Em7 pad  │        │  ├ Housha (2D)     │
│ + WordBoundary │          │  sub pulse         │        │  ├ props/diagrams  │
│                │          │  bell arpeggio     │        │  ├ Beat budgets    │
│ ▼              │          │  fades             │        │  └ updater(t)      │
│ voice_*.mp3 ★  │          │                    │        │                    │
│ words.json  ★  │          └─────────┬──────────┘        └─────────┬──────────┘
│ mix.json    ★  │                    │                              │
│ fa.ass      ★  │                    │                    silent.mp4 (1080p30)
│ fa.srt      ★  │                    │                              │
│ visemes.json★  │◄───────────────────┼───── لب شخصیت با تایم واقعی ──┘
└───────┬────────┘                    │                              │
        │                            │                              │
        ▼                            ▼                              ▼
   build/voice.wav            build/music.wav            build/media/.../silent.mp4
        │                            │                              │
        └────────────────┬───────────┴──────────────────────────────┘
                         ▼
              ┌───────────────────────────────┐
              │        tools/edit.py          │
              │  FFmpeg filter_complex:       │
              │  • ass=fa.ass:shaping=complex│  ← زیرنویس کارائوکه RTL
              │  • sidechaincompress         │  ← ducking موسیقی زیر صدا
              │  • amix + loudnorm -14 LUFS  │
              │  • eq + fade in/out + trim   │
              └───────────────┬───────────────┘
                              ▼
              rendered/explainer-1080p.mp4
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   720p.mp4            vertical.mp4           preview.gif / contact-sheet.png
                              │
                              ▼
              ┌───────────────────────────────┐
              │         tools/qa.py           │
              │  ffprobe · loudnorm measure   │
              │  ffmpeg-skill check.py        │
              │  caption-check.png            │
              └───────────────┬───────────────┘
                              ▼
                        rendered/qa.json

★ = کامیت شده → CI کاملاً آفلاین و تکرارپذیر است
```

## نکات طراحی

### ۱. چرا یک صحنهٔ پیوسته (نه ۶ فایل جدا)؟

`src/main.py` یک `Scene` واحد ۶۰ ثانیهای است. پراپها محو میشوند ولی شخصیت
همیشه روی صحنه است. مزایا: نیازی به `concat`/`xfade` و همگامسازی صدای جداگانه
نداریم، و حرکات ثانویه (تنفس، پلک) هیچوقت قطع نمیشود.

### ۲. همگامسازی (Sync)

- `self.renderer.time` ساعت مطلق فیلم است (نه `dt` جمعشده — آن درift میکند).
- `Beat` در انتهای هر صحنه تا رسیدن ساعت به `start + duration - 0.35` صبر
  میکند؛ بنابراین گردکردن فریمهای Manim در هر `play()` انباشته نمیشود.
- `captions/visemes.json` (از `WordBoundary`) مستقیماً `Housha.tick()` را
  تغذیه میکند: دهان فقط وقتی باز میشود که واقعاً کلمهای در حال پخش است.

### ۳. چرا CI آفلاین است؟

TTS یک سرویس شبکهای است و نمیتواند تضمین کند که فردا همان بایت را بدهد.
پس MP3ها و تمام فایلهای زمانبندی **کامیت میشوند**. CI فقط میکس میکند،
رندر میکند و تدوین میکند. `python tools/build_voice.py` (بدون `--offline`)
فقط وقتی لازم است که نقلقول عوض شود.

### ۴. چرا `shaping=complex`؟

`subtitles` و `ass` در FFmpeg بهطور پیشفرض از shaper سادهٔ FriBidi استفاده
میکنند که متن RTL را بههم میریزد. فیلتر `ass` گزینهٔ `shaping=complex`
دارد (فقط در بیلدهایی که libass با HarfBuzz ساخته شده). به همین دلیل CI
یک FFmpeg استاتیک پین میکند و `shaping_supported()` مسیر جایگزین را چک میکند.

### ۵. دروازهٔ کیفیت

`tools/qa.py` فقط به نیّت ما اعتماد نمیکند؛ پیکسلها و صدای واقعی را چک
میکند: مدت، رزولوشن، fps، کدک، `pix_fmt`، وجود استریم صدا، `input_i`
(بلندی یکپارچه) و `input_tp` (پیک واقعی). علاوه بر این `check.py` از
`ffmpeg-skill` را روی پروفایل `youtube` اجرا میکند.

## برای عاملها

[`AGENTS.md`](../AGENTS.md) و [`SKILL.md`](../SKILL.md) را ببین. تمام
تصمیمها در کد/JSON است، پس diff شدنی، review شدنی و قابل برگشت است.
