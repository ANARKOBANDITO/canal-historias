# PLAN: GPU on-demand + Chatterbox para produccion multi-idioma

> **Estado: RUNPOD DESCARTADO PARA PODS.** 7 intentos, 4 imagenes (CUDA 12.4, 12.8, 13.0),
> todos los tiers (COMMUNITY + SECURE), todos los hosts: `cuInit=999` en cada uno.
> El nvidia-container-toolkit de RunPod no inyecta libs del host con el driver 580.
> **La API serverless Chatterbox Turbo SI funciona.**
> **Alternativa GPU:** Vast.ai (~$0.10-0.20/hr, Docker, sin el problema de driver de RunPod).

---

## 1. Objetivo

Migrar el pipeline de audio/video a una GPU on-demand (RunPod, RTX 3080 Ti)
ejecutando:
- **Chatterbox Multilingual V3** (TTS con voice cloning, multi-idioma)
- **faster-whisper CUDA** (transcripcion word-level)
- **ffmpeg NVENC** (render de video por GPU)

Produciendo contenido en 3 idiomas (ingles, portugues, espanol) con
cadencia semanal (1-2 historias completas/semana + shorts).

## 2. Volumen mensual

| Idioma | Historias/mes | Audio total | Episodios (5 min) |
|---|---|---|---|
| Ingles | 4 | ~100 min | ~20 |
| Portugues BR | 2 | ~50 min | ~10 |
| Espanol LATAM | 2 | ~50 min | ~10 |
| **Total** | **8** | **~200 min** | **~40** |

## 3. Arquitectura de modelos TTS

Chatterbox Multilingual V3 usa **voice cloning**: necesita un clip de
referencia de ~10s de la voz que se quiere clonar. Las referencias se
generan con edge-tts (gratis) y se almacenan en `storage/voces/`.

| Idioma | Voz Edge-TTS | Archivo de referencia |
|---|---|---|
| Espanol LATAM | es-MX-JorgeNeural | storage/voces/referencia_es.mp3 |
| Ingles US | en-US-GuyNeural | storage/voces/referencia_en.mp3 |
| Portugues BR | pt-BR-AntonioNeural | storage/voces/referencia_pt.mp3 |

El modelo es el mismo para los 3 idiomas (Multilingual V3, 500M params,
6-8 GB VRAM). Se pasa `language_id` por guion.

## 4. Proveedor GPU: Vast.ai (RunPod descartado)

### Precios reales (2026-08-10, GPUs >= 12GB VRAM)

| GPU | VRAM | Ofertas | Mediana/hr | Min/hr |
|---|---|---|---|---|
| RTX A4000 | 16GB | 187 | $0.10 | $0.033 |
| RTX 3080 Ti | 12GB | 69 | $0.10 | $0.028 |
| **RTX 3090** | **24GB** | **424** | **$0.117** | **$0.081** |
| RTX 4070 Ti | 12GB | 23 | $0.07 | $0.08 |
| RTX 4080 | 16GB | 30 | $0.13 | $0.067 |
| RTX 4090 | 24GB | 632 | $0.27 | $0.097 |
| RTX A5000 | 24GB | 31 | $0.17 | $0.071 |

**Recomendado:** RTX 3090 (24GB) — 424 ofertas, ~$0.08-0.12/hr. Sweet spot.
Chatterbox (6-8GB) + whisper (2-4GB) + NVENC con holgura.

**Costo mensual estimado:** 4-6 hrs GPU + 50GB disco ≈ **$0.50-1.50/mes**
(interruptible 50-80% mas barato; on-demand ~$0.50-1.00).

### Por que NO RunPod

**CAUSA RAIZ (confirmada por investigacion, 10/08):** NO es "drivers rotos
globalmente". Es un bug especifico del driver 580.95.05 a nivel del host:

