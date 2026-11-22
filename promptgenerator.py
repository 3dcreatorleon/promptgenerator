import os
import re
import streamlit as st
from deep_translator import MyMemoryTranslator

st.set_page_config(page_title="Prompt Generator", layout="wide")

MARKDOWNS_DIR = "./markdowns"
LIGHTS_FILE = os.path.join(MARKDOWNS_DIR, "lights.md")
MIDJOURNEY_STYLE_FILE = os.path.join(MARKDOWNS_DIR, "midjourneystyle.md")


@st.cache_data
def parse_grouped_markdown(filepath: str) -> dict[str, list[str]]:
    """
    Lee un archivo .md y devuelve un diccionario {categoria: [items...]}.
    Soporta:
      - Encabezados (#, ##, ###) como categorías y listas (-, *, +) o líneas de texto como ítems.
      - Líneas con formato 'Categoria: item1, item2' o 'Categoria | item'.
    """
    if not os.path.exists(filepath):
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    grouped: dict[str, list[str]] = {}
    current_category: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("<!--"):
            continue

        # Encabezado de categoría (# / ## / ###)
        header_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if header_match:
            current_category = header_match.group(1).strip()
            grouped.setdefault(current_category, [])
            continue

        # Elemento de lista (- item / * item / + item)
        bullet_match = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet_match:
            item = bullet_match.group(1).strip()
            if current_category is None:
                current_category = "General"
                grouped.setdefault(current_category, [])
            if item not in grouped[current_category]:
                grouped[current_category].append(item)
            continue

        # Formato alternativo "Categoría: valor" fuera de encabezados
        if ":" in line and current_category is None:
            cat, val = line.split(":", 1)
            cat = cat.strip()
            val = val.strip()
            if cat and val:
                grouped.setdefault(cat, [])
                for part in [p.strip() for p in val.split(",") if p.strip()]:
                    if part not in grouped[cat]:
                        grouped[cat].append(part)
            continue

        # Texto plano como ítem bajo la categoría activa
        if current_category is not None:
            if line not in grouped[current_category]:
                grouped[current_category].append(line)

    # Limpiar categorías vacías
    return {k: v for k, v in grouped.items() if v}


@st.cache_data
def translate_to_english(text: str) -> str:
    """Traduce al inglés únicamente cuando se solicita explícitamente."""
    clean = text.strip()
    if not clean:
        return ""
    return MyMemoryTranslator(source="es-ES", target="en-GB").translate(clean)


def render_lighting_selectors(lights_data: dict[str, list[str]]) -> tuple[str, str]:
    """Renderiza los dos desplegables de iluminación a partir de lights.md."""
    st.subheader("Iluminación")
    if not lights_data:
        st.warning(f"No se encontraron datos en `{LIGHTS_FILE}`.")
        return "", ""

    categories = list(lights_data.keys())
    col1, col2 = st.columns(2)

    with col1:
        selected_light_cat = st.selectbox(
            "Categoría de luz",
            options=["Ninguna"] + categories,
            key="light_category_select",
        )

    with col2:
        if selected_light_cat != "Ninguna":
            light_types = lights_data.get(selected_light_cat, [])
            selected_light_type = st.selectbox(
                "Tipo de luz",
                options=["Ninguno"] + light_types,
                key="light_type_select",
            )
        else:
            selected_light_type = st.selectbox(
                "Tipo de luz",
                options=["Ninguno"],
                disabled=True,
                key="light_type_select_disabled",
            )

    return (
        "" if selected_light_cat == "Ninguna" else selected_light_cat,
        "" if selected_light_type == "Ninguno" else selected_light_type,
    )


def render_midjourney_style_selectors(mj_data: dict[str, list[str]]) -> tuple[str, str]:
    """Renderiza los dos desplegables de Estilo Midjourney a partir de midjourneystyle.md."""
    st.subheader("Estilo Midjourney")
    if not mj_data:
        st.warning(f"No se encontraron datos en `{MIDJOURNEY_STYLE_FILE}`.")
        return "", ""

    mj_categories = list(mj_data.keys())
    col1, col2 = st.columns(2)

    with col1:
        selected_mj_cat = st.selectbox(
            "Categoría de Midjourney",
            options=["Ninguna"] + mj_categories,
            key="mj_category_select",
        )

    with col2:
        if selected_mj_cat != "Ninguna":
            artists = mj_data.get(selected_mj_cat, [])
            selected_artist = st.selectbox(
                "Artista / Estilo específico",
                options=["Ninguno"] + artists,
                key="mj_artist_select",
            )
        else:
            selected_artist = st.selectbox(
                "Artista / Estilo específico",
                options=["Ninguno"],
                disabled=True,
                key="mj_artist_select_disabled",
            )

    return (
        "" if selected_mj_cat == "Ninguna" else selected_mj_cat,
        "" if selected_artist == "Ninguno" else selected_artist,
    )


def main() -> None:
    st.title("Generador de Prompts")

    lights_data = parse_grouped_markdown(LIGHTS_FILE)
    mj_data = parse_grouped_markdown(MIDJOURNEY_STYLE_FILE)

    # 1. Cuadro donde se escribe el prompt base
    base_prompt = st.text_area(
        "Escribe tu prompt",
        height=120,
        placeholder="Describe la escena, sujeto, entorno o acción...",
        key="base_prompt_input",
    )

    # 2. Dos desplegables de iluminación justo después del cuadro de prompt
    light_cat, light_type = render_lighting_selectors(lights_data)

    st.divider()

    # 3. Apartado de checks (incluyendo 'Estilo Midjourney')
    st.subheader("Opciones y estilos")
    mj_mode = st.checkbox("Estilo Midjourney", value=False, key="estilo_midjourney_check")

    mj_cat = ""
    mj_artist = ""
    extra_options: list[str] = []

    if mj_mode:
        # Al activar Estilo Midjourney: desaparecen el resto de opciones,
        # quedan las de iluminación (ya mostradas arriba) y aparecen los 2 desplegables de Midjourney
        mj_cat, mj_artist = render_midjourney_style_selectors(mj_data)
    else:
        # Resto de checks / opciones normales (puedes añadir aquí los tuyos)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.checkbox("Fotorrealismo", key="chk_photorealism"):
                extra_options.append("photorealistic, raw photography")
        with c2:
            if st.checkbox("Alta definición", key="chk_hd"):
                extra_options.append("high detail, sharp focus")
        with c3:
            if st.checkbox("Sin texto", key="chk_notext"):
                extra_options.append("no text, no watermark")

    st.divider()

    # 4. Construcción del prompt final
    parts: list[str] = []
    if base_prompt.strip():
        parts.append(base_prompt.strip())
    if light_type:
        parts.append(light_type)
    elif light_cat:
        parts.append(light_cat)

    if mj_mode:
        if mj_artist:
            parts.append(f"style of {mj_artist}")
        elif mj_cat:
            parts.append(f"{mj_cat} style")
    else:
        parts.extend(extra_options)

    final_prompt_es = ", ".join(parts)

    st.markdown("**Prompt generado (ES):**")
    st.code(final_prompt_es or "Escribe algo o selecciona opciones...", language="text")

    if st.button("Generar / Traducir a Inglés", type="primary"):
        if not final_prompt_es:
            st.warning("Introduce un prompt o selecciona alguna opción primero.")
        else:
            with st.spinner("Traduciendo..."):
                translated = translate_to_english(final_prompt_es)
            st.markdown("**Prompt final (EN):**")
            st.code(translated, language="text")


if __name__ == "__main__":
    main()