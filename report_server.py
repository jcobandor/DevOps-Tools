#!/usr/bin/env python3
"""
Report Server - API REST para generar reportes de PRs y Manifests
Expone los reportes de pr_commit_report.py como endpoints HTTP.

Uso:
    python3 report_server.py                    # Inicia en puerto 5000
    python3 report_server.py --port 8080        # Puerto personalizado
    REPORT_API_TOKEN=mi_token python3 report_server.py  # Con autenticación

Endpoints:
    GET /api/report/daily?date=2026-02-16
    GET /api/report/manifest?branch=uat
    GET /api/report/pr?id=11361&branch=uat
"""

import os
import sys
import tempfile
import subprocess
from datetime import datetime, date, timedelta
from flask import Flask, request, Response, jsonify

# Agregar el directorio de scripts al path para importar pr_commit_report
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from pr_commit_report import (
    get_project_root,
    get_pr_info,
    get_pr_specific_files,
    get_pr_changed_files_by_merge_commit,
    get_file_commit_info_in_branch,
    get_file_commit_history,
    get_approved_prs_by_date,
    categorize_component,
    get_component_name,
    parse_package_xml,
    parse_package_yaml,
    find_component_path,
    generate_html,
    generate_html_daily_report,
)

app = Flask(__name__)

# Token de autenticación opcional
API_TOKEN = os.environ.get('REPORT_API_TOKEN', '')


def check_auth():
    """Verifica autenticación si está configurada."""
    if not API_TOKEN:
        return None  # Sin auth configurada, permitir todo
    token = request.args.get('token', '')
    if token != API_TOKEN:
        return Response(
            '<h1>401 - No autorizado</h1><p>Token inválido o faltante. Use ?token=SU_TOKEN</p>',
            status=401,
            mimetype='text/html'
        )
    return None


def git_fetch():
    """Actualiza el repo antes de generar reportes."""
    project_root = get_project_root()
    subprocess.run(
        ['git', 'fetch', 'origin', '--quiet'],
        cwd=project_root,
        capture_output=True,
        timeout=60
    )


