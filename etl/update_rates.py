#!/usr/bin/env python3
"""Troca comparações por volume (SP 'ganha' por ser grande) por taxas padronizadas."""

from __future__ import annotations

import http.cookiejar
import json
import urllib.error
import urllib.request
from urllib.parse import quote

BASE = "http://127.0.0.1:8088"
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
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}\n{e.read().decode()[:2000]}") from e


def login():
    payload = req(
        "POST",
        "/api/v1/security/login",
        "",
        {"username": "admin", "password": "admin", "provider": "db", "refresh": True},
    )
    token = payload["access_token"]
    csrf = req("GET", "/api/v1/security/csrf_token/", token).get("result")
    return token, csrf


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


def refresh(token, csrf, ds_id: int):
    req("PUT", f"/api/v1/dataset/{ds_id}/refresh", token, {}, csrf)
    print("refreshed dataset", ds_id)


def ensure_dataset(token, csrf, table: str) -> int:
    q = quote(f"(filters:!((col:table_name,opr:eq,value:'{table}')),page_size:10)", safe="")
    listing = req("GET", f"/api/v1/dataset/?q={q}", token)
    for row in listing.get("result") or []:
        if row.get("table_name") == table:
            refresh(token, csrf, row["id"])
            return row["id"]
    created = req(
        "POST",
        "/api/v1/dataset/",
        token,
        {"database": 2, "schema": "public", "table_name": table, "owners": [1]},
        csrf,
    )
    refresh(token, csrf, created["id"])
    print("created dataset", table, created["id"])
    return created["id"]


def get_chart(token, chart_id: int) -> dict:
    return req("GET", f"/api/v1/chart/{chart_id}", token)["result"]


def put_chart(
    token,
    csrf,
    chart_id: int,
    name: str,
    viz: str,
    params: dict,
    ds_id: int | None = None,
    description: str | None = None,
):
    payload = {
        "slice_name": name,
        "viz_type": viz,
        "params": json.dumps(params),
        "query_context": json.dumps(
            {
                "datasource": {"id": ds_id or int(str(params.get("datasource", "0")).split("__")[0]), "type": "table"},
                "force": False,
                "queries": [{}],
                "form_data": params,
                "result_format": "json",
                "result_type": "full",
            }
        ),
    }
    if ds_id is not None:
        payload["datasource_id"] = ds_id
        payload["datasource_type"] = "table"
    if description is not None:
        payload["description"] = description
    req("PUT", f"/api/v1/chart/{chart_id}", token, payload, csrf)
    print("updated chart", chart_id, name)


