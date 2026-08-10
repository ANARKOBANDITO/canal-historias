# RESUMEN COMPLETO DEL PROYECTO `canal-historias`

> Actualizado al cierre de la sesion del 07/08. Este documento es la fuente de
> verdad para retomar el proyecto en una terminal NUEVA. Leo junto con
> `NEXT_STEPS.md` (pendientes) y `AGENTS.md` (convenciones).

---

## 1. QUE ES

Pipeline automatizado que genera **guiones narrados en espanol** estilo
"historias de reddit" (confesiones en primera persona) y los convierte en
**video**: audio (TTS local Kokoro) + subtitulos karaoke (ASS) + gameplay de
fondo. Destino: YouTube (16:9) y TikTok/Shorts/Reels (9:16).

**Estado actual:** pipeline completo y probado de punta a punta. Fase de
subtitulos terminada con el estilo visual correcto. Pendiente: descargar
gameplay real y decidir motor TTS de produccion.

---

## 2. ESTRUCTURA DEL REPOSITORIO

```
canal-historias/
├── AGENTS.md                  # Convenciones y flujo para el agente
├── NEXT_STEPS.md              # Pendientes agendados (leer primero al retomar)
├── RESUMEN_PROYECTO.md        # Este documento
├── requirements.txt
├── .opencode/
│   ├── agents/
│   │   ├── scriptwriter.md    # Subagente fase guiones
│   │   └── video-producer.md  # Subagente fase audio/video
│   ├── rules/
│   │   ├── espanol.md
│   │   ├── deepseek-api.md
│   │   ├── ffmpeg-windows.md
│   │   └── kokoro-tts.md
│   └── skills/
│       ├── recover-batch/     # Recuperar lote de guiones interrumpido
│       ├── recover-video/     # Recuperar fase video interrumpida
│       └── renderear-shorts/  # Guia 16:9 -> 9:16
├── src/
│   ├── utilidades.py              # normalizar_nombre() (compartido)
│   ├── generar_temas.py           # Premisas DeepSeek + deduplicacion
│   ├── generar_historia.py        # Guion (gancho+esquema+capitulos)
│   ├── generar_lote.py            # Batch de guiones
│   ├── variacion_narrativa.py     # Rota gancho/desenlace
│   ├── firma_editorial.py         # Sello de cierre del canal
│   ├── banco_temas.py             # Dedupe de temas (vectores locales)
│   ├── buscar_gameplay.py         # Busca gameplay en YouTube y lo agrega a gameplay_urls.txt
│   ├── descargar_gameplay.py      # Descarga gameplay (yt-dlp + aria2c + .txt)
│   ├── generar_audio.py           # Audio Kokoro (em_alex/ef_dora)
│   ├── generar_subtitulos_ass.py  # whisper -> ASS karaoke
│   ├── ensamblar_video.py         # Audio+ASS+gameplay -> video 16:9/9:16
│   ├── cortar_shorts.py           # Video 9:16 -> clips
│   ├── estadisticas.py            # Dashboard
│   ├── validar_guiones.py         # QA pre-locucion
│   ├── limpiar_banco.py           # Gestiona banco de temas
│   ├── renombrar_guiones.py       # Normaliza nombres
│   ├── verificar_entorno.py       # Chequea dependencias
│   ├── pipeline_completo.py       # Todo el flujo en cascada
│   └── limpiar_output.py          # Borra temporales
├── data/
│   ├── temas_pendientes.txt       # Cola de temas
│   ├── temas_usados.txt           # Registro historico
│   ├── banco_temas.pkl            # Vectores de temas usados
│   └── gameplay_urls.txt          # Lista de URLs de gameplay (una por linea)
├── output/
│   ├── guiones_listos/            # 12 guiones (.txt normalizados 001_...)
│   ├── audio/                     # Locuciones .mp3 (vacio tras limpieza)
│   ├── subtitulos_ass/            # ASS karaoke 16:9 y 9:16 (vacio tras limpieza)
│   ├── videos/                    # Videos finales (vacio tras limpieza)
│   └── shorts/                    # Clips para Shorts (vacio tras limpieza)
└── storage/
    ├── raw_gameplay/              # Gameplay loops (vacio, por descargar)
    ├── kokoro-v1.0.onnx           # Modelo Kokoro (310 MB)
    ├── voices-v1.0.bin            # Voces Kokoro (27 MB)
    └── Montserrat-Bold.ttf        # Fuente de subtitulos
```

