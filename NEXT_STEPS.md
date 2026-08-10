# NEXT STEPS — Pendientes del proyecto canal-historias

> Leer este archivo PRIMERO al retomar el proyecto.
> Contexto completo en `RESUMEN_PROYECTO.md` y convenciones en `AGENTS.md`.

---

## Estado actual (10/08, cierre de sesion)

- Pipeline CPU completo probado (guiones + audio + subtitulos + video + gameplay).
- **Nuevos scripts creados y pusheados** (commit `675e8`):
  - `generar_tarjeta_reddit.py` — tarjeta estilo Reddit superpuesta al 16:9 mientras dura el gancho. Probada (PNG + overlay con fade OK).
  - `generar_miniaturas.py` + `concatenar_miniatura.py` — miniaturas Qwen-Image-Edit + Pillow.
  - `revisar_miniaturas.py` — review con MiniMax M3 (`--backend api|local`).
  - `generar_cta_parte.py` — CTA "like para la parte N" (overlay PNG + audio edge-tts). Probado OK.
  - `cortar_shorts.py` actualizado — partes de ~5 min, corte en fin de capitulo, CTA visual+narrado.
  - `generar_audio.py` — nuevo motor `chatterbox-api` (serverless RunPod) implementado y validado.
  - Fix bug latente: `DEVICE_CHATTERBOX` fallaba sin torch.
- **RunPod Pods DESCARTADOS** (driver 580.95.05 + toolkit 1.19.1 rompen CUDA, cuInit=999 en 7 intentos).
- **API serverless Chatterbox Turbo SI funciona** ($0.001/seg, voice cloning via voice_url).
- Nombre del canal decidido: **r/HopStories**.
- Pillow agregado a requirements.txt e instalado localmente.

## DECISION PENDIENTE (el usuario debe responder)

**Como hacer la revision de miniaturas con M3:**
- **A)** API de MiniMax M3 (paga cuando el usuario tenga creditos). `--backend api`.
- **B)** Modelo VL liviano local en Vast.ai (ej. Qwen2.5-VL-7B, cabe en RTX 3090, cero API).
- **C)** Ambas: M3 por API cuando haya creditos + local como respaldo.

> M3 completo local (GGUF) es un MoE enorme → no cabe en 24GB; exigiria A6000 48GB. No vale la pena.
> NOTA aclarada: **Qwen y Nano Banana NO necesitan API de pago** — son pesos abiertos
> (Apache 2.0 y Gemma) que corren localmente en la GPU de Vast.ai. Solo Vast.ai es pago (por hora).

## LO QUE SE NECESITA PARA ARRANCAR (cuando el usuario vuelva)

1. **Cuenta Vast.ai + credito + API key** — el "combustible" de todo el pipeline GPU.
   - Buscar instancia RTX 3090 filtrando `driver_version < 580` y `cuda_max_good >= 12.8`.
   - Smoke test al conectar: `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`.
     Si != 0 → terminar y reprovisionar.
   - Docker options: `--shm-size=32gb`.
2. **Foto del conejito del usuario** → guardar en `storage/fotos/conejito.jpg` (para el avatar).
3. **Token de HuggingFace** (gratis, cuenta ya creada) → para Nano Banana (gated) y modelos.
4. API keys que YA tenemos: `DEEPSEEK_API_KEY`, `RUNPOD_API_KEY` (guardada como env var).

## PROXIMOS PASOS (en orden)

### 1. Avatar del canal (una sola vez)
- Generar con **Nano Banana 2** (GPU A6000 48GB en Vast.ai) + 10 expresiones
  (neutral, feliz, triste, enojado, sorprendido, asustado, decepcionado,
  emocionado, pensativo, sospechoso). PNG transparente en `storage/avatar/`.
- Prioridad de diseño: parecerse MAS al conejito que al robot de Reddit
  (adaptacion animada tipo Snoo, NO el logo oficial).
- Requiere: la foto del conejito + sesion A6000 (~$0.50, una vez).

### 2. Probar Vast.ai (antes de pagar mas)
- Crear cuenta, cargar credito minimo. Verificar CUDA ANTES de instalar nada.

### 3. Probar Chatterbox en Vast.ai
- `pip install chatterbox-tts` (torch 2.6.0). Import: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
- 1 frase por idioma (es/en/pt) con voice cloning desde `storage/voces/`.

### 4. Miniaturas con Qwen-Image-Edit
- Probar `generar_miniaturas.py --backend local` con 1 guion de referencia en Vast.ai.

### 5. Revision (segun la decision pendiente)
- `revisar_miniaturas.py --backend api` (M3 por API) o `--backend local` (VL 7B).

### 6. Flujo semanal completo
- 3 videos/semana (2 EN + 1 ES/PT), opcion A (1 sesion GPU). Ver skill `producir-semana`.
- TTS mes 1: `--motor chatterbox-api` (quema saldo RunPod ~$14.45, cubre ~9.6 videos).
  Mes 2+: `--motor chatterbox` en Vast.ai (~$0.02/video GPU).
- Flujo por historia: guion → audio → subs (16:9 + 9:16) → ensamblar (16:9 + 9:16)
  → tarjeta Reddit (solo 16:9) → miniaturas → review → cortar shorts (9:16 en partes ~5 min + CTA).

---

## NOTAS DE CONTEXTO IMPORTANTES

- **RunPod Pods NO funcionan** con CUDA (driver 580.95.05, cuInit=999).
  Causa raiz: bug kernel nvidia-uvm (open-gpu-kernel-modules#797) + toolkit 1.19.1 (#1934/#1967/#1246).
- **API serverless SI funciona** (Chatterbox Turbo, `https://api.runpod.ai/v2/chatterbox-turbo/runsync`,
  $0.001/seg, voice_url para voice cloning, audio expira en 7 dias).
- **Vast.ai:** filtrar driver < 580. RTX 3090 ~$0.08-0.12/hr, A6000 48GB ~$0.30/hr.
- **Chatterbox-tts 0.1.7** requiere torch==2.6.0. Import: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
- **Modelo HF TTS:** ResembleAI/chatterbox (publico, no gated, NO requiere token).
- **Nano Banana (Gemma 3)** y **MiniMax M3** en HF son gated → requieren token de HF.
- **Nunca usar Reddit real:** solo historias "tipo reddit" generadas con DeepSeek.
- **Licencias imagenes:** FLUX Kontext dev = NON-COMMERCIAL (NO usar). Qwen-Image-Edit = Apache 2.0 (OK). Nano Banana = Gemma (OK comercial).
- **Nombres de archivo:** siempre normalizar con `normalizar_nombre()` de `src/utilidades.py`.
- **Actualizacion de docs:** al terminar cada tarea, mantener al dia `AGENTS.md` y `RESUMEN_PROYECTO.md`.
- **Ejecutar siempre desde la raiz del proyecto** (`C:\Users\allen\OneDrive\Desktop\canal-historias`).
- En Windows, ffmpeg puede no estar en PATH: `$env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"`.
