#!/bin/bash

################################################################################
# Script para Verificar Conflictos entre Ramas
################################################################################

# Ruta absoluta al directorio de DevOps-Tools (donde vive este script y generate-delta-deploy-job.js)
DEVOPS_TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATE_DELTA_SCRIPT="${DEVOPS_TOOLS_DIR}/generate-delta-deploy-job.js"

# Colores básicos compatibles con cualquier terminal
COLOR_PRIMARY="\033[0;35m"     # Magenta
COLOR_ACCENT="\033[0;36m"      # Cyan
COLOR_SUCCESS="\033[0;32m"     # Verde
COLOR_WARNING="\033[0;33m"     # Amarillo
COLOR_ERROR="\033[0;31m"       # Rojo
COLOR_INFO="\033[0;36m"        # Cyan
COLOR_TEXT="\033[0;37m"        # Blanco
COLOR_MUTED="\033[0;90m"       # Gris
COLOR_BOLD="\033[1m"           # Negrita
COLOR_RESET="\033[0m"          # Reset

# Manifest dinámico según proyecto seleccionado (default: manifest/Salud)
MANIFEST_DIR="${MANIFEST_DIR:-manifest/Salud}"

clear
echo -e "${COLOR_PRIMARY}${COLOR_BOLD}"
echo "╔═════════════════════════════════════════════════════════════╗"
echo "║                                                             ║"
echo "║        Verificación de Conflictos entre Ramas               ║"
echo "║                                                             ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo -e "${COLOR_RESET}\n"

# Guardar la rama actual
RAMA_ACTUAL=$(git branch --show-current)
echo -e "${COLOR_INFO}Rama actual: ${COLOR_ACCENT}$RAMA_ACTUAL${COLOR_RESET}"
echo -e "${COLOR_MUTED}Este script cambiará temporalmente de rama para realizar el merge${COLOR_RESET}"
echo ""

# Solicitar rama origen (HU)
echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}Ingrese la rama ORIGEN (HU):${COLOR_RESET}"
echo -e "${COLOR_MUTED}  Ejemplo: HU29572${COLOR_RESET}"
read RAMA_ORIGEN

if [ -z "$RAMA_ORIGEN" ]; then
    echo -e "${COLOR_ERROR}Rama origen es requerida${COLOR_RESET}"
    exit 1
fi

# Solicitar rama destino (Sprint) - Selección dinámica
echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}Rama DESTINO (Sprint):${COLOR_RESET} ${COLOR_ACCENT}$RAMA_ACTUAL${COLOR_RESET}"
echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Usar esta rama como destino? (S/N):${COLOR_RESET} "
read usar_rama_actual

if [[ "$usar_rama_actual" =~ ^[Ss]$ ]]; then
    RAMA_DESTINO="$RAMA_ACTUAL"
    echo -e "${COLOR_SUCCESS}✓ Usando rama destino: ${COLOR_ACCENT}$RAMA_DESTINO${COLOR_RESET}"
else
    echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}Ingrese la rama DESTINO (Sprint):${COLOR_RESET}"
    echo -e "${COLOR_MUTED}  Ejemplo: sura-salud-sprintxxx${COLOR_RESET}"
    read RAMA_DESTINO

    if [ -z "$RAMA_DESTINO" ]; then
        echo -e "${COLOR_ERROR}Rama destino es requerida${COLOR_RESET}"
        exit 1
    fi
fi

# Confirmación
echo ""
echo -e "${COLOR_WARNING}${COLOR_BOLD}"
echo "╔═════════════════════════════════════════════════════════════╗"
echo "║           VERIFICACIÓN DE CONFLICTOS                        ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo -e "${COLOR_RESET}"
echo -e "${COLOR_WARNING}"
echo "  Rama Origen: $RAMA_ORIGEN"
echo "  Rama Destino: $RAMA_DESTINO"
echo "  Rama Actual: $RAMA_ACTUAL"
echo ""
echo "  Esta operación:"
echo "    1. Actualizará las referencias remotas (git fetch)"
echo "    2. Cambiará temporalmente a la rama $RAMA_ORIGEN"
echo "    3. Realizará el merge de $RAMA_DESTINO en $RAMA_ORIGEN"
echo "    4. Si NO hay conflictos: creará el commit"
echo "    5. Si hay conflictos: mostrará la lista y abortará"
echo "    6. Regresará a tu rama actual: $RAMA_ACTUAL"
echo -e "${COLOR_RESET}"
echo ""
echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Desea continuar? (S/N):${COLOR_RESET} "
read confirmacion

if [[ ! "$confirmacion" =~ ^[Ss]$ ]]; then
    echo "Verificación cancelada."
    exit 0
fi

# Iniciar proceso
echo ""
echo -e "${COLOR_INFO}${COLOR_BOLD}═══════════════════════════════════════════════════════════${COLOR_RESET}"
echo -e "${COLOR_INFO}Iniciando verificación de conflictos...${COLOR_RESET}"
echo -e "${COLOR_INFO}${COLOR_BOLD}═══════════════════════════════════════════════════════════${COLOR_RESET}"
echo ""

# Cambiar al directorio raíz del proyecto
cd "$(git rev-parse --show-toplevel)" || exit 1

# Paso 1: Fetch para actualizar referencias remotas
echo -e "${COLOR_INFO}[1/3] Actualizando referencias remotas...${COLOR_RESET}"
if git fetch origin; then
    echo -e "${COLOR_SUCCESS}✓ Git fetch completado${COLOR_RESET}"
else
    echo -e "${COLOR_ERROR}✗ Error al ejecutar git fetch${COLOR_RESET}"
    exit 1
