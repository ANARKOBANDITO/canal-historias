"""
cortar_shorts.py

Divide un video 9:16 pre-renderizado en clips para Shorts/Reels/TikTok.
Detecta pausas naturales entre subtitulos como puntos de corte para no
cortar a mitad de palabra ni de frase. Se priorizan los finales de
parrafo/capitulo del guion como puntos de corte (~5 min por parte).

Al final de cada parte agrega el CTA "like para la parte N":
  - Overlay visual (PNG generado por generar_cta_parte.py o aqui mismo)
  - Audio narrado (edge-tts) mezclado al final

IMPORTANTE: los videos deben estar pre-renderizados en 9:16 por
ensamblar_video.py --tambien-vertical.

Uso (desde la raiz del proyecto):
    python src/cortar_shorts.py output/videos/mi_video_9x16.mp4
    python src/cortar_shorts.py output/videos/mi_video_9x16.mp4 --minutos 5 --idioma es
    python src/cortar_shorts.py --procesar --minutos 5
"""

import argparse
import re
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

FFMPEG = "ffmpeg"
CARPETA_VIDEOS = Path("output/videos")
CARPETA_SHORTS = Path("output/shorts")
CARPETA_ASS = Path("output/subtitulos_ass")
CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_CTA = Path("output/cta")

DURACION_CLIP = 300  # duracion objetivo de cada short en segundos (~5 min)
MIN_DURACION_CLIP = 90  # minimo de un clip; por debajo se fusiona (prohibido clips de 45s)

TEXTO_CTA_POR_IDIOMA = {
    "es": "Para la parte {n}, dale like y seguí.",
    "en": "For part {n}, like and follow.",
    "pt": "Para a parte {n}, deixa o like e segue.",
}
VOZ_EDGE_POR_IDIOMA = {
    "es": "es-MX-JorgeNeural",
    "en": "en-US-GuyNeural",
    "pt": "pt-BR-AntonioNeural",
}


def _obtener_duracion_video(ruta_video: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(ruta_video)],
        capture_output=True, text=True,
    )
    return float(proc.stdout.strip())


def _leer_tiempos_ass(ruta_ass: Path) -> list[float]:
    tiempos = []
    if not ruta_ass.exists():
        return tiempos
    texto = ruta_ass.read_text(encoding="utf-8")
    for linea in texto.split("\n"):
        if linea.startswith("Dialogue:"):
            partes = linea.split(",")
            if len(partes) >= 3:
                end_str = partes[2]
                match = re.match(r"(\d+):(\d+):(\d+)\.(\d+)", end_str)
                if match:
                    h, m, s, c = int(match[1]), int(match[2]), int(match[3]), int(match[4])
                    segundos = h * 3600 + m * 60 + s + c / 100.0
                    tiempos.append(segundos)
    return sorted(tiempos)


def _rebalancear_cortes(cortes: list[float], duration: float, minimo: float = MIN_DURACION_CLIP) -> list[float]:
    """Fusiona segmentos < minimo para que ningun clip quede corto (ej. 45s).

    Se eliminan cortes hasta que todos los segmentos cumplan el minimo.
    Si al final queda un solo segmento, se devuelve [] (no dividir).
    """
    puntos = [0.0] + cortes + [duration]
    cambiado = True
    while cambiado:
        cambiado = False
        for i in range(len(puntos) - 1):
            seg = puntos[i + 1] - puntos[i]
            if seg < minimo:
                if i < len(puntos) - 2:
                    del puntos[i + 1]  # fusionar corto con el siguiente
                else:
                    del puntos[i]      # ultimo corto: fusionar con el anterior
                cambiado = True
                break
    resultado = puntos[1:-1]
    if len(resultado) <= 1:
        return []
    return resultado


def _puntos_corte(duration: float, tiempos_sub: list[float], duracion_objetivo: float = DURACION_CLIP, puntos_capitulo: list[float] | None = None) -> list[float]:
    if duration <= duracion_objetivo * 1.5:
        return []

    cortes = []
    cursor = duracion_objetivo

    while cursor < duration - 30:
        mejor = None
        # 1) si hay final de capitulo cerca, es el mejor candidato
        if puntos_capitulo:
            for t in puntos_capitulo:
                if t > cursor - 10 and abs(t - cursor) < 25:
                    if mejor is None or abs(t - cursor) < abs(mejor - cursor):
                        mejor = t
        # 2) sino, pausa natural entre subtitulos
        if mejor is None:
            for t in tiempos_sub:
                if abs(t - cursor) < 15:
                    if mejor is None or abs(t - cursor) < abs(mejor - cursor):
                        mejor = t
        if mejor:
            cortes.append(mejor)
        else:
            cortes.append(cursor)
        cursor = cortes[-1] + duracion_objetivo

    return _rebalancear_cortes(cortes, duration)


