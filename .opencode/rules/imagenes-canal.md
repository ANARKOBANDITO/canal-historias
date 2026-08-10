# Miniaturas, tarjeta Reddit y avatar (imagenes del canal)

## Identidad del canal

- Nombre: **r/HopStories** (username en la tarjeta Reddit).
- Avatar: conejito-robot estilo Snoo adaptado (NO el logo oficial de Reddit).
  Prioridad: parecerse MAS al conejito que al robot de Reddit.
  Se genera UNA vez con Nano Banana 2 (27B, GPU A6000 48GB) + variantes de expresion.
- 10 expresiones: neutral, feliz, triste, enojado, sorprendido, asustado,
  decepcionado, emocionado, pensativo, sospechoso. PNG transparente en `storage/avatar/`.

## Licencias (canal monetizado — CRITICO)

- **FLUX.1 Kontext dev = NON-COMMERCIAL. NO USAR** en canal monetizado.
- **Qwen-Image-Edit-2511 = Apache 2.0** (uso comercial OK). Usar para miniaturas.
- **Nano Banana (Gemma 3) = licencia Gemma** (comercial OK, revisar prohibidos). Usar para avatar.
- **MiniMax M3** para revision de miniaturas (revisar licencia al configurar).

## Scripts

| Script | Funcion |
|---|---|
| `generar_tarjeta_reddit.py` | Tarjeta estilo publicacion Reddit (avatar + `r/HopStories` + texto del gancho). Overlay SOLO en 16:9, duracion = gancho. `--usuario`, `--segundos N`. |
| `generar_miniaturas.py` | Escena con Qwen-Image-Edit-2511 (`--backend local` en Vast.ai, o `api`) + composicion con avatar + titulo (Pillow). |
| `concatenar_miniatura.py` | Composicion final separada (escena + avatar + titulo). |
| `revisar_miniaturas.py` | Review con MiniMax M3 (`--backend api|local`). Puntaje + clickability + sugerencia. |

## Convenciones

- Salida: tarjetas en `output/tarjetas/`, miniaturas en `output/miniaturas/`,
  escenas temporales en `output/miniaturas/_escenas/`.
- La tarjeta Reddit y las miniaturas usan `storage/Montserrat-Bold.ttf`.
- Avatar por expresion: se detecta el tono del guion por palabras clave
  (triste/enojado/feliz...) y se usa el PNG correspondiente.
- Pillow es dependencia obligatoria (`pip install pillow`).