fi
echo ""

# Paso 2: Verificar que ambas ramas existen en remoto
echo -e "${COLOR_INFO}[2/3] Verificando que las ramas existen...${COLOR_RESET}"

if ! git rev-parse --verify "origin/$RAMA_ORIGEN" >/dev/null 2>&1; then
    echo -e "${COLOR_ERROR}✗ La rama origin/$RAMA_ORIGEN no existe${COLOR_RESET}"
    exit 1
fi

if ! git rev-parse --verify "origin/$RAMA_DESTINO" >/dev/null 2>&1; then
    echo -e "${COLOR_ERROR}✗ La rama origin/$RAMA_DESTINO no existe${COLOR_RESET}"
    exit 1
fi

echo -e "${COLOR_SUCCESS}✓ Ambas ramas existen en remoto${COLOR_RESET}"
echo ""

# Paso 3: Hacer checkout a la rama ORIGEN (necesario para el merge)
echo -e "${COLOR_INFO}[3/3] Cambiando temporalmente a $RAMA_ORIGEN para realizar el merge...${COLOR_RESET}"

# Verificar si hay cambios sin guardar
if ! git diff-index --quiet HEAD --; then
    echo -e "${COLOR_WARNING}Hay cambios sin guardar. Guardándolos temporalmente...${COLOR_RESET}"
    git stash push -m "Auto-stash antes de verificar conflictos - $(date +'%Y-%m-%d %H:%M:%S')"
    STASH_CREATED=true
else
    STASH_CREATED=false
fi

# Intentar checkout normal primero
if git checkout "$RAMA_ORIGEN" 2>/dev/null; then
    echo -e "${COLOR_SUCCESS}✓ Cambio exitoso a rama $RAMA_ORIGEN${COLOR_RESET}"
else
    # Si falla, intentar crear la rama local desde el remoto
    echo -e "${COLOR_WARNING}Rama local no existe. Creando desde origin/$RAMA_ORIGEN...${COLOR_RESET}"

    # Capturar el error para mostrarlo si falla
    CHECKOUT_ERROR=$(git checkout -b "$RAMA_ORIGEN" "origin/$RAMA_ORIGEN" 2>&1)
    CHECKOUT_STATUS=$?

    if [ $CHECKOUT_STATUS -eq 0 ]; then
        echo -e "${COLOR_SUCCESS}✓ Rama $RAMA_ORIGEN creada y configurada${COLOR_RESET}"
    else
        echo ""
        echo -e "${COLOR_ERROR}${COLOR_BOLD}ERROR: No se pudo cambiar a la rama $RAMA_ORIGEN${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_MUTED}Detalles del error:${COLOR_RESET}"
        echo -e "${COLOR_MUTED}$CHECKOUT_ERROR${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_WARNING}Posibles causas:${COLOR_RESET}"
        echo -e "${COLOR_WARNING}  1. El nombre de la rama no coincide exactamente (verifica mayúsculas/minúsculas)${COLOR_RESET}"
        echo -e "${COLOR_WARNING}  2. La rama no existe en origin/${COLOR_RESET}"
        echo -e "${COLOR_WARNING}  3. Hay cambios sin guardar que están bloqueando el checkout${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_INFO}Buscando ramas similares...${COLOR_RESET}"
        git branch -a | grep -i "$RAMA_ORIGEN" || echo -e "${COLOR_MUTED}No se encontraron ramas similares${COLOR_RESET}"
        echo ""
        git checkout "$RAMA_ACTUAL" >/dev/null 2>&1

        # Restaurar stash si se creó
        if [ "$STASH_CREATED" = true ]; then
            echo -e "${COLOR_INFO}Restaurando cambios guardados...${COLOR_RESET}"
            git stash pop >/dev/null 2>&1
        fi

        exit 1
    fi
fi

# Actualizar la rama origen con pull
if ! git pull origin "$RAMA_ORIGEN"; then
    echo -e "${COLOR_ERROR}✗ Error al actualizar rama $RAMA_ORIGEN${COLOR_RESET}"
    git checkout "$RAMA_ACTUAL" >/dev/null 2>&1

    # Restaurar stash si se creó
    if [ "$STASH_CREATED" = true ]; then
        echo -e "${COLOR_INFO}Restaurando cambios guardados...${COLOR_RESET}"
        git stash pop >/dev/null 2>&1
    fi

    exit 1
fi

echo -e "${COLOR_SUCCESS}✓ Rama $RAMA_ORIGEN actualizada${COLOR_RESET}"
echo ""

# Verificar si las ramas ya están sincronizadas (no hay diferencias)
echo -e "${COLOR_INFO}Verificando diferencias entre las ramas...${COLOR_RESET}"

# Comparar los commits de ambas ramas
RAMA_ORIGEN_COMMIT=$(git rev-parse "$RAMA_ORIGEN")
RAMA_DESTINO_COMMIT=$(git rev-parse "origin/$RAMA_DESTINO")

# Verificar si hay diferencias entre las ramas
DIFERENCIAS=$(git rev-list --count "$RAMA_ORIGEN".."origin/$RAMA_DESTINO")

