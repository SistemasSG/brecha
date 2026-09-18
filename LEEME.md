# Panel de brecha BCV / Binance P2P en GitHub

## Estructura que debe quedar en el repositorio

```
.github/workflows/recolectar.yml     <- el archivo recolectar.yml va AQUÍ
recolectar.py                        <- en la raíz
index.html                           <- en la raíz
datos/cuotas.enc                     <- tus cuotas, cifradas
datos/brecha.csv, datos/datos.json   <- los crea solo el recolector
```

## Montaje

1. Crea un repositorio **público** (Pages gratuito lo exige). Nombre sugerido: `brecha`.
2. Sube `recolectar.py` e `index.html` a la raíz.
3. Crea la carpeta `.github/workflows/` y sube ahí `recolectar.yml`.
4. Ve a **Settings → Pages**. En *Source* elige **Deploy from a branch**, rama `main`, carpeta `/ (root)`. Guarda.
5. Ve a la pestaña **Actions**, abre *Recolectar brecha* y pulsa **Run workflow**. Esa primera corrida crea `datos/brecha.csv` y `datos/datos.json`.
6. Abre `https://TU-USUARIO.github.io/brecha/` desde el teléfono.

## Cuotas

Están en `datos/cuotas.enc`, cifradas con AES-256-GCM y una clave derivada de tu frase
con PBKDF2 (200.000 iteraciones). El repositorio es público, pero ese archivo no dice nada
sin la frase.

La primera vez que abras el panel en un dispositivo te pedirá la frase. Queda recordada
en ese navegador; no vuelve a preguntarla.

Los pagos que registres se guardan en el dispositivo donde los registras. Si quieres que
el resto los vea, pulsa **Descargar cuotas.enc** y reemplaza el archivo en `datos/` del
repositorio.

Para cambiar la frase, dímelo y regenero el archivo.

## Horario

El flujo corre a las 13:00–23:00 y 00:00 UTC, es decir 9:00 a 20:00 en Caracas.
GitHub puede retrasar las corridas programadas algunos minutos cuando hay carga alta;
no es un fallo. Para forzar una lectura, **Run workflow** en la pestaña Actions
(funciona también desde el navegador del teléfono).

## Si algo falla

Mira el log de la corrida en Actions.

- `Binance devolvió 0 anuncios`: bloqueó el rango de GitHub. El recolector de tu PC
  sigue siendo el plan B.
- `BCV directo falló`: usa automáticamente la API de respaldo; si también falla,
  la corrida no escribe nada y lo reintenta a la hora siguiente.
- El commit falla: **no** cambies *Workflow permissions* a "Read and write". El flujo ya
  pide lo que necesita con `permissions: contents: write` dentro de `recolectar.yml`, y ese
  bloque manda por encima del valor del repositorio. Lo de Settings → Actions → General es
  el permiso **por defecto**, no un techo: dejarlo en "Read repository contents" es lo
  correcto, porque así cada flujo declara su propio permiso en vez de que todos escriban
  por defecto. Si aun así falla, mira si el repositorio pertenece a una organización con
  una política que limite los permisos, o si el token expiró.
