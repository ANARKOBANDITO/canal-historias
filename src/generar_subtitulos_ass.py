"""
generar_subtitulos_ass.py

Transcribe un archivo de audio con faster-whisper (word-level) y genera
un archivo .ASS con estilo karaoke: Montserrat Bold, blanco, borde
negro, centrado.

Uso (desde la raiz del proyecto):
    python src/generar_subtitulos_ass.py output/audio/mi_guion.mp3
    python src/generar_subtitulos_ass.py --audio output/audio/ --procesar
"""

import argparse
from pathlib import Path

from faster_whisper import WhisperModel

from utilidades import normalizar_nombre

CARPETA_AUDIO = Path("output/audio")
CARPETA_ASS = Path("output/subtitulos_ass")
FUENTE = Path("storage/Montserrat-Bold.ttf")
MODELO_WHISPER = "base"

# Config del estilo de subtitulos
FONT_SIZE = 48           # tamano para 16:9 (el doble del inicial 24)
FONT_SIZE_VERTICAL = 96  # tamano para 9:16 (muy grande, palabra por palabra)
PLAYRES_X_169 = 1920
PLAYRES_Y_169 = 1080
PLAYRES_X_916 = 1080
PLAYRES_Y_916 = 1920
MARGIN_V_169 = 80
MARGIN_V_916 = 900       # centrado vertical (~47% del alto 1920)
ALIGNMENT_169 = 2        # abajo centrado
ALIGNMENT_916 = 5        # centro
MAX_PALABRAS_LINEA_169 = 8   # 16:9: no limitar por palabras (gobierna SEGUNDOS_LINEA_169)
MAX_PALABRAS_LINEA_916 = 2   # 9:16: 1-2 palabras por linea
SEGUNDOS_LINEA_169 = 2.5     # 16:9: frases ~1s mas largas (cierra por tiempo, no por palabras)
COLOR_TEXTO = "&H00FFFFFF"       # blanco
COLOR_RESALTADO = "&H0000FFFF"   # amarillo
COLOR_BORDE = "&H00000000"       # negro
GROSOR_BORDE_169 = 4
GROSOR_BORDE_916 = 6


