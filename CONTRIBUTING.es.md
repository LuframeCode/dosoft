# Contribuir a Dosoft

**Disponible en:** [English](CONTRIBUTING.md) · [Français](CONTRIBUTING.fr.md)

¡Gracias por tu interés en Dosoft! Esta guía explica cómo contribuir de forma efectiva, ya sea reportando un bug, sugiriendo una mejora o enviando código.

---

## Tabla de contenidos

1. [Antes de empezar](#antes-de-empezar)
2. [Reportar un bug](#reportar-un-bug)
3. [Sugerir una funcionalidad](#sugerir-una-funcionalidad)
4. [Contribuir código](#contribuir-código)
5. [Convención de commits](#convención-de-commits)
6. [Estilo de código](#estilo-de-código)
7. [Build y pruebas locales](#build-y-pruebas-locales)

---

## Antes de empezar

- Verifica que no exista ya una issue o pull request similar antes de abrir una nueva.
- Para cambios significativos, **abre primero una issue** para discutir el enfoque. Así evitas invertir tiempo en algo que podría no ser mergeado.
- El proyecto es exclusivo para **Windows** y para jugadores de **Dofus** (Unity y Rétro). Las contribuciones fuera de este ámbito no serán aceptadas.
- El idioma oficial del proyecto es el **inglés**. El francés y el español también son aceptados para issues, PRs y comentarios.

---

## Reportar un bug

Abre una [issue](https://github.com/LuframeCode/dosoft/issues) usando la plantilla **Bug report** e incluye:

- **Versión de Dosoft** (visible en la interfaz o en `version.json`)
- **Versión del juego**: Unity o Rétro
- **Comportamiento observado**: lo que ocurre realmente
- **Comportamiento esperado**: lo que debería ocurrir
- **Pasos para reproducirlo**: cuanto más preciso, mejor
- **Logs o capturas de pantalla** si es posible

---

## Sugerir una funcionalidad

Abre una [issue](https://github.com/LuframeCode/dosoft/issues) usando la plantilla **Feature request** y describe:

- El **problema** que resuelve o la necesidad que cubre
- La **solución que propones**
- Las **alternativas** que hayas considerado

---

## Contribuir código

### 1. Fork y clone

```bash
git clone https://github.com/<tu-usuario>/dosoft
cd dosoft
```

### 2. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 3. Crea una rama

Nómbrala de forma clara, reflejando lo que estás haciendo:

```bash
git checkout -b fix/deteccion-ventanas-retro
git checkout -b feat/atajo-equipo-personalizado
```

Prefijos recomendados: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`

### 4. Haz tus cambios

- Respeta la estructura existente del proyecto (ver [Estilo de código](#estilo-de-código))
- Prueba manualmente el comportamiento modificado
- Un único tema por pull request

### 5. Haz commit y push

Respeta la [convención de commits](#convención-de-commits) a continuación.

```bash
git push origin feat/atajo-equipo-personalizado
```

### 6. Abre una Pull Request

- Título claro y conciso
- Descripción explicando **por qué** este cambio y **cómo** fue probado
- Vincula la issue correspondiente con `Closes #42` si aplica

---

## Convención de commits

El proyecto sigue una convención inspirada en [Conventional Commits](https://www.conventionalcommits.org/).

### Formato

```
<tipo>(<scope>): <descripción corta>

[cuerpo opcional]

[footer opcional]
```

### Tipos

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `refactor` | Refactorización sin cambio de comportamiento |
| `style` | Formato, indentación (sin cambio de lógica) |
| `docs` | Solo documentación |
| `chore` | Tareas de mantenimiento (build, dependencias, config…) |
| `perf` | Mejora de rendimiento |
| `revert` | Revertir un commit anterior |

### Scope (opcional)

Indica el módulo afectado: `gui`, `logic`, `hotkeys`, `config`, `radial`, `build`, `installer`

### Reglas

- La **descripción corta** está en inglés (o francés), en modo imperativo, sin mayúscula inicial, sin punto final
- Máximo **72 caracteres** en la primera línea
- El **cuerpo** es opcional pero recomendado para cambios no triviales
- Un commit = una unidad lógica de cambio

### Ejemplos

```
feat(hotkeys): add MB4/MB5 support per team

fix(logic): fix window detection in Rétro mode

refactor(gui): move display settings into a dedicated panel

docs: update build instructions in README

chore(build): bump version to 1.2.0

fix: prevent crash on startup when settings.json is corrupted
```

---

## Estilo de código

- **Python 3**, compatible con las versiones soportadas por las dependencias del proyecto
- Indentación: **4 espacios** (sin tabulaciones)
- Nomenclatura: `snake_case` para variables y funciones, `PascalCase` para clases
- Comentarios en **inglés** o francés
- No añadir librerías externas sin discusión previa en una issue
- Mantén el proyecto ligero: debe ser sencillo de instalar y ejecutar

---

## Build y pruebas locales

Ejecuta la app directamente con Python para pruebas rápidas:

```bash
python main.py
```

Para crear un build completo (`.exe` + instalador):

```bash
build.cmd
```

> Requiere [PyInstaller](https://pyinstaller.org/) e [Inno Setup 6+](https://jrsoftware.org/isinfo.php) instalados en tu máquina.

---

Para cualquier pregunta, abre una issue o visita [dosoft.fr](https://dosoft.fr).
