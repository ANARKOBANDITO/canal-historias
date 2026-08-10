---
name: recover-batch
description: Recupera un lote interrumpido de generacion de guiones. Compara los temas pendientes contra los guiones ya generados, limpia la cola para dejar solo lo no procesado, y reanuda el lote automaticamente.
---

## Que hace este skill

Cuando `generar_lote.py` se interrumpe (timeout, error de API, cierre de terminal),
los temas pendientes quedan intactos en `data/temas_pendientes.txt` y los ya procesados
quedan en `output/guiones_listos/`. Este skill detecta la situacion y la resuelve.

## Procedimiento paso a paso

### 1. Verificar que haya algo que recuperar

Ejecuta:
```powershell
Get-Content "data/temas_pendientes.txt"
```
Si el archivo esta vacio, no hay nada que recuperar. Informa al usuario.

### 2. Comparar pendientes vs. generados

Para cada tema en `data/temas_pendientes.txt`, determina si ya existe un guion
correspondiente en `output/guiones_listos/`.

La correspondencia NO es exacta: el nombre del archivo de salida se genera con
`_nombre_archivo_valido()`, que toma el tema, limpia caracteres especiales,
convierte a lowercase, reemplaza espacios por `_` y trunca a 50 caracteres.
Es una coincidencia aproximada, no un match exacto.

Estrategia recomendada: para cada tema pendiente, genera su nombre de archivo
esperado aplicando la misma logica que `generar_lote.py`:
```python
import re
def nombre_archivo(tema):
    t = re.sub(r"[^\w\s-]", "", tema).strip().lower()
    t = re.sub(r"[\s]+", "_", t)
    return t[:50] + ".txt"
```
Luego verifica si ese archivo existe en `output/guiones_listos/`.

### 3. Clasificar temas

Resultado esperado: dos listas.
- **Ya procesados**: los temas cuyo `.txt` SI existe en `output/guiones_listos/`
- **Pendientes reales**: los temas cuyo `.txt` NO existe

### 4. Limpiar la cola

Sobrescribe `data/temas_pendientes.txt` SOLO con los pendientes reales:
```powershell
Set-Content -Path "data/temas_pendientes.txt" -Value @"
tema pendiente 1
tema pendiente 2
"@
```

### 5. Informar al usuario

Mostrar un resumen claro:
```
Lote interrumpido detectado:
  5 guiones ya generados (se conservan en output/guiones_listos/)
  3 temas pendientes por procesar
  2 temas quedan en data/temas_pendientes.txt
```

### 6. Ofrecer reanudar

Preguntar al usuario si quiere ejecutar el lote con los pendientes restantes.
Si acepta, ejecutar:
```bash
python src/generar_lote.py --genero hombre --minutos 20
```
(Ajustar `--genero` y `--minutos` segun lo que el usuario indique.)

## Notas importantes

- NUNCA borres `output/guiones_listos/`. Los guiones ya generados son validos.
- NUNCA borres `data/temas_usados.txt`. Lleva el historial completo.
- Los nombres de archivo pueden tener encoding raro en Windows (tildes, eñes).
  Usa `Get-ChildItem` de PowerShell para listar archivos, no Python puro.
- Si un tema aparece tanto en pendientes como en usados, esta DUPLICADO.
  En ese caso, eliminalo de pendientes (ya fue procesado en una ejecucion anterior).
