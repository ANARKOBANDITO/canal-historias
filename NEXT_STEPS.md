# NEXT STEPS — Pendientes del proyecto canal-historias

> Leer este archivo PRIMERO al retomar el proyecto.
> Contexto completo en `RESUMEN_PROYECTO.md` y convenciones en `AGENTS.md`.

---

## Estado actual (10/08)

- Pipeline CPU completo probado (guiones + Kokoro + subtitulos + video + gameplay).
- **RunPod Pods DESCARTADOS:** 7 intentos fallidos (ver `data/INFORME_RUNPOD_FALLIDO.txt`).
  El nvidia-container-toolkit no inyecta librerias del host con el driver 580.
- Codigo para Chatterbox GPU escrito (Fase 1), pero no se pudo probar en Pod.
- API serverless Chatterbox Turbo de RunPod SI funciona (voice cloning probado).

## PROXIMOS PASOS

### 1. Investigar alternativa GPU (Vast.ai / similares)
- Vast.ai: RTX 3080 Ti a ~$0.10-0.20/hr (interruptible), Docker, CUDA
- Comparar con otras opciones (TensorDock, etc.)
- Ver `PLAN_GPU_CHATTERBOX.md` actualizado.

### 2. Opcion inmediata: API serverless Chatterbox Turbo
- Ya probada y funcionando. $0.001/segundo.
- Permite producir YA sin GPU Pod.
- El saldo de RunPod ($14.45) cubre ~1 mes de TTS.

### 3. Verificar Pod via CONSOLA web de RunPod (no REST API)
- Posible issue: los Pods por API no ejecutan el toolkit correctamente.
- Crear Pod desde console.runpod.io con template "RunPod PyTorch" oficial.

### 4. Probar CUDA en otro proveedor
- Una vez elegido el proveedor GPU, verificar CUDA ANTES de instalar nada.
- Flujo: Pod nuevo -> nvidia-smi -> torch.cuda.is_available() -> instalar chatterbox.

---

## NOTAS DE CONTEXTO IMPORTANTES

- **RunPod Pods NO funcionan** con CUDA (driver 580.95.05, cuInit=999 en 7 intentos).
- **API serverless SI funciona** (Chatterbox Turbo, $0.001/seg, voz clonada).
- **Chatterbox-tts 0.1.7** requiere torch==2.6.0. Import correcto: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`.
- **Imagen CUDA 13.0**: `runpod/pytorch:1.0.2-cu1300-torch260-ubuntu2404` (torch 2.6.0)
- **Modelo HF**: ResembleAI/chatterbox (publico, no gated, NO requiere token).
- **SSH RunPod**: solo funciona con -tt (interactivo), no comandos no-interactivos en Windows.

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
