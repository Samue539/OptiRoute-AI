# OptiRoute AI frontend

Dashboard local en React, TypeScript y Vite para consultar rutas, ejecutar la
planificacion multi-entrega y solicitar el analisis logistico determinista.

## Requisitos

- Node.js 22.12 o posterior.
- Backend FastAPI disponible (por defecto en `http://127.0.0.1:8000`).

## Configuracion local

1. Copiar `.env.example` a `.env.local` si se necesita cambiar la URL de la API.
2. Instalar las dependencias con `npm install`.
3. Iniciar desarrollo con `npm run dev`.

La variable `VITE_API_URL` es la unica configuracion de conexion del cliente.
No contiene secretos.

## Validacion

```text
npm run lint
npm run build
```

Las pantallas de pedidos, vehiculos y conductores muestran estados vacios hasta
que el backend publique endpoints de catalogo. El frontend no genera registros
ni metricas simuladas.