if [ "$DIFERENCIAS" -eq 0 ]; then
    # Las ramas están sincronizadas, no hay nada que mergear
    echo ""
    echo -e "${COLOR_SUCCESS}${COLOR_BOLD}"
    echo "╔═════════════════════════════════════════════════════════════╗"
    echo "║           RAMAS YA ESTÁN SINCRONIZADAS                      ║"
    echo "╚═════════════════════════════════════════════════════════════╝"
    echo -e "${COLOR_RESET}"
    echo ""
    echo -e "${COLOR_SUCCESS}Las ramas $RAMA_ORIGEN y $RAMA_DESTINO están actualizadas.${COLOR_RESET}"
    echo -e "${COLOR_SUCCESS}No hay cambios por mergear.${COLOR_RESET}"
    echo ""

    # Ir directamente a la generación del package.xml
    echo -e "${COLOR_INFO}${COLOR_BOLD}¿Deseas generar el package.xml con los componentes CORE modificados?${COLOR_RESET}"
    echo -e "${COLOR_INFO}Esto identificará los componentes entre las ramas:${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Origen:    ${COLOR_RESET}${COLOR_ACCENT}$RAMA_ORIGEN${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Destino:   ${COLOR_RESET}${COLOR_ACCENT}$RAMA_DESTINO${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Resultado: ${COLOR_RESET}${COLOR_ACCENT}${MANIFEST_DIR}/package.xml${COLOR_RESET}"
    echo ""
    echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Generar package.xml? (S/N):${COLOR_RESET} "
    read generar_package

    if [[ "$generar_package" =~ ^[Ss]$ ]]; then
        echo ""
        echo -e "${COLOR_INFO}Generando package.xml de componentes CORE...${COLOR_RESET}"
        echo -e "${COLOR_MUTED}Ejecutando: sf sgd source delta --to $RAMA_ORIGEN --from origin/$RAMA_DESTINO --output-dir .${COLOR_RESET}"
        echo ""

        # Cambiar al directorio raíz del proyecto
        cd "$(git rev-parse --show-toplevel)" || exit 1

        # Ejecutar el comando de generación
        if sf sgd source delta --to "$RAMA_ORIGEN" --from "origin/$RAMA_DESTINO" --output-dir .; then
            echo ""

            # Mostrar resumen del package generado
            if [ -f "package/package.xml" ]; then
                echo -e "${COLOR_INFO}Resumen del package.xml:${COLOR_RESET}"
                echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"

                # Contar total de metadatos (members)
                TOTAL_MEMBERS=$(grep -c "<members>" package/package.xml)
                echo -e "${COLOR_INFO}Total de metadatos: ${COLOR_ACCENT}$TOTAL_MEMBERS${COLOR_RESET}"
                echo ""
                echo -e "${COLOR_MUTED}Componentes CORE detectados:${COLOR_RESET}"
                python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('package/package.xml')
ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
for t in tree.findall('sf:types', ns):
    name = t.find('sf:name', ns).text
    members = [m.text for m in t.findall('sf:members', ns)]
    print(f'  \033[0;36m{name}\033[0m \033[2m({len(members)})\033[0m')
    for m in members:
        print(f'    \033[0;35m→\033[0m {m}')
"
                echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                echo ""

                # Copiar metadatos al manifest del proyecto
                TIPOS_METADATA=$(sed -n '/<types>/,/<\/types>/p' package/package.xml)

                if [ -n "$TIPOS_METADATA" ]; then
                    cat > ${MANIFEST_DIR}/package.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
$TIPOS_METADATA
    <version>65.0</version>
