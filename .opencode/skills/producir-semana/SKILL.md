---
name: producir-semana
description: Guia la produccion semanal completa de 3 videos (2 en ingles + 1 en español o portugues alternando), desde guiones hasta clips 9:16 con CTA, en una sola sesion GPU (opcion A). Incluye tarjeta Reddit 16:9, miniaturas y revision con MiniMax M3.
---

## Que hace este skill

Orquesta la cadencia semanal del plan maestro: producir los 3 videos de la
semana en UNA sesion de trabajo (opcion A), dejando todo listo para que el
usuario suba a las plataformas en los dias que prefiera.

## Cadencia semanal

- **3 videos/semana**: 2 en ingles + 1 en español o portugues (alternando).
- Cada historia ~20-25 min de audio.
- Por cada historia se genera: 16:9 (YouTube) + 9:16 dividido en partes ~5 min
  con CTA "like para la parte N".

## Flujo completo (una historia)

### 1. Guion
```bash
python src/generar_lote.py --genero hombre --minutos 20
```
Verificar que el guion tenga `[IDIOMA: en|es|pt]` y el gancho en el primer parrafo.

### 2. Audio
- Mes 1 (quemar saldo RunPod): `python src/generar_audio.py --motor chatterbox-api --idioma <idioma>`
- Mes 2+ (Vast.ai local): `python src/generar_audio.py --motor chatterbox --idioma <idioma>`

### 3. Subtitulos
```bash
python src/generar_subtitulos_ass.py --procesar --idioma <idioma>
python src/generar_subtitulos_ass.py --procesar --vertical --idioma <idioma>
```

### 4. Videos
```bash
python src/ensamblar_video.py --procesar --tambien-vertical
```

### 5. Tarjeta Reddit (SOLO 16:9)
```bash
python src/generar_tarjeta_reddit.py --procesar --usuario "r/HopStories"
```

### 6. Miniaturas
```bash
python src/generar_miniaturas.py --procesar
```

### 7. Revision M3
```bash
python src/revisar_miniaturas.py --procesar
```

### 8. Partes 9:16 con CTA
```bash
python src/cortar_shorts.py --procesar --minutos 5 --idioma <idioma>
```

## Notas

- Hacer las 3 historias de la semana en una sola pasada (opcion A) para
  amortizar el arranque de la instancia GPU y la carga de modelos.
- El 9:16 NO lleva tarjeta Reddit (solo gameplay vertical + subtitulos).
- El CTA dice "like para la parte N" con N = parte siguiente (parte 2 → "parte 3").
- El usuario sube luego a YouTube (16:9) y TikTok/Reels/IG (partes 9:16).
