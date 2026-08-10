---
name: recover-video
description: Recupera una fase de video interrumpida. Detecta que guiones ya tienen audio, subtitulos ASS y videos generados, y reanuda el pipeline desde donde quedo sin regenerar lo ya hecho.
---

## Que hace este skill

Cuando el pipeline de video se interrumpe (timeout, cierre de terminal, error
de ffmpeg), algunas etapas quedaron hechas y otras no. Este skill detecta el
estado real de cada guion y reanuda solo lo que falta.

## Procedimiento paso a paso

### 1. Mapear el estado por guion

Para cada guion en `output/guiones_listos/` (usa nombres normalizados), verifica
que existe su archivo derivado:

```python
from pathlib import Path
from utilidades import normalizar_nombre

# nombre_base es el stem del guion normalizado
nombre_base = normalizar_nombre(guion.stem, max_largo=60)

estado = {
    "audio": Path(f"output/audio/{nombre_base}.mp3").exists(),
    "ass_16": Path(f"output/subtitulos_ass/{nombre_base}.ass").exists(),
    "ass_9": Path(f"output/subtitulos_ass/{nombre_base}_9x16.ass").exists(),
    "video_16": Path(f"output/videos/{nombre_base}_16x9.mp4").exists(),
    "video_9": Path(f"output/videos/{nombre_base}_9x16.mp4").exists(),
}
```

### 2. Clasificar cada guion

- **Completo**: audio + ASS(16 y 9) + video(16 y 9) existen → no tocar.
- **A medio camino**: faltan algunas etapas → reanudar desde la primera que falta.
- **Solo guion**: no tiene audio → empezar desde audio.

### 3. Reanudar por etapas (solo las que faltan)

Agregar ffmpeg al PATH si es necesario:
```powershell
$env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"
```

Etapas en orden, cada una se salta si su salida ya existe:
1. `python src/generar_audio.py --cantidad N --genero hombre`
2. `python src/generar_subtitulos_ass.py --procesar`
3. `python src/generar_subtitulos_ass.py --procesar --vertical`
4. `python src/ensamblar_video.py --procesar --tambien-vertical`
5. `python src/cortar_shorts.py --procesar`

### 4. Reportar

Mostrar un resumen:
```
Recuperacion de pipeline de video:
  4 guiones completos (se conservan)
  3 con audio y ASS, falta video
  2 sin audio
  1 sin gameplay de fondo (raw_gameplay/ vacio)
```

## Notas importantes

- NUNCA borres `output/audio/`, `output/subtitulos_ass/` ni `output/videos/`.
- Los archivos ya generados son validos y no se regeneran.
- Si `storage/raw_gameplay/` esta vacio, los videos se renderizan con fondo
  negro (ensamblar_video.py lo maneja solo) — avisale al usuario que falta gameplay.
- Los nombres de archivo pueden tener encoding raro en Windows. Usa
  `normalizar_nombre()` para derivar el nombre esperado.
