# DevOps CLI Tool - Manual de Usuario

## Descripcion

Herramienta CLI para automatizar operaciones de DevOps en Salesforce, incluyendo:
- Deploy/Retrieve de metadata CORE (XML)
- Deploy/Retrieve de metadata VLOCITY (YAML)
- Sistema de tracking de componentes
- Integracion con Azure DevOps para gestion de PRs
- Generacion de reportes de commits

---

## Prerequisitos

### 1. Homebrew (Gestor de paquetes para macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

### 2. Salesforce CLI (sf)

Herramienta oficial de Salesforce para interactuar con orgs.

```bash
# Instalacion
brew install sf

# Verificar instalacion
sf --version

# Autenticarse en una org (abre navegador)
sf org login web --alias mi-org

# Autenticarse con archivo JSON
sf force auth sfdxurl store --sfdx-url-file authFile.json
```

---

### 3. Vlocity Build Tool

Para deploy/retrieve de componentes OmniStudio/Vlocity.

```bash
# Instalacion global con npm
npm install -g vlocity

# Verificar instalacion
vlocity --version
```

**Nota:** Requiere Node.js instalado previamente:
```bash
brew install node
```

---

### 4. Azure CLI + Extension DevOps

Para aprobar y completar Pull Requests desde el CLI.

```bash
# Instalar Azure CLI
brew install azure-cli

# Agregar extension de Azure DevOps
az extension add --name azure-devops

# Autenticarse (abre navegador)
az login --allow-no-subscriptions

# Configurar organizacion y proyecto por defecto
az devops configure --defaults organization=https://dev.azure.com/SuratechDevOpsColombia project="Suratech Colombia"

# Verificar configuracion
az devops configure --list
```

#### Comandos utiles de Azure DevOps:
```bash
# Ver informacion de un PR
az repos pr show --id <PR_ID>

# Aprobar un PR
az repos pr set-vote --id <PR_ID> --vote approve

# Completar (merge) un PR
az repos pr update --id <PR_ID> --status completed

# Listar PRs activos
az repos pr list --status active
```

---

### 5. Python 3

Requerido para el script de reportes de commits.

```bash
# Instalacion
brew install python@3

# Verificar instalacion
python3 --version
```

---

### 6. Git

Control de versiones.

```bash
# Instalacion
brew install git

# Verificar instalacion
git --version

# Configuracion basica
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@ejemplo.com"
```

---

### 7. SGD Plugin (Salesforce Git Delta)

Plugin para generar package.xml basado en diferencias de Git.

```bash
# Instalacion
sf plugins install sfdx-git-delta

# Verificar instalacion
sf plugins

# Uso basico
sf sgd source delta --to <rama_destino> --from <rama_origen> --output-dir .
```

---

## Resumen de Comandos de Instalacion

Ejecutar todos los prerequisitos en orden:

```bash
# 1. Homebrew (si no esta instalado)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Herramientas basicas
brew install git node python@3

# 3. Salesforce CLI
brew install sf

# 4. Vlocity
npm install -g vlocity

# 5. SGD Plugin
sf plugins install sfdx-git-delta

# 6. Azure CLI
brew install azure-cli
az extension add --name azure-devops

# 7. Autenticacion Azure (ejecutar y seguir instrucciones)
az login --allow-no-subscriptions
az devops configure --defaults organization=https://dev.azure.com/SuratechDevOpsColombia project="Suratech Colombia"
```

---

## Autenticacion en Orgs de Salesforce

### Orgs disponibles en el CLI:

| Alias | Username | Ambiente |
|-------|----------|----------|
| DEVBANCA | juan.obando@suratechcol.com.devbanca | Desarrollo |
| SITBANCA | juan.obando@suratechcol.com.sitbanca | SIT |
| PRE-UAT | devcb@sura.com.preuat | Pre-UAT |
| UAT | devcb@sura.com.uat | UAT |
| PROD | juan.obando@sura.com.prod | Produccion |
| NESPON | juan.obando@nespon.com | Tracking |

### Comandos de autenticacion:

```bash
# Autenticarse via navegador
sf org login web --alias SITBANCA --instance-url https://test.salesforce.com

# Autenticarse con archivo JSON (generado desde el CLI)
sf force auth sfdxurl store --sfdx-url-file authSITBANCA.json

# Listar orgs autenticadas
sf org list

# Abrir org en navegador
sf org open --target-org SITBANCA
```

---

## Uso del CLI Tool

### Ejecutar el CLI:

```bash
cd /ruta/al/proyecto/scripts
./sura-cli-command-banca
```

### Menu Principal:

```
+-----------------------------------+
|         DevOps CLI Tool           |
+-----------------------------------+

1. Metadata CORE      (Deploy/Retrieve XML)
2. Metadata VLOCITY   (Deploy/Retrieve YAML)
3. Export List        (Listar componentes)
4. Autenticar         (Gestion de orgs)
5. Release            (PRs y Git)

E. Salir
```

---

## Flujo de Deploy a SITBANCA

1. **Seleccionar opcion 1** -> Metadata CORE
2. **Seleccionar opcion 3** -> Deploy
3. **Seleccionar org destino** -> SITBANCA
4. **Confirmar deploy** -> S
5. **Deploy ejecutado** -> Si es exitoso...
6. **Guardar en Tracking?** -> S
7. **Ingresar datos:**
   - Sprint (ej: SP23)
   - HU (ej: 31258)
   - PR ID (ej: 10914)
8. **Tracking guardado** -> Componentes registrados en Salesforce
9. **Aprobar/Completar PR en Azure?** -> S
10. **PR aprobado y completado** -> Merge automatico

---

## Archivos de Configuracion

| Archivo | Ubicacion | Descripcion |
|---------|-----------|-------------|
| package.xml | manifest/Salud/ | Componentes CORE a deploy |
| package.yaml | manifest/Salud/ | Componentes VLOCITY a deploy |
| sura-cli-command-banca | scripts/ | Script principal del CLI |
| component_commit_report.py | scripts/ | Generador de reportes |

---

## Troubleshooting

### Error: "sf command not found"
```bash
brew install sf
```

### Error: "vlocity command not found"
```bash
npm install -g vlocity
```

### Error: "az command not found"
```bash
brew install azure-cli
az extension add --name azure-devops
```

### Error: "No subscriptions found"
```bash
az login --allow-no-subscriptions
```

### Error de autenticacion en Azure DevOps
```bash
az logout
az login --allow-no-subscriptions
az devops configure --defaults organization=https://dev.azure.com/SuratechDevOpsColombia project="Suratech Colombia"
```

### Error de permisos al ejecutar el script
```bash
chmod +x scripts/sura-cli-command-banca
```

---

## Contacto

Para soporte o mejoras del CLI, contactar al equipo de DevOps.

---

*Ultima actualizacion: Enero 2026*