def _formato_ass(td_sec: float) -> str:
    """Convierte segundos a formato ASS: H:MM:SS.cc"""
    horas = int(td_sec // 3600)
    minutos = int((td_sec % 3600) // 60)
    segundos = int(td_sec % 60)
    centisecs = int((td_sec - int(td_sec)) * 100)
    return f"{horas}:{minutos:02d}:{segundos:02d}.{centisecs:02d}"


def _encabezado_ass(ruta_fuente: str, tamano: int, ancho: int, alto: int, margin_v: int, alignment: int, grosor_borde: float) -> str:
    return f"""[Script Info]
Title: Subtitulos generados automaticamente
ScriptType: v4.00+
PlayResX: {ancho}
PlayResY: {alto}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat-Bold,{tamano},{COLOR_TEXTO},{COLOR_RESALTADO},{COLOR_BORDE},&H00000000,-1,0,0,0,100,100,0,0,1,{grosor_borde},0,{alignment},50,50,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _generar_eventos_karaoke(palabras: list[dict], desplazamiento: float = 0.0, max_palabras: int = 3, max_segundos: float | None = None) -> str:
    """Genera eventos ASS con efecto karaoke (\\k por palabra).
    Cierra la linea al superar max_palabras, al superar max_segundos de duracion,
    o si hay una pausa larga entre palabras."""
    if not palabras:
        return ""

    lineas_texto = []
    linea_actual = []
    linea_inicio = None

    for i, w in enumerate(palabras):
        if not linea_actual:
            linea_inicio = w["start"]

        linea_actual.append(w)
        palabra_hora = w["start"] + desplazamiento

        # cerrar linea cuando llegamos al max de palabras, al max de segundos, o hay pausa larga
        cerrar = len(linea_actual) >= max_palabras
        if not cerrar and max_segundos is not None:
            cerrar = (w["end"] - linea_inicio) >= max_segundos
        if not cerrar and i < len(palabras) - 1:
            gap = palabras[i + 1]["start"] - w["end"]
            if gap > 0.5:
                cerrar = True

        if cerrar or i == len(palabras) - 1:
            linea_fin = w["end"] + desplazamiento
            inicio = _formato_ass(linea_inicio + desplazamiento)
            fin = _formato_ass(linea_fin + desplazamiento)

            partes = []
            for word in linea_actual:
                d = max(0, int((word["end"] - word["start"]) * 100))
                partes.append(f"{{\\k{d}}}{word['text']}")
            texto = " ".join(partes)

            lineas_texto.append(f"Dialogue: 0,{inicio},{fin},Default,,0,0,0,,{texto}")
            linea_actual = []
            linea_inicio = None

    return "\n".join(lineas_texto)


def _duracion_audio(ruta_audio: Path) -> float:
    """Obtiene la duracion del audio en segundos via ffprobe."""
    import subprocess
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(ruta_audio)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def _validar_timing(palabras: list[dict], duracion_audio: float) -> None:
    """Valida que los timestamps sean monotonicos y cubran el audio."""
    if not palabras:
        return

    ultimo_fin = 0.0
    solapados = 0
    for w in palabras:
        if w["start"] < ultimo_fin - 0.05:
            solapados += 1
        ultimo_fin = max(ultimo_fin, w["end"])

    inicio = palabras[0]["start"]
    fin = palabras[-1]["end"]

    print(f"  [VALIDACION] inicio={inicio:.2f}s, fin={fin:.2f}s, audio={duracion_audio:.2f}s, solapados={solapados}")
    if inicio > 0.5:
        print("    [AVISO] Los subtitulos empiezan tarde respecto al audio.")
    if duracion_audio > 0 and fin < duracion_audio - 1.0:
        print("    [AVISO] Los subtitulos terminan antes que el audio.")
    if solapados > 0:
        print(f"    [AVISO] {solapados} palabra(s) con timestamps solapados.")


def transcribir_y_generar_ass(ruta_audio: Path, ruta_ass: Path, vertical: bool = False, offset: float = 0.0, idioma: str | None = None) -> bool:
    ruta_fuente_absoluta = str(FUENTE.resolve())
    tamano = FONT_SIZE_VERTICAL if vertical else FONT_SIZE
    ancho = PLAYRES_X_916 if vertical else PLAYRES_X_169
    alto = PLAYRES_Y_916 if vertical else PLAYRES_Y_169
    margin_v = MARGIN_V_916 if vertical else MARGIN_V_169
    alignment = ALIGNMENT_916 if vertical else ALIGNMENT_169
    grosor_borde = GROSOR_BORDE_916 if vertical else GROSOR_BORDE_169
    max_palabras = MAX_PALABRAS_LINEA_916 if vertical else MAX_PALABRAS_LINEA_169
    max_segundos = None if vertical else SEGUNDOS_LINEA_169

    print(f"  Transcribiendo {ruta_audio.name}...")
    modelo = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")

    segmentos, info = modelo.transcribe(str(ruta_audio), word_timestamps=True, language=idioma or "es")

    todas_palabras = []
    for seg in segmentos:
        if seg.words:
            for w in seg.words:
                todas_palabras.append({
                    "start": w.start + offset,
                    "end": w.end + offset,
                    "text": w.word.strip(),
                })

    if not todas_palabras:
        print("  [ADVERTENCIA] No se detectaron palabras.")
        return False

    _validar_timing(todas_palabras, _duracion_audio(ruta_audio))

    encabezado = _encabezado_ass(ruta_fuente_absoluta, tamano, ancho, alto, margin_v, alignment, grosor_borde)
    eventos = _generar_eventos_karaoke(todas_palabras, max_palabras=max_palabras, max_segundos=max_segundos)

    ruta_ass.write_text(encabezado + eventos + "\n", encoding="utf-8")
    print(f"  ASS: {ruta_ass} ({len(todas_palabras)} palabras, {eventos.count(chr(10))+1} lineas)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Genera subtitulos ASS karaoke desde audio con faster-whisper.")
    parser.add_argument("audio", nargs="?", help="Ruta al archivo de audio (MP3 o WAV)")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los audios en output/audio/")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad de audios a procesar")
    parser.add_argument("--tamano", type=int, default=FONT_SIZE, help="Tamano de fuente base (16:9)")
    parser.add_argument("--vertical", action="store_true", help="Generar ASS para formato 9:16 (TikTok/Shorts)")
    parser.add_argument("--offset", type=float, default=0.0, help="Desplazamiento en segundos para ajustar timing (ej: -0.2 o 0.3)")
    parser.add_argument("--idioma", type=str, default=None, choices=["es", "en", "pt", "fr", "de", "auto"],
                        help="Idioma del audio para whisper (default: es. 'auto' = deteccion automatica)")
    args = parser.parse_args()

    if not FUENTE.exists():
        print(f"No se encontro la fuente Montserrat en {FUENTE}. Descargala primero.")
        return

    audios: list[Path] = []
    if args.audio:
        audios = [Path(args.audio)]
    elif args.procesar or args.cantidad:
        if not CARPETA_AUDIO.exists():
            print(f"No existe {CARPETA_AUDIO}/")
            return
        todos = sorted(CARPETA_AUDIO.glob("*.mp3")) + sorted(CARPETA_AUDIO.glob("*.wav"))
        audios = todos[: args.cantidad] if args.cantidad else todos
    else:
        print("Especifica un archivo de audio o usa --procesar.")
        return

    if not audios:
        print("No se encontraron archivos de audio para transcribir.")
        return

    CARPETA_ASS.mkdir(exist_ok=True)
    procesados = 0

    for i, audio in enumerate(audios, 1):
        print(f"[{i}/{len(audios)}] {audio.name}")
        nombre_base = normalizar_nombre(audio.stem, max_largo=60)
        sufijo = "_9x16" if args.vertical else ""
        ruta_ass = CARPETA_ASS / f"{nombre_base}{sufijo}.ass"

        idioma_whisper = None if args.idioma == "auto" else (args.idioma or "es")
        if transcribir_y_generar_ass(audio, ruta_ass, vertical=args.vertical, offset=args.offset, idioma=idioma_whisper):
            procesados += 1

    print(f"\nListo. {procesados}/{len(audios)} procesados.")


if __name__ == "__main__":
    main()
