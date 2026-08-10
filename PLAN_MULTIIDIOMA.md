# PLAN: Expansión multi-idioma del pipeline `canal-historias`

> **Estado: EN PRODUCCION PARCIAL.** El canal ya produce multi-idioma de
> forma operativa: **3 videos/semana = 2 en ingles + 1 en español o portugues
> (alternando)**. El pipeline acepta `--idioma es|en|pt` en audio, whisper y
> subtitulos. Este documento describe la fase FUTURA de separacion estructural
> completa por idioma (prompts nativos, carpetas `data/<idioma>/`,
> `output/<idioma>/`, banco de deduplicacion independiente). No ejecutar la
> migracion estructural hasta que se confirme explicitamente.

---

## 1. Objetivo

Agregar la capacidad de generar guiones nativos (no traducidos) en otros
idiomas (ingles, portugues, aleman, frances, u otros a definir), manteniendo
un unico pipeline de codigo compartido en `src/`, sin duplicar scripts por
idioma.

## 2. Decision de arquitectura

**`src/` se queda unico (no se duplica por idioma).** Los scripts se
parametrizan con un flag `--idioma` (default: `es`, para no romper el
funcionamiento actual). La convencion critica de la API DeepSeek
(`thinking: disabled`, valores minimos de `max_tokens`) vive en un solo
lugar y aplica igual sin importar el idioma.

**`data/` y `output/` SI se separan por idioma**, en subcarpetas. Razones:

1. `banco_temas.pkl` (deduplicacion por embeddings) debe ser independiente
   por idioma. El modelo `paraphrase-multilingual-MiniLM-L12-v2` es
   multilingue y podria detectar similitud entre una premisa en ingles y
   una en portugues -- eso NO es deseable, cada idioma necesita su propio
   banco de deduplicacion.
2. `temas_usados.txt`, `temas_pendientes.txt` y las estadisticas
   (`estadisticas.py`) se ensuciarian si se mezclan idiomas en los mismos
   archivos.

**Los prompts SI se separan por idioma, y deben ser redactados de forma
nativa, no traducidos.** Cada idioma tiene su propio archivo de categorias
e instrucciones de prompt, escrito directamente en ese idioma -- NO como
traduccion automatica de las categorias en español. Motivo: contenido
traducido literalmente se nota como traducido (dinamicas familiares,
expresiones y giros narrativos varian por cultura), y ademas genera riesgo
de que la plataforma detecte contenido duplicado entre canales/idiomas del
mismo proyecto.

## 3. Estructura de carpetas objetivo

```
canal-historias/
├── src/
│   ├── generar_temas.py          # acepta --idioma es|en|pt|de|fr (default: es)
│   ├── generar_historia.py       # acepta --idioma, carga prompts/<idioma>.py
│   ├── generar_lote.py           # acepta --idioma
│   ├── banco_temas.py            # recibe la ruta del .pkl correspondiente al idioma
│   ├── estadisticas.py           # acepta --idioma o muestra desglose por idioma
│   └── prompts/
│       ├── es.py                 # categorias + instrucciones nativas en español
│       ├── en.py                 # categorias + instrucciones nativas en ingles
│       ├── pt.py                 # categorias + instrucciones nativas en portugues
│       ├── de.py                 # categorias + instrucciones nativas en aleman
│       └── fr.py                 # categorias + instrucciones nativas en frances
├── data/
│   ├── es/
│   │   ├── temas_pendientes.txt
│   │   ├── temas_usados.txt
│   │   └── banco_temas.pkl
│   ├── en/
│   │   ├── temas_pendientes.txt
│   │   ├── temas_usados.txt
│   │   └── banco_temas.pkl
│   ├── pt/ ...
│   ├── de/ ...
│   └── fr/ ...
└── output/
    ├── es/guiones_listos/
    ├── en/guiones_listos/
    ├── pt/guiones_listos/
    ├── de/guiones_listos/
    └── fr/guiones_listos/
```

## 4. Cambios concretos requeridos (cuando se implemente)

1. Agregar argumento `--idioma` (default `"es"`) a `generar_temas.py`,
   `generar_historia.py`, `generar_lote.py`.
2. Crear `src/prompts/` con un archivo por idioma. Cada archivo expone al
   menos: lista de categorias (equivalente pero NO traduccion literal de
   las 15 categorias en español) e instrucciones de prompt para gancho,
   esquema y expansion de capitulos, redactadas nativamente.
3. Cambiar las rutas hardcodeadas de `data/` y `output/` para que se
   construyan como `data/<idioma>/...` y `output/<idioma>/guiones_listos/`
   segun el flag recibido.
4. Migrar los datos actuales (`data/temas_pendientes.txt`,
   `data/temas_usados.txt`, `data/banco_temas.pkl`,
   `output/guiones_listos/`) a `data/es/` y `output/es/` respectivamente,
   como parte de la migracion (para no perder el historial ya generado).
5. Actualizar `estadisticas.py` para poder filtrar o desglosar metricas por
   idioma.
6. Actualizar `AGENTS.md` y el subagente `scriptwriter.md` para documentar
   el flag `--idioma` y la ubicacion de `src/prompts/`.

## 5. Fuera de alcance por ahora (no incluir en esta fase)

- Voces de TTS por idioma (se define en la fase de integracion de audio,
  no en esta migracion de estructura).
- Decidir el orden en que se lanzan los idiomas (se definira aparte).
- Cualquier cambio a la logica interna de generacion (gancho/esquema/
  capitulos) mas alla de parametrizarla por idioma -- la logica narrativa
  en si no cambia.

## 6. Criterio de aceptacion

- `python src/generar_lote.py` (sin `--idioma`) sigue funcionando exactamente
  igual que hoy, generando en `data/es/` y `output/es/` -- cero regresion
  para el canal en español ya en marcha.
- `python src/generar_lote.py --idioma pt` genera premisas y guiones nativos
  en portugues, usando su propio banco de deduplicacion y su propia carpeta
  de salida, sin tocar ni mezclar los datos de `es/`.

---

## 7. Estado operativo actual (10/08)

El multi-idioma YA esta activo a nivel de audio/video sin separacion estructural:

| Capa | Estado | Como |
|---|---|---|
| Guiones | `--idioma` no implementado en generar_historia/lote | Se pide tema en el idioma deseado |
| Audio | ✅ `generar_audio.py --idioma en|es|pt` | Chatterbox (voice cloning) o edge-tts |
| Whisper | ✅ `generar_subtitulos_ass.py --idioma en|es|pt|auto` | Transcripcion multi-idioma |
| Subtitulos | ✅ Mismo `--idioma` | ASS karaoke en el idioma |
| Cadencia | ✅ 3/semana = 2 EN + 1 ES/PT alternando | Plan maestro (AGENTS.md) |

La separacion estructural de este plan (prompts nativos + carpetas por idioma
+ banco dedupe independiente) queda pendiente y se decide por separado si se
necesita. No es bloqueante para la produccion actual.