</Package>
EOF
                    _l1=$(printf "║  Archivo:      %-43s║" "${MANIFEST_DIR}/package.xml")
                    _l2=$(printf "║  Componentes:  %-43s║" "${TOTAL_MEMBERS} metadatos CORE")
                    echo -e "${COLOR_SUCCESS}╔═══════════════════════════════════════════════════════════╗"
                    echo -e "║  ✓  package.xml actualizado correctamente                 ║"
                    echo -e "╠═══════════════════════════════════════════════════════════╣"
                    echo -e "${_l1}"
                    echo -e "${_l2}"
                    echo -e "╚═══════════════════════════════════════════════════════════╝${COLOR_RESET}"
                else
                    echo -e "${COLOR_WARNING}⚠ No se encontraron tipos de metadata para copiar${COLOR_RESET}"
                fi
                echo ""
            fi

            echo -e "${COLOR_ERROR}${COLOR_BOLD}⚠️  RECORDATORIO IMPORTANTE:${COLOR_RESET}"
            echo -e "${COLOR_ERROR}  → NO OLVIDES aprobar el PR en Azure DevOps${COLOR_RESET}"
            echo -e "${COLOR_ERROR}  → NO OLVIDES documentar el MERGE${COLOR_RESET}"
            echo ""
        else
            echo ""
            echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar package.xml${COLOR_RESET}"
            echo -e "${COLOR_WARNING}Verifica que sf sgd (sfdx-git-delta) esté instalado${COLOR_RESET}"
            echo -e "${COLOR_INFO}Para instalarlo: ${COLOR_ACCENT}sf plugins install sfdx-git-delta${COLOR_RESET}"
            echo ""
        fi
    else
        echo ""
        echo -e "${COLOR_INFO}Generación de package.xml omitida.${COLOR_RESET}"
        echo ""
    fi

    # Preguntar si desea generar delta-deploy-job.yaml (Vlocity) - siempre preguntar
    echo ""
    echo -e "${COLOR_INFO}${COLOR_BOLD}¿Deseas generar el delta-deploy-job.yaml con los componentes VLOCITY modificados?${COLOR_RESET}"
    echo -e "${COLOR_INFO}Esto identificará los componentes Vlocity entre las ramas:${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Origen:    ${COLOR_RESET}${COLOR_ACCENT}$RAMA_ORIGEN${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Destino:   ${COLOR_RESET}${COLOR_ACCENT}$RAMA_DESTINO${COLOR_RESET}"
    echo -e "${COLOR_ACCENT}  Resultado: ${COLOR_RESET}${COLOR_ACCENT}delta-deploy-job.yaml${COLOR_RESET}"
    echo ""
    echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Generar delta-deploy-job.yaml? (S/N):${COLOR_RESET} "
    read generar_vlocity

    if [[ "$generar_vlocity" =~ ^[Ss]$ ]]; then
        echo ""
        echo -e "${COLOR_INFO}Generando delta-deploy-job.yaml de componentes Vlocity...${COLOR_RESET}"
        echo -e "${COLOR_MUTED}Paso 1: git diff --name-only $RAMA_ORIGEN $RAMA_DESTINO > changes.txt${COLOR_RESET}"

        # Cambiar al directorio raíz del proyecto
        cd "$(git rev-parse --show-toplevel)" || exit 1

        # Generar archivo changes.txt con las diferencias
        if git diff --name-only "$RAMA_ORIGEN" "$RAMA_DESTINO" > changes.txt; then
            echo -e "${COLOR_SUCCESS}✓ Archivo changes.txt generado${COLOR_RESET}"

            # Contar archivos modificados
            TOTAL_CHANGES=$(wc -l < changes.txt | tr -d ' ')
            echo -e "${COLOR_INFO}Total de archivos modificados: ${COLOR_ACCENT}$TOTAL_CHANGES${COLOR_RESET}"
            echo ""

            echo -e "${COLOR_MUTED}Paso 2: node ${GENERATE_DELTA_SCRIPT}${COLOR_RESET}"

            # Ejecutar script de generación
            if node "$GENERATE_DELTA_SCRIPT"; then
                echo ""

                # Mostrar resumen del archivo generado
                if [ -f "delta-deploy-job.yaml" ]; then
                    # Extraer los componentes del delta-deploy-job.yaml (líneas que comienzan con "  - ")
                    VLOCITY_COMPONENTS=$(grep -E "^\s*-\s+[A-Za-z0-9_]+/" delta-deploy-job.yaml | sed 's/^[[:space:]]*/    /')

                    # Contar total de componentes Vlocity
                    TOTAL_VLOCITY=$(grep -cE "^\s*-\s+[A-Za-z0-9_]+/" delta-deploy-job.yaml)

                    echo -e "${COLOR_INFO}Resumen del package.yaml:${COLOR_RESET}"
                    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                    echo -e "${COLOR_INFO}Total de metadatos: ${COLOR_ACCENT}$TOTAL_VLOCITY${COLOR_RESET}"
                    echo ""
                    echo -e "${COLOR_MUTED}Componentes Vlocity detectados:${COLOR_RESET}"
                    while IFS= read -r componente; do
                        nombre=$(echo "$componente" | sed 's/^[[:space:]]*-[[:space:]]*//')
                        echo -e "  ${COLOR_ACCENT}→${COLOR_RESET} ${nombre}"
                    done <<< "$VLOCITY_COMPONENTS"
                    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                    echo ""

                    # Copiar componentes Vlocity al manifest del proyecto
                    echo -e "${COLOR_INFO}Actualizando ${MANIFEST_DIR}/package.yaml...${COLOR_RESET}"

                    if [ -n "$VLOCITY_COMPONENTS" ]; then
                        # Crear el nuevo package.yaml con los componentes Vlocity y configuración completa
                        cat > ${MANIFEST_DIR}/package.yaml << EOF
projectPath: .
expansionPath: ./vlocity/
manifest:
$VLOCITY_COMPONENTS

delete: true
activate: true
compileOnBuild: true
maxDepth: 0
continueAfterError: true
useAllRelationships: false
supportHeadersOnly: true
supportForceDeploy: true
verbose: false
deltaGeneration: false
EOF
                        _l1=$(printf "║  Archivo:      %-43s║" "${MANIFEST_DIR}/package.yaml")
                        _l2=$(printf "║  Componentes:  %-43s║" "${TOTAL_VLOCITY} metadatos Vlocity")
                        echo -e "${COLOR_SUCCESS}╔═══════════════════════════════════════════════════════════╗"
                        echo -e "║  ✓  package.yaml actualizado correctamente                ║"
                        echo -e "╠═══════════════════════════════════════════════════════════╣"
                        echo -e "${_l1}"
                        echo -e "${_l2}"
                        echo -e "╚═══════════════════════════════════════════════════════════╝${COLOR_RESET}"
                    else
                        echo -e "${COLOR_WARNING}⚠ No se encontraron componentes Vlocity para copiar${COLOR_RESET}"
                    fi
                    echo ""
                fi

                echo -e "${COLOR_ERROR}${COLOR_BOLD}⚠️  RECORDATORIO IMPORTANTE:${COLOR_RESET}"
                echo -e "${COLOR_ERROR}  → NO OLVIDES aprobar el PR en Azure DevOps${COLOR_RESET}"
                echo -e "${COLOR_ERROR}  → NO OLVIDES documentar el MERGE${COLOR_RESET}"
                echo ""
            else
                echo ""
                echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar delta-deploy-job.yaml${COLOR_RESET}"
                echo -e "${COLOR_WARNING}Verifica que el script generate-delta-deploy-job.js exista${COLOR_RESET}"
                echo ""
            fi
        else
            echo ""
            echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar changes.txt${COLOR_RESET}"
            echo ""
        fi
    else
        echo ""
        echo -e "${COLOR_INFO}Generación de delta-deploy-job.yaml omitida.${COLOR_RESET}"
        echo ""
    fi

