# RESUMEN COMPLETO DEL PROYECTO `canal-historias`

> Actualizado al cierre de la sesion del 10/08. Este documento es la fuente de
> verdad para retomar el proyecto en una terminal NUEVA. Leo junto con
> `NEXT_STEPS.md` (pendientes) y `AGENTS.md` (convenciones).

---

## 1. QUE ES

Pipeline automatizado que genera **guiones narrados en primera persona** estilo
"historias de reddit" (confesiones) y los convierte en **video**: audio (TTS
multi-motor) + subtitulos karaoke (ASS) + gameplay de fondo. Destino: YouTube
(16:9) y TikTok/Shorts/Reels/IG (9:16 dividido en partes de ~5 min con CTA).

**Estado actual (13/08):** primer video PILOTO ES entregado (16:9 + 9:16, 16 min,
audio alonso 97% cobertura, subtitulos aprobados). Voz del canal definida:
alonso (hombre) + dalia (mujer) para es/en/pt. Quedan refinamientos del feedback
(ver NEXT_STEPS.md): genero del narrador, guiones sin repeticiones, gameplay de
calidad, 9:16 en partes con CTA, avatar/miniaturas (Replicate sin credito),
NVENC. RunPod Pods descartados (driver 580 roto); Vast.ai es el proveedor GPU.
Nombre del canal: **r/HopStories**.

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
│   │   └── video-producer.md  # Subagente fase audio/video/miniaturas
│   ├── rules/
│   │   ├── espanol.md
│   │   ├── deepseek-api.md
│   │   ├── ffmpeg-windows.md
│   │   ├── kokoro-tts.md
│   │   ├── tts-chatterbox.md  # Motores TTS + estrategia serverless/Vast.ai
│   │   └── imagenes-canal.md  # Tarjeta Reddit, miniaturas, avatar, licencias
│   └── skills/
│       ├── recover-batch/     # Recuperar lote de guiones interrumpido
│       ├── recover-video/     # Recuperar fase video interrumpida
│       ├── renderear-shorts/  # Guia 16:9 -> 9:16 con CTA
│       └── producir-semana/   # Cadencia semanal (3 videos, opcion A)
├── src/
│   ├── utilidades.py              # normalizar_nombre() (compartido)
│   ├── generar_temas.py           # Premisas DeepSeek + deduplicacion
│   ├── generar_historia.py        # Guion (gancho+esquema+capitulos)
│   ├── generar_lote.py            # Batch de guiones
│   ├── variacion_narrativa.py     # Rota gancho/desenlace
│   ├── firma_editorial.py         # Sello de cierre del canal
│   ├── banco_temas.py             # Dedupe de temas (vectores locales)
│   ├── buscar_gameplay.py         # Busca gameplay libre en YouTube (solo URLs)
│   ├── descargar_gameplay.py      # Descarga gameplay (yt-dlp + aria2c)
│   ├── generar_referencias.py     # Voces de referencia edge-tts para Chatterbox
│   ├── generar_audio.py           # Audio (Kokoro/edge/chatterbox/chatterbox-api)
│   ├── generar_subtitulos_ass.py  # whisper -> ASS karaoke
│   ├── ensamblar_video.py         # Audio+ASS+gameplay -> video 16:9/9:16
│   ├── dividir_audio.py           # Audio -> episodios ~5 min (ffmpeg copy)
│   ├── pipeline_gpu.py            # Orquestador del Pod GPU
│   ├── cortar_shorts.py           # 9:16 -> partes ~5 min con CTA
│   ├── generar_tarjeta_reddit.py  # Tarjeta estilo Reddit al inicio del 16:9
│   ├── generar_miniaturas.py      # Miniaturas (Qwen-Image-Edit + Pillow)
│   ├── concatenar_miniatura.py    # Composicion final miniatura
│   ├── revisar_miniaturas.py      # Review con MiniMax M3
│   ├── generar_cta_parte.py       # CTA "like para la parte N"
│   ├── estadisticas.py            # Dashboard
│   ├── validar_guiones.py         # QA pre-locucion
│   ├── limpiar_banco.py           # Gestiona banco de temas
│   └── renombrar_guiones.py       # Normaliza nombres
├── data/
│   ├── temas_pendientes.txt       # Cola de temas
│   ├── temas_usados.txt           # Registro historico
│   ├── banco_temas.pkl            # Vectores de temas usados
│   └── gameplay_urls.txt          # Lista de URLs de gameplay
├── output/
│   ├── guiones_listos/            # 12 guiones (.txt normalizados)
│   ├── audio/                     # Locuciones .mp3
│   ├── subtitulos_ass/            # ASS karaoke 16:9 y 9:16
│   ├── videos/                    # Videos finales (_16x9.mp4 y _9x16.mp4)
│   ├── tarjetas/                  # Tarjeta Reddit (PNG)
│   ├── miniaturas/                # Miniaturas finales (PNG)
│   ├── cta/                       # Overlay + audio del CTA
│   └── shorts/                    # Partes 9:16 con CTA
└── storage/
    ├── raw_gameplay/              # Gameplay loops (5 videos, 3.14 GB)
    ├── voces/                     # Referencias de voz Chatterbox (es, en, pt)
    ├── avatar/                    # Avatar del canal (pendiente de generar)
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
5. python src/generar_audio.py --cantidad 5        -> output/audio/*.mp3
   (mes 1: --motor chatterbox-api; mes 2+: --motor chatterbox en Vast.ai)
6. python src/generar_subtitulos_ass.py --procesar            -> ASS 16:9
7. python src/generar_subtitulos_ass.py --procesar --vertical -> ASS 9:16
8. python src/ensamblar_video.py --procesar --tambien-vertical
                                                   -> output/videos/*_16x9.mp4 y *_9x16.mp4
9. python src/generar_tarjeta_reddit.py --procesar --usuario "r/HopStories"
                                                   -> tarjeta Reddit SOLO en 16:9
10. python src/generar_miniaturas.py --procesar    -> output/miniaturas/
11. python src/revisar_miniaturas.py --procesar    -> review MiniMax M3
12. python src/cortar_shorts.py --procesar --minutos 5 --idioma es
                                                   -> output/shorts/ (partes ~5 min + CTA)
```

**Alternativa en un comando (con GPU):**
`python src/pipeline_gpu.py --cantidad 5`

---

## 4. CONVENCIONES CRITICAS

### DeepSeek (guiones)
- Modelo `deepseek-v4-flash`, base URL `https://api.deepseek.com/v1`.
- SIEMPRE `extra_body={"thinking": {"type": "disabled"}}` en cada llamada.
- max_tokens minimos: gancho 200, premisas 400, capitulos 2000, esquemas 4000.
- API key: `DEEPSEEK_API_KEY`.

### Audio (Kokoro / edge-tts / Chatterbox / Chatterbox API)
- **Kokoro (CPU local):** voces `em_alex` (hombre) / `ef_dora` (mujer). Modelos en `storage/`.
- **edge-tts (nube, rapido):** `--motor edge`, voces `es-MX-JorgeNeural` / `es-MX-DaliaNeural`.
- **Chatterbox (GPU, voice cloning):** `--motor chatterbox --idioma en`. Multilingual V3,
  500M params, ~6-8 GB VRAM. Necesita voces de referencia en `storage/voces/`.
  Generar con `generar_referencias.py`. Corre en Vast.ai (mes 2+).
- **Chatterbox API (serverless RunPod):** `--motor chatterbox-api --idioma en`.
  $0.001/seg, voice cloning via `voice_url`. Mes 1 (quema saldo RunPod).

### Tarjeta Reddit (16:9 SOLO)
- `generar_tarjeta_reddit.py`: tarjeta estilo publicacion Reddit (avatar + `r/HopStories`
  + texto del gancho) superpuesta al inicio del 16:9 mientras dura el gancho (~8-12% del
  audio, max 12s). El 9:16 NO lleva tarjeta.

### Miniaturas y avatar
- `generar_miniaturas.py`: Qwen-Image-Edit-2511 (Apache 2.0, comercial OK) en Vast.ai
  (`--backend local`) para la escena + composicion con avatar/titulo (Pillow).
- `revisar_miniaturas.py`: evalua con MiniMax M3 (puntaje + clickability + sugerencia).
- Avatar del canal: conejito-robot estilo Snoo adaptado, 10 expresiones, PNG transparente
  en `storage/avatar/`. Se genera UNA vez con Nano Banana 2 (A6000 48GB).
- **LICENCIAS:** FLUX.1 Kontext dev = NON-COMMERCIAL (NO usar). Qwen y Nano Banana = OK comercial.

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
| Videos generados | 001 (16:9 y 9:16, gameplay real) + pruebas de 011 |
| Gameplay en storage | 5 (3.14 GB, duraciones 10-31 min) |
| URLs de gameplay en data | 7 (en `data/gameplay_urls.txt`) |
| CTA de partes | Probado: overlay PNG + audio edge-tts en `output/cta/` |
| Tarjeta Reddit | Probado: PNG renderizado (falta avatar del canal) |
| Pipeline probado | ✅ Guiones -> audio -> subs -> video -> shorts con CTA |

---

## 6. PENDIENTES (ver NEXT_STEPS.md para detalle)

1. **Avatar del canal**: generar con Nano Banana 2 (A6000 48GB) + 10 expresiones,
   PNG transparente en `storage/avatar/`. Requiere la foto del conejito del usuario.
2. **Vast.ai**: crear cuenta, cargar credito, probar CUDA (filtro driver < 580).
3. **Chatterbox**: probar en Vast.ai local (voice cloning) y/o serverless API.
4. **Miniaturas**: probar Qwen-Image-Edit con 1 guion de referencia.
5. **Revision M3**: configurar cuando el usuario tenga creditos/API de MiniMax M3.
6. **Probar el flujo semanal completo** (3 videos) una vez Vast.ai funcione.

---

## 7. COSTOS (referencia, ~12 videos/mes = 3/semana)

| Camino | TOTAL/mes |
|---|---|
| Mes 1: TTS serverless (quema saldo RunPod $14.45) + Vast.ai (whisper+video) | ~$1.60 |
| Mes 2+: Todo en Vast.ai (TTS local + whisper + video) | ~$5 |
| Alternativa: serverless TTS indefinido | ~$12+ |

Desglose mes 2+ (12 videos): DeepSeek ~$1.50 + GPU Vast.ai RTX 3090 ~$3.00
+ miniaturas/revision ~$0.15. Avatar (Nano Banana, A6000) = ~$0.50 una vez.
El saldo de RunPod se quema SIEMPRE primero en TTS serverless (costo hundido).

---

## 8. DECISIONES TOMADAS (para no repetir)

- **Nombre del canal:** `r/HopStories` (avatar conejito-robot + formato Reddit).
- **Motor TTS:** mes 1 = `chatterbox-api` (serverless, quema saldo RunPod);
  mes 2+ = `chatterbox` local en Vast.ai (voice cloning). Kokoro/edge como respaldo.
- **Proveedor GPU:** Vast.ai (RTX 3090 ~$0.12/hr). RunPod Pods DESCARTADOS
  (driver 580 + toolkit 1.19.1 rompen CUDA en contenedores).
- **Subtitulos:** ASS karaoke, estilo final definido (fuente 48/96, frases 2.5s, centrado vertical).
- **Tarjeta Reddit:** SOLO en el 16:9, al inicio mientras dura el gancho. Usuario `r/HopStories`.
- **9:16:** sin tarjeta; gameplay vertical + subtitulos; cortes en fin de capitulo;
  CTA "like para la parte N" (visual + narrado) al final de cada parte.
- **Miniaturas:** Qwen-Image-Edit-2511 (Apache 2.0, comercial OK). Review con MiniMax M3.
- **LICENCIAS:** FLUX.1 Kontext dev NON-COMMERCIAL → NO usar en canal monetizado.
- **Reddit:** NO se usa la API de Reddit ni historias reales. Solo "tipo reddit" generadas.
- **Normalizacion de nombres:** centralizada en `src/utilidades.py`.
