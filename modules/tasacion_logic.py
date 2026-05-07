"""
Lógica de Tasación - Motor de cálculo de valuaciones inmobiliarias
Sistema LUMEN basado en comparables y ajustes por calidad
"""
from typing import List, Dict

ESTADO_LABELS = {1: "Malo", 2: "Regular", 3: "Bueno", 4: "Excelente"}
UBICACION_LABELS = {1: "Mala", 2: "Regular", 3: "Buena", 4: "Excelente"}

# Pesos de ajuste por punto de diferencia en escala 1-4
PESO_ESTADO = 0.05   # 5% por nivel de diferencia de estado edilicio
PESO_UBICACION = 0.07  # 7% por nivel de diferencia de ubicación

# Margen para rango bajo/alto
MARGEN_BAJO = 0.08   # -8%
MARGEN_ALTO = 0.08   # +8%


def calcular_puntaje_total(estado: int, ubicacion: int) -> float:
    """Puntaje compuesto de un inmueble (promedio ponderado)."""
    return round((estado * 0.5 + ubicacion * 0.5), 2)


def calcular_usd_m2(precio: float, metros2: float) -> float:
    """Precio por m² de un comparable."""
    if metros2 <= 0:
        return 0.0
    return round(precio / metros2, 2)


def factor_ajuste(puntaje_sujeto: float, puntaje_comparable: float) -> float:
    """
    Factor multiplicador para ajustar el USD/m² del comparable
    al nivel de calidad de la propiedad sujeto.

    Si el sujeto es mejor → factor > 1 (los comparables valen más si fueran iguales).
    Si el sujeto es peor  → factor < 1.
    """
    diferencia = puntaje_sujeto - puntaje_comparable
    # Cada 0.5 puntos de diferencia representa ~6% de ajuste
    factor = 1 + (diferencia * 0.12)
    # Limitar factor entre 0.70 y 1.40
    return round(max(0.70, min(1.40, factor)), 4)


def calcular_tasacion(
    metros2_sujeto: float,
    estado_sujeto: int,
    ubicacion_sujeto: int,
    comparables: List[Dict]
) -> Dict:
    """
    Calcula la tasación completa.

    comparables: lista de dicts con keys:
        - metros2, precio, estado_edilicio, ubicacion, link (opcional)
    
    Retorna dict con resultados completos.
    """
    if not comparables or metros2_sujeto <= 0:
        return {}

    puntaje_sujeto = calcular_puntaje_total(estado_sujeto, ubicacion_sujeto)

    comps_calculados = []
    usd_m2_ajustados = []

    for i, comp in enumerate(comparables):
        m2 = float(comp.get("metros2", 0))
        precio = float(comp.get("precio", 0))
        estado = int(comp.get("estado_edilicio", 2))
        ubicacion = int(comp.get("ubicacion", 2))

        if m2 <= 0 or precio <= 0:
            continue

        usd_m2_base = calcular_usd_m2(precio, m2)
        puntaje_comp = calcular_puntaje_total(estado, ubicacion)
        factor = factor_ajuste(puntaje_sujeto, puntaje_comp)
        usd_m2_ajustado = round(usd_m2_base * factor, 2)

        comps_calculados.append({
            "numero": i + 1,
            "link": comp.get("link", ""),
            "metros2": m2,
            "precio": precio,
            "estado_edilicio": estado,
            "estado_label": ESTADO_LABELS.get(estado, str(estado)),
            "ubicacion": ubicacion,
            "ubicacion_label": UBICACION_LABELS.get(ubicacion, str(ubicacion)),
            "puntaje_total": puntaje_comp,
            "usd_m2_base": usd_m2_base,
            "factor_ajuste": factor,
            "usd_m2_ajustado": usd_m2_ajustado,
        })
        usd_m2_ajustados.append(usd_m2_ajustado)

    if not usd_m2_ajustados:
        return {}

    promedio_usd_m2 = round(sum(usd_m2_ajustados) / len(usd_m2_ajustados), 2)
    promedio_puntajes_comp = round(
        sum(c["puntaje_total"] for c in comps_calculados) / len(comps_calculados), 2
    )

    valor_medio = round(promedio_usd_m2 * metros2_sujeto, 2)
    valor_minimo = round(valor_medio * (1 - MARGEN_BAJO), 2)
    valor_maximo = round(valor_medio * (1 + MARGEN_ALTO), 2)

    return {
        "puntaje_sujeto": puntaje_sujeto,
        "comparables": comps_calculados,
        "promedio_usd_m2": promedio_usd_m2,
        "promedio_puntajes_comp": promedio_puntajes_comp,
        "usd_m2_ajustado_final": promedio_usd_m2,
        "valor_minimo": valor_minimo,
        "valor_medio": valor_medio,
        "valor_maximo": valor_maximo,
        "metros2_sujeto": metros2_sujeto,
        "margen_pct": MARGEN_BAJO * 100,
    }


def format_usd(valor: float) -> str:
    """Formatea un valor en USD con separadores de miles."""
    return f"USD {valor:,.0f}".replace(",", ".")


def format_usd_m2(valor: float) -> str:
    return f"USD {valor:,.2f}/m²"
