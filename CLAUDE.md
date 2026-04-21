# DevOps-Tools — Contexto para Claude

Herramientas de DevOps Salesforce para los proyectos de Suratech Colombia.
Repositorio git del proyecto principal: `/Users/jcobandor84/Documents/NESPON/SURA/BANCA/suratech-salesforce-app`

---

## Archivos del proyecto

| Archivo | Descripción |
|---------|-------------|
| `sura-cli-command-banca` | **Orquestador principal** — bash script 3215 líneas |
| `jarvis/auto_pr_monitor.py` | Monitor automático de PRs (Python, cron cada 30 min) |
| `pr_commit_report.py` | Generador de reportes de commits/PRs |
| `report_server.py` | Servidor HTTP para visualizar reportes |
| `verificar-conflictos-git.sh` | Script de detección de conflictos git |
| `package_hibridos.xml/.yaml` | Listas de componentes híbridos (Vlocity+CORE) |
| `DevOps_CLI_Tool.md` | Manual de usuario del CLI |

---

## Orquestador: `sura-cli-command-banca`

Script bash ejecutado desde el directorio del proyecto Salesforce.

### Proyectos configurables

| Proyecto | Función | Manifest | ORG Tracking |
|----------|---------|----------|--------------|
| BANCA COL | `configurar_banca()` | `manifest/Salud/package.xml` | `juan.obando@suratechcol.com.sitbanca` |
| VIAJES COL | `configurar_viajes()` | `manifest/Viajes/package-viajes.xml` | `juan.obando@nespon.com.sitviajes` |
| AUTOS CL | `configurar_banca_nequi()` | `manifest/Autos/package.xml` | — |

### Funciones principales

| Función | Línea | Descripción |
|---------|-------|-------------|
| `verificar_hibridos()` | 96 | Detecta componentes híbridos en manifests de deploy |
| `verificar_hibridos_por_pr()` | 204 | Detecta híbridos en los archivos de un PR específico |
| `aprobar_completar_pr_azure()` | 434 | Aprueba y completa PRs en Azure DevOps |
| `guardar_tracking_componentes()` | 543 | Guarda tracking en Salesforce (XML/CORE) |
| `guardar_tracking_componentes_yaml()` | 689 | Guarda tracking en Salesforce (YAML/Vlocity) |
| `seleccionar_org_origen()` | 824 | Menú para elegir ORG de retrieve |
| `seleccionar_org_destino()` | 900 | Menú para elegir ORG de deploy |
| `gestionar_monitor_prs()` | 1222 | Gestiona el monitor automático Jarvis |
| `mostrar_menu_git()` | 1454 | Menú de operaciones Git/PR (Menú Release) |
| `verificar_cambios_pr()` | 1477 | Verifica archivos cambiados en un PR |
| `crear_commit_hacia_uat()` | 1761 | **Migrar componentes de un PR a otra rama** |

### Menús

| Menú | Función | Descripción |
|------|---------|-------------|
| Proyecto | `mostrar_menu_proyecto()` | Selecciona BANCA / VIAJES / AUTOS |
| Principal | `mostrar_menu_principal()` | CORE / Vlocity / Export / Autenticar / Release |
| CORE (XML) | `mostrar_menu_xml()` | Deploy / Retrieve CORE |
| Vlocity (YAML) | `mostrar_menu_yaml()` | Deploy / Retrieve Vlocity |
| Export | `mostrar_menu_export()` | Listado de componentes |
| Autenticar | `mostrar_menu_autenticar()` | Gestión de ORGs Salesforce |
| Release | `mostrar_menu_git()` | PRs, Git, Monitor, Migración |

---

## ORGs Salesforce

| Alias/Username | Ambiente | Notas |
|----------------|----------|-------|
| `juan.obando@suratechcol.com.devbanca` | DEV Banca | SP(X+1) |
| `juan.obando@suratechcol.com.sitbanca` | SIT Banca | SP(X) |
| `juan.obando@nespon.com` | Nespon | Tracking |
| `juan.obando@nespon.com.buildviajes` | Build Viajes | SP(X+1) |
| `juan.obando@nespon.com.sitviajes` | SIT Viajes | — |
| `devcb@sura.com.uat` | UAT | — |
| `juan.obando@sura.com.prod` | **PROD** | **SOLO LECTURA** |
| `juan.obando@sura.com.chile.prod` | PROD Chile | — |
| `juan.obando.banca@suratech.com.nequi.prod` | PROD NEQUI | ORG nueva, se puede modificar |

---

## Azure DevOps

