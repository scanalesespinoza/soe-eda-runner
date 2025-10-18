# Guía de Contribución

¡Gracias por tu interés en contribuir a **SOE EDA Runner**! Esta guía describe el flujo de trabajo recomendado, el estilo de código y los pasos de revisión que seguimos para asegurar contribuciones consistentes y de alta calidad.

## Flujo de contribución
1. **Crea un issue** describiendo el problema o mejora propuesta, incluyendo contexto, motivación y criterios de aceptación.
2. **Discute la solución** con el equipo para alinear alcances, dependencias y responsables.
3. **Crea una rama** a partir de `main` siguiendo la convención `feature/<descripcion-corta>` o `fix/<descripcion-corta>`.
4. **Desarrolla la solución** aplicando las convenciones de estilo y manteniendo commits autocontenidos y con mensajes descriptivos.
5. **Ejecuta las pruebas y validaciones** relevantes antes de abrir el Pull Request.
6. **Abre un Pull Request (PR)** enlazando el issue correspondiente, resumiendo los cambios y destacando consideraciones importantes.
7. **Itera sobre la retroalimentación** recibida en la revisión hasta obtener la aprobación requerida.
8. **Realiza el merge** siguiendo la estrategia definida (merge commit o squash) y verifica el despliegue/estado posterior.

## Estilo de código
- Sigue los linters y formateadores definidos en el proyecto (por ejemplo, `black`, `isort`, `flake8`, `eslint`, etc.).
- Prefiere nombres descriptivos para variables, funciones y módulos.
- Documenta funciones y clases públicas con docstrings o comentarios claros.
- Evita duplicar lógica; refactoriza cuando identifiques patrones reutilizables.
- Incluye pruebas automatizadas cuando introduzcas nueva funcionalidad o corrijas errores.

## Pasos de revisión
1. **Revisión automática**: verifica que las integraciones continuas (CI) pasen sin errores.
2. **Revisión manual**: al menos una persona del equipo debe revisar el PR, asegurándose de que el código cumpla con los estándares y de que la solución resuelva el issue planteado.
3. **Pruebas manuales o de aceptación**: cuando aplique, el autor o revisor debe ejecutar los escenarios críticos manualmente.
4. **Checklist de documentación**: comprueba que se actualicen las guías, changelog o diagramas cuando corresponda.

Al seguir estas prácticas mantenemos la calidad y coherencia del proyecto, facilitando la colaboración entre equipos.
