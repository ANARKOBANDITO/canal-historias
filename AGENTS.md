# canal-historias

Pipeline automatizado para generar guiones narrados estilo "historias de reddit"
usando DeepSeek API, y convertirlos en video (audio + subtitulos + gameplay).
Cada guion incluye gancho de apertura + historia completa en primera persona,
lista para locucion.

## Estructura del proyecto

```
canal-historias/
├── AGENTS.md
├── requirements.txt
├── src/
│   ├── utilidades.py             # Funciones compartidas (normalizacion de nombres)
│   ├── generar_temas.py          # Genera premisas con DeepSeek (+ deduplicacion)
│   ├── generar_historia.py       # Guion completo (gancho + esquema + capitulos)
│   ├── generar_lote.py           # Batch: procesa data/temas_pendientes.txt
│   ├── buscar_vast.py            # Busca instancias GPU Vast.ai (driver<580, cuda>=12.8)
│   ├── provisionar_vast.py       # Alquila + smoke test + instala + prueba en Vast.ai
│   ├── variacion_narrativa.py    # Rota tipos de gancho y desenlace
│   ├── firma_editorial.py        # Sello de cierre reconocible del canal
│   ├── banco_temas.py            # Deduplicacion de temas (sentence-transformers)
│   ├── buscar_gameplay.py        # Busca gameplay libre en YouTube y llena gameplay_urls.txt
│   ├── descargar_gameplay.py     # Descarga gameplay por URL (yt-dlp)
│   ├── generar_referencias.py    # Genera voces de referencia edge-tts para Chatterbox
│   ├── generar_audio.py          # Audio (Kokoro / edge-tts / Chatterbox / chatterbox-api)
│   ├── generar_subtitulos_ass.py # Transcripcion whisper -> ASS karaoke
│   ├── ensamblar_video.py        # Audio + subtitulos + gameplay -> video 16:9/9:16
│   ├── dividir_audio.py          # Parte audio en episodios de ~5 min (ffmpeg copy)
│   ├── pipeline_gpu.py           # Orquestador completo para Pod con GPU
│   ├── cortar_shorts.py          # Divide video 9:16 en partes ~5 min con CTA
│   ├── generar_tarjeta_reddit.py # Tarjeta estilo Reddit al inicio del 16:9
│   ├── generar_miniaturas.py     # Miniaturas (Qwen-Image-Edit + Pillow)
│   ├── concatenar_miniatura.py   # Composicion final de miniatura (escena+avatar+titulo)
│   ├── revisar_miniaturas.py     # Review de miniaturas con MiniMax M3
│   ├── generar_cta_parte.py      # CTA "like para la parte N" (overlay + audio)
│   ├── estadisticas.py           # Dashboard del proyecto
│   ├── validar_guiones.py        # QA pre-locucion
│   ├── limpiar_banco.py          # Gestiona banco de temas
│   └── renombrar_guiones.py      # Normaliza nombres de archivos
├── data/
│   ├── temas_pendientes.txt      # Cola de temas (uno por linea)
│   ├── temas_usados.txt          # Registro historico
│   └── banco_temas.pkl           # Vectores de temas usados
├── output/
│   ├── guiones_listos/           # Guiones generados (.txt, nombres normalizados)
│   ├── audio/                    # Locuciones (.mp3)
│   ├── subtitulos_ass/           # Subtitulos ASS karaoke (16:9 y 9:16)
│   ├── videos/                   # Videos finales (_16x9.mp4 y _9x16.mp4)
│   ├── tarjetas/                 # Tarjeta Reddit (PNG)
│   ├── miniaturas/               # Miniaturas finales (PNG)
│   ├── cta/                      # Overlay + audio del CTA de partes
│   └── shorts/                   # Partes 9:16 con CTA
├── storage/
│   ├── raw_gameplay/             # Gameplay loops descargados
│   ├── voces/                    # Referencias de voz para Chatterbox (es, en, pt)
│   ├── avatar/                   # Avatar del canal (PNG transparente, 10 expresiones)
│   ├── kokoro-v1.0.onnx          # Modelo Kokoro (310 MB)
│   ├── voices-v1.0.bin           # Voces Kokoro (27 MB)
│   └── Montserrat-Bold.ttf       # Fuente de subtitulos
```


## Flujo de trabajo

