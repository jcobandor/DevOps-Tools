#!/usr/bin/env python3
"""
Auto PR Monitor — Monitoreo automático de PRs en Azure DevOps con MySQL.

Monitorea TODOS los PRs (creados, activos, completados) hacia ramas objetivo.
Detecta componentes híbridos (por lista y por autor externo).
Sube reportes HTML a rama devops-reports y comparte link de descarga en Teams.

Uso manual:
    python3 auto_pr_monitor.py --check          # Ejecutar verificación
    python3 auto_pr_monitor.py --status          # Ver estado del monitor
    python3 auto_pr_monitor.py --db-status       # Ver PRs en base de datos
    python3 auto_pr_monitor.py --cron-log        # Ver historial de ejecuciones del cron
    python3 auto_pr_monitor.py --clear           # Limpiar historial

Diseñado para ejecutarse via cron cada 30 minutos.
"""

import subprocess
import json
import sys
import os
import hashlib
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import mysql.connector
from datetime import datetime, timedelta

# ── Configuración ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
CONFIG_FILE = os.path.join(SCRIPT_DIR, '.pr_monitor_config.json')

# Azure DevOps
AZURE_REPO = "suratech-salesforce-app"
AZURE_ORG = "SuratechDevOpsColombia"
AZURE_PROJECT = "Suratech%20Colombia"
AZURE_PROJECT_CLEAN = "Suratech Colombia"
PR_BASE_URL = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_git/{AZURE_REPO}/pullrequest"
REPORT_BRANCH = "devops-reports"
REPORT_DOWNLOAD_URL = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/git/repositories/{AZURE_REPO}/items?path={{path}}&versionDescriptor.version={REPORT_BRANCH}&versionDescriptor.versionType=branch&download=true"

# MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "devops"
}

# Dominios vigilados (equipo propio)
WATCHED_DOMAINS = ['@nespon.com', '@cloudblue.us']
# Autores adicionales del equipo (no tienen dominio vigilado pero son del equipo)
EXTRA_WATCHED_AUTHORS = ['omar', 'omar marmolejo', 'amanda andrade']

TARGET_BRANCHES = ["uat", "main"]

DEFAULT_CONFIG = {
    "teams_webhook_url": "",
    "target_branches": ["uat", "main"],
    "active": False
}


