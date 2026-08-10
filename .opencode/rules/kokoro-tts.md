Kokoro es el motor TTS local del proyecto. Datos clave:

- Modelos en `storage/`:
  - `kokoro-v1.0.onnx` (310 MB)
  - `voices-v1.0.bin` (27 MB)
- Voces en espanol: `em_alex` (hombre) y `ef_dora` (mujer).
- Genera WAV a 24kHz; se convierte a MP3 con ffmpeg
  (`-codec:a libmp3lame -qscale:a 2`).
- En CPU, un guion de 20 min tarda ~3-5 min. Para pruebas rapidas
  usar `--motor edge` (edge-tts, mas rapido, en la nube).

Uso:
    python src/generar_audio.py --cantidad 5 --genero hombre --motor kokoro

- El script auto-detecta el genero del guion por su metadato `[GENERO: hombre]`.
- `--voz "em_alex"` fuerza una voz especifica e ignora el metadato.
- `--rate 0.9` ajusta la velocidad (0.5-2.0).
- Si `kokoro_onnx` o los modelos no estan, verificar instalacion y storage/.