---

## 3. FLUJO PRINCIPAL

```
1. python src/generar_temas.py --cantidad 10      -> data/temas_pendientes.txt
2. python src/generar_lote.py --genero hombre --minutos 20
                                                   -> output/guiones_listos/*.txt
3. python src/buscar_gameplay.py --libre --guardar "no copyright gameplay"
                                                   -> data/gameplay_urls.txt (solo URLs)
4. python src/descargar_gameplay.py data/gameplay_urls.txt  -> storage/raw_gameplay/
5. python src/generar_audio.py --cantidad 5        -> output/audio/*.mp3 (Kokoro)
6. python src/generar_subtitulos_ass.py --procesar            -> ASS 16:9
7. python src/generar_subtitulos_ass.py --procesar --vertical -> ASS 9:16
8. python src/ensamblar_video.py --procesar --tambien-vertical
                                                   -> output/videos/*_16x9.mp4 y *_9x16.mp4
9. python src/cortar_shorts.py --procesar          -> output/shorts/
```

**Alternativa en un comando:**
`python src/pipeline_completo.py --cantidad 5 --genero hombre`

**Diagnostico del entorno:**
`python src/verificar_entorno.py`

---

## 4. CONVENCIONES CRITICAS

### DeepSeek (guiones)
- Modelo `deepseek-v4-flash`, base URL `https://api.deepseek.com/v1`.
- SIEMPRE `extra_body={"thinking": {"type": "disabled"}}` en cada llamada.
- max_tokens minimos: gancho 200, premisas 400, capitulos 2000, esquemas 4000.
- API key: `DEEPSEEK_API_KEY`.

### Audio (Kokoro / edge-tts / Chatterbox)
- **Kokoro (CPU local):** voces `em_alex` (hombre) / `ef_dora` (mujer). Modelos en `storage/`.
- **edge-tts (nube, rapido):** `--motor edge`, voces `es-MX-JorgeNeural` / `es-MX-DaliaNeural`.
- **Chatterbox (GPU, voice cloning):** `--motor chatterbox --idioma en`. Multilingual V3,
  500M params, ~6-8 GB VRAM. Necesita voces de referencia en `storage/voces/`.
  Generar con `generar_referencias.py`.

### Subtitulos (ASS karaoke) - ESTILO FINAL
- Montserrat-Bold, blanco + borde negro, karaoke `\k` por palabra (activa en amarillo).
- **16:9**: PlayRes 1920x1080, fuente 48, frases ~2.5s (cierra por tiempo,
  `SEGUNDOS_LINEA_169=2.5`), MarginV 80, Alignment 2 (abajo).
- **9:16**: PlayRes 1080x1920, fuente 96, 1-2 palabras por linea, MarginV 900
  (centrado ~47% alto), Alignment 5 (centro).
- `--offset` permite ajustar timing manualmente (ej. `--offset -0.2`).
- `_validar_timing()` avisa si los subtitulos no cubren el audio.

### Descarga de gameplay (actualizado con aria2c)
- Usa la libreria `yt_dlp`. Detecta aria2c automaticamente (16 conexiones paralelas).
- `buscar_gameplay.py` (previo a descargar): busca en YouTube sin descargar, filtra por
  duracion y licencia libre (`--libre`), deduplica y agrega URLs a `data/gameplay_urls.txt`
  con comentario titulo/canal de referencia. El usuario debe confirmar la licencia.