- **Organización:** `SuratechDevOpsColombia`
- **Proyecto:** `Suratech Colombia`
- **Repositorio:** `suratech-salesforce-app`
- **URL PRs:** `https://dev.azure.com/SuratechDevOpsColombia/Suratech%20Colombia/_git/suratech-salesforce-app/pullrequest`
- **Rama de reportes:** `devops-reports`

---

## Monitor Jarvis (`jarvis/auto_pr_monitor.py`)

- Monitorea PRs hacia ramas `uat` y `main`
- Detecta componentes híbridos (por lista XML y por autor externo)
- Guarda historial en MySQL local (`database: devops`, `host: localhost`)
- Sube reportes HTML a rama `devops-reports` y comparte link en Teams
- Corre por cron cada 30 min
- Dominios vigilados (equipo propio): `@nespon.com`, `@cloudblue.us`
- Autores adicionales del equipo: `omar`, `omar marmolejo`, `amanda andrade`

---

## Dependencias requeridas

- `sf` (Salesforce CLI) — deploy/retrieve metadata CORE
- `vlocity` (npm) — deploy/retrieve metadata OmniStudio/Vlocity
- `az` + extensión `azure-devops` — gestión de PRs
- `python3` — reportes y monitor
- `mysql.connector` (Python) — base de datos del monitor
- `sfdx-git-delta` (sf plugin) — generar package.xml por diff git

---

## Pipeline de desarrollo — SURA CHILE (AUTOS CL)

### Flujo del Desarrollador

```
1. git checkout development-autos
   git pull origin development-autos

2. git checkout -b feature/HU-XXXX

3. [Desarrolla los cambios]

4. git add .
   git commit -m "HU-XXXX: descripción del cambio"
   git push origin feature/HU-XXXX

5. Crea PR en Azure DevOps:
   feature/HU-XXXX → sura-autos-sprint01
   - Título:       HU-XXXX: descripción
   - Descripción:  Disponible para pruebas aliado #HU-XXXX
   - Reviewer:     Juan Carlos Obando Ramos
   - Work Items:   Relacionar la HU en la sección de work items del PR

6. En Azure DevOps:
   - Cambia estado HU: En proceso → Disponible para SIT
   - Asigna la HU a Juan Carlos Obando Ramos
```

### Flujo del Release Manager / DevOps

**Por cada HU que llega:**

```
1. Revisar y aprobar PR feature/HU-XXXX → sura-autos-sprint01
2. Mergear
3. Actualizar manifests en sura-autos-sprint01:
   - manifest/autos/package.xml  (componentes CORE)
   - manifest/autos/package.yaml (componentes Vlocity)
```

**Cuando el sprint cierra (todas las HUs mergeadas):**

```
4. PR sura-autos-sprint01 → development-autos  (sincronizar rama de desarrollo)
5. PR sura-autos-sprint01 → Integracion        (subir sprint completo a SIT)
   - Deploy a ambiente INTEGRACION
   - Notificar a QA para validación
```

**Si QA rechaza una HU:**

```
6. Desarrollador corrige sobre feature/HU-XXXX-fix (desde sura-autos-sprint01)
   PR feature/HU-XXXX-fix → sura-autos-sprint01
   Volver al paso 5
```

**Si QA aprueba:**

```
7. PR sura-autos-sprint01 → uat
   - Deploy a ambiente UAT
   - Notificar a cliente para pruebas de aceptación
```

**Si UAT aprueba:**

```
8. PR sura-autos-sprint01 → main
   - Deploy a PRODUCCIÓN
```

**Al inicio del siguiente sprint:**

```
9. Crear sura-autos-sprint02 desde development-autos
   (que ya está sincronizado con el sprint anterior)
```

---

## Notas importantes

- El script se ejecuta desde el directorio raíz del repo git (`suratech-salesforce-app`)
- `PROJECT_ROOT` se resuelve con `git rev-parse --show-toplevel`
- La función `crear_commit_hacia_uat()` usa worktree temporal para no cambiar la rama activa. Si la rama destino es la misma que la rama actual, trabaja directamente en `PROJECT_ROOT` sin crear worktree.
- El commit en `crear_commit_hacia_uat()` hace `git add` archivo por archivo solo con los archivos del PR (`filtered_files`). **No usar `git add -A`** — agregaría archivos ajenos al PR que estén pendientes en la rama (ej: `delta-deploy-job.yaml`).
- Los componentes híbridos son aquellos que tienen metadata CORE y Vlocity simultáneamente — se deben desplegar en orden específico.
