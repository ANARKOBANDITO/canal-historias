# Sesion GPU en Vast.ai — convenciones tecnicas (11/08, validado)

## Pipeline GPU FUNCIONA (validado 11/08 en RTX 3090)

- **Smoke test CUDA**: `cuInit == 0` → la instancia sirve. El mismo test que
  fallo 7 veces en RunPod paso a la primera en Vast.ai con driver < 580.
- **Flujo correcto de video**: audio completo → ASS (16:9 + 9:16) → video
  COMPLETO (16:9 + 9:16) → `cortar_shorts` divide en partes con CTA.
  NO ensamblar por episodio (bug de diseno del pipeline_gpu viejo).

## Errores ya diagnosticados y sus fixes (NO volver a investigar)

| Sintoma | Causa | Fix |
|---|---|---|
| `Permission denied (publickey)` en SSH | Clave SSH no registrada en Vast.ai, o instancia creada ANTES de registrarla | Registrar en Account > SSH Keys; crear instancia DESPUES |
| `Connection refused` al hacer SSH | Vast dice "running" antes de que sshd este listo | `_ssh()` con reintentos (6x, pausa 10s) |
| scp de 348MB+ se corta | Conexion del host inestable en transferencias largas | Comprimir gameplay a loops ligeros (~60-80MB) ANTES de subir; verificar tamano en el pod |
| `CUDA error: device-side assert` en Chatterbox | Guion entero excede max_new_tokens=1000 hardcodeado | `_dividir_texto()` en fragmentos ~180 palabras + concatenar WAV |
| `Error initializing filter 'ass'` en ffmpeg | Falta `storage/Montserrat-Bold.ttf` en el pod | Desplegar la fuente junto con el codigo |
| `NameError: name 'Kokoro' is not defined` | Type hint evaluado al importar sin kokoro-onnx | `from __future__ import annotations` en scripts con imports opcionales |
| Descarga HF se corta (`xet-read-token` error) | Acelerador Xet falla en hosts del marketplace | `export HF_HUB_DISABLE_XET=1` antes de todo `from_pretrained` |
| `ChatterboxMultilingualTTS.__init__() got an unexpected keyword 'model_id'` | API 0.1.7 cambio el constructor | Usar `from_pretrained(device=...)` + `generate(text=..., language_id=..., audio_prompt_path=...)` |

## Modelos e imagenes (decision 11/08)

- **Nano Banana RETIRADO de HF** (google/nano-banana = 404 incluso con token).
  NO planificar nada con el. Alternativa: **Qwen-Image-Edit-2511** para avatar.
- **Qwen-Image-Edit-2511** (Apache 2.0, comercial OK): 38.3GB en bf16 → NO cabe
  en 24GB sin cuantizar. Usar **GGUF Q4_K_M (12.3GB)** (unsloth/Qwen-Image-Edit-2511-GGUF).
  Sirve para avatar (editar foto conejito) Y miniaturas (escena).
- **Qwen2.5-VL-7B-Instruct** (15.4GB, publico, NO gated): review de frames/
  miniaturas/tarjetas en `revisar_miniaturas.py --backend local`. Sin token HF.
- El avatar (10 expresiones) va en `storage/avatar/avatar_<expresion>.png` y lo
  usa `componer_miniatura()` en cada miniatura.
- Las miniaturas deben reflejar la PREMISA del guion (el gancho/primer parrafo),
  no el nombre del archivo.

## Miniaturas acordes a premisa

`generar_miniaturas.py` debe construir el prompt de Qwen con el **gancho del
guion** (primer parrafo tras los metadatos `[GENERO:]`/`[IDIOMA:]`), no con
`ruta_guion.stem`. El gancho es la esencia de la historia y la escena debe
representarlo.

## API de Vast.ai

- Busqueda publica: `GET https://console.vast.ai/api/v0/bundles/?q=<json>`
  responde `offers`. Filtros: `driver_version < "580.0.0"`, `cuda_max_good >= "12.8"`.
- Crear instancia: `PUT /api/v0/asks/{offer_id}/` con `{"image", "disk":60}`.
- Detalle instancia: `GET /api/v0/instances/{id}/` (v0). Lista: `GET /api/v1/instances/` (v1).
- Destruir: `DELETE /api/v0/instances/{id}/`.
- Imagen Docker: `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime` (torch 2.6.0 ya instalado).
- `VAST_AI_API_KEY` en entorno. SSH: clave `id_ed25519` registrada en la cuenta.