else
    # Hay diferencias, proceder con el merge normal
    echo -e "${COLOR_INFO}Se detectaron $DIFERENCIAS commit(s) por mergear.${COLOR_RESET}"
    echo ""

    # Realizar el merge
    echo -e "${COLOR_INFO}Realizando merge de origin/$RAMA_DESTINO en $RAMA_ORIGEN...${COLOR_RESET}"
    echo -e "${COLOR_MUTED}Ejecutando: git merge origin/$RAMA_DESTINO --no-edit${COLOR_RESET}"
    echo ""

    # Capturar salida del merge
    MERGE_OUTPUT=$(git merge "origin/$RAMA_DESTINO" --no-edit 2>&1)
    MERGE_STATUS=$?

    if [ $MERGE_STATUS -eq 0 ]; then
        # Mostrar output del merge exitoso
        echo "$MERGE_OUTPUT"
        # Merge exitoso sin conflictos
        echo ""
        echo -e "${COLOR_SUCCESS}${COLOR_BOLD}"
        echo "╔═════════════════════════════════════════════════════════════╗"
        echo "║              MERGE COMPLETADO EXITOSAMENTE                  ║"
        echo "╚═════════════════════════════════════════════════════════════╝"
        echo -e "${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_SUCCESS}El merge de $RAMA_DESTINO en $RAMA_ORIGEN se realizó sin conflictos.${COLOR_RESET}"
        echo -e "${COLOR_SUCCESS}Los cambios han sido confirmados con un commit automático.${COLOR_RESET}"
        echo ""

        # Mostrar el último commit
        echo -e "${COLOR_INFO}Último commit creado:${COLOR_RESET}"
        git log -1 --oneline --decorate
        echo ""

        # Mostrar estadísticas del merge (sin pager para evitar bloqueos con listados grandes)
        echo -e "${COLOR_INFO}Resumen de cambios:${COLOR_RESET}"
        git --no-pager diff --stat HEAD~1 HEAD
        echo ""

        # Preguntar si desea hacer push
        echo -e "${COLOR_WARNING}${COLOR_BOLD}¿Deseas subir los cambios al repositorio remoto?${COLOR_RESET}"
        echo -e "${COLOR_WARNING}Esto ejecutará: ${COLOR_ACCENT}git push origin $RAMA_ORIGEN${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Hacer push ahora? (S/N):${COLOR_RESET} "
        read hacer_push

        if [[ "$hacer_push" =~ ^[Ss]$ ]]; then
            echo ""
            echo -e "${COLOR_INFO}Subiendo cambios a origin/$RAMA_ORIGEN...${COLOR_RESET}"

            if git push origin "$RAMA_ORIGEN"; then
                echo ""
                echo -e "${COLOR_SUCCESS}${COLOR_BOLD}✓ Push completado exitosamente${COLOR_RESET}"
                echo -e "${COLOR_SUCCESS}La rama $RAMA_ORIGEN ha sido actualizada en el repositorio remoto${COLOR_RESET}"
                echo ""
            else
                echo ""
                echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al hacer push${COLOR_RESET}"
                echo -e "${COLOR_WARNING}Puedes intentar manualmente con: ${COLOR_ACCENT}git push origin $RAMA_ORIGEN${COLOR_RESET}"
                echo ""
            fi
        else
            echo ""
            echo -e "${COLOR_INFO}Push omitido.${COLOR_RESET}"
            echo -e "${COLOR_WARNING}Para subir los cambios más tarde, ejecuta:${COLOR_RESET}"
            echo -e "${COLOR_ACCENT}  git checkout $RAMA_ORIGEN${COLOR_RESET}"
            echo -e "${COLOR_ACCENT}  git push origin $RAMA_ORIGEN${COLOR_RESET}"
            echo ""
        fi

        # Preguntar si desea generar package.xml
        echo ""
        echo -e "${COLOR_INFO}${COLOR_BOLD}¿Deseas generar el package.xml con los componentes CORE modificados?${COLOR_RESET}"
        echo -e "${COLOR_INFO}Esto identificará los componentes entre las ramas:${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Origen:    ${COLOR_RESET}${COLOR_ACCENT}$RAMA_ORIGEN${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Destino:   ${COLOR_RESET}${COLOR_ACCENT}$RAMA_DESTINO${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Resultado: ${COLOR_RESET}${COLOR_ACCENT}${MANIFEST_DIR}/package.xml${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Generar package.xml? (S/N):${COLOR_RESET} "
        read generar_package

        if [[ "$generar_package" =~ ^[Ss]$ ]]; then
            echo ""
            echo -e "${COLOR_INFO}Generando package.xml de componentes CORE...${COLOR_RESET}"
            echo -e "${COLOR_MUTED}Ejecutando: sf sgd source delta --to $RAMA_ORIGEN --from origin/$RAMA_DESTINO --output-dir .${COLOR_RESET}"
            echo ""

            # Cambiar al directorio raíz del proyecto
            cd "$(git rev-parse --show-toplevel)" || exit 1

            # Ejecutar el comando de generación
            if sf sgd source delta --to "$RAMA_ORIGEN" --from "origin/$RAMA_DESTINO" --output-dir .; then
                echo ""

                # Mostrar resumen del package generado
                if [ -f "package/package.xml" ]; then
                    echo -e "${COLOR_INFO}Resumen del package.xml:${COLOR_RESET}"
                    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"

                    # Contar total de metadatos (members)
                    TOTAL_MEMBERS=$(grep -c "<members>" package/package.xml)
                    echo -e "${COLOR_INFO}Total de metadatos: ${COLOR_ACCENT}$TOTAL_MEMBERS${COLOR_RESET}"
                    echo ""
                    echo -e "${COLOR_MUTED}Componentes CORE detectados:${COLOR_RESET}"
                    python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('package/package.xml')
ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
for t in tree.findall('sf:types', ns):
    name = t.find('sf:name', ns).text
    members = [m.text for m in t.findall('sf:members', ns)]
    print(f'  \033[0;36m{name}\033[0m \033[2m({len(members)})\033[0m')
    for m in members:
        print(f'    \033[0;35m→\033[0m {m}')
