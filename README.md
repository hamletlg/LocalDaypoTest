# 📚 Daypo XML Quiz Viewer (wxPython)

Este es un proyecto de código abierto que implementa una aplicación de escritorio multiplataforma (usando wxPython) para cargar, visualizar y realizar tests interactivos a partir de archivos XML con un formato similar al utilizado por la plataforma de tests online Daypo.

Permite a los usuarios practicar tests sin conexión, ofreciendo diferentes tipos de preguntas (selección simple/múltiple, ordenación), retroalimentación inmediata, y la opción de guardar/cargar el progreso de la sesión.

## 🌟 Características

* **Carga de Tests XML:** Carga archivos de test en formato XML (estructuras de Daypo o similares).
* **Compatibilidad con Preguntas:** Soporte para preguntas de **Selección Simple**, **Selección Múltiple** y **Ordenación**.
* **Visualización de Imágenes:** Muestra las imágenes (`<i/>`) asociadas a las preguntas (codificadas en Base64 dentro del XML).
* **Guardado y Carga de Progreso:** Guarda automáticamente el progreso (respuestas y pregunta actual) en un archivo `.progress.json` y ofrece reanudar la sesión al volver a cargar el mismo test.
* **Interfaz de Usuario Intuitiva (wxPython):** Una interfaz de escritorio clara con navegación, visualización de preguntas/opciones y un panel de retroalimentación.
* **Resumen de Resultados:** Muestra un resumen de aciertos y fallos al finalizar el test y permite **reintentar solo las preguntas fallidas**.

---

## 🛠️ Instalación y Requisitos

Este proyecto requiere Python 3.x y la librería `wxPython`.

### Requisitos

Asegúrate de tener Python instalado y luego instala `wxPython` (y opcionalmente `pip` si aún no lo tienes):

```bash
# Instalar wxPython
pip install wxPython
````

### Uso

1.  **Guarda el Código:** Guarda el código proporcionado como `local_daypo.py`.

2.  **Ejecuta la Aplicación:** Abre tu terminal y ejecuta el script:

    ```bash
    python local_daypo.py
    ```

3.  **Carga un Test:** En la aplicación, ve a **File -\> Open Test...** y selecciona tu archivo de test en formato XML.

-----

## 💻 Estructura del Código

El script `local_daypo.py` está organizado siguiendo el patrón **MVC (Modelo-Vista-Controlador)**:

1.  **`MODEL` (Clases `Question` y `Test`):** Contiene la lógica de datos. `Question` almacena texto, opciones, respuestas correctas y el estado de la respuesta del usuario. `Test` gestiona la colección de preguntas y el estado general del test (índice actual, puntuaciones).
2.  **`CONTROLLER` (Clase `TestController`):** Contiene la lógica de la aplicación. Es responsable de cargar el archivo XML, analizar su contenido, gestionar la navegación entre preguntas, evaluar las respuestas y manejar el guardado/carga del progreso en JSON.
3.  **`VIEW` (Clase `TestFrame`):** Contiene la interfaz de usuario wxPython. Gestiona la creación de los *widgets* (botones, texto, checkboxes/radiobuttons/spin controls), actualiza la vista basándose en el modelo, y maneja los eventos de usuario (clicks en botones, selección de opciones).

### Tipos de Pregunta Soportados

El controlador analiza las siguientes etiquetas dentro del XML para determinar el tipo de pregunta:

| Código `t` | Tipo de Pregunta | Descripción |
| :---: | :---: | :--- |
| `1` | `single` / `multiple` | Preguntas de selección. Determinado por el código de respuesta `c` (código `2` indica opción correcta). |
| `6` | `ordering` | Preguntas de ordenar elementos. El orden correcto se extrae del código de respuesta `c`. |

-----

## 🤝 Contribuciones

Si encuentras un error o tienes alguna sugerencia de mejora, por favor, abre un *issue* o envía un *pull request*. ¡Toda contribución es bienvenida\!

-----

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.
```