1. `python src/generar_temas.py --cantidad 10` --> genera premisas y las guarda en `data/temas_pendientes.txt`
2. `python src/generar_temas.py --cantidad 5 --tema "venganza post infidelidad"` --> premisas sobre un tema especifico
3. `python src/generar_lote.py --genero hombre --minutos 20` --> procesa toda la cola y guarda guiones en `output/guiones_listos/`
4. `python src/generar_historia.py "mi tema" --genero hombre --minutos 20` --> un solo guion, manual
5. `python src/buscar_gameplay.py --libre --guardar "no copyright gameplay"` --> busca URLs de gameplay libre en YouTube y las agrega a `data/gameplay_urls.txt` (sin descargar)
6. `python src/descargar_gameplay.py "url"` --> baja gameplay a `storage/raw_gameplay/` (completo, o con `--cortar 120`)
7. `python src/descargar_gameplay.py data/gameplay_urls.txt` --> baja un lote de URLs desde un archivo (una por linea)
8. `python src/generar_referencias.py` --> genera voces de referencia edge-tts para Chatterbox en `storage/voces/` (es, en, pt)
9. `python src/generar_audio.py --cantidad 5` --> audio MP3 en `output/audio/` (Kokoro, auto-detecta genero)
   - `python src/generar_audio.py --motor chatterbox --idioma en` --> audio con Chatterbox (GPU, voice cloning)
10. `python src/dividir_audio.py --procesar` --> parte audios en episodios de ~5 min (`output/audio/episodios/`)
11. `python src/generar_subtitulos_ass.py --procesar` --> ASS 16:9 en `output/subtitulos_ass/`
    - `--idioma en|pt|es|auto` para whisper multi-idioma
12. `python src/generar_subtitulos_ass.py --procesar --vertical` --> ASS 9:16
13. `python src/ensamblar_video.py --procesar --tambien-vertical` --> videos en `output/videos/`
    - `--segundos N` limita el render a N segundos (pruebas rapidas)
    - Auto-detecta NVENC en GPU con fallback a libx264 en CPU
14. `python src/cortar_shorts.py --procesar --minutos 5 --idioma es` --> partes 9:16 en `output/shorts/` con CTA "like para la parte N"
15. `python src/pipeline_gpu.py --procesar` --> pipeline completo en Pod con GPU
16. `python src/generar_tarjeta_reddit.py --procesar --usuario "r/HopStories"` --> tarjeta Reddit sobre el 16:9 (SOLO 16:9)
17. `python src/generar_miniaturas.py --procesar` --> miniaturas en `output/miniaturas/`
18. `python src/revisar_miniaturas.py --procesar` --> review de miniaturas con MiniMax M3
19. `python src/generar_cta_parte.py --parte 1 --siguiente 2 --idioma es` --> CTA individual (overlay + audio)

## Plan maestro (produccion semanal)

- **3 videos/semana**: 2 en ingles + 1 en español o portugues (alternando).
- **Formato por historia**: 16:9 (YouTube) + 9:16 dividido en partes de ~5 min (Shorts/TikTok/Reels/IG).
- **Opcion A**: los 3 videos de la semana se producen en UNA sesion (1 arranque de instancia GPU).
- **Tarjeta Reddit**: solo el 16:9, al inicio mientras dura el gancho. Usuario `r/HopStories` + avatar.
- **9:16**: sin tarjeta; solo gameplay vertical + subtitulos. Cortes en fin de capitulo + CTA "like para la parte N" (visual + narrado).
- **TTS**: mes 1 por API serverless (quema saldo RunPod); mes 2+ por Chatterbox local en Vast.ai.
- **Miniaturas**: Qwen-Image-Edit-2511 (Apache 2.0) + Pillow; revisadas por MiniMax M3.
- **Avatar**: conejito-robot (estilo Snoo adaptado), 10 expresiones, PNG transparente. Se genera una vez con Nano Banana 2 (A6000 48GB).
- Ver skill `.opencode/skills/producir-semana/` para el flujo detallado.

## Dependencias

```
pip install -r requirements.txt
```

Contenido: `openai`, `sentence-transformers`, `numpy`, `edge-tts`, `kokoro-onnx`,
`soundfile`, `faster-whisper`, `yt-dlp`, `pillow`.
GPU (Vast.ai, aparte): `chatterbox-tts`, `torch`, `diffusers`, `transformers`.