"
                    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                    echo ""

                    # Copiar metadatos al manifest del proyecto
                    echo -e "${COLOR_INFO}Actualizando ${MANIFEST_DIR}/package.xml...${COLOR_RESET}"

                    # Extraer los tipos de metadata del package generado (todo entre <Package> y <version>)
                    TIPOS_METADATA=$(sed -n '/<types>/,/<\/types>/p' package/package.xml)

                    if [ -n "$TIPOS_METADATA" ]; then
                        # Crear el nuevo package.xml con los tipos de metadata
                        cat > ${MANIFEST_DIR}/package.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
$TIPOS_METADATA
    <version>65.0</version>
</Package>
EOF
                        echo -e "${COLOR_SUCCESS}╔═══════════════════════════════════════════════════════════╗${COLOR_RESET}"
                        echo -e "${COLOR_SUCCESS}║  ✓  package.xml actualizado correctamente                 ║${COLOR_RESET}"
                        echo -e "${COLOR_SUCCESS}╠═══════════════════════════════════════════════════════════╣${COLOR_RESET}"
                        echo -e "${COLOR_SUCCESS}║  Archivo:      ${COLOR_ACCENT}${MANIFEST_DIR}/package.xml${COLOR_SUCCESS}$(printf '%*s' $((27 - ${#MANIFEST_DIR})) '')║${COLOR_RESET}"
                        echo -e "${COLOR_SUCCESS}║  Componentes:  ${COLOR_ACCENT}${TOTAL_MEMBERS} metadatos CORE${COLOR_SUCCESS}$(printf '%*s' $((27 - ${#TOTAL_MEMBERS})) '')║${COLOR_RESET}"
                        echo -e "${COLOR_SUCCESS}╚═══════════════════════════════════════════════════════════╝${COLOR_RESET}"
                    else
                        echo -e "${COLOR_WARNING}⚠ No se encontraron tipos de metadata para copiar${COLOR_RESET}"
                    fi
                    echo ""
                fi

                echo -e "${COLOR_ERROR}${COLOR_BOLD}⚠️  RECORDATORIO IMPORTANTE:${COLOR_RESET}"
                echo -e "${COLOR_ERROR}  → NO OLVIDES aprobar el PR en Azure DevOps${COLOR_RESET}"
                echo -e "${COLOR_ERROR}  → NO OLVIDES documentar el MERGE${COLOR_RESET}"
                echo ""
            else
                echo ""
                echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar package.xml${COLOR_RESET}"
                echo -e "${COLOR_WARNING}Verifica que sf sgd (sfdx-git-delta) esté instalado${COLOR_RESET}"
                echo -e "${COLOR_INFO}Para instalarlo: ${COLOR_ACCENT}sf plugins install sfdx-git-delta${COLOR_RESET}"
                echo ""
            fi
        else
            echo ""
            echo -e "${COLOR_INFO}Generación de package.xml omitida.${COLOR_RESET}"
            echo ""
        fi

        # Preguntar si desea generar delta-deploy-job.yaml (Vlocity) - siempre preguntar
        echo ""
        echo -e "${COLOR_INFO}${COLOR_BOLD}¿Deseas generar el delta-deploy-job.yaml con los componentes VLOCITY modificados?${COLOR_RESET}"
        echo -e "${COLOR_INFO}Esto identificará los componentes Vlocity entre las ramas:${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Origen:    ${COLOR_RESET}${COLOR_ACCENT}$RAMA_ORIGEN${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Destino:   ${COLOR_RESET}${COLOR_ACCENT}$RAMA_DESTINO${COLOR_RESET}"
        echo -e "${COLOR_ACCENT}  Resultado: ${COLOR_RESET}${COLOR_ACCENT}delta-deploy-job.yaml${COLOR_RESET}"
        echo ""
        echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}¿Generar delta-deploy-job.yaml? (S/N):${COLOR_RESET} "
        read generar_vlocity

        if [[ "$generar_vlocity" =~ ^[Ss]$ ]]; then
            echo ""
            echo -e "${COLOR_INFO}Generando delta-deploy-job.yaml de componentes Vlocity...${COLOR_RESET}"
            echo -e "${COLOR_MUTED}Paso 1: git diff --name-only $RAMA_ORIGEN $RAMA_DESTINO > changes.txt${COLOR_RESET}"

            # Cambiar al directorio raíz del proyecto
            cd "$(git rev-parse --show-toplevel)" || exit 1

            # Generar archivo changes.txt con las diferencias
            if git diff --name-only "$RAMA_ORIGEN" "$RAMA_DESTINO" > changes.txt; then
                echo -e "${COLOR_SUCCESS}✓ Archivo changes.txt generado${COLOR_RESET}"

                # Contar archivos modificados
                TOTAL_CHANGES=$(wc -l < changes.txt | tr -d ' ')
                echo -e "${COLOR_INFO}Total de archivos modificados: ${COLOR_ACCENT}$TOTAL_CHANGES${COLOR_RESET}"
                echo ""

                echo -e "${COLOR_MUTED}Paso 2: node ${GENERATE_DELTA_SCRIPT}${COLOR_RESET}"

                # Ejecutar script de generación
                if node "$GENERATE_DELTA_SCRIPT"; then
                    echo ""

                    # Mostrar resumen del archivo generado
                    if [ -f "delta-deploy-job.yaml" ]; then
                        # Extraer los componentes del delta-deploy-job.yaml (líneas que comienzan con "  - ")
                        VLOCITY_COMPONENTS=$(grep -E "^\s*-\s+[A-Za-z0-9_]+/" delta-deploy-job.yaml | sed 's/^[[:space:]]*/    /')

                        # Contar total de componentes Vlocity
                        TOTAL_VLOCITY=$(grep -cE "^\s*-\s+[A-Za-z0-9_]+/" delta-deploy-job.yaml)

                        echo -e "${COLOR_INFO}Resumen del package.yaml:${COLOR_RESET}"
                        echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                        echo -e "${COLOR_INFO}Total de metadatos: ${COLOR_ACCENT}$TOTAL_VLOCITY${COLOR_RESET}"
                        echo ""
                        echo -e "${COLOR_MUTED}Componentes Vlocity detectados:${COLOR_RESET}"
                        while IFS= read -r componente; do
                            nombre=$(echo "$componente" | sed 's/^[[:space:]]*-[[:space:]]*//')
                            echo -e "  ${COLOR_ACCENT}→${COLOR_RESET} ${nombre}"
                        done <<< "$VLOCITY_COMPONENTS"
                        echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
                        echo ""

                        # Copiar componentes Vlocity al manifest del proyecto
                        echo -e "${COLOR_INFO}Actualizando ${MANIFEST_DIR}/package.yaml...${COLOR_RESET}"

                        if [ -n "$VLOCITY_COMPONENTS" ]; then
                            # Crear el nuevo package.yaml con los componentes Vlocity y configuración completa
                            cat > ${MANIFEST_DIR}/package.yaml << EOF
