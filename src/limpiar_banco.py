"""
limpiar_banco.py

Administra el banco de temas (data/banco_temas.pkl):
- Listar todos los temas almacenados
- Borrar uno o varios temas especificos
- Resetear el banco completo
- Exportar a archivo de texto

Uso (desde la raiz del proyecto):
    python src/limpiar_banco.py --listar
    python src/limpiar_banco.py --borrar "tema a borrar"
    python src/limpiar_banco.py --borrar-todo
    python src/limpiar_banco.py --exportar data/respaldo_temas.txt
"""

import argparse
import sys
from pathlib import Path

from banco_temas import cargar_banco

ARCHIVO_BANCO = Path("data/banco_temas.pkl")


def _confirmar(accion: str) -> bool:
    respuesta = input(f"Estas seguro de {accion}? [s/N]: ").strip().lower()
    return respuesta == "s"


def cmd_listar(banco: dict):
    if not banco["temas"]:
        print("El banco esta vacio.")
        return
    print(f"Banco de temas: {len(banco['temas'])} temas almacenados.\n")
    for i, tema in enumerate(banco["temas"], 1):
        print(f"  {i:3d}. {tema[:100]}")


def cmd_borrar(banco: dict, temas_a_borrar: list[str]):
    temas_restantes = [t for t in banco["temas"] if t not in temas_a_borrar]
    borrados = len(banco["temas"]) - len(temas_restantes)

    if borrados == 0:
        print("Ninguno de los temas indicados estaba en el banco.")
        return

    print(f"Se eliminaran {borrados} tema(s). El banco quedara con {len(temas_restantes)} temas.")
    if not _confirmar("aplicar este cambio"):
        print("Cancelado.")
        return

    from banco_temas import agregar_tema
    nuevo_banco = {"temas": [], "vectores": None}
    for t in temas_restantes:
        nuevo_banco = agregar_tema(t, nuevo_banco)
    print(f"Listo. {borrados} tema(s) eliminados. El banco ahora tiene {len(nuevo_banco['temas'])} temas.")


def cmd_borrar_todo():
    if not ARCHIVO_BANCO.exists():
        print("El banco ya esta vacio (no existe el archivo).")
        return
    if _confirmar("ELIMINAR TODO el banco de temas. Esto es IRREVERSIBLE"):
        ARCHIVO_BANCO.unlink()
        print("Banco eliminado. Se recreara vacio la proxima vez que se genere un tema.")
    else:
        print("Cancelado.")


def cmd_exportar(banco: dict, ruta: str):
    destino = Path(ruta)
    contenido = "\n".join(banco["temas"])
    destino.write_text(contenido, encoding="utf-8")
    print(f"Exportados {len(banco['temas'])} temas a {destino}")


def main():
    parser = argparse.ArgumentParser(description="Administra el banco de temas duplicados.")
    parser.add_argument("--listar", action="store_true", help="Mostrar todos los temas en el banco")
    parser.add_argument("--borrar", nargs="+", metavar="TEMA", help="Borrar uno o mas temas del banco")
    parser.add_argument("--borrar-todo", action="store_true", help="Eliminar el banco completo")
    parser.add_argument("--exportar", metavar="RUTA", help="Exportar todos los temas a un archivo de texto")
    args = parser.parse_args()

    if not any([args.listar, args.borrar, args.borrar_todo, args.exportar]):
        parser.print_help()
        sys.exit(1)

    banco = cargar_banco() if ARCHIVO_BANCO.exists() else {"temas": [], "vectores": None}

    if args.listar:
        cmd_listar(banco)
    elif args.borrar:
        cmd_borrar(banco, args.borrar)
    elif args.borrar_todo:
        cmd_borrar_todo()
    elif args.exportar:
        cmd_exportar(banco, args.exportar)


if __name__ == "__main__":
    main()
