# Motores TTS del proyecto y estrategia

## Motores disponibles en `src/generar_audio.py`

| Motor | Donde corre | Voz clonada | Idiomas | Costo |
|---|---|---|---|---|
| `kokoro` | CPU local | No | es | $0 |
| `edge` | Nube gratis | No | muchos | $0 |
| `chatterbox-api` | Serverless RunPod | Si | es/en/pt | $0.001/seg |
| `chatterbox` | GPU local (Vast.ai) | Si | es/en/pt | ~$0.02/video GPU |

## Estrategia (plan maestro)

- **Mes 1**: `--motor chatterbox-api` — quema el saldo de RunPod (~$14.45).
  Cada historia de 25 min = 1,500 seg × $0.001 = $1.50. El saldo cubre ~9.6 videos.
- **Mes 2+**: `--motor chatterbox` en Vast.ai (voice cloning local). ~$0.02/video GPU.

## Chatterbox (pip install chatterbox-tts)

- Paquete: `chatterbox-tts` 0.1.7. **Import correcto**:
  `from chatterbox.mtl_tts import ChatterboxMultilingualTTS` (NO `chatterbox_tts`).
- Requiere `torch==2.6.0`. Modelo en HF: `ResembleAI/chatterbox` (publico, no gated).
- Voice cloning: necesita clip de referencia ~10s por idioma en `storage/voces/`
  (generar con `generar_referencias.py`, edge-tts). Voces: es-MX-JorgeNeural,
  en-US-GuyNeural, pt-BR-AntonioNeural.
- El CTA "like para la parte N" usa edge-tts por defecto (`src/generar_cta_parte.py`).

## RunPod: estado

- Pods GPU NO funcionan (driver 580.95.05 + toolkit 1.19.1, cuInit=999). Ver historial.
- La API serverless Chatterbox Turbo SI funciona: `https://api.runpod.ai/v2/chatterbox-turbo/runsync`.
  Request: `{"input": {"prompt": "...", "voice_url": "...", "format": "wav"}}`.
  `voice_url` acepta URL publica del clip de referencia para voice cloning.
  Costo $0.001/seg. El audio_url expira a los 7 dias (descargar inmediatamente).

## Vast.ai (GPU on-demand elegido)

- Filtrar `driver_version < 580` y `cuda_max_good >= 12.8` en la busqueda ANTES de alquilar.
- Smoke test obligatorio al conectar: `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`.
  Si != 0 → instancia rota, terminar y reprovisionar.
- Docker options: `--shm-size=32gb`.
- RTX 3090 24GB ~$0.08-0.12/hr es el sweet spot. A6000 48GB (~$0.30/hr) para Nano Banana (avatar).
