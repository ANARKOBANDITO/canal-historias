# NEXT STEPS — Pendientes del proyecto canal-historias

> Leer este archivo PRIMERO al retomar el proyecto. Define que falta hacer.
> Contexto completo en `RESUMEN_PROYECTO.md` y convenciones en `AGENTS.md`.

---

## Estado de la ultima sesion (09/08)

- Pipeline completo probado de punta a punta con gameplay real (3 bugs ffmpeg corregidos).
- 5 gameplays descargados (10-31 min, 3.14 GB), 7 URLs en `data/gameplay_urls.txt`.
- **Fase 1 GPU/Chaterbox completada:** nuevos scripts (`generar_referencias.py`,
  `dividir_audio.py`, `pipeline_gpu.py`), `generar_audio.py` con `--motor chatterbox`
  + `--idioma`, NVENC auto-deteccion en `ensamblar_video.py`, whisper multi-idioma.
- Voces de referencia generadas en `storage/voces/` (es-MX, en-US, pt-BR).
- Plan GPU documentado en `PLAN_GPU_CHATTERBOX.md`.
- **Pendiente Fase 2:** configurar Pod en RunPod y probar Chatterbox real.

---

## PROXIMOS PASOS (en orden sugerido)

### 1. Fase 2 — Configurar Pod GPU (tarea del usuario)
- Crear cuenta en runpod.io, cargar $10.
- Crear Pod: RTX 3060 (12 GB), 40 GB disco, template PyTorch.
- Clonar repo, `pip install -r requirements.txt chatterbox-tts`.
- Subir gameplays y voces.
- Ver `PLAN_GPU_CHATTERBOX.md` para el detalle completo.

### 2. Probar Chatterbox en el Pod
- Generar 1 frase de prueba por idioma, escuchar y ajustar.
- Pipeline completo con 1 historia corta.
- Medir tiempos reales vs estimaciones.

### 3. Produccion multi-idioma
- 4 historias/mes en ingles, 2 en portugues, 2 en espanol.
- Pipeline semanal: 1-2 historias completas + shorts.

### 4. Decision del motor TTS de produccion (resuelto)
- Chatterbox Multilingual V3 + RTX 3060 GPU on-demand. Costo ~$4/mes total.
- Alternativas descartadas: ElevenLabs (~$28/mes), Fish Audio (~$17/mes),
  Kokoro puro (calidad de voz femenina insuficiente).

---

## NOTAS DE CONTEXTO IMPORTANTES

- **Nunca usar Reddit real:** el usuario NO usara historias reales de Reddit
  (la API no esta disponible). Solo historias "tipo reddit" generadas con DeepSeek.
- **Nombres de archivo:** siempre normalizar con `normalizar_nombre()` de
  `src/utilidades.py` (sin tildes/enes, compatibilidad Windows).
- **Modo plan vs build:** si la terminal nueva esta en modo plan, cambiar a build
  para ejecutar comandos.
- **Session ID de la sesion larga:** `ses_02f6ba8d1ffeSAL9BgAm6Uw0JK`
  (en `data/sesion_id.txt`). Para retomar con `opencode --session <ID>`.
- **Actualizacion de docs:** al terminar cada tarea, mantener al dia
  `AGENTS.md` y `RESUMEN_PROYECTO.md`.