@app.route('/')
def index():
    """Página principal con documentación de la API."""
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SURA Banca - Report Server</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            font-size: 2rem;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #94a3b8; margin-bottom: 40px; }
        .endpoint {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .endpoint h2 {
            color: #38bdf8;
            font-size: 1.1rem;
            margin-bottom: 12px;
        }
        .method {
            display: inline-block;
            background: #065f46;
            color: #34d399;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 8px;
        }
        .path {
            font-family: 'SF Mono', Monaco, monospace;
            color: #f1f5f9;
            font-size: 0.95rem;
        }
        .params {
            margin-top: 12px;
            padding-left: 16px;
        }
        .params li {
            color: #94a3b8;
            margin-bottom: 4px;
            list-style: none;
        }
        .params code {
            background: #334155;
            padding: 1px 6px;
            border-radius: 3px;
            color: #e2e8f0;
            font-size: 0.85rem;
        }
        .example {
            margin-top: 12px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
        }
        .example a {
            color: #818cf8;
            text-decoration: none;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.85rem;
        }
        .example a:hover { text-decoration: underline; }
        .status {
            margin-top: 40px;
            text-align: center;
            color: #64748b;
            font-size: 0.85rem;
        }
        .status .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #34d399;
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>SURA Banca Report Server</h1>
        <p class="subtitle">API REST para reportes de PRs y Manifests</p>

        <div class="endpoint">
            <h2><span class="method">GET</span> <span class="path">/api/report/daily</span></h2>
            <p style="color:#94a3b8">Reporte de PRs aprobados por fecha (hacia uat/main)</p>
            <ul class="params">
                <li><code>date</code> — Fecha en formato YYYY-MM-DD (default: ayer)</li>
            </ul>
            <div class="example">
                <a href="/api/report/daily">/api/report/daily</a><br>
                <a href="/api/report/daily?date=2026-02-17">/api/report/daily?date=2026-02-17</a>
            </div>
        </div>

        <div class="endpoint">
            <h2><span class="method">GET</span> <span class="path">/api/report/manifest</span></h2>
            <p style="color:#94a3b8">Reporte de manifest vs una rama</p>
            <ul class="params">
                <li><code>branch</code> — Rama de comparación (default: uat)</li>
            </ul>
            <div class="example">
                <a href="/api/report/manifest">/api/report/manifest</a><br>
                <a href="/api/report/manifest?branch=main">/api/report/manifest?branch=main</a>
            </div>
        </div>

        <div class="endpoint">
            <h2><span class="method">GET</span> <span class="path">/api/report/pr</span></h2>
            <p style="color:#94a3b8">Reporte de un PR específico</p>
            <ul class="params">
                <li><code>id</code> — ID del Pull Request (requerido)</li>
                <li><code>branch</code> — Rama de comparación (default: uat)</li>
            </ul>
            <div class="example">
                <a href="/api/report/pr?id=11376">/api/report/pr?id=11376</a><br>
                <a href="/api/report/pr?id=11376&branch=main">/api/report/pr?id=11376&amp;branch=main</a>
            </div>
        </div>

        <div class="status">
            <span class="dot"></span> Servidor activo — """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>
    </div>
</body>
</html>"""
    return Response(html, mimetype='text/html')


@app.route('/api/report/daily')
def daily_report():
    """Genera reporte diario de PRs aprobados por fecha."""
    auth_error = check_auth()
    if auth_error:
        return auth_error

    # Parámetro de fecha (default: ayer)
    report_date = request.args.get('date', '')
    if not report_date:
        report_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Validar formato
    try:
        datetime.strptime(report_date, '%Y-%m-%d')
    except ValueError:
        return Response(
            f'<h1>400 - Formato de fecha inválido</h1><p>Use YYYY-MM-DD. Recibido: {report_date}</p>',
            status=400, mimetype='text/html'
        )

    try:
        git_fetch()

        # Obtener PRs aprobados en la fecha
        prs = get_approved_prs_by_date(report_date)
        if not prs:
            return Response(
                f'<h1>No se encontraron PRs aprobados el {report_date}</h1>',
                status=200, mimetype='text/html'
            )

        # Filtrar solo PRs hacia uat o main
        TARGET_BRANCHES = {'refs/heads/uat', 'refs/heads/main'}
        prs = [p for p in prs if p.get('targetRefName', '') in TARGET_BRANCHES]
        if not prs:
            return Response(
                f'<h1>No se encontraron PRs hacia uat/main el {report_date}</h1>',
                status=200, mimetype='text/html'
            )

        # Ordenar por PR ID descendente
        prs = sorted(prs, key=lambda p: p.get('pullRequestId', 0), reverse=True)

        # Procesar cada PR
        prs_data = []
        for pr in prs:
            pr_id = pr.get('pullRequestId')
            title = pr.get('title', '')
            source_ref = pr.get('sourceRefName', '')
            target_ref = pr.get('targetRefName', '')
            author = pr.get('createdBy', {}).get('displayName', 'N/A')
            closed_date = pr.get('closedDate', '')[:10]
            merge_commit = pr.get('lastMergeCommit', {}).get('commitId', '')

            changed_files = get_pr_changed_files_by_merge_commit(merge_commit) if merge_commit else []

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
                'merge_commit': merge_commit[:8] if merge_commit else '',
                'merge_commit_full': merge_commit,
                'components_by_category': components_by_category,
                'total_components': sum(len(c) for c in components_by_category.values())
            })

        # Excluir PRs sin componentes
        prs_data = [p for p in prs_data if p['total_components'] > 0]
        if not prs_data:
            return Response(
                f'<h1>PRs del {report_date} no afectan componentes Salesforce/Vlocity</h1>',
                status=200, mimetype='text/html'
            )

        # Generar HTML en archivo temporal
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, dir=script_dir)
        tmp.close()

        target_branch = "uat"
        if generate_html_daily_report(prs_data, report_date, target_branch, tmp.name):
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            os.unlink(tmp.name)

            # Eliminar el botón de "Eliminar reporte" (no aplica en modo servidor)
            html_content = html_content.replace(
                'onclick="deleteReport()"', 'style="display:none"'
            )

            return Response(html_content, mimetype='text/html')
        else:
            os.unlink(tmp.name)
            return Response('<h1>Error al generar el reporte</h1>', status=500, mimetype='text/html')

    except Exception as e:
        return Response(f'<h1>Error</h1><pre>{str(e)}</pre>', status=500, mimetype='text/html')


