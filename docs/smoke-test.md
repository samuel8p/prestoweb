# Prueba de humo manual

Checklist para verificar a mano la app contra el backend real. No sustituye la
suite automática (que corre contra MSW), sirve para confirmar el flujo completo
en el navegador.

## Preparación

- Backend de Presto corriendo y accesible (por ejemplo `http://127.0.0.1:8000`).
- `VITE_API_URL` apuntando a ese backend.
- Front servido (`npm run dev` o el build de producción con `npm run preview`).
- El backend en modo demo (`DEMO_MODE=true`) para poder mover dinero simulado.

## Flujo

| #   | Paso                                                                         | Qué hay que ver                                                                                                                          |
| --- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Abrir la app                                                                 | Si el backend está en demo, aparece el cartel fijo **"Demo: el dinero es simulado"**. Si no, no aparece.                                 |
| 2   | Registrarse en `/registro`                                                   | Se crea la cuenta y se entra al panel.                                                                                                   |
| 3   | `/perfil` → pedir verificación KYC                                           | Se envía la metadata del documento y el estado pasa a _Pendiente_.                                                                       |
| 4   | `/billetera` → abrir billetera ARS                                           | Aparece la billetera con saldo 0.                                                                                                        |
| 5   | `/billetera` → nuevo movimiento → depósito                                   | El saldo sube y el movimiento aparece en el historial.                                                                                   |
| 6   | `/billetera` → historial                                                     | El movimiento tiene importe, fecha y moneda. Si fue revertido por un staff, aparece marcado **Revertido**.                               |
| 7   | `/ofertas` → publicar una oferta                                             | La oferta aparece en "Mis ofertas" con estado _Activa_.                                                                                  |
| 8   | `/ofertas` → buscar y comparar                                               | La búsqueda filtra por moneda, rango, tasa y plazo. Con dos ofertas marcadas, la comparación muestra cuota, interés total y costo total. |
| 9   | `/ofertas` → aceptar una oferta (con una segunda cuenta que sea prestamista) | Se crea el préstamo y se abre el detalle.                                                                                                |
| 10  | `/prestamos` → ver cuotas y pagar una                                        | La cuota pasa a _Pagada_ y el saldo del prestatario baja.                                                                                |
| 11  | `/inversiones` → invertir en un producto                                     | La posición aparece con el interés esperado.                                                                                             |
| 12  | `/presupuestos` → crear categoría y presupuesto                              | El presupuesto muestra gastado, disponible y umbral.                                                                                     |
| 13  | `/presupuestos` → categorizar un movimiento                                  | El gasto aparece en "Gastos categorizados" y el presupuesto suma ese importe.                                                            |
| 14  | `/reportes` → recorrer las cuatro pestañas                                   | Movimientos, gasto por categoría, préstamos e inversiones.                                                                               |
| 15  | `/reportes` → descargar CSV                                                  | Se baja el archivo con el nombre que manda el backend (`reporte-gasto.csv`, etc.).                                                       |
| 16  | `/avisos`                                                                    | La lista de avisos y las preferencias por tipo; al apagar una preferencia, queda guardada.                                               |
| 17  | Recargar la página                                                           | La sesión se recupera con el refresh token: seguís adentro, sin volver al login.                                                         |
| 18  | Cerrar sesión                                                                | Vuelve al login y la sesión se borra del navegador.                                                                                      |

## Cosas que hay que mirar

- **Errores por campo**: al mandar un dato inválido (por ejemplo, un importe
  con letras), el mensaje aparece debajo del campo, no como un error genérico.
- **KYC**: sin KYC aprobado, mover dinero responde con el aviso
  **"Tu cuenta aún no fue verificada (KYC)"**.
- **401**: con el access token vencido, la app renueva sola y reintenta la
  petición; no se cae la sesión ni aparece un error.
- **Responsive**: en menos de 640 px el menú colapsa en el botón "Menú" y las
  tablas tienen scroll horizontal.
