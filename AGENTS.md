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
│   ├── variacion_narrativa.py    # Rota tipos de gancho y desenlace
│   ├── firma_editorial.py        # Sello de cierre reconocible del canal
│   ├── banco_temas.py            # Deduplicacion de temas (sentence-transformers)
│   ├── buscar_gameplay.py        # Busca gameplay libre en YouTube y llena gameplay_urls.txt
│   ├── descargar_gameplay.py     # Descarga gameplay por URL (yt-dlp)
│   ├── generar_referencias.py    # Genera voces de referencia edge-tts para Chatterbox
│   ├── generar_audio.py          # Audio (Kokoro / edge-tts / Chatterbox + voice cloning)
│   ├── generar_subtitulos_ass.py # Transcripcion whisper -> ASS karaoke
│   ├── ensamblar_video.py        # Audio + subtitulos + gameplay -> video 16:9/9:16
│   ├── dividir_audio.py          # Parte audio en episodios de ~5 min (ffmpeg copy)
│   ├── pipeline_gpu.py           # Orquestador completo para Pod con GPU
│   ├── cortar_shorts.py          # Divide video 9:16 en clips para Shorts
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
│   └── shorts/                   # Clips para Shorts/TikTok
├── storage/
│   ├── raw_gameplay/             # Gameplay loops descargados
│   ├── voces/                    # Referencias de voz para Chatterbox (es, en, pt)
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
14. `python src/cortar_shorts.py --procesar` --> clips 9:16 en `output/shorts/`
15. `python src/pipeline_gpu.py --procesar` --> pipeline completo en Pod con GPU

## Dependencias

```
pip install -r requirements.txt
```

Contenido: `openai`, `sentence-transformers`, `numpy`, `edge-tts`, `kokoro-onnx`,
`soundfile`, `faster-whisper`, `yt-dlp`.

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
  COMMUNITY y SECURE). Ver `INFORME_RUNPOD_FALLIDO.txt` para el detalle completo.
  La API serverless Chatterbox Turbo SI funciona ($0.001/seg).
- **IMPORTANTE: Causa raiz del cuInit=999.** Bug del modulo kernel nvidia-uvm en
  driver 580.95.05 (NVIDIA/open-gpu-kernel-modules#797) + bug del toolkit 1.19.1
  (#1934/#1967/#1246). Es problema del HOST, no de la imagen ni del Pod.
- **IMPORTANTE: Vast.ai (proveedor GPU elegido).** Usar la API de busqueda para
  filtrar `driver_version < 580` y `cuda_max_good >= 12.8` ANTES de alquilar.
  Smoke test obligatorio al conectar: `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`.
  Si != 0, terminar instancia y reprovisionar. Docker options: `--shm-size=32gb`.
- **IMPORTANTE: Imagen GPU correcta.** Si se vuelve a intentar GPU en cualquier proveedor,
  la imagen debe tener CUDA >= version del driver del host. Para RunPod driver 580:
  `runpod/pytorch:1.0.2-cu1300-torch260-ubuntu2404` (CUDA 13.0 + torch 2.6.0).
- **IMPORTANTE: Chatterbox.** `pip install chatterbox-tts` instala el paquete 0.1.7.
  Import correcto: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
  NO usar `from chatterbox_tts import ...`. Requiere torch==2.6.0.
  Modelo en HF: `ResembleAI/chatterbox` (publico, NO gated, NO requiere token).
- **IMPORTANTE: Verificar CUDA primero.** Antes de instalar cualquier cosa en un Pod
  GPU, ejecutar: `python3 -c "import torch; print(torch.cuda.is_available())"`.
  Si es False, no seguir. Terminar el Pod y buscar otro host/proveedor.
- **Vast.ai (nuevo proveedor GPU):** hosts heterogeneos, ~$0.08-0.12/hr RTX 3090.
  Docker options: `--shm-size=32gb`. Verificar CUDA antes de instalar.
  Cuenta: vast.ai, credito prepago, API key en Account Settings.
  Un guion de 20 minutos tarda ~2-3 minutos en generarse.
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
