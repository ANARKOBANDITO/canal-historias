# NEXT STEPS — Pendientes del proyecto canal-historias

> Leer este archivo PRIMERO al retomar el proyecto.
> Contexto completo en `RESUMEN_PROYECTO.md` y convenciones en `AGENTS.md`.
> **PLAN DE CALIDAD vigente: `PLAN_CALIDAD.md`** — leerlo antes de producir.

---

## Estado actual (13/08, PILOTO ES ENTREGADO — feedback del usuario)

> El 13/08 se produjo el primer video piloto end-to-end (ES, 16 min) y se bajo
> con rclone. **Calidad MUCHO mejor que el 11/08** (audio sin glitches, 97% de
> cobertura, subtitulos perfectos segun el usuario). Queda pulir lo siguiente.

### Feedback del usuario (accionable)
1. **VOZ INCORRECTA**: el guion `descubri...` esta narrado por una MUJER
   (primera persona femenina: "mi novio...") pero el metadato `[GENERO: hombre]`
   y la locucion usaron la voz de HOMBRE (Alonso). FIX: coherencia genero-narrador
   en generacion (`validar_guiones.py` ya lo detecta).
2. **GUIONES con fallas**: palabras repetidas y frases mal redactadas → el TTS
   las lee con sonidos extraños. FIX: mejorar prompts anti-repeticion +
   `validar_guiones.py` (ya detecta repetidas consecutivas, n-gramas loop, frases largas).
3. **SONIDOS EXTRAÑOS en pausas** del narrador (como que va a hablar y solo
   respira). Causa probable: artefactos de Chatterbox en inicios de fragmento.
   FIX a investigar: silencio mas largo, fades por fragmento, o re-sintesis.
4. **GAMEPLAY PIXELEADO** (parece red inestable). Causa: gameplay_lite a
   2 Mbps (crf 28). FIX: subir bitrate (~6-8 Mbps, crf ~20) o usar el crudo.
5. **9:16 en partes cortas**: para un video de 16 min deben ser ~3 partes
   (5+5+6 min) con CTA narrado "para la parte X, like y seguir". Destino:
   TikTok/Shorts/Reels.

### Lo que quedo (13/08)
- Videos piloto en `output/videos/`: 16:9 (802MB) + 9:16 (948MB) + previews + frames.
- Audio `output/audio/...mp3` (alonso, 16 min) + ASS 16:9 y 9:16 (subtitulos APROBADOS).
- Referencias de voz del canal: `storage/voces/referencia_hombre.wav` (alonso) y
  `referencia_mujer.wav` (dalia), clonadas para TODOS los idiomas (es/en/pt).
- Scripts nuevos/mejorados: `qwen_api.py`, `generar_avatar.py` (API Replicate),
  `muestras_cross_idiomas.py`, `qa_audio.py`, `validar_guiones.py` (calidad
  narrativa), fragmentacion por parrafos en `generar_audio.py`, fixes en
  `ensamblar_video.py` (os.devnull), `cortar_shorts.py` (remanente <90s),
  `provisionar_vast.py` (BaseException + boot 1800s).
- **SE BORRARON** (13/08): muestras de voz (`output/muestras_voz/`) y guiones
  (`output/guiones_listos/`) — se regeneran con guiones mejorados.

---

## PLAN PARA MAÑANA (14/08)

### A. Assets del canal (usuario carga credito Replicate)
1. Cargar credito en replicate.com (hoy dio `402 Payment Required`).
2. **Avatar** (una vez): `python src/generar_avatar.py --todas` → 10 expresiones
   transparentes en `storage/avatar/`. Revisar fondo/transparencia.
3. **Miniaturas**: `python src/generar_miniaturas.py --procesar --backend api`
   (escena Qwen + avatar + titulo). Probar calidad de escena desde base oscura.
4. **Tarjeta Reddit / capturas tipo publicacion**: `generar_tarjeta_reddit.py`
   con el avatar (solo 16:9, duracion del gancho).
5. **Fotos de perfil y banners multi-idioma**: definir dimensiones (perfil ~512x512,
   banner ~1500x500 / 2048x1152) y generar para es/en/pt (Qwen-Image-Edit + Pillow).
   Skill: `assets-canal`.

### B. Mejorar guiones (fase escritura)
1. Corregir `[GENERO:]` para que SIEMPRE coincida con la voz del narrador:
   instruccion explicita en `system_esquema`/`system_capitulo` + correr
   `validar_guiones.py` post-generacion (chequea genero, repeticiones, frases largas).
2. Instrucciones anti-repeticion en prompts (nunca repetir palabras/frases).
3. Regenerar guiones con `generar_lote.py` y validarlos ANTES de locutar.

### C. Audio (artefactos en pausas)
1. Investigar los "sonidos extraños" en pausas: silencio mas largo, fade-in/out
   por fragmento, o re-sintesis de los fragmentos problematicos.
2. Validar siempre con `qa_audio.py` (cobertura >= 95% + final presente).

### D. Gameplay de calidad
1. Subir bitrate de `gameplay_lite.py` (crf 28/2M → crf ~20 / maxrate 6-8M).
2. O usar el gameplay crudo (177MB) directo en el pod.

### E. 9:16 en partes + CTA (Shorts/TikTok)
1. `cortar_shorts.py --procesar --minutos 5 --idioma <idioma>` → partes ~5 min
   (3 para un video de 16 min), corte en fin de capitulo, sin clips <90s.
