# NEXT STEPS — Pendientes del proyecto canal-historias

> Leer este archivo PRIMERO al retomar el proyecto.
> Contexto completo en `RESUMEN_PROYECTO.md` y convenciones en `AGENTS.md`.

---

## Estado actual (10/08)

- Pipeline CPU completo probado (guiones + audio + subtitulos + video + gameplay).
- **Nuevos scripts creados:** `generar_tarjeta_reddit.py` (tarjeta Reddit 16:9),
  `generar_miniaturas.py` + `concatenar_miniatura.py` (miniaturas Qwen+Pillow),
  `revisar_miniaturas.py` (review M3), `generar_cta_parte.py` (CTA "like parte N").
  `cortar_shorts.py` actualizado: partes de ~5 min + corte en fin de capitulo + CTA.
- CTA de partes probado (overlay PNG + audio edge-tts OK). Tarjeta Reddit probada
  (PNG renderizado OK, falta el avatar del canal).
- **RunPod Pods DESCARTADOS** (driver 580.95.05 + toolkit 1.19.1 rompen CUDA).
  API serverless Chatterbox Turbo SI funciona ($0.001/seg, voice cloning probado).
- Nombre del canal decidido: **r/HopStories**.

## PROXIMOS PASOS

### 1. Avatar del canal (una sola vez)
- Generar con **Nano Banana 2** (GPU A6000 48GB en Vast.ai) + 10 expresiones
  (neutral, feliz, triste, enojado, sorprendido, asustado, decepcionado,
  emocionado, pensativo, sospechoso). PNG transparente en `storage/avatar/`.
- **Requiere la foto del conejito del usuario** (guardar en `storage/fotos/conejito.jpg`).

### 2. Probar Vast.ai (antes de pagar mas)
- Crear cuenta, cargar credito minimo.
- Buscar instancia RTX 3090 filtrando `driver_version < 580` y `cuda_max_good >= 12.8`.
- Smoke test al conectar: `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`.
  Si != 0 → terminar y reprovisionar.

### 3. Probar Chatterbox en Vast.ai
- `pip install chatterbox-tts` (torch 2.6.0). Import: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
- 1 frase por idioma (es/en/pt) con voice cloning desde `storage/voces/`.

### 4. Miniaturas con Qwen-Image-Edit
- Probar `generar_miniaturas.py --backend local` con 1 guion de referencia en Vast.ai.

### 5. Revision con MiniMax M3
- Configurar cuando el usuario tenga creditos/API de M3. `revisar_miniaturas.py --backend api|local`.

### 6. Flujo semanal completo
- 3 videos/semana (2 EN + 1 ES/PT), opcion A (1 sesion GPU). Ver skill `producir-semana`.
- TTS mes 1: `--motor chatterbox-api` (quema saldo RunPod). Mes 2+: `--motor chatterbox` en Vast.ai.

---

## NOTAS DE CONTEXTO IMPORTANTES

- **RunPod Pods NO funcionan** con CUDA (driver 580.95.05, cuInit=999 en 7 intentos).
  Causa raiz: bug kernel nvidia-uvm (open-gpu-kernel-modules#797) + toolkit 1.19.1 (#1934/#1967/#1246).
- **API serverless SI funciona** (Chatterbox Turbo, $0.001/seg, voz clonada).
- **Vast.ai:** filtrar driver < 580. RTX 3090 ~$0.08-0.12/hr. Docker: `--shm-size=32gb`.
- **Chatterbox-tts 0.1.7** requiere torch==2.6.0. Import correcto: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
- **Modelo HF:** ResembleAI/chatterbox (publico, no gated, NO requiere token).
- **Nunca usar Reddit real:** solo historias "tipo reddit" generadas con DeepSeek.
- **Licencias imagenes:** FLUX Kontext dev = NON-COMMERCIAL (NO usar). Qwen-Image-Edit = Apache 2.0 (OK). Nano Banana = Gemma (OK).
- **Nombres de archivo:** siempre normalizar con `normalizar_nombre()` de `src/utilidades.py`.
- **Actualizacion de docs:** al terminar cada tarea, mantener al dia `AGENTS.md` y `RESUMEN_PROYECTO.md`.
