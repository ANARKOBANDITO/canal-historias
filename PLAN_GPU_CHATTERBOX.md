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

| Recurso | Especificacion | Costo |
|---|---|---|
| GPU | RTX 3080 Ti 12GB (interruptible) | ~$0.10-0.20/hr |
| GPU | RTX 3090 24GB (interruptible) | ~$0.15-0.30/hr |
| Almacenamiento | Por GB/mes | variable |
| **Total estimado** | **~4-6 hrs/mes GPU** | **~$1-2/mes** |

**Por que NO RunPod:** Driver 580.95.05 del host + nvidia-container-toolkit no
inyecta libs compatibles en contenedores (`/usr/local/nvidia/lib/` vacio).
Esto causa `cuInit=999` (CUDA_ERROR_UNKNOWN) en TODAS las imagenes probadas
(CUDA 12.4, 12.8, y 13.0 con driver match). 7 intentos, 7 fracasos.
Costo de intentos fallidos: ~$0.30 total.

**Por que Vast.ai:** Hosts comunitarios individuales con sus propias configuraciones.
Sin el problema de toolkit de RunPod. Interruptible = 50-80% mas barato que on-demand.
Soporta Docker + imagenes PyTorch + CUDA + NVENC.

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