- Acepta URL directa o archivo `.txt` con URLs (una por linea, `#` = comentario).
- Limita a 1080p por defecto (suficiente para recortes verticales).
- Nombres normalizados secuenciales (`gameplay_001.mp4`).
- Recorte opcional con `--cortar N` (muestreo aleatorio).
- aria2c se instala con `winget install aria2.aria2`.

### Video
- ffmpeg en Windows: `%LOCALAPPDATA%\ffmpeg\ffmpeg-9.0-essentials_build\bin`.
- Filtro ASS: paths con `/`, `fontsdir` como opcion del filtro (no global).
- 9:16 se renderiza INDEPENDIENTE: `crop=iw*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920:flags=lanczos`.
- Gameplay con `-stream_loop -1`. Sin gameplay: `color=black` + `-shortest`.
- **Crop-cover 16:9:** `force_original_aspect_ratio=increase` + `crop=W:H` (el valor `crop`
  en `force_original_aspect_ratio` NO es valido en ffmpeg 9.0, ver AGENTS.md).
- **SAR 9:16:** agregar `setsar=1` al final de la cadena 9:16 (`crop=1080x1080,scale=1080:1920`
  hace que ffmpeg recalcule el SAR a 16:9 por defecto y deforme el video reproducido).
- `--segundos N` limita el render (pruebas rapidas). Preset `medium` en CPU: ~4-7 min por
  minuto de video (~40 min render de 16 min completos).
- Shorts cortados en pausas naturales entre subtitulos.

---

## 5. ESTADO ACTUAL DE DATOS

| Metrica | Valor |
|---|---|
| Guiones generados | 12 (nombres normalizados `001_...txt`) |
| Banjo de temas | 20 temas vectorizados |
| Audio generado | 2 (001 + 011, Kokoro, 16.3 y 4.1 min) |
| ASS generados | 4 (16:9 y 9:16 para 001 y 011) |
| Videos generados | 4 de prueba (3 min c/u: 001/011 x 16:9/9:16, gameplay_003) |
| Gameplay en storage | 5 (3.14 GB, duraciones 10-31 min) |
| URLs de gameplay en data | 7 (en `data/gameplay_urls.txt`) |
| Pipeline probado | ✅ Con gameplay real (subtitulos sobre fondo de juego) |

---

## 6. PENDIENTES (ver NEXT_STEPS.md para detalle)

1. Descargar gameplay real (internet lenta -> usar `data/gameplay_urls.txt` + aria2c).
   Ya hay 7 URLs candidatas anotadas; revisar licencias y ejecutar el downloader.
2. Prueba visual final con gameplay real (subtitulos sobre fondo de juego).
3. Decision del motor TTS de produccion (actual: Kokoro gratis; alternativas evaluadas:
   ElevenLabs, Fish Audio, Chatterbox).

---

## 7. COSTOS (referencia, ~8 guiones/mes)

| Camino | TOTAL/mes |
|---|---|
| Kokoro puro (actual) | ~$6 (VPS) |
| Chatterbox + GPU on-demand | ~$8-10 |
| Fish Audio Plus | ~$17 |
| ElevenLabs Creator | ~$28 |

DeepSeek (guiones): ~$1/mes para 8 guiones de 20 min.

---

## 8. DECISIONES TOMADAS (para no repetir)

- **Motor actual:** Kokoro (gratis, local, `em_alex`/`ef_dora`). edge-tts como respaldo rapido.
- **Subtitulos:** ASS karaoke, estilo final definido (fuente 48/96, frases 2.5s, centrado vertical).
- **Reddit:** NO se usa la API de Reddit ni historias reales. Solo historias "tipo reddit" generadas.
- **Scripts heredados eliminados:** adaptar_guion, buscar_historias_reddit, embeddings_utils, indexar_historias.
- **Normalizacion de nombres:** centralizada en `src/utilidades.py`.
- **aria2c:** instalado en Windows para descargas paralelas de gameplay.
