from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd
from supabase import create_client


def normalize_name(name: str) -> str:
    import re
    return re.sub(r"\s+", " ", str(name or "").strip().upper()).replace(".", "")


def get_sqlite_df(db_path: Path, query: str) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def chunked(seq, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def load_sqlite_data(db_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    players = get_sqlite_df(db_path, "SELECT * FROM players")
    results = get_sqlite_df(db_path, "SELECT * FROM monthly_results")
    return players, results


def fetch_supabase_players(sb) -> dict[str, int]:
    rows = sb.table("players").select("id,normalized_name").execute().data or []
    return {str(r["normalized_name"]): int(r["id"]) for r in rows}


def upsert_players(sb, players_df: pd.DataFrame, dry_run: bool) -> dict[str, int]:
    if players_df.empty:
        return fetch_supabase_players(sb)

    payloads = []
    for _, row in players_df.iterrows():
        payloads.append({
            "normalized_name": str(row.get("normalized_name") or normalize_name(row.get("display_name", ""))),
            "display_name": str(row.get("display_name") or "").strip(),
            "sexo": str(row.get("sexo") or "").strip(),
            "club": str(row.get("club") or "").strip(),
            "categoria": str(row.get("categoria") or "").strip(),
            "cedula": str(row.get("cedula") or "").strip(),
            "fecha_nacimiento": str(row.get("fecha_nacimiento") or "").strip(),
            "telefono": str(row.get("telefono") or "").strip(),
            "correo": str(row.get("correo") or "").strip(),
            "activo": bool(int(row.get("activo", 1))) if pd.notna(row.get("activo")) else True,
        })

    print(f"Jugadores a migrar: {len(payloads)}")
    if dry_run:
        print("DRY RUN: no se enviaron jugadores a Supabase.")
        return {p["normalized_name"]: -1 for p in payloads}

    for batch in chunked(payloads, 200):
        sb.table("players").upsert(batch, on_conflict="normalized_name").execute()

    return fetch_supabase_players(sb)


def build_result_payloads(results_df: pd.DataFrame, players_df: pd.DataFrame, player_map: dict[str, int]) -> list[dict]:
    if results_df.empty:
        return []

    if "player_id" not in results_df.columns:
        raise RuntimeError("La tabla monthly_results de SQLite no tiene la columna player_id.")

    players_lookup = players_df[["id", "normalized_name"]].copy()
    players_lookup["id"] = players_lookup["id"].astype(int)
    id_to_norm = dict(zip(players_lookup["id"], players_lookup["normalized_name"]))

    payloads = []
    missing_players = []

    for _, row in results_df.iterrows():
        old_player_id = int(row["player_id"])
        normalized_name = id_to_norm.get(old_player_id)
        if not normalized_name:
            missing_players.append(old_player_id)
            continue

        new_player_id = player_map.get(str(normalized_name))
        if not new_player_id or new_player_id == -1:
            missing_players.append(old_player_id)
            continue

        payloads.append({
            "player_id": int(new_player_id),
            "year": int(row["year"]),
            "month_code": str(row["month_code"]),
            "month_name": str(row["month_name"]),
            "club_snapshot": str(row.get("club_snapshot") or ""),
            "line_1": int(row["line_1"]),
            "line_2": int(row["line_2"]),
            "line_3": int(row["line_3"]),
            "line_4": int(row["line_4"]),
            "line_5": int(row["line_5"]),
            "line_6": int(row["line_6"]),
            "line_7": int(row["line_7"]),
            "line_8": int(row["line_8"]),
            "line_9": int(row["line_9"]),
            "line_10": int(row["line_10"]),
            "line_11": int(row["line_11"]),
            "line_12": int(row["line_12"]),
            "serie_1": int(row["serie_1"]),
            "serie_2": int(row["serie_2"]),
            "total_dia_1": int(row["total_dia_1"]),
            "serie_3": int(row["serie_3"]),
            "serie_4": int(row["serie_4"]),
            "total_dia_2": int(row["total_dia_2"]),
            "total_mes": int(row["total_mes"]),
            "promedio_mes": float(row["promedio_mes"]),
            "mejor_linea": int(row["mejor_linea"]),
            "peor_linea": int(row["peor_linea"]),
            "notes": str(row.get("notes") or ""),
        })

    if missing_players:
        unique_missing = sorted(set(missing_players))
        print(f"Aviso: {len(unique_missing)} player_id de SQLite no pudieron mapearse a Supabase: {unique_missing[:10]}")

    return payloads


def upsert_results(sb, payloads: list[dict], dry_run: bool) -> None:
    print(f"Resultados mensuales a migrar: {len(payloads)}")
    if dry_run:
        print("DRY RUN: no se enviaron resultados a Supabase.")
        return

    for batch in chunked(payloads, 200):
        sb.table("monthly_results").upsert(batch, on_conflict="player_id,year,month_code").execute()


def count_remote(sb) -> tuple[int, int]:
    players = sb.table("players").select("id", count="exact").execute().count or 0
    results = sb.table("monthly_results").select("id", count="exact").execute().count or 0
    return int(players), int(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar datos desde SQLite a Supabase.")
    parser.add_argument("--sqlite", required=True, help="Ruta al archivo SQLite, por ejemplo asobolos.db")
    parser.add_argument("--url", required=True, help="SUPABASE_URL")
    parser.add_argument("--key", required=True, help="SUPABASE_KEY")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra conteos y validaciones, sin escribir en Supabase.")
    args = parser.parse_args()

    db_path = Path(args.sqlite)
    if not db_path.exists():
        print(f"No existe el archivo SQLite: {db_path}")
        return 1

    print(f"Leyendo SQLite: {db_path}")
    players_df, results_df = load_sqlite_data(db_path)
    print(f"Jugadores SQLite: {len(players_df)}")
    print(f"Resultados SQLite: {len(results_df)}")

    sb = create_client(args.url, args.key)

    player_map = upsert_players(sb, players_df, args.dry_run)
    result_payloads = build_result_payloads(results_df, players_df, player_map)
    upsert_results(sb, result_payloads, args.dry_run)

    if not args.dry_run:
        remote_players, remote_results = count_remote(sb)
        print(f"Supabase ahora tiene {remote_players} jugadores y {remote_results} resultados.")

    print("Migración finalizada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