- ffmpeg se instala aparte. En Windows esta en `%LOCALAPPDATA%\ffmpeg\ffmpeg-9.0-essentials_build\bin\ffmpeg.exe`.
- aria2c (opcional, acelera descargas de gameplay con conexiones paralelas): `winget install aria2.aria2`.
- API keys en variables de entorno: `DEEPSEEK_API_KEY` (obligatoria), `FISH_AUDIO_API_KEY`, `ELEVENLABS_API_KEY` (opcionales).

## Modelo y API DeepSeek

- Modelo: `deepseek-v4-flash`
- Base URL: `https://api.deepseek.com/v1`
- **IMPORTANTE**: El modelo tiene modo "thinking" activo por defecto, que consume tokens
  del presupuesto de `max_tokens` sin producir contenido visible. Para cualquier llamada
  a la API, siempre pasar `extra_body={"thinking": {"type": "disabled"}}` y usar
  `max_tokens` generoso (minimo 200 para ganchos, 2000 para capitulos, 4000 para esquemas).

## Pipeline de audio/video

- **Kokoro (TTS local):** voces `em_alex` (hombre) / `ef_dora` (mujer). Modelos en `storage/`.
  Genera WAV 24kHz que se convierte a MP3 con ffmpeg. En CPU, un guion de 20 min tarda
  ~3-5 min. Alternativa: `--motor edge` (edge-tts, mas rapido, voz en la nube).
- **Subtitulos ASS karaoke:** Montserrat Bold, blanco + borde negro, karaoke `\k` por
  palabra (la activa en amarillo). 16:9 -> PlayRes 1920x1080, fuente 48, frases ~2.5s,
  MarginV 80, abajo centrado. 9:16 -> PlayRes 1080x1920, fuente 96, 1-2 palabras por
  linea, centrado en la mitad de la pantalla (MarginV 900).
- **Video 9:16:** se renderiza INDEPENDIENTE desde el gameplay (center-crop de la franja
  vertical + upscale `lanczos`), NO recortando el video 16:9. Cada formato usa su propio ASS.
- **SAR 9:16 (fix 09/08):** al escalar `crop=1080x1080 -> scale=1080:1920`, ffmpeg recalcula el
  SAR automaticamente a 16:9 (deformando el video reproducido, aunque los frames se vean bien).
  SIEMPRE agregar `setsar=1` al final de la cadena de filtros 9:16 para forzar SAR 1:1 / DAR 9:16.
- **Gameplay:** se repite con `-stream_loop -1`. Los shorts se cortan en pausas naturales
  entre subtitulos (no a mitad de palabra).
- **Bug conocido (fix 09/08):** `force_original_aspect_ratio=crop` NO es valido en ffmpeg 9.0
  (falla al renderizar con gameplay real). Usar `force_original_aspect_ratio=increase` seguido
  de `crop=W:H` para el crop-cover 16:9. El fallo solo aparecia con gameplay (fondo negro no
  usaba ese filtro), por eso las pruebas anteriores pasaban.
- **Bug audio (fix 09/08):** si el gameplay tiene pista de audio (opus de ~1 kbps), ffmpeg
  auto-mapea esa pista como audio de salida en vez del MP3 de narracion. Agregar SIEMPRE
  `-map 0:v -map 1:a` para forzar video del gameplay + audio de Kokoro.
- **`--segundos N` en ensamblar_video.py:** limita el render a N segundos (`-t N` + `-shortest`)
  para pruebas rapidas sin renderizar el video completo.
- **Chatterbox (GPU):** `generar_audio.py --motor chatterbox --idioma en`. Necesita voces de
  referencia en `storage/voces/` (generadas con `generar_referencias.py`). Solo funciona
  en Pod con GPU (ChatterboxMultilingualTTS V3, 500M params, ~6-8 GB VRAM).
- **Chatterbox API (serverless RunPod):** `generar_audio.py --motor chatterbox-api --idioma en`.
  $0.001/seg. Voice cloning via `voice_url` (clip de referencia publico). Mes 1 de produccion.
- **Tarjeta Reddit (16:9 SOLO):** `generar_tarjeta_reddit.py` renderiza la publicacion con
  Pillow (avatar + `r/HopStories` + texto del gancho) y la superpone al inicio del 16:9
  mientras dura el gancho (~8-12% del audio, max 12s). El 9:16 NO lleva tarjeta.
- **Miniaturas:** `generar_miniaturas.py` usa Qwen-Image-Edit-2511 (Apache 2.0, uso comercial)
  en GPU Vast.ai (`--backend local`) para la escena + composicion con avatar/titulo (Pillow).
  `concatenar_miniatura.py` separa la composicion. `revisar_miniaturas.py` las evalúa con M3.
