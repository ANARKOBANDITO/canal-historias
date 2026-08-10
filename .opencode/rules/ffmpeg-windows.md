En Windows, ffmpeg puede no estar en el PATH. Agregalo antes de cualquier
llamada o usa la ruta completa:
    $env:Path = "$env:Path;$env:LOCALAPPDATA\ffmpeg\ffmpeg-9.0-essentials_build\bin"

Los filtros de subtitulos ASS en ffmpeg necesitan rutas con forward slashes
y el `:` de la letra de unidad escapado:
    ass=filename='C:/ruta/archivo.ass':fontsdir='C:/ruta/fonts'

Puntos importantes:
- `fontsdir` es una opcion DEL FILTRO `ass=`, NO una opcion global de ffmpeg.
  Pasarlo como `-fontsdir` a nivel global da error "Unrecognized option".
- El video 9:16 se renderiza INDEPENDIENTE desde el gameplay con
  `crop=iw*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920:flags=lanczos`.
  No recortar un video 16:9 ya renderizado a `crop=1080:1920` (es invalido:
  la fuente de 1920x1080 no tiene 1920 de alto).
- Para loop infinito de gameplay: `-stream_loop -1`.
- Si no hay gameplay, la fuente `color=black` debe usarse con `-stream_loop -1`
  o la duracion correcta para que el video dure igual que el audio.
