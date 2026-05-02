
from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle, PageBreak
from io import BytesIO
from supabase import create_client

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "asobolos.db"

MONTH_ORDER = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
MONTH_LABELS = {
    "ENE": "Enero",
    "FEB": "Febrero",
    "MAR": "Marzo",
    "ABR": "Abril",
    "MAY": "Mayo",
    "JUN": "Junio",
    "JUL": "Julio",
    "AGO": "Agosto",
    "SEP": "Septiembre",
    "OCT": "Octubre",
    "NOV": "Noviembre",
    "DIC": "Diciembre",
}
GENDER_OPTIONS = ["Hombre", "Mujer"]

st.set_page_config(page_title="Asobolos Pichincha Pro", page_icon="🎳", layout="wide")


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b0b0e;
            --panel: #151518;
            --panel-2: #1b1b20;
            --text: #f5f5f7;
            --muted: #a4a7ae;
            --accent: #ff7a1a;
            --accent-2: #ff9d57;
            --success: #21c063;
            --danger: #f04f5f;
            --border: rgba(255,255,255,.08);
        }
        .stApp { background: var(--bg); color: var(--text); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d0d11 0%, #111117 100%);
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] * { color: var(--text); }
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        h1, h2, h3 { color: var(--text); letter-spacing: -.02em; }
        .hero {
            padding: 1.2rem 1.2rem 1rem 1.2rem;
            border: 1px solid var(--border);
            border-radius: 22px;
            background:
                radial-gradient(circle at top right, rgba(255,122,26,.18), transparent 25%),
                linear-gradient(180deg, #17171b 0%, #121217 100%);
            margin-bottom: 1rem;
        }
        .mini-card, .feature-card {
            background: linear-gradient(180deg, #17171b 0%, #131318 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1rem 1rem;
            height: 100%;
            box-shadow: 0 12px 30px rgba(0,0,0,.18);
        }
        .feature-card {
            min-height: 130px;
            border-color: rgba(255,122,26,.18);
        }
        .card-title {
            font-size: 0.9rem;
            color: var(--muted);
            margin-bottom: .35rem;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .card-value {
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.1;
        }
        .card-sub {
            color: var(--muted);
            font-size: .92rem;
            margin-top: .35rem;
        }
        .section-title {
            font-size: 1rem;
            font-weight: 700;
            margin: 1rem 0 .65rem 0;
            color: var(--text);
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #17171b 0%, #131318 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: .6rem .8rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 18px;
            overflow: hidden;
        }
        div.stButton > button, .stDownloadButton button {
            border-radius: 12px;
            border: 1px solid rgba(255,122,26,.25);
            background: linear-gradient(180deg, #ff8a35 0%, #ff7a1a 100%);
            color: white;
            font-weight: 700;
        }
        div.stButton > button:hover, .stDownloadButton button:hover {
            border-color: rgba(255,122,26,.45);
            filter: brightness(1.04);
        }
        .muted { color: var(--muted); }
        .status-ok { color: var(--success); font-weight: 700; }
        .status-no { color: var(--danger); font-weight: 700; }
        .badge {
            display: inline-block;
            font-size: .78rem;
            font-weight: 700;
            padding: .18rem .52rem;
            border-radius: 999px;
            background: rgba(255,122,26,.12);
            color: var(--accent-2);
            border: 1px solid rgba(255,122,26,.18);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
            gap: 1rem;
            margin-bottom: 1.2rem;
        }
        .stat-card {
            background: linear-gradient(180deg, #17171b 0%, #131318 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: .85rem .9rem;
            min-height: 88px;
            box-shadow: 0 12px 30px rgba(0,0,0,.18);
        }
        .stat-label {
            font-size: .78rem;
            color: var(--muted);
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: .35rem;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .stat-value {
            font-size: 1.7rem;
            font-weight: 850;
            line-height: 1.05;
            color: var(--text);
            overflow-wrap: anywhere;
        }
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: .7rem;
            }
            .stat-card {
                padding: .75rem;
                min-height: 78px;
            }
            .stat-value {
                font-size: 1.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="mini-card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(title: str, desc: str, badge: str = "") -> None:
    badge_html = f'<div class="badge">{badge}</div>' if badge else ""
    st.markdown(
        f"""
        <div class="feature-card">
            {badge_html}
            <div style="height:.5rem"></div>
            <div style="font-size:1.1rem;font-weight:800;">{title}</div>
            <div class="card-sub">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def stat_card_grid(stats: list[tuple[str, str | int | float]]) -> None:
    cards = ""
    for label, value in stats:
        cards += f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
        </div>
        """

    st.markdown(
        f"""
        <div class="stats-grid">
            {cards}
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().upper()).replace(".", "")


def display_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip()).title()


def month_sort_key(month_code: str) -> int:
    try:
        return MONTH_ORDER.index(month_code)
    except ValueError:
        return 99


def compute_metrics(lines: Iterable[int | float]) -> dict[str, float]:
    vals = [int(x or 0) for x in list(lines)]
    while len(vals) < 12:
        vals.append(0)
    s1 = sum(vals[0:3])
    s2 = sum(vals[3:6])
    d1 = s1 + s2
    s3 = sum(vals[6:9])
    s4 = sum(vals[9:12])
    d2 = s3 + s4
    total = d1 + d2
    avg = round(total / 12, 2)
    return {
        "serie_1": s1,
        "serie_2": s2,
        "total_dia_1": d1,
        "serie_3": s3,
        "serie_4": s4,
        "total_dia_2": d2,
        "total_mes": total,
        "promedio_mes": avg,
        "mejor_linea": max(vals) if vals else 0,
        "peor_linea": min(vals) if vals else 0,
    }


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            sexo TEXT DEFAULT '',
            club TEXT DEFAULT '',
            categoria TEXT DEFAULT '',
            cedula TEXT DEFAULT '',
            fecha_nacimiento TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            correo TEXT DEFAULT '',
            activo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS monthly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month_code TEXT NOT NULL,
            month_name TEXT NOT NULL,
            club_snapshot TEXT DEFAULT '',
            line_1 INTEGER NOT NULL,
            line_2 INTEGER NOT NULL,
            line_3 INTEGER NOT NULL,
            line_4 INTEGER NOT NULL,
            line_5 INTEGER NOT NULL,
            line_6 INTEGER NOT NULL,
            line_7 INTEGER NOT NULL,
            line_8 INTEGER NOT NULL,
            line_9 INTEGER NOT NULL,
            line_10 INTEGER NOT NULL,
            line_11 INTEGER NOT NULL,
            line_12 INTEGER NOT NULL,
            serie_1 INTEGER NOT NULL,
            serie_2 INTEGER NOT NULL,
            total_dia_1 INTEGER NOT NULL,
            serie_3 INTEGER NOT NULL,
            serie_4 INTEGER NOT NULL,
            total_dia_2 INTEGER NOT NULL,
            total_mes INTEGER NOT NULL,
            promedio_mes REAL NOT NULL,
            mejor_linea INTEGER NOT NULL,
            peor_linea INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_id, year, month_code),
            FOREIGN KEY(player_id) REFERENCES players(id)
        );
        """
    )
    conn.commit()
    conn.close()


def upsert_player(
    name: str,
    sexo: str = "",
    club: str = "",
    categoria: str = "",
    cedula: str = "",
    fecha_nacimiento: str = "",
    telefono: str = "",
    correo: str = "",
    activo: int = 1,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    norm = normalize_name(name)
    row = cur.execute("SELECT id FROM players WHERE normalized_name = ?", (norm,)).fetchone()
    if row:
        player_id = int(row["id"])
        cur.execute(
            """
            UPDATE players
            SET display_name = ?, sexo = ?, club = ?, categoria = ?, cedula = ?,
                fecha_nacimiento = ?, telefono = ?, correo = ?, activo = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                display_name(name),
                sexo.strip(),
                club.strip(),
                categoria.strip(),
                cedula.strip(),
                fecha_nacimiento.strip(),
                telefono.strip(),
                correo.strip(),
                int(activo),
                player_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO players(normalized_name, display_name, sexo, club, categoria, cedula, fecha_nacimiento, telefono, correo, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                norm,
                display_name(name),
                sexo.strip(),
                club.strip(),
                categoria.strip(),
                cedula.strip(),
                fecha_nacimiento.strip(),
                telefono.strip(),
                correo.strip(),
                int(activo),
            ),
        )
        player_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return player_id


def update_player_by_id(
    player_id: int,
    name: str,
    sexo: str,
    club: str,
    categoria: str,
    cedula: str,
    fecha_nacimiento: str,
    telefono: str,
    correo: str,
    activo: int,
) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE players
        SET normalized_name = ?, display_name = ?, sexo = ?, club = ?, categoria = ?,
            cedula = ?, fecha_nacimiento = ?, telefono = ?, correo = ?, activo = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            normalize_name(name),
            display_name(name),
            sexo.strip(),
            club.strip(),
            categoria.strip(),
            cedula.strip(),
            fecha_nacimiento.strip(),
            telefono.strip(),
            correo.strip(),
            int(activo),
            int(player_id),
        ),
    )
    conn.commit()
    conn.close()



def delete_monthly_result(player_id: int, year: int, month_code: str) -> None:
    conn = get_conn()
    conn.execute(
        "DELETE FROM monthly_results WHERE player_id = ? AND year = ? AND month_code = ?",
        (int(player_id), int(year), month_code),
    )
    conn.commit()
    conn.close()


def save_monthly_result(player_id: int, year: int, month_code: str, club_snapshot: str, lines: list[int], notes: str = "") -> None:
    m = compute_metrics(lines)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO monthly_results (
            player_id, year, month_code, month_name, club_snapshot,
            line_1, line_2, line_3, line_4, line_5, line_6,
            line_7, line_8, line_9, line_10, line_11, line_12,
            serie_1, serie_2, total_dia_1, serie_3, serie_4, total_dia_2,
            total_mes, promedio_mes, mejor_linea, peor_linea, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(player_id, year, month_code) DO UPDATE SET
            month_name = excluded.month_name,
            club_snapshot = excluded.club_snapshot,
            line_1 = excluded.line_1, line_2 = excluded.line_2, line_3 = excluded.line_3,
            line_4 = excluded.line_4, line_5 = excluded.line_5, line_6 = excluded.line_6,
            line_7 = excluded.line_7, line_8 = excluded.line_8, line_9 = excluded.line_9,
            line_10 = excluded.line_10, line_11 = excluded.line_11, line_12 = excluded.line_12,
            serie_1 = excluded.serie_1, serie_2 = excluded.serie_2, total_dia_1 = excluded.total_dia_1,
            serie_3 = excluded.serie_3, serie_4 = excluded.serie_4, total_dia_2 = excluded.total_dia_2,
            total_mes = excluded.total_mes, promedio_mes = excluded.promedio_mes,
            mejor_linea = excluded.mejor_linea, peor_linea = excluded.peor_linea,
            notes = excluded.notes, updated_at = CURRENT_TIMESTAMP
        """,
        (
            int(player_id), int(year), month_code, MONTH_LABELS.get(month_code, month_code), club_snapshot,
            *[int(v) for v in lines],
            int(m["serie_1"]), int(m["serie_2"]), int(m["total_dia_1"]),
            int(m["serie_3"]), int(m["serie_4"]), int(m["total_dia_2"]),
            int(m["total_mes"]), float(m["promedio_mes"]), int(m["mejor_linea"]), int(m["peor_linea"]),
            notes.strip(),
        ),
    )
    conn.commit()
    conn.close()


def get_existing_result(player_id: int, year: int, month_code: str) -> sqlite3.Row | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM monthly_results WHERE player_id = ? AND year = ? AND month_code = ?",
        (int(player_id), int(year), month_code),
    ).fetchone()
    conn.close()
    return row


@st.cache_data(show_spinner=False)
def load_players_df() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM players ORDER BY sexo, display_name", conn)
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def load_results_df() -> pd.DataFrame:
    conn = get_conn()
    query = """
        SELECT r.*, p.display_name AS jugador, p.sexo, p.club AS club_actual, p.categoria,
               p.cedula, p.fecha_nacimiento, p.telefono, p.correo, p.activo
        FROM monthly_results r
        JOIN players p ON p.id = r.player_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if df.empty:
        return df
    df["month_order"] = df["month_code"].map(month_sort_key)
    return df.sort_values(["year", "month_order", "sexo", "jugador"]).reset_index(drop=True)


def build_season_ranking(df: pd.DataFrame, year: int) -> tuple[pd.DataFrame, int, int]:
    subset = df[df["year"] == year].copy()
    if subset.empty:
        return pd.DataFrame(), 0, 0
    total_months = subset[["year", "month_code"]].drop_duplicates().shape[0]
    required_months = max(1, math.ceil(total_months * 0.8))
    g = subset.groupby(["player_id", "jugador", "sexo", "club_actual", "categoria"], as_index=False).agg(
        meses_jugados=("id", "count"),
        pines=("total_mes", "sum"),
        promedio=("promedio_mes", lambda s: round(float(s.mean()), 2)),
        mejor_linea=("mejor_linea", "max"),
        mejor_mes=("total_mes", "max"),
        regularidad=("promedio_mes", lambda s: round(float(s.std(ddof=0)) if len(s) > 1 else 0, 2)),
    )
    g["meses_disputados"] = total_months
    g["meses_minimos"] = required_months
    g["cumplimiento_pct"] = (g["meses_jugados"] / total_months * 100).round(1)
    g["elegible_nacional"] = g["meses_jugados"] >= required_months
    g["estado"] = g["elegible_nacional"].map({True: "Elegible", False: "No elegible"})
    frames = []
    for sexo in GENDER_OPTIONS:
        sec = g[g["sexo"] == sexo].copy()
        if sec.empty:
            continue
        sec = sec.sort_values(["promedio", "pines", "mejor_linea"], ascending=[False, False, False]).reset_index(drop=True)
        sec["orden_general"] = range(1, len(sec) + 1)
        sec["ranking_general"] = sec["orden_general"]
        sec["ranking_oficial"] = pd.Series([None] * len(sec), dtype="object")
        eligible = sec[sec["elegible_nacional"]].copy().sort_values(
            ["promedio", "pines", "mejor_linea"], ascending=[False, False, False]
        ).reset_index()
        for pos, row in enumerate(eligible.itertuples(index=False), start=1):
            sec.at[int(row.index), "ranking_oficial"] = int(pos)
        frames.append(sec)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), total_months, required_months


def month_ranking(df: pd.DataFrame, year: int, month_code: str, sexo: str) -> pd.DataFrame:
    subset = df[(df["year"] == year) & (df["month_code"] == month_code) & (df["sexo"] == sexo)].copy()
    if subset.empty:
        return subset
    subset = subset.sort_values(["promedio_mes", "total_mes", "mejor_linea"], ascending=[False, False, False]).reset_index(drop=True)
    subset["ranking"] = range(1, len(subset) + 1)
    cols = ["ranking", "jugador", "club_actual", "categoria", "serie_1", "serie_2", "total_dia_1", "serie_3", "serie_4", "total_dia_2", "total_mes", "promedio_mes", "mejor_linea"]
    return subset[cols]


def player_history(df: pd.DataFrame, player_id: int) -> pd.DataFrame:
    hist = df[df["player_id"] == player_id].copy()
    if hist.empty:
        return hist
    return hist.sort_values(["year", "month_order"]).reset_index(drop=True)



def admin_login_box() -> bool:
    with st.sidebar:
        st.markdown("## 🔐 Acceso administrador")
        st.markdown('<div class="muted">La vista pública queda abierta para consulta.</div>', unsafe_allow_html=True)

        if st.session_state.get("is_admin", False):
            st.success("Sesión admin activa")
            if st.button("Cerrar sesión admin", key="admin_logout_btn"):
                st.session_state["is_admin"] = False
                st.session_state["dashboard_target_page"] = "Vista pública"
                st.rerun()
            return True

        password = st.text_input("Clave admin", type="password", key="admin_password_input")
        if st.button("Ingresar como admin", key="admin_login_btn"):
            if password == st.secrets.get("ADMIN_PASSWORD", ""):
                st.session_state["is_admin"] = True
                st.session_state["dashboard_target_page"] = "Dashboard"
                st.rerun()
            else:
                st.error("Clave incorrecta.")
        return False


def sidebar_admin() -> None:
    with st.sidebar:
        st.markdown("## 🎳 Asobolos Pro")
        st.markdown('<div class="muted">Ranking · jugadores · análisis</div>', unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Limpiar caché visual"):
            load_players_df.clear()
            load_results_df.clear()
            st.success("Caché refrescada.")


def apply_eligibility_view(
    ranking_df: pd.DataFrame,
    mode: str,
    eligibility_filter: str,
) -> pd.DataFrame:
    if ranking_df.empty:
        return ranking_df

    df = ranking_df.copy()
    if eligibility_filter == "Solo elegibles":
        df = df[df["elegible_nacional"] == True].copy()
    elif eligibility_filter == "Solo no elegibles":
        df = df[df["elegible_nacional"] == False].copy()

    if mode == "Oficial":
        df = df[df["elegible_nacional"] == True].copy()
        df = df.sort_values(["ranking_oficial", "promedio", "pines"], ascending=[True, False, False])
    else:
        df = df.sort_values(["ranking_general", "promedio", "pines"], ascending=[True, False, False])

    return df.reset_index(drop=True)



def go_to_page(page_name: str) -> None:
    st.session_state["dashboard_target_page"] = page_name


def page_dashboard(results_df: pd.DataFrame, players_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="badge">Panel Oficial</div>
            <h1 style="margin:.5rem 0 0 0;">Dashboard de Ranking Asobolos Pichincha</h1>
            <div class="muted">Vista moderna inspirada en panel competitivo, adaptada a hombres, mujeres, elegibilidad y rendimiento mensual.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if results_df.empty:
        a, b, c = st.columns(3)
        with a: card("Jugadores inscritos", str(players_df.shape[0]), "Crea fichas primero")
        with b: card("Registros mensuales", "0", "Todavía no hay líneas cargadas")
        with c: card("Temporada activa", "-", "Sin datos")
        st.info("Empieza registrando jugadores y luego carga el primer mes.")
        return

    latest_year = int(results_df["year"].max())
    season_ranking, total_months, required_months = build_season_ranking(results_df, latest_year)
    men = players_df[players_df["sexo"] == "Hombre"].shape[0] if not players_df.empty else 0
    women = players_df[players_df["sexo"] == "Mujer"].shape[0] if not players_df.empty else 0
    avg = round(float(results_df[results_df["year"] == latest_year]["promedio_mes"].mean()), 2)
    high = int(results_df[results_df["year"] == latest_year]["mejor_linea"].max())

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Temporada", str(latest_year), f"{total_months} meses disputados")
    with c2: card("Hombres", str(men), "Fichas inscritas")
    with c3: card("Mujeres", str(women), "Fichas inscritas")
    with c4: card("Promedio general", f"{avg:.2f}", "Temporada actual")
    with c5: card("Línea más alta", str(high), "Mejor línea del año")

    st.markdown('<div class="section-title">Accesos rápidos</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        feature_card("Inscribir jugadores", "Crear o editar fichas con sexo, club, categoría y datos de contacto.", "Jugadores")
        if st.button("Abrir Jugadores", key="go_players"):
            go_to_page("Jugadores")
            st.rerun()
    with f2:
        feature_card("Ingresar resultados", "Cargar 12 líneas por mes, con previsualización antes de guardar.", "Mensual")
        if st.button("Abrir Ingreso mensual", key="go_entry"):
            go_to_page("Ingreso mensual")
            st.rerun()
    with f3:
        feature_card("Editar líneas", "Corregir registros ya guardados y recalcular series y totales.", "Corrección")
        if st.button("Abrir Ficha del jugador", key="go_profile"):
            go_to_page("Ficha del jugador")
            st.rerun()
    with f4:
        feature_card("Acumulado oficial", f"Regla activa: mínimo {required_months}/{total_months} meses para nacionales.", "80%")
        if st.button("Abrir Reportes", key="go_reports"):
            go_to_page("Reportes")
            st.rerun()

    f5, f6 = st.columns(2)
    with f5:
        feature_card("Ranking mensual", "Consulta posiciones por mes, sección y rendimiento.", "Ranking")
        if st.button("Abrir Ranking mensual", key="go_monthly_ranking"):
            go_to_page("Ranking mensual")
            st.rerun()
    with f6:
        feature_card("Vista pública", "Consulta pública de rankings y fichas deportivas.", "Público")
        if st.button("Abrir Vista pública", key="go_public"):
            go_to_page("Vista pública")
            st.rerun()

    st.markdown('<div class="section-title">Analítica de temporada</div>', unsafe_allow_html=True)
    filt1, filt2, filt3 = st.columns(3)
    with filt1:
        sexo = st.selectbox("Sección", GENDER_OPTIONS, key="dash_gender")
    with filt2:
        ranking_mode = st.selectbox("Modo de ranking", ["Oficial", "General"], key="dash_mode")
    with filt3:
        eligibility_filter = st.selectbox("Filtro de elegibilidad", ["Todos", "Solo elegibles", "Solo no elegibles"], key="dash_eligibility")
    sec = results_df[(results_df["year"] == latest_year) & (results_df["sexo"] == sexo)].copy()
    if sec.empty:
        st.info(f"No hay resultados cargados para {sexo}.")
        return

    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.markdown("#### Tendencia de promedio por jugador")
        trend = sec.groupby("jugador", as_index=False)["promedio_mes"].mean().sort_values("promedio_mes", ascending=False).head(10)
        trend.columns = ["Jugador", "Promedio"]
        st.bar_chart(trend.set_index("Jugador"))
    with col_b:
        st.markdown("#### Distribución de líneas")
        lines = []
        for i in range(1, 13):
            lines.extend(sec[f"line_{i}"].astype(int).tolist())
        bins = pd.cut(pd.Series(lines), bins=[0, 149, 169, 189, 209, 229, 300], include_lowest=True)
        dist = bins.value_counts().sort_index().rename_axis("Rango").reset_index(name="Cantidad")
        dist["Rango"] = dist["Rango"].astype(str)
        st.bar_chart(dist.set_index("Rango"))

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("#### Top 10 rendimiento mensual")
        top = sec.sort_values(["promedio_mes", "total_mes"], ascending=[False, False])[["jugador", "month_name", "promedio_mes", "total_mes"]].head(10)
        top.columns = ["Jugador", "Mes", "Promedio", "Total"]
        st.dataframe(top, use_container_width=True, hide_index=True)
    with col_d:
        st.markdown("#### Elegibilidad a nacionales")
        eligibility = season_ranking[season_ranking["sexo"] == sexo][["ranking_oficial", "orden_general", "jugador", "meses_jugados", "meses_minimos", "cumplimiento_pct", "promedio", "estado"]]
        st.dataframe(eligibility, use_container_width=True, hide_index=True)


def page_player_registration(players_df: pd.DataFrame) -> None:
    st.title("👥 Inscripción de jugadores")
    st.caption("Crea fichas nuevas o edita fichas existentes. El sexo definido aquí separa rankings y acumulados.")

    mode = "Nuevo jugador"
    selected_row = None
    selected_player_id = None

    if not players_df.empty:
        mode = st.radio("Modo", ["Nuevo jugador", "Editar jugador inscrito"], horizontal=True)
        if mode == "Editar jugador inscrito":
            sexo_edit = st.selectbox("Sexo", GENDER_OPTIONS, key="players_edit_gender")
            sec = players_df[players_df["sexo"] == sexo_edit].copy()
            if not sec.empty:
                options = {f"{r['display_name']} | {r['club']}": int(r['id']) for _, r in sec.iterrows()}
                pick = st.selectbox("Jugador", list(options.keys()), key="players_edit_pick")
                selected_player_id = options[pick]
                selected_row = sec[sec["id"] == selected_player_id].iloc[0]

    c1, c2 = st.columns(2)
    with c1:
        jugador = st.text_input("Nombres y apellidos", value=str(selected_row["display_name"]) if selected_row is not None else "")
        sexo = st.selectbox("Sexo", ["", *GENDER_OPTIONS], index=(["", *GENDER_OPTIONS].index(str(selected_row["sexo"])) if selected_row is not None else 0), format_func=lambda x: x or "Selecciona una opción")
        club = st.text_input("Club", value=str(selected_row["club"]) if selected_row is not None else "")
        categoria = st.text_input("Categoría", value=str(selected_row["categoria"]) if selected_row is not None else "")
        cedula = st.text_input("Cédula", value=str(selected_row["cedula"]) if selected_row is not None else "")
    with c2:
        fecha_nacimiento = st.text_input("Fecha de nacimiento", value=str(selected_row["fecha_nacimiento"]) if selected_row is not None else "")
        telefono = st.text_input("Teléfono", value=str(selected_row["telefono"]) if selected_row is not None else "")
        correo = st.text_input("Correo", value=str(selected_row["correo"]) if selected_row is not None else "")
        activo = st.checkbox("Jugador activo", value=bool(selected_row["activo"]) if selected_row is not None else True)

    if st.button("Guardar ficha", type="primary"):
        if not jugador.strip():
            st.error("Ingresa el nombre del jugador.")
        elif not sexo:
            st.error("Selecciona Hombre o Mujer.")
        else:
            if selected_player_id:
                update_player_by_id(selected_player_id, jugador, sexo, club, categoria, cedula, fecha_nacimiento, telefono, correo, 1 if activo else 0)
                st.success(f"Ficha actualizada: {display_name(jugador)}")
            else:
                upsert_player(jugador, sexo, club, categoria, cedula, fecha_nacimiento, telefono, correo, 1 if activo else 0)
                st.success(f"Ficha creada: {display_name(jugador)}")
            load_players_df.clear()
            load_results_df.clear()

    st.markdown("### Listado")
    if players_df.empty:
        st.info("Todavía no hay jugadores inscritos.")
    else:
        sexo_table = st.selectbox("Ver listado de", GENDER_OPTIONS, key="players_table_gender")
        sec = players_df[players_df["sexo"] == sexo_table].copy()
        view = sec[["display_name", "club", "categoria", "cedula", "telefono", "correo", "activo"]].copy()
        view.columns = ["Jugador", "Club", "Categoría", "Cédula", "Teléfono", "Correo", "Activo"]
        view["Activo"] = view["Activo"].map({1: "Sí", 0: "No"})
        st.dataframe(view, use_container_width=True, hide_index=True)


def page_entry(players_df: pd.DataFrame, results_df: pd.DataFrame) -> None:
    st.title("📝 Ingreso mensual")
    st.caption("Selecciona el jugador y valida los cálculos antes de guardar.")

    if st.session_state.get("clear_new_entry", False):
        for i in range(1, 13):
            st.session_state[f"new_line_{i}"] = 0
        st.session_state["notes"] = ""
        st.session_state["clear_new_entry"] = False

    if st.session_state.get("last_save_message"):
        st.success(st.session_state["last_save_message"])
        st.session_state["last_save_message"] = ""

    tab_new, tab_edit = st.tabs(["Nuevo registro", "Editar líneas"])

    with tab_new:
        left, right = st.columns([1.05, 1])
        with left:
            player_id = None
            if players_df.empty:
                st.warning("No hay jugadores inscritos. Crea primero la ficha del jugador.")
                jugador = st.text_input("Nombre del jugador")
                sexo = st.selectbox("Sexo", ["", *GENDER_OPTIONS], format_func=lambda x: x or "Selecciona una opción")
                club = st.text_input("Club")
                categoria = st.text_input("Categoría")
                cedula = fecha_nacimiento = telefono = correo = ""
            else:
                sexo_filtro = st.selectbox("Sexo", GENDER_OPTIONS, key="entry_gender")
                sec = players_df[(players_df["sexo"] == sexo_filtro) & (players_df["activo"] == 1)].copy()
                if sec.empty:
                    st.info(f"No hay jugadores activos en {sexo_filtro}.")
                    return
                options = {f"{r['display_name']} | {r['club']}": int(r['id']) for _, r in sec.iterrows()}
                pick = st.selectbox("Jugador", list(options.keys()), key="entry_pick")
                player_id = options[pick]
                row = sec[sec["id"] == player_id].iloc[0]
                jugador = str(row["display_name"])
                sexo = str(row["sexo"])
                club = str(row["club"])
                categoria = str(row["categoria"])
                cedula = str(row["cedula"])
                fecha_nacimiento = str(row["fecha_nacimiento"])
                telefono = str(row["telefono"])
                correo = str(row["correo"])

            year = st.number_input("Año", min_value=2024, max_value=2035, value=2025, step=1)
            month_code = st.selectbox("Mes", MONTH_ORDER, format_func=lambda m: MONTH_LABELS[m])
            notes = st.text_area("Notas", key="notes")

            st.markdown("#### Ficha cargada automáticamente")
            i1, i2, i3, i4 = st.columns(4)
            i1.text_input("Jugador", value=jugador, disabled=True)
            i2.text_input("Sexo", value=sexo, disabled=True)
            i3.text_input("Club", value=club, disabled=True)
            i4.text_input("Categoría", value=categoria, disabled=True)
            j1, j2, j3 = st.columns(3)
            j1.text_input("Cédula", value=cedula, disabled=True)
            j2.text_input("Nacimiento", value=fecha_nacimiento, disabled=True)
            j3.text_input("Teléfono", value=telefono, disabled=True)
            st.text_input("Correo", value=correo, disabled=True)

            if player_id is not None and get_existing_result(player_id, int(year), month_code):
                st.warning(f"Ya existe un registro para {jugador} en {MONTH_LABELS[month_code]} {year}. Si guardas, se actualizará.")

        with right:
            st.markdown("#### Día 1")
            a1, a2, a3 = st.columns(3)
            linea_1 = a1.number_input("Línea 1", 0, 300, 0, 1, key="new_line_1")
            linea_2 = a2.number_input("Línea 2", 0, 300, 0, 1, key="new_line_2")
            linea_3 = a3.number_input("Línea 3", 0, 300, 0, 1, key="new_line_3")

            a4, a5, a6 = st.columns(3)
            linea_4 = a4.number_input("Línea 4", 0, 300, 0, 1, key="new_line_4")
            linea_5 = a5.number_input("Línea 5", 0, 300, 0, 1, key="new_line_5")
            linea_6 = a6.number_input("Línea 6", 0, 300, 0, 1, key="new_line_6")

            day1 = [linea_1, linea_2, linea_3, linea_4, linea_5, linea_6]

            st.markdown("#### Día 2")
            b1, b2, b3 = st.columns(3)
            linea_7 = b1.number_input("Línea 7", 0, 300, 0, 1, key="new_line_7")
            linea_8 = b2.number_input("Línea 8", 0, 300, 0, 1, key="new_line_8")
            linea_9 = b3.number_input("Línea 9", 0, 300, 0, 1, key="new_line_9")

            b4, b5, b6 = st.columns(3)
            linea_10 = b4.number_input("Línea 10", 0, 300, 0, 1, key="new_line_10")
            linea_11 = b5.number_input("Línea 11", 0, 300, 0, 1, key="new_line_11")
            linea_12 = b6.number_input("Línea 12", 0, 300, 0, 1, key="new_line_12")

            day2 = [linea_7, linea_8, linea_9, linea_10, linea_11, linea_12]

        lines = [int(v) for v in (day1 + day2)]
        m = compute_metrics(lines)
        st.markdown("### Previsualización")
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Serie 1", m["serie_1"])
        x2.metric("Serie 2", m["serie_2"])
        x3.metric("Total Día 1", m["total_dia_1"])
        x4.metric("Promedio Día 1", f"{m['total_dia_1']/6:.2f}")
        y1, y2, y3, y4 = st.columns(4)
        y1.metric("Serie 3", m["serie_3"])
        y2.metric("Serie 4", m["serie_4"])
        y3.metric("Total Día 2", m["total_dia_2"])
        y4.metric("Promedio Día 2", f"{m['total_dia_2']/6:.2f}")
        z1, z2, z3, z4 = st.columns(4)
        z1.metric("Total del mes", m["total_mes"])
        z2.metric("Promedio del mes", f"{m['promedio_mes']:.2f}")
        z3.metric("Mejor línea", m["mejor_linea"])
        z4.metric("Peor línea", m["peor_linea"])

        preview = pd.DataFrame({
            "Bloque": ["Serie 1", "Serie 2", "Día 1", "Serie 3", "Serie 4", "Día 2", "Mes"],
            "Detalle": [
                f"{lines[0]} + {lines[1]} + {lines[2]}",
                f"{lines[3]} + {lines[4]} + {lines[5]}",
                f"{m['serie_1']} + {m['serie_2']}",
                f"{lines[6]} + {lines[7]} + {lines[8]}",
                f"{lines[9]} + {lines[10]} + {lines[11]}",
                f"{m['serie_3']} + {m['serie_4']}",
                f"{m['total_dia_1']} + {m['total_dia_2']}",
            ],
            "Total": [m["serie_1"], m["serie_2"], m["total_dia_1"], m["serie_3"], m["serie_4"], m["total_dia_2"], m["total_mes"]],
        })
        st.dataframe(preview, use_container_width=True, hide_index=True)

        if st.button("Guardar registro mensual", type="primary"):
            if player_id is None:
                st.error("Selecciona un jugador inscrito.")
            else:
                save_monthly_result(player_id, int(year), month_code, club.strip().upper(), lines, notes=notes)
                load_results_df.clear()
                st.session_state["clear_new_entry"] = True
                st.session_state["last_save_message"] = f"Registro guardado para {jugador} en {MONTH_LABELS[month_code]} {year}."
                st.rerun()

    with tab_edit:
        if results_df.empty or players_df.empty:
            st.info("No hay registros mensuales para editar.")
            return
        sexo_edit = st.selectbox("Sexo", GENDER_OPTIONS, key="edit_gender")
        sec_results = results_df[results_df["sexo"] == sexo_edit].copy()
        sec_players = players_df[players_df["sexo"] == sexo_edit].copy()
        if sec_results.empty or sec_players.empty:
            st.info(f"No hay datos en {sexo_edit}.")
            return
        options = {f"{r['display_name']} | {r['club']}": int(r['id']) for _, r in sec_players.iterrows()}
        pick = st.selectbox("Jugador", list(options.keys()), key="edit_pick")
        player_id = options[pick]
        hist = sec_results[sec_results["player_id"] == player_id].copy()
        if hist.empty:
            st.info("Ese jugador todavía no tiene resultados.")
            return
        year = st.selectbox("Año", sorted(hist["year"].unique()), key="edit_year")
        months = sorted(hist[hist["year"] == year]["month_code"].unique(), key=month_sort_key)
        month_code = st.selectbox("Mes", months, format_func=lambda m: MONTH_LABELS[m], key="edit_month")
        row = hist[(hist["year"] == year) & (hist["month_code"] == month_code)].iloc[0]

        for i in range(1, 13):
            st.session_state.setdefault(f"line_edit_{i}", int(row[f"line_{i}"]))
        st.session_state.setdefault("notes_edit", str(row["notes"] or ""))

        if st.button("Cargar registro", key="load_edit"):
            for i in range(1, 13):
                st.session_state[f"line_edit_{i}"] = int(row[f"line_{i}"])
            st.session_state["notes_edit"] = str(row["notes"] or "")

        pinfo = sec_players[sec_players["id"] == player_id].iloc[0]
        info1, info2, info3, info4 = st.columns(4)
        info1.text_input("Jugador", value=str(pinfo["display_name"]), disabled=True, key="edit_info_player")
        info2.text_input("Club", value=str(pinfo["club"]), disabled=True, key="edit_info_club")
        info3.text_input("Sexo", value=str(pinfo["sexo"]), disabled=True, key="edit_info_gender")
        info4.text_input("Categoría", value=str(pinfo["categoria"]), disabled=True, key="edit_info_cat")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Día 1")
            e1, e2, e3 = st.columns(3)
            el1 = e1.number_input("Línea 1", 0, 300, step=1, key="line_edit_1")
            el2 = e2.number_input("Línea 2", 0, 300, step=1, key="line_edit_2")
            el3 = e3.number_input("Línea 3", 0, 300, step=1, key="line_edit_3")

            e4, e5, e6 = st.columns(3)
            el4 = e4.number_input("Línea 4", 0, 300, step=1, key="line_edit_4")
            el5 = e5.number_input("Línea 5", 0, 300, step=1, key="line_edit_5")
            el6 = e6.number_input("Línea 6", 0, 300, step=1, key="line_edit_6")

            edit_day1 = [el1, el2, el3, el4, el5, el6]
        with c2:
            st.markdown("#### Día 2")
            f1, f2, f3 = st.columns(3)
            el7 = f1.number_input("Línea 7", 0, 300, step=1, key="line_edit_7")
            el8 = f2.number_input("Línea 8", 0, 300, step=1, key="line_edit_8")
            el9 = f3.number_input("Línea 9", 0, 300, step=1, key="line_edit_9")

            f4, f5, f6 = st.columns(3)
            el10 = f4.number_input("Línea 10", 0, 300, step=1, key="line_edit_10")
            el11 = f5.number_input("Línea 11", 0, 300, step=1, key="line_edit_11")
            el12 = f6.number_input("Línea 12", 0, 300, step=1, key="line_edit_12")

            edit_day2 = [el7, el8, el9, el10, el11, el12]

        edit_lines = [int(v) for v in (edit_day1 + edit_day2)]
        em = compute_metrics(edit_lines)
        st.text_area("Notas", key="notes_edit")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Serie 1", em["serie_1"])
        g2.metric("Serie 2", em["serie_2"])
        g3.metric("Total Día 1", em["total_dia_1"])
        g4.metric("Promedio Día 1", f"{em['total_dia_1']/6:.2f}")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Serie 3", em["serie_3"])
        h2.metric("Serie 4", em["serie_4"])
        h3.metric("Total Día 2", em["total_dia_2"])
        h4.metric("Promedio Día 2", f"{em['total_dia_2']/6:.2f}")
        i1, i2, i3 = st.columns(3)
        i1.metric("Total del mes", em["total_mes"])
        i2.metric("Promedio del mes", f"{em['promedio_mes']:.2f}")
        i3.metric("Mejor línea", em["mejor_linea"])

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button("Guardar cambios", type="primary", key="save_edit"):
                save_monthly_result(player_id, int(year), month_code, str(pinfo["club"]).strip().upper(), edit_lines, notes=st.session_state["notes_edit"])
                load_results_df.clear()
                st.success(f"Registro actualizado para {pinfo['display_name']} en {MONTH_LABELS[month_code]} {year}.")
                st.rerun()

        with action_col2:
            confirm_delete = st.checkbox(
                f"Confirmo eliminar {MONTH_LABELS[month_code]} {year} de {pinfo['display_name']}",
                key="confirm_delete_monthly"
            )
            if st.button("Eliminar registro mensual", key="delete_monthly_record") and confirm_delete:
                delete_monthly_result(player_id, int(year), month_code)
                load_results_df.clear()
                st.success(f"Registro eliminado: {pinfo['display_name']} - {MONTH_LABELS[month_code]} {year}.")
                st.rerun()


def page_monthly_ranking(df: pd.DataFrame) -> None:
    st.title("🏆 Ranking mensual")
    if df.empty:
        st.info("No hay resultados todavía.")
        return
    year = st.selectbox("Año", sorted(df["year"].unique()), index=len(sorted(df["year"].unique())) - 1)
    month_code = st.selectbox("Mes", sorted(df[df["year"] == year]["month_code"].unique(), key=month_sort_key), format_func=lambda m: MONTH_LABELS[m])
    sexo = st.selectbox("Sección", GENDER_OPTIONS)
    table = month_ranking(df, int(year), month_code, sexo)
    if table.empty:
        st.info("No hay datos para ese filtro.")
        return
    top = table.iloc[0]
    a, b, c = st.columns(3)
    with a: card("Líder mensual", str(top["jugador"]), f"{top['promedio_mes']:.2f} de promedio")
    with b: card("Mejor total", str(int(table['total_mes'].max())), MONTH_LABELS[month_code])
    with c: card("Jugadores", str(table.shape[0]), sexo)
    st.dataframe(table, use_container_width=True, hide_index=True)




def build_report_table(
    results_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    sexo: str,
    year: int,
    ranking_mode: str,
    selected_columns: list[str],
) -> pd.DataFrame:
    month_subset = results_df[(results_df["year"] == year) & (results_df["sexo"] == sexo)].copy()
    months_present = sorted(month_subset["month_code"].dropna().unique().tolist(), key=month_sort_key) if not month_subset.empty else []

    month_pivot = pd.DataFrame()
    if not month_subset.empty:
        month_pivot = month_subset.pivot_table(
            index="jugador",
            columns="month_code",
            values="total_mes",
            aggfunc="max"
        ).reset_index()
        for m in months_present:
            if m not in month_pivot.columns:
                month_pivot[m] = None
        month_pivot = month_pivot[["jugador", *months_present]]

    base = ranking_df.copy()
    if ranking_mode == "Oficial":
        base["Ranking"] = base["ranking_oficial"]
    else:
        base["Ranking"] = base["ranking_general"]

    if not month_pivot.empty:
        base = base.merge(month_pivot, on="jugador", how="left")

    col_map = {
        "Ranking": "Ranking",
        "Jugador": "jugador",
        "Club": "club_actual",
        "Categoría": "categoria",
        "Meses jugados": "meses_jugados",
        "% cumplimiento": "cumplimiento_pct",
        "Promedio": "promedio",
        "Mejor línea": "mejor_linea",
        "Regularidad": "regularidad",
        "Estado": "estado",
    }

    cols = []
    renamed = {}
    for label in selected_columns:
        if label in col_map:
            cols.append(col_map[label])
            renamed[col_map[label]] = label

    for m in months_present:
        cols.append(m)
        renamed[m] = MONTH_LABELS.get(m, m)

    cols.append("pines")
    renamed["pines"] = "Total acumulado"

    cols = [c for c in cols if c in base.columns]
    out = base[cols].copy().rename(columns=renamed)

    if "Ranking" in out.columns:
        out["Ranking"] = out["Ranking"].fillna("")

    month_names = [MONTH_LABELS.get(m, m) for m in months_present]
    for c in month_names + ["Total acumulado", "Meses jugados", "Mejor línea"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda x: "" if pd.isna(x) else int(float(x)) if str(x).replace(".", "", 1).isdigit() else x)

    for c in ["% cumplimiento", "Promedio", "Regularidad"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda x: "" if pd.isna(x) else round(float(x), 2))

    return out


def _pdf_table_from_df(df: pd.DataFrame) -> Table:
    table_df = df.copy()
    for col in table_df.columns:
        table_df[col] = table_df[col].apply(lambda x: "" if pd.isna(x) else str(x))

    data = [list(table_df.columns)] + table_df.values.tolist()
    available_width = landscape(A4)[0] - 28
    widths = []
    for col in table_df.columns:
        if col in ["Jugador"]:
            widths.append(140)
        elif col in ["Club", "Categoría", "Sección"]:
            widths.append(82)
        elif col in ["Estado"]:
            widths.append(70)
        elif col in MONTH_LABELS.values():
            widths.append(46)
        elif col in ["Ranking", "Ranking Oficial", "Ranking General", "Meses jugados", "Mejor línea"]:
            widths.append(42)
        elif col in ["% cumplimiento", "Promedio", "Regularidad", "Total acumulado"]:
            widths.append(58)
        else:
            widths.append(52)
    scale = min(1.0, available_width / max(sum(widths), 1))
    widths = [round(w * scale, 2) for w in widths]
    table = Table(data, repeatRows=1, colWidths=widths)
    body_font = 7 if len(table_df.columns) <= 12 else 6
    head_font = 7 if len(table_df.columns) <= 12 else 6.2
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF7A1A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), head_font),
        ("FONTSIZE", (0, 1), (-1, -1), body_font),
        ("LEADING", (0, 0), (-1, -1), body_font + 1),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFCFCF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#F7F7F7")]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
    ]
    for idx, col in enumerate(table_df.columns):
        if col in ["Jugador", "Club", "Categoría", "Sección"]:
            style_cmds.append(("ALIGN", (idx, 1), (idx, -1), "LEFT"))
    table.setStyle(TableStyle(style_cmds))
    return table


def build_accumulated_pdf(
    report_tables: list[tuple[str, pd.DataFrame]],
    year: int,
    scope_label: str,
    total_months: int,
    required_months: int,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=14,
        rightMargin=14,
        topMargin=18,
        bottomMargin=18,
    )
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"<b>ASOBOLOS PICHINCHA - REPORTE ACUMULADO {scope_label.upper()} {year}</b>", styles["Title"])
    subtitle = Paragraph(
        f"Temporada {year} | Meses jugados en la temporada: {total_months} | "
        f"Regla de elegibilidad: minimo {required_months} meses jugados para nacionales",
        styles["Normal"],
    )
    story.extend([title, Spacer(1, 8), subtitle, Spacer(1, 10)])

    for idx, (label, df) in enumerate(report_tables):
        story.append(Paragraph(f"<b>{label}</b>", styles["Heading3"]))
        story.append(Spacer(1, 6))
        if df.empty:
            story.append(Paragraph("Sin datos para esta sección.", styles["Normal"]))
        else:
            story.append(_pdf_table_from_df(df))
        story.append(Spacer(1, 12))
        if len(report_tables) > 1 and idx < len(report_tables) - 1:
            story.append(PageBreak())

    story.append(Paragraph("Emitido desde el sistema de ranking Asobolos Pichincha.", styles["Italic"]))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_player_summary(player_row: pd.Series, hist: pd.DataFrame, results_df: pd.DataFrame) -> dict:
    if hist.empty:
        return {
            "promedio_general": 0.0,
            "mejor_linea": 0,
            "mejor_mes": 0,
            "meses_jugados": 0,
            "total_acumulado": 0,
            "mejor_anio": "-",
            "elegibilidad": "-",
            "mejor_serie_3": 0,
            "mejor_serie_6": 0,
        }

    latest_year = int(hist["year"].max())
    ranking, total_months, required_months = build_season_ranking(results_df, latest_year)
    row = ranking[ranking["player_id"] == int(player_row["id"])]
    elegibilidad = "-"
    if not row.empty:
        r = row.iloc[0]
        elegibilidad = f'{r["estado"]} ({int(r["meses_jugados"])}/{int(r["meses_minimos"])})'

    yearly = hist.groupby("year", as_index=False).agg(
        promedio=("promedio_mes", "mean"),
        total=("total_mes", "sum"),
    ).sort_values(["promedio", "total"], ascending=[False, False])

    best_year = str(int(yearly.iloc[0]["year"])) if not yearly.empty else "-"

    best_3 = int(
        max(
            hist["serie_1"].max(),
            hist["serie_2"].max(),
            hist["serie_3"].max(),
            hist["serie_4"].max(),
        )
    )
    best_6 = int(
        max(
            hist["total_dia_1"].max(),
            hist["total_dia_2"].max(),
        )
    )

    return {
        "promedio_general": round(float(hist["promedio_mes"].mean()), 2),
        "mejor_linea": int(hist["mejor_linea"].max()),
        "mejor_mes": int(hist["total_mes"].max()),
        "meses_jugados": int(hist.shape[0]),
        "total_acumulado": int(hist["total_mes"].sum()),
        "mejor_anio": best_year,
        "elegibilidad": elegibilidad,
        "mejor_serie_3": best_3,
        "mejor_serie_6": best_6,
    }


def build_player_pdf(player_row: pd.Series, hist: pd.DataFrame, summary: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=16,
        rightMargin=16,
        topMargin=16,
        bottomMargin=16,
    )
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"<b>ASOBOLOS PICHINCHA - FICHA DEL JUGADOR</b>", styles["Title"])
    subtitle = Paragraph(
        f"{player_row['display_name']} | {player_row['sexo']} | {player_row['club'] or '-'} | {player_row['categoria'] or '-'}",
        styles["Normal"],
    )
    story.extend([title, Spacer(1, 6), subtitle, Spacer(1, 10)])

    info_rows = [
        ["Promedio general", summary["promedio_general"], "Mejor línea", summary["mejor_linea"]],
        ["Mejor mes", summary["mejor_mes"], "Meses jugados", summary["meses_jugados"]],
        ["Total acumulado", summary["total_acumulado"], "Mejor año", summary["mejor_anio"]],
        ["Mejor serie 3", summary.get("mejor_serie_3", 0), "Mejor serie 6", summary.get("mejor_serie_6", 0)],
        ["Elegibilidad", summary["elegibilidad"], "Cédula", player_row.get("cedula", "") or "-"],
    ]

    info_table = Table(info_rows, colWidths=[95, 120, 95, 170])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.whitesmoke, colors.HexColor("#F7F7F7")]),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
    ]))
    story.extend([info_table, Spacer(1, 12)])

    if not hist.empty:
        detail = hist[[
            "year", "month_name",
            "line_1", "line_2", "line_3", "serie_1",
            "line_4", "line_5", "line_6", "serie_2", "total_dia_1",
            "line_7", "line_8", "line_9", "serie_3",
            "line_10", "line_11", "line_12", "serie_4", "total_dia_2",
            "total_mes", "promedio_mes", "mejor_linea"
        ]].copy()

        detail.columns = [
            "Año", "Mes",
            "L1", "L2", "L3", "S1",
            "L4", "L5", "L6", "S2", "Día 1",
            "L7", "L8", "L9", "S3",
            "L10", "L11", "L12", "S4", "Día 2",
            "Total", "Prom.", "Mej. Línea"
        ]

        for col in detail.columns:
            detail[col] = detail[col].apply(
                lambda x: "" if pd.isna(x) else str(round(float(x), 2)) if isinstance(x, float) else str(x)
            )

        data = [list(detail.columns)] + detail.values.tolist()
        widths = [36, 56, 28, 28, 28, 34, 28, 28, 28, 34, 42, 28, 28, 28, 34, 30, 30, 30, 34, 42, 46, 42, 40, 46]
        total_width = landscape(A4)[0] - doc.leftMargin - doc.rightMargin
        scale = min(1.0, total_width / max(sum(widths), 1))
        widths = [round(w * scale, 2) for w in widths]

        table = Table(data, repeatRows=1, colWidths=widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#222831")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F7F7")]),
            ("FONTSIZE", (0,0), (-1,0), 7),
            ("FONTSIZE", (0,1), (-1,-1), 6.2),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,0), 5),
            ("BOTTOMPADDING", (0,0), (-1,0), 5),
            ("TOPPADDING", (0,1), (-1,-1), 3),
            ("BOTTOMPADDING", (0,1), (-1,-1), 3),
        ]))
        story.append(Paragraph("<b>Historial mensual con líneas y totales</b>", styles["Heading3"]))
        story.append(Spacer(1, 6))
        story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render_player_profile_content(results_df: pd.DataFrame, players_df: pd.DataFrame, public_mode: bool = False) -> None:
    title = "🌐 Consulta pública de jugadores" if public_mode else "👤 Ficha del jugador"
    st.title(title)
    if players_df.empty:
        st.info("No hay jugadores inscritos.")
        return

    top_cols = st.columns([1, 1, 1.2] if public_mode else [1, 1])
    with top_cols[0]:
        sexo = st.selectbox("Sección", GENDER_OPTIONS, key="public_profile_gender" if public_mode else "profile_gender")
    sec = players_df[players_df["sexo"] == sexo].copy()
    if sec.empty:
        st.info(f"No hay jugadores en {sexo}.")
        return

    with top_cols[1]:
        search = st.text_input("Buscar jugador", key="public_profile_search" if public_mode else "profile_search")
    if search.strip():
        sec = sec[sec["display_name"].str.contains(search.strip(), case=False, na=False)]
        if sec.empty:
            st.warning("No se encontraron jugadores con ese texto.")
            return

    options = {f"{r['display_name']} | {r['club']}": int(r['id']) for _, r in sec.iterrows()}
    selector_col = top_cols[2] if public_mode else st.container()
    with selector_col:
        pick = st.selectbox("Jugador", list(options.keys()), key="public_profile_pick" if public_mode else "profile_pick")
    player_id = options[pick]
    prow = sec[sec["id"] == player_id].iloc[0]
    hist = player_history(results_df, player_id)
    summary = build_player_summary(prow, hist, results_df)

    info_left, info_right = st.columns([0.75, 1.65])
    with info_left:
        st.markdown("### Datos de ficha")
        st.write(f"**Nombre:** {prow['display_name']}")
        st.write(f"**Sexo:** {prow['sexo']}")
        st.write(f"**Club:** {prow['club'] or '-'}")
        st.write(f"**Categoría:** {prow['categoria'] or '-'}")
        if not public_mode:
            st.write(f"**Cédula:** {prow['cedula'] or '-'}")
            st.write(f"**Fecha nacimiento:** {prow['fecha_nacimiento'] or '-'}")
            st.write(f"**Teléfono:** {prow['telefono'] or '-'}")
            st.write(f"**Correo:** {prow['correo'] or '-'}")
        st.write(f"**Elegibilidad:** {summary['elegibilidad']}")
        if not hist.empty:
            pdf_bytes = build_player_pdf(prow, hist, summary)
            st.download_button(
                "Descargar ficha PDF",
                data=pdf_bytes,
                file_name=f"ficha_{str(prow['display_name']).replace(' ', '_').lower()}.pdf",
                mime="application/pdf",
                key=f"pdf_player_{'public' if public_mode else 'admin'}_{player_id}",
            )

    with info_right:
        if hist.empty:
            st.info("Este jugador aún no tiene resultados.")
        else:
            stat_card_grid([
                ("Promedio general", f"{summary['promedio_general']:.2f}"),
                ("Mejor línea", summary["mejor_linea"]),
                ("Mejor serie 3", summary.get("mejor_serie_3", 0)),
                ("Mejor serie 6", summary.get("mejor_serie_6", 0)),
                ("Mejor mes", summary["mejor_mes"]),
                ("Meses jugados", summary["meses_jugados"]),
                ("Total acumulado", summary["total_acumulado"]),
            ])

            tabs = st.tabs(["Evolución", "Totales por mes", "Historial completo"])
            with tabs[0]:
                chart = hist[["year", "month_name", "promedio_mes"]].copy()
                chart["Periodo"] = chart["month_name"] + " " + chart["year"].astype(str)
                chart.columns = ["Año", "Mes", "Promedio", "Periodo"]
                st.line_chart(chart.set_index("Periodo")[["Promedio"]])

            with tabs[1]:
                monthly = hist[["year", "month_name", "total_mes", "promedio_mes", "mejor_linea"]].copy()
                monthly.columns = ["Año", "Mes", "Total Mes", "Promedio", "Mejor Línea"]
                st.dataframe(monthly, use_container_width=True, hide_index=True)

            with tabs[2]:
                show = hist[["year", "month_name", "serie_1", "serie_2", "total_dia_1", "serie_3", "serie_4", "total_dia_2", "total_mes", "promedio_mes", "mejor_linea", "peor_linea"]].copy()
                show.columns = ["Año", "Mes", "Serie 1", "Serie 2", "Total Día 1", "Serie 3", "Serie 4", "Total Día 2", "Total Mes", "Promedio", "Mejor Línea", "Peor Línea"]
                st.dataframe(show, use_container_width=True, hide_index=True)


def page_public_view(results_df: pd.DataFrame, players_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="badge">Consulta pública</div>
            <h1 style="margin:.5rem 0 0 0;">Asobolos Pichincha</h1>
            <div class="muted">Consulta el ranking general y la ficha deportiva de cada jugador.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if results_df.empty:
        st.info("No hay resultados cargados todavía.")
    else:
        st.markdown("## Ranking general")
        c1, c2, c3 = st.columns([1, 1, 1.2])
        with c1:
            year = st.selectbox(
                "Temporada",
                sorted(results_df["year"].unique()),
                index=len(sorted(results_df["year"].unique())) - 1,
                key="public_year",
            )
        with c2:
            sexo = st.selectbox("Sección", GENDER_OPTIONS, key="public_gender")
        with c3:
            public_search = st.text_input("Buscar jugador o club", key="public_rank_search")

        ranking, total_months, _required_months = build_season_ranking(results_df, int(year))
        sec = ranking[ranking["sexo"] == sexo].copy()
        sec = apply_eligibility_view(sec, "General", "Todos")

        st.caption(f"Temporada {year} | Meses jugados: {total_months}")

        month_subset = results_df[(results_df["year"] == int(year)) & (results_df["sexo"] == sexo)].copy()
        months_present = sorted(month_subset["month_code"].dropna().unique().tolist(), key=month_sort_key) if not month_subset.empty else []
        month_pivot = pd.DataFrame()

        if not month_subset.empty:
            month_pivot = month_subset.pivot_table(
                index="jugador",
                columns="month_code",
                values="total_mes",
                aggfunc="max",
            ).reset_index()
            for m in months_present:
                if m not in month_pivot.columns:
                    month_pivot[m] = None
            month_pivot = month_pivot[["jugador", *months_present]]

        show = sec[["ranking_general", "jugador", "club_actual", "promedio", "pines"]].copy()
        show.columns = ["Ranking", "Jugador", "Club", "Promedio", "Total acumulado"]

        if not month_pivot.empty:
            month_pivot = month_pivot.rename(columns={"jugador": "Jugador", **{m: MONTH_LABELS.get(m, m) for m in months_present}})
            month_cols_named = [MONTH_LABELS.get(m, m) for m in months_present]
            show = show[[c for c in show.columns if c not in month_cols_named]].copy()
            show = show.merge(month_pivot, on="Jugador", how="left")
            ordered_months = [MONTH_LABELS.get(m, m) for m in months_present]
            base_before = [c for c in show.columns if c not in ordered_months and c != "Total acumulado"]
            tail_cols = [c for c in ["Total acumulado"] if c in show.columns]
            fixed_cols = base_before + ordered_months + tail_cols
            fixed_cols = [c for c in fixed_cols if c in show.columns]
            fixed_cols = list(dict.fromkeys(fixed_cols))
            show = show.loc[:, ~show.columns.duplicated()]
            show = show[fixed_cols]

        if public_search.strip():
            search_text = public_search.strip()
            mask = (
                show["Jugador"].astype(str).str.contains(search_text, case=False, na=False)
                | show["Club"].astype(str).str.contains(search_text, case=False, na=False)
            )
            show = show[mask].copy()

        st.dataframe(show.loc[:, ~show.columns.duplicated()], use_container_width=True, hide_index=True)

    st.markdown("## Ficha pública del jugador")
    render_player_profile_content(results_df, players_df, public_mode=True)

def page_player_profile(results_df: pd.DataFrame, players_df: pd.DataFrame) -> None:
    render_player_profile_content(results_df, players_df, public_mode=False)

def page_data(results_df: pd.DataFrame) -> None:
    st.title("📦 Reportes y exportación")
    if results_df.empty:
        st.info("No hay datos para exportar.")
        return

    year = st.selectbox("Año", sorted(results_df["year"].unique()), index=len(sorted(results_df["year"].unique())) - 1, key="data_year")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        scope = st.selectbox("Sección", ["Hombre", "Mujer", "Ambos"], key="data_scope")
    with f2:
        ranking_mode = st.selectbox("Modo de ranking", ["Oficial", "General"], key="data_mode")
    with f3:
        eligibility_filter = st.selectbox("Filtro de elegibilidad", ["Todos", "Solo elegibles", "Solo no elegibles"], key="data_eligibility")
    with f4:
        pdf_section_mode = st.selectbox("PDF", ["Una tabla", "Dos tablas por sexo"], key="pdf_section_mode")

    ranking, total_months, required_months = build_season_ranking(results_df, int(year))

    st.markdown("### Configuración del reporte")
    selected_columns = st.multiselect(
        "Columnas fijas a incluir",
        ["Ranking", "Jugador", "Club", "Categoría", "Meses jugados", "% cumplimiento", "Promedio", "Mejor línea", "Regularidad", "Estado"],
        default=["Ranking", "Jugador", "Club", "Categoría", "Promedio", "Estado"],
        key="report_columns",
    )

    if "Jugador" not in selected_columns:
        selected_columns = ["Jugador", *selected_columns]
    if "Ranking" not in selected_columns:
        selected_columns = ["Ranking", *selected_columns]

    st.caption(
        f"Se incluirán automáticamente los meses jugados en la temporada ({total_months}) y al final el Total acumulado."
    )

    scopes = ["Hombre", "Mujer"] if scope == "Ambos" else [scope]

    report_tables = []
    preview_tables = []

    for sx in scopes:
        official = ranking[ranking["sexo"] == sx].copy()
        official = apply_eligibility_view(official, ranking_mode, eligibility_filter)
        report_df = build_report_table(results_df, official, sx, int(year), ranking_mode, selected_columns)
        report_tables.append((sx, report_df))
        preview_tables.append((sx, report_df))

    st.markdown("### Vista previa del reporte")
    st.caption(
        f"Meses jugados en la temporada: {total_months} | "
        f"Regla vigente: mínimo {required_months} meses para ser elegible a nacionales."
    )

    for sx, table_df in preview_tables:
        if scope == "Ambos" or pdf_section_mode == "Dos tablas por sexo":
            st.markdown(f"#### {sx}")
        st.dataframe(table_df, use_container_width=True, hide_index=True)

    csv_df = pd.concat(
        [df.assign(Seccion=label) for label, df in preview_tables],
        ignore_index=True
    ) if preview_tables else pd.DataFrame()

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Descargar reporte CSV",
            csv_df.to_csv(index=False).encode("utf-8"),
            file_name=f"reporte_{ranking_mode.lower()}_{scope.lower()}_{year}.csv",
            mime="text/csv",
        )
    with d2:
        if st.button("Preparar PDF", key="prepare_pdf_accumulated"):
            if scope == "Ambos" and pdf_section_mode == "Una tabla":
                combined = pd.concat(
                    [df.assign(Sección=label) for label, df in report_tables],
                    ignore_index=True
                )
                combined_cols = ["Sección", *[c for c in combined.columns if c != "Sección"]]
                combined = combined[combined_cols]
                pdf_tables = [("Hombres y Mujeres", combined)]
                scope_label = f"Ambos {ranking_mode}"
            else:
                pdf_tables = report_tables
                scope_label = f"{scope} {ranking_mode}"

            st.session_state["pdf_acumulado_ready"] = build_accumulated_pdf(
                pdf_tables, int(year), scope_label, int(total_months), int(required_months)
            )

        if st.session_state.get("pdf_acumulado_ready"):
            st.download_button(
                "Descargar reporte PDF",
                data=st.session_state["pdf_acumulado_ready"],
                file_name=f"reporte_{ranking_mode.lower()}_{scope.lower()}_{year}.pdf",
                mime="application/pdf",
                key="download_accumulated_pdf",
            )


def main() -> None:
    inject_theme()
    init_db()

    players_df = load_players_df()
    results_df = load_results_df()

    is_admin = admin_login_box()

    if not is_admin:
        page_public_view(results_df, players_df)
        return

    sidebar_admin()

    menu = [
        "Dashboard",
        "Jugadores",
        "Ingreso mensual",
        "Ranking mensual",
        "Ficha del jugador",
        "Vista pública",
        "Reportes",
    ]
    default_page = st.session_state.get("dashboard_target_page", "Dashboard")
    default_index = menu.index(default_page) if default_page in menu else 0
    try:
        page = st.sidebar.radio("Menú", menu, index=default_index, use_container_width=True)
    except TypeError:
        page = st.sidebar.radio("Menú", menu, index=default_index)
    st.session_state["dashboard_target_page"] = page

    if page == "Dashboard":
        page_dashboard(results_df, players_df)
    elif page == "Jugadores":
        page_player_registration(players_df)
    elif page == "Ingreso mensual":
        page_entry(players_df, results_df)
    elif page == "Ranking mensual":
        page_monthly_ranking(results_df)
    elif page == "Ficha del jugador":
        page_player_profile(results_df, players_df)
    elif page == "Vista pública":
        page_public_view(results_df, players_df)
    else:
        page_data(results_df)


# =========================
# Supabase backend overrides
# =========================

@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception as e:
        raise RuntimeError(
            "Faltan SUPABASE_URL y SUPABASE_KEY en .streamlit/secrets.toml o en Streamlit Cloud Secrets."
        ) from e
    return create_client(url, key)


def init_db() -> None:
    # Las tablas ya deben existir en Supabase.
    return None


def _safe_execute(builder):
    try:
        return builder.execute()
    except Exception as e:
        st.error(f"Error de Supabase: {e}")
        raise


def _rows_to_df(rows) -> pd.DataFrame:
    return pd.DataFrame(rows or [])


@st.cache_data(show_spinner=False)
def load_players_df() -> pd.DataFrame:
    sb = get_supabase()
    rows = _safe_execute(
        sb.table("players").select("*").order("sexo").order("display_name")
    ).data
    df = _rows_to_df(rows)
    if df.empty:
        return df
    if "activo" in df.columns:
        # normalizar a 1/0 para no romper la UI existente
        df["activo"] = df["activo"].apply(lambda x: 1 if bool(x) else 0)
    return df


@st.cache_data(show_spinner=False)
def load_results_df() -> pd.DataFrame:
    sb = get_supabase()
    results = _safe_execute(sb.table("monthly_results").select("*")).data
    players = _safe_execute(sb.table("players").select("*")).data

    rdf = _rows_to_df(results)
    pdf = _rows_to_df(players)

    if rdf.empty or pdf.empty:
        return pd.DataFrame()

    if "activo" in pdf.columns:
        pdf["activo"] = pdf["activo"].apply(lambda x: 1 if bool(x) else 0)

    df = rdf.merge(pdf, left_on="player_id", right_on="id", how="left", suffixes=("", "_player"))
    df["jugador"] = df["display_name"]
    df["club_actual"] = df["club"]
    df["month_order"] = df["month_code"].map(month_sort_key)
    return df.sort_values(["year", "month_order", "sexo", "jugador"]).reset_index(drop=True)


def upsert_player(
    name: str,
    sexo: str = "",
    club: str = "",
    categoria: str = "",
    cedula: str = "",
    fecha_nacimiento: str = "",
    telefono: str = "",
    correo: str = "",
    activo: int = 1,
) -> int:
    sb = get_supabase()
    norm = normalize_name(name)

    existing = _safe_execute(
        sb.table("players").select("id").eq("normalized_name", norm).limit(1)
    ).data

    payload = {
        "normalized_name": norm,
        "display_name": display_name(name),
        "sexo": sexo.strip(),
        "club": club.strip(),
        "categoria": categoria.strip(),
        "cedula": cedula.strip(),
        "fecha_nacimiento": fecha_nacimiento.strip(),
        "telefono": telefono.strip(),
        "correo": correo.strip(),
        "activo": bool(activo),
        "updated_at": "now()",
    }

    if existing:
        player_id = int(existing[0]["id"])
        _safe_execute(
            sb.table("players").update(payload).eq("id", player_id)
        )
    else:
        payload["created_at"] = "now()"
        inserted = _safe_execute(
            sb.table("players").insert(payload)
        ).data
        player_id = int(inserted[0]["id"])
    load_players_df.clear()
    return player_id


def update_player_by_id(
    player_id: int,
    name: str,
    sexo: str,
    club: str,
    categoria: str,
    cedula: str,
    fecha_nacimiento: str,
    telefono: str,
    correo: str,
    activo: int,
) -> None:
    sb = get_supabase()
    payload = {
        "normalized_name": normalize_name(name),
        "display_name": display_name(name),
        "sexo": sexo.strip(),
        "club": club.strip(),
        "categoria": categoria.strip(),
        "cedula": cedula.strip(),
        "fecha_nacimiento": fecha_nacimiento.strip(),
        "telefono": telefono.strip(),
        "correo": correo.strip(),
        "activo": bool(activo),
    }
    _safe_execute(sb.table("players").update(payload).eq("id", int(player_id)))
    load_players_df.clear()


def get_existing_result(player_id: int, year: int, month_code: str):
    sb = get_supabase()
    rows = _safe_execute(
        sb.table("monthly_results")
        .select("*")
        .eq("player_id", int(player_id))
        .eq("year", int(year))
        .eq("month_code", month_code)
        .limit(1)
    ).data
    return rows[0] if rows else None


def save_monthly_result(player_id: int, year: int, month_code: str, club_snapshot: str, lines: list[int], notes: str = "") -> None:
    m = compute_metrics(lines)
    sb = get_supabase()
    payload = {
        "player_id": int(player_id),
        "year": int(year),
        "month_code": month_code,
        "month_name": MONTH_LABELS.get(month_code, month_code),
        "club_snapshot": club_snapshot,
        "line_1": int(lines[0]),
        "line_2": int(lines[1]),
        "line_3": int(lines[2]),
        "line_4": int(lines[3]),
        "line_5": int(lines[4]),
        "line_6": int(lines[5]),
        "line_7": int(lines[6]),
        "line_8": int(lines[7]),
        "line_9": int(lines[8]),
        "line_10": int(lines[9]),
        "line_11": int(lines[10]),
        "line_12": int(lines[11]),
        "serie_1": int(m["serie_1"]),
        "serie_2": int(m["serie_2"]),
        "total_dia_1": int(m["total_dia_1"]),
        "serie_3": int(m["serie_3"]),
        "serie_4": int(m["serie_4"]),
        "total_dia_2": int(m["total_dia_2"]),
        "total_mes": int(m["total_mes"]),
        "promedio_mes": float(m["promedio_mes"]),
        "mejor_linea": int(m["mejor_linea"]),
        "peor_linea": int(m["peor_linea"]),
        "notes": notes.strip(),
    }
    existing = get_existing_result(player_id, year, month_code)
    if existing:
        _safe_execute(
            sb.table("monthly_results")
            .update(payload)
            .eq("player_id", int(player_id))
            .eq("year", int(year))
            .eq("month_code", month_code)
        )
    else:
        _safe_execute(sb.table("monthly_results").insert(payload))
    load_results_df.clear()


def delete_monthly_result(player_id: int, year: int, month_code: str) -> None:
    sb = get_supabase()
    _safe_execute(
        sb.table("monthly_results")
        .delete()
        .eq("player_id", int(player_id))
        .eq("year", int(year))
        .eq("month_code", month_code)
    )
    load_results_df.clear()



if __name__ == "__main__":
    main()
