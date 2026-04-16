#!/usr/bin/env python3
"""
Unified Commit Report Generator
Genera reportes HTML con commits de:
- Un PR especifico comparado contra una rama (ej: UAT)
- Componentes de los manifests (package.xml y package.yaml) comparados contra una rama

Uso:
    # Reporte desde PR
    python3 pr_commit_report.py 10930 uat

    # Reporte desde manifests
    python3 pr_commit_report.py --manifest uat
    python3 pr_commit_report.py --manifest uat --output reporte.html
"""

import subprocess
import json
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuracion
AZURE_ORG = "SuratechDevOpsColombia"
AZURE_PROJECT = "Suratech%20Colombia"
AZURE_REPO = "suratech-salesforce-app"
BASE_URL = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_git/{AZURE_REPO}"

# Autores adicionales del equipo (no tienen dominio vigilado pero son del equipo)
EXTRA_WATCHED_AUTHORS = ['omar', 'omar marmolejo', 'amanda andrade']

# Mapeo de tipos de metadata a rutas en el proyecto
METADATA_TYPE_PATHS = {
    'ApexClass': 'force-app/main/default/classes/{name}.cls',
    'ApexTrigger': 'force-app/main/default/triggers/{name}.trigger',
    'LightningComponentBundle': 'force-app/main/default/lwc/{name}/',
    'AuraDefinitionBundle': 'force-app/main/default/aura/{name}/',
    'FlexiPage': 'force-app/main/default/flexipages/{name}.flexipage-meta.xml',
    'Flow': 'force-app/main/default/flows/{name}.flow-meta.xml',
    'CustomObject': 'force-app/main/default/objects/{name}/',
    'CustomField': 'force-app/main/default/objects/{object}/fields/{field}.field-meta.xml',
    'CustomLabel': 'force-app/main/default/labels/CustomLabels.labels-meta.xml',
    'StaticResource': 'force-app/main/default/staticresources/{name}.*',
    'PermissionSet': 'force-app/main/default/permissionsets/{name}.permissionset-meta.xml',
    'Profile': 'force-app/main/default/profiles/{name}.profile-meta.xml',
    'Layout': 'force-app/main/default/layouts/{name}.layout-meta.xml',
    'RecordType': 'force-app/main/default/objects/{object}/recordTypes/{name}.recordType-meta.xml',
    'CustomMetadata': 'force-app/main/default/customMetadata/{name}.md-meta.xml',
    'RemoteSiteSetting': 'force-app/main/default/remoteSiteSettings/{name}.remoteSite-meta.xml',
    'NamedCredential': 'force-app/main/default/namedCredentials/{name}.namedCredential-meta.xml',
    'ConnectedApp': 'force-app/main/default/connectedApps/{name}.connectedApp-meta.xml',
    'ApexPage': 'force-app/main/default/pages/{name}.page',
    'ApexComponent': 'force-app/main/default/components/{name}.component',
    'ListView': 'force-app/main/default/objects/{object}/listViews/{name}.listView-meta.xml',
    'ValidationRule': 'force-app/main/default/objects/{object}/validationRules/{name}.validationRule-meta.xml',
    'CustomTab': 'force-app/main/default/tabs/{name}.tab-meta.xml',
    'CustomPermission': 'force-app/main/default/customPermissions/{name}.customPermission-meta.xml',
    'Network': 'force-app/main/default/networks/{name}.network-meta.xml',
    'NavigationMenu': 'force-app/main/default/navigationMenus/{name}.navigationMenu-meta.xml',
    'Queue': 'force-app/main/default/queues/{name}.queue-meta.xml',
    'Group': 'force-app/main/default/groups/{name}.group-meta.xml',
    'EmailTemplate': 'force-app/main/default/email/{name}.email-meta.xml',
    'Report': 'force-app/main/default/reports/{name}.report-meta.xml',
    'Dashboard': 'force-app/main/default/dashboards/{name}.dashboard-meta.xml',
    'CustomApplication': 'force-app/main/default/applications/{name}.app-meta.xml',
    'GlobalValueSet': 'force-app/main/default/globalValueSets/{name}.globalValueSet-meta.xml',
    'GlobalValueSetTranslation': 'force-app/main/default/globalValueSetTranslations/{name}.globalValueSetTranslation-meta.xml',
    'QuickAction': 'force-app/main/default/quickActions/{name}.quickAction-meta.xml',
    'DocumentType': 'force-app/main/default/documentTypes/{name}.documentType-meta.xml',
    'ActionPlanTemplate': 'force-app/main/default/actionPlanTemplates/{name}.apt-meta.xml',
    'DecisionMatrixDefinition': 'force-app/main/default/decisionMatrixDefinition/{name}.decisionMatrixDefinition-meta.xml',
    'AssignmentRule': 'force-app/main/default/assignmentRules/{name}.assignmentRules-meta.xml',
    'AutoResponseRule': 'force-app/main/default/autoResponseRules/{name}.autoResponseRules-meta.xml',
    'ApprovalProcess': 'force-app/main/default/approvalProcesses/{name}.approvalProcess-meta.xml',
    'PermissionSetGroup': 'force-app/main/default/permissionsetgroups/{name}.permissionsetgroup-meta.xml',
    'PlatformEventChannel': 'force-app/main/default/platformEventChannels/{name}.platformEventChannel-meta.xml',
    'LightningMessageChannel': 'force-app/main/default/messageChannels/{name}.messageChannel-meta.xml',
    'Workflow': 'force-app/main/default/workflows/{name}.workflow-meta.xml',
    'PathAssistant': 'force-app/main/default/pathAssistants/{name}.pathAssistant-meta.xml',
    'BusinessProcess': 'force-app/main/default/objects/{object}/businessProcesses/{name}.businessProcess-meta.xml',
    'StandardValueSet': 'force-app/main/default/standardValueSets/{name}.standardValueSet-meta.xml',
    'CustomNotificationType': 'force-app/main/default/notificationtypes/{name}.notiftype-meta.xml',
    'ReportType': 'force-app/main/default/reportTypes/{name}.reportType-meta.xml',
}

# Mapeo de tipos Vlocity a rutas
VLOCITY_TYPE_PATHS = {
    'IntegrationProcedure': 'vlocity/IntegrationProcedure/{name}/',
    'DataRaptor': 'vlocity/DataRaptor/{name}/',
    'OmniScript': 'vlocity/OmniScript/{name}/',
    'FlexCard': 'vlocity/FlexCard/{name}/',
    'VlocityUITemplate': 'vlocity/VlocityUITemplate/{name}/',
    'VlocityUILayout': 'vlocity/VlocityUILayout/{name}/',
    'CalculationMatrix': 'vlocity/CalculationMatrix/{name}/',
    'CalculationProcedure': 'vlocity/CalculationProcedure/{name}/',
    'DecisionMatrix': 'vlocity/DecisionMatrix/{name}/',
    'Document': 'vlocity/Document/{name}/',
    'DocumentTemplate': 'vlocity/DocumentTemplate/{name}/',
    'AttributeCategory': 'vlocity/AttributeCategory/{name}/',
    'ContentVersion': 'vlocity/ContentVersion/{name}/',
    'ExpressionSet': 'vlocity/ExpressionSet/{name}/',
    'Product2': 'vlocity/Product2/{name}/',
    'PriceList': 'vlocity/PriceList/{name}/',
}

def get_project_root():
    """Obtiene la raiz del proyecto git desde el directorio de trabajo actual"""
    try:
        result = subprocess.run(
            'git rev-parse --show-toplevel',
            shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback: un nivel arriba del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

# Cache para evitar fetch duplicados en la misma ejecucion
_fetched_branches = set()

def fetch_branches(*branches):
    """Hace git fetch de las ramas indicadas para asegurar que estan actualizadas.
    Evita fetch duplicados usando cache interno."""
    project_root = get_project_root()
    for branch in branches:
        branch_clean = branch.replace("refs/heads/", "")
        if branch_clean in _fetched_branches:
            continue
        print(f"      Actualizando rama remota: {branch_clean}...")
        try:
            result = subprocess.run(
                f'git fetch origin {branch_clean} 2>&1',
                shell=True, capture_output=True, text=True, cwd=project_root
            )
            if result.returncode == 0:
                _fetched_branches.add(branch_clean)
            else:
                print(f"      Advertencia: No se pudo actualizar {branch_clean}: {result.stderr.strip()}")
        except Exception as e:
            print(f"      Advertencia: Error al actualizar {branch_clean}: {e}")

def run_command(cmd):
    """Ejecuta un comando y retorna el output"""
    try:
        # Ejecutar desde la raiz del proyecto para que git funcione correctamente
        project_root = get_project_root()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=project_root)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def get_pr_info(pr_id):
    """Obtiene informacion del PR usando Azure CLI"""
    cmd = f'az repos pr show --id {pr_id} --query "{{title:title, sourceBranch:sourceRefName, targetBranch:targetRefName, status:status, lastMergeCommit:lastMergeCommit, author:createdBy.displayName}}" -o json 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output:
        try:
            return json.loads(output)
        except:
            return None
    return None

def get_watched_authors(domains=None):
    """Obtiene dinámicamente los autores vigilados desde Azure DevOps + git log.
    Combina usuarios activos de la org con nombres de commit por dominio de email.
    Dominios configurables — agregar o quitar dominios aquí:
    """
    if domains is None:
        domains = ['@nespon.com', '@cloudblue.us']

    watched = set()

    # Fuente 0: Autores adicionales configurados manualmente
    for name in EXTRA_WATCHED_AUTHORS:
        watched.add(name.lower())

    # Fuente 1: Azure DevOps — usuarios activos de la organización
    try:
        cmd = 'az devops user list --top 200 -o json 2>/dev/null'
        output, code = run_command(cmd)
        if code == 0 and output:
            data = json.loads(output)
            members = data.get('members', data.get('items', []))
            for m in members:
                user = m.get('user', {})
                email = user.get('mailAddress', '').lower()
                name = user.get('displayName', '').strip()
                if name and any(d in email for d in domains):
                    watched.add(name.lower())
    except Exception:
        pass

    # Fuente 2: Git log — nombres de commit con emails de esos dominios
    # También detecta aliases: si "Omar" tiene email cloudblue.us en otro commit,
    # todas las variantes del nombre quedan como vigiladas
    try:
        cmd = "git log --all --format='%an|%ae' 2>/dev/null"
        output, code = run_command(cmd)
        if code == 0 and output:
            seen = set()
            # Mapear: email → set de nombres, nombre → set de emails
            email_to_names = {}
            name_to_emails = {}
            for line in output.strip().split('\n'):
                if '|' not in line:
                    continue
                name, email = line.split('|', 1)
                name = name.strip().strip("'").lower()
                email = email.strip().strip("'").lower()
                if not name or not email:
                    continue
                key = f"{name}|{email}"
                if key in seen:
                    continue
                seen.add(key)
                email_to_names.setdefault(email, set()).add(name)
                name_to_emails.setdefault(name, set()).add(email)
                # Agregar directamente si el email es de un dominio vigilado
                if any(d in email for d in domains):
                    watched.add(name)
            # Resolver aliases: si un nombre tiene email vigilado,
            # todos los nombres asociados a ese email también son vigilados
            for email, names in email_to_names.items():
                if any(d in email for d in domains):
                    for n in names:
                        watched.add(n)
            # Inverso: si un nombre es vigilado, todos los nombres
            # que comparten email con él también son vigilados
            changed = True
            while changed:
                changed = False
                for name in list(watched):
                    for email in name_to_emails.get(name, set()):
                        for alias in email_to_names.get(email, set()):
                            if alias not in watched:
                                watched.add(alias)
                                changed = True
    except Exception:
        pass

    return watched

def get_changed_files(source_branch, target_branch):
    """Obtiene los archivos cambiados entre dos ramas (solo los del PR)"""
    # Limpiar nombres de rama
    source = source_branch.replace("refs/heads/", "")
    target = target_branch.replace("refs/heads/", "")

    # Comparar source vs target del PR (solo archivos del PR)
    cmd = f'git diff --name-only origin/{target}...origin/{source} 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output:
        return [f for f in output.split('\n') if f.strip()]
    return []

def get_pr_specific_files(source_branch, target_branch):
    """Obtiene SOLO los archivos que cambiaron en el PR (source vs target del PR)"""
    source = source_branch.replace("refs/heads/", "")
    target = target_branch.replace("refs/heads/", "")

    # Comparar la rama del PR contra su rama destino
    cmd = f'git diff --name-only origin/{target}...origin/{source} 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output:
        return [f for f in output.split('\n') if f.strip()]
    return []

def get_file_commit_info_in_branch(file_path, branch):
    """Obtiene informacion del ultimo commit de un archivo EN una rama especifica"""
    branch_clean = branch.replace("refs/heads/", "")

    # Buscar el ultimo commit de este archivo EN la rama de comparacion (ej: UAT)
    # Esto muestra quien fue el ultimo en modificar el archivo en esa rama
    cmd = f'git log -1 --format="%H|%h|%an|%ad|%s" --date=short origin/{branch_clean} -- "{file_path}" 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output:
        parts = output.split('|')
        if len(parts) >= 5:
            return {
                'full_hash': parts[0],
                'short_hash': parts[1],
                'author': parts[2],
                'date': parts[3],
                'message': '|'.join(parts[4:])  # Por si el mensaje tiene |
            }
    return None

def get_file_commit_history(file_path, branch, limit=None):
    """Obtiene el historial de commits de un archivo EN una rama especifica"""
    branch_clean = branch.replace("refs/heads/", "")

    # Obtener todos los commits del archivo (sin limite)
    limit_flag = f'-{limit} ' if limit else ''
    cmd = f'git log {limit_flag}--format="%H|%h|%an|%ad|%s" --date=short origin/{branch_clean} -- "{file_path}" 2>/dev/null'
    output, code = run_command(cmd)

    commits = []
    if code == 0 and output:
        for line in output.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'full_hash': parts[0],
                        'short_hash': parts[1],
                        'author': parts[2],
                        'date': parts[3],
                        'message': '|'.join(parts[4:])
                    })
    return commits

def get_approved_prs_by_date(date_str, target_branch=None, end_date_str=None):
    """Obtiene PRs completados en una fecha o rango de fechas (hora Bogota UTC-5)
    Usa az devops invoke con filtro por rango de fechas — funciona para cualquier fecha historica.
    Si end_date_str se proporciona, busca PRs entre date_str y end_date_str (inclusivo).
    """
    from datetime import datetime, timedelta

    # Calcular rango UTC para el dia en hora Bogota (UTC-5)
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start_utc = date_obj + timedelta(hours=5)
    if end_date_str:
        end_obj = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_utc = end_obj + timedelta(hours=5) + timedelta(days=1)
    else:
        end_utc = start_utc + timedelta(days=1)

    start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    # az devops invoke con filtro de fecha — busca PRs cerrados en el rango exacto
    cmd = (
        f'az devops invoke --area git --resource pullrequests '
        f'--route-parameters repositoryId={AZURE_REPO} '
        f'--query-parameters '
        f'"searchCriteria.status=completed'
        f'&searchCriteria.queryTimeRangeType=closed'
        f'&searchCriteria.minTime={start_iso}'
        f'&searchCriteria.maxTime={end_iso}'
        f'&$top=1000'
        f'" --api-version 7.1 -o json 2>/dev/null'
    )

    output, code = run_command(cmd)
    if code == 0 and output:
        try:
            result = json.loads(output)
            if isinstance(result, dict):
                return result.get('value', [])
            elif isinstance(result, list):
                return result
        except:
            pass

    # Fallback: az repos pr list (limitado a los ultimos PRs)
    print(f"      az devops invoke no disponible, usando fallback...")
    target_arg = f'--target-branch {target_branch}' if target_branch else ''
    cmd = f'az repos pr list --status completed {target_arg} --top 1000 -o json 2>/dev/null'
    output, code = run_command(cmd)
    if code != 0 or not output:
        return []
    try:
        all_prs = json.loads(output)
    except:
        return []

    filtered = []
    for pr in all_prs:
        closed_date_str = pr.get('closedDate', '')
        if not closed_date_str:
            continue
        try:
            closed_clean = closed_date_str[:19]
            closed_dt = datetime.strptime(closed_clean, '%Y-%m-%dT%H:%M:%S')
            if start_utc <= closed_dt < end_utc:
                filtered.append(pr)
        except:
            if closed_date_str.startswith(date_str):
                filtered.append(pr)
    return filtered


def get_pr_changed_files_by_merge_commit(merge_commit_id):
    """
    Obtiene archivos cambiados en un PR usando su merge commit ID.
    Usa git diff entre el padre del merge commit y el merge commit mismo,
    lo que refleja exactamente los cambios introducidos por el PR.
    Fallback: git show si el diff de padres no funciona.
    """
    if not merge_commit_id:
        return []

    # git diff <parent1> <merge_commit> — archivos exactos del PR
    cmd = f'git diff --name-only {merge_commit_id}^1 {merge_commit_id} 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output.strip():
        return [f for f in output.split('\n') if f.strip()]

    # Fallback: git show (muestra archivos del commit directamente)
    cmd = f'git show --name-only --format="" {merge_commit_id} 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output.strip():
        return [f for f in output.split('\n') if f.strip()]

    return []


