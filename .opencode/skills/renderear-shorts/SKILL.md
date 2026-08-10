---
name: renderear-shorts
description: Guia el proceso de generar videos verticales 9:16 y dividirlos en partes para Shorts/Reels/TikTok, con CTA "like para la parte N", usando las convenciones ffmpeg correctas (render independiente, center-crop, upscale lanczos, ASS vertical, cortes en fin de capitulo).
---

## Que hace este skill

Guia la generacion de contenido vertical (9:16) para plataformas de video
corto, asegurando que los subtitulos se vean bien, que se corte en finales
de capitulo (no a mitad de frase), y que cada parte termine con el CTA
"like para la parte N".

## Regla de oro: render independiente, NO recortar el video 16:9

El video 9:16 se renderiza DIRECTAMENTE desde el gameplay con center-crop
de la franja vertical + upscale `lanczos`, y quema el ASS vertical (9:16).
NUNCA se recorta el video 16:9 ya renderizado (falla por geometria y los
subtitulos quedan mal posicionados).

## Pasos

### 1. Generar el ASS vertical (si no existe)

```bash
python src/generar_subtitulos_ass.py --procesar --vertical --idioma en
```

Produce `output/subtitulos_ass/<nombre>_9x16.ass` (PlayRes 1080x1920,
Montserrat 96, MarginV 900 centrado, karaoke amarillo).

### 2. Renderizar el video 9:16

```bash
python src/ensamblar_video.py --procesar --tambien-vertical
```

Esto genera ambos: `*_16x9.mp4` y `*_9x16.mp4`. El 9:16 usa:

```
crop=iw*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920:flags=lanczos,ass=filename='...9x16.ass'
```

### 3. Cortar en partes de ~5 min con CTA

```bash
python src/cortar_shorts.py --procesar --minutos 5 --idioma en
```

- Divide cada `*_9x16.mp4` en partes de ~5 min (`--minutos`).
- Los cortes se alinean a **finales de capitulo** del guion (si existe el
  .txt en `output/guiones_listos/`) y a pausas naturales entre subtitulos.
- Al final de cada parte agrega el **CTA "like para la parte N"**:
  - Overlay visual (PNG generado con Pillow)
  - Audio narrado (edge-tts, voz segun `--idioma`)
- Salida en `output/shorts/` con nombres `<nombre>_shorts_NNN.mp4`.

Para generar solo el CTA de una parte:
```bash
python src/generar_cta_parte.py --parte 1 --siguiente 2 --idioma es
```

## Verificacion rapida de un video

Extraer un frame para confirmar que los subtitulos se ven bien:
```powershell
$env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"
ffmpeg -ss 10 -i output/videos/mi_video_9x16.mp4 -frames:v 1 frame_check.png
```

## Errores comunes

- **`crop=1080:1920` falla**: ese crop es invalido sobre un video 1920x1080.
  Usar el render independiente de `ensamblar_video.py`.
- **Subtitulos invisibles**: el ASS debe tener `SecondaryColour` amarillo
  distinto del `PrimaryColour` blanco.
- **`fontsdir`**: va dentro del filtro `ass=...:fontsdir='ruta'`.
- **CTA sin audio**: verificar que edge-tts este instalado. El overlay PNG
  se genera igual aunque el audio falle.
- **Corte a mitad de frase**: el guion debe existir en `output/guiones_listos/`
  para que `cortar_shorts.py` detecte los finales de capitulo.
