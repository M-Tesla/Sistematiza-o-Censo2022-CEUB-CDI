#!/usr/bin/env python3
"""Troca o treemap ilegível por barras empilhadas e tira travessão do painel."""

from __future__ import annotations

import http.cookiejar
import json
import urllib.request

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
    with OPENER.open(r, timeout=120) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def strip_travessao(value):
    if isinstance(value, str):
        for mark in ("\u2014", "\u2013"):
            value = value.replace(f" {mark} ", ": ").replace(mark, ": ")
        return value
    if isinstance(value, list):
        return [strip_travessao(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_travessao(item) for key, item in value.items()}
    return value


def main() -> None:
    token = req(
        "POST",
        "/api/v1/security/login",
        "",
        {"username": "admin", "password": "admin", "provider": "db", "refresh": True},
    )["access_token"]
    csrf = req("GET", "/api/v1/security/csrf_token/", token).get("result")

    n_mat = {
        "expressionType": "SQL",
        "sqlExpression": "SUM(qt_mat_bas)",
        "column": None,
        "aggregate": None,
        "hasCustomLabel": True,
        "label": "Matrículas",
        "optionName": "m_mat",
    }
    params = {
        "viz_type": "echarts_timeseries_bar",
        "datasource": "22__table",
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
        "adhoc_filters": [],
        "annotation_layers": [],
        "extra_form_data": {},
        "dashboards": [],
    }
    req(
        "PUT",
        "/api/v1/chart/115",
        token,
        {
            "slice_name": "Matrículas por região e UF",
            "viz_type": "echarts_timeseries_bar",
            "datasource_id": 22,
            "datasource_type": "table",
            "params": json.dumps(params),
            "query_context": json.dumps(
                {
                    "datasource": {"id": 22, "type": "table"},
                    "force": False,
                    "queries": [{}],
                    "form_data": params,
                    "result_format": "json",
                    "result_type": "full",
                }
            ),
        },
        csrf,
    )
    print("chart 115 agora e barras empilhadas por regiao")

    dash = req("GET", "/api/v1/dashboard/10", token)["result"]
    pos = json.loads(dash["position_json"])
    for node in pos.values():
        if not isinstance(node, dict):
            continue
        meta = node.get("meta") or {}
        if node.get("type") == "CHART" and meta.get("chartId") == 115:
            meta["height"] = 64
            meta["sliceName"] = "Matrículas por região e UF"
        if node.get("type") == "MARKDOWN":
            code = meta.get("code") or ""
            code = code.replace(
                "O ponto extra: inclusão sem acessibilidade: está na aba 3.",
                "O ponto extra, inclusão sem acessibilidade, está na aba 3.",
            )
            code = code.replace(
                "irrelevante: isso só mede",
                "irrelevante: isso só mede",
            )
            code = code.replace(
                "sem acessibilidade</b>: senão",
                "sem acessibilidade</b>, senão",
            )
            meta["code"] = code
        node["meta"] = meta

    pos = strip_travessao(pos)
    title = strip_travessao(dash.get("dashboard_title") or "Educação de Qualidade: Censo Escolar 2022")
    cert = strip_travessao(dash.get("certification_details") or "ODS 4: Educação de Qualidade")
    req(
        "PUT",
        "/api/v1/dashboard/10",
        token,
        {
            "dashboard_title": title,
            "certification_details": cert,
            "position_json": json.dumps(pos),
            "published": True,
        },
        csrf,
    )
    print("dashboard 10 atualizado")


if __name__ == "__main__":
    main()