projectPath: .
expansionPath: ./vlocity/
manifest:
$VLOCITY_COMPONENTS

delete: true
activate: true
compileOnBuild: true
maxDepth: 0
continueAfterError: true
useAllRelationships: false
supportHeadersOnly: true
supportForceDeploy: true
verbose: false
deltaGeneration: false
EOF
                            _l1=$(printf "║  Archivo:      %-43s║" "${MANIFEST_DIR}/package.yaml")
                        _l2=$(printf "║  Componentes:  %-43s║" "${TOTAL_VLOCITY} metadatos Vlocity")
                        echo -e "${COLOR_SUCCESS}╔═══════════════════════════════════════════════════════════╗"
                        echo -e "║  ✓  package.yaml actualizado correctamente                ║"
                        echo -e "╠═══════════════════════════════════════════════════════════╣"
                        echo -e "${_l1}"
                        echo -e "${_l2}"
                        echo -e "╚═══════════════════════════════════════════════════════════╝${COLOR_RESET}"
                        else
                            echo -e "${COLOR_WARNING}⚠ No se encontraron componentes Vlocity para copiar${COLOR_RESET}"
                        fi
                        echo ""
                    fi

                    echo -e "${COLOR_ERROR}${COLOR_BOLD}⚠️  RECORDATORIO IMPORTANTE:${COLOR_RESET}"
                    echo -e "${COLOR_ERROR}  → NO OLVIDES aprobar el PR en Azure DevOps${COLOR_RESET}"
                    echo -e "${COLOR_ERROR}  → NO OLVIDES documentar el MERGE${COLOR_RESET}"
                    echo ""
                else
                    echo ""
                    echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar delta-deploy-job.yaml${COLOR_RESET}"
                    echo -e "${COLOR_WARNING}Verifica que el script generate-delta-deploy-job.js exista${COLOR_RESET}"
                    echo ""
                fi
            else
                echo ""
                echo -e "${COLOR_ERROR}${COLOR_BOLD}✗ Error al generar changes.txt${COLOR_RESET}"
                echo ""
            fi
        else
            echo ""
            echo -e "${COLOR_INFO}Generación de delta-deploy-job.yaml omitida.${COLOR_RESET}"
            echo ""
        fi

    else
        # Hubo conflictos durante el merge
    echo ""
    echo -e "${COLOR_ERROR}${COLOR_BOLD}"
    echo "╔═════════════════════════════════════════════════════════════╗"
    echo "║                 CONFLICTOS DETECTADOS                       ║"
    echo "╚═════════════════════════════════════════════════════════════╝"
    echo -e "${COLOR_RESET}"
    echo ""

    # Mostrar el output completo del merge con conflictos
    echo -e "${COLOR_ERROR}${COLOR_BOLD}Mensaje de Git:${COLOR_RESET}"
    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
    echo "$MERGE_OUTPUT"
    echo -e "${COLOR_MUTED}─────────────────────────────────────────────────────────────${COLOR_RESET}"
    echo ""

    # Obtener lista de archivos con conflictos
    ARCHIVOS_CONFLICTO=$(git diff --name-only --diff-filter=U 2>/dev/null)

    if [ -n "$ARCHIVOS_CONFLICTO" ]; then
        echo -e "${COLOR_ERROR}${COLOR_BOLD}Se detectaron conflictos en los siguientes archivos:${COLOR_RESET}"
        echo ""
        echo "$ARCHIVOS_CONFLICTO" | while read -r archivo; do
            echo -e "  ${COLOR_ERROR}✗${COLOR_RESET} $archivo"
        done
        echo ""

        # Contar archivos con conflictos
        TOTAL_CONFLICTOS=$(echo "$ARCHIVOS_CONFLICTO" | wc -l | tr -d ' ')
        echo -e "${COLOR_WARNING}Total de archivos con conflictos: $TOTAL_CONFLICTOS${COLOR_RESET}"
        echo ""

        # Guardar reporte
        REPORTE_FILE="./scripts/conflictos-$(date +'%Y%m%d_%H%M%S').txt"
        cat > "$REPORTE_FILE" << EOF