- **CTA de partes:** `cortar_shorts.py --minutos 5` corta en finales de capitulo y agrega
  "like para la parte N" (N = parte siguiente): overlay PNG + audio edge-tts narrado.
  `generar_cta_parte.py` genera el CTA de forma independiente.
- **LICENCIAS (canal monetizado):** FLUX.1 Kontext dev es NON-COMMERCIAL → NO usar.
  Qwen-Image-Edit-2511 y Nano Banana (Gemma) permiten uso comercial.

## Convenciones de codigo

- Python 3.11+, sin type hints obligatorios pero bienvenidos.
- Nombres de funciones y variables en `snake_case` en espanol descriptivo.
- Docstrings en espanol al inicio de cada archivo explicando proposito y uso.
- Sin comentarios innecesarios en el cuerpo del codigo.
- Variables de entorno para secretos, nunca hardcodear API keys.
- Paths con `pathlib.Path`, no strings.
- Salida en `output/`, siempre con `encoding="utf-8"`.
- Todos los scripts se ejecutan desde la raiz del proyecto.
- Nombres de archivo normalizados con `normalizar_nombre()` de `src/utilidades.py`
  (sin tildes/enes para compatibilidad Windows).

## Comandos utiles

```bash
# Generar 10 temas variados
python src/generar_temas.py --cantidad 10
# Generar 5 temas sobre un topico especifico
python src/generar_temas.py --cantidad 5 --tema "traicion entre hermanos"

# Buscar instancias GPU validas en Vast.ai (gratis, sin API key)
python src/buscar_vast.py

# Alquilar + smoke test CUDA + instalar + probar Chatterbox en Vast.ai
python src/provisionar_vast.py --provisionar --clave "C:\Users\allen\.ssh\id_ed25519" --conservar

# Generar un solo guion de prueba
python src/generar_historia.py "un perro perdido que vuelve a casa" --genero mujer --minutos 5

# Procesar toda la cola de pendientes
python src/generar_lote.py --genero hombre --minutos 20

# Descargar gameplay (completo o recortado)
python src/descargar_gameplay.py "url" --cortar 120

# Buscar y guardar gameplay libre en data/gameplay_urls.txt (sin descargar)
python src/buscar_gameplay.py --libre --guardar "no copyright gameplay" "free to use gameplay"

# Descargar un lote desde archivo (una URL por linea)
python src/descargar_gameplay.py data/gameplay_urls.txt

# Generar voces de referencia para Chatterbox (edge-tts)
python src/generar_referencias.py

# Generar audio + subtitulos + videos
python src/generar_audio.py --cantidad 5 --genero hombre
python src/generar_subtitulos_ass.py --procesar
python src/generar_subtitulos_ass.py --procesar --vertical
python src/ensamblar_video.py --procesar --tambien-vertical
python src/cortar_shorts.py --procesar

# Tarjeta Reddit + miniaturas + revision
python src/generar_tarjeta_reddit.py --procesar --usuario "r/HopStories"
python src/generar_miniaturas.py --procesar
python src/revisar_miniaturas.py --procesar

# CTA individual de partes
python src/generar_cta_parte.py --parte 1 --siguiente 2 --idioma es

# Pipeline GPU completo (Pod)
python src/pipeline_gpu.py --procesar

# Dividir audio en episodios
python src/dividir_audio.py --procesar
```

## Notas para el agente

- Siempre verificar que `DEEPSEEK_API_KEY` este configurada antes de ejecutar.
- Los scripts de generacion hacen multiples llamadas a la API (gancho + esquema + 5-9 capitulos).
- **IMPORTANTE: RunPod Pods.** El driver 580.95.05 del host NO funciona con CUDA en
  contenedores de ningun tipo (7 intentos fallidos, imagenes CUDA 12.x y 13.0, tiers
  COMMUNITY y SECURE). La API serverless Chatterbox Turbo SI funciona ($0.001/seg).