@app.route('/api/report/manifest')
def manifest_report():
    """Genera reporte de manifest vs una rama."""
    auth_error = check_auth()
    if auth_error:
        return auth_error

    compare_branch = request.args.get('branch', 'uat')

    try:
        git_fetch()
        project_root = get_project_root()

        # Leer manifests
        package_xml = os.path.join(project_root, 'manifest/Salud/package.xml')
        package_yaml = os.path.join(project_root, 'manifest/Salud/package.yaml')

        xml_components = parse_package_xml(package_xml)
        yaml_components = parse_package_yaml(package_yaml)

        # Convertir a rutas de archivos
        changed_files = []
        for component_type, component_name in xml_components + yaml_components:
            file_path = find_component_path(component_type, component_name, project_root)
            if file_path:
                rel_path = os.path.relpath(file_path, project_root)
                changed_files.append(rel_path)

        if not changed_files:
            return Response(
                '<h1>No se encontraron componentes en los manifests</h1>',
                status=200, mimetype='text/html'
            )

        # Obtener commits por archivo
        components_by_category = {}
        for file_path in changed_files:
            if not file_path.startswith('force-app/') and not file_path.startswith('vlocity/'):
                continue
            if file_path.endswith('.cls-meta.xml') or file_path.endswith('.trigger-meta.xml'):
                continue

            commit_info = get_file_commit_info_in_branch(file_path, compare_branch)
            commit_history = get_file_commit_history(file_path, compare_branch)
            category = categorize_component(file_path)
            component_name = get_component_name(file_path)

            if category == 'CustomField':
                parts = file_path.split('/objects/')
                if len(parts) > 1:
                    obj_name = parts[1].split('/')[0]
                    component_name = f"{obj_name}.{component_name}"

            if commit_info:
                component_data = {
                    'name': component_name,
                    'path': file_path,
                    'full_hash': commit_info['full_hash'],
                    'short_hash': commit_info['short_hash'],
                    'author': commit_info['author'],
                    'date': commit_info['date'],
                    'message': commit_info['message'],
                    'is_new': False,
                    'history': commit_history
                }
            else:
                component_data = {
                    'name': component_name,
                    'path': file_path,
                    'full_hash': '',
                    'short_hash': 'NUEVO',
                    'author': '(No existe en rama)',
                    'date': '-',
                    'message': f'Componente nuevo - no existe en {compare_branch}',
                    'is_new': True,
                    'history': []
                }

            if category not in components_by_category:
                components_by_category[category] = []
            components_by_category[category].append(component_data)

        # Generar HTML
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, dir=script_dir)
        tmp.close()

        pr_id = "manifest_salud"
        if generate_html(None, components_by_category, compare_branch, pr_id, tmp.name, report_type='manifest'):
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            os.unlink(tmp.name)
            html_content = html_content.replace(
                'onclick="deleteReport()"', 'style="display:none"'
            )
            return Response(html_content, mimetype='text/html')
        else:
            os.unlink(tmp.name)
            return Response('<h1>Error al generar el reporte</h1>', status=500, mimetype='text/html')

    except Exception as e:
        return Response(f'<h1>Error</h1><pre>{str(e)}</pre>', status=500, mimetype='text/html')