═══════════════════════════════════════════════════════════
 REPORTE DE CONFLICTOS
═══════════════════════════════════════════════════════════

Fecha: $(date +'%Y-%m-%d %H:%M:%S')
Rama Origen: $RAMA_ORIGEN
Rama Destino: $RAMA_DESTINO

RESULTADO: CONFLICTOS DETECTADOS

Total de archivos con conflictos: $TOTAL_CONFLICTOS

Archivos afectados:
$ARCHIVOS_CONFLICTO

═══════════════════════════════════════════════════════════
ACCIÓN REQUERIDA:
═══════════════════════════════════════════════════════════

Notificar al desarrollador con la siguiente información:
- Lista de archivos en conflicto
- Solicitar resolución de conflictos antes de continuar

El merge ha sido ABORTADO. No se realizaron cambios en la rama.

═══════════════════════════════════════════════════════════
EOF

        echo -e "${COLOR_INFO}📄 Reporte guardado en: $REPORTE_FILE${COLOR_RESET}"
        echo ""
    else
        echo -e "${COLOR_ERROR}Error durante el merge. Revisa el output anterior para más detalles.${COLOR_RESET}"
        echo ""
    fi

    echo -e "${COLOR_ERROR}${COLOR_BOLD}ACCIÓN REQUERIDA:${COLOR_RESET}"
    echo -e "${COLOR_ERROR}→ Notificar al desarrollador sobre los conflictos detectados${COLOR_RESET}"
    echo -e "${COLOR_ERROR}→ El desarrollador debe resolver los conflictos antes de continuar${COLOR_RESET}"
    echo ""

    echo -e "${COLOR_WARNING}Abortando el merge...${COLOR_RESET}"
    # Abortar el merge
    git merge --abort >/dev/null 2>&1
    echo -e "${COLOR_SUCCESS}Merge abortado. La rama $RAMA_ORIGEN no fue modificada.${COLOR_RESET}"
    echo ""
    fi
fi

# Preguntar si desea quedarse en la rama origen o volver a la rama original
echo -e "${COLOR_INFO}${COLOR_BOLD}¿En qué rama deseas quedarte?${COLOR_RESET}"
echo -e "${COLOR_ACCENT}  1.${COLOR_RESET} ${COLOR_TEXT}Quedarse en rama ORIGEN: ${COLOR_SUCCESS}$RAMA_ORIGEN${COLOR_RESET} ${COLOR_MUTED}(recomendado para hacer deploy)${COLOR_RESET}"
echo -e "${COLOR_ACCENT}  2.${COLOR_RESET} ${COLOR_TEXT}Volver a rama inicial: ${COLOR_WARNING}$RAMA_ACTUAL${COLOR_RESET}"
echo ""
echo -e "${COLOR_PRIMARY}→${COLOR_RESET} ${COLOR_TEXT}Seleccione opción (1/2):${COLOR_RESET} "
read opcion_rama

if [[ "$opcion_rama" == "2" ]]; then
    # Volver a la rama original
    echo -e "${COLOR_INFO}Regresando a la rama original: $RAMA_ACTUAL${COLOR_RESET}"
    git checkout "$RAMA_ACTUAL" >/dev/null 2>&1
    echo -e "${COLOR_SUCCESS}✓ De vuelta en: $RAMA_ACTUAL${COLOR_RESET}"
    echo ""

    # Restaurar cambios guardados si se creó un stash
    if [ "$STASH_CREATED" = true ]; then
        echo -e "${COLOR_INFO}Restaurando cambios guardados temporalmente...${COLOR_RESET}"
        if git stash pop >/dev/null 2>&1; then
            echo -e "${COLOR_SUCCESS}✓ Cambios restaurados correctamente${COLOR_RESET}"
        else
            echo -e "${COLOR_WARNING}⚠ No se pudieron restaurar algunos cambios automáticamente${COLOR_RESET}"
            echo -e "${COLOR_WARNING}Usa 'git stash list' y 'git stash pop' para restaurarlos manualmente${COLOR_RESET}"
        fi
        echo ""
    fi
else
    # Quedarse en la rama origen
    echo ""
    echo -e "${COLOR_SUCCESS}✓ Permaneciendo en rama: $RAMA_ORIGEN${COLOR_RESET}"
    echo -e "${COLOR_INFO}Ahora puedes ejecutar el deploy desde esta rama.${COLOR_RESET}"
    echo ""

    # Notificar sobre el stash si existe
    if [ "$STASH_CREATED" = true ]; then
        echo -e "${COLOR_WARNING}⚠ NOTA: Tienes cambios guardados en stash de la rama $RAMA_ACTUAL${COLOR_RESET}"
        echo -e "${COLOR_WARNING}Cuando vuelvas a esa rama, ejecuta: ${COLOR_ACCENT}git stash pop${COLOR_RESET}"
        echo ""
    fi
fi

echo -e "${COLOR_INFO}${COLOR_BOLD}═══════════════════════════════════════════════════════════${COLOR_RESET}"
echo -e "${COLOR_INFO}Verificación completada${COLOR_RESET}"
RAMA_FINAL=$(git branch --show-current)
echo -e "${COLOR_INFO}Rama actual: ${COLOR_ACCENT}$RAMA_FINAL${COLOR_RESET}"
echo -e "${COLOR_INFO}${COLOR_BOLD}═══════════════════════════════════════════════════════════${COLOR_RESET}"
echo ""
