# PLAN: GPU on-demand + Chatterbox para produccion multi-idioma

> **Estado: EN PREPARACION.** El codigo de Fase 1 esta implementado y probado
> localmente. Falta la Fase 2 (configuracion del Pod en RunPod) y Fase 3
> (primera prueba de produccion real).

---

## 1. Objetivo

Migrar el pipeline de audio/video a una GPU on-demand (RunPod, RTX 3060)
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

## 4. Proveedor GPU: RunPod

| Recurso | Especificacion | Costo |
|---|---|---|
| GPU | RTX 3060 (12 GB VRAM) | $0.29/hr |
| Disco | 40 GB | ~$2.80/mes |
| **Total estimado** | **~4 hrs/mes GPU + almacenamiento** | **~$4/mes** |

El Pod se enciende solo para procesar (1-2 sesiones/semana) y se apaga
al terminar. Los modelos y gameplays quedan en disco persistente.

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

- [ ] Crear cuenta en runpod.io y cargar $10
- [ ] Crear Pod (RTX 3060 12 GB, 40 GB disco, template PyTorch)
- [ ] Clonar el repo en el Pod
- [ ] `pip install -r requirements.txt chatterbox-tts`
- [ ] Subir gameplays a storage/raw_gameplay/
- [ ] Subir voces de referencia a storage/voces/
- [ ] Probar Chatterbox con 1 frase corta