def get_component_commit_count(file_path, branch):
    """Retorna el numero total de commits de un archivo en una rama (rapido)"""
    branch_clean = branch.replace("refs/heads/", "")
    cmd = f'git rev-list --count origin/{branch_clean} -- "{file_path}" 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output.strip().isdigit():
        return int(output.strip())
    return 0


def categorize_component(file_path):
    """Categoriza un componente segun su ruta"""
    # Componentes CORE (force-app)
    if '/classes/' in file_path and file_path.endswith('.cls'):
        return 'ApexClass'
    elif '/classes/' in file_path and file_path.endswith('.cls-meta.xml'):
        return 'ApexClass-meta'
    elif '/triggers/' in file_path:
        return 'ApexTrigger'
    elif '/lwc/' in file_path:
        return 'LWC'
    elif '/aura/' in file_path:
        return 'Aura'
    elif '/customMetadata/' in file_path:
        return 'CustomMetadata'
    elif '/objects/' in file_path and '/fields/' in file_path:
        return 'CustomField'
    elif '/objects/' in file_path:
        return 'CustomObject'
    elif '/flows/' in file_path:
        return 'Flow'
    elif '/layouts/' in file_path:
        return 'Layout'
    elif '/permissionsets/' in file_path:
        return 'PermissionSet'
    elif '/profiles/' in file_path:
        return 'Profile'
    elif '/pages/' in file_path:
        return 'VisualforcePage'
    elif '/staticresources/' in file_path:
        return 'StaticResource'
    elif '/labels/' in file_path:
        return 'CustomLabel'
    elif '/flexipages/' in file_path:
        return 'FlexiPage'
    elif '/queues/' in file_path:
        return 'Queue'
    elif '/groups/' in file_path:
        return 'Group'
    elif '/email/' in file_path:
        return 'EmailTemplate'
    elif '/reports/' in file_path:
        return 'Report'
    elif '/dashboards/' in file_path:
        return 'Dashboard'
    elif '/applications/' in file_path:
        return 'CustomApplication'
    elif '/quickActions/' in file_path:
        return 'QuickAction'
    elif '/globalValueSets/' in file_path:
        return 'GlobalValueSet'
    elif '/globalValueSetTranslations/' in file_path:
        return 'GlobalValueSetTranslation'
    elif '/decisionMatrixDefinition/' in file_path:
        return 'DecisionMatrixDefinition'
    elif '/documentTypes/' in file_path:
        return 'DocumentType'
    elif '/tabs/' in file_path:
        return 'CustomTab'
    elif '/remoteSiteSettings/' in file_path:
        return 'RemoteSiteSetting'
    elif '/namedCredentials/' in file_path:
        return 'NamedCredential'
    elif '/connectedApps/' in file_path:
        return 'ConnectedApp'
    elif '/platformEventChannels/' in file_path:
        return 'PlatformEventChannel'
    elif '/platformEventSubscriberConfigs/' in file_path:
        return 'PlatformEventSubscriberConfig'
    elif '/assignmentRules/' in file_path:
        return 'AssignmentRule'
    elif '/autoResponseRules/' in file_path:
        return 'AutoResponseRule'
    elif '/approvalProcesses/' in file_path:
        return 'ApprovalProcess'
    elif '/contentassets/' in file_path:
        return 'ContentAsset'
    elif '/dataSources/' in file_path:
        return 'ExternalDataSource'
    elif '/pathAssistants/' in file_path:
        return 'PathAssistant'
    elif '/recordTypes/' in file_path:
        return 'RecordType'
    elif '/validationRules/' in file_path:
        return 'ValidationRule'
    elif '/webLinks/' in file_path:
        return 'WebLink'
    elif '/actionPlanTemplates/' in file_path:
        return 'ActionPlanTemplate'
    elif '/workflowRules/' in file_path or '/workflows/' in file_path:
        return 'Workflow'
    elif '/messageChannels/' in file_path:
        return 'LightningMessageChannel'
    elif '/permissionsetgroups/' in file_path:
        return 'PermissionSetGroup'
    elif '/businessProcesses/' in file_path:
        return 'BusinessProcess'
    elif '/standardValueSets/' in file_path:
        return 'StandardValueSet'
    elif '/notificationtypes/' in file_path:
        return 'CustomNotificationType'
    elif '/reportTypes/' in file_path:
        return 'ReportType'
    # Componentes VLOCITY
    elif 'vlocity/IntegrationProcedure/' in file_path:
        return 'IntegrationProcedure'
    elif 'vlocity/DataRaptor/' in file_path:
        return 'DataRaptor'
    elif 'vlocity/OmniScript/' in file_path:
        return 'OmniScript'
    elif 'vlocity/FlexCard/' in file_path:
        return 'FlexCard'
    elif 'vlocity/VlocityUITemplate/' in file_path:
        return 'VlocityUITemplate'
    elif 'vlocity/AttributeCategory/' in file_path:
        return 'AttributeCategory'
    elif 'vlocity/Product2/' in file_path:
        return 'Product2'
    elif 'vlocity/CalculationMatrix/' in file_path:
        return 'CalculationMatrix'
    elif 'vlocity/CalculationProcedure/' in file_path:
        return 'CalculationProcedure'
    elif 'vlocity/' in file_path:
        # Extraer nombre de carpeta como tipo genérico Vlocity
        parts = file_path.split('vlocity/')
        if len(parts) > 1:
            folder = parts[1].split('/')[0]
            return folder
        return 'Vlocity-Other'
    elif 'force-app/main/default/' in file_path:
        # Extraer nombre de carpeta como tipo generico
        parts = file_path.split('force-app/main/default/')
        if len(parts) > 1:
            folder = parts[1].split('/')[0]
            return folder
        return 'Other'
    else:
        return 'Other'

def get_component_name(file_path):
    """Extrae el nombre del componente de la ruta"""
    basename = os.path.basename(file_path)
    # Quitar extensiones comunes
    for ext in ['.cls-meta.xml', '.cls', '.md-meta.xml', '.object-meta.xml',
                '.field-meta.xml', '.trigger-meta.xml', '.trigger', '.page-meta.xml',
                '.page', '.component-meta.xml', '.component', '.flow-meta.xml',
                '.xml', '.json']:
        if basename.endswith(ext):
            basename = basename[:-len(ext)]
            break
    return basename

def parse_package_xml(xml_path):
    """
    Parsea un package.xml y retorna lista de (tipo, nombre)
    """
    components = []

    if not os.path.exists(xml_path):
        print(f"Advertencia: No se encontro el archivo {xml_path}")
        return components

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Manejar namespace de Salesforce
        ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}

        # Buscar con y sin namespace
        types_elements = root.findall('.//sf:types', ns)
        if not types_elements:
            types_elements = root.findall('.//types')

        for types_elem in types_elements:
            # Obtener el nombre del tipo
            name_elem = types_elem.find('sf:name', ns)
            if name_elem is None:
                name_elem = types_elem.find('name')
            if name_elem is None:
                continue

            component_type = name_elem.text

            # Obtener todos los members
            members = types_elem.findall('sf:members', ns)
            if not members:
                members = types_elem.findall('members')
            for member in members:
                if member.text and member.text != '*':
                    components.append((component_type, member.text))

    except ET.ParseError as e:
        print(f"Error parseando XML {xml_path}: {e}")

    return components

def parse_package_yaml(yaml_path):
    """
    Parsea un package.yaml de Vlocity y retorna lista de (tipo, nombre)
    El formato esperado es lineas como:
    - IntegrationProcedure/NombreIP
    - DataRaptor/NombreDR
    """
    components = []

    if not os.path.exists(yaml_path):
        print(f"Advertencia: No se encontro el archivo {yaml_path}")
        return components

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        in_manifest = False

        for line in lines:
            stripped = line.strip()

            # Detectar inicio de seccion manifest
            if stripped.startswith('manifest:'):
                in_manifest = True
                continue

            # Detectar fin de seccion manifest (otra clave de nivel superior)
            if in_manifest and ':' in stripped and not stripped.startswith('-'):
                in_manifest = False
                continue

            # Procesar componentes dentro de manifest
            if in_manifest and stripped.startswith('- '):
                component = stripped[2:].strip()
                # Limpiar comentarios YAML (ej: "# cancelaciones arrendamiento")
                component = component.split('#')[0].strip()

                # Buscar patron Tipo/Nombre
                if '/' in component:
                    parts = component.split('/')
                    if len(parts) >= 2:
                        component_type = parts[0].strip()
                        component_name = '/'.join(parts[1:]).strip()

                        # Verificar que sea un tipo conocido de Vlocity
                        if component_type in VLOCITY_TYPE_PATHS:
                            components.append((component_type, component_name))

    except Exception as e:
        print(f"Error leyendo YAML {yaml_path}: {e}")

    return components