@app.route('/api/report/pr')
def pr_report():
    """Genera reporte de un PR específico."""
    auth_error = check_auth()
    if auth_error:
        return auth_error

    pr_id = request.args.get('id', '')
    if not pr_id:
        return Response(
            '<h1>400 - Falta parámetro</h1><p>Use ?id=NUMERO_PR</p>',
            status=400, mimetype='text/html'
        )

    compare_branch = request.args.get('branch', 'uat')

    try:
        git_fetch()

        # Obtener info del PR
        pr_info = get_pr_info(pr_id)
        if not pr_info:
            return Response(
                f'<h1>PR #{pr_id} no encontrado</h1><p>Verifique que el PR existe en Azure DevOps.</p>',
                status=404, mimetype='text/html'
            )

        # Obtener archivos cambiados
        changed_files = get_pr_specific_files(pr_info['sourceBranch'], pr_info['targetBranch'])

        if not changed_files:
            # Fallback: usar merge commit
            merge_commit = pr_info.get('lastMergeCommit', {}).get('commitId', '')
            if merge_commit:
                changed_files = get_pr_changed_files_by_merge_commit(merge_commit)

        if not changed_files:
            return Response(
                f'<h1>PR #{pr_id} sin archivos cambiados</h1>',
                status=200, mimetype='text/html'
            )

        # Obtener commits por archivo
        components_by_category = {}
        for file_path in changed_files:
            if not file_path.startswith('force-app/') and not file_path.startswith('vlocity/'):
                continue
            if file_path.endswith('.cls-meta.xml') or file_path.endswith('.trigger-meta.xml'):
                continue

            commit_info = get_file_commit_info_in_branch(file_path, compare_branch)
            commit_history = get_file_commit_history(file_path, compare_branch)
            category = categorize_component(file_path)
            component_name = get_component_name(file_path)

            if category == 'CustomField':
                parts = file_path.split('/objects/')
                if len(parts) > 1:
                    obj_name = parts[1].split('/')[0]
                    component_name = f"{obj_name}.{component_name}"

            if commit_info:
                component_data = {
                    'name': component_name,
                    'path': file_path,
                    'full_hash': commit_info['full_hash'],
                    'short_hash': commit_info['short_hash'],
                    'author': commit_info['author'],
                    'date': commit_info['date'],
                    'message': commit_info['message'],
                    'is_new': False,
                    'history': commit_history
                }
            else:
                component_data = {
                    'name': component_name,
                    'path': file_path,
                    'full_hash': '',
                    'short_hash': 'NUEVO',
                    'author': '(No existe en rama)',
                    'date': '-',
                    'message': f'Componente nuevo - no existe en {compare_branch}',
                    'is_new': True,
                    'history': []
                }

            if category not in components_by_category:
                components_by_category[category] = []
            components_by_category[category].append(component_data)

        # Generar HTML
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, dir=script_dir)
        tmp.close()

        if generate_html(pr_info, components_by_category, compare_branch, pr_id, tmp.name, report_type='pr'):
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            os.unlink(tmp.name)
            html_content = html_content.replace(
                'onclick="deleteReport()"', 'style="display:none"'
            )
            return Response(html_content, mimetype='text/html')
        else:
            os.unlink(tmp.name)
            return Response('<h1>Error al generar el reporte</h1>', status=500, mimetype='text/html')

    except Exception as e:
        return Response(f'<h1>Error</h1><pre>{str(e)}</pre>', status=500, mimetype='text/html')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='SURA Banca Report Server')
    parser.add_argument('--port', type=int, default=5000, help='Puerto del servidor (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  SURA Banca Report Server")
    print(f"{'='*60}")
    print(f"  URL local:  http://localhost:{args.port}")
    print(f"  Host:       {args.host}:{args.port}")
    if API_TOKEN:
        print(f"  Auth:       Token requerido (?token=...)")
    else:
        print(f"  Auth:       Sin autenticación (configurar REPORT_API_TOKEN)")
    print(f"\n  Endpoints:")
    print(f"    GET /api/report/daily?date=YYYY-MM-DD")
    print(f"    GET /api/report/manifest?branch=uat")
    print(f"    GET /api/report/pr?id=XXXXX&branch=uat")
    print(f"{'='*60}\n")

    app.run(host=args.host, port=args.port, debug=False)
