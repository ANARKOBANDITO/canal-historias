"""
bajar_resultados.py

Baja los resultados del pipeline GPU desde una instancia Vast.ai al
repositorio local usando rclone (SFTP). Reemplaza el split/rejoin
improvisado con scp: rclone retoma donde quedo si la conexion se corta
(resume) y verifica la integridad con `rclone check`.

Baja por defecto (remoto -> local):
    output/videos/      -> output/videos/
    output/shorts/      -> output/shorts/
    output/miniaturas/  -> output/miniaturas/
    output/tarjetas/    -> output/tarjetas/

Con --todo agrega tambien:
    output/audio/           -> output/audio/
    output/subtitulos_ass/  -> output/subtitulos_ass/

Requisitos:
    - rclone instalado (winget install Rclone.Rclone)
    - Clave privada SSH registrada en la cuenta Vast.ai (--clave)
    - VAST_AI_API_KEY en el entorno para resolver el host/port de la
      instancia (o pasar --host/--port explicitos)

Uso (desde la raiz del proyecto):
    python src/bajar_resultados.py --instancia 12345678 --clave "C:\\Users\\allen\\.ssh\\id_ed25519"
    python src/bajar_resultados.py --instancia 12345678 --clave "..." --todo
    python src/bajar_resultados.py --host "1.2.3.4" --port 22000 --clave "..." --destruir 12345678
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_REMOTO = "/root/canal-historias"

RUTAS_CORE = [
    ("output/videos", "output/videos"),
    ("output/shorts", "output/shorts"),
    ("output/miniaturas", "output/miniaturas"),
    ("output/tarjetas", "output/tarjetas"),
]

RUTAS_TODO = [
    ("output/audio", "output/audio"),
    ("output/subtitulos_ass", "output/subtitulos_ass"),
]

WINGET_RCLONE = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Microsoft" / "WinGet" / "Packages"
)


def _encontrar_rclone() -> str:
    """Devuelve la ruta al binario de rclone o la primera en el PATH."""
    which = shutil.which("rclone")
    if which:
        return which
    candidatos = [
        WINGET_RCLONE / "Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "rclone-v1.75.0-windows-amd64" / "rclone.exe",
        Path("C:/Program Files/rclone/rclone.exe"),
        Path("C:/Program Files (x86)/rclone/rclone.exe"),
    ]
    for c in candidatos:
        if c.exists():
            return str(c)
    if WINGET_RCLONE.exists():
        coincidencias = sorted(WINGET_RCLONE.rglob("rclone.exe"))
        if coincidencias:
            return str(coincidencias[0])
    raise SystemExit(
        "No se encontro rclone. Instalalo con: winget install Rclone.Rclone"
    )


def _datos_conexion(inst_id: int | None, host: str | None, port: int | None) -> tuple[str, int]:
    """Resuelve host/port desde la instancia (API Vast) o los explicitos."""
    if host and port:
        return host, port
    if not inst_id:
        raise SystemExit("Falta --instancia (o --host + --port) para saber a donde conectarse.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from provisionar_vast import _datos_instancia  # noqa: E402

    print(f"  Resolviendo host/port de la instancia {inst_id}...")
    inst = _datos_instancia(inst_id)
    ssh_host = inst.get("ssh_host")
    ssh_port = inst.get("ssh_port")
    if not ssh_host or not ssh_port:
        raise SystemExit(f"No se pudo obtener ssh_host/ssh_port de la instancia {inst_id}.")
    return ssh_host, ssh_port


def _crear_config(rclone: str, host: str, port: int, clave: str, base: Path) -> Path:
    """Crea un archivo de config temporal con el remote sftp de la instancia."""
    cfg = base / "vast_rclone_tmp.conf"
    cmd = [
        rclone, "--config", str(cfg), "config", "create", "vast_sftp", "sftp",
        f"host={host}", f"port={port}", "user=root", f"key_file={clave}",
        "--non-interactive",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return cfg


def _dirs_remotas(rclone: str, cfg: Path) -> set[str]:
    """Devuelve el conjunto de carpetas presentes en output/ del pod."""
    cmd = [rclone, "--config", str(cfg), "lsd", f"vast_sftp:{BASE_REMOTO}/output/"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  [AVISO] No se pudo listar output/ en el pod: {proc.stderr.strip()[-200:]}")
        return set()
    carpetas = set()
    for linea in proc.stdout.splitlines():
        if linea.strip():
            carpetas.add(linea.strip().split()[-1])
    return carpetas


def _copiar(rclone: str, cfg: Path, remoto: str, local: Path) -> bool:
    """Copia una carpeta del pod al repo. True si rclone termino sin error."""
    local.mkdir(exist_ok=True, parents=True)
    cmd = [
        rclone, "--config", str(cfg), "copy",
        f"vast_sftp:{BASE_REMOTO}/{remoto}", str(local),
        "-v", "--progress", "--stats-one-line", "--stats", "10s",
        "--transfers", "4", "--retries", "3",
    ]
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        print(f"  [X] rclone copy fallo en {remoto} (rc={proc.returncode})")
        return False
    return True


def _verificar(rclone: str, cfg: Path, remoto: str, local: Path) -> bool:
    """Verifica integridad con rclone check. True si no hay diferencias."""
    cmd = [rclone, "--config", str(cfg), "check",
           f"vast_sftp:{BASE_REMOTO}/{remoto}", str(local)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"  [OK] {remoto} verificado (sin diferencias)")
        return True
    detalle = proc.stderr.strip() or proc.stdout.strip()
    print(f"  [X] {remoto} NO coincide: {detalle[-300:]}")
    return False


def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Baja resultados del pod Vast.ai al repo local con rclone (SFTP).")
    parser.add_argument("--instancia", type=int, default=None, help="ID de la instancia Vast.ai")
    parser.add_argument("--clave", required=True, help="Ruta a la clave privada SSH")
    parser.add_argument("--host", default=None, help="Host SSH (alternativa a --instancia)")
    parser.add_argument("--port", type=int, default=None, help="Puerto SSH (con --host)")
    parser.add_argument("--rclone", default=None, help="Ruta al binario de rclone")
    parser.add_argument("--todo", action="store_true", help="Bajar tambien audio y subtitulos")
    parser.add_argument("--destruir", action="store_true",
                        help="Destruir la instancia tras bajar y verificar todo OK")
    args = parser.parse_args()

    rclone = args.rclone or _encontrar_rclone()
    print(f"rclone: {rclone}")

    host, port = _datos_conexion(args.instancia, args.host, args.port)
    print(f"Pod: {host}:{port} (base remota {BASE_REMOTO})")

    rutas = RUTAS_CORE + (RUTAS_TODO if args.todo else [])
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _crear_config(rclone, host, port, args.clave, Path(tmp))
        disponibles = _dirs_remotas(rclone, cfg)

        ok = True
        bajadas = 0
        for remoto, local in rutas:
            carpeta = remoto.split("/")[-1]
            if disponibles and carpeta not in disponibles:
                print(f"  [SKIP] {remoto} no existe en el pod")
                continue
            print(f"\n  Bajando {remoto} -> {local}")
            if _copiar(rclone, cfg, remoto, Path(local)):
                if _verificar(rclone, cfg, remoto, Path(local)):
                    bajadas += 1
                else:
                    ok = False
            else:
                ok = False

    print(f"\nBajadas OK: {bajadas}/{len(rutas)} carpetas.")

    if args.destruir:
        if ok and args.instancia:
            print("\nVerificacion completa. Destruyendo instancia...")
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
            from provisionar_vast import destruir  # noqa: E402
            destruir(args.instancia)
        elif not ok:
            print("\n[AVISO] No se destruyo la instancia: hubo carpetas con errores.")
            print("  Revisar y reintentar la bajada antes de --destruir.")
        else:
            print("\n[AVISO] --destruir requiere --instancia.")

    if not ok:
        raise SystemExit("Hubo errores en la bajada. Reintentar con rclone (retoma solo lo faltante).")


if __name__ == "__main__":
    main()