# ── MySQL ──

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_tracked_pr(pr_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pr_tracking WHERE pr_id = %s", (pr_id,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row


def upsert_pr(pr_data, status, notified_status, html_sent=False, report_path=None, report_url=None, hybrid_count=0, comp_hash=None, comp_count=0):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO pr_tracking (pr_id, title, author, source_branch, target_branch,
                                  status, last_notified_status, html_sent, report_path, report_url,
                                  hybrid_count, component_hash, component_count, notified_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            author = VALUES(author),
            status = VALUES(status),
            last_notified_status = VALUES(last_notified_status),
            html_sent = VALUES(html_sent),
            report_path = COALESCE(VALUES(report_path), report_path),
            report_url = COALESCE(VALUES(report_url), report_url),
            hybrid_count = VALUES(hybrid_count),
            component_hash = VALUES(component_hash),
            component_count = VALUES(component_count),
            notified_at = NOW()
    """, (
        pr_data['id'], pr_data['title'], pr_data['author'],
        pr_data['source_branch'], pr_data['target_branch'],
        status, notified_status, html_sent, report_path, report_url,
        hybrid_count, comp_hash, comp_count
    ))
    db.commit()
    cursor.close()
    db.close()


def update_pr_status(pr_id, status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE pr_tracking SET status = %s WHERE pr_id = %s", (status, pr_id))
    db.commit()
    cursor.close()
    db.close()


def log_cron_execution(prs_found=0, new_prs=0, status_changes=0, notifications_sent=0,
                        duration=0, result='OK', detail=None):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO cron_log (prs_found, new_prs, status_changes, notifications_sent,
                                   duration_seconds, result, detail)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (prs_found, new_prs, status_changes, notifications_sent, duration, result, detail))
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        log(f"Error registrando cron_log: {e}")


def get_all_tracked_prs():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pr_tracking ORDER BY updated_at DESC LIMIT 50")
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows


# ── Config ──

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


# ── Utilidades ──

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = os.path.join(SCRIPT_DIR, '.pr_monitor.log')
    line = f"[{timestamp}] {message}"
    print(line)
    with open(log_file, 'a') as f:
        f.write(line + '\n')


# ── Detección de Híbridos ──

def load_hybrid_set():
    """Carga componentes híbridos desde package_hibridos.xml y package_hibridos.yaml"""
    hybrid_names = set()

    # CORE
    hybrid_xml = os.path.join(SCRIPTS_DIR, 'package_hibridos.xml')
    if os.path.exists(hybrid_xml):
        try:
            tree = ET.parse(hybrid_xml)
            root = tree.getroot()
            ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
            for types_elem in root.findall('.//sf:types', ns) or root.findall('.//types'):
                for member in types_elem.findall('sf:members', ns) or types_elem.findall('members'):
                    if member.text and member.text != '*':
                        hybrid_names.add(member.text)
        except Exception:
            pass

    # Vlocity
    hybrid_yaml = os.path.join(SCRIPTS_DIR, 'package_hibridos.yaml')
    if os.path.exists(hybrid_yaml):
        try:
            with open(hybrid_yaml, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith('- ') and '/' in stripped:
                        comp = stripped[2:].split('#')[0].strip()
                        parts = comp.split('/')
                        if len(parts) >= 2:
                            hybrid_names.add('/'.join(parts[1:]).strip())
        except Exception:
            pass

    return hybrid_names


def get_watched_authors():
    """Obtiene autores del equipo propio desde git log + autores adicionales"""
    watched = set()
    # Agregar autores adicionales configurados manualmente
    for name in EXTRA_WATCHED_AUTHORS:
        watched.add(name.lower())
    try:
        cmd = "git log --all --format='%an|%ae' 2>/dev/null"
        output, code = run_command(cmd)
        if code == 0 and output:
            for line in output.strip().split('\n'):
                if '|' not in line:
                    continue
                name, email = line.split('|', 1)
                name = name.strip().strip("'").lower()
                email = email.strip().strip("'").lower()
                if name and email and any(d in email for d in WATCHED_DOMAINS):
                    watched.add(name)
    except Exception:
        pass
    return watched


def get_component_name(file_path):
    """Extrae nombre del componente de la ruta"""
    basename = os.path.basename(file_path)
    for ext in ['.cls-meta.xml', '.cls', '.md-meta.xml', '.trigger-meta.xml', '.trigger',
                '.flow-meta.xml', '.flexipage-meta.xml', '.field-meta.xml',
                '.permissionset-meta.xml', '.object-meta.xml', '.xml', '.json']:
        if basename.endswith(ext):
            return basename[:-len(ext)]
    return basename


def get_pr_files(pr):
    """Obtiene archivos modificados de un PR con fetch y fallback por merge commit.
    Funciona tanto para PRs activos como completados/mergeados."""
    source = pr['source_branch']
    target = pr['target_branch']

    # Fetch ramas para asegurar datos actualizados
    run_command(f'git fetch origin {source} 2>/dev/null')
    run_command(f'git fetch origin {target} 2>/dev/null')

    # Intentar diff entre ramas
    cmd = f'git diff --name-only origin/{target}...origin/{source} 2>/dev/null'
    output, code = run_command(cmd)
    if code == 0 and output and output.strip():
        return [f for f in output.split('\n') if f.strip()]

    # Fallback: usar merge commit (PR ya mergeado, ramas apuntan al mismo punto)
    pr_id = pr['id']
    mc_cmd = f'az repos pr show --id {pr_id} --query "lastMergeCommit.commitId" -o tsv 2>/dev/null'
    mc_output, mc_code = run_command(mc_cmd)
    if mc_code == 0 and mc_output and mc_output.strip():
        merge_commit = mc_output.strip()
        # Fetch el merge commit
        run_command(f'git fetch origin {merge_commit} 2>/dev/null')
        # diff entre padre del merge y el merge
        diff_cmd = f'git diff --name-only {merge_commit}^1 {merge_commit} 2>/dev/null'
        diff_output, diff_code = run_command(diff_cmd)
        if diff_code == 0 and diff_output and diff_output.strip():
            return [f for f in diff_output.split('\n') if f.strip()]
        # Fallback: git show
        show_cmd = f'git show --name-only --format="" {merge_commit} 2>/dev/null'
        show_output, show_code = run_command(show_cmd)
        if show_code == 0 and show_output and show_output.strip():
            return [f for f in show_output.split('\n') if f.strip()]

    return []


def detect_hybrids(pr, target_branch):
    """Detecta componentes híbridos en un PR.
    Retorna lista de dicts: {name, file, reason, last_author}
    """
    hybrid_set = load_hybrid_set()
    watched = get_watched_authors()
    hybrids = []

    target = target_branch

    # Obtener archivos del PR (con fetch y fallback por merge commit)
    files = get_pr_files(pr)

    for file_path in files:
        if not (file_path.startswith('force-app/') or file_path.startswith('vlocity/')):
            continue

        comp_name = get_component_name(file_path)
        reasons = []

        # Detección 1: En lista de híbridos
        if comp_name in hybrid_set:
            reasons.append("en lista de híbridos")

        # Detección 2: Componente tocado por AMBOS equipos (interno + externo) en rama destino
        cmd_log = f'git log --format="%an" origin/{target} -- "{file_path}" 2>/dev/null'
        author_output, a_code = run_command(cmd_log)
        last_author = ''
        if a_code == 0 and author_output:
            authors = [a.strip().strip('"').lower() for a in author_output.strip().split('\n') if a.strip()]
            last_author = authors[0] if authors else ''
            has_internal = any(a in watched for a in authors)
            has_external = any(a not in watched for a in authors)
            if has_internal and has_external:
                external_authors = sorted(set(a for a in authors if a not in watched))
                reasons.append(f"híbrido: autores externos: {', '.join(external_authors[:3])}")

        if reasons:
            hybrids.append({
                'name': comp_name,
                'file': file_path,
                'reason': ', '.join(reasons),
                'last_author': last_author
            })

    return hybrids


# ── Upload a Azure DevOps ──

def upload_report_to_repo(report_path, pr_id):
    """Sube el HTML a la rama devops-reports via Azure DevOps REST API.
    Usa az CLI para autenticación, compatible con cron (no depende de osxkeychain)."""
    import base64
    import tempfile

    filename = os.path.basename(report_path)
    repo_path = f"/reports/{filename}"

    try:
        # Leer contenido del HTML y codificar en base64
        with open(report_path, 'rb') as f:
            content_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Obtener el último objectId de la rama devops-reports
        ref_cmd = (
            f'az repos ref list --repository {AZURE_REPO} '
            f'--filter heads/{REPORT_BRANCH} -o json 2>/dev/null'
        )
        ref_output, ref_code = run_command(ref_cmd)
        if ref_code != 0 or not ref_output:
            log(f"Error obteniendo ref de {REPORT_BRANCH}")
            return None

        refs = json.loads(ref_output)
        if not refs:
            log(f"Rama {REPORT_BRANCH} no encontrada")
            return None

        old_object_id = refs[0]['objectId']

        # Construir payload del push via API
        push_body = {
            "refUpdates": [{
                "name": f"refs/heads/{REPORT_BRANCH}",
                "oldObjectId": old_object_id
            }],
            "commits": [{
                "comment": f"Auto-report: PR #{pr_id} - {filename}",
                "changes": [{
                    "changeType": "add",
                    "item": {"path": repo_path},
                    "newContent": {
                        "content": content_b64,
                        "contentType": "base64encoded"
                    }
                }]
            }]
        }

        # Escribir body a archivo temporal (evitar problemas con shell escaping)
        tmp_body = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(push_body, tmp_body)
        tmp_body.close()

        # Push via Azure DevOps REST API
        api_url = (
            f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}/_apis/git/repositories/"
            f"{AZURE_REPO}/pushes?api-version=7.0"
        )
        push_cmd = (
            f'az rest --method post --uri "{api_url}" '
            f'--body @{tmp_body.name} '
            f'--resource "499b84ac-1321-427f-aa17-267ca6975798" -o json 2>&1'
        )
        push_output, push_code = run_command(push_cmd)

        # Limpiar archivo temporal
        os.unlink(tmp_body.name)

        if push_code != 0:
            log(f"Error en push API: {push_output[:200]}")
            return None

        download_url = REPORT_DOWNLOAD_URL.format(path=repo_path)
        log(f"Reporte subido: {repo_path}")
        return download_url

    except Exception as e:
        log(f"Error subiendo reporte: {e}")
        return None


# ── Azure DevOps ──

def get_all_prs(target_branches):
    prs_found = []
    seen_ids = set()

    for branch in target_branches:
        for status in ['active', 'completed']:
            top = 50 if status == 'active' else 20
            cmd = (
                f'az repos pr list --status {status} '
                f'--target-branch {branch} --top {top} -o json 2>/dev/null'
            )
            output, code = run_command(cmd)
            if code != 0 or not output:
                continue

            try:
                prs = json.loads(output)
            except Exception:
                continue

            cutoff = datetime.utcnow() - timedelta(hours=2)

            for pr in prs:
                pr_id = pr.get('pullRequestId')
                if pr_id in seen_ids:
                    continue
                seen_ids.add(pr_id)

                pr_status = pr.get('status', '')
                closed_date = pr.get('closedDate', '')

                if status == 'completed' and closed_date:
                    try:
                        closed_dt = datetime.strptime(closed_date[:19], '%Y-%m-%dT%H:%M:%S')
                        if closed_dt < cutoff:
                            continue
                    except Exception:
                        continue

                # Determinar estado de aprobación desde reviewers
                reviewers = pr.get('reviewers', [])
                votes = [r.get('vote', 0) for r in reviewers]
                if any(v == 10 for v in votes):
                    approval = 'Aprobado'
                elif any(v == 5 for v in votes):
                    approval = 'Aprobado con sugerencias'
                elif any(v == -10 for v in votes):
                    approval = 'Rechazado'
                elif any(v == -5 for v in votes):
                    approval = 'Esperando autor'
                else:
                    approval = 'Sin revisión'

                prs_found.append({
                    'id': pr_id,
                    'title': pr.get('title', ''),
                    'author': pr.get('createdBy', {}).get('displayName', ''),
                    'source_branch': pr.get('sourceRefName', '').replace('refs/heads/', ''),
                    'target_branch': pr.get('targetRefName', '').replace('refs/heads/', ''),
                    'status': pr_status,
                    'closed_date': closed_date or '',
                    'approval': approval,
                })

    return prs_found


# ── Reportes y notificaciones ──

def generate_report(pr_id, target_branch):
    report_script = os.path.join(SCRIPTS_DIR, 'pr_commit_report.py')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(SCRIPT_DIR, f'auto_report_pr_{pr_id}_{target_branch}_{timestamp}.html')

    cmd = f'python3 "{report_script}" {pr_id} {target_branch} --output "{output_file}"'
    output, code = run_command(cmd)

    if code == 0 and os.path.exists(output_file):
        return output_file
    return None


def get_pr_components(pr):
    files = sorted(get_pr_files(pr))
    core = [f for f in files if f.startswith('force-app/')]
    vlocity = [f for f in files if f.startswith('vlocity/')]
    return core, vlocity


def get_component_hash(pr):
    """Genera un hash de la lista de archivos del PR para detectar cambios"""
    core, vlocity = get_pr_components(pr)
    all_files = sorted(core + vlocity)
    file_list = '\n'.join(all_files)
    return hashlib.md5(file_list.encode()).hexdigest(), len(all_files)


def send_teams_notification(webhook_url, pr, hybrids=None, report_url=None,
                             is_status_change=False, old_status=None):
    """Envía notificación a Microsoft Teams con alerta de híbridos y link de descarga"""
    pr_url = f"{PR_BASE_URL}/{pr['id']}"
    core, vlocity = get_pr_components(pr)
    total = len(core) + len(vlocity)
    hybrids = hybrids or []

    comp_lines = ""
    all_files = core[:7] + vlocity[:3]
    for f in all_files:
        name = os.path.basename(f)
        comp_lines += f"- {name}\n"
    if total > len(all_files):
        comp_lines += f"- ... y {total - len(all_files)} más\n"

    # Título según contexto
    if is_status_change:
        title_text = f"PR #{pr['id']} cambió de {old_status.upper()} a {pr['status'].upper()}"
    else:
        title_text = f"Nuevo PR #{pr['id']} hacia {pr['target_branch'].upper()}"

    status_emoji = {"active": "🔵", "completed": "✅", "abandoned": "❌"}.get(pr['status'], "⚪")
    approval = pr.get('approval', 'Sin revisión')
    approval_emoji = {"Aprobado": "✅", "Aprobado con sugerencias": "⚠️", "Rechazado": "❌",
                       "Esperando autor": "⏳", "Sin revisión": "⬜"}.get(approval, "⬜")

    # Construir body de la card
    body = [
        {
            "type": "TextBlock",
            "text": f"{status_emoji} {title_text}",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Título", "value": pr['title']},
                {"title": "Autor", "value": pr['author']},
                {"title": "Rama", "value": f"{pr['source_branch']} → {pr['target_branch']}"},
                {"title": "Estado", "value": f"{status_emoji} {pr['status'].upper()}"},
                {"title": "Aprobación", "value": f"{approval_emoji} {approval}"},
                {"title": "Componentes", "value": f"Core: {len(core)} | Vlocity: {len(vlocity)}"},
            ]
        },
    ]

    # Alerta de híbridos
    if hybrids:
        hybrid_text = f"⚠️ **{len(hybrids)} componente(s) posiblemente híbrido(s):**\n"
        for h in hybrids[:10]:
            hybrid_text += f"- **{h['name']}** ({h['reason']})\n"
        if len(hybrids) > 10:
            hybrid_text += f"- ... y {len(hybrids) - 10} más\n"

        body.append({
            "type": "TextBlock",
            "text": hybrid_text,
            "wrap": True,
            "spacing": "Medium",
            "color": "Attention"
        })
    else:
        body.append({
            "type": "TextBlock",
            "text": "✅ Sin componentes híbridos detectados",
            "wrap": True,
            "spacing": "Medium",
            "color": "Good"
        })

    body.append({
        "type": "TextBlock",
        "text": "**Componentes modificados:**",
        "wrap": True,
        "spacing": "Medium"
    })
    body.append({
        "type": "TextBlock",
        "text": comp_lines if comp_lines else "Sin componentes CORE/Vlocity",
        "wrap": True,
        "fontType": "Monospace",
        "size": "Small"
    })

    # Botones (acciones a nivel top-level para mayor compatibilidad)
    actions = [
        {
            "type": "Action.OpenUrl",
            "title": "Ver PR en Azure DevOps",
            "url": pr_url
        }
    ]
    if report_url:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "📎 Descargar Reporte HTML",
            "url": report_url
        })

    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": body,
                "actions": actions
            }
        }]
    }

    try:
        data = json.dumps(card).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        response = urllib.request.urlopen(req, timeout=10)
        return response.status in (200, 202, 204)
    except urllib.error.HTTPError as e:
        if e.code in (400, 405):
            return _send_teams_simple(webhook_url, pr, pr_url, core, vlocity,
                                      comp_lines, title_text, status_emoji, hybrids, report_url,
                                      approval, approval_emoji)
        log(f"Error enviando a Teams: {e}")
        return False
    except Exception as e:
        log(f"Error enviando a Teams: {e}")
        return False


def _send_teams_simple(webhook_url, pr, pr_url, core, vlocity, comp_lines,
                        title_text, status_emoji, hybrids=None, report_url=None,
                        approval='Sin revisión', approval_emoji='⬜'):
    """Fallback: formato simple para Teams Workflows"""
    hybrids = hybrids or []

    hybrid_section = ""
    if hybrids:
        hybrid_section = f"\n\n⚠️ **{len(hybrids)} componente(s) posiblemente híbrido(s):**\n"
        for h in hybrids[:10]:
            hybrid_section += f"- **{h['name']}** ({h['reason']})\n"
    else:
        hybrid_section = "\n\n✅ Sin componentes híbridos detectados\n"

    report_section = ""
    if report_url:
        report_section = f"\n\n📎 [Descargar Reporte HTML]({report_url})"

    payload = {
        "title": title_text,
        "body": (
            f"**{pr['title']}**\n\n"
            f"- **Autor:** {pr['author']}\n"
            f"- **Rama:** {pr['source_branch']} → {pr['target_branch']}\n"
            f"- **Estado:** {status_emoji} {pr['status'].upper()}\n"
            f"- **Aprobación:** {approval_emoji} {approval}\n"
            f"- **Componentes:** Core: {len(core)} | Vlocity: {len(vlocity)}\n"
            f"{hybrid_section}\n"
            f"**Componentes modificados:**\n{comp_lines}"
            f"\n[Ver PR en Azure DevOps]({pr_url})"
            f"{report_section}"
        )
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        response = urllib.request.urlopen(req, timeout=10)
        return response.status in (200, 202, 204)
    except Exception as e:
        log(f"Error formato simple Teams: {e}")
        return False


def send_macos_notification(title, message):
    safe_title = title.replace('"', '\\"').replace("'", "")
    safe_msg = message.replace('"', '\\"').replace("'", "")
    os.system(f'osascript -e \'display notification "{safe_msg}" with title "{safe_title}"\'')


# ── Lógica principal ──

def process_pr(pr, webhook_url, is_new=True, old_status=None):
    """Procesa un PR: detecta híbridos, genera reporte, sube a repo, notifica"""
    pr_id = pr['id']
    current_status = pr['status']

    # Detectar híbridos
    hybrids = detect_hybrids(pr, pr['target_branch'])
    if hybrids:
        log(f"  ⚠️ {len(hybrids)} híbrido(s): {', '.join(h['name'] for h in hybrids[:5])}")

    # Generar reporte HTML
    report_path = None
    report_url = None
    html_sent = False

    report_path = generate_report(pr_id, pr['target_branch'])
    if report_path:
        html_sent = True
        log(f"  Reporte generado: {os.path.basename(report_path)}")

        # Subir a rama devops-reports
        report_url = upload_report_to_repo(report_path, pr_id)
        if report_url:
            log(f"  Reporte subido a Azure DevOps")
        else:
            log(f"  No se pudo subir el reporte a Azure DevOps")
    else:
        log(f"  No se pudo generar reporte HTML")

    # Notificar via Teams
    if webhook_url:
        teams_ok = send_teams_notification(
            webhook_url, pr,
            hybrids=hybrids,
            report_url=report_url,
            is_status_change=not is_new,
            old_status=old_status
        )
        log(f"  Teams: {'enviado' if teams_ok else 'error'}")

    # Notificación macOS
    hybrid_note = f" | ⚠️ {len(hybrids)} híbridos" if hybrids else ""
    if is_new:
        send_macos_notification(
            f"Nuevo PR #{pr_id} → {pr['target_branch'].upper()}",
            f"[{current_status.upper()}] {pr['title']}{hybrid_note}"
        )
    else:
        send_macos_notification(
            f"PR #{pr_id}: {old_status} → {current_status.upper()}",
            f"{pr['title']}{hybrid_note}"
        )

    # Calcular hash de componentes
    comp_hash, comp_count = get_component_hash(pr)

    # Guardar en DB
    upsert_pr(pr, current_status, current_status, html_sent, report_path, report_url,
              len(hybrids), comp_hash, comp_count)

    return hybrids, report_path, report_url


def check_prs():
    """Verificación principal — busca PRs nuevos o con cambio de estado"""
    import time
    start_time = time.time()

    config = load_config()

    if not config.get('active', False):
        log("Monitor inactivo. Active desde el CLI.")
        log_cron_execution(result='INACTIVO', detail='Monitor desactivado')
        return

    target_branches = config.get('target_branches', TARGET_BRANCHES)
    webhook_url = config.get('teams_webhook_url', '')

    log(f"Verificando PRs hacia: {', '.join(target_branches)}")

    try:
        # Fetch ramas destino
        for branch in target_branches:
            run_command(f'git fetch origin {branch} 2>/dev/null')

        prs = get_all_prs(target_branches)
        log(f"PRs encontrados en Azure: {len(prs)}")

        # Fetch ramas origen de PRs activos para detectar nuevos commits
        for pr in prs:
            if pr['status'] == 'active':
                run_command(f"git fetch origin {pr['source_branch']} 2>/dev/null")

        new_count = 0
        changed_count = 0
        notif_count = 0

        for pr in prs:
            pr_id = pr['id']
            current_status = pr['status']
            tracked = get_tracked_pr(pr_id)

            if tracked is None:
                # ── PR NUEVO ──
                log(f"NUEVO PR #{pr_id}: {pr['title']} [{current_status}]")
                process_pr(pr, webhook_url, is_new=True)
                new_count += 1
                notif_count += 1

            elif tracked['last_notified_status'] != current_status:
                # ── CAMBIO DE ESTADO ──
                old_status = tracked['last_notified_status']
                log(f"CAMBIO PR #{pr_id}: {old_status} → {current_status} | {pr['title']}")
                process_pr(pr, webhook_url, is_new=False, old_status=old_status)
                changed_count += 1
                notif_count += 1

            else:
                # ── MISMO ESTADO — verificar si cambiaron componentes ──
                comp_hash, comp_count = get_component_hash(pr)
                old_hash = tracked.get('component_hash')

                if old_hash and comp_hash != old_hash:
                    old_count = tracked.get('component_count', 0) or 0
                    diff = comp_count - old_count
                    diff_text = f"+{diff}" if diff > 0 else str(diff)
                    log(f"COMPONENTES PR #{pr_id}: {old_count} → {comp_count} ({diff_text}) | {pr['title']}")
                    process_pr(pr, webhook_url, is_new=False, old_status=f"actualizado ({diff_text} comp)")
                    changed_count += 1
                    notif_count += 1
                else:
                    update_pr_status(pr_id, current_status)

        duration = round(time.time() - start_time, 2)
        detail = f"{new_count} nuevos, {changed_count} cambios" if (new_count + changed_count) > 0 else "Sin novedades"
        log(f"Resultado: {detail} ({duration}s)")

        log_cron_execution(
            prs_found=len(prs), new_prs=new_count, status_changes=changed_count,
            notifications_sent=notif_count, duration=duration, result='OK', detail=detail
        )

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        log(f"Error en check_prs: {e}")
        log_cron_execution(result='ERROR', duration=duration, detail=str(e)[:500])


def show_status():
    config = load_config()
    active = config.get('active', False)
    has_webhook = bool(config.get('teams_webhook_url', ''))

    print(f"\n  Estado: {'ACTIVO' if active else 'INACTIVO'}")
    print(f"  Teams webhook: {'Configurado' if has_webhook else 'No configurado'}")
    print(f"  Ramas monitoreadas: {', '.join(config.get('target_branches', []))}")
    print(f"  Base de datos: MySQL devops.pr_tracking")

    cron_output, _ = run_command("crontab -l 2>/dev/null | grep auto_pr_monitor")
    print(f"  Cron activo: {'Sí' if cron_output else 'No'}")

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*), SUM(status='active'), SUM(status='completed'), SUM(hybrid_count > 0) FROM pr_tracking")
        total, active_prs, completed_prs, hybrid_prs = cursor.fetchone()
        cursor.close()
        db.close()
        print(f"  PRs en DB: {total} (activos: {active_prs or 0}, completados: {completed_prs or 0}, con híbridos: {hybrid_prs or 0})")
    except Exception as e:
        print(f"  Error DB: {e}")
    print()


def show_db_status():
    try:
        rows = get_all_tracked_prs()
        if not rows:
            print("\n  No hay PRs registrados en la base de datos.\n")
            return

        print(f"\n  {'PR':>7} | {'Estado':^12} | {'Híbridos':^8} | {'HTML':^5} | {'Destino':^10} | Título")
        print(f"  {'─'*7} | {'─'*12} | {'─'*8} | {'─'*5} | {'─'*10} | {'─'*40}")

        for row in rows:
            pr_id = row['pr_id']
            status = row['status'] or ''
            hyb = row.get('hybrid_count', 0) or 0
            hyb_str = f"⚠️ {hyb}" if hyb > 0 else "✅"
            html = 'Sí' if row['html_sent'] else 'No'
            target = row['target_branch'] or ''
            title = (row['title'] or '')[:40]
            print(f"  #{pr_id:>6} | {status:^12} | {hyb_str:^8} | {html:^5} | {target:^10} | {title}")
        print()
    except Exception as e:
        print(f"  Error: {e}\n")


def clear_history():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM pr_tracking")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM pr_tracking")
        db.commit()
        cursor.close()
        db.close()
        print(f"  Historial limpiado ({count} PRs eliminados de la base de datos)")
    except Exception as e:
        print(f"  Error: {e}")


def show_cron_log():
    """Muestra las últimas ejecuciones del cron"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cron_log ORDER BY executed_at DESC LIMIT 20")
        rows = cursor.fetchall()
        cursor.close()
        db.close()

        if not rows:
            print("\n  No hay ejecuciones registradas.\n")
            return

        print(f"\n  {'Fecha/Hora':^19} | {'PRs':^4} | {'Nuevos':^6} | {'Cambios':^7} | {'Notif':^5} | {'Tiempo':^7} | {'Estado':^8} | Detalle")
        print(f"  {'─'*19} | {'─'*4} | {'─'*6} | {'─'*7} | {'─'*5} | {'─'*7} | {'─'*8} | {'─'*30}")

        for row in rows:
            dt = row['executed_at'].strftime('%Y-%m-%d %H:%M:%S') if row['executed_at'] else ''
            prs = row.get('prs_found', 0) or 0
            new = row.get('new_prs', 0) or 0
            changes = row.get('status_changes', 0) or 0
            notif = row.get('notifications_sent', 0) or 0
            dur = f"{row.get('duration_seconds', 0) or 0}s"
            result = row.get('result', '')
            detail = (row.get('detail', '') or '')[:30]
            result_icon = '✅' if result == 'OK' else ('⚠️' if result == 'INACTIVO' else '❌')
            print(f"  {dt} | {prs:^4} | {new:^6} | {changes:^7} | {notif:^5} | {dur:>7} | {result_icon} {result:<6} | {detail}")

        print()
    except Exception as e:
        print(f"  Error: {e}\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    action = sys.argv[1]

    if action == '--check':
        check_prs()
    elif action == '--status':
        show_status()
    elif action == '--db-status':
        show_db_status()
    elif action == '--cron-log':
        show_cron_log()
    elif action == '--clear':
        clear_history()
    else:
        print(f"Acción desconocida: {action}")
        print("Use: --check, --status, --db-status, --cron-log, --clear")
        sys.exit(1)