2. CTA narrado "para la parte X, like y seguir" (visual + audio edge-tts).
3. `generar_cta_parte.py` para el CTA individual.

### F. Pipeline / rendimiento
1. **NVENC**: instalar en el pod un ffmpeg BtbN de release 2025 (nvenc API 13.0,
   compatible driver 570) → renders ~2 min en vez de ~25. Ver bloqueo abajo.
2. Re-producir el piloto ES con TODO (voz correcta, gameplay bueno, shorts con CTA,
   tarjeta + miniatura + avatar) y validar con el usuario.

---

## Historial

### 12/08 — Reconstruccion (Fase 0 y 1)
- Output residual limpiado, Rclone 1.75.0 (winget) + `src/bajar_resultados.py`.
- PLAN_CALIDAD.md aprobado (Chatterbox local, Qwen API, Rclone).

### 11/08 — Producido y RECHAZADO por calidad
- 8 shorts de 45s, miniaturas genericas, locucion con glitches (fragmentacion ~180 palabras).

### 10/08 — Primera sesion
- Pipeline CPU completo probado. RunPod Pods descartados (driver 580 roto).
- Chatterbox Turbo serverless OK. Nombre del canal: r/HopStories.

---

## GUIA DE ARRANQUE Vast.ai (automatizado)

```bash
# 0. Ver instancias validas AHORA (gratis, sin cuenta)
python src/buscar_vast.py

# 4. Alquilar la mas barata y probar en 1 paso (~$0.01 si el smoke falla):
python src/provisionar_vast.py --provisionar --clave "C:\Users\allen\.ssh\id_ed25519" --conservar
```

Pasos alternativos: `--alquilar <OFFER_ID>`, `--esperar <INSTANCE_ID>`,
`--smoke-test <ID> --clave ...` (cuInit == 0 obligatorio), `--instalar <ID>`,
`--probar-chatterbox <ID>`, `--destruir <ID>`.

**Regla de oro:** si `--smoke-test` falla (cuInit != 0), el script destruye solo
(~$0.01). Reintentar con otra oferta.

---

## NOTAS DE CONTEXTO IMPORTANTES

- **RunPod Pods NO funcionan** con CUDA (driver 580.95.05, cuInit=999).
  La API serverless Chatterbox Turbo SI funciona (solo lectura espanol aceptable,
  pero usa voz preset "lucy"; para la voz del canal usar Chatterbox LOCAL en Vast.ai).
- **Voz del canal**: narrador HOMBRE = alonso, MUJER = dalia, clonadas para es/en/pt.
  `generar_audio.py` elige la referencia por `[GENERO:]` (`VOZ_REFERENCIA_POR_GENERO`).
- **Vast.ai:** filtrar driver < 580. RTX 3090 ~$0.08-0.17/hr. Imagen
  `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`. SSH: clave `id_ed25519`.
- **Chatterbox-tts 0.1.7**: `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`;
  `from_pretrained(device=...)`. Fragmentar por parrafos (max_new_tokens=1000 hardcodeado).
- **Nunca usar Reddit real**: solo historias "tipo reddit" generadas con DeepSeek.
- **Licencias imagenes**: Qwen-Image-Edit = Apache 2.0 (OK comercial). FLUX = NON-COMMERCIAL (NO).
- **Nombres de archivo**: normalizar con `normalizar_nombre()`.
- **Ejecutar siempre desde la raiz del proyecto.**
- En Windows, ffmpeg: `$env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"`.

## BLOQUEOS CONOCIDOS (13/08) — no re-investigar

- **Host GPU caido = cambiar de host (leccion 13/08).** El host ssh3.vast.ai se
  cayo repetidamente (SSH banner timeout, "offline", scp colgado, boot > 15 min)
  y se perdio mucho tiempo insistiendo. **REGLA:** tras 2-3 fallos consecutivos,
  DESTRUIR y provisionar OTRO host. Automatizado:
  `python src/provisionar_vast.py --salud <ID> --clave ...` (diagnostico) y
  `--cambiar-de-host <ID> --clave ...` (destruir + reprovisionar). Registro en
  `data/hosts_descartados.txt`. Ver `.opencode/rules/vast-session.md`.
- **NVENC roto en Vast.ai (driver 570).** El pod RTX 3090 tiene driver 570 (nvenc API 13.0).
  - ffmpeg Ubuntu 22.04: h264_nvenc existe pero falla "No capable devices found".
  - johnvansickle static 7.0.2: NO compila nvenc.
  - BtbN `latest` (2026): exige nvenc API 13.1 / driver 610 → "Driver does not support...".
  - Resultado: render con `libx264` CPU (~25 min por video de 16 min, ~0.8-1 GB c/u).
  - **Fix pendiente:** ffmpeg BtbN de release 2025 (nvenc 13.0), o subir el filtro de `buscar_vast.py`. Ver `.opencode/rules/vast-session.md`.
- **Replicate 402 Payment Required.** La cuenta no tiene credito/billing → `generar_avatar.py`
  y `generar_miniaturas.py --backend api` fallan. Cargar credito en replicate.com.
- **Prueba larga Chatterbox trunca.** max_new_tokens=1000 hardcodeado (320 palabras → ~29s).
  `generar_audio.py --motor chatterbox` fragmenta por parrafos con pausas de 0.35s
  (fix 13/08, cobertura 97%).
