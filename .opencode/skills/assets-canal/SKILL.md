---
name: assets-canal
description: Guia la produccion de los assets visuales del canal (una vez por canal y por idioma): avatar del conejito-robot (10 expresiones, PNG transparente), foto de perfil y banner para los canales multi-idioma (es/en/pt), usando Qwen-Image-Edit-2511 por API (Replicate) + Pillow. ACTIVAR cuando el usuario pida: generar/crear el avatar del canal, fotos de perfil, banners, o capturas tipo publicacion de Reddit.
---

## Que hace este skill

Genera los assets visuales de identidad del canal `r/HopStories`:

1. **Avatar** (una vez): 10 expresiones (neutral, feliz, triste, enojado,
   sorprendido, asustado, decepcionado, emocionado, pensativo, sospechoso),
   PNG transparente en `storage/avatar/avatar_<expresion>.png`.
2. **Foto de perfil** por idioma (~512x512) en `storage/perfil/`.
3. **Banner de canal** por idioma (~1500x500 o 2048x1152) en `storage/banners/`.
4. **Captura tipo publicacion de Reddit** (gancho) → `generar_tarjeta_reddit.py`.

## Prerequisitos

- `REPLICATE_API_TOKEN` con **credito cargado** (sin credito da `402 Payment Required`).
- Foto del conejito del usuario en `storage/fotos/` (<= 256 KB para data URL).
- `storage/Montserrat-Bold.ttf` para textos con Pillow.

## Pasos

### 1. Avatar (una vez, ~$0.40 por 10 expresiones)
```bash
python src/generar_avatar.py --todas
```
- Usa `src/qwen_api.py` (data URL de la foto + prediccion Qwen-Image-Edit).
- El fondo se pide blanco liso y se quita en post-proceso (Pillow) → transparente.
- Revisar que las 10 expresiones esten en `storage/avatar/` y que el recorte
  no tenga bordes feos.

### 2. Foto de perfil por idioma (~512x512)
- Componer con Pillow: avatar (expresion neutral/feliz) + fondo del color del
  idioma + opcionalmente el codigo del idioma. Salida `storage/perfil/perfil_<idioma>.png`.

### 3. Banner por idioma (~1500x500 / 2048x1152)
- Fondo escena generada con Qwen-Image-Edit (prompt segun el idioma/canal) +
  avatar + nombre `r/HopStories` + tagline. Salida `storage/banners/banner_<idioma>.png`.

### 4. Tarjeta Reddit (captura tipo publicacion)
```bash
python src/generar_tarjeta_reddit.py --procesar --usuario "r/HopStories"
```
- Solo se superpone al 16:9 (duracion del gancho). Requiere el avatar.

## Notas

- Los archivos de entrada <= 256 KB van como data URL; para mayores hostearlos
  con un URL publico (regla de Replicate).
- Qwen-Image-Edit es modelo de EDICION: los prompts deben indicar "edita/convie
  rte/coloca sobre fondo ..." y referenciar que mantener.
- Ejecutar siempre desde la raiz del proyecto.
