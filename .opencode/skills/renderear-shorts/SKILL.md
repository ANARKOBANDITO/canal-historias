---
name: renderear-shorts
description: Guia el proceso de generar videos verticales 9:16 y dividirlos en clips para Shorts/Reels/TikTok, con las convenciones ffmpeg correctas (render independiente, center-crop, upscale lanczos, ASS vertical).
---

## Que hace este skill

Guia la generacion de contenido vertical (9:16) para plataformas de video
corto, asegurando que los subtitulos se vean bien y no se corten.

## Regla de oro: render independiente, NO recortar el video 16:9

El video 9:16 se renderiza DIRECTAMENTE desde el gameplay con center-crop
de la franja vertical + upscale `lanczos`, y quema el ASS vertical (9:16).
NUNCA se recorta el video 16:9 ya renderizado (falla por geometria y los
subtitulos quedan mal posicionados).

## Pasos

### 1. Generar el ASS vertical (si no existe)

```bash
python src/generar_subtitulos_ass.py --procesar --vertical
```

Produce `output/subtitulos_ass/<nombre>_9x16.ass` con:
- PlayRes 1080x1920
- Fuente Montserrat-Bold 44
- MarginV 250 (subtitulos en ~78% del alto)
- Karaoke `\k` con SecondaryColour amarillo

### 2. Renderizar el video 9:16

```bash
python src/ensamblar_video.py --procesar --tambien-vertical
```

Esto genera ambos: `*_16x9.mp4` y `*_9x16.mp4`. El 9:16 usa:

```
crop=iw*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920:flags=lanczos,ass=filename='...9x16.ass'
```

### 3. Cortar en clips

```bash
python src/cortar_shorts.py --procesar
```

Divide cada `*_9x16.mp4` en clips de ~2 min. Los cortes se alinean a las
pausas naturales entre subtitulos (finales de eventos Dialogue del ASS)
para no cortar a mitad de frase.

## Verificacion rapida de un video

Extraer un frame para confirmar que los subtitulos se ven bien:
```powershell
$env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"
ffmpeg -ss 10 -i output/videos/mi_video_9x16.mp4 -frames:v 1 frame_check.png
```

## Errores comunes

- **`crop=1080:1920` falla**: ese crop es invalido sobre un video 1920x1080.
  Usar el render independiente de `ensamblar_video.py` (crop de gameplay a
  franja 9:16 + scale a 1080x1920).
- **Subtitulos invisibles**: el ASS debe tener `SecondaryColour` amarillo
  distinto del `PrimaryColour` blanco; si ambos son iguales el karaoke no se ve.
- **`fontsdir`**: va dentro del filtro `ass=...:fontsdir='ruta'`, no como
  opcion global.