def main() -> None:
    token, csrf = login()
    escola = 22
    uf = ensure_dataset(token, csrf, "agg_uf")
    mun = ensure_dataset(token, csrf, "agg_municipio")
    ufdep = ensure_dataset(token, csrf, "agg_uf_dependencia")
    refresh(token, csrf, escola)

    mat_esc = metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "m_mat_esc")
    pct_eisa = metric_sql(
        "AVG(pct_inclusao_sem_acessibilidade)",
        "% escolas inclusão sem acessibilidade",
        "m_pct_eisa",
    )
    pcd_mil = metric_sql(
        "AVG(pcd_sem_acess_por_mil)",
        "PCD sem acessibilidade por 1.000 alunos",
        "m_pcd_mil",
    )
    taxa_pcd = metric_sql(
        "AVG(taxa_pcd_sem_acess)",
        "% da educ. especial sem acessibilidade",
        "m_taxa_pcd",
    )
    pct_net = metric_sql("AVG(pct_escolas_com_internet)", "% escolas com internet", "m_pct_net")
    alunos_doc = metric_sql("AVG(media_alunos_por_docente)", "Alunos por docente", "m_apd")

    # 116 map
    p = json.loads(get_chart(token, 116)["params"])
    p.update(
        {
            "metric": mat_esc,
            "number_format": ",.0f",
            "linear_color_scheme": "schemeYlGnBu",
            "entity": "iso_uf",
            "select_country": "brazil",
            "datasource": f"{uf}__table",
        }
    )
    put_chart(token, csrf, 116, "Porte da escola (matrículas por escola)", "country_map", p, uf)

    # 117 bar UF
    p = json.loads(get_chart(token, 117)["params"])
    p.update(
        {
            "metrics": [mat_esc],
            "x_axis": "sg_uf",
            "y_axis_format": ",.0f",
            "datasource": f"{uf}__table",
        }
    )
    put_chart(token, csrf, 117, "Matrículas por escola, por UF", "echarts_timeseries_bar", p, uf)

    # 118 scatter: tamanho = taxa, nao volume
    p = json.loads(get_chart(token, 118)["params"])
    p["point_radius_fixed"] = {
        "type": "metric",
        "value": metric_sql(
            "AVG(pcd_sem_acess_por_mil)",
            "PCD sem acessibilidade por 1.000 alunos",
            "m_pcd_mun",
        ),
    }
    p["datasource"] = f"{mun}__table"
    put_chart(
        token,
        csrf,
        118,
        "Municípios: intensidade do risco de acessibilidade",
        "deck_scatter",
        p,
        mun,
    )

    # 119 table municípios
    p = json.loads(get_chart(token, 119)["params"])
    p["groupby"] = ["no_municipio", "sg_uf"]
    p["metrics"] = [
        metric_sql("SUM(n_escolas)", "Escolas", "t_esc"),
        metric_sql("SUM(qt_matriculas)", "Matrículas totais", "t_mat"),
        metric_sql(
            "SUM(qt_mat_esp_sem_acessibilidade)",
            "Alunos PCD sem acessibilidade",
            "t_pcd_n",
        ),
        metric_sql(
            "AVG(pcd_sem_acess_por_mil)",
            "PCD sem acessibilidade por 1.000 alunos",
            "t_pcd",
        ),
    ]
    p["datasource"] = f"{mun}__table"
    p["column_config"] = {
        "Escolas": {"d3NumberFormat": ",.0f"},
        "Matrículas totais": {"d3NumberFormat": ",.0f"},
        "Alunos PCD sem acessibilidade": {"d3NumberFormat": ",.0f"},
        "PCD sem acessibilidade por 1.000 alunos": {"d3NumberFormat": ",.2f"},
    }
    put_chart(
        token,
        csrf,
        119,
        "Municípios: taxa visível (PCD sem acessibilidade por 1.000 alunos)",
        "table",
        p,
        mun,
        description=(
            "Fórmula: (alunos PCD em escola sem acessibilidade ÷ matrículas totais) × 1.000. "
            "Não é volume em milhares. Município de São Paulo: 10.667 ÷ 2.693.361 × 1.000 = 3,96 "
            "(são 10.667 alunos, não 3.960)."
        ),
    )

    # 120 EISA by UF as %
    p = json.loads(get_chart(token, 120)["params"])
    p.update(
        {
            "metrics": [pct_eisa],
            "y_axis_format": ".1%",
            "datasource": f"{uf}__table",
        }
    )
    put_chart(
        token,
        csrf,
        120,
        "% de escolas com inclusão sem acessibilidade, por UF",
        "echarts_timeseries_bar",
        p,
        uf,
    )

    # 122 two rates
    p = json.loads(get_chart(token, 122)["params"])
    p.update(
        {
            "metrics": [pct_eisa, taxa_pcd],
            "y_axis_format": ".1%",
            "datasource": f"{uf}__table",
        }
    )
    put_chart(
        token,
        csrf,
        122,
        "Risco relativo: escolas EISA vs % da educ. especial sem acessibilidade",
        "echarts_timeseries_bar",
        p,
        uf,
    )

    # 124 pivot → composição da rede (soma 100% em cada UF)
    p = json.loads(get_chart(token, 124)["params"])
    p.update(
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
            "valueFormat": ".1%",
            "datasource": f"{ufdep}__table",
        }
    )
    put_chart(
        token,
        csrf,
        124,
        "Composição da rede em cada UF (% das matrículas)",
        "pivot_table_v2",
        p,
        ufdep,
    )

    # 126 table rates
    p = json.loads(get_chart(token, 126)["params"])
    p["metrics"] = [
        metric_sql("SUM(n_escolas)", "Escolas", "u_esc"),
        metric_sql("SUM(qt_matriculas)", "Matrículas totais", "u_mat"),
        metric_sql(
            "SUM(qt_mat_esp_sem_acessibilidade)",
            "Alunos PCD sem acessibilidade",
            "u_pcd_n",
        ),
        metric_sql(
            "AVG(pcd_sem_acess_por_mil)",
            "PCD sem acessibilidade por 1.000 alunos",
            "u_pcd",
        ),
        metric_sql("AVG(matriculas_por_escola)", "Matrículas por escola", "u_mpe"),
        metric_sql("AVG(pct_inclusao_sem_acessibilidade)", "% escolas EISA", "u_eisa"),
        metric_sql("AVG(taxa_pcd_sem_acess)", "% da educ. especial sem acess.", "u_taxa"),
    ]
    p["datasource"] = f"{uf}__table"
    p["column_config"] = {
        "Escolas": {"d3NumberFormat": ",.0f"},
        "Matrículas totais": {"d3NumberFormat": ",.0f"},
        "Alunos PCD sem acessibilidade": {"d3NumberFormat": ",.0f"},
        "PCD sem acessibilidade por 1.000 alunos": {"d3NumberFormat": ",.2f"},
        "Matrículas por escola": {"d3NumberFormat": ",.1f"},
        "% escolas EISA": {"d3NumberFormat": ".1%"},
        "% da educ. especial sem acess.": {"d3NumberFormat": ".1%"},
    }
    put_chart(
        token,
        csrf,
        126,
        "UF: taxa visível (PCD sem acessibilidade por 1.000 alunos)",
        "table",
        p,
        uf,
        description=(
            "Fórmula: (alunos PCD em escola sem acessibilidade ÷ matrículas totais) × 1.000. "
            "Estado de São Paulo: 50.086 ÷ 10.029.069 × 1.000 = 4,99 (50.086 alunos, não 4.990). "
            "DF: 340 ÷ 643.698 × 1.000 = 0,53."
        ),
    )

    # markdown and tab titles
    dash = req("GET", "/api/v1/dashboard/10", token)["result"]
    pos = json.loads(dash["position_json"])
    for node in pos.values():
        if not isinstance(node, dict):
            continue
        if node.get("type") == "TAB":
            text = node.get("meta", {}).get("text") or ""
            if "Matriz" in text or "detalhamento" in text:
                node["meta"]["text"] = "5. Comparação justa entre UFs"
            continue
        if node.get("type") != "MARKDOWN":
            continue
        code = node.get("meta", {}).get("code") or ""
        if "Comparação justa entre UFs" in code or "Matriz e leitura por UF" in code or "tabela dinâmica" in code.lower():
            node["meta"]["code"] = """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 6px">Comparação justa entre UFs</h3>
<p style="margin:0 0 8px;font-size:13px;line-height:1.5">
Volume absoluto faz São Paulo parecer “quase tudo” e o DF parecer irrelevante: isso só mede <b>tamanho</b>.
Aqui cada UF vale 100%: a matriz é a <b>composição da rede</b> (quanto da matrícula é estadual, municipal, privada).
</p>
<p style="margin:0 0 4px;font-size:13px;line-height:1.5"><b>Fórmula da taxa de PCD:</b> (alunos PCD em escola sem acessibilidade ÷ matrículas totais) × 1.000</p>
<p style="margin:0;font-size:13px;line-height:1.5">Estado de São Paulo: 50.086 ÷ 10.029.069 × 1.000 = <b>4,99</b> (50.086 alunos, não 4.990). DF: 340 ÷ 643.698 × 1.000 = <b>0,53</b>.</p>
</div>"""
        if "Distribuição territorial" in code:
            node["meta"]["code"] = """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 4px">Distribuição territorial (padronizada)</h3>
<p style="margin:0 0 8px;font-size:13px;line-height:1.5">O mapa e as barras mostram <b>matrículas por escola</b>, não o total do estado. Assim DF, RR e SP entram na mesma escala.</p>
<p style="margin:0 0 4px;font-size:13px;line-height:1.5"><b>Fórmula da taxa de PCD (não é volume em milhares):</b><br>
(alunos PCD em escola sem acessibilidade ÷ matrículas totais) × 1.000</p>
<p style="margin:0;font-size:13px;line-height:1.5">Exemplo da tabela: município de São Paulo = 10.667 ÷ 2.693.361 × 1.000 = <b>3,96</b>. São 10.667 alunos, não 3.960. O estado de SP está na aba 5: 50.086 ÷ 10.029.069 × 1.000 = <b>4,99</b>.</p>
</div>"""
        if "Indicador extra" in code:
            node["meta"]["code"] = """<div style="font-family:Inter,system-ui,sans-serif;padding:8px 16px">
<h3 style="margin:0 0 6px;color:#8a1c1c">Indicador extra · Inclusão sem acessibilidade (EISA)</h3>
<p style="margin:0;color:#4b5c6b;font-size:13px;line-height:1.5">
Escola ativa com matrícula de educação especial e <b>nenhum</b> recurso de acessibilidade.
Os KPIs nacionais continuam em volume (quantas crianças). Os gráficos por UF usam <b>percentual de escolas</b> e <b>% da educação especial sem acessibilidade</b>, senão SP e MG “ganham” só por serem grandes.
Brasil 2022: <b>25.911 escolas</b> e <b>153.726 matrículas</b> nessa condição.
</p></div>"""

    req(
        "PUT",
        "/api/v1/dashboard/10",
        token,
        {"position_json": json.dumps(pos), "published": True},
        csrf,
    )
    print("dashboard markdown updated")


if __name__ == "__main__":
    main()