- **IMPORTANTE: Causa raiz del cuInit=999.** Bug del modulo kernel nvidia-uvm en
  driver 580.95.05 (NVIDIA/open-gpu-kernel-modules#797) + bug del toolkit 1.19.1
  (#1934/#1967/#1246). Es problema del HOST, no de la imagen ni del Pod.
- **IMPORTANTE: Vast.ai (proveedor GPU elegido).** Automatizado en
  `src/buscar_vast.py` (busqueda publica, sin key) y `src/provisionar_vast.py`
  (alquilar + smoke test + instalar + probar). La busqueda filtra
  `driver_version < 580` y `cuda_max_good >= 12.8` ANTES de alquilar.
  Smoke test obligatorio al conectar: `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`.
  Si != 0, el script destruye la instancia solo (costo ~$0.01). Docker options: `--shm-size=32gb`.
  Imagen con torch 2.6.0: `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`. La API
  responde `offers` (no `bundles`). Crear instancia: `PUT /api/v0/asks/{offer_id}/`.
- **IMPORTANTE: Verificar CUDA primero.** Antes de instalar cualquier cosa en un Pod
  GPU, ejecutar: `python3 -c "import torch; print(torch.cuda.is_available())"`.
  Si es False, no seguir. Terminar el Pod y buscar otro host/proveedor.
- **Vast.ai:** hosts heterogeneos, ~$0.08-0.12/hr RTX 3090. Docker options:
  `--shm-size=32gb`. Cuenta: vast.ai, credito prepago, API key en Account Settings.
- **IMPORTANTE: Chatterbox.** `pip install chatterbox-tts` instala el paquete 0.1.7.
  Import correcto: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
  NO usar `from chatterbox_tts import ...`. Requiere torch==2.6.0.
  Modelo en HF: `ResembleAI/chatterbox` (publico, NO gated, NO requiere token).
- **IMPORTANTE: Licencias de imagenes.** FLUX.1 Kontext dev es NON-COMMERCIAL (no usar
  en canal monetizado). Qwen-Image-Edit-2511 es Apache 2.0 (OK). Nano Banana/Gemma es
  licencia Gemma (OK comercial, revisar prohibidos).
- `generar_lote.py` vacia `data/temas_pendientes.txt` al terminar. Si se interrumpe, los temas
  ya procesados quedan en `data/temas_usados.txt` pero los pendientes **no se borran** hasta
  que el script termina naturalmente.
- `data/banco_temas.pkl` usa `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
  para detectar temas duplicados por similitud de vectores (umbral 0.75).
- En Windows, ffmpeg puede no estar en el PATH. Usar ruta completa:
  `%LOCALAPPDATA%\ffmpeg\ffmpeg-9.0-essentials_build\bin\ffmpeg.exe`.
- Los filtros `ass=` de ffmpeg necesitan paths con `/` y `:` escapada (ej. `C:/ruta`).
- Kokoro en CPU es lento para guiones largos; para pruebas rapidas usar `--motor edge`.
- `buscar_gameplay.py` usa yt-dlp (sin descargar) para buscar gameplay y poblar
  `data/gameplay_urls.txt`. Con `--libre` solo conserva resultados cuyo titulo/canal
  sugiere licencia libre ("no copyright", "free to use"...). Aun asi, confirmar la
  licencia de cada video antes de usarlo en canal monetizado (el .txt guarda el
  titulo/canal como comentario de referencia).
- Ejecutar siempre desde la raiz del proyecto.

## Lecciones 13/08 (piloto ES) — reglas duras

- **Genero del narrador = voz.** El `[GENERO:]` del guion debe coincidir con la voz
  que usa la historia (p.ej. "mi novio..." => narradora mujer). Correr SIEMPRE
  `python src/validar_guiones.py` antes de locutar (detecta genero, palabras
  repetidas, n-gramas loop y frases largas).
- **Gameplay de calidad:** el gameplay_lite NO debe ir a 2 Mbps (queda pixelado).
  Usar crf ~20 / maxrate 6-8M, o el gameplay crudo.
- **9:16 en partes:** los videos verticales se dividen en partes de ~5 min (corte
  en fin de capitulo, sin clips <90s) y cada parte termina con CTA NARRADO
  "para la parte X, like y seguir" (TikTok/Shorts/Reels).
- **Replicate sin credito = 402.** `generar_avatar.py` y
  `generar_miniaturas.py --backend api` fallan si no hay saldo. Verificar antes.
- **NVENC roto en pods driver 570** (nvenc API 13.0 vs ffmpeg nuevo 13.1): render
  cae a libx264 CPU (lento). Fix pendiente: ffmpeg BtbN 2025 en el pod.
- **Chatterbox fragmenta por parrafos** (max_new_tokens=1000): pausas de 0.35s entre
  fragmentos. Cobertura validada con `src/qa_audio.py` (>= 95%).
