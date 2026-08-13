# PLAN DE CALIDAD — Reconstruir canal-historias para producto monetizable

> Fecha: 12/08. Estado: APROBADO, pendiente de ejecucion.
> Objetivo: producir un video de calidad entregable, luego escalar a la
> cadencia semanal (2 EN + 1 ES/PT).
> Contexto completo: AGENTS.md, RESUMEN_PROYECTO.md, NEXT_STEPS.md.

---

## Diagnosticos (12/08) — que salio mal y por que

| Problema | Causa raiz |
|---|---|
| Miniaturas impresentables | Se uso fondo generico por no resolver el conflicto `diffusers==0.29` (chatterbox) vs `QwenImageEditPipeline`. Qwen-Image-Edit NUNCA corrio en el pod. |
| Shorts con clips de 45-47s | Bug en `_puntos_corte` de `cortar_shorts.py`: nunca rebalancea el remanente (video 10 min -> 2 clips de 5 min + 1 de 45s). |
| Locucion con fallas (esp) | Chatterbox local fragmentado en pedazos de ~180 palabras concatenados = cortes/glitches. |
| Sin video 16:9 entregado | Los 16:9 se generaron bien pero la descarga scp se cortaba (sin resume) y se perdieron al destruir el pod. |
| Lentitud (6 hrs para 3 videos) | TTS autoregresivo Chatterbox a ~0.7x tiempo real + descarga de modelo VL + descargas frágiles. |

**Hilo comun**: se priorizo infraestructura barata/gratuita en vez de las
herramientas de pago ya disponibles. Eso costo calidad Y tiempo.

---

## Decisiones acordadas (12/08)

1. **TTS = Chatterbox SE QUEDA** (quemar saldo RunPod via `chatterbox-api`,
   $0.001/seg, que es la que funciona). NO se cambia por ahora.
2. **Miniaturas = Qwen-Image-Edit-2511 por API** (Replicate, ~$0.04/imagen).
   Calidad consistente, sin conflictos de diffusers, funciona desde la PC.
3. **Avatar = Qwen-Image-Edit por API** (mismo modelo que miniaturas).
   El plan original con Nano Banana fue descartado (retirado de HF).
4. **Transferencia = Rclone** (reemplaza el split/rejoin improvisado).
   Resume + checksum automatico. Instalar via winget.
5. **Enfoque**: piloto de 1 video para validar calidad, luego escalar a 3.

---

## Fase 0 — Limpieza (PENDIENTE, primero)

Borrar TODO el output residual del trabajo anterior (producto inaceptable):
- `output/shorts/` (8 archivos ~1.7GB, clips de 45s inutilizables)
- `output/miniaturas/` (3 genericas)
- `output/tarjetas/` (3, sin avatar real)
- `output/audio/`, `output/subtitulos_ass/`, `output/videos/`, `output/cta/`
- GUIONES: se conservan los 3 actuales para el piloto (~3100-3500 palabras,
  ~21-24 min) — decidido conservar.

CONSERVAR: `data/` (temas, banco, gameplay_urls), `storage/fotos/` (conejito),
`storage/voces/`, modelos Kokoro, fuente Montserrat.

## Fase 1 — Infraestructura de transferencia (reemplaza split/rejoin)

- Instalar **Rclone** via winget: `winget install Rclone.Rclone`
- Configurar SFTP hacia Vast.ai (host:puerto + clave SSH).
- Script `src/bajar_resultados.py`: `rclone copy` de `output/videos/`,
  `output/shorts/`, `output/miniaturas/`, `output/tarjetas/` del pod -> repo,
  con `--progress` y verificacion de integridad.
- Beneficio: si se corta, retoma donde quedo (resume) y verifica checksum.
- Los 3 videos 16:9 (~2GB) se bajan en una pasada confiable.

## Fase 2 — Avatar (Qwen API)

- Implementar `generar_avatar.py --backend api` (Replicate).
- Editar la foto del conejito (`storage/fotos/`) -> avatar conejito-robot
  con las 10 expresiones (neutral, feliz, triste, enojado, sorprendido,
  asustado, decepcionado, emocionado, pensativo, sospechoso).
- Salida: `storage/avatar/avatar_<expresion>.png`.
- NOTA: el `generar_avatar.py` actual usa `QwenImageEditPipeline` LOCAL con
  diffusers 0.29 — NO funciona (mismo conflicto que las miniaturas). Reescribir
  hacia API.

## Fase 3 — Miniaturas Qwen API

- Implementar `generar_miniaturas.py --backend api` real (Replicate).
- Prompt basado en la **premisa/gancho** del guion (ya hay `_leer_premisa`).
- Composicion con avatar + titulo (Pillow) — ya existe `componer_miniatura()`.
- Flujo: avatar -> escena Qwen API -> avatar+titulo -> `output/miniaturas/`.

## Fase 4 — Fixes de calidad

1. **`cortar_shorts.py`**: `_puntos_corte` debe redistribuir el remanente
   (si ultimo clip < 90s, fusionarlo con el anterior o rebalancear).
   Prohibido clips de 45s.
2. **Audio Chatterbox**: probar `chatterbox-api` (serverless) con el texto
   completo por llamada (sin fragmentacion local de ~180 palabras) para
   eliminar glitches. Verificar calidad por idioma y voz preset.

## Fase 5 — Piloto de 1 video

Flujo completo para 1 guion (el de mejor calidad):
1. Audio `chatterbox-api` -> QA de audio (whisper transcribe vs guion,
   detectar omisiones/cortes)
2. ASS 16:9 + 9:16
3. Video 16:9 + 9:16 (NVENC, gameplay lite completo)
4. Tarjeta Reddit (solo 16:9)
5. Avatar + Miniatura Qwen API + review Qwen2.5-VL local
6. Shorts (con fix de remanente)
7. **Bajar TODO con rclone** (garantiza el 16:9 entregado)

## Fase 6 — Validacion y escalado

- Revisar el piloto con el usuario (locucion, miniatura, shorts).
- Ajustar lo que falle. Luego producir los 3 de la semana.

---

## Costos estimados (por semana de 3 videos)

| Item | Costo |
|---|---|
| RunPod (chatterbox-api, 3x10 min = 1800s @ $0.001/seg) | ~$1.80 (quema saldo) |
| Replicate (miniaturas 3 + avatar 10) | ~$0.50 |
| Vast.ai (pod ~3-4 hrs @ $0.12) | ~$0.50 |
| DeepSeek (3 guiones) | ~$0.15 |
| **Total** | **~$3/semana** |

---

## Recordatorios criticos

- Chatterbox se mantiene como TTS hasta agotar saldo RunPod.
- Replicate requiere API key (`REPLICATE_API_TOKEN`) — configurar.
- Rclone: `winget install Rclone.Rclone`; configurar remote sftp.
- Ejecutar siempre desde la raiz del proyecto.
- Verificar cierre de pod al terminar cada sesion (0 instancias activas).
