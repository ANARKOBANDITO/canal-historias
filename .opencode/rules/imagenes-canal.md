# Miniaturas, tarjeta Reddit y avatar (imagenes del canal)

## Identidad del canal

- Nombre: **r/HopStories** (username en la tarjeta Reddit).
- Avatar: conejito-robot estilo Snoo adaptado (NO el logo oficial de Reddit).
  Prioridad: parecerse MAS al conejito que al robot de Reddit.
  10 expresiones: neutral, feliz, triste, enojado, sorprendido, asustado,
  decepcionado, emocionado, pensativo, sospechoso. PNG transparente en `storage/avatar/`.
- **Nano Banana FUE RETIRADO de HF** (google/nano-banana da 404, incluso con
  token). El avatar se genera con **Qwen-Image-Edit-2511** (editar la foto del
  conejito en `storage/fotos/`), el mismo modelo que las miniaturas.

## Licencias (canal monetizado — CRITICO)

- **FLUX.1 Kontext dev = NON-COMMERCIAL. NO USAR** en canal monetizado.
- **Qwen-Image-Edit-2511 = Apache 2.0** (uso comercial OK). Usar para miniaturas Y avatar.
- **Qwen2.5-VL-7B-Instruct** (publico, no gated) para review de frames/miniaturas.
- **MiniMax M3** solo por API si el usuario decide pagarla (revisar licencia al configurar).

## Modelos de imagen (decision 11/08)

| Modelo | Uso | Tamano | En RTX 3090 24GB |
|---|---|---|---|
| Qwen-Image-Edit-2511 (bf16) | Escena miniatura / avatar | 38.3 GB | NO sin cuantizar |
| Qwen-Image-Edit-2511 GGUF **Q4_K_M** | Escena miniatura / avatar | 12.3 GB | SI |
| Qwen2.5-VL-7B-Instruct | Review frames/miniaturas/tarjetas | 15.4 GB | SI (publico) |

## Scripts

| Script | Funcion |
|---|---|
| `generar_tarjeta_reddit.py` | Tarjeta estilo publicacion Reddit (avatar + `r/HopStories` + texto del gancho). Overlay SOLO en 16:9, duracion = gancho. `--usuario`, `--segundos N`. |
| `generar_miniaturas.py` | Escena con Qwen-Image-Edit-2511 (`--backend local` en Vast.ai, o `api`) + composicion con avatar + titulo (Pillow). **El prompt usa el GANCHO del guion (premisa), no el nombre de archivo.** |
| `concatenar_miniatura.py` | Composicion final separada (escena + avatar + titulo). |
| `revisar_miniaturas.py` | Review con Qwen2.5-VL-7B local (`--backend local`) o MiniMax M3 (`--backend api`). Modo `--frames` para frames de video. Puntaje + clickability + sugerencia. |

## Convenciones

- Salida: tarjetas en `output/tarjetas/`, miniaturas en `output/miniaturas/`,
  escenas temporales en `output/miniaturas/_escenas/`.
- La tarjeta Reddit y las miniaturas usan `storage/Montserrat-Bold.ttf`.
- Avatar por expresion: se detecta el tono del guion por palabras clave
  (triste/enojado/feliz...) y se usa el PNG correspondiente.
- Pillow es dependencia obligatoria (`pip install pillow`).
- En el pod, cargar Qwen-Image-Edit con cuantizacion 4-bit (bitsandbytes) para
  que quepa en 24GB: `pipe = QwenImageEditPipeline.from_pretrained(..., load_in_4bit=True)`.