1. **Bug de kernel nvidia-uvm** (NVIDIA/open-gpu-kernel-modules#797):
   el modulo nvidia-uvm falla su init HMM/PMM en 580.95.05, causando
   cuInit=999 mientras nvidia-smi sigue funcionando. Fix: parche de kernel
   (Ubuntu >= 6.8.0-88, LP #2120209) o `uvm_disable_hmm=1`.
2. **Bug del nvidia-container-toolkit 1.19.1** (#1934, #1967, #1246):
   escribe major=510 incorrecto para nvidia-uvm, y rompe la inyeccion de
   libs en /usr/local/nvidia/lib (queda VACIO).

Ambos son del HOST. No se arreglan desde el Pod. 7 intentos, 7 fracasos.
Costo: ~$0.30 total. Detalle completo en `INFORME_RUNPOD_FALLIDO.txt`.

### Por que Vast.ai

- **Puedo filtrar `driver_version` en la API de busqueda ANTES de pagar.**
  Buscar drivers 570/575 (CUDA 12.8/12.9, maduros, sin el bug #797).
- Hosts individuales con configuraciones propias.
- Soporta Docker + imagenes PyTorch/CUDA + NVENC + SSH.

### Pasos para Vast.ai

1. Crear cuenta en vast.ai (email + verificar) → cargar $10-20 (credito prepago)
2. Obtener API key en Account Settings
3. **ANTES de alquilar:** buscar instancia RTX 3090 filtrando:
   `driver_version < 580` y `cuda_max_good >= 12.8` (via API, sin costo)
4. Usar imagen con CUDA 12.8 o menor: `runpod/pytorch:1.0.2-cu1281-torch260-ubuntu2404`
   o `nvidia/cuda:12.4.1-devel-ubuntu22.04` + instalar torch cu126
5. Docker options: `--shm-size=32gb`
6. **SMOKE TEST de 10 segundos ANTES de instalar nada:**
   `python3 -c "import ctypes; c=ctypes.CDLL('libcuda.so.1'); print(c.cuInit(0))"`
   Si != 0 → instancia rota. Terminar y reprovisionar en otro host.
7. Si cuInit=0 → `import torch; torch.cuda.is_available()` = True →
   clonar repo, `pip install chatterbox-tts`, pipeline completo
8. Almacenamiento: disco de instancia + Cloud Sync (Backblaze B2 ~$0.005/GB/mes)
   para modelos/gameplays entre sesiones

**Respaldo inmediato (ya probado):** RunPod Chatterbox Turbo API serverless.
$0.001/segundo, voice cloning, NO Pod ni CUDA.

## 5. Tiempos estimados por historia (~25 min de audio)

| Fase | Tiempo GPU |
|---|---|
| Audio (Chatterbox) | ~10 min |
| Transcripcion (whisper CUDA) | ~2 min |
| Render 5 episodios (NVENC, 16:9+9:16) | ~17 min |
| Division + shorts | ~1 min |
| **Total por historia** | **~31 min** |

## 6. Nuevos scripts y cambios

| Archivo | Cambio |
|---|---|
| `src/generar_referencias.py` | Nuevo — genera las 3 voces de referencia con edge-tts |
| `src/dividir_audio.py` | Nuevo — parte audio en episodios de 5 min (ffmpeg copy) |
| `src/pipeline_gpu.py` | Nuevo — orquesta todo en el Pod |
| `src/generar_audio.py` | Motor `chatterbox` + `--idioma` + voice cloning |
| `src/generar_subtitulos_ass.py` | `--idioma` para whisper |
| `src/ensamblar_video.py` | NVENC auto-deteccion + fallback libx264 |
| `requirements.txt` | chatterbox-tts, torch, torchaudio (comentados, solo Pod) |

## 7. Flujo en el Pod (1 historia)

```
1. python src/generar_audio.py guion.txt --motor chatterbox --idioma en
2. python src/dividir_audio.py output/audio/historia.mp3
3. python src/generar_subtitulos_ass.py output/audio/historia.mp3 --idioma en
4. python src/generar_subtitulos_ass.py output/audio/historia.mp3 --vertical --idioma en
5. python src/ensamblar_video.py --procesar --tambien-vertical
6. python src/cortar_shorts.py --procesar
```

O en un solo comando:
```
python src/pipeline_gpu.py --cantidad 1
```

## 8. Pendientes para Fase 2 (usuario)

- [x] Crear cuenta en runpod.io y cargar $10
- [x] Identificar imagen correcta: `runpod/pytorch:1.1.0-cu1300-torch260-ubuntu2404`
- [ ] Verificar CUDA en Pod fresco (cuInit=0, torch.cuda.is_available()=True)
- [ ] Clonar el repo en el Pod + `pip install chatterbox-tts`
- [ ] Probar Chatterbox con 1 frase corta (es, en, pt)
- [ ] Subir gameplays a storage/raw_gameplay/
- [ ] Pipeline completo con 1 historia corta
