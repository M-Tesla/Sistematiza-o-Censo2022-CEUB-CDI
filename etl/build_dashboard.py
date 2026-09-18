#!/usr/bin/env python3
"""Cria o dashboard ODS 4 / Censo Escolar 2022 no Apache Superset."""

from __future__ import annotations

import http.cookiejar
import json
import uuid
import urllib.error
import urllib.request
from urllib.parse import quote

BASE = "http://127.0.0.1:8088"
DB_ID = 2
SLUG = "ods4-educacao-qualidade"
JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))


def req(method: str, path: str, token: str, body=None, csrf: str | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": BASE + "/",
        "Origin": BASE,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if csrf:
        headers["X-CSRFToken"] = csrf
        headers["X-CSRF-Token"] = csrf
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with OPENER.open(r, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        raise SystemExit(f"{method} {path} -> {e.code}\n{err[:2000]}") from e


def login():
    status, payload = req(
        "POST",
        "/api/v1/security/login",
        token="",
        body={"username": "admin", "password": "admin", "provider": "db", "refresh": True},
    )
    token = payload["access_token"]
    _, csrf = req("GET", "/api/v1/security/csrf_token/", token)
    return token, csrf.get("result")


def metric_sql(expr: str, label: str, option: str) -> dict:
    return {
        "expressionType": "SQL",
        "sqlExpression": expr,
        "column": None,
        "aggregate": None,
        "hasCustomLabel": True,
        "label": label,
        "optionName": option,
    }


def sid() -> str:
    return uuid.uuid4().hex[:10]


def create_dataset(token, csrf, table_name: str) -> int:
    _, listing = req(
        "GET",
        f"/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:'{table_name}')),page_size:10)",
        token,
    )
    for row in listing.get("result") or []:
        if row.get("table_name") == table_name and row.get("database", {}).get("id") == DB_ID:
            print("dataset exists", table_name, row["id"])
            req("PUT", f"/api/v1/dataset/{row['id']}/refresh", token, body={}, csrf=csrf)
            return row["id"]
    _, created = req(
        "POST",
        "/api/v1/dataset/",
        token,
        body={"database": DB_ID, "schema": "public", "table_name": table_name, "owners": [1]},
        csrf=csrf,
    )
    ds_id = created["id"]
    print("dataset created", table_name, ds_id)
    req("PUT", f"/api/v1/dataset/{ds_id}/refresh", token, body={}, csrf=csrf)
    return ds_id


def create_chart(token, csrf, name: str, viz: str, ds_id: int, params: dict) -> dict:
    q = quote(f"(filters:!((col:slice_name,opr:eq,value:'{name}')),page_size:5)", safe="")
    _, listing = req("GET", f"/api/v1/chart/?q={q}", token)
    for row in listing.get("result") or []:
        if row.get("slice_name") == name:
            print("chart exists", row["id"], viz, name)
            _, full = req("GET", f"/api/v1/chart/{row['id']}", token)
            return {
                "id": row["id"],
                "uuid": full["result"].get("uuid"),
                "name": name,
                "viz": viz,
            }
    params = {
        **params,
        "viz_type": viz,
        "datasource": f"{ds_id}__table",
        "dashboards": [],
        "extra_form_data": {},
        "annotation_layers": [],
        "adhoc_filters": params.get("adhoc_filters", []),
    }
    _, created = req(
        "POST",
        "/api/v1/chart/",
        token,
        body={
            "slice_name": name,
            "viz_type": viz,
            "datasource_id": ds_id,
            "datasource_type": "table",
            "params": json.dumps(params),
            "query_context": json.dumps(
                {
                    "datasource": {"id": ds_id, "type": "table"},
                    "force": False,
                    "queries": [{}],
                    "form_data": params,
                    "result_format": "json",
                    "result_type": "full",
                }
            ),
            "owners": [1],
        },
        csrf=csrf,
    )
    chart_id = created["id"]
    _, full = req("GET", f"/api/v1/chart/{chart_id}", token)
    print("chart", chart_id, viz, name)
    return {
        "id": chart_id,
        "uuid": full["result"].get("uuid"),
        "name": name,
        "viz": viz,
    }


def native_filter(fid: str, name: str, column: str, ds_id: int) -> dict:
    return {
        "id": fid,
        "name": name,
        "filterType": "filter_select",
        "targets": [{"datasetId": ds_id, "column": {"name": column}}],
        "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
        "controlValues": {
            "enableEmptyFilter": False,
            "defaultToFirstItem": False,
            "multiSelect": True,
            "searchAllOptions": True,
            "inverseSelection": False,
        },
        "cascadeParentIds": [],
        "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
        "type": "NATIVE_FILTER",
        "description": "",
        "chartsInScope": [],
        "tabsInScope": [],
    }


class Dash:
    def __init__(self, title: str):
        self.title = title
        self.pos = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"children": ["GRID_ID"], "id": "ROOT_ID", "type": "ROOT"},
            "GRID_ID": {
                "children": ["TABS-MAIN"],
                "id": "GRID_ID",
                "parents": ["ROOT_ID"],
                "type": "GRID",
            },
            "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": title}},
            "TABS-MAIN": {
                "children": [],
                "id": "TABS-MAIN",
                "meta": {},
                "parents": ["ROOT_ID", "GRID_ID"],
                "type": "TABS",
            },
        }
        self.chart_ids: list[int] = []

    def add_tab(self, title: str) -> str:
        tab_id = f"TAB-{sid()}"
        self.pos[tab_id] = {
            "children": [],
            "id": tab_id,
            "meta": {"text": title, "defaultText": title, "placeholder": "Aba"},
            "parents": ["ROOT_ID", "GRID_ID", "TABS-MAIN"],
            "type": "TAB",
        }
        self.pos["TABS-MAIN"]["children"].append(tab_id)
        return tab_id

    def add_row(self, tab_id: str, items: list[tuple[dict, int, int]]):
        """items: (chart_or_md, width, height)"""
        row_id = f"ROW-{sid()}"
        children = []
        for item, width, height in items:
            if item.get("_markdown"):
                node_id = f"MARKDOWN-{sid()}"
                self.pos[node_id] = {
                    "children": [],
                    "id": node_id,
                    "meta": {
                        "width": width,
                        "height": height,
                        "code": item["code"],
                    },
                    "parents": ["ROOT_ID", "GRID_ID", "TABS-MAIN", tab_id, row_id],
                    "type": "MARKDOWN",
                }
            else:
                node_id = f"CHART-{sid()}"
                self.pos[node_id] = {
                    "children": [],
                    "id": node_id,
                    "meta": {
                        "chartId": item["id"],
                        "uuid": item.get("uuid") or str(uuid.uuid4()),
                        "height": height,
                        "width": width,
                        "sliceName": item["name"],
                    },
                    "parents": ["ROOT_ID", "GRID_ID", "TABS-MAIN", tab_id, row_id],
                    "type": "CHART",
                }
                self.chart_ids.append(item["id"])
            children.append(node_id)
        self.pos[row_id] = {
            "children": children,
            "id": row_id,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID", "TABS-MAIN", tab_id],
            "type": "ROW",
        }
        self.pos[tab_id]["children"].append(row_id)