def _leer_fines_capitulo(ruta_guion: Path) -> list[float]:
    """Estima el tiempo de cada fin de capitulo como fraccion del guion.
    Retorna tiempos relativos (0-1) multiplicados por la duracion del video.
    Nota: requiere ASS para mapear palabras a tiempo; aqui se usa una heuristica
    simple de fracciones por parrafo."""
    if not ruta_guion.exists():
        return []
    texto = ruta_guion.read_text(encoding="utf-8")
    parrafos = [p for p in texto.split("\n\n") if p.strip() and not p.strip().startswith("[")]
    if not parrafos:
        return []
    # distribuir los cortes aproximadamente en el tiempo: cada parrafo ocupa
    # una porcion del audio (los mas largos ocupan mas).
    pesos = [len(p) for p in parrafos]
    total = sum(pesos)
    acum = 0.0
    fracciones = []
    for i, p in enumerate(parrafos[:-1]):
        acum += pesos[i] / total
        fracciones.append(acum)
    return fracciones


def _generar_audio_cta(ruta_mp3: Path, texto: str, idioma: str) -> bool:
    """Genera audio narrado del CTA con edge-tts. True si ok."""
    try:
        import asyncio
        import edge_tts
    except ImportError:
        return False

    async def _run():
        voz = VOZ_EDGE_POR_IDIOMA.get(idioma, "es-MX-JorgeNeural")
        communicate = edge_tts.Communicate(texto, voz)
        with open(ruta_mp3, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

    try:
        asyncio.run(_run())
        return ruta_mp3.exists() and ruta_mp3.stat().st_size > 0
    except Exception:
        return False


def _generar_overlay_cta(ruta_png: Path, texto: str) -> bool:
    """Genera PNG 1080x300 con el texto del CTA."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (1080, 300), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            fuente = ImageFont.truetype("storage/Montserrat-Bold.ttf", 72)
        except Exception:
            fuente = ImageFont.load_default()
        draw.rounded_rectangle([40, 40, 1040, 260], radius=40, fill=(0, 0, 0, 170))
        try:
            bbox = draw.textbbox((0, 0), texto, font=fuente)
            w = bbox[2] - bbox[0]
            draw.text(((1080 - w) // 2, 90), texto, fill=(255, 255, 255), font=fuente)
        except Exception:
            draw.text((400, 100), texto, fill=(255, 255, 255), font=fuente)
        ruta_png.parent.mkdir(exist_ok=True, parents=True)
        img.save(str(ruta_png))
        return True
    except Exception:
        return False


def _extraer_clip(ruta_video: Path, ruta_out: Path, inicio: float, duracion: float) -> None:
    args = [
        FFMPEG, "-y",
        "-ss", str(inicio), "-i", str(ruta_video),
        "-t", str(duracion),
        "-c:v", "copy", "-c:a", "copy",
        str(ruta_out),
    ]
    subprocess.run(args, capture_output=True, check=True)


def _aplicar_cta(ruta_clip: Path, ruta_out: Path, siguiente_parte: int, idioma: str) -> None:
    """Agrega overlay visual + audio narrado del CTA al final del clip."""
    texto = TEXTO_CTA_POR_IDIOMA.get(idioma, TEXTO_CTA_POR_IDIOMA["es"]).format(n=siguiente_parte)

    # 1) audio narrado
    ruta_cta_mp3 = CARPETA_CTA / f"cta_p{ siguiente_parte - 1:02d}_{idioma}.mp3"
    if not ruta_cta_mp3.exists():
        _generar_audio_cta(ruta_cta_mp3, texto, idioma)

    # 2) overlay visual
    ruta_cta_png = CARPETA_CTA / f"cta_p{siguiente_parte - 1:02d}_{idioma}.png"
    if not ruta_cta_png.exists():
        _generar_overlay_cta(ruta_cta_png, texto)

    # 3) mezclar: clip + overlay + audio cta al final
    duracion_clip = _obtener_duracion_video(ruta_clip)
    duracion_cta = _obtener_duracion_video(ruta_cta_mp3) if ruta_cta_mp3.exists() else 0.0
    overlay_start = max(0, duracion_clip - duracion_cta - 0.5)

    # Inputs: [0]=clip, [1]=audio cta (si existe), [2]=overlay png (si existe)
    args = [FFMPEG, "-y", "-i", str(ruta_clip)]
    idx_png = None
    if ruta_cta_mp3.exists():
        args += ["-i", str(ruta_cta_mp3)]
    if ruta_cta_png.exists():
        args += ["-i", str(ruta_cta_png)]
        idx_png = 2 if ruta_cta_mp3.exists() else 1

    fc = []
    maps = []
    if ruta_cta_png.exists():
        fc.append(f"[{idx_png}:v]format=rgba,scale=1080:300,setpts=PTS-STARTPTS+{overlay_start}/TB[cta];[0:v][cta]overlay=0:0:shortest=1[vout]")
        maps.append("[vout]")
    else:
        maps.append("0:v")
    if ruta_cta_mp3.exists():
        fc.append(f"[0:a]volume=1.0[a1];[1:a]adelay={int(overlay_start * 1000)}|{int(overlay_start * 1000)}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=3[aout]")
        maps.append("[aout]")
    else:
        maps.append("0:a")

    if fc:
        args += ["-filter_complex", ";".join(fc)]
    for m in maps:
        args += ["-map", m]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "128k", str(ruta_out)]
    subprocess.run(args, capture_output=True, check=True)


def _cortar_shorts(ruta_video: Path, ruta_ass: Path, minutos: int, idioma: str, ruta_guion: Path | None = None) -> None:
    nombre_base = ruta_video.stem.replace("_9x16", "")

    duration = _obtener_duracion_video(ruta_video)
    tiempos_sub = _leer_tiempos_ass(ruta_ass) if ruta_ass.exists() else []

    # puntos de capitulo del guion (fracciones del audio)
    capitulos = _leer_fines_capitulo(ruta_guion) if ruta_guion else []
    puntos_capitulo = [f * duration for f in capitulos] if capitulos else None

    cortes = _puntos_corte(duration, tiempos_sub, duracion_objetivo=minutos * 60, puntos_capitulo=puntos_capitulo)

    if not cortes:
        ruta_tmp = CARPETA_SHORTS / f"{nombre_base}_shorts_001_tmp.mp4"
        _extraer_clip(ruta_video, ruta_tmp, 0, duration)
        ruta_out = CARPETA_SHORTS / f"{nombre_base}_shorts_001.mp4"
        _aplicar_cta(ruta_tmp, ruta_out, 2, idioma)
        ruta_tmp.unlink(missing_ok=True)
        print(f"  1 clip (sin dividir, {duration:.0f}s) -> {ruta_out}")
        return

    cortes_completos = [0.0] + cortes + [duration]

    for i in range(len(cortes_completos) - 1):
        inicio = cortes_completos[i]
        fin = cortes_completos[i + 1]

        ruta_tmp = CARPETA_SHORTS / f"{nombre_base}_shorts_{i + 1:03d}_tmp.mp4"
        ruta_out = CARPETA_SHORTS / f"{nombre_base}_shorts_{i + 1:03d}.mp4"
        _extraer_clip(ruta_video, ruta_tmp, inicio, fin - inicio)
        _aplicar_cta(ruta_tmp, ruta_out, i + 2, idioma)
        ruta_tmp.unlink(missing_ok=True)
        print(f"  Clip {i+1}: {inicio:.0f}s - {fin:.0f}s ({fin-inicio:.0f}s) -> {ruta_out}")


def main():
    parser = argparse.ArgumentParser(description="Divide video 9:16 en clips para Shorts, con CTA 'like para la parte N'.")
    parser.add_argument("video", nargs="?", help="Ruta a un video 9:16")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los videos 9:16 en output/videos/")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad a procesar")
    parser.add_argument("--minutos", type=int, default=DURACION_CLIP // 60, help="Duracion objetivo de cada parte en minutos (default: 5)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default="es", help="Idioma del texto/audio del CTA")
    args = parser.parse_args()

    videos: list[Path] = []
    if args.video:
        videos = [Path(args.video)]
    elif args.procesar or args.cantidad:
        if not CARPETA_VIDEOS.exists():
            print(f"No existe {CARPETA_VIDEOS}/")
            return
        todos = sorted(CARPETA_VIDEOS.glob("*_9x16.mp4"))
        videos = todos[: args.cantidad] if args.cantidad else todos
    else:
        print("Especifica un archivo de video o usa --procesar.")
        return

    if not videos:
        print("No se encontraron videos 9:16 (_9x16.mp4) para cortar.")
        return

    CARPETA_SHORTS.mkdir(exist_ok=True)
    CARPETA_CTA.mkdir(exist_ok=True)

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.name}")
        nombre_base = normalizar_nombre(video.stem.replace("_9x16", ""), max_largo=60)
        ruta_ass = CARPETA_ASS / f"{nombre_base}_9x16.ass"
        ruta_guion = CARPETA_GUIONES / f"{nombre_base}.txt"
        if not ruta_guion.exists():
            ruta_guion = None
        _cortar_shorts(video, ruta_ass, args.minutos, args.idioma, ruta_guion)

    print(f"\nListo. Shorts generados en {CARPETA_SHORTS}/.")


if __name__ == "__main__":
    main()
