Para cualquier llamada a la API de DeepSeek (deepseek-v4-flash), siempre
inclui `extra_body={"thinking": {"type": "disabled"}}` en el
chat.completions.create del cliente OpenAI.

Valores minimos de max_tokens segun la funcion:
- ganchos: 200
- generacion de premisas/temas: 400
- capitulos o narracion larga: 2000
- esquemas: 4000

Si un script falla con respuesta vacia de la API, verificar primero que
estos valores sean correctos ANTES de asumir otro tipo de error.