def md(html: str) -> dict:
    return {"_markdown": True, "code": html}


def main() -> None:
    token, csrf = login()
    escola = create_dataset(token, csrf, "v_escola_ativa")
    uf = create_dataset(token, csrf, "agg_uf")
    mun = create_dataset(token, csrf, "agg_municipio")
    ufdep = create_dataset(token, csrf, "agg_uf_dependencia")

    n_escolas = metric_sql("COUNT(*)", "Escolas", "m_escolas")
    n_mat = metric_sql("SUM(qt_mat_bas)", "Matrículas", "m_mat")
    n_doc = metric_sql("SUM(qt_doc_bas)", "Docentes", "m_doc")
    n_eisa = metric_sql(
        "SUM(flag_inclusao_sem_acessibilidade)",
        "Escolas sem acessibilidade",
        "m_eisa",
    )
    n_pcd = metric_sql(
        "SUM(qt_mat_esp_sem_acessibilidade)",
        "Matrículas PCD sem acessibilidade",
        "m_pcd",
    )
    n_mat_esp = metric_sql("SUM(qt_mat_esp)", "Matrículas educação especial", "m_esp")
    pct_net = metric_sql(
        "AVG(CASE WHEN in_internet = 1 THEN 1.0 ELSE 0.0 END)",
        "% com internet",
        "m_net",
    )
    n_deserto = metric_sql("SUM(flag_deserto_digital)", "Escolas sem internet", "m_deserto")
    ratio = metric_sql(
        "SUM(qt_mat_bas)::float / NULLIF(SUM(qt_doc_bas),0)",
        "Alunos por docente",
        "m_ratio",
    )

    def kpi(name, metric, ds, fmt="SMART_NUMBER", subheader=""):
        return create_chart(
            token,
            csrf,
            name,
            "big_number_total",
            ds,
            {
                "metric": metric,
                "header_font_size": 0.4,
                "subheader_font_size": 0.15,
                "subheader": subheader,
                "y_axis_format": fmt,
                "time_format": "smart_date",
            },
        )

    def bar(name, x, metric, ds, limit=27, horizontal=False, fmt=",.0f"):
        return create_chart(
            token,
            csrf,
            name,
            "echarts_timeseries_bar",
            ds,
            {
                "x_axis": x,
                "metrics": [metric],
                "groupby": [],
                "orientation": "horizontal" if horizontal else "vertical",
                "order_desc": True,
                "row_limit": limit,
                "color_scheme": "supersetColors",
                "show_legend": False,
                "y_axis_format": fmt,
                "truncate_metric": True,
                "rich_tooltip": True,
                "show_value": False,
            },
        )

    c_escolas = kpi("Escolas em atividade", n_escolas, escola, subheader="Censo Escolar 2022")
    c_mat = kpi("Matrículas na educação básica", n_mat, escola, subheader="Alunos matriculados")
    c_doc = kpi("Docentes", n_doc, escola, subheader="Funções docentes")
    c_ratio = kpi("Alunos por docente", ratio, escola, fmt=",.1f", subheader="Média nacional")
    c_eisa = kpi("Escolas inclusão sem acessibilidade", n_eisa, escola, subheader="Indicador EISA")
    c_pcd = kpi("Alunos PCD em escolas sem acessibilidade", n_pcd, escola, subheader="ODS 4.5")
    c_deserto = kpi("Escolas sem internet", n_deserto, escola, subheader="Com matrícula ativa")
    c_net = kpi("% escolas com internet", pct_net, escola, fmt=".1%", subheader="Rede de acesso")
    pct_banda = metric_sql(
        "AVG(CASE WHEN in_banda_larga = 1 THEN 1.0 ELSE 0.0 END)",
        "% com banda larga",
        "m_banda",
    )
    c_banda = kpi(
        "% escolas com banda larga",
        pct_banda,
        escola,
        fmt=".1%",
        subheader="Acesso estável à rede",
    )

    c_regiao = bar("Matrículas por região", "no_regiao", n_mat, escola, limit=5)
    c_dep = create_chart(
        token,
        csrf,
        "Escolas por dependência administrativa",
        "pie",
        escola,
        {
            "groupby": ["no_dependencia"],
            "metric": n_escolas,
            "donut": True,
            "innerRadius": 40,
            "outerRadius": 70,
            "label_type": "key_percent",
            "labels_outside": True,
            "show_labels": True,
            "show_legend": True,
            "color_scheme": "supersetColors",
            "number_format": "SMART_NUMBER",
            "row_limit": 10,
        },
    )
    c_loc = create_chart(
        token,
        csrf,
        "Escolas urbanas e rurais",
        "pie",
        escola,
        {
            "groupby": ["no_localizacao"],
            "metric": n_escolas,
            "donut": True,
            "innerRadius": 38,
            "outerRadius": 68,
            "label_type": "key_value",
            "labels_outside": True,
            "show_labels": True,
            "show_legend": True,
            "color_scheme": "googleCategory10c",
            "number_format": ",d",
            "row_limit": 5,
        },
    )
    c_tree = create_chart(
        token,
        csrf,
        "Matrículas por região e UF",
        "echarts_timeseries_bar",
        escola,
        {
            "x_axis": "no_regiao",
            "metrics": [n_mat],
            "groupby": ["sg_uf"],
            "orientation": "horizontal",
            "stack": True,
            "order_desc": True,
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "show_legend": True,
            "legendOrientation": "bottom",
            "y_axis_format": ",.0f",
            "rich_tooltip": True,
            "show_value": False,
            "truncate_metric": True,
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_title_margin": 0,
            "y_axis_title_margin": 0,
        },
    )
    c_map = create_chart(
        token,
        csrf,
        "Porte da escola (matrículas por escola)",
        "country_map",
        uf,
        {
            "entity": "iso_uf",
            "select_country": "brazil",
            "metric": metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "m_mat_esc"),
            "linear_color_scheme": "schemeYlGnBu",
            "number_format": ",.0f",
            "row_limit": 30,
        },
    )
    c_uf_bar = bar(
        "Matrículas por escola, por UF",
        "sg_uf",
        metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "m_mat_esc2"),
        uf,
        limit=27,
        horizontal=True,
        fmt=",.0f",
    )
    c_scatter = create_chart(
        token,
        csrf,
        "Municípios: intensidade do risco de acessibilidade",
        "deck_scatter",
        mun,
        {
            "spatial": {"latCol": "latitude", "lonCol": "longitude", "type": "latlong"},
            "mapbox_style": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "viewport": {
                "longitude": -51.9,
                "latitude": -14.2,
                "zoom": 3.4,
                "bearing": 0,
                "pitch": 0,
            },
            "point_radius_fixed": {
                "type": "metric",
                "value": metric_sql(
                    "AVG(pcd_sem_acess_por_mil)",
                    "PCD sem acessibilidade / mil matrículas",
                    "m_pcd_mun",
                ),
            },
            "min_radius": 2,
            "max_radius": 80,
            "multiplier": 1,
            "row_limit": 5570,
            "autozoom": False,
            "legend_format": ",.2f",
        },
    )
    c_mun_tbl = create_chart(
        token,
        csrf,
        "Municípios padronizados (não o volume bruto)",
        "table",
        mun,
        {
            "query_mode": "aggregate",
            "groupby": ["no_municipio", "sg_uf", "no_regiao"],
            "metrics": [
                metric_sql("AVG(n_escolas)", "Escolas (contexto)", "t_esc"),
                metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "t_mpe"),
                metric_sql("AVG(pct_inclusao_sem_acessibilidade)", "% EISA", "t_eisa"),
                metric_sql(
                    "AVG(pcd_sem_acess_por_mil)",
                    "PCD sem acess. / mil matrículas",
                    "t_pcd",
                ),
            ],
            "percent_metrics": [],
            "order_desc": True,
            "row_limit": 30,
            "table_timestamp_format": "smart_date",
            "show_cell_bars": True,
            "color_pn": True,
            "page_length": 15,
        },
    )
    c_eisa_uf = bar(
        "% de escolas com inclusão sem acessibilidade, por UF",
        "sg_uf",
        metric_sql(
            "AVG(pct_inclusao_sem_acessibilidade)",
            "% escolas inclusão sem acessibilidade",
            "m_pct_eisa",
        ),
        uf,
        limit=27,
        horizontal=True,
        fmt=".1%",
    )
    c_sun = create_chart(
        token,
        csrf,
        "PCD sem acessibilidade por região e rede",
        "echarts_timeseries_bar",
        escola,
        {
            "x_axis": "no_regiao",
            "metrics": [n_pcd],
            "groupby": ["no_dependencia"],
            "orientation": "horizontal",
            "stack": True,
            "order_desc": True,
            "row_limit": 20,
            "color_scheme": "supersetColors",
            "show_legend": True,
            "legendOrientation": "bottom",
            "y_axis_format": ",.0f",
            "rich_tooltip": True,
            "show_value": False,
            "truncate_metric": True,
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_title_margin": 0,
            "y_axis_title_margin": 0,
        },
    )
    c_esp_vs = create_chart(
        token,
        csrf,
        "Risco relativo: escolas EISA vs % da educ. especial sem acessibilidade",
        "echarts_timeseries_bar",
        uf,
        {
            "x_axis": "sg_uf",
            "metrics": [
                metric_sql(
                    "AVG(pct_inclusao_sem_acessibilidade)",
                    "% escolas inclusão sem acessibilidade",
                    "m_pct_eisa2",
                ),
                metric_sql(
                    "AVG(taxa_pcd_sem_acess)",
                    "% da educ. especial sem acessibilidade",
                    "m_taxa_pcd",
                ),
            ],
            "groupby": [],
            "orientation": "vertical",
            "order_desc": True,
            "row_limit": 27,
            "color_scheme": "supersetColors",
            "show_legend": True,
            "y_axis_format": ".1%",
            "rich_tooltip": True,
        },
    )
    c_net_reg = bar(
        "Escolas sem internet, por região",
        "no_regiao",
        n_deserto,
        escola,
        limit=5,
    )
    c_pivot = create_chart(
        token,
        csrf,
        "Composição da rede em cada UF (% das matrículas)",
        "pivot_table_v2",
        ufdep,
        {
            "groupbyRows": ["sg_uf"],
            "groupbyColumns": ["no_dependencia"],
            "metrics": [
                metric_sql(
                    "AVG(pct_matriculas_na_uf)",
                    "% das matrículas da UF",
                    "m_share",
                )
            ],
            "metricsLayout": "COLUMNS",
            "aggregateFunction": "Sum",
            "row_limit": 10000,
            "valueFormat": ".1%",
            "order_desc": True,
            "combineMetric": False,
            "transposePivot": False,
        },
    )
    c_loc_bar = create_chart(
        token,
        csrf,
        "Matrículas urbanas e rurais por região",
        "echarts_timeseries_bar",
        escola,
        {
            "x_axis": "no_regiao",
            "metrics": [n_mat],
            "groupby": ["no_localizacao"],
            "orientation": "vertical",
            "stack": True,
            "order_desc": False,
            "row_limit": 20,
            "color_scheme": "supersetColors",
            "show_legend": True,
            "y_axis_format": ",.0f",
        },
    )
    c_uf_tbl = create_chart(
        token,
        csrf,
        "UF comparáveis: taxas, não o tamanho do estado",
        "table",
        uf,
        {
            "query_mode": "aggregate",
            "groupby": ["no_uf", "sg_uf", "no_regiao"],
            "metrics": [
                metric_sql("AVG(n_escolas)", "Nº escolas (contexto)", "u_esc"),
                metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "u_mpe"),
                metric_sql("AVG(media_alunos_por_docente)", "Alunos por docente", "u_apd"),
                metric_sql("AVG(pct_escolas_com_internet)", "% com internet", "u_net"),
                metric_sql(
                    "AVG(pct_inclusao_sem_acessibilidade)",
                    "% escolas EISA",
                    "u_eisa",
                ),
                metric_sql(
                    "AVG(pcd_sem_acess_por_mil)",
                    "PCD sem acess. / mil matrículas",
                    "u_pcd",
                ),
                metric_sql(
                    "AVG(taxa_pcd_sem_acess)",
                    "% da educ. especial sem acess.",
                    "u_taxa",
                ),
            ],
            "percent_metrics": [],
            "order_desc": True,
            "row_limit": 30,
            "show_cell_bars": True,
            "color_pn": True,
            "page_length": 27,
        },
    )

    dash = Dash("Educação de Qualidade: Censo Escolar 2022")
    t1 = dash.add_tab("1. Visão geral")
    t2 = dash.add_tab("2. Geografia")
    t3 = dash.add_tab("3. Inclusão sem acessibilidade")
    t4 = dash.add_tab("4. Infraestrutura digital")
    t5 = dash.add_tab("5. Comparação justa entre UFs")

    dash.add_row(
        t1,
        [
            (
                md(
                    """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px 4px">
<h2 style="margin:0 0 6px;color:#123047;font-size:22px">ODS 4 · Educação básica brasileira em 2022</h2>
<p style="margin:0;color:#4b5c6b;font-size:14px;line-height:1.45">
Painel construído com microdados oficiais do INEP (escolas em atividade).
Use os filtros de <b>UF</b>, <b>região</b>, <b>rede</b> e <b>localização</b> para cruzar os recortes.
O ponto extra, inclusão sem acessibilidade, está na aba 3.
</p></div>"""
                ),
                12,
                12,
            )
        ],
    )
    dash.add_row(t1, [(c_escolas, 3, 18), (c_mat, 3, 18), (c_doc, 3, 18), (c_ratio, 3, 18)])
    dash.add_row(t1, [(c_regiao, 6, 42), (c_dep, 3, 42), (c_loc, 3, 42)])
    dash.add_row(t1, [(c_tree, 12, 64)])

    dash.add_row(
        t2,
        [
            (
                md(
                    """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 4px;color:#123047">Distribuição territorial (padronizada)</h3>
<p style="margin:0;color:#4b5c6b;font-size:13px">O mapa e as barras mostram <b>matrículas por escola</b>, não o total do estado. Assim DF, RR e SP entram na mesma escala. O mapa municipal usa a intensidade do risco de acessibilidade (PCD sem acessibilidade a cada mil matrículas).</p>
</div>"""
                ),
                12,
                10,
            )
        ],
    )
    dash.add_row(t2, [(c_map, 7, 58), (c_uf_bar, 5, 58)])
    dash.add_row(t2, [(c_scatter, 7, 56), (c_mun_tbl, 5, 56)])

    dash.add_row(
        t3,
        [
            (
                md(
                    """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 6px;color:#8a1c1c">Indicador extra · Inclusão sem acessibilidade (EISA)</h3>
<p style="margin:0;color:#4b5c6b;font-size:13px;line-height:1.5">
Escola ativa com matrícula de educação especial e <b>nenhum</b> recurso de acessibilidade
(rampa, corrimão, elevador, piso tátil, vão livre, banheiro PNE, dependências PNE ou sala de AEE).
Os KPIs nacionais continuam em volume (quantas crianças). Os gráficos por UF usam <b>percentual de escolas</b> e <b>% da educação especial sem acessibilidade</b>, senão SP e MG “ganham” só por serem grandes.
Em 2022: <b>25.911 escolas</b> e <b>153.726 matrículas</b> nessa condição.
</p></div>"""
                ),
                12,
                16,
            )
        ],
    )
    dash.add_row(t3, [(c_eisa, 4, 20), (c_pcd, 4, 20), (c_escolas, 4, 20)])
    dash.add_row(t3, [(c_eisa_uf, 6, 52), (c_sun, 6, 52)])
    dash.add_row(t3, [(c_esp_vs, 12, 48)])

    dash.add_row(
        t4,
        [
            (
                md(
                    """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 4px;color:#123047">Infraestrutura tecnológica</h3>
<p style="margin:0;color:#4b5c6b;font-size:13px">Sem internet a inclusão também falha: material acessível, AEE a distância e software leitor de tela não chegam. Cruze com a aba 3: escola EISA e sem rede é exclusão em dobro, e isso pesa no Norte e no rural.</p>
</div>"""
                ),
                12,
                10,
            )
        ],
    )
    dash.add_row(t4, [(c_net, 4, 20), (c_deserto, 4, 20), (c_banda, 4, 20)])
    dash.add_row(t4, [(c_net_reg, 6, 44), (c_loc_bar, 6, 44)])

    dash.add_row(
        t5,
        [
            (
                md(
                    """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 6px;color:#123047">Comparação justa entre UFs</h3>
<p style="margin:0;color:#4b5c6b;font-size:13px;line-height:1.5">
Volume absoluto faz São Paulo parecer “quase tudo” e o DF parecer irrelevante: isso só mede <b>tamanho</b>.
Aqui cada UF vale 100%: a matriz é a <b>composição da rede</b> (quanto da matrícula é estadual, municipal, privada).
A tabela usa <b>matrículas por escola</b>, alunos por docente e taxas de inclusão/internet.
Exemplo: o DF tem menos escolas que SP, mas <b>mais alunos por escola</b> (461 vs 329) e <b>muito menos</b> inclusão sem acessibilidade (1,6% vs 21%).
</p></div>"""
                ),
                12,
                10,
            )
        ],
    )
    dash.add_row(t5, [(c_pivot, 12, 58)])
    dash.add_row(t5, [(c_uf_tbl, 12, 52)])

    filters = [
        native_filter(f"NATIVE_FILTER-{sid()}", "UF", "sg_uf", escola),
        native_filter(f"NATIVE_FILTER-{sid()}", "Região", "no_regiao", escola),
        native_filter(f"NATIVE_FILTER-{sid()}", "Dependência administrativa", "no_dependencia", escola),
        native_filter(f"NATIVE_FILTER-{sid()}", "Localização", "no_localizacao", escola),
    ]
    metadata = {
        "color_scheme": "supersetColors",
        "refresh_frequency": 0,
        "cross_filters_enabled": True,
        "native_filter_configuration": filters,
        "chart_configuration": {},
        "global_chart_configuration": {
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "chartsInScope": dash.chart_ids,
        },
        "shared_label_colors": {},
        "map_label_colors": {},
        "label_colors": {},
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "filter_bar_orientation": "VERTICAL",
    }
    css = """
.dashboard-header .dashboard-component-header {
  font-weight: 650;
  letter-spacing: -0.02em;
}
.dashboard-markdown h2, .dashboard-markdown h3 { font-weight: 650; }
.filter-bar { background: #f6f8fb; }
"""

    # remove previous
    _, listing = req("GET", f"/api/v1/dashboard/?q=(filters:!((col:slug,opr:eq,value:'{SLUG}')),page_size:5)", token)
    for row in listing.get("result") or []:
        if row.get("slug") == SLUG:
            req("DELETE", f"/api/v1/dashboard/{row['id']}", token, csrf=csrf)
            print("deleted old dashboard", row["id"])

    _, created = req(
        "POST",
        "/api/v1/dashboard/",
        token,
        body={
            "dashboard_title": dash.title,
            "slug": SLUG,
            "published": True,
            "certified_by": "Censo Escolar 2022 / INEP",
            "certification_details": "ODS 4: Educação de Qualidade",
            "owners": [1],
            "position_json": json.dumps(dash.pos),
            "json_metadata": json.dumps(metadata),
            "css": css,
        },
        csrf=csrf,
    )
    dash_id = created["id"]
    req(
        "PUT",
        f"/api/v1/dashboard/{dash_id}",
        token,
        body={
            "published": True,
            "slug": SLUG,
            "position_json": json.dumps(dash.pos),
            "json_metadata": json.dumps(metadata),
            "css": css,
            "slices": dash.chart_ids,
        },
        csrf=csrf,
    )
    print("DASHBOARD", dash_id, f"{BASE}/superset/dashboard/{SLUG}/")
    print("charts", dash.chart_ids)


if __name__ == "__main__":
    main()