def load_hybrid_set():
    """
    Carga las listas de componentes híbridos (package_hibridos.xml y package_hibridos.yaml)
    Retorna un set de nombres de componentes híbridos para búsqueda rápida.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    hybrid_xml = os.path.join(script_dir, 'package_hibridos.xml')
    hybrid_yaml = os.path.join(script_dir, 'package_hibridos.yaml')

    hybrid_names = set()

    # Cargar híbridos CORE desde XML
    if os.path.exists(hybrid_xml):
        core_hybrids = parse_package_xml(hybrid_xml)
        for comp_type, comp_name in core_hybrids:
            hybrid_names.add(comp_name)

    # Cargar híbridos Vlocity desde YAML
    if os.path.exists(hybrid_yaml):
        vlocity_hybrids = parse_package_yaml(hybrid_yaml)
        for comp_type, comp_name in vlocity_hybrids:
            hybrid_names.add(comp_name)

    return hybrid_names

def find_component_path(component_type, component_name, repo_root):
    """
    Encuentra la ruta del archivo/directorio de un componente
    """
    import glob as glob_module

    # Intentar con rutas de metadata Salesforce
    if component_type in METADATA_TYPE_PATHS:
        path_template = METADATA_TYPE_PATHS[component_type]

        # Manejar casos especiales como CustomField (Object.Field)
        if component_type == 'CustomField' and '.' in component_name:
            obj, field = component_name.rsplit('.', 1)
            path = path_template.format(object=obj, field=field)
        elif component_type == 'RecordType' and '.' in component_name:
            obj, rt = component_name.rsplit('.', 1)
            path = path_template.format(object=obj, name=rt)
        elif component_type == 'ListView' and '.' in component_name:
            obj, lv = component_name.rsplit('.', 1)
            path = path_template.format(object=obj, name=lv)
        elif component_type == 'ValidationRule' and '.' in component_name:
            obj, vr = component_name.rsplit('.', 1)
            path = path_template.format(object=obj, name=vr)
        elif component_type == 'BusinessProcess' and '.' in component_name:
            obj, bp = component_name.rsplit('.', 1)
            path = path_template.format(object=obj, name=bp)
        else:
            path = path_template.format(name=component_name)

        full_path = os.path.join(repo_root, path)

        # Si tiene wildcard, buscar el archivo
        if '*' in path:
            matches = glob_module.glob(full_path)
            if matches:
                return matches[0]
        elif os.path.exists(full_path):
            return full_path

        # Para directorios, verificar si existe
        if path.endswith('/'):
            dir_path = full_path.rstrip('/')
            if os.path.isdir(dir_path):
                return dir_path

    # Intentar con rutas Vlocity
    if component_type in VLOCITY_TYPE_PATHS:
        path_template = VLOCITY_TYPE_PATHS[component_type]
        path = path_template.format(name=component_name)
        full_path = os.path.join(repo_root, path.rstrip('/'))

        if os.path.exists(full_path):
            return full_path

    return None

def get_icon_class(category):
    """Retorna la clase de icono segun categoria"""
    icons = {
        'ApexClass': 'icon-apex',
        'ApexClass-meta': 'icon-apex',
        'ApexTrigger': 'icon-apex',
        'LWC': 'icon-lwc',
        'Aura': 'icon-aura',
        'CustomMetadata': 'icon-metadata',
        'CustomField': 'icon-object',
        'CustomObject': 'icon-object',
        'Flow': 'icon-flow',
        'Layout': 'icon-layout',
        'PermissionSet': 'icon-perm',
        'Profile': 'icon-perm',
        'IntegrationProcedure': 'icon-vlocity',
        'DataRaptor': 'icon-vlocity',
        'OmniScript': 'icon-vlocity',
        'FlexCard': 'icon-vlocity',
        'VlocityUITemplate': 'icon-vlocity',
        'Vlocity-Other': 'icon-vlocity',
        'AttributeCategory': 'icon-vlocity',
        'Product2': 'icon-vlocity',
        'CalculationMatrix': 'icon-vlocity',
        'CalculationProcedure': 'icon-vlocity',
        'CustomApplication': 'icon-metadata',
        'QuickAction': 'icon-flow',
        'GlobalValueSet': 'icon-metadata',
        'GlobalValueSetTranslation': 'icon-metadata',
        'DecisionMatrixDefinition': 'icon-metadata',
        'DocumentType': 'icon-metadata',
        'CustomTab': 'icon-layout',
        'RemoteSiteSetting': 'icon-perm',
        'NamedCredential': 'icon-perm',
        'ConnectedApp': 'icon-perm',
        'PlatformEventChannel': 'icon-flow',
        'PlatformEventSubscriberConfig': 'icon-flow',
        'AssignmentRule': 'icon-flow',
        'AutoResponseRule': 'icon-flow',
        'ApprovalProcess': 'icon-flow',
        'ContentAsset': 'icon-other',
        'ExternalDataSource': 'icon-metadata',
        'PathAssistant': 'icon-flow',
        'RecordType': 'icon-object',
        'ValidationRule': 'icon-flow',
        'WebLink': 'icon-layout',
        'ActionPlanTemplate': 'icon-metadata',
        'Workflow': 'icon-flow',
        'LightningMessageChannel': 'icon-lwc',
        'PermissionSetGroup': 'icon-perm',
        'VisualforcePage': 'icon-layout',
        'StaticResource': 'icon-other',
        'CustomLabel': 'icon-metadata',
        'FlexiPage': 'icon-layout',
        'Queue': 'icon-perm',
        'Group': 'icon-perm',
        'EmailTemplate': 'icon-layout',
        'Report': 'icon-metadata',
        'Dashboard': 'icon-metadata',
        'Other': 'icon-other'
    }
    return icons.get(category, 'icon-other')

def get_icon_letter(category):
    """Retorna la letra del icono segun categoria"""
    letters = {
        'ApexClass': 'A',
        'ApexClass-meta': 'A',
        'ApexTrigger': 'T',
        'LWC': 'L',
        'Aura': 'Au',
        'CustomMetadata': 'M',
        'CustomField': 'F',
        'CustomObject': 'O',
        'Flow': 'Fl',
        'Layout': 'Ly',
        'PermissionSet': 'PS',
        'Profile': 'Pr',
        'IntegrationProcedure': 'IP',
        'DataRaptor': 'DR',
        'OmniScript': 'OS',
        'FlexCard': 'FC',
        'VlocityUITemplate': 'VT',
        'Vlocity-Other': 'V',
        'AttributeCategory': 'AC',
        'Product2': 'P2',
        'CalculationMatrix': 'CM',
        'CalculationProcedure': 'CP',
        'CustomApplication': 'App',
        'QuickAction': 'QA',
        'GlobalValueSet': 'GV',
        'GlobalValueSetTranslation': 'GT',
        'DecisionMatrixDefinition': 'DM',
        'DocumentType': 'DT',
        'CustomTab': 'Tab',
        'RemoteSiteSetting': 'RS',
        'NamedCredential': 'NC',
        'ConnectedApp': 'CA',
        'PlatformEventChannel': 'PE',
        'PlatformEventSubscriberConfig': 'PS',
        'AssignmentRule': 'AR',
        'AutoResponseRule': 'RR',
        'ApprovalProcess': 'AP',
        'ContentAsset': 'CA',
        'ExternalDataSource': 'DS',
        'PathAssistant': 'PA',
        'RecordType': 'RT',
        'ValidationRule': 'VR',
        'WebLink': 'WL',
        'ActionPlanTemplate': 'AT',
        'Workflow': 'WF',
        'LightningMessageChannel': 'MC',
        'PermissionSetGroup': 'PG',
        'VisualforcePage': 'VF',
        'StaticResource': 'SR',
        'CustomLabel': 'CL',
        'FlexiPage': 'FP',
        'Queue': 'Qu',
        'Group': 'Gr',
        'EmailTemplate': 'ET',
        'Report': 'Rp',
        'Dashboard': 'Db',
        'Other': '?'
    }
    return letters.get(category, '?')

def generate_html(pr_info, components_by_category, compare_branch, pr_id, output_file, report_type='pr', report_title=None, manifest_xml_path=None, manifest_yaml_path=None):
    """Genera el archivo HTML

    Args:
        pr_info: Información del PR (puede ser None para reportes tipo 'manifest')
        components_by_category: Componentes organizados por categoría
        compare_branch: Rama contra la que se compara
        pr_id: ID del PR o identificador del reporte
        output_file: Ruta del archivo de salida
        report_type: Tipo de reporte ('pr' o 'manifest')
        report_title: Título personalizado del reporte (opcional)
    """

    # Cargar set de componentes híbridos
    hybrid_names = load_hybrid_set()

    # Obtener información de las ramas
    if pr_info:
        source_branch = pr_info.get('sourceBranch', '').replace('refs/heads/', '')
        target_branch = pr_info.get('targetBranch', '').replace('refs/heads/', '')
    else:
        source_branch = None
        target_branch = None

    compare_branch_clean = compare_branch.replace('refs/heads/', '')

    # Separar componentes CORE y VLOCITY
    VLOCITY_TYPES = {'IntegrationProcedure', 'DataRaptor', 'OmniScript', 'FlexCard',
                     'VlocityUITemplate', 'AttributeCategory', 'Product2',
                     'CalculationMatrix', 'CalculationProcedure', 'Vlocity-Other'}

    core_components = {}
    vlocity_components = {}

    for category, comps in components_by_category.items():
        if category in VLOCITY_TYPES:
            vlocity_components[category] = comps
        else:
            core_components[category] = comps

    total_components = sum(len(comps) for comps in components_by_category.values())
    core_count = sum(len(comps) for comps in core_components.values())
    vlocity_count = sum(len(comps) for comps in vlocity_components.values())

    # Paleta de colores para autores (misma del daily)
    AUTHOR_COLORS = [
        '#5BA4D9',  # azul cielo
        '#E07070',  # rojo suave
        '#6DC96D',  # verde
        '#C49BDE',  # lavanda
        '#D4A85C',  # dorado
        '#4ECDC4',  # turquesa
        '#FF8A80',  # salmon
        '#82B1FF',  # azul claro
        '#B9F6CA',  # verde menta
        '#FFD180',  # naranja claro
    ]
    unique_authors = set()
    for comps in components_by_category.values():
        for c in comps:
            unique_authors.add(c.get('author', ''))
            for h in c.get('history', []):
                unique_authors.add(h.get('author', ''))
    unique_authors.discard('')
    author_color_map = {}
    for idx, author in enumerate(sorted(unique_authors)):
        author_color_map[author] = AUTHOR_COLORS[idx % len(AUTHOR_COLORS)]

    # Obtener autores vigilados para detección de posible híbrido
    watched_set = get_watched_authors()

    # Detectar posibles híbridos por sección (CORE / VLOCITY)
    # Posible híbrido solo si hay MEZCLA de vigilados y no vigilados
    def detect_hybrid_alert(section_components):
        hybrid_comps = set()
        for cat, comps in section_components.items():
            for comp in comps:
                if comp['name'] in hybrid_names:
                    continue
                has_watched = False
                has_unwatched = False
                for h in comp.get('history', []):
                    h_author = h.get('author', '').lower()
                    if not h_author:
                        continue
                    if h_author in watched_set:
                        has_watched = True
                    else:
                        has_unwatched = True
                    if has_watched and has_unwatched:
                        hybrid_comps.add(comp['name'])
                        break
        if hybrid_comps:
            tooltip = f"{len(hybrid_comps)} componente(s) con commits de ambos equipos"
            return f'<span class="watch-alert-badge" title="{tooltip}">⚠ posible híbrido</span>'
        return ''

    core_alert_html = detect_hybrid_alert(core_components) if core_components else ''
    vlocity_alert_html = detect_hybrid_alert(vlocity_components) if vlocity_components else ''

    # Generar timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Definir títulos según el tipo de reporte
    if report_title:
        page_title = report_title
    elif report_type == 'manifest':
        page_title = f"Reporte de Verificación de Manifest vs {compare_branch_clean.upper()}"
    else:  # 'pr'
        page_title = f"Reporte de Componentes del PR #{pr_id} vs {compare_branch_clean.upper()}"

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        :root {{
            --bg-primary: #1E2A4A;
            --bg-secondary: #0D0D1A;
            --bg-card: rgba(43,58,103,0.25);
            --bg-card-hover: rgba(43,58,103,0.40);
            --bg-table-header: rgba(0,0,0,0.30);
            --accent: #C4884D;
            --accent-soft: rgba(196,136,77,0.15);
            --accent-border: rgba(196,136,77,0.3);
            --accent-secondary: #CC3333;
            --text-primary: #F5E6D8;
            --text-secondary: #C4A882;
            --text-muted: #7A8A99;
            --border: rgba(255,255,255,0.08);
            --border-accent: rgba(196,136,77,0.2);
            --success: #4CAF50;
            --danger: #CC3333;
            --core-color: #6A8FD4;
            --vlocity-color: #9B6FC0;
            --hybrid-color: #C4884D;
            --commit-color: #F5D0B0;
            --commit-bg: rgba(245,208,176,0.12);
        }}
        [data-theme="light"] {{
            --bg-primary: #FFFAF5;
            --bg-secondary: #FFF5EB;
            --bg-card: rgba(30,42,74,0.04);
            --bg-card-hover: rgba(30,42,74,0.08);
            --bg-table-header: rgba(30,42,74,0.06);
            --accent: #1E2A4A;
            --accent-soft: rgba(30,42,74,0.08);
            --accent-border: rgba(30,42,74,0.2);
            --accent-secondary: #C4884D;
            --text-primary: #0D0D1A;
            --text-secondary: #3D4F6A;
            --text-muted: #8A9AB0;
            --border: rgba(0,0,0,0.08);
            --border-accent: rgba(30,42,74,0.15);
            --success: #388E3C;
            --danger: #CC3333;
            --core-color: #2B3A67;
            --vlocity-color: #4A3F8A;
            --hybrid-color: #D46A15;
            --commit-color: #B85C10;
            --commit-bg: rgba(184,92,16,0.08);
        }}
        html, body {{ overflow-x: hidden; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-secondary);
            min-height: 100vh; padding: 15px; color: var(--text-primary);
            transition: background 0.3s ease, color 0.3s ease;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; overflow: hidden; }}
        .header {{
            background: var(--bg-primary);
            border-radius: 12px; padding: 12px 20px; margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15); border: 1px solid var(--border);
            display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        }}
        .header-logo {{
            width: 36px; height: 36px; border-radius: 8px;
            background: var(--accent); display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; box-shadow: 0 2px 8px rgba(196,136,77,0.3);
        }}
        .header-logo svg {{ width: 22px; height: 22px; color: #0D0D1A; }}
        [data-theme="light"] .header-logo svg {{ color: #8A9AB0; }}
        .header-info {{ flex: 1; }}
        .header h1 {{ font-size: 16px; margin-bottom: 2px; color: var(--accent); }}
        .header .subtitle {{ color: var(--text-muted); font-size: 12px; }}
        .theme-toggle {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 8px 14px; border-radius: 8px; cursor: pointer;
            font-size: 13px; font-weight: 600; transition: all 0.2s ease; flex-shrink: 0;
        }}
        .theme-toggle:hover {{ background: var(--accent-border); }}
        .summary-bar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
        .summary-card {{
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 130px;
            transition: all 0.2s ease;
        }}
        .summary-card:hover {{ border-color: var(--accent-border); background: var(--bg-card-hover); }}
        .summary-card label {{ font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.2px; display: block; }}
        .summary-card value {{ display: block; font-size: 24px; color: var(--accent); font-weight: 700; margin-top: 4px; }}
        .summary-card .sub-value {{ font-size: 11px; color: var(--text-secondary); margin-top: 2px; }}
        .badges {{ display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }}
        .badge {{ padding: 6px 12px; border-radius: 16px; font-size: 11px; font-weight: 600; }}
        .badge-core {{ background: var(--accent-soft); color: var(--accent); border: 1px solid var(--accent-border); }}
        .badge-count {{ background: var(--accent-soft); color: var(--accent); border: 1px solid var(--accent-border); }}
        .search-box {{
            width: 100%; padding: 10px 15px; border-radius: 8px;
            border: 1px solid var(--border); background: var(--bg-card);
            color: var(--text-primary); font-size: 13px; margin-bottom: 20px;
            transition: border-color 0.2s ease;
        }}
        .search-box::placeholder {{ color: var(--text-muted); }}
        .search-box:focus {{ outline: none; border-color: var(--accent); }}
        .toggle-all-btn {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 6px 14px; border-radius: 8px; cursor: pointer;
            font-size: 12px; font-weight: 600; transition: all 0.2s ease; white-space: nowrap;
        }}
        .toggle-all-btn:hover {{ background: var(--accent-border); }}
        .section {{
            background: var(--bg-card); border-radius: 8px; margin: 8px;
            overflow: hidden; border: 1px solid var(--border); min-width: 0;
        }}
        .section-header {{
            display: flex; align-items: center; padding: 10px 14px;
            background: var(--bg-table-header);
            border-bottom: 1px solid var(--border);
            cursor: pointer; user-select: none; transition: background 0.2s ease;
        }}
        .section-header:hover {{ background: var(--bg-card-hover); }}
        .section-body {{ transition: max-height 0.3s ease; overflow: hidden; max-width: 100%; min-width: 0; }}
        .section-body.collapsed {{ display: none; }}
        .section-toggle {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 18px; height: 18px; flex-shrink: 0; color: var(--accent);
            font-size: 10px; margin-right: 6px; transition: transform 0.3s ease;
        }}
        .section-toggle.collapsed {{ transform: rotate(-90deg); }}
        .section-icon {{
            width: 28px; height: 28px; border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; margin-right: 10px; font-size: 11px;
        }}
        .icon-apex {{ background: linear-gradient(135deg, #CC3333, #E85050); color: white; }}
        .icon-metadata {{ background: linear-gradient(135deg, #4A3F8A, #6A5FCF); color: white; }}
        .icon-object {{ background: linear-gradient(135deg, #1E2A4A, #3D5A8A); color: white; }}
        .icon-flow {{ background: linear-gradient(135deg, #2E7D32, #4CAF50); color: white; }}
        .icon-lwc {{ background: linear-gradient(135deg, #2B3A67, #6A8FD4); color: white; }}
        .icon-aura {{ background: linear-gradient(135deg, #CC3333, #C4884D); color: white; }}
        .icon-layout {{ background: linear-gradient(135deg, #D46A15, #C4884D); color: white; }}
        .icon-perm {{ background: linear-gradient(135deg, #00695C, #26A69A); color: white; }}
        .icon-vlocity {{ background: linear-gradient(135deg, #4A3F8A, #9B6FC0); color: white; }}
        .icon-other {{ background: linear-gradient(135deg, #546E7A, #78909C); color: white; }}
        .section-title {{ font-size: 13px; color: var(--text-primary); font-weight: 600; }}
        .section-count {{
            margin-left: 8px; padding: 2px 8px; background: var(--accent-soft);
            border-radius: 12px; font-size: 10px; color: var(--accent);
        }}
        .table-wrapper {{ overflow-x: auto; max-width: 100%; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        th {{
            text-align: left; padding: 10px 12px; background: var(--bg-table-header);
            color: var(--text-muted); font-size: 10px; text-transform: uppercase;
            letter-spacing: 1px; font-weight: 600;
        }}
        th:nth-child(1) {{ width: 28%; }}
        th:nth-child(2) {{ width: 7%; }}
        th:nth-child(3) {{ width: 12%; }}
        th:nth-child(4) {{ width: 18%; }}
        th:nth-child(5) {{ width: 14%; white-space: nowrap; }}
        th:nth-child(6) {{ width: 21%; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; max-width: 0; }}
        tr:hover {{ background: var(--bg-card-hover); }}
        .component-name {{ display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; }}
        .status-icon {{
            width: 20px; height: 20px; border-radius: 50%;
            background: var(--accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }}
        .status-icon svg {{ width: 12px; height: 12px; fill: var(--bg-secondary); }}
        .component-text {{ color: var(--text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; cursor: pointer; position: relative; font-size: 13px; }}
        .component-text:hover {{ color: var(--accent); }}
        .component-tooltip {{
            display: none; position: absolute; top: calc(100% + 8px); left: 0;
            background: var(--bg-primary); color: var(--text-primary);
            padding: 8px 12px; border-radius: 8px; font-size: 13px; white-space: nowrap;
            z-index: 1000; border: 1px solid var(--accent-border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4); pointer-events: none;
        }}
        .component-tooltip::after {{
            content: ''; position: absolute; bottom: 100%; left: 16px;
            border-width: 6px; border-style: solid;
            border-color: transparent transparent var(--bg-primary) transparent;
        }}
        .component-text:hover .component-tooltip {{ display: block; }}
        .commit-cell {{ display: flex; align-items: center; gap: 6px; }}
        .commit-hash {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--commit-color); background: var(--commit-bg);
            padding: 4px 10px; border-radius: 6px; text-decoration: none; transition: all 0.2s ease;
        }}
        .commit-hash:hover {{ opacity: 0.8; }}
        .copy-commit-btn {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 4px 8px; border-radius: 4px; cursor: pointer;
            font-size: 11px; transition: all 0.2s ease; display: inline-flex; align-items: center; gap: 4px;
        }}
        .copy-commit-btn:hover {{ background: var(--accent-border); }}
        .commit-new {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--success); background: rgba(76,175,80,0.15);
            padding: 4px 10px; border-radius: 6px; font-weight: bold;
        }}
        .hybrid-badge {{
            font-size: 10px; color: var(--hybrid-color); background: rgba(196,136,77,0.15);
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
            border: 1px solid rgba(196,136,77,0.3); text-align: center;
        }}
        .hybrid-possible-badge {{
            font-size: 10px; color: #E8A040; background: rgba(232,122,29,0.15);
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
            border: 1px solid rgba(232,122,29,0.3); text-align: center;
        }}
        .watch-alert-badge {{
            display: inline-flex; align-items: center; gap: 4px;
            background: rgba(232,122,29,0.15); color: #E8A040;
            border: 1px solid rgba(232,122,29,0.3); padding: 3px 10px;
            border-radius: 6px; font-size: 11px; font-weight: 600;
            margin-left: 8px; white-space: nowrap; cursor: default;
        }}
        .row-new {{ background: rgba(76,175,80,0.06); }}
        .row-not-found {{ background: rgba(196,136,77,0.06); }}
        .commit-not-found {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 11px;
            color: var(--accent); background: var(--accent-soft);
            padding: 4px 10px; border-radius: 6px; font-weight: bold;
        }}
        .author-new {{ color: var(--success); font-style: italic; font-size: 13px; }}
        .author-not-found {{ color: var(--accent); font-style: italic; font-size: 13px; }}
        .author {{ color: var(--text-secondary); font-size: 13px; }}
        .date {{ color: var(--text-muted); font-size: 13px; }}
        .message {{ color: var(--text-secondary); font-size: 13px; max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .footer {{
            display: flex; flex-direction: column; align-items: flex-end;
            padding: 20px; color: var(--text-muted); font-size: 11px; gap: 15px;
        }}
        .footer-text {{ width: 100%; text-align: center; }}
        .delete-btn {{
            background: linear-gradient(135deg, #EF5350, #D32F2F); color: white;
            border: none; padding: 10px 20px; border-radius: 8px; font-size: 12px;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
        }}
        .delete-btn:hover {{ background: linear-gradient(135deg, #D32F2F, #B71C1C); }}
        .toast {{
            position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: var(--accent); color: var(--bg-secondary); padding: 15px 30px;
            border-radius: 8px; font-size: 13px; font-weight: 600;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 10000; display: none;
        }}
        .pr-info {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px; margin-top: 15px;
        }}
        .pr-info-item {{ background: var(--bg-card); padding: 10px 12px; border-radius: 6px; }}
        .pr-info-item label {{ font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
        .pr-info-item value {{ display: block; font-size: 14px; color: var(--text-primary); margin-top: 5px; word-break: break-word; }}
        .highlight {{ color: var(--accent); }}
        .clickable {{ cursor: pointer; transition: all 0.2s ease; }}
        .clickable:hover {{ background: var(--accent-soft); border-radius: 6px; padding: 4px; margin: -4px; }}
        .history-badge {{
            display: inline-flex; align-items: center; justify-content: center;
            background: #5A6785; color: #D0D8E8;
            width: 20px; height: 20px; border-radius: 50%; font-size: 10px;
            font-weight: bold; flex-shrink: 0; margin-left: 6px;
        }}
        .history-row td {{ padding: 0; background: var(--bg-table-header); border-bottom: 1px solid var(--border); }}
        .history-container {{ padding: 16px 20px; }}
        .history-header {{
            display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
            color: var(--accent); font-size: 13px; font-weight: 600;
        }}
        .history-icon {{ flex-shrink: 0; color: var(--accent); }}
        .history-list {{ display: flex; flex-direction: column; gap: 0; }}
        .history-item, .history-item-latest {{ display: flex; gap: 12px; padding: 8px 0; }}
        .history-timeline {{
            display: flex; flex-direction: column; align-items: center;
            width: 20px; flex-shrink: 0; padding-top: 2px;
        }}
        .timeline-dot {{
            width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
            background: var(--accent-soft); border: 2px solid var(--accent-border);
        }}
        .timeline-dot-latest {{
            background: var(--accent); border-color: var(--accent);
            box-shadow: 0 0 8px rgba(196,136,77,0.5);
        }}
        .timeline-line {{
            width: 2px; flex: 1; min-height: 20px;
            background: linear-gradient(180deg, var(--accent-border) 0%, transparent 100%);
            margin-top: 4px;
        }}
        .history-content {{ flex: 1; min-width: 0; padding-bottom: 8px; }}
        .history-top {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }}
        .history-commit-wrapper {{ display: flex; align-items: center; gap: 6px; }}
        .history-commit {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--commit-color); background: var(--commit-bg);
            padding: 3px 8px; border-radius: 4px; text-decoration: none;
        }}
        .history-commit:hover {{ opacity: 0.8; }}
        .history-author {{ color: var(--text-secondary); font-size: 12px; }}
        .history-date {{ color: var(--text-muted); font-size: 11px; margin-left: auto; }}
        .history-message {{ color: var(--text-secondary); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        /* Secciones principales CORE/VLOCITY */
        .main-section {{
            background: var(--bg-card); border-radius: 12px; margin-bottom: 20px;
            overflow: hidden; border: 1px solid var(--border-accent);
            max-width: 100%; box-sizing: border-box; min-width: 0;
        }}
        .main-section-header {{
            background: var(--bg-primary);
            padding: 16px 20px; border-bottom: 1px solid var(--border-accent);
            cursor: pointer; user-select: none; transition: background 0.2s ease;
            display: flex; align-items: center; gap: 12px;
        }}
        .main-section-header:hover {{ background: var(--bg-card-hover); }}
        .main-section-body {{ transition: max-height 0.3s ease; overflow: hidden; padding: 8px 16px; min-width: 0; max-width: 100%; }}
        .main-section-body.collapsed {{ display: none; }}
        .main-toggle {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
            background: var(--accent-soft); color: var(--accent); font-size: 12px;
            transition: transform 0.3s ease;
        }}
        .main-toggle.collapsed {{ transform: rotate(-90deg); }}
        .main-section-title {{ display: flex; align-items: center; gap: 12px; }}
        .main-section-icon {{
            width: 34px; height: 34px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 12px; flex-shrink: 0; letter-spacing: 0.5px;
        }}
        .icon-core {{ background: #5BA4D9; color: white; }}
        .icon-vlocity-main {{ background: #5BA4D9; color: white; }}
        .main-section-name {{ font-size: 12px; font-weight: 700; color: var(--accent); }}
        .main-section-count {{
            margin-left: auto; padding: 3px 10px;
            background: var(--accent-soft); border-radius: 12px;
            font-size: 11px; color: var(--accent); font-weight: 600;
        }}
        .main-section-subtitle {{ color: var(--text-muted); font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
            </div>
            <div class="header-info">'''

    # Construir contenido dinámico del card Manifest
    has_both_manifests = core_count > 0 and manifest_xml_path and vlocity_count > 0 and manifest_yaml_path
    bullet = '• ' if has_both_manifests else ''
    manifest_card_content = ''
    if core_count > 0 and manifest_xml_path:
        manifest_card_content += f'<value style="font-size:12px; margin-top:8px;">{bullet}{manifest_xml_path}</value>'
    if vlocity_count > 0 and manifest_yaml_path:
        manifest_card_content += f'<value style="font-size:12px; margin-top:4px;">{bullet}{manifest_yaml_path}</value>'

    # Generar título según el tipo de reporte
    if report_type == 'manifest':
        html += f'''
                <h1>Reporte de Verificación de Manifest vs <span style="color:#ff4444">{compare_branch_clean.upper()}</span></h1>
                <p class="subtitle">Componentes del manifest, su historial de commits y alertas de posible híbrido en la rama de comparación</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">🌙 Modo oscuro</button>
        </div>
        <div class="summary-bar">
            <div class="summary-card">
                <label>Total</label>
                <value>{total_components}</value>
                <div class="sub-value">componentes</div>
            </div>
            <div class="summary-card">
                <label>CORE</label>
                <value>{core_count}</value>
            </div>
            <div class="summary-card">
                <label>Vlocity</label>
                <value>{vlocity_count}</value>
            </div>
            <div class="summary-card">
                <label>Manifest</label>
                {manifest_card_content}
            </div>
        </div>'''
    else:  # 'pr'
        html += f'''
                <h1>Reporte de Componentes del PR #{pr_id} vs <span style="color:#ff4444">{compare_branch_clean.upper()}</span></h1>
                <p class="subtitle">Análisis de componentes modificados por el PR, historial de autoría y detección de posible híbrido</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">🌙 Modo oscuro</button>
        </div>
        <div class="summary-bar">
            <div class="summary-card">
                <label>PR</label>
                <value style="font-size:12px; margin-top:8px;">ID: {pr_id}</value>
                <div class="sub-value">Estado: {pr_info.get('status', 'N/A').capitalize()}</div>
                <div class="sub-value">Autor: {pr_info.get('author', 'N/A')}</div>
            </div>
            <div class="summary-card">
                <label>Total Componentes</label>
                <value>{total_components}</value>
                <div class="sub-value">Core: {core_count} | Vlocity: {vlocity_count}</div>
            </div>
            <div class="summary-card">
                <label>Ramas</label>
                <value style="font-size:12px; margin-top:8px;">Origen: {source_branch}</value>
                <div class="sub-value">Destino: {target_branch}</div>
            </div>
            <div class="summary-card">
                <label>Comparado vs</label>
                <value style="font-size:14px; margin-top:8px;"><span style="color:#ff4444">{compare_branch_clean.upper()}</span></value>
            </div>
        </div>'''

    html += '''
        </div>

        <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center;">
            <input type="text" class="search-box" placeholder="Buscar por componente, autor o mensaje..." onkeyup="filterTable(this.value)" style="margin-bottom: 0; flex: 1;">
            <button class="toggle-all-btn" onclick="toggleAllSections()">▶ Expandir todos</button>
        </div>
'''

    # Función auxiliar para generar una categoría
    def generate_category_section(category, components):
        nonlocal html
        if not components:
            return

        icon_class = get_icon_class(category)
        icon_letter = get_icon_letter(category)

        cat_id = f"cat_{category.replace(' ', '_').replace('-', '_')}"
        html += f'''
        <div class="section">
            <div class="section-header" onclick="toggleCategory('{cat_id}', this)">
                <span class="section-toggle" id="toggle-icon-{cat_id}">▼</span>
                <span class="section-title">{category}</span>
                <span class="section-count">{len(components)} componente{"s" if len(components) > 1 else ""}</span>
            </div>
            <div class="section-body" id="{cat_id}">
            <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Componente</th>
                        <th>Híbrido</th>
                        <th>Commit</th>
                        <th>Autor</th>
                        <th>Aprobado (YY-MM-DD)</th>
                        <th>Mensaje</th>
                    </tr>
                </thead>
                <tbody>
'''
        for idx, comp in enumerate(components):
            is_new = comp.get('is_new', False)
            commit_url = f"{BASE_URL}/commit/{comp['full_hash']}" if comp.get('full_hash') else "#"
            short_hash = comp.get('short_hash', 'N/A')
            history = comp.get('history', [])
            has_history = len(history) > 1  # Si hay mas de 1 commit (el actual + anteriores)

            # ID unico para este componente
            comp_id = f"{category}_{idx}"

            # Estilos diferentes para componentes nuevos, no encontrados, o existentes
            is_not_found = comp.get('not_found', False)
            if is_not_found:
                row_class = "row-not-found"
                hash_html = f'<span class="commit-not-found">NO LOCAL</span>'
                author_class = "author-not-found"
            elif is_new:
                row_class = "row-new"
                hash_html = f'<span class="commit-new">{short_hash}</span>'
                author_class = "author-new"
            else:
                row_class = ""
                copy_btn = f'<button class="copy-commit-btn" onclick="copyCommitUrl(\'{commit_url}\')" title="Copiar URL del commit">📋</button>'
                hash_html = f'<div class="commit-cell"><a href="{commit_url}" target="_blank" class="commit-hash">{short_hash}</a>{copy_btn}</div>'
                author_class = "author"

            # Indicador de historial disponible
            history_indicator = ""
            if has_history:
                history_indicator = f'<span class="history-badge" title="Click para ver {len(history)} commits">{len(history)}</span>'

            # Construir atributos del div component-name
            clickable_class = 'clickable' if has_history else ''
            onclick_attr = f'onclick="toggleHistory(\'{comp_id}\')"' if has_history else ''

            # Verificar si es componente híbrido o posible híbrido
            is_hybrid = comp['name'] in hybrid_names
            is_possible_hybrid = False
            if not is_hybrid:
                # Posible híbrido solo si hay MEZCLA de vigilados y no vigilados
                has_watched = False
                has_unwatched = False
                for h in comp.get('history', []):
                    h_author = h.get('author', '').lower()
                    if not h_author:
                        continue
                    if h_author in watched_set:
                        has_watched = True
                    else:
                        has_unwatched = True
                    if has_watched and has_unwatched:
                        is_possible_hybrid = True
                        break
            if is_hybrid:
                hybrid_html = '<span class="hybrid-badge">SI</span>'
            elif is_possible_hybrid:
                hybrid_html = '<span class="hybrid-possible-badge">posible</span>'
            else:
                hybrid_html = ''

            html += f'''
                    <tr class="{row_class} main-row" data-component-id="{comp_id}">
                        <td>
                            <div class="component-name {clickable_class}" {onclick_attr}>
                                <span class="component-text" onclick="copyComponentName(event, &#39;{comp['name']}&#39;)"><span class="component-tooltip">{comp['name']} (click para copiar)</span>{comp['name']}</span>
                                {history_indicator}
                            </div>
                        </td>
                        <td>{hybrid_html}</td>
                        <td>{hash_html}</td>
                        <td class="{author_class}" style="color:{author_color_map.get(comp.get('author', ''), 'var(--text-secondary)')};font-weight:600">{comp.get('author', 'N/A')}</td>
                        <td class="date">{comp.get('date', 'N/A')}</td>
                        <td class="message" title="{comp.get('message', '')}">{comp.get('message', 'N/A')[:60]}{"..." if len(comp.get('message', '')) > 60 else ""}</td>
                    </tr>
'''

            # Agregar filas de historial (ocultas por defecto, estilo daily)
            if has_history and len(history) > 1:
                for h_idx, h_commit in enumerate(history[1:]):
                    h_commit_url = f"{BASE_URL}/commit/{h_commit['full_hash']}"
                    h_copy_btn = f'<button class="copy-commit-btn" onclick="copyCommitUrl(\'{h_commit_url}\')" title="Copiar URL del commit">📋</button>'
                    h_msg = h_commit['message'][:60] + ('...' if len(h_commit['message']) > 60 else '')
                    h_author_color = author_color_map.get(h_commit['author'], 'var(--text-secondary)')
                    html += f'''
                    <tr class="history-detail-row" data-history="{comp_id}" style="display: none;">
                        <td><span style="padding-left:8px;display:inline-flex;align-items:center;gap:6px"><svg viewBox="0 0 24 24" width="14" height="14" style="vertical-align:middle;opacity:0.6"><path fill="currentColor" d="M13.5,8H12V13L16.28,15.54L17,14.33L13.5,12.25V8M13,3A9,9 0 0,0 4,12H1L4.96,16.03L9,12H6A7,7 0 0,1 13,5A7,7 0 0,1 20,12A7,7 0 0,1 13,19C11.07,19 9.32,18.21 8.06,16.94L6.64,18.36C8.27,20 10.5,21 13,21A9,9 0 0,0 22,12A9,9 0 0,0 13,3Z"/></svg> <span style="font-size:12px;color:var(--text-muted)">Historial de commits</span></span></td>
                        <td></td>
                        <td><div class="commit-cell"><a href="{h_commit_url}" target="_blank" class="commit-hash">{h_commit['short_hash']}</a>{h_copy_btn}</div></td>
                        <td style="color:{h_author_color};font-weight:600;font-size:13px">{h_commit['author']}</td>
                        <td class="date">{h_commit['date']}</td>
                        <td class="message" title="{h_commit['message']}">{h_msg}</td>
                    </tr>
'''
        html += '''
                </tbody>
            </table>
            </div>
            </div>
        </div>
'''

    # Generar sección CORE si hay componentes
    if core_components:
        html += f'''
        <div class="main-section">
            <div class="main-section-header" onclick="toggleMainSection('main-body-core', this)">
                <span class="main-toggle" id="toggle-icon-main-body-core">▼</span>
                <div class="main-section-icon icon-core">SF</div>
                <div>
                    <div class="main-section-name">SALESFORCE CORE</div>
                    <div class="main-section-subtitle">Componentes nativos de Salesforce (Apex, Objects, Flows, etc.)</div>
                </div>
                <span class="main-section-count">{core_count} componente{"s" if core_count > 1 else ""}</span>
                {core_alert_html}
            </div>
            <div class="main-section-body" id="main-body-core">
'''
        for category in sorted(core_components.keys()):
            generate_category_section(category, core_components[category])

        html += '''
            </div>
        </div>
'''

    # Generar sección VLOCITY si hay componentes
    if vlocity_components:
        html += f'''
        <div class="main-section">
            <div class="main-section-header" onclick="toggleMainSection('main-body-vlocity', this)">
                <span class="main-toggle" id="toggle-icon-main-body-vlocity">▼</span>
                <div class="main-section-icon icon-vlocity-main">VL</div>
                <div>
                    <div class="main-section-name">OMNISTUDIO / VLOCITY</div>
                    <div class="main-section-subtitle">DataRaptors, Integration Procedures, OmniScripts, FlexCards</div>
                </div>
                <span class="main-section-count">{vlocity_count} componente{"s" if vlocity_count > 1 else ""}</span>
                {vlocity_alert_html}
            </div>
            <div class="main-section-body" id="main-body-vlocity">
'''
        for category in sorted(vlocity_components.keys()):
            generate_category_section(category, vlocity_components[category])

        html += '''
            </div>
        </div>
'''

    html += f'''
        <div class="footer">
            <button class="delete-btn" onclick="deleteReport()">🗑️ Delete</button>
            <div class="footer-text">
                <p>Generado el: {timestamp} | Verificación de componentes Manifest vs → {compare_branch_clean.upper()}</p>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        const reportFilePath = '{output_file}';

        function toggleTheme() {{
            const html = document.documentElement;
            const btn = document.querySelector('.theme-toggle');
            if (html.getAttribute('data-theme') === 'light') {{
                html.removeAttribute('data-theme');
                btn.textContent = '🌙 Modo oscuro';
                localStorage.setItem('theme', 'dark');
            }} else {{
                html.setAttribute('data-theme', 'light');
                btn.textContent = '☀️ Modo claro';
                localStorage.setItem('theme', 'light');
            }}
        }}

        function toggleAllSections() {{
            const bodies = document.querySelectorAll('.section-body');
            const allExpanded = [...bodies].every(b => !b.classList.contains('collapsed'));
            bodies.forEach(body => {{
                body.classList.toggle('collapsed', allExpanded);
                const section = body.closest('.section');
                if (section) {{
                    const icon = section.querySelector('.section-toggle');
                    if (icon) {{
                        icon.textContent = allExpanded ? '▶' : '▼';
                        icon.classList.toggle('collapsed', allExpanded);
                    }}
                }}
            }});
            const btn = document.querySelector('.toggle-all-btn');
            if (btn) btn.textContent = allExpanded ? '▶ Expandir todos' : '▼ Colapsar todos';
        }}

        function filterTable(query) {{
            query = query.toLowerCase();
            const rows = document.querySelectorAll('tbody tr.main-row');
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                const isVisible = text.includes(query);
                row.style.display = isVisible ? '' : 'none';

                // Ocultar tambien las filas de historial si la fila principal esta oculta
                const compId = row.getAttribute('data-component-id');
                const historyRow = document.getElementById('history-' + compId);
                if (historyRow && !isVisible) {{
                    historyRow.style.display = 'none';
                }}
            }});
        }}

        function copyComponentName(event, name) {{
            event.stopPropagation();
            navigator.clipboard.writeText(name).then(() => {{
                showToast('Copiado: ' + name);
            }});
        }}

        function toggleMainSection(bodyId, headerEl) {{
            const body = document.getElementById(bodyId);
            const icon = document.getElementById('toggle-icon-' + bodyId);
            if (!body) return;
            const isCollapsed = body.classList.toggle('collapsed');
            if (icon) {{
                icon.textContent = isCollapsed ? '▶' : '▼';
                icon.classList.toggle('collapsed', isCollapsed);
            }}
        }}

        function toggleCategory(catId, headerEl) {{
            const body = document.getElementById(catId);
            const icon = document.getElementById('toggle-icon-' + catId);
            if (!body) return;
            const isCollapsed = body.classList.toggle('collapsed');
            if (icon) {{
                icon.textContent = isCollapsed ? '▶' : '▼';
                icon.classList.toggle('collapsed', isCollapsed);
            }}
        }}

        function toggleHistory(compId) {{
            const rows = document.querySelectorAll(`tr[data-history="${{compId}}"]`);
            if (!rows.length) return;
            const isHidden = rows[0].style.display === 'none' || rows[0].style.display === '';
            rows.forEach(r => r.style.display = isHidden ? 'table-row' : 'none');
        }}

        function showToast(message, duration = 3000) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.style.display = 'block';
            setTimeout(() => {{
                toast.style.display = 'none';
            }}, duration);
        }}

        async function copyCommitUrl(commitUrl) {{
            try {{
                await navigator.clipboard.writeText(commitUrl);
                showToast('✓ URL del commit copiada al portapapeles');
            }} catch (err) {{
                // Fallback si falla el clipboard API
                const textArea = document.createElement('textarea');
                textArea.value = commitUrl;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                try {{
                    document.execCommand('copy');
                    showToast('✓ URL del commit copiada al portapapeles');
                }} catch (err2) {{
                    showToast('✗ No se pudo copiar la URL');
                }}
                document.body.removeChild(textArea);
            }}
        }}

        async function deleteReport() {{
            const deleteCommand = `rm "${{reportFilePath}}"`;

            try {{
                // Intentar copiar al portapapeles
                await navigator.clipboard.writeText(deleteCommand);
                showToast('✓ Comando copiado al portapapeles. Pégalo en la terminal para eliminar el reporte.');

                // Esperar 2 segundos antes de cerrar
                setTimeout(() => {{
                    // Intentar cerrar la ventana
                    window.close();

                    // Si no se pudo cerrar (depende del navegador), mostrar instrucción
                    setTimeout(() => {{
                        if (!window.closed) {{
                            alert('Por favor cierra esta pestaña y pega el comando en la terminal para eliminar el archivo.');
                        }}
                    }}, 100);
                }}, 2000);
            }} catch (err) {{
                // Si falla copiar al portapapeles, mostrar el comando
                const confirmed = confirm(`No se pudo copiar automáticamente.\\n\\nEjecuta este comando en la terminal para eliminar el reporte:\\n\\n${{deleteCommand}}\\n\\n¿Cerrar esta ventana?`);
                if (confirmed) {{
                    window.close();
                }}
            }}
        }}
    </script>
</body>
</html>
'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return True

def generate_html_daily_report(prs_data, report_date, target_branch, output_file):
    """Genera HTML agrupado por PR para el reporte diario de aprobaciones"""
    is_date_range = ' al ' in report_date
    hybrid_names = load_hybrid_set()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_prs = len(prs_data)
    total_components = sum(pr['total_components'] for pr in prs_data)

    # Paleta de colores para autores (distinguibles entre si)
    AUTHOR_COLORS = [
        '#5BA4D9',  # azul cielo
        '#E07070',  # rojo suave
        '#6DC96D',  # verde
        '#C49BDE',  # lavanda
        '#D4A85C',  # dorado
        '#4ECDC4',  # turquesa
        '#FF8A80',  # salmon
        '#82B1FF',  # azul claro
        '#B9F6CA',  # verde menta
        '#FFD180',  # naranja claro
    ]
    # ════════════════════════════════════════════════════════════
    # AUTORES VIGILADOS — Consulta dinámica por dominio de email
    # Si un PR es de otra persona pero toca componentes con commits
    # de estos autores, se muestra alerta. Dominios configurables
    # en get_watched_authors() → domains=['@nespon.com', '@cloudblue.us']
    # ════════════════════════════════════════════════════════════
    watched_set = get_watched_authors()

    # Recolectar todos los autores unicos y asignar color
    unique_authors = set()
    for pr_data in prs_data:
        unique_authors.add(pr_data['author'])
        for cat, comps in pr_data['components_by_category'].items():
            for c in comps:
                for h in c.get('history', []):
                    unique_authors.add(h.get('author', ''))
    author_color_map = {}
    for idx, author in enumerate(sorted(unique_authors)):
        author_color_map[author] = AUTHOR_COLORS[idx % len(AUTHOR_COLORS)]

    # Calcular resumen ejecutivo
    all_authors = set()
    all_target_branches = set()
    total_core = 0
    total_vlocity = 0
    total_hybrid = 0
    for pr_data in prs_data:
        all_authors.add(pr_data['author'])
        all_target_branches.add(pr_data['target_branch'])
        for cat, comps in pr_data['components_by_category'].items():
            is_vloc = cat in {'IntegrationProcedure', 'DataRaptor', 'OmniScript', 'FlexCard',
                              'VlocityUITemplate', 'AttributeCategory', 'Product2',
                              'CalculationMatrix', 'CalculationProcedure', 'Vlocity-Other'}
            if is_vloc:
                total_vlocity += len(comps)
            else:
                total_core += len(comps)
            for c in comps:
                if c['name'] in hybrid_names:
                    total_hybrid += 1

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Pull Requests Aprobados | {report_date}</title>
    <style>
        :root {{
            --bg-primary: #1E2A4A;
            --bg-secondary: #0D0D1A;
            --bg-card: rgba(43,58,103,0.25);
            --bg-card-hover: rgba(43,58,103,0.40);
            --bg-table-header: rgba(0,0,0,0.30);
            --accent: #C4884D;
            --accent-soft: rgba(196,136,77,0.15);
            --accent-border: rgba(196,136,77,0.3);
            --accent-secondary: #CC3333;
            --text-primary: #F5E6D8;
            --text-secondary: #C4A882;
            --text-muted: #7A8A99;
            --border: rgba(255,255,255,0.08);
            --border-accent: rgba(196,136,77,0.2);
            --success: #4CAF50;
            --danger: #CC3333;
            --core-color: #6A8FD4;
            --vlocity-color: #9B6FC0;
            --hybrid-color: #C4884D;
            --commit-color: #F5D0B0;
            --commit-bg: rgba(245,208,176,0.12);
        }}
        [data-theme="light"] {{
            --bg-primary: #FFFAF5;
            --bg-secondary: #FFF5EB;
            --bg-card: rgba(30,42,74,0.04);
            --bg-card-hover: rgba(30,42,74,0.08);
            --bg-table-header: rgba(30,42,74,0.06);
            --accent: #1E2A4A;
            --accent-soft: rgba(30,42,74,0.08);
            --accent-border: rgba(30,42,74,0.2);
            --accent-secondary: #C4884D;
            --text-primary: #0D0D1A;
            --text-secondary: #3D4F6A;
            --text-muted: #8A9AB0;
            --border: rgba(0,0,0,0.08);
            --border-accent: rgba(30,42,74,0.15);
            --success: #388E3C;
            --danger: #CC3333;
            --core-color: #2B3A67;
            --vlocity-color: #4A3F8A;
            --hybrid-color: #D46A15;
            --commit-color: #B85C10;
            --commit-bg: rgba(184,92,16,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-secondary);
            min-height: 100vh; padding: 15px; color: var(--text-primary);
            transition: background 0.3s ease, color 0.3s ease;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: var(--bg-primary);
            border-radius: 12px; padding: 12px 20px; margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15); border: 1px solid var(--border);
            display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        }}
        .header-logo {{
            width: 36px; height: 36px; border-radius: 8px;
            background: var(--accent); display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; box-shadow: 0 2px 8px rgba(196,136,77,0.3);
        }}
        .header-logo svg {{ width: 22px; height: 22px; color: #0D0D1A; }}
        [data-theme="light"] .header-logo svg {{ color: #8A9AB0; }}
        .header-info {{ flex: 1; }}
        .header h1 {{ font-size: 16px; margin-bottom: 2px; color: var(--accent); }}
        .header .subtitle {{ color: var(--text-muted); font-size: 12px; }}
        .theme-toggle {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 8px 14px; border-radius: 8px; cursor: pointer;
            font-size: 13px; font-weight: 600; transition: all 0.2s ease; flex-shrink: 0;
        }}
        .theme-toggle:hover {{ background: var(--accent-border); }}
        .summary-bar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
        .summary-card {{
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 130px;
            transition: all 0.2s ease;
        }}
        .summary-card:hover {{ border-color: var(--accent-border); background: var(--bg-card-hover); }}
        .summary-card label {{ font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.2px; display: block; }}
        .summary-card value {{ display: block; font-size: 24px; color: var(--accent); font-weight: 700; margin-top: 4px; }}
        .summary-card .sub-value {{ font-size: 11px; color: var(--text-secondary); margin-top: 2px; }}
        .search-box {{
            width: 100%; padding: 10px 15px; border-radius: 8px;
            border: 1px solid var(--border); background: var(--bg-card);
            color: var(--text-primary); font-size: 13px; margin-bottom: 20px;
            transition: border-color 0.2s ease;
        }}
        .search-box::placeholder {{ color: var(--text-muted); }}
        .search-box:focus {{ outline: none; border-color: var(--accent); }}
        .pr-section {{
            background: var(--bg-card); border-radius: 12px; margin-bottom: 20px;
            overflow: hidden; border: 1px solid var(--border-accent);
            transition: all 0.2s ease;
        }}
        .pr-section:hover {{ border-color: var(--accent-border); }}
        .pr-section.pr-expanded {{ border: 1.5px solid var(--accent); border-radius: 12px; box-shadow: 0 0 0 1px var(--accent-border); }}
        .pr-header {{
            background: var(--bg-primary);
            padding: 16px 20px; border-bottom: 1px solid var(--border-accent);
            cursor: pointer; user-select: none; transition: background 0.2s ease;
        }}
        .pr-header:hover {{ background: var(--bg-card-hover); }}
        .pr-body {{ transition: max-height 0.3s ease; overflow: hidden; }}
        .pr-body.collapsed {{ display: none; }}
        .pr-toggle {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
            background: var(--accent-soft); color: var(--accent); font-size: 12px;
            transition: transform 0.3s ease;
        }}
        .pr-toggle.collapsed {{ transform: rotate(-90deg); }}
        .toggle-all-btn {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 6px 14px; border-radius: 8px; cursor: pointer;
            font-size: 12px; font-weight: 600; transition: all 0.2s ease;
        }}
        .toggle-all-btn:hover {{ background: var(--accent-border); }}
        .pr-title-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }}
        .pr-id-badge {{
            background: rgba(123,104,238,0.25); color: #9B8FCC;
            padding: 5px 14px; border-radius: 6px; font-weight: 700; font-size: 14px;
            text-decoration: none; flex-shrink: 0;
        }}
        .pr-id-badge:hover {{ opacity: 0.85; }}
        .pr-title {{ font-size: 16px; font-weight: 600; color: var(--text-primary); flex: 1; }}
        .pr-count-badge {{
            background: var(--accent-soft); color: var(--accent);
            border: 1px solid var(--accent-border); padding: 4px 12px;
            border-radius: 16px; font-size: 12px; font-weight: 600; flex-shrink: 0;
        }}
        .pr-meta {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .pr-meta-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; }}
        .pr-meta-label {{ color: var(--text-muted); }}
        .pr-meta-value {{ color: var(--text-secondary); }}
        .branch-arrow {{ color: var(--accent); font-weight: bold; margin: 0 4px; }}
        .pr-date {{ color: var(--accent); }}
        .merge-commit-link {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--commit-color); background: var(--commit-bg);
            padding: 3px 8px; border-radius: 4px; text-decoration: none;
        }}
        .merge-commit-link:hover {{ opacity: 0.8; }}
        .type-section {{
            background: var(--bg-card); margin: 8px 0;
            border-radius: 8px; overflow: hidden; border: 1px solid var(--border);
        }}
        .type-header {{
            display: flex; align-items: center; padding: 10px 14px;
            background: var(--bg-table-header);
            border-bottom: 1px solid var(--border);
            cursor: pointer; user-select: none; transition: background 0.2s ease;
        }}
        .type-header:hover {{ background: var(--bg-card-hover); }}
        .type-body {{ transition: max-height 0.3s ease; overflow: hidden; }}
        .type-body.collapsed {{ display: none; }}
        .type-toggle {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 18px; height: 18px; flex-shrink: 0; color: var(--accent);
            font-size: 10px; margin-right: 6px; transition: transform 0.3s ease;
        }}
        .type-toggle.collapsed {{ transform: rotate(-90deg); }}
        .section-icon {{
            width: 28px; height: 28px; border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; margin-right: 10px; font-size: 11px;
        }}
        .icon-apex {{ background: linear-gradient(135deg, #CC3333, #E85050); color: white; }}
        .icon-metadata {{ background: linear-gradient(135deg, #4A3F8A, #6A5FCF); color: white; }}
        .icon-object {{ background: linear-gradient(135deg, #1E2A4A, #3D5A8A); color: white; }}
        .icon-flow {{ background: linear-gradient(135deg, #2E7D32, #4CAF50); color: white; }}
        .icon-lwc {{ background: linear-gradient(135deg, #2B3A67, #6A8FD4); color: white; }}
        .icon-aura {{ background: linear-gradient(135deg, #CC3333, #C4884D); color: white; }}
        .icon-layout {{ background: linear-gradient(135deg, #D46A15, #C4884D); color: white; }}
        .icon-perm {{ background: linear-gradient(135deg, #00695C, #26A69A); color: white; }}
        .icon-vlocity {{ background: linear-gradient(135deg, #4A3F8A, #9B6FC0); color: white; }}
        .icon-other {{ background: linear-gradient(135deg, #546E7A, #78909C); color: white; }}
        .type-title {{ font-size: 13px; color: var(--text-primary); font-weight: 600; }}
        .type-count {{
            margin-left: 8px; padding: 2px 8px; background: var(--accent-soft);
            border-radius: 12px; font-size: 10px; color: var(--accent);
        }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        th {{
            text-align: left; padding: 10px 15px; background: var(--bg-table-header);
            color: var(--text-muted); font-size: 10px; text-transform: uppercase;
            letter-spacing: 1px; font-weight: 600;
        }}
        th:nth-child(1) {{ width: 26%; }}
        th:nth-child(2) {{ width: 7%; }}
        th:nth-child(3) {{ width: 13%; }}
        th:nth-child(4) {{ width: 16%; }}
        th:nth-child(5) {{ width: 14%; white-space: nowrap; }}
        th:nth-child(6) {{ width: 24%; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid var(--border); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; }}
        tr:hover {{ background: var(--bg-card-hover); }}
        .comp-cell {{ display: flex; align-items: center; gap: 8px; }}
        .status-icon {{
            width: 10px; height: 2px; border-radius: 1px;
            background: #8A9AB0; flex-shrink: 0;
        }}
        .status-icon svg {{ display: none; }}
        .comp-name {{ color: var(--text-primary); font-weight: 500; font-size: 13px; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }}
        .comp-name:hover {{ color: var(--accent); }}
        .commit-cell {{ display: flex; align-items: center; gap: 6px; }}
        .commit-hash {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--commit-color); background: var(--commit-bg);
            padding: 4px 10px; border-radius: 6px; text-decoration: none; transition: all 0.2s ease;
        }}
        .commit-hash:hover {{ opacity: 0.8; }}
        .copy-btn {{
            background: var(--accent-soft); border: 1px solid var(--accent-border);
            color: var(--accent); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;
        }}
        .copy-btn:hover {{ background: var(--accent-border); }}
        .col-author {{ color: var(--text-secondary); font-size: 13px; }}
        .col-date {{ color: var(--text-muted); font-size: 13px; }}
        .col-message {{ color: var(--text-secondary); font-size: 13px; }}
        .history-detail-row td {{ background: var(--bg-table-header); font-size: 12px; opacity: 0.8; }}
        .history-indent {{ color: var(--text-muted); font-size: 14px; padding-left: 20px; }}
        .watch-alert-badge {{
            display: inline-flex; align-items: center; gap: 4px;
            background: rgba(232,122,29,0.15); color: #E8A040;
            border: 1px solid rgba(232,122,29,0.3); padding: 3px 10px;
            border-radius: 6px; font-size: 11px; font-weight: 600;
            margin-left: 8px; white-space: nowrap; cursor: default;
        }}
        .shared-badge {{
            display: inline-flex; align-items: center; gap: 3px;
            background: rgba(204,51,51,0.15); color: #E07070;
            border: 1px solid rgba(204,51,51,0.3); padding: 1px 7px;
            border-radius: 4px; font-size: 10px; font-weight: 600;
            margin-left: 6px; white-space: nowrap;
        }}
        .history-badge {{
            display: inline-flex; align-items: center; justify-content: center;
            background: #5A6785; color: #D0D8E8;
            width: 20px; height: 20px; border-radius: 50%; font-size: 10px;
            font-weight: bold; flex-shrink: 0; margin-left: 6px;
        }}
        .hybrid-badge {{
            font-size: 10px; color: var(--hybrid-color); background: rgba(196,136,77,0.15);
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
            border: 1px solid rgba(196,136,77,0.3);
        }}
        .hybrid-possible-badge {{
            font-size: 10px; color: #E8A040; background: rgba(232,160,64,0.12);
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
            border: 1px solid rgba(232,160,64,0.25);
        }}
        .no-components {{
            padding: 20px; text-align: center; color: var(--text-muted);
            font-style: italic; font-size: 13px;
        }}
        .daily-main-section {{ margin: 8px; }}
        .daily-main-header {{
            background: var(--bg-primary);
            border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
            border: 1px solid var(--border-accent);
            cursor: pointer; user-select: none; transition: background 0.2s ease;
            display: flex; align-items: center; gap: 12px;
        }}
        .daily-main-header:hover {{ background: var(--bg-card-hover); }}
        .daily-main-body {{ transition: max-height 0.3s ease; overflow: hidden; }}
        .daily-main-body.collapsed {{ display: none; }}
        .daily-main-toggle {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
            background: var(--accent-soft); color: var(--accent); font-size: 12px;
            transition: transform 0.3s ease;
        }}
        .daily-main-toggle.collapsed {{ transform: rotate(-90deg); }}
        .daily-main-icon {{
            width: 34px; height: 34px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 12px; flex-shrink: 0; letter-spacing: 0.5px;
        }}
        .daily-icon-core {{
            background: #5BA4D9; color: white;
        }}
        .daily-icon-vlocity {{
            background: #5BA4D9; color: white;
        }}
        .daily-main-name {{ font-size: 12px; font-weight: 700; color: var(--accent); }}
        .daily-main-subtitle {{ color: var(--text-muted); font-size: 11px; }}
        .daily-main-count {{
            margin-left: auto; padding: 3px 10px;
            background: var(--accent-soft); border-radius: 12px;
            font-size: 11px; color: var(--accent); font-weight: 600;
        }}
        .footer {{
            display: flex; flex-direction: column; align-items: flex-end;
            padding: 20px; color: var(--text-muted); font-size: 11px; gap: 15px;
        }}
        .footer-text {{ width: 100%; text-align: center; }}
        .delete-btn {{
            background: linear-gradient(135deg, #EF5350, #D32F2F); color: white;
            border: none; padding: 10px 20px; border-radius: 8px; font-size: 12px;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
        }}
        .delete-btn:hover {{ background: linear-gradient(135deg, #D32F2F, #B71C1C); }}
        .toast {{
            position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: var(--accent); color: var(--bg-secondary); padding: 15px 30px;
            border-radius: 8px; font-size: 13px; font-weight: 600;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 10000; display: none;
        }}
        .clickable {{ cursor: pointer; }}
        .clickable:hover .comp-name {{ color: var(--accent); }}
        .tab-bar {{
            display: flex; gap: 4px; margin-bottom: 20px;
            background: var(--bg-card); border-radius: 10px; padding: 4px;
            border: 1px solid var(--border);
        }}
        .tab-btn {{
            flex: 1; padding: 10px 16px; border: 1px solid var(--accent-border); border-radius: 8px;
            background: var(--accent-soft); color: var(--accent); font-size: 13px;
            font-weight: 600; cursor: pointer; transition: all 0.2s ease;
            text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .tab-btn:hover {{ background: var(--accent-border); }}
        .tab-btn.active {{
            background: var(--accent); color: var(--bg-secondary);
        }}
        .tab-btn .tab-count {{
            display: inline-block; margin-left: 6px; padding: 1px 7px;
            border-radius: 10px; font-size: 11px; font-weight: 700;
        }}
        .tab-btn.active .tab-count {{ background: rgba(0,0,0,0.2); color: var(--bg-secondary); }}
        .tab-btn:not(.active) .tab-count {{ background: var(--accent-soft); color: var(--accent); }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .history-row td {{ padding: 0; background: var(--bg-table-header); border-bottom: 1px solid var(--border); }}
        .history-container {{ padding: 16px 20px; }}
        .history-header {{
            display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
            color: var(--accent); font-size: 13px; font-weight: 600;
        }}
        .history-icon {{ flex-shrink: 0; color: var(--accent); }}
        .history-list {{ display: flex; flex-direction: column; gap: 0; }}
        .history-item, .history-item-latest {{
            display: flex; gap: 12px; padding: 8px 0;
        }}
        .history-timeline {{
            display: flex; flex-direction: column; align-items: center;
            width: 20px; flex-shrink: 0; padding-top: 2px;
        }}
        .timeline-dot {{
            width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
            background: var(--accent-soft); border: 2px solid var(--accent-border);
        }}
        .timeline-dot-latest {{
            background: var(--accent); border-color: var(--accent);
            box-shadow: 0 0 8px rgba(196,136,77,0.5);
        }}
        .timeline-line {{
            width: 2px; flex: 1; min-height: 20px;
            background: linear-gradient(180deg, var(--accent-border) 0%, transparent 100%);
            margin-top: 4px;
        }}
        .history-content {{ flex: 1; min-width: 0; padding-bottom: 8px; }}
        .history-top {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }}
        .history-commit-wrapper {{ display: flex; align-items: center; gap: 6px; }}
        .history-commit {{
            font-family: 'Monaco', 'Menlo', monospace; font-size: 12px;
            color: var(--commit-color); background: var(--commit-bg);
            padding: 3px 8px; border-radius: 4px; text-decoration: none;
        }}
        .history-commit:hover {{ opacity: 0.8; }}
        .history-author {{ color: var(--text-secondary); font-size: 12px; }}
        .history-date {{ color: var(--text-muted); font-size: 11px; margin-left: auto; }}
        .history-message {{ color: var(--text-secondary); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-logo">
                <svg viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18L19.18 7 12 10.82 4.82 7 12 4.18zM4 8.72l7 3.5v7.56l-7-3.5V8.72zm16 0v7.56l-7 3.5v-7.56l7-3.5z" fill="currentColor"/></svg>
            </div>
            <div class="header-info">
                <h1>Reporte de Pull Requests Aprobados | {report_date}</h1>
                <p class="subtitle">Componentes impactados por Pull Request completados, historial de autoría y alertas de posible híbrido</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">🌙 Modo oscuro</button>
        </div>

        <div class="summary-bar">
            <div class="summary-card"><label>PRs Aprobados</label><value>{total_prs}</value></div>
            <div class="summary-card"><label>Total Componentes</label><value>{total_components}</value><div class="sub-value">Core: {total_core} | Vlocity: {total_vlocity}</div></div>
            <div class="summary-card"><label>Ramas Destino</label><value>{len(all_target_branches)}</value><div class="sub-value">{', '.join(sorted(all_target_branches))}</div></div>
        </div>

        <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center;">
            <input type="text" class="search-box" placeholder="Buscar por componente, PR o autor..." onkeyup="filterContent(this.value)" style="margin-bottom: 0; flex: 1;">
            <button class="toggle-all-btn" onclick="toggleAllPRs()">▶ Expandir todos</button>
        </div>
'''

    # Agrupar PRs por rama destino
    from collections import OrderedDict
    prs_by_branch = OrderedDict()
    for pr_data in prs_data:
        branch = pr_data['target_branch']
        if branch not in prs_by_branch:
            prs_by_branch[branch] = []
        prs_by_branch[branch].append(pr_data)

    # Detectar componentes compartidos entre PRs (por rama)
    shared_components = {}  # {branch: {comp_name: [pr_id1, pr_id2, ...]}}
    for branch, branch_prs in prs_by_branch.items():
        comp_map = {}
        for pr_data in branch_prs:
            for cat, comps in pr_data['components_by_category'].items():
                for c in comps:
                    name = c['name']
                    if name not in comp_map:
                        comp_map[name] = []
                    comp_map[name].append(pr_data['pr_id'])
        shared_components[branch] = {name: prs for name, prs in comp_map.items() if len(prs) > 1}

    # Generar tabs si hay mas de una rama
    branch_list = list(prs_by_branch.keys())
    if len(branch_list) > 1:
        html += '        <div class="tab-bar">\n'
        for idx, branch in enumerate(branch_list):
            active = ' active' if idx == 0 else ''
            count = len(prs_by_branch[branch])
            html += f'            <button class="tab-btn{active}" onclick="switchTab(\'{branch}\')" data-tab="{branch}">{branch} <span class="tab-count">{count}</span></button>\n'
        html += '        </div>\n'

    for branch_idx, (branch, branch_prs) in enumerate(prs_by_branch.items()):
        active_panel = ' active' if branch_idx == 0 else ''
        if len(branch_list) > 1:
            html += f'        <div class="tab-panel{active_panel}" data-tab-panel="{branch}">\n'

        for pr_data in branch_prs:
            pr_id = pr_data['pr_id']
            pr_url = f"{BASE_URL}/pullrequest/{pr_id}"
            components_by_category = pr_data['components_by_category']

            # Detectar si el PR toca componentes con commits de autores vigilados
            pr_author_is_watched = pr_data['author'].lower() in watched_set
            watched_hits = {}  # {author_name: [comp_name, ...]}
            if not pr_author_is_watched:
                for cat, comps in components_by_category.items():
                    for comp in comps:
                        for h in comp.get('history', []):
                            h_author = h.get('author', '')
                            if h_author.lower() in watched_set:
                                watched_hits.setdefault(h_author, set()).add(comp['name'])
            # Generar HTML de alerta
            watch_alert_html = ''
            if watched_hits:
                alert_details = []
                for wa, wa_comps in watched_hits.items():
                    alert_details.append(f"{wa} ({len(wa_comps)} comp.)")
                alert_tooltip = '&#10;'.join(alert_details)
                watch_alert_html = f'<span class="watch-alert-badge" title="{alert_tooltip}">⚠ posible híbrido</span>'

            html += f'''
        <div class="pr-section" data-searchtext="{pr_data['title'].lower()} {pr_data['author'].lower()} pr{pr_id}">
            <div class="pr-header" onclick="togglePR('pr-body-{pr_id}', this)">
                <div class="pr-title-row">
                    <span class="pr-toggle collapsed" id="toggle-icon-pr-body-{pr_id}">▶</span>
                    <a href="{pr_url}" target="_blank" class="pr-id-badge" onclick="event.stopPropagation()">PR #{pr_id}</a>
                    <span class="pr-title">{pr_data['title']}</span>
                    <span class="pr-count-badge">{pr_data['total_components']} componente{"s" if pr_data['total_components'] > 1 else ""}</span>
                    {watch_alert_html}
                </div>
                <div class="pr-meta">
                    <div class="pr-meta-item">
                        <span class="pr-meta-label">Rama:</span>
                        <span class="pr-meta-value">{pr_data['source_branch']}<span class="branch-arrow">→</span><span style="color:#ff4444">{pr_data['target_branch']}</span></span>
                    </div>
                    <div class="pr-meta-item">
                        <span class="pr-meta-label">Autor:</span>
                        <span class="pr-meta-value">{pr_data['author']}</span>
                    </div>
                    <div class="pr-meta-item">
                        <span class="pr-meta-label">Creado (YY-MM-DD):</span>
                        <span class="pr-meta-value">{pr_data['creation_date']}</span>
                    </div>
                    <div class="pr-meta-item">
                        <span class="pr-meta-label">Aprobado (YY-MM-DD):</span>
                        <span class="pr-meta-value">{pr_data['closed_date']}</span>
                    </div>
                </div>
            </div>
            <div class="pr-body collapsed" id="pr-body-{pr_id}">
'''
            if not components_by_category:
                html += '            <div class="no-components">Sin componentes Salesforce/Vlocity detectados</div>\n'
            else:
                # Separar CORE y VLOCITY
                DAILY_VLOCITY_TYPES = {'IntegrationProcedure', 'DataRaptor', 'OmniScript', 'FlexCard',
                                       'VlocityUITemplate', 'AttributeCategory', 'Product2',
                                       'CalculationMatrix', 'CalculationProcedure', 'Vlocity-Other'}
                def is_vlocity_cat(cat, comps):
                    if cat in DAILY_VLOCITY_TYPES:
                        return True
                    return any(c.get('path', '').startswith('vlocity/') for c in comps)
                core_cats = {k: v for k, v in components_by_category.items() if not is_vlocity_cat(k, v)}
                vloc_cats = {k: v for k, v in components_by_category.items() if is_vlocity_cat(k, v)}

                core_total = sum(len(v) for v in core_cats.values())
                vloc_total = sum(len(v) for v in vloc_cats.values())

                sections_to_render = []
                if core_cats:
                    sections_to_render.append(('core', 'SALESFORCE CORE', 'Componentes nativos de Salesforce (Apex, Objects, Flows, etc.)', 'daily-icon-core', 'SF', core_cats, core_total))
                if vloc_cats:
                    sections_to_render.append(('vlocity', 'OMNISTUDIO / VLOCITY', 'Componentes de OmniStudio/Vlocity (DataRaptors, IPs, etc.)', 'daily-icon-vlocity', 'VL', vloc_cats, vloc_total))

                for sec_key, sec_name, sec_subtitle, sec_icon_class, sec_emoji, sec_cats, sec_total in sections_to_render:
                    sec_id = f"daily_main_{pr_id}_{sec_key}"
                    html += f'''
            <div class="daily-main-section">
                <div class="daily-main-header" onclick="toggleDailyMain('{sec_id}', this)">
                    <span class="daily-main-toggle" id="toggle-icon-{sec_id}">▼</span>
                    <div class="daily-main-icon {sec_icon_class}">{sec_emoji}</div>
                    <div>
                        <div class="daily-main-name">{sec_name}</div>
                        <div class="daily-main-subtitle">{sec_subtitle}</div>
                    </div>
                    <span class="daily-main-count">{sec_total} componente{"s" if sec_total > 1 else ""}</span>
                </div>
                <div class="daily-main-body" id="{sec_id}">
'''
                    for category in sorted(sec_cats.keys()):
                        comps = sec_cats[category]
                        icon_class = get_icon_class(category)
                        icon_letter = get_icon_letter(category)
                        commit_short = pr_data.get('merge_commit', '')
                        commit_full = pr_data.get('merge_commit_full', '')
                        commit_url = f"{BASE_URL}/commit/{commit_full}" if commit_full else '#'
                        pr_author = pr_data['author']
                        pr_date = pr_data['closed_date']
                        pr_title = pr_data['title']
                        copy_btn = f'<button class="copy-btn" onclick="copyCommitUrl(\'{commit_url}\')" title="Copiar URL">📋</button>' if commit_full else ''

                        type_id = f"type_{pr_id}_{category.replace(' ', '_')}"
                        html += f'''
            <div class="type-section">
                <div class="type-header" onclick="toggleType('{type_id}', this)">
                    <span class="type-toggle" id="toggle-icon-{type_id}">▼</span>
                    <span class="type-title">{category}</span>
                    <span class="type-count">{len(comps)}</span>
                </div>
                <div class="type-body" id="{type_id}">
                <table>
                    <thead>
                        <tr>
                            <th>Componente</th>
                            <th>Híbrido</th>
                            <th>Commit</th>
                            <th>Autor</th>
                            <th>Aprobado (YY-MM-DD)</th>
                            <th>Mensaje</th>
                        </tr>
                    </thead>
                    <tbody>
'''
                        for c_idx, comp in enumerate(comps):
                            is_hybrid = comp['name'] in hybrid_names
                            # Detectar posible híbrido: autor del PR no es vigilado pero el componente tiene commits de vigilados
                            is_possible_hybrid = False
                            if not pr_author_is_watched:
                                for h in comp.get('history', []):
                                    if h.get('author', '').lower() in watched_set:
                                        is_possible_hybrid = True
                                        break
                            if is_hybrid:
                                hybrid_html = '<span class="hybrid-badge">SI</span>'
                            elif is_possible_hybrid:
                                hybrid_html = '<span class="hybrid-possible-badge">posible</span>'
                            else:
                                hybrid_html = ''
                            hash_html = f'<div class="commit-cell"><a href="{commit_url}" target="_blank" class="commit-hash">{commit_short}</a>{copy_btn}</div>' if commit_short else '<span style="color:#5a6785">—</span>'
                            msg_truncated = pr_title[:60] + ('...' if len(pr_title) > 60 else '')
                            history = comp.get('history', [])
                            count = len(history)
                            comp_id = f"daily_{pr_id}_{category}_{c_idx}"
                            has_history = count > 1
                            clickable_class = 'clickable' if has_history else ''
                            onclick_attr = f'onclick="toggleHistory(\'{comp_id}\')"' if has_history else ''
                            count_badge = f'<span class="history-badge" title="Click para ver {count} commits">{count}</span>' if has_history else ''
                            branch_shared = shared_components.get(branch, {})
                            shared_prs = branch_shared.get(comp['name'], [])
                            other_prs = [p for p in shared_prs if p != pr_id]
                            shared_badge = f'<span class="shared-badge" title="Compartido con PR #{", #".join(str(p) for p in other_prs)}">⚠ {len(shared_prs)} PRs</span>' if other_prs else ''
                            html += f'''
                        <tr class="main-row" data-component-id="{comp_id}">
                            <td><div class="comp-cell {clickable_class}" {onclick_attr}><span class="comp-name" onclick="copyText(&#39;{comp['name']}&#39;);event.stopPropagation()" title="{comp['name']} (click para copiar)">{comp['name']}</span>{count_badge}{shared_badge}</div></td>
                            <td>{hybrid_html}</td>
                            <td>{hash_html}</td>
                            <td class="col-author" style="color:{author_color_map.get(pr_author, 'var(--text-secondary)')};font-weight:600">{pr_author}</td>
                            <td class="col-date">{pr_date}</td>
                            <td class="col-message" title="{pr_title}">{msg_truncated}</td>
                        </tr>
'''
                            if has_history:
                                for h_idx, h_commit in enumerate(history[1:]):
                                    h_url = f"{BASE_URL}/commit/{h_commit['full_hash']}"
                                    h_copy = f'<button class="copy-btn" onclick="copyCommitUrl(\'{h_url}\')" title="Copiar URL">📋</button>'
                                    h_msg = h_commit['message'][:60] + ('...' if len(h_commit['message']) > 60 else '')
                                    h_author_color = author_color_map.get(h_commit['author'], 'var(--text-secondary)')
                                    html += f'''
                        <tr class="history-detail-row" data-history="{comp_id}" style="display: none;">
                            <td><span class="history-indent"><svg viewBox="0 0 24 24" width="14" height="14" style="vertical-align:middle;opacity:0.6"><path fill="currentColor" d="M13.5,8H12V13L16.28,15.54L17,14.33L13.5,12.25V8M13,3A9,9 0 0,0 4,12H1L4.96,16.03L9,12H6A7,7 0 0,1 13,5A7,7 0 0,1 20,12A7,7 0 0,1 13,19C11.07,19 9.32,18.21 8.06,16.94L6.64,18.36C8.27,20 10.5,21 13,21A9,9 0 0,0 22,12A9,9 0 0,0 13,3Z"/></svg> <span style="font-size:11px;color:var(--text-muted)">Historial de commits</span></span></td>
                            <td></td>
                            <td><div class="commit-cell"><a href="{h_url}" target="_blank" class="commit-hash">{h_commit['short_hash']}</a>{h_copy}</div></td>
                            <td class="col-author" style="color:{h_author_color};font-weight:600">{h_commit['author']}</td>
                            <td class="col-date">{h_commit['date']}</td>
                            <td class="col-message" title="{h_commit['message']}">{h_msg}</td>
                        </tr>
'''
                        html += '                    </tbody>\n                </table>\n                </div>\n            </div>\n'

                    html += '                </div>\n            </div>\n'  # close daily-main-body + daily-main-section

            html += '            </div>\n'  # close pr-body
            html += '        </div>\n'  # close pr-section

        if len(branch_list) > 1:
            html += '        </div>\n'  # close tab-panel

    html += f'''
        <div class="footer">
            <button class="delete-btn" onclick="deleteReport()">🗑️ Delete</button>
            <div class="footer-text">
                <p>Generado el: {timestamp} | PRs aprobados el {report_date} → {', '.join(b.upper() for b in branch_list)}</p>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        const reportFilePath = '{output_file}';

        function switchTab(branch) {{
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.getAttribute('data-tab') === branch);
            }});
            document.querySelectorAll('.tab-panel').forEach(panel => {{
                panel.classList.toggle('active', panel.getAttribute('data-tab-panel') === branch);
            }});
        }}

        function getActivePanel() {{
            const active = document.querySelector('.tab-panel.active');
            return active || document;
        }}

        function filterContent(query) {{
            query = query.toLowerCase();
            const scope = getActivePanel();
            scope.querySelectorAll('.pr-section').forEach(section => {{
                const text = section.getAttribute('data-searchtext') + ' ' + section.textContent.toLowerCase();
                section.style.display = text.includes(query) ? '' : 'none';
            }});
        }}

        function copyText(text) {{
            navigator.clipboard.writeText(text).then(() => showToast('Copiado: ' + text));
        }}

        async function copyCommitUrl(url) {{
            try {{
                await navigator.clipboard.writeText(url);
                showToast('✓ URL del commit copiada');
            }} catch(e) {{
                const ta = document.createElement('textarea');
                ta.value = url; ta.style.position = 'fixed'; ta.style.opacity = '0';
                document.body.appendChild(ta); ta.select();
                try {{ document.execCommand('copy'); showToast('✓ URL copiada'); }} catch(e2) {{}}
                document.body.removeChild(ta);
            }}
        }}

        function showToast(message) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.style.display = 'block';
            setTimeout(() => {{ toast.style.display = 'none'; }}, 3000);
        }}

        function toggleHistory(compId) {{
            const rows = document.querySelectorAll(`tr[data-history="${{compId}}"]`);
            if (!rows.length) return;
            const isHidden = rows[0].style.display === 'none' || rows[0].style.display === '';
            rows.forEach(r => r.style.display = isHidden ? 'table-row' : 'none');
        }}

        function toggleType(typeId, headerEl) {{
            const body = document.getElementById(typeId);
            const icon = document.getElementById('toggle-icon-' + typeId);
            if (!body) return;
            const isCollapsed = body.classList.toggle('collapsed');
            if (icon) {{
                icon.textContent = isCollapsed ? '▶' : '▼';
                icon.classList.toggle('collapsed', isCollapsed);
            }}
        }}

        function toggleDailyMain(secId, headerEl) {{
            const body = document.getElementById(secId);
            const icon = document.getElementById('toggle-icon-' + secId);
            if (!body) return;
            const isCollapsed = body.classList.toggle('collapsed');
            if (icon) {{
                icon.textContent = isCollapsed ? '▶' : '▼';
                icon.classList.toggle('collapsed', isCollapsed);
            }}
        }}

        function togglePR(bodyId, headerEl) {{
            const body = document.getElementById(bodyId);
            const icon = document.getElementById('toggle-icon-' + bodyId);
            if (!body) return;
            const willOpen = body.classList.contains('collapsed');
            const prSection = body.closest('.pr-section');
            // Colapsar todos los demas PRs abiertos
            if (willOpen) {{
                const scope = getActivePanel();
                scope.querySelectorAll('.pr-body:not(.collapsed)').forEach(other => {{
                    if (other.id !== bodyId) {{
                        other.classList.add('collapsed');
                        other.closest('.pr-section')?.classList.remove('pr-expanded');
                        const otherIcon = document.getElementById('toggle-icon-' + other.id);
                        if (otherIcon) {{ otherIcon.textContent = '▶'; otherIcon.classList.add('collapsed'); }}
                    }}
                }});
            }}
            body.classList.toggle('collapsed');
            prSection?.classList.toggle('pr-expanded', willOpen);
            if (icon) {{
                icon.textContent = willOpen ? '▼' : '▶';
                icon.classList.toggle('collapsed', !willOpen);
            }}
        }}

        let allCollapsed = true;
        function toggleAllPRs() {{
            allCollapsed = !allCollapsed;
            const scope = getActivePanel();
            scope.querySelectorAll('.pr-body').forEach(body => {{
                if (allCollapsed) {{
                    body.classList.add('collapsed');
                    body.closest('.pr-section')?.classList.remove('pr-expanded');
                }} else {{
                    body.classList.remove('collapsed');
                    body.closest('.pr-section')?.classList.add('pr-expanded');
                }}
            }});
            scope.querySelectorAll('.pr-toggle').forEach(icon => {{
                icon.textContent = allCollapsed ? '▶' : '▼';
                icon.classList.toggle('collapsed', allCollapsed);
            }});
            const btn = document.querySelector('.toggle-all-btn');
            if (btn) btn.textContent = allCollapsed ? '▶ Expandir todos' : '▼ Colapsar todos';
        }}

        function toggleTheme() {{
            const html = document.documentElement;
            const btn = document.querySelector('.theme-toggle');
            if (html.getAttribute('data-theme') === 'light') {{
                html.removeAttribute('data-theme');
                btn.textContent = '🌙 Modo oscuro';
                localStorage.setItem('theme', 'dark');
            }} else {{
                html.setAttribute('data-theme', 'light');
                btn.textContent = '☀️ Modo claro';
                localStorage.setItem('theme', 'light');
            }}
        }}
        // Restaurar tema guardado
        (function() {{
            const saved = localStorage.getItem('theme');
            if (saved === 'light') {{
                document.documentElement.setAttribute('data-theme', 'light');
                const btn = document.querySelector('.theme-toggle');
                if (btn) btn.textContent = '☀️ Modo claro';
            }}
        }})();

        async function deleteReport() {{
            const cmd = `rm "${{reportFilePath}}"`;
            try {{
                await navigator.clipboard.writeText(cmd);
                showToast('✓ Comando copiado. Pégalo en la terminal.');
                setTimeout(() => window.close(), 2000);
            }} catch(e) {{
                alert('Ejecuta en terminal:\\n' + cmd);
                window.close();
            }}
        }}
    </script>
</body>
</html>
'''
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return True


def merge_manifest_xml(base_path, delta_path):
    """
    Merge acumulativo de package.xml: agrega members de delta a base sin duplicar.
    Retorna (tipos_nuevos, members_nuevos) para resumen.
    """
    ns_uri = 'http://soap.sforce.com/2006/04/metadata'
    ns = {'sf': ns_uri}

    if os.path.exists(base_path):
        base_tree = ET.parse(base_path)
        base_root = base_tree.getroot()
    else:
        base_root = ET.fromstring(f'<?xml version="1.0" encoding="UTF-8"?><Package xmlns="{ns_uri}"><version>65.0</version></Package>')

    if not os.path.exists(delta_path):
        print(f"  No se encontro delta: {delta_path}")
        return 0, 0

    delta_tree = ET.parse(delta_path)
    delta_root = delta_tree.getroot()

    # Mapa de tipos existentes en base: {nombre_tipo: set(members)}
    base_types = {}
    base_type_elems = {}

    for types_elem in list(base_root.findall('.//sf:types', ns)) + list(base_root.findall('.//types')):
        name_elem = types_elem.find('sf:name', ns)
        if name_elem is None:
            name_elem = types_elem.find('name')
        if name_elem is None:
            continue
        type_name = name_elem.text
        members_set = set()
        for m in list(types_elem.findall('sf:members', ns)) + list(types_elem.findall('members')):
            if m.text:
                members_set.add(m.text)
        base_types[type_name] = members_set
        base_type_elems[type_name] = types_elem

    tipos_nuevos = 0
    members_nuevos = 0

    for types_elem in list(delta_root.findall('.//sf:types', ns)) + list(delta_root.findall('.//types')):
        name_elem = types_elem.find('sf:name', ns)
        if name_elem is None:
            name_elem = types_elem.find('name')
        if name_elem is None:
            continue
        type_name = name_elem.text

        delta_members = set()
        for m in list(types_elem.findall('sf:members', ns)) + list(types_elem.findall('members')):
            if m.text:
                delta_members.add(m.text)

        if type_name in base_types:
            new_members = delta_members - base_types[type_name]
            if new_members:
                existing_elem = base_type_elems[type_name]
                for member_name in sorted(new_members):
                    member_elem = ET.SubElement(existing_elem, f'{{{ns_uri}}}members' if ns_uri in (existing_elem.tag or '') else 'members')
                    member_elem.text = member_name
                members_nuevos += len(new_members)
                base_types[type_name].update(new_members)
        else:
            tipos_nuevos += 1
            members_nuevos += len(delta_members)
            version_elem = base_root.find('sf:version', ns)
            if version_elem is None:
                version_elem = base_root.find('version')
            idx = list(base_root).index(version_elem) if version_elem is not None else len(list(base_root))

            new_type = ET.Element(f'{{{ns_uri}}}types')
            for member_name in sorted(delta_members):
                m = ET.SubElement(new_type, f'{{{ns_uri}}}members')
                m.text = member_name
            n = ET.SubElement(new_type, f'{{{ns_uri}}}name')
            n.text = type_name
            base_root.insert(idx, new_type)
            base_types[type_name] = delta_members
            base_type_elems[type_name] = new_type

    # Reordenar members alfabéticamente dentro de cada tipo
    for type_name, elem in base_type_elems.items():
        name_elem = elem.find(f'{{{ns_uri}}}name')
        if name_elem is None:
            name_elem = elem.find('name')
        members = []
        for m in list(elem.findall(f'{{{ns_uri}}}members')) + list(elem.findall('members')):
            if m.text:
                members.append(m.text)
            elem.remove(m)
        for member_name in sorted(set(members)):
            m = ET.SubElement(elem, f'{{{ns_uri}}}members')
            m.text = member_name
        if name_elem is not None:
            elem.remove(name_elem)
            elem.append(name_elem)

    # Escribir resultado con formato limpio
    ET.register_namespace('', ns_uri)
    xml_str = ET.tostring(base_root, encoding='unicode', xml_declaration=False)

    import re
    with open(base_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        xml_str = xml_str.replace('><', '>\n<')
        lines = xml_str.split('\n')
        indent = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('</'):
                indent -= 1
            f.write('    ' * indent + stripped + '\n')
            if stripped.startswith('<') and not stripped.startswith('</') and not stripped.endswith('/>') and '</' not in stripped:
                indent += 1

    return tipos_nuevos, members_nuevos


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  # Reporte desde PR:")
        print("  python3 pr_commit_report.py <PR_ID> [rama_comparacion] [--output archivo.html]")
        print("")
        print("  # Reporte desde manifests:")
        print("  python3 pr_commit_report.py --manifest [rama_comparacion] [--output archivo.html]")
        print("")
        print("  # Merge acumulativo de package.xml:")
        print("  python3 pr_commit_report.py --merge-manifest base.xml delta.xml")
        print("")
        print("  # Filtrar archivos de PR contra manifests:")
        print("  python3 pr_commit_report.py --filter-files <rama_origen> < archivos.txt")
        print("")
        print("Ejemplos:")
        print("  python3 pr_commit_report.py 10930 uat")
        print("  python3 pr_commit_report.py 10930 uat --output reporte.html")
        print("  python3 pr_commit_report.py --manifest uat")
        print("  python3 pr_commit_report.py --manifest uat --output reporte_manifest.html")
        print("  python3 pr_commit_report.py --daily-report --date 2026-02-16 --target-branch uat")
        print("  python3 pr_commit_report.py --daily-report --date 2026-02-16 --target-branch uat --output reporte_daily.html")
        print("  python3 pr_commit_report.py --merge-manifest manifest/Salud/package.xml delta.xml")
        sys.exit(1)

    # Detectar modo merge-manifest
    if sys.argv[1] == "--merge-manifest":
        if len(sys.argv) < 4:
            print("Uso: python3 pr_commit_report.py --merge-manifest <base.xml> <delta.xml>")
            sys.exit(1)
        base_xml = sys.argv[2]
        delta_xml = sys.argv[3]
        tipos_nuevos, members_nuevos = merge_manifest_xml(base_xml, delta_xml)
        total_components = parse_package_xml(base_xml)
        print(f"TIPOS_NUEVOS={tipos_nuevos}")
        print(f"MEMBERS_NUEVOS={members_nuevos}")
        print(f"TOTAL_MEMBERS={len(total_components)}")
        sys.exit(0)

    # Detectar modo filter-files
    if sys.argv[1] == "--filter-files":
        if len(sys.argv) < 3:
            print("Uso: python3 pr_commit_report.py --filter-files <rama_origen> < archivos.txt")
            sys.exit(1)
        branch = sys.argv[2]
        project_root = get_project_root()

        if branch == "LOCAL":
            # Leer manifests directamente desde archivos locales
            xml_path = os.path.join(project_root, 'manifest/Salud/package.xml')
            yaml_path = os.path.join(project_root, 'manifest/Salud/package.yaml')

            core_components = parse_package_xml(xml_path)
            vlocity_components = parse_package_yaml(yaml_path)
        else:
            # Leer manifests desde la rama origen usando git show
            import tempfile

            # Leer package.xml de la rama
            xml_content, rc = run_command(f'git show {branch}:manifest/Salud/package.xml')
            core_components = []
            if rc == 0 and xml_content:
                tmp_xml = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
                tmp_xml.write(xml_content)
                tmp_xml.close()
                core_components = parse_package_xml(tmp_xml.name)
                os.unlink(tmp_xml.name)

            # Leer package.yaml de la rama
            yaml_content, rc = run_command(f'git show {branch}:manifest/Salud/package.yaml')
            vlocity_components = []
            if rc == 0 and yaml_content:
                tmp_yaml = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
                tmp_yaml.write(yaml_content)
                tmp_yaml.close()
                vlocity_components = parse_package_yaml(tmp_yaml.name)
                os.unlink(tmp_yaml.name)

        # Construir set de paths esperados para CORE
        core_paths = set()
        for comp_type, comp_name in core_components:
            if comp_type in METADATA_TYPE_PATHS:
                path_template = METADATA_TYPE_PATHS[comp_type]
                if '{object}' in path_template and '.' in comp_name:
                    obj, field = comp_name.split('.', 1)
                    path = path_template.replace('{object}', obj).replace('{field}', field).replace('{name}', field)
                    core_paths.add(path)
                    # Agregar también el -meta.xml si el path no lo tiene
                    if not path.endswith('-meta.xml'):
                        core_paths.add(path + '-meta.xml')
                else:
                    path = path_template.replace('{name}', comp_name)
                    core_paths.add(path)
                    if not path.endswith('-meta.xml') and not path.endswith('/'):
                        core_paths.add(path + '-meta.xml')

        # Construir set de prefijos para Vlocity
        vlocity_prefixes = set()
        for comp_type, comp_name in vlocity_components:
            vlocity_prefixes.add(f'vlocity/{comp_type}/{comp_name}/')

        # Leer archivos del stdin y filtrar
        changed_files = sys.stdin.read().strip().split('\n')
        filtered = []
        skipped = []

        for f in changed_files:
            f = f.strip()
            if not f:
                continue

            matched = False

            # Verificar CORE
            if f.startswith('force-app/'):
                for core_path in core_paths:
                    if core_path.endswith('/'):
                        # Directorio (lwc, aura, objects)
                        if f.startswith(core_path):
                            matched = True
                            break
                    else:
                        if f == core_path:
                            matched = True
                            break

            # Verificar Vlocity
            elif f.startswith('vlocity/'):
                for prefix in vlocity_prefixes:
                    if f.startswith(prefix):
                        matched = True
                        break

            if matched:
                filtered.append(f)
            else:
                skipped.append(f)

        # Output: archivos filtrados (uno por línea)
        for f in filtered:
            print(f)

        # Resumen en stderr para que bash lo capture por separado
        print(f"FILTERED={len(filtered)}", file=sys.stderr)
        print(f"SKIPPED={len(skipped)}", file=sys.stderr)
        if skipped:
            print(f"SKIPPED_FILES={'|'.join(skipped)}", file=sys.stderr)

        sys.exit(0)

    # Detectar modo daily-report
    if sys.argv[1] == "--daily-report":
        report_date = None
        target_branch = "uat"
        output_file = None
        end_date_arg = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--date" and i + 1 < len(sys.argv):
                report_date = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--end-date" and i + 1 < len(sys.argv):
                end_date_arg = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--target-branch" and i + 1 < len(sys.argv):
                target_branch = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        end_date = end_date_arg
        if not report_date:
            print("Error: Se requiere --date YYYY-MM-DD")
            print("Uso: python3 pr_commit_report.py --daily-report --date 2026-02-16 [--end-date 2026-02-20] [--output archivo.html]")
            sys.exit(1)

        # Validar formato fecha inicial
        try:
            datetime.strptime(report_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Formato de fecha invalido '{report_date}'. Use YYYY-MM-DD")
            sys.exit(1)

        # Validar formato fecha final si es rango
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                print(f"Error: Formato de fecha invalido '{end_date}'. Use YYYY-MM-DD")
                sys.exit(1)
            if end_date < report_date:
                print(f"Error: La fecha final ({end_date}) no puede ser anterior a la inicial ({report_date})")
                sys.exit(1)

        date_label = f"{report_date} al {end_date}" if end_date else report_date

        if not output_file:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, f"commit_report_daily_{report_date}_{ts}.html")

        print(f"\n{'='*60}")
        print(f"  PRs Aprobados: {date_label} — todas las ramas")
        print(f"{'='*60}\n")

        print(f"[1/3] Obteniendo PRs aprobados ({date_label})...")
        prs = get_approved_prs_by_date(report_date, end_date_str=end_date)

        if not prs:
            print(f"      No se encontraron PRs aprobados: {date_label}")
            sys.exit(0)

        # Filtrar solo PRs hacia uat o main
        TARGET_BRANCHES = {'refs/heads/uat', 'refs/heads/main'}
        prs = [p for p in prs if p.get('targetRefName', '') in TARGET_BRANCHES]

        if not prs:
            print(f"      No se encontraron PRs hacia uat/main: {date_label}")
            sys.exit(0)

        # Ordenar por PR ID descendente (ultimo al primero)
        prs = sorted(prs, key=lambda p: p.get('pullRequestId', 0), reverse=True)
        print(f"      Encontrados: {len(prs)} PRs hacia uat/main (del mas reciente al mas antiguo)")

        print(f"\n[2/3] Obteniendo componentes por PR...")
        # Fetch ramas target de los PRs para asegurar datos actualizados
        target_branches_to_fetch = set()
        for pr in prs:
            target_branches_to_fetch.add(pr.get('targetRefName', ''))
            target_branches_to_fetch.add(pr.get('sourceRefName', ''))
        target_branches_to_fetch.discard('')
        if target_branches_to_fetch:
            fetch_branches(*target_branches_to_fetch)

        project_root = get_project_root()
        prs_data = []

        for pr in prs:
            pr_id = pr.get('pullRequestId')
            title = pr.get('title', '')
            source_ref = pr.get('sourceRefName', '')
            target_ref = pr.get('targetRefName', '')
            author = pr.get('createdBy', {}).get('displayName', 'N/A')
            closed_date = pr.get('closedDate', '')[:10]
            creation_date = pr.get('creationDate', '')[:10]

            merge_commit = pr.get('lastMergeCommit', {}).get('commitId', '')
            print(f"      PR #{pr_id} [{merge_commit[:8] if merge_commit else 'sin merge commit'}]: {title[:50]}...")

            changed_files = get_pr_changed_files_by_merge_commit(merge_commit)

            components_by_category = {}
            for file_path in changed_files:
                if not file_path.startswith('force-app/') and not file_path.startswith('vlocity/'):
                    continue
                if file_path.endswith('.cls-meta.xml') or file_path.endswith('.trigger-meta.xml'):
                    continue

                category = categorize_component(file_path)
                component_name = get_component_name(file_path)

                if category == 'CustomField':
                    parts = file_path.split('/objects/')
                    if len(parts) > 1:
                        obj_name = parts[1].split('/')[0]
                        component_name = f"{obj_name}.{component_name}"

                if category not in components_by_category:
                    components_by_category[category] = []
                if not any(c['name'] == component_name for c in components_by_category[category]):
                    target_branch_clean = target_ref.replace('refs/heads/', '')
                    history = get_file_commit_history(file_path, target_branch_clean)
                    components_by_category[category].append({
                        'name': component_name,
                        'path': file_path,
                        'commit_count': len(history),
                        'history': history
                    })

            prs_data.append({
                'pr_id': pr_id,
                'title': title,
                'source_branch': source_ref.replace('refs/heads/', ''),
                'target_branch': target_ref.replace('refs/heads/', ''),
                'author': author,
                'closed_date': closed_date,
                'creation_date': creation_date,
                'merge_commit': merge_commit[:8] if merge_commit else '',
                'merge_commit_full': merge_commit,
                'components_by_category': components_by_category,
                'total_components': sum(len(c) for c in components_by_category.values())
            })

        # Excluir PRs sin componentes Salesforce/Vlocity
        prs_data = [p for p in prs_data if p['total_components'] > 0]
        print(f"      PRs con componentes core/vlocity: {len(prs_data)}")

        if not prs_data:
            print(f"      Ninguno de los PRs afecto componentes Salesforce/Vlocity")
            sys.exit(0)

        print(f"\n[3/3] Generando reporte HTML...")
        if generate_html_daily_report(prs_data, date_label, target_branch, output_file):
            print(f"      Archivo generado: {output_file}")
            print(f"\n{'='*60}")
            print(f"  Reporte generado exitosamente!")
            print(f"{'='*60}\n")
            print(f"OUTPUT_FILE={output_file}")
        else:
            print("Error al generar el archivo HTML")
            sys.exit(1)
        sys.exit(0)

    # Detectar modo manifest
    if sys.argv[1] == "--manifest":
        report_type = "manifest"
        pr_id = "manifest"
        compare_branch = "uat"  # Default
        output_file = None
        manifest_xml_path = None
        manifest_yaml_path = None

        # Parsear argumentos para modo manifest
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--output" and i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--manifest-xml" and i + 1 < len(sys.argv):
                manifest_xml_path = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--manifest-yaml" and i + 1 < len(sys.argv):
                manifest_yaml_path = sys.argv[i + 1]
                i += 2
            else:
                compare_branch = sys.argv[i]
                i += 1
    else:
        # Modo PR
        report_type = "pr"
        pr_id = sys.argv[1]
        compare_branch = "uat"  # Default
        output_file = None
        manifest_xml_path = None
        manifest_yaml_path = None

        # Parsear argumentos para modo PR
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--output" and i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 2
            else:
                compare_branch = sys.argv[i]
                i += 1

    # Generar nombre de archivo si no se especifico
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if report_type == 'manifest':
            output_file = os.path.join(script_dir, f"commit_report_manifest_{compare_branch}_{timestamp}.html")
        else:
            output_file = os.path.join(script_dir, f"commit_report_pr_{pr_id}_{compare_branch}_{timestamp}.html")

    print(f"\n{'='*60}")
    if report_type == 'manifest':
        print(f"  Generando reporte de MANIFESTS vs {compare_branch.upper()}")
    else:
        print(f"  Generando reporte para PR #{pr_id} vs {compare_branch.upper()}")
    print(f"{'='*60}\n")

    # Obtener info del PR (solo si es tipo 'pr')
    pr_info = None
    if report_type == 'pr':
        print(f"[1/4] Obteniendo informacion del PR #{pr_id}...")
        pr_info = get_pr_info(pr_id)
        if not pr_info:
            print(f"Error: No se pudo obtener informacion del PR #{pr_id}")
            print("Verifique que el PR existe y que esta autenticado en Azure CLI")
            sys.exit(1)

        print(f"      Titulo: {pr_info['title']}")
        print(f"      Rama origen: {pr_info['sourceBranch'].replace('refs/heads/', '')}")
        print(f"      Rama destino: {pr_info['targetBranch'].replace('refs/heads/', '')}")

    # Obtener archivos cambiados
    not_found_components = []
    if report_type == 'pr':
        print(f"\n[2/4] Obteniendo archivos del PR (source vs target)...")
        # Fetch ramas del PR y de comparacion para asegurar datos actualizados
        fetch_branches(pr_info['sourceBranch'], pr_info['targetBranch'], compare_branch)
        changed_files = get_pr_specific_files(pr_info['sourceBranch'], pr_info['targetBranch'])

        if not changed_files:
            # Fallback: usar merge commit del PR (cuando la rama source fue eliminada)
            merge_commit = pr_info.get('lastMergeCommit', {}).get('commitId', '')
            if merge_commit:
                print(f"      Rama source no disponible, usando merge commit: {merge_commit[:8]}...")
                changed_files = get_pr_changed_files_by_merge_commit(merge_commit)

        if not changed_files:
            print(f"      No se encontraron archivos cambiados")
            sys.exit(0)

        print(f"      Encontrados: {len(changed_files)} archivos")
    else:  # 'manifest'
        print(f"\n[2/4] Leyendo componentes de los manifests...")
        # Fetch rama de comparacion para asegurar datos actualizados
        fetch_branches(compare_branch)

        # Obtener raiz del proyecto
        project_root = get_project_root()

        # Rutas de los manifests (usar paths dinámicos si se proporcionaron, sino Salud por defecto)
        if manifest_xml_path:
            package_xml = os.path.join(project_root, manifest_xml_path)
        else:
            package_xml = os.path.join(project_root, 'manifest/Salud/package.xml')
        if manifest_yaml_path:
            package_yaml = os.path.join(project_root, manifest_yaml_path)
        else:
            package_yaml = os.path.join(project_root, 'manifest/Salud/package.yaml')

        print(f"      Package XML: {package_xml}")
        print(f"      Package YAML: {package_yaml}")

        # Parsear componentes desde manifests
        xml_components = parse_package_xml(package_xml)
        yaml_components = parse_package_yaml(package_yaml)

        print(f"      Componentes CORE: {len(xml_components)}")
        print(f"      Componentes VLOCITY: {len(yaml_components)}")

        # Convertir componentes de manifest a rutas de archivos
        changed_files = []
        manifest_components = []  # Para rastrear (tipo, nombre)

        not_found_components = []  # Componentes que no se encuentran en la rama local

        for component_type, component_name in xml_components + yaml_components:
            file_path = find_component_path(component_type, component_name, project_root)
            if file_path:
                # Hacer la ruta relativa al proyecto
                rel_path = os.path.relpath(file_path, project_root)
                changed_files.append(rel_path)
                manifest_components.append((component_type, component_name, rel_path))
            else:
                print(f"      Advertencia: No se encontro ruta para {component_type}/{component_name}")
                not_found_components.append((component_type, component_name))

        if not changed_files:
            print(f"      No se encontraron componentes en los manifests")
            sys.exit(0)

        print(f"      Total archivos encontrados: {len(changed_files)}")

    # Obtener commits por archivo
    print(f"\n[3/4] Obteniendo informacion de commits...")
    components_by_category = {}

    for file_path in changed_files:
        # Filtrar solo archivos de metadata (CORE y VLOCITY)
        if not file_path.startswith('force-app/') and not file_path.startswith('vlocity/'):
            continue

        # Ignorar archivos -meta.xml de clases (redundantes)
        if file_path.endswith('.cls-meta.xml'):
            continue
        if file_path.endswith('.trigger-meta.xml'):
            continue

        # Buscar el ultimo commit de este archivo EN la rama de comparacion (UAT/MAIN)
        # Para saber quien lo modifico por ultima vez y predecir posibles sobrescrituras
        commit_info = get_file_commit_info_in_branch(file_path, compare_branch)

        # Obtener historial completo (ultimos 10 commits)
        commit_history = get_file_commit_history(file_path, compare_branch)

        category = categorize_component(file_path)
        component_name = get_component_name(file_path)

        # Agregar info del path para campos de objetos
        if category == 'CustomField':
            # Extraer nombre del objeto
            parts = file_path.split('/objects/')
            if len(parts) > 1:
                obj_name = parts[1].split('/')[0]
                component_name = f"{obj_name}.{component_name}"

        if commit_info:
            # Archivo existe en la rama de comparacion
            component_data = {
                'name': component_name,
                'path': file_path,
                'full_hash': commit_info['full_hash'],
                'short_hash': commit_info['short_hash'],
                'author': commit_info['author'],
                'date': commit_info['date'],
                'message': commit_info['message'],
                'is_new': False,
                'history': commit_history  # Agregar historial completo
            }
        else:
            # Archivo NO existe en la rama de comparacion (es nuevo)
            component_data = {
                'name': component_name,
                'path': file_path,
                'full_hash': '',
                'short_hash': 'NUEVO',
                'author': '(No existe en rama)',
                'date': '-',
                'message': f'Componente nuevo - no existe en {compare_branch}',
                'is_new': True,
                'history': []  # Sin historial para componentes nuevos
            }

        if category not in components_by_category:
            components_by_category[category] = []
        components_by_category[category].append(component_data)

    # Agregar componentes del manifest que no se encontraron en la rama local
    # Pero podrían existir en origin/{compare_branch} (subidos por otro equipo)
    if report_type == 'manifest' and not_found_components:
        found_remote = 0
        not_found_anywhere = 0
        for component_type, component_name in not_found_components:
            category = component_type
            # Construir la ruta esperada para buscar en la rama remota
            if component_type in VLOCITY_TYPE_PATHS:
                expected_path = VLOCITY_TYPE_PATHS[component_type].format(name=component_name).rstrip('/')
            elif component_type in METADATA_TYPE_PATHS:
                expected_path = METADATA_TYPE_PATHS[component_type].format(name=component_name)
            else:
                expected_path = None

            # Intentar buscar commit info en la rama de comparación
            commit_info = None
            commit_history = []
            if expected_path:
                commit_info = get_file_commit_info_in_branch(expected_path, compare_branch)
                if commit_info:
                    commit_history = get_file_commit_history(expected_path, compare_branch)

            if commit_info:
                found_remote += 1
                component_data = {
                    'name': component_name,
                    'path': expected_path,
                    'full_hash': commit_info['full_hash'],
                    'short_hash': commit_info['short_hash'],
                    'author': commit_info['author'],
                    'date': commit_info['date'],
                    'message': commit_info['message'],
                    'is_new': False,
                    'not_found': False,
                    'not_local': True,
                    'history': commit_history
                }
            else:
                not_found_anywhere += 1
                component_data = {
                    'name': component_name,
                    'path': f'(manifest: {component_type}/{component_name})',
                    'full_hash': '',
                    'short_hash': 'NO LOCAL',
                    'author': '',
                    'date': '-',
                    'message': f'No se encuentra en la rama local ni en {compare_branch}',
                    'is_new': True,
                    'not_found': True,
                    'history': []
                }

            if category not in components_by_category:
                components_by_category[category] = []
            components_by_category[category].append(component_data)

        print(f"      No encontrados localmente: {len(not_found_components)} (encontrados en {compare_branch}: {found_remote}, no encontrados: {not_found_anywhere})")

    total = sum(len(comps) for comps in components_by_category.values())
    print(f"      Procesados: {total} componentes")

    # Generar HTML
    print(f"\n[4/4] Generando reporte HTML...")
    # Pasar rutas de manifest si aplica
    m_xml = manifest_xml_path if report_type == 'manifest' else None
    m_yaml = manifest_yaml_path if report_type == 'manifest' else None
    if generate_html(pr_info, components_by_category, compare_branch, pr_id, output_file, report_type=report_type, manifest_xml_path=m_xml, manifest_yaml_path=m_yaml):
        print(f"      Archivo generado: {output_file}")
        print(f"\n{'='*60}")
        print(f"  Reporte generado exitosamente!")
        print(f"{'='*60}\n")

        # Retornar la ruta del archivo para el script de shell
        print(f"OUTPUT_FILE={output_file}")
    else:
        print("Error al generar el archivo HTML")
        sys.exit(1)

if __name__ == "__main__":
    main()
